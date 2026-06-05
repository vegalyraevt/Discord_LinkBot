"""
safety.ssrf.py - SSRF prevention utilities.

Provides async-safe URL validation that blocks connections to
private, loopback, link-local, and reserved IP addresses.

Used by: safety/__init__.py, enrichment/archive.py
"""

import asyncio
import socket
import ipaddress
from urllib.parse import urlparse


async def is_safe_url(url: str) -> bool:
    """
    Validate that a URL does not resolve to a private, loopback,
    link-local, or reserved IP address.

    Uses run_in_executor to avoid blocking the async event loop
    during DNS resolution.

    Returns True if the URL is safe to connect to.
    """
    try:
        hostname = urlparse(url).hostname
        if not hostname:
            return False
        loop = asyncio.get_event_loop()
        ip = await loop.run_in_executor(None, socket.gethostbyname, hostname)
        addr = ipaddress.ip_address(ip)
        if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
            print(f"SSRF blocked: {url} -> {ip}")
            return False
        return True
    except Exception:
        return False
