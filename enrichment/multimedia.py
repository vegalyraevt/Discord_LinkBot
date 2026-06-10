"""
enrichment.multimedia.py - YouTube and Twitch link enrichment.

Uses free oEmbed APIs - no API keys required.

YouTube: Only handles Shorts conversion. Regular watch URLs are left alone
         to let Discord's native video embed work.
Twitch: Shows streamer name, game/title, thumbnail for clips and channels
"""

import re
import aiohttp
from urllib.parse import urlparse, parse_qs

import discord
import stats


# --- YouTube ---

YOUTUBE_WATCH_REGEX = re.compile(
    r'https?://(?:www\.)?youtube\.com/watch\?v=([A-Za-z0-9_-]{11})'
)
YOUTUBE_SHORTS_REGEX = re.compile(
    r'https?://(?:www\.)?youtube\.com/shorts/([^/?\s]+)'
)
YOUTUBE_YOUTU_BE_REGEX = re.compile(
    r'https?://youtu\.be/([A-Za-z0-9_-]{11})'
)

YOUTUBE_OEMBED = "https://www.youtube.com/oembed"
YOUTUBE_NOEMBED_BASE = "https://noembed.com/embed"


async def handle_youtube(message: discord.Message, config: dict = None) -> bool:
    """
    YouTube links are handled by embeds.handle_link_fixer():
    - Regular watch URLs: Discord native embed (no bot action needed)
    - Shorts: converted to watch URLs and reposted via webhook (impersonating user)
    - youtu.be: Discord native embed (no bot action needed)
    This handler does nothing and always returns False.
    """
    return False


# --- Twitch ---

TWITCH_CLIP_REGEX = re.compile(
    r'https?://(?:www\.)?(?:clips\.twitch\.tv|twitch\.tv/[^/]+/clip)/([A-Za-z0-9_-]+)'
)
TWITCH_CHANNEL_REGEX = re.compile(
    r'https?://(?:www\.)?twitch\.tv/([A-Za-z0-9_]{4,25})(?:/.*)?'
)

TWITCH_OEMBED = "https://embed.twitch.tv/oembed"


async def handle_twitch(message: discord.Message, config: dict = None) -> bool:
    """Handle Twitch clip and channel links with rich info embed."""
    if config is None:
        config = {}
    if not config.get("enrichment", {}).get("twitch", True):
        return False

    twitch_url = None
    
    # Check for clips first (more specific)
    clip_match = TWITCH_CLIP_REGEX.search(message.content)
    if clip_match:
        twitch_url = clip_match.group(0)
    else:
        # Check for channels
        chan_match = TWITCH_CHANNEL_REGEX.search(message.content)
        if chan_match:
            twitch_url = f"https://www.twitch.tv/{chan_match.group(1)}"

    if not twitch_url:
        return False

    try:
        async with aiohttp.ClientSession() as session:
            oembed_url = f"{TWITCH_OEMBED}?url={twitch_url}&format=json"
            async with session.get(oembed_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    title = data.get("title", "Unknown Broadcast")
                    author_name = data.get("author_name", "Unknown")
                    thumbnail_url = data.get("thumbnail_url", "")

                    # Try to extract game name from title (Twitch oEmbed puts "[Game] Streamer - Title")
                    description_parts = [f"Streamer: {author_name}"]
                    if " - " in title:
                        parts = title.split(" - ", 1)
                        if parts[0].startswith("["):
                            game = parts[0].strip("[]")
                            description_parts.append(f"Game: {game}")
                            description_parts.append(parts[1])
                        else:
                            description_parts.append(title)

                    embed = discord.Embed(
                        title=title[:256],
                        url=twitch_url,
                        color=discord.Color.purple(),
                        description="\n".join(description_parts)[:1024]
                    )
                    if thumbnail_url:
                        embed.set_image(url=thumbnail_url)
                    embed.set_footer(text="Twitch - LinkBot")
                    await message.reply(embed=embed, mention_author=False)
                    await stats.increment("twitch_enrichments")
                    return True
    except Exception as e:
        print(f"Twitch enrichment error: {e}")
    return True
