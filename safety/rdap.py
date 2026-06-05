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
    'dev': 'https://rdap.nic.google/',
    'gg': 'https://rdap.nic.gg/',
    'me': 'https://rdap.nic.me/',
    'tv': 'https://rdap.nic.tv/',
    'cc': 'https://rdap.nic.cc/',
}

IANA_BOOTSTRAP_URL = "https://data.iana.org/rdap/dns.json"


async def _get_rdap_url(tld: str) -> Optional[str]:
    """Get the RDAP server URL for a TLD."""
    if tld in RDAP_SERVERS:
        return RDAP_SERVERS[tld]

    # Fallback: query IANA bootstrap
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                IANA_BOOTSTRAP_URL,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    for service in data.get("services", []):
                        if tld in service.get("tlds", []):
                            return service["tlds"][0]
    except Exception:
        pass
    return None


async def query_domain(domain: str) -> Optional[Dict[str, Any]]:
    """
    Query RDAP for domain registration info.
    Returns a dict with keys: domain, registered_date, registrar, nameservers, status
    or None if lookup fails.
    """
    hostname = domain.lower().removeprefix("www.").split(".")[0]
    tld = domain.lower().removeprefix("www.").rsplit(".", 1)[-1] if "." in domain else "com"
    
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
        # RDAP dates are ISO 8601: 2024-01-15T12:00:00Z
        reg_date = datetime.fromisoformat(registered_date.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = now - reg_date
        return delta.days
    except (ValueError, TypeError):
        return None
