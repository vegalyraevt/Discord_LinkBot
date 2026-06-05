"""
embeds.py - Embed fixing and link transformation.

Handles:
  - Domain mapping for embed-friendly alternatives (Twitter→fixupx, TikTok→tnktok, etc.)
  - YouTube Shorts → regular video conversion
  - Translation suffix detection (.translate.spanish)
  - Tracking parameter stripping
  - Webhook repost impersonating original author
  - NSFW domain detection (Phase 12)
"""

import re
import aiohttp
from urllib.parse import urlparse, parse_qsl, urlencode

import discord

import stats
import easter_eggs


# Dictionary mapping standard domains to their embed-fixing alternatives
DOMAIN_MAP = {
    'twitter.com': 'fixupx.com',
    'x.com': 'fixupx.com',
    'tiktok.com': 'tnktok.com',
    'instagram.com': 'uuinstagram.com',
    'reddit.com': 'rxddit.com',
    'pixiv.net': 'phixiv.net',
    'bsky.app': 'bskyx.app',
    'threads.net': 'vxthreads.net',
    'threads.com': 'vxthreads.net',
}

# Language name to ISO 639-1 two-letter code mapping
LANGUAGE_MAP = {
    'spanish': 'es', 'french': 'fr', 'portuguese': 'pt', 'italian': 'it',
    'romanian': 'ro', 'catalan': 'ca',
    'german': 'de', 'dutch': 'nl', 'swedish': 'sv', 'danish': 'da',
    'norwegian': 'no', 'finnish': 'fi',
    'russian': 'ru', 'polish': 'pl', 'ukrainian': 'uk', 'czech': 'cs',
    'slovak': 'sk', 'bulgarian': 'bg', 'serbian': 'sr', 'croatian': 'hr',
    'japanese': 'ja', 'chinese': 'zh', 'korean': 'ko',
    'hindi': 'hi', 'bengali': 'bn', 'thai': 'th', 'vietnamese': 'vi',
    'indonesian': 'id', 'malay': 'ms',
    'arabic': 'ar', 'hebrew': 'he', 'turkish': 'tr', 'persian': 'fa',
    'swahili': 'sw',
    'english': 'en', 'greek': 'el', 'hungarian': 'hu',
}

# YouTube Shorts
YOUTUBE_SHORTS_REGEX = re.compile(
    r'https?://(?:www\.)?youtube\.com/shorts/([^/?\s]+)'
)

# Translate suffix regex
TRANSLATE_SUFFIX_REGEX = re.compile(r'\.translate(?:\.([a-zA-Z]+))?$', re.IGNORECASE)

# Tracking domains and params
TRACKING_DOMAINS = {
    'facebook.com', 'youtube.com', 'youtu.be', 'aliexpress.com', 'ebay.com',
    'amazon.com', 'amazon.co.uk', 'amazon.de', 'amazon.fr', 'amazon.ca',
    'twitter.com', 'x.com', 'instagram.com', 'tiktok.com', 'reddit.com',
}
TRACKING_PARAMS = {
    'si', 'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
    'utm_id', 'utm_name', 'fbclid', 'igshid', 'ref', 'referrer', 'feature',
    'pp', 'ab_channel', 'tag', 'source',
}

TRACKING_URL_REGEX = re.compile(
    r'https?://(?:www\.)?(?:' +
    '|'.join(re.escape(d) for d in TRACKING_DOMAINS) +
    r')/[^\s\)\]>]+'
)

# Domain pattern for embed fixing
DOMAINS_PATTERN = '|'.join(re.escape(domain) for domain in DOMAIN_MAP.keys())
URL_REGEX = re.compile(rf'https?://(?:www\.)?({DOMAINS_PATTERN})(/[^\s]*)')


async def strip_tracking(message: discord.Message) -> None:
    """Strip tracking parameters from known tracking-heavy domains."""
    tracking_match = TRACKING_URL_REGEX.search(message.content)
    if not tracking_match:
        return

    raw_tracking_url = tracking_match.group(0)
    tracking_hostname = urlparse(raw_tracking_url).hostname or ''
    tracking_base = tracking_hostname.removeprefix('www.')

    # Don't touch embed-fixed domains (they're handled by the link fixer)
    if tracking_base in DOMAIN_MAP:
        return

    # Shorts are handled by the link fixer
    if YOUTUBE_SHORTS_REGEX.search(message.content):
        return

    parsed = urlparse(raw_tracking_url)
    kept = [(k, v) for k, v in parse_qsl(parsed.query) if k.lower() not in TRACKING_PARAMS]
    stripped_query = urlencode(kept)
    clean_parsed = parsed._replace(query=stripped_query, fragment='')
    clean_url = clean_parsed.geturl()

    if clean_url.rstrip('/') != raw_tracking_url.rstrip('/'):
        await message.reply(f"🧹 Clean link without tracking: {clean_url}", mention_author=False)
        await stats.increment("tracking_stripped")
        try:
            await message.edit(suppress=True)
        except (discord.Forbidden, discord.HTTPException):
            pass


async def handle_link_fixer(message: discord.Message) -> None:
    """
    Fix links: replace domains with embed-friendly alternatives,
    convert YouTube Shorts, handle translation suffixes,
    and repost via webhook impersonating the original author.
    """
    try:
        matches = list(URL_REGEX.finditer(message.content))
        shorts_match = YOUTUBE_SHORTS_REGEX.search(message.content)

        if not matches and not shorts_match:
            return

        fixed_content = message.content

        # YouTube Shorts converter
        if shorts_match:
            fixed_content = YOUTUBE_SHORTS_REGEX.sub(
                lambda m: f"https://www.youtube.com/watch?v={m.group(1)}",
                fixed_content
            )

        pending_translations = []

        for match in matches:
            matched_domain = match.group(1)
            fixed_domain = DOMAIN_MAP[matched_domain]
            original_url = match.group(0)
            path = match.group(2)

            # Translation tag detection
            translate_lang = None
            translate_suffix_match = TRANSLATE_SUFFIX_REGEX.search(path)
            if translate_suffix_match:
                lang_word = (translate_suffix_match.group(1) or 'en').lower()
                if len(lang_word) == 2:
                    translate_lang = lang_word
                else:
                    translate_lang = LANGUAGE_MAP.get(lang_word, 'en')
                path = path[:translate_suffix_match.start()]

            fixed_url = f"https://{fixed_domain}{path}"

            if translate_lang:
                if fixed_domain == 'fixupx.com':
                    fixed_url = f"{fixed_url}/{translate_lang}"
                    pending_translations.append((path, translate_lang))
                elif fixed_domain == 'phixiv.net':
                    fixed_url = f"https://{fixed_domain}/{translate_lang}{path}"

            fixed_content = fixed_content.replace(original_url, fixed_url)

        # Rare item drop
        rare_drop = easter_eggs.maybe_rare_drop()
        if rare_drop:
            fixed_content += rare_drop
            await stats.increment("rare_drops")

        webhooks = await message.channel.webhooks()
        webhook = discord.utils.get(webhooks, name="LinkFixerWebhook")
        if not webhook:
            webhook = await message.channel.create_webhook(name="LinkFixerWebhook")

        await webhook.send(
            content=fixed_content,
            username=message.author.display_name,
            avatar_url=message.author.display_avatar.url
        )
        await stats.increment("links_fixed")

        # Translation fetch for fixupx
        if pending_translations:
            async with aiohttp.ClientSession() as session:
                for tweet_path, lang in pending_translations:
                    api_url = f"https://api.fxtwitter.com{tweet_path}/{lang}"
                    try:
                        async with session.get(api_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                            if resp.status == 200:
                                data = await resp.json(content_type=None)
                                tweet = data.get('tweet', {})
                                translation = tweet.get('translation', {})
                                translated_text = translation.get('text', '')
                                src_lang = translation.get('source_lang_en', translation.get('source_lang', '?'))
                                if translated_text:
                                    await message.channel.send(
                                        f"🌐 **Translation** ({src_lang} → {lang.upper()}):\n{translated_text}"
                                    )
                                else:
                                    await message.channel.send(
                                        "🌐 *(No translation available for this tweet)*"
                                    )
                    except Exception as e:
                        print(f"❌ Translation fetch error: {e}")

        await message.delete()
        await stats.increment("messages_deleted")
    except discord.Forbidden:
        print(f"❌ Missing permissions in {message.channel}.")
    except Exception as e:
        print(f"❌ Error processing message: {e}")


# ===== NSFW Domain Detection (Phase 12) =====

NSFW_DOMAINS = {
    'pornhub.com', 'xvideos.com', 'xnxx.com', 'redtube.com',
    'youporn.com', 'onlyfans.com', 'fansly.com',
    'chaturbate.com', 'stripchat.com', 'bongacams.com',
    'e621.net', 'rule34.xxx', 'rule34.paheal.net',
    'gelbooru.com', 'danbooru.donmai.us', 'sankakucomplex.com',
}

NSFW_DOMAIN_REGEX = re.compile(
    r'https?://(?:www\.)?(?:' +
    '|'.join(re.escape(d) for d in NSFW_DOMAINS) +
    r')/[^\s\)\]>]*'
)


async def warn_nsfw(message: discord.Message, config: dict = None) -> None:
    """
    Warn about links to known adult/NSFW content domains.
    Only fires if nsfw_warning is enabled in config.
    Skips channels listed in nsfw_exempt_channels.
    """
    if config is None:
        config = {}

    if not config.get("nsfw_warning", False):
        return

    # Check if this channel is exempt
    exempt_channels = config.get("nsfw_exempt_channels", [])
    if message.channel.id in exempt_channels:
        return

    match = NSFW_DOMAIN_REGEX.search(message.content)
    if match:
        embed = discord.Embed(
            title="🔞 NSFW Content Warning",
            description=(
                f"{message.author.mention}, this link leads to a site known "
                f"for adult/NSFW content.\n\n"
                f"🔗 `{match.group(0)}`\n\n"
                f"*This warning can be configured by server admins using `/config toggle nsfw_warning`.*"
            ),
            color=discord.Color.dark_purple(),
        )
        await message.channel.send(embed=embed)
        await stats.increment("nsfw_warnings")
