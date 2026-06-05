"""
safety.py - Safety/security checks for URLs and files.

Includes:
  - Phishing detection via SinkingYachts API
  - URL unshortening with redirect chain
  - Direct file inspection (type, size)
  - Executable file danger warnings
  - Suspicious TLD detection
  - HTTP downgrade warning
  - Domain age checker via RDAP
  - VirusTotal scanner
  - Composite safety score card
"""

import os
import re
import aiohttp
from urllib.parse import urlparse
from typing import Optional, List, Tuple

from safety import rdap
from safety import virustotal
from safety import scorecard

import discord
import stats


# Known URL shortener domains
SHORTENER_DOMAINS = {
    'bit.ly', 'tinyurl.com', 't.co', 'goo.gl', 'ow.ly', 'is.gd', 'buff.ly',
    'j.mp', 'cutt.ly', 'rb.gy', 'shrtco.de', 'v.gd', 'bl.ink', 't2m.io',
    'qr.ae', 'snip.ly', 'clk.im', 'rebrand.ly', 'short.gy', 'cutt.us',
    'soo.gd', 's.id', 'adf.ly', 'lnkd.in', 'amzn.to', 'wp.me',
    't.me', 'b.link', 'tiny.cc', 'shorturl.at', 'cli.re'
}

# Direct file extensions to inspect
FILE_EXTENSIONS = (
    '.zip', '.rar', '.7z', '.tar', '.gz', '.tgz', '.bz2', '.xz', '.iso', '.dmg', '.cab',
    '.exe', '.msi', '.apk', '.app', '.bat', '.cmd', '.sh', '.vbs', '.ps1', '.scr', '.jar', '.pif',
    '.mp4', '.mkv', '.avi', '.mov', '.webm', '.mp3', '.wav', '.flac', '.ogg',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.xlsm', '.ppt', '.pptx'
)

# Executable / dangerous file extensions
DANGEROUS_EXTENSIONS = {'.exe', '.msi', '.apk', '.bat', '.cmd', '.sh', '.vbs', '.ps1', '.scr', '.pif'}

# Suspicious TLDs
SUSPICIOUS_TLDS = {
    '.tk', '.ml', '.ga', '.cf', '.gq',
    '.xyz', '.top', '.click', '.work',
    '.bar', '.rest', '.hair', '.makeup',
    '.cyou', '.cfd', '.sbs', '.icu',
}

# General URL regex
GENERAL_URL_REGEX = re.compile(r'https?://(?:www\.)?([^/\s]+)(/[^\s]*[^\s\)\]>.,!?])?')


async def check_phishing(message: discord.Message) -> bool:
    """Check URLs against SinkingYachts phishing API. Returns True if malicious."""
    for raw_url in re.findall(r'https?://[^\s\)\]>]+', message.content):
        hostname = urlparse(raw_url).hostname
        if not hostname:
            continue
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://phish.sinking.yachts/v2/check/{hostname}",
                    timeout=aiohttp.ClientTimeout(total=3)
                ) as resp:
                    is_malicious = await resp.json()
            if is_malicious is True:
                await message.delete()
                await stats.increment("malicious_blocked")
                await stats.increment("messages_deleted")
                await message.channel.send("Malicious link removed to protect the kingdom. HYYYAAAAAHHH!")
                return True
        except Exception:
            pass
    return False


async def unshorten_links(message: discord.Message) -> None:
    """Detect and unshorten shortened URLs, showing full redirect chain."""
    url_matches = GENERAL_URL_REGEX.findall(message.content)
    for domain, path in url_matches:
        if domain.lower() in SHORTENER_DOMAINS:
            short_url = f"https://{domain}{path or ''}"
            try:
                redirect_chain = [short_url]
                current_url = short_url
                max_hops = 10
                async with aiohttp.ClientSession() as session:
                    for _ in range(max_hops):
                        async with session.get(
                            current_url, allow_redirects=False,
                            timeout=aiohttp.ClientTimeout(total=3)
                        ) as resp:
                            if resp.status in (301, 302, 303, 307, 308):
                                location = resp.headers.get('Location', '')
                                if not location:
                                    break
                                if location.startswith('/'):
                                    parsed = urlparse(current_url)
                                    location = f"{parsed.scheme}://{parsed.netloc}{location}"
                                redirect_chain.append(location)
                                current_url = location
                            else:
                                break
                if len(redirect_chain) == 1:
                    await message.reply(f"shortened link detected! for safety heres what it is linking too! {redirect_chain[0]}")
                elif len(redirect_chain) > 3:
                    embed = discord.Embed(
                        title="Shortened Link - Redirect Chain Detected",
                        description=f"This shortened link went through **{len(redirect_chain)} hops**.\n\n" + '\n'.join(f"{i}. {url}" for i, url in enumerate(redirect_chain, 1)),
                        color=discord.Color.orange()
                    )
                    await message.reply(embed=embed, mention_author=False)
                else:
                    hops_text = '\n'.join(f"-> {url}" for url in redirect_chain[1:])
                    await message.reply(f"**Redirect chain:**\n{short_url}\n{hops_text}")
                await stats.increment("links_unshortened")
            except Exception as e:
                print(f"Failed to unshorten URL {short_url}: {e}")


async def inspect_files(message: discord.Message, config: dict = None) -> None:
    """Inspect direct file links. Shows danger warning for executables."""
    if config is None:
        config = {}
    url_matches = GENERAL_URL_REGEX.findall(message.content)
    for domain, path in url_matches:
        if path and path.lower().endswith(FILE_EXTENSIONS):
            file_url = f"https://{domain}{path}"
            ext = os.path.splitext(path)[1].lower()
            is_dangerous = ext in DANGEROUS_EXTENSIONS
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.head(file_url, allow_redirects=True,
                        timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        content_type = resp.headers.get('Content-Type', 'unknown')
                        content_length = resp.headers.get('Content-Length')
                        if content_length:
                            size_bytes = int(content_length)
                            file_size = f"{size_bytes / 1_048_576:.2f} MB" if size_bytes >= 1_048_576 else f"{size_bytes / 1024:.2f} KB"
                        else:
                            file_size = "unknown size"
                if is_dangerous and config.get("file_warnings", True):
                    embed = discord.Embed(title="Dangerous File Detected", description=f"**{message.author.mention} posted a potentially harmful file!**\n\n`{file_url}`\n**Type:** `{ext.upper().lstrip('.')}` | {content_type}\n**Size:** {file_size}\n\n*Executable files can contain malware.*", color=discord.Color.red())
                    await message.channel.send(embed=embed)
                    if config.get("file_auto_delete", False):
                        try:
                            await message.delete()
                            await stats.increment("messages_deleted")
                        except (discord.Forbidden, discord.NotFound, discord.HTTPException):
                            pass
                else:
                    await message.channel.send(f"*File info: {content_type} | {file_size}*")
                await stats.increment("files_inspected")
            except Exception as e:
                print(f"Failed to fetch file info for {file_url}: {e}")


def check_suspicious_tld(hostname: str) -> bool:
    for tld in SUSPICIOUS_TLDS:
        if hostname.endswith(tld):
            return True
    return False


async def warn_suspicious_tld(message: discord.Message, config: dict = None) -> None:
    if config is None:
        config = {}
    if not config.get("suspicious_tld_warn", True):
        return
    warned_domains = set()
    for raw_url in re.findall(r'https?://[^\s\)\]>]+', message.content):
        hostname = urlparse(raw_url).hostname
        if not hostname:
            continue
        hostname_clean = hostname.lower().removeprefix("www.")
        if hostname_clean in warned_domains:
            continue
        if check_suspicious_tld(hostname_clean):
            warned_domains.add(hostname_clean)
            embed = discord.Embed(title="Suspicious Domain Detected", description=f"The domain `{hostname_clean}` uses a TLD frequently associated with phishing/malware.\n\n`{raw_url}`\n\n*Exercise caution.*", color=discord.Color.orange())
            await message.channel.send(embed=embed)
            await stats.increment("safety_cards_shown")


async def warn_http_downgrade(message: discord.Message, config: dict = None) -> None:
    if config is None:
        config = {}
    if not config.get("http_downgrade_warn", True):
        return
    warned_domains = set()
    for raw_url in re.findall(r'https?://[^\s\)\]>]+', message.content):
        if not raw_url.startswith('http://'):
            continue
        hostname = urlparse(raw_url).hostname
        if not hostname:
            continue
        hostname_clean = hostname.lower().removeprefix("www.")
        if hostname_clean in warned_domains:
            continue
        https_expected = hostname_clean.endswith(('.com', '.org', '.net', '.io', '.dev', '.app'))
        if hostname_clean in ('localhost', '127.0.0.1') or hostname_clean.startswith('192.168.'):
            https_expected = False
        if https_expected:
            warned_domains.add(hostname_clean)
            https_url = raw_url.replace('http://', 'https://', 1)
            embed = discord.Embed(title="Insecure Connection Warning", description=f"`{raw_url}` is using an **unencrypted HTTP** connection.\n\nTry HTTPS instead: `{https_url}`", color=discord.Color.yellow())
            await message.channel.send(embed=embed)
            await stats.increment("safety_cards_shown")


async def warn_new_domain(message: discord.Message, config: dict = None) -> bool:
    """
    Warn when a domain was registered less than 30 days ago.
    Returns True if a block occurred (caller should halt pipeline).
    """
    if config is None:
        config = {}
    if not config.get("domain_age_warn", True) and not config.get("domain_age_block", False):
        return False
    warned_domains = set()
    blocked = False
    for raw_url in re.findall(r'https?://[^\s\)\]>]+', message.content):
        hostname = urlparse(raw_url).hostname
        if not hostname:
            continue
        hostname_clean = hostname.lower().removeprefix("www.")
        if hostname_clean in warned_domains:
            continue
        warned_domains.add(hostname_clean)
        try:
            result = await rdap.query_domain(hostname_clean)
            if not result or not result.get("registered_date"):
                continue
            age_days = rdap.get_domain_age_days(result["registered_date"])
            if age_days is None or age_days > 30:
                continue
            await stats.increment("domain_age_checks")
            if config.get("domain_age_block", False):
                try:
                    await message.delete()
                    await stats.increment("messages_deleted")
                    await stats.increment("new_domains_blocked")
                except (discord.Forbidden, discord.NotFound, discord.HTTPException):
                    pass
                embed = discord.Embed(title="New Domain Blocked", description=f"**{message.author.mention}, your link was removed.**\n\nThe domain `{hostname_clean}` was registered only **{age_days} day(s)** ago.\nRegistered: {result['registered_date'][:10]}\nRegistrar: {result.get('registrar', 'Unknown')}", color=discord.Color.red())
                await message.channel.send(embed=embed, delete_after=15)
                blocked = True
            else:
                embed = discord.Embed(title="New Domain Warning", description=f"The domain `{hostname_clean}` was registered only **{age_days} day(s)** ago.\n\n`{raw_url}`\n\n*New domains are frequently used for phishing.*\nRegistered: {result['registered_date'][:10]}", color=discord.Color.orange())
                await message.channel.send(embed=embed)
                await stats.increment("safety_cards_shown")
        except Exception:
            pass
    return blocked
