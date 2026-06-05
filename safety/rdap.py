"""
safety.rdap.py - Domain age checking via free RDAP (Registration Data Access Protocol).

Phase 2e: Warns on domains registered less than 30 days ago.
Phase 2f: /whois command returns full domain registration details.

Uses IANA's RDAP bootstrap to find the right registry, then queries
the RDAP server directly. No API key required - entirely free.
"""

import json
import re
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from urllib.parse import urlparse

import aiohttp

import stats


# Known RDAP server overrides for major TLDs (avoids the bootstrap roundtrip)
RDAP_SERVERS = {
    'com': 'https://rdap.verisign.com/com/v1/',
    'net': 'https://rdap.verisign.com/net/v1/',
    'org': 'https://rdap.publicinterestregistry.org/rdap/',
    'io': 'https://rdap.nic.io/',
    'co': 'https://rdap.nic.co/',
    'uk': 'https://rdap.nominet.uk/uk/',
    'de': 'https://rdap.denic.de/de/',
    'xyz': 'https://rdap.centralnic.com/xyz/',
    'online': 'https://rdap.centralnic.com/online/',
    'site': 'https://rdap.centralnic.com/site/',
    'tech': 'https://rdap.centralnic.com/tech/',
    'store': 'https://rdap.centralnic.com/store/',
    'app': 'https://rdap.nic.google/',
    'dev': 'https://rdap.nic.google/',
    'gg': 'https://rdap.nic.gg/',
    'me': 'https://rdap.nic.me/',
    'tv': 'https://rdap.nic.tv/',
    'cc': 'https://rdap.nic.cc/',
}

IANA_BOOTSTRAP_URL = "https://data.iana.org/rdap/dns.json"

# Two-part TLDs (SLD+ccTLD structure) - heuristic for domain splitting
# Full list from Mozilla PSL would need tldextract; this covers most common cases
TWO_PART_TLDS = {
    'co.uk', 'org.uk', 'me.uk', 'ltd.uk', 'plc.uk', 'net.uk', 'ac.uk', 'gov.uk',
    'co.jp', 'or.jp', 'ne.jp', 'ac.jp', 'ad.jp', 'go.jp',
    'com.au', 'net.au', 'org.au', 'edu.au', 'gov.au',
    'co.nz', 'net.nz', 'org.nz',
    'co.za', 'web.za', 'org.za',
    'co.il', 'org.il', 'net.il', 'ac.il', 'gov.il',
    'co.in', 'net.in', 'org.in', 'gen.in', 'firm.in', 'ind.in',
    'com.br', 'net.br', 'org.br', 'gov.br',
    'co.at', 'or.at',
    'co.kr', 'or.kr', 'ne.kr',
    'com.cn', 'net.cn', 'org.cn', 'gov.cn',
    'com.tw', 'net.tw', 'org.tw',
    'com.mx', 'net.mx', 'org.mx',
    'co.id', 'net.id', 'or.id', 'web.id',
}


async def _get_rdap_url(tld: str) -> Optional[str]:
    """Get the RDAP server URL for a TLD."""
    if tld in RDAP_SERVERS:
        return RDAP_SERVERS[tld]

    # Fallback: query IANA bootstrap (RFC 7484)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                IANA_BOOTSTRAP_URL,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    for entry in data.get("services", []):
                        # IANA format: [[tld_list], [url_list]] per RFC 7484
                        if isinstance(entry, list) and len(entry) >= 2:
                            tlds_list, servers_list = entry[0], entry[1]
                            if tld in tlds_list:
                                return servers_list[0]
                        # Some registries use dict format
                        elif isinstance(entry, dict):
                            if tld in entry.get("tlds", []):
                                return entry["tlds"][0]
    except Exception:
        pass
    return None


async def query_domain(domain: str) -> Optional[Dict[str, Any]]:
    """
    Query RDAP for domain registration info.
    Returns a dict with keys: domain, registered_date, registrar, nameservers, status
    or None if lookup fails.
    """
    clean = domain.lower().removeprefix("www.")
    parts = clean.split(".")

    # Determine TLD (handle multi-part TLDs like co.uk, com.au)
    tld = parts[-1]
    sld = ""
    if len(parts) >= 3 and f"{parts[-2]}.{parts[-1]}" in TWO_PART_TLDS:
        tld = f"{parts[-2]}.{parts[-1]}"
        sld = ".".join(parts[:-2]) if len(parts) > 2 else parts[0]
    else:
        sld = ".".join(parts[:-1]) if len(parts) > 1 else parts[0]

    # For the RDAP query, use the registered domain part (eTLD+1 format)
    hostname = sld.split(".")[-1] if sld else (parts[0] if parts else clean)

    rdap_url = await _get_rdap_url(tld)
    if not rdap_url:
        return None

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{rdap_url}domain/{hostname}.{tld}",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)

                    # Extract registration date
                    registered_date = None
                    for event in data.get("events", []):
                        if event.get("eventAction") == "registration":
                            registered_date = event.get("eventDate")
                            break

                    # Extract registrar
                    registrar = "Unknown"
                    entities = data.get("entities", [])
                    for entity in entities:
                        if "registrar" in (entity.get("roles", [])):
                            vcard = entity.get("vcardArray", [[], []])
                            if len(vcard) > 1:
                                for item in vcard[1]:
                                    if item[0] == "fn":
                                        registrar = item[3]
                                        break

                    # Nameservers
                    nameservers = [
                        ns.get("ldhName", "")
                        for ns in data.get("nameservers", [])
                    ]

                    # Status
                    status = [s for s in data.get("status", [])]

                    return {
                        "domain": f"{hostname}.{tld}",
                        "registered_date": registered_date,
                        "registrar": registrar,
                        "nameservers": nameservers[:5],
                        "status": status,
                        "raw": data,
                    }
    except Exception:
        pass
    return None


def get_domain_age_days(registered_date: Optional[str]) -> Optional[int]:
    """Calculate domain age in days from RDAP date string."""
    if not registered_date:
        return None
    try:
        reg_date = datetime.fromisoformat(registered_date.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = now - reg_date
        return delta.days
    except (ValueError, TypeError):
        return None
