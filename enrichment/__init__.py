"""
enrichment/__init__.py - Link enrichment router.

Dispatches URL types to specialized sub-modules:
  - multimedia.py : YouTube, Twitch
  - github.py     : GitHub blob/repo/user/gist
  - storefronts.py: Steam, Amazon, IMDb
  - academic.py   : DOI, arXiv, npm, PyPI, Stack Overflow, GitHub Gist
  - social.py     : Hacker News, Dev.to, Bluesky
  - archive.py    : Wayback Machine snapshots
"""

import re
import aiohttp
from urllib.parse import quote

import discord
import stats

from enrichment import multimedia
from enrichment import github
from enrichment import storefronts
from enrichment import archive
from enrichment import academic
from enrichment import social


# --- Music (Odesli/song.link) ---

MUSIC_DOMAINS = {'open.spotify.com', 'music.apple.com', 'soundcloud.com'}
MUSIC_URL_REGEX = re.compile(
    r'https?://(?:www\.)?(open\.spotify\.com|music\.apple\.com|soundcloud\.com)/[^\s\)\]>]+'
)

# --- Wikipedia ---

WIKI_URL_REGEX = re.compile(r'https?://en\.wikipedia\.org/wiki/([^\s\)\]>#?]+)')

# --- Discord Message ---

DISCORD_MSG_REGEX = re.compile(
    r'https?://(?:ptb\.|canary\.)?discord\.com/channels/(\d+)/(\d+)/(\d+)'
)


# ===== Universal Music Linker =====

async def handle_music_links(message: discord.Message) -> bool:
    """Handle music links via Odesli API. Returns True if handled."""
    match = MUSIC_URL_REGEX.search(message.content)
    if not match:
        return False

    music_url = match.group(0)
    clean_music_url = music_url.split('?')[0]
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.song.link/v1-alpha.1/links?url={quote(clean_music_url, safe='')}",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    page_url = data.get('pageUrl')
                    if page_url:
                        await message.reply(
                            f"🎧 Listen on other platforms: {page_url}",
                            mention_author=False
                        )
                        await stats.increment("music_links")
    except Exception as e:
        print(f"❌ Failed to fetch Odesli link: {e}")
    return True


# ===== Wikipedia Summary =====

async def handle_wikipedia(message: discord.Message) -> bool:
    """Handle Wikipedia article URLs with TL;DR summary. Returns True if handled."""
    match = WIKI_URL_REGEX.search(message.content)
    if not match:
        return False

    title = match.group(1)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}",
                headers={'User-Agent': 'DiscordBot (https://github.com/vegalyraevt/Discord_LinkBot)'},
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    page_title = data.get('title', title.replace('_', ' '))
                    description = data.get('description', '')
                    extract = data.get('extract', '')
                    article_url = data.get('content_urls', {}).get('desktop', {}).get(
                        'page', f"https://en.wikipedia.org/wiki/{title}"
                    )
                    thumbnail_source = data.get('thumbnail', {}).get('source')

                    if extract:
                        desc_parts = []
                        if description:
                            desc_parts.append(f"*{description}*")
                        desc_parts.append(extract)
                        full_description = '\n\n'.join(desc_parts)
                        if len(full_description) > 4096:
                            full_description = full_description[:4090] + '...'

                        embed = discord.Embed(
                            title=page_title,
                            description=full_description,
                            color=discord.Color.light_gray(),
                            url=article_url
                        )
                        if thumbnail_source:
                            embed.set_thumbnail(url=thumbnail_source)
                        embed.set_footer(text="Wikipedia")
                        await message.reply(embed=embed, mention_author=False)
                        try:
                            await message.edit(suppress=True)
                        except (discord.Forbidden, discord.HTTPException):
                            pass
                        await stats.increment("wikipedia_summaries")
    except Exception as e:
        print(f"❌ Failed to fetch Wikipedia summary: {e}")
    return True


# ===== Discord Message Quote =====

async def handle_discord_message(message: discord.Message, client: discord.Client) -> bool:
    """Handle Discord message links by quoting the target message. Returns True if handled."""
    match = DISCORD_MSG_REGEX.search(message.content)
    if not match:
        return False

    guild_id = match.group(1)
    channel_id = match.group(2)
    message_id = match.group(3)
    original_url = match.group(0)
    try:
        guild = client.get_guild(int(guild_id))
        channel = guild.get_channel(int(channel_id)) if guild else None
        target_message = await channel.fetch_message(int(message_id))
        embed = discord.Embed(
            description=target_message.content or '*No text content*',
            color=discord.Color.dark_theme()
        )
        embed.set_author(
            name=target_message.author.display_name,
            icon_url=target_message.author.display_avatar.url
        )
        embed.add_field(
            name='\u200b',
            value=f"[Jump to original message]({original_url})",
            inline=False
        )
        if target_message.attachments:
            embed.set_image(url=target_message.attachments[0].url)
        await message.reply(embed=embed, mention_author=False)
        await stats.increment("discord_quotes")
    except (discord.NotFound, discord.Forbidden, AttributeError):
        pass
    return True


# ===== Run All Enrichment Handlers =====

async def run_all_enrichment(message: discord.Message, client: discord.Client, config: dict = None) -> None:
    """Run all enrichment handlers in priority order."""
    if config is None:
        config = {}

    # Fast oEmbed lookups first
    await multimedia.handle_youtube(message, config)
    await multimedia.handle_twitch(message, config)

    # Academic + developer enrichment
    await academic.handle_doi(message, config)
    await academic.handle_arxiv(message, config)
    await academic.handle_npm(message, config)
    await academic.handle_pypi(message, config)
    await academic.handle_stackoverflow(message, config)
    await academic.handle_github_gist(message, config)

    # Social enrichment
    await social.handle_hackernews(message, config)
    await social.handle_devto(message, config)
    await social.handle_bluesky(message, config)

    # Core enrichment
    await github.handle_github_blob(message)
    await handle_music_links(message)
    await storefronts.handle_steam_game(message)
    await storefronts.handle_steam_dev(message)
    await handle_wikipedia(message)
    await github.handle_github_repo(message)
    await github.handle_github_user(message)
    await storefronts.handle_amazon(message)
    await storefronts.handle_imdb(message)

    # Discord message quote needs client reference
    await handle_discord_message(message, client)

    # Archive.org auto-snapshot (runs last - doesn't reply visibly)
    await archive.auto_archive_links(message, config)
