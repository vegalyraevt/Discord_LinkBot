"""
enrichment.social.py - Social media and community enrichment.

Handles:
  - Hacker News via Algolia API (free, no API key)
  - Dev.to articles via Dev.to API (free, no API key)
  - Bluesky posts via bsky.social API (free, no API key)
"""

import re
import aiohttp

import discord
import stats


# --- Hacker News ---

HN_ITEM_REGEX = re.compile(r'https?://news\.ycombinator\.com/item\?id=(\d+)')


async def handle_hackernews(message: discord.Message, config: dict = None) -> bool:
    """Handle Hacker News links with item preview. Returns True if matched."""
    if config is None:
        config = {}
    if not config.get("enrichment", {}).get("hacker_news", True):
        return False

    match = HN_ITEM_REGEX.search(message.content)
    if not match:
        return False

    item_id = match.group(1)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://hn.algolia.com/api/v1/items/{item_id}",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    title = data.get("title", "Unknown")
                    points = data.get("points", 0)
                    author = data.get("author", "Unknown")
                    comment_count = len(data.get("children", []))

                    embed = discord.Embed(
                        title=title[:256],
                        url=f"https://news.ycombinator.com/item?id={item_id}",
                        color=discord.Color.orange(),
                    )
                    embed.add_field(name="👍 Points", value=str(points), inline=True)
                    embed.add_field(name="💬 Comments", value=str(comment_count), inline=True)
                    embed.add_field(name="👤 Author", value=author, inline=True)
                    embed.set_footer(text="Hacker News")
                    await message.reply(embed=embed, mention_author=False)
                    await stats.increment("hacker_news_enrichments")
    except Exception as e:
        print(f"❌ Hacker News enrichment error: {e}")
    return True


# --- Dev.to ---

DEVTO_REGEX = re.compile(r'https?://dev\.to/([^/]+)/([^/\s\)\]>]+)')


async def handle_devto(message: discord.Message, config: dict = None) -> bool:
    """Handle Dev.to article links with preview. Returns True if matched."""
    if config is None:
        config = {}
    if not config.get("enrichment", {}).get("dev_to", True):
        return False

    match = DEVTO_REGEX.search(message.content)
    if not match:
        return False

    username = match.group(1)
    slug = match.group(2)
    article_url = f"https://dev.to/{username}/{slug}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://dev.to/api/articles/{username}/{slug}",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    title = data.get("title", "Unknown")
                    description = (data.get("description") or "No description.")[:500]
                    tags = ", ".join(data.get("tags", [])[:5])
                    reading_time = data.get("reading_time_minutes", "?")
                    reactions = data.get("public_reactions_count", 0)
                    comments = data.get("comments_count", 0)

                    embed = discord.Embed(
                        title=title[:256],
                        url=article_url,
                        description=description,
                        color=discord.Color.dark_blue(),
                    )
                    embed.add_field(name="⏱️ Reading Time", value=f"{reading_time} min", inline=True)
                    embed.add_field(name="❤️ Reactions", value=str(reactions), inline=True)
                    embed.add_field(name="💬 Comments", value=str(comments), inline=True)
                    if tags:
                        embed.add_field(name="🏷️ Tags", value=tags, inline=False)
                    embed.set_footer(text="Dev.to")
                    await message.reply(embed=embed, mention_author=False)
                    await stats.increment("dev_to_enrichments")
    except Exception as e:
        print(f"❌ Dev.to enrichment error: {e}")
    return True


# --- Bluesky ---

BLUESKY_POST_REGEX = re.compile(r'https?://bsky\.app/profile/([^/]+)/post/([^/\s\)\]>]+)')


async def handle_bluesky(message: discord.Message, config: dict = None) -> bool:
    """Handle Bluesky post links with content preview. Returns True if matched."""
    if config is None:
        config = {}

    match = BLUESKY_POST_REGEX.search(message.content)
    if not match:
        return False

    # Bluesky public API - no auth needed for read
    did = match.group(1)
    post_id = match.group(2)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://public.api.bsky.app/xrpc/app.bsky.feed.getPostThread"
                f"?uri=at://{did}/app.bsky.feed.post/{post_id}",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    thread = data.get("thread", {})
                    post = thread.get("post", {})
                    record = post.get("record", {})
                    author_info = post.get("author", {})

                    text = record.get("text", "*No text content*")
                    author_name = author_info.get("displayName") or author_info.get("handle", "Unknown")
                    created = record.get("createdAt", "")

                    embed = discord.Embed(
                        description=text[:1024],
                        color=discord.Color.blue(),
                        url=f"https://bsky.app/profile/{did}/post/{post_id}",
                    )
                    embed.set_author(name=f"🦋 {author_name}")
                    if created:
                        embed.set_footer(text=f"Posted: {created[:10]}")
                    await message.reply(embed=embed, mention_author=False)
                    await stats.increment("bluesky_enrichments")
    except Exception as e:
        print(f"❌ Bluesky enrichment error: {e}")
    return True
