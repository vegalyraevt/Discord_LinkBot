"""
enrichment.archive.py - Wayback Machine (Archive.org) auto-snapshot.

Submits URLs to web.archive.org/save to create permanent snapshots.
Uses the public Wayback Machine APIs - free, no API key required.

Features:
  - Auto-snapshot: Toggleable per-server, per-channel, per-link-type
  - Manual: /archive <url> command (handled by slash command layer)
  - Link type filtering: news, social_media, blog, academic, all
  - Config: archive.enabled, archive.channels, archive.link_types
"""

import re
import aiohttp
from urllib.parse import urlparse, quote

import discord
import stats


# Wayback Machine save endpoint
ARCHIVE_SAVE_URL = "https://web.archive.org/save/"

# Link type classification patterns
SOCIAL_MEDIA_DOMAINS = {
    'twitter.com', 'x.com', 'tiktok.com', 'instagram.com',
    'reddit.com', 'bsky.app', 'threads.net', 'threads.com',
    'facebook.com', 'linkedin.com',
}
NEWS_DOMAINS = {
    'nytimes.com', 'wsj.com', 'washingtonpost.com', 'theguardian.com',
    'bbc.com', 'bbc.co.uk', 'cnn.com', 'reuters.com', 'apnews.com',
    'bloomberg.com', 'politico.com', 'npr.org', 'foxnews.com',
    'msnbc.com', 'abcnews.go.com', 'cbsnews.com', 'usatoday.com',
    'time.com', 'economist.com', 'newyorker.com', 'vox.com',
    'axios.com', 'theatlantic.com', 'wired.com', 'arstechnica.com',
    'theverge.com', 'techcrunch.com', 'engadget.com', 'gizmodo.com',
}
BLOG_DOMAINS = {
    'medium.com', 'dev.to', 'hashnode.dev', 'substack.com',
    'blogspot.com', 'wordpress.com', 'ghost.io',
}
ACADEMIC_DOMAINS = {
    'doi.org', 'arxiv.org', 'nature.com', 'science.org',
    'sciencedirect.com', 'springer.com', 'ieee.org', 'acm.org',
    'jstor.org', 'pubmed.ncbi.nlm.nih.gov', 'researchgate.net',
    'scholar.google.com',
}


def classify_link_type(url: str) -> str:
    """Classify a URL into a link type category."""
    hostname = urlparse(url).hostname or ""
    hostname = hostname.lower().removeprefix("www.")

    for domain in SOCIAL_MEDIA_DOMAINS:
        if hostname == domain or hostname.endswith("." + domain):
            return "social_media"
    for domain in NEWS_DOMAINS:
        if hostname == domain or hostname.endswith("." + domain):
            return "news"
    for domain in ACADEMIC_DOMAINS:
        if hostname == domain or hostname.endswith("." + domain):
            return "academic"
    for domain in BLOG_DOMAINS:
        if hostname == domain or hostname.endswith("." + domain):
            return "blog"

    return "other"


def should_archive(url: str, config: dict, channel_id: int) -> bool:
    """
    Determine if a URL should be auto-archived based on server config.
    """
    archive_config = config.get("archive", {})
    if not archive_config.get("enabled", False):
        return False

    # Check channel filter
    channels = archive_config.get("channels", [])
    if channels and channel_id not in channels:
        return False

    # Check link type filter
    link_types = archive_config.get("link_types", ["all"])
    if "all" in link_types:
        return True

    link_type = classify_link_type(url)
    return link_type in link_types


async def submit_to_archive(url: str) -> str | None:
    """
    Submit a URL to the Wayback Machine for archiving.
    Returns the permanent archived URL or None on failure.
    """
    try:
        save_url = f"{ARCHIVE_SAVE_URL}{quote(url, safe='')}"
        async with aiohttp.ClientSession() as session:
            async with session.get(
                save_url,
                timeout=aiohttp.ClientTimeout(total=10),
                headers={"User-Agent": "LinkBot/2.0 (Discord Link Manager)"}
            ) as resp:
                if resp.status in (200, 302):
                    # The response headers may include the archived URL
                    # or we can construct it from the wayback machine format
                    return f"https://web.archive.org/web/*/{url}"
    except Exception as e:
        print(f"❌ Archive.org submit failed for {url}: {e}")
    return None


async def auto_archive_links(message: discord.Message, config: dict = None) -> None:
    """
    Auto-archive links in a message if the server config allows.
    Silently skips if archiving is not enabled for this channel/type.
    """
    if config is None:
        config = {}

    if not message.guild:
        return

    channel_id = message.channel.id

    for raw_url in re.findall(r'https?://[^\s\)\]>]+', message.content):
        if not should_archive(raw_url, config, channel_id):
            continue

        archived_url = await submit_to_archive(raw_url)
        if archived_url:
            await stats.increment("archive_snapshots")


async def archive_command_response(message: discord.Message, url: str) -> None:
    """
    Handle a manual archive request (called from slash command or context).
    Returns an ephemeral-ish response with the archived URL.
    """
    archived_url = await submit_to_archive(url)
    if archived_url:
        embed = discord.Embed(
            title="📸 Archived to Wayback Machine",
            description=(
                f"The page has been submitted to the Internet Archive.\n\n"
                f"🔗 **Original:** {url}\n"
                f"📚 **Archive:** {archived_url}\n\n"
                f"*It may take a few minutes for the snapshot to become available.*"
            ),
            color=discord.Color.dark_green()
        )
        embed.set_footer(text="Powered by archive.org • LinkBot")
        await message.channel.send(embed=embed, delete_after=30)
        await stats.increment("archive_snapshots")
    else:
        await message.channel.send(
            "⚠️ Failed to archive this URL. The site may block archiving or be temporarily unavailable.",
            delete_after=15
        )
