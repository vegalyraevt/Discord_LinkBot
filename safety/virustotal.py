"""
safety.virustotal.py - VirusTotal URL scanning integration.

Per-server encrypted API key support:
  - Each server can provide its own VT key via /vtkey set
  - Keys are encrypted at rest using Fernet (keyvault.py)
  - Keys are NEVER echoed in any message or config display
  - Built-in rate limiting: configurable per-hour and daily caps
  - Premium users can disable limits via /vtkey limit disable

Self-hosting:
  - Set VT_LOCAL_MODE=true and VIRUSTOTAL_API_KEY in .env for single-server mode
"""

import os
import time
import re
import aiohttp
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from urllib.parse import urlparse

import discord
import stats
import keyvault


# Self-hosted mode (set in .env for single-server deployments)
VT_LOCAL_MODE = os.getenv("VT_LOCAL_MODE", "").lower() == "true"
VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY", "")

VIRUSTOTAL_URL_SCAN = "https://www.virustotal.com/api/v3/urls"
DAILY_LIMIT = 500

# Per-key rate tracking: {api_key: {"hourly": [(timestamp, count)], "daily": count, "daily_reset": datetime}}
_key_usage: Dict[str, Dict] = {}


def _get_hourly_count(api_key: str) -> int:
    """Count lookups in the last hour for this key."""
    now = time.time()
    entry = _key_usage.setdefault(api_key, {"hourly": [], "daily": 0, "daily_reset": datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)})
    entry["hourly"] = [ts for ts in entry["hourly"] if now - ts < 3600]
    return len(entry["hourly"])


def _increment_key_usage(api_key: str) -> None:
    """Record a lookup for this key."""
    now = time.time()
    entry = _key_usage.setdefault(api_key, {"hourly": [], "daily": 0, "daily_reset": datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)})
    entry["hourly"].append(now)
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    if today_start > entry["daily_reset"]:
        entry["daily"] = 0
        entry["daily_reset"] = today_start
    entry["daily"] += 1


def _check_rate_limit(api_key: str, hourly_limit: int = 20, daily_limit: int = 500) -> str | None:
    """Check if a key has exceeded rate limits. Returns error message or None."""
    if hourly_limit == 0 and daily_limit == 0:
        return None  # Limits disabled (premium)

    hourly_count = _get_hourly_count(api_key)
    if hourly_limit > 0 and hourly_count >= hourly_limit:
        return "Hourly lookup limit reached for this server."

    entry = _key_usage.get(api_key, {"daily": 0})
    if daily_limit > 0 and entry.get("daily", 0) >= daily_limit:
        return "Daily lookup limit reached for this server."

    return None


async def scan_url(url: str, config: dict = None, server_id: int = None) -> Optional[Dict[str, Any]]:
    """
    Submit a URL to VirusTotal for scanning. Returns analysis dict or None.

    Key priority:
      1. Per-server encrypted key (vt_api_key_encrypted in config)
      2. Local mode env var (VT_LOCAL_MODE + VIRUSTOTAL_API_KEY)
      3. None (feature disabled)
    """
    api_key = None
    hourly_limit = 20
    daily_limit = 500

    if config and server_id:
        vt_config = config.get("vt_settings", {})
        encrypted_key = vt_config.get("api_key_encrypted", "")
        if encrypted_key:
            try:
                api_key = keyvault.decrypt_value(encrypted_key)
            except Exception:
                return None  # Corrupted key, silently skip
            hourly_limit = vt_config.get("hourly_limit", 20)
            daily_limit = vt_config.get("daily_limit", 500)

    if not api_key and VT_LOCAL_MODE and VIRUSTOTAL_API_KEY:
        api_key = VIRUSTOTAL_API_KEY

    if not api_key:
        return None

    # Check rate limits
    limit_error = _check_rate_limit(api_key, hourly_limit, daily_limit)
    if limit_error:
        return None

    headers = {"x-apikey": api_key, "Accept": "application/json"}

    try:
        async with aiohttp.ClientSession() as session:
            form_data = aiohttp.FormData()
            form_data.add_field("url", url)
            async with session.post(VIRUSTOTAL_URL_SCAN, headers=headers, data=form_data, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return None
                submit_data = await resp.json(content_type=None)
                analysis_id = submit_data.get("data", {}).get("id", "")

            if not analysis_id:
                return None

            _increment_key_usage(api_key)

            # Poll for results
            for _ in range(6):
                async with session.get(f"https://www.virustotal.com/api/v3/analyses/{analysis_id}", headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status != 200:
                        break
                    analysis = await resp.json(content_type=None)
                    status = analysis.get("data", {}).get("attributes", {}).get("status", "")
                    if status == "completed":
                        stats_data = analysis.get("data", {}).get("attributes", {}).get("stats", {})
                        return {
                            "malicious": stats_data.get("malicious", 0),
                            "suspicious": stats_data.get("suspicious", 0),
                            "harmless": stats_data.get("harmless", 0),
                            "undetected": stats_data.get("undetected", 0),
                            "timeout": stats_data.get("timeout", 0),
                            "total": sum(stats_data.values()),
                            "permalink": f"https://www.virustotal.com/gui/url/{analysis_id}",
                        }
                    elif status == "queued":
                        import asyncio
                        await asyncio.sleep(1)
                    else:
                        break
    except Exception as e:
        print(f"VirusTotal scan error: {e}")

    return None


async def warn_virustotal(message: discord.Message, config: dict = None) -> None:
    """
    Scan URLs in a message with VirusTotal and warn if threats detected.
    Uses per-server encrypted key if configured.
    """
    if config is None:
        config = {}

    scored_domains = set()
    for raw_url in re.findall(r'https?://[^\s\)\]>]+', message.content):
        hostname = urlparse(raw_url).hostname
        if not hostname:
            continue
        hostname_clean = hostname.lower().removeprefix("www.")
        if hostname_clean in scored_domains:
            continue
        scored_domains.add(hostname_clean)

        server_id = message.guild.id if message.guild else None
        result = await scan_url(raw_url, config, server_id)
        if not result:
            continue

        await stats.increment("vt_scans")

        if result["malicious"] == 0 and result["suspicious"] == 0:
            continue

        malicious = result["malicious"]
        suspicious = result["suspicious"]
        total = result["total"]

        if malicious >= 3:
            color = discord.Color.red()
            title = "Malicious Link Detected (VirusTotal)"
        elif malicious >= 1:
            color = discord.Color.orange()
            title = "Suspicious Link Detected (VirusTotal)"
        else:
            color = discord.Color.yellow()
            title = "Link Flagged by VirusTotal"

        description = (
            f"**{malicious}** security engines flagged this as **malicious**.\n"
            f"**{suspicious}** engines marked it as **suspicious**.\n"
            f"**{result['harmless']}** engines found it clean.\n"
            f"Out of **{total}** total engines.\n\n"
            f"`{raw_url}`\n\n"
            f"[View full report on VirusTotal]({result['permalink']})"
        )

        embed = discord.Embed(title=title, description=description, color=color, url=result["permalink"])
        embed.set_footer(text="Powered by VirusTotal / LinkBot Safety")
        await message.channel.send(embed=embed)
        await stats.increment("safety_cards_shown")


def is_vt_configured(config: dict) -> bool:
    """Check if a server has a valid VT key configured."""
    vt_config = config.get("vt_settings", {})
    return bool(vt_config.get("api_key_encrypted", ""))
