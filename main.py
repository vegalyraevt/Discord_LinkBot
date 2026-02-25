import discord
import re
import os
import random
import asyncio
import aiohttp
import json as _json
from datetime import datetime
from urllib.parse import urlparse, quote, unquote, parse_qsl, urlencode
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# Load environment variables from .env file
load_dotenv()

OMDB_API_KEY = os.getenv('OMDB_API_KEY', '')

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

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

# Backup proxy domains if primary ones fail (for future use)
BACKUP_DOMAINS = {
    'instagram.com': ['gginstagram.com', 'd.vxinstagram.com']
}

# Language name → ISO 639-1 two-letter code mapping for .translate tag
LANGUAGE_MAP = {
    # Romance
    'spanish': 'es', 'french': 'fr', 'portuguese': 'pt', 'italian': 'it',
    'romanian': 'ro', 'catalan': 'ca',
    # Germanic
    'german': 'de', 'dutch': 'nl', 'swedish': 'sv', 'danish': 'da',
    'norwegian': 'no', 'finnish': 'fi',
    # Slavic
    'russian': 'ru', 'polish': 'pl', 'ukrainian': 'uk', 'czech': 'cs',
    'slovak': 'sk', 'bulgarian': 'bg', 'serbian': 'sr', 'croatian': 'hr',
    # East Asian
    'japanese': 'ja', 'chinese': 'zh', 'korean': 'ko',
    # South / Southeast Asian
    'hindi': 'hi', 'bengali': 'bn', 'thai': 'th', 'vietnamese': 'vi',
    'indonesian': 'id', 'malay': 'ms',
    # Middle Eastern / African
    'arabic': 'ar', 'hebrew': 'he', 'turkish': 'tr', 'persian': 'fa',
    'swahili': 'sw',
    # Other
    'english': 'en', 'greek': 'el', 'hungarian': 'hu',
    # Allow bare ISO codes to pass through as-is (2-letter)
}

# Regex to detect and strip .translate or .translate.LANG suffix on a URL path
TRANSLATE_SUFFIX_REGEX = re.compile(r'\.translate(?:\.([a-zA-Z]+))?$', re.IGNORECASE)

# Zelda Easter Egg Data
ZELDA_TEXT_RESPONSES = [
    # --- The Classics & Game Memes ---
    "HYYAAAAAA! <a:link_spin:1475252964708057118>",
    "Hey! Listen! 🧚",
    "It's dangerous to go alone! Take this. ⚔️",
    "It's a secret to everybody.",
    "Dodongo dislikes smoke.",
    "I AM ERROR.",
    "You've met a terrible fate, haven't you?",
    "A puppet without a role is merely garbage.",
    "The flow of time is always cruel...",
    "Grumble, grumble...",
    "You got a green rupee! Don't spend it all in one place!",
    "The wind... it is blowing...",
    "Watch out!",
    
    # --- The 1989 Animated Series ---
    "Well, excuuuuuuuse me, Princess! <a:link_spin:1475252964708057118>",
    "Oh boy! I'm so hungry, I could eat an octorok! <a:link_spin:1475252964708057118>",
    "I'm a hero, not a handyman! <a:link_spin:1475252964708057118>",
    "I'll take a raincheck on that kiss, princess. Duty calls! <a:link_spin:1475252964708057118>",
    "Looking good, princess, especially from this angle! <a:link_spin:1475252964708057118>",

    # --- The CD-i Masterpieces ---
    "Mah boi, this peace is what all true warriors strive for!",
    "Lamp oil, rope, bombs? You want it? It's yours, my friend, as long as you have enough rubies.",
    "Sorry Link, I can't give credit! Come back when you're a little, mmmm... richer!",
    "Gee, it sure is boring around here.",
    "I just wonder what Ganon's up to.",
    "Squadala! We're off!",
    "I guess that's worth a kiss, huh? <a:link_spin:1475252964708057118>",
    "Great! I'll grab my stuff!",
    "I can't wait to bomb some Dodongos! <a:link_spin:1475252964708057118>",
    "You dare bring light to my lair?! You must die!"
]

# Expanded list for Pots/Crime/Destruction - word boundaries only
POT_KEYWORDS = r'\b(pot|pots|smash|break|vase|vases|jar|jars|urn|urns|ceramics|pottery|rupee|rupees|money|burglary|theft|vandalism|vandalize|steal|stealing|thief|rob|robbery|loot|looting|crime|shatter|trespass|trespassing|crash|destroy|destruction|ransack|pillage)\b'

# Expanded list for Cuccos/Chickens/Swarm - word boundaries only
CUCCO_KEYWORDS = r'\b(cucco|cuccos|cuckoo|cuckoos|chicken|chickens|poultry|peck|pecking|flock|kakariko|rooster|cluck|feathers|swarm|revenge)\b'

# Triforce-themed keywords
TRIFORCE_KEYWORDS = r'\b(wisdom|courage|power|triforce|goddess|goddesses|din|nayru|farore|hylia|master|sword|demise|triangle)\b'

# Compile regex patterns with word boundaries
POT_PATTERN = re.compile(POT_KEYWORDS, re.IGNORECASE)
CUCCO_PATTERN = re.compile(CUCCO_KEYWORDS, re.IGNORECASE)
TRIFORCE_PATTERN = re.compile(TRIFORCE_KEYWORDS, re.IGNORECASE)

# General URL regex for security and utility checks
GENERAL_URL_REGEX = re.compile(r'https?://(?:www\.)?([^/\s]+)(/[^\s]*[^\s\)\]>.,!?])?')

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
    # Archives & Disk Images
    '.zip', '.rar', '.7z', '.tar', '.gz', '.tgz', '.bz2', '.xz', '.iso', '.dmg', '.cab',
    # Executables & Scripts
    '.exe', '.msi', '.apk', '.app', '.bat', '.cmd', '.sh', '.vbs', '.ps1', '.scr', '.jar', '.pif',
    # Media (Video & Audio)
    '.mp4', '.mkv', '.avi', '.mov', '.webm', '.mp3', '.wav', '.flac', '.ogg',
    # Documents (Often flagged for macros or payloads)
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.xlsm', '.ppt', '.pptx'
)

# Rickroll URLs (angle brackets suppress Discord embed)
RICKROLL_URLS = [
    '<https://www.youtube.com/watch?v=5H1nNqGtLxM>',
    '<https://www.youtube.com/watch?v=ZkEv2SOHZJ0>',
]

# ===== NEW FEATURE PATTERNS =====

# GitHub blob URL with line numbers: #L10 or #L10-L20
GITHUB_BLOB_REGEX = re.compile(
    r'https?://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.+?)#L(\d+)(?:-L(\d+))?'
)

# GitHub bare repository URL
GITHUB_REPO_REGEX = re.compile(
    r'https?://github\.com/([^/]+)/([^/]+)/?$'
)

# GitHub user profile URL (must be checked before repo regex - fewer path segments)
GITHUB_USER_REGEX = re.compile(
    r'https?://github\.com/([^/]+)/?$'
)

# File extension to Discord syntax highlight language mapping
GITHUB_LANG_MAP = {
    '.py': 'python', '.js': 'javascript', '.ts': 'typescript', '.jsx': 'jsx',
    '.tsx': 'tsx', '.java': 'java', '.c': 'c', '.cpp': 'cpp', '.h': 'h',
    '.cs': 'csharp', '.go': 'go', '.rs': 'rust', '.rb': 'ruby', '.php': 'php',
    '.swift': 'swift', '.kt': 'kotlin', '.lua': 'lua', '.r': 'r',
    '.sql': 'sql', '.html': 'html', '.css': 'css', '.scss': 'scss',
    '.json': 'json', '.xml': 'xml', '.yaml': 'yaml', '.yml': 'yaml',
    '.toml': 'toml', '.md': 'markdown', '.sh': 'bash', '.bash': 'bash',
    '.ps1': 'powershell', '.dockerfile': 'dockerfile',
}

# Music platform domains for Odesli/song.link
MUSIC_DOMAINS = {'open.spotify.com', 'music.apple.com', 'soundcloud.com'}
MUSIC_URL_REGEX = re.compile(
    r'https?://(?:www\.)?(open\.spotify\.com|music\.apple\.com|soundcloud\.com)/[^\s\)\]>]+'
)

# Steam store URL: store.steampowered.com/app/{app_id}
STEAM_URL_REGEX = re.compile(
    r'https?://store\.steampowered\.com/app/(\d+)'
)

# Steam developer/publisher search URL
STEAM_DEV_REGEX = re.compile(
    r'https?://store\.steampowered\.com/search/[^?\s]*\?[^\s\)\]>]*?\b(developer|publisher)=([^&\s\)\]>]+)'
)

# Wikipedia article URL
WIKI_URL_REGEX = re.compile(
    r'https?://en\.wikipedia\.org/wiki/([^\s\)\]>#?]+)'
)

# YouTube Shorts URL
YOUTUBE_SHORTS_REGEX = re.compile(
    r'https?://(?:www\.)?youtube\.com/shorts/([^/?\s]+)'
)

# Discord message link
DISCORD_MSG_REGEX = re.compile(
    r'https?://(?:ptb\.|canary\.)?discord\.com/channels/(\d+)/(\d+)/(\d+)'
)

# Amazon product URL (any TLD)
AMAZON_URL_REGEX = re.compile(
    r'https?://(?:www\.)?amazon\.[a-z.]{2,6}/(?:[^\s]*?/)?(?:dp|gp/product)/([A-Z0-9]{10})[^\s\)\]>]*'
)

# IMDb title URL
IMDB_URL_REGEX = re.compile(
    r'https?://(?:www\.)?imdb\.com/title/(tt\d+)'
)

# Domains notorious for tracking parameters
# NOTE: Do NOT include domains that are in DOMAIN_MAP (embed-fixed sites like tiktok, instagram, twitter, x)
# Those are handled by the embed fixer and should never hit the tracking stripper.
TRACKING_DOMAINS = {
    'facebook.com', 'youtube.com', 'youtu.be', 'aliexpress.com', 'ebay.com',
}
TRACKING_URL_REGEX = re.compile(
    r'https?://(?:www\.)?(?:' +
    '|'.join(re.escape(d) for d in TRACKING_DOMAINS) +
    r')/[^\s\)\]>]+'
)

# Query params that are pure tracking noise — strip these, keep everything else
TRACKING_PARAMS = {
    'si', 'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
    'utm_id', 'utm_name', 'fbclid', 'igshid', 'ref', 'referrer', 'feature',
    'pp', 'ab_channel',
}

# Construct a regex pattern dynamically from the dictionary keys
DOMAINS_PATTERN = '|'.join(re.escape(domain) for domain in DOMAIN_MAP.keys())
URL_REGEX = re.compile(rf'https?://(?:www\.)?({DOMAINS_PATTERN})(/[^\s]*)')

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author.bot:
        return

    # Debug: Log all messages
    print(f"Message from {message.author}: {message.content}")

    # ===== UTILITY 1: SCAM / PHISHING PROTECTION (SinkingYachts API) =====
    # Runs first - nukes malicious links before anything else touches the message
    url_matches = GENERAL_URL_REGEX.findall(message.content)
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
                await message.channel.send("⚠️ Malicious link removed to protect the kingdom. HYYYAAAAAHHH!")
                return
        except Exception:
            pass  # API timeout or error - allow message to continue

    # ===== UTILITY 2: LINK UNSHORTENING =====
    for domain, path in url_matches:
        if domain.lower() in SHORTENER_DOMAINS:
            short_url = f"https://{domain}{path or ''}"
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(short_url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        final_url = str(resp.url)
                await message.reply(f"shortened link detected! 🔍 for safety heres what it is linking too! {final_url}")
            except Exception as e:
                print(f"❌ Failed to unshorten URL {short_url}: {e}")

    # ===== UTILITY 3: DIRECT FILE LINK ANALYSIS =====
    for domain, path in url_matches:
        if path and path.lower().endswith(FILE_EXTENSIONS):
            file_url = f"https://{domain}{path}"
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.head(file_url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        content_type = resp.headers.get('Content-Type', 'unknown')
                        content_length = resp.headers.get('Content-Length')
                        if content_length:
                            size_bytes = int(content_length)
                            if size_bytes >= 1_048_576:
                                file_size = f"{size_bytes / 1_048_576:.2f} MB"
                            else:
                                file_size = f"{size_bytes / 1024:.2f} KB"
                        else:
                            file_size = "unknown size"
                await message.channel.send(f"📎 *File info: {content_type} | {file_size}*")
            except Exception as e:
                print(f"❌ Failed to fetch file info for {file_url}: {e}")

    # ===== UTILITY 4: GITHUB CODE SNIPPET EXTRACTOR =====
    github_match = GITHUB_BLOB_REGEX.search(message.content)
    if github_match:
        user, repo, branch, file_path = github_match.group(1), github_match.group(2), github_match.group(3), github_match.group(4)
        start_line = int(github_match.group(5))
        end_line = int(github_match.group(6)) if github_match.group(6) else start_line
        raw_url = f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{file_path}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(raw_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        lines = text.splitlines()
                        # Clamp to actual file length
                        start_line = max(1, start_line)
                        end_line = min(len(lines), end_line)
                        snippet = '\n'.join(lines[start_line - 1:end_line])
                        # Determine language for syntax highlighting
                        ext = os.path.splitext(file_path)[1].lower()
                        lang = GITHUB_LANG_MAP.get(ext, '')
                        # Format: file path + line range header
                        header = f"📄 `{file_path}` (L{start_line}" + (f"-L{end_line})" if start_line != end_line else ")")
                        code_block = f"{header}\n```{lang}\n{snippet}\n```"
                        # Discord 2000 char limit check
                        if len(code_block) > 2000:
                            code_block = f"{header}\n```{lang}\n{snippet[:1900]}\n... (truncated)\n```"
                        if len(code_block) <= 2000:
                            await message.reply(code_block, mention_author=False)
                        else:
                            await message.reply(f"{header}\n⚠️ Snippet too large to display.", mention_author=False)
        except Exception as e:
            print(f"❌ Failed to fetch GitHub snippet: {e}")

    # ===== UTILITY 5: UNIVERSAL MUSIC LINKER (Odesli API) =====
    music_match = MUSIC_URL_REGEX.search(message.content)
    if music_match:
        music_url = music_match.group(0)
        # Strip query parameters to prevent Odesli API issues
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
                            await message.reply(f"🎧 Listen on other platforms: {page_url}", mention_author=False)
        except Exception as e:
            print(f"❌ Failed to fetch Odesli link: {e}")

    # ===== UTILITY 6: STEAM GAME INSPECTOR =====
    steam_match = STEAM_URL_REGEX.search(message.content)
    if steam_match:
        app_id = steam_match.group(1)
        try:
            async with aiohttp.ClientSession() as session:
                # Fetch app details
                async with session.get(
                    f"https://store.steampowered.com/api/appdetails?appids={app_id}",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json(content_type=None)
                        app_data = data.get(str(app_id), {})
                        if app_data.get('success'):
                            info = app_data['data']
                            name = info.get('name', 'Unknown')
                            price_info = info.get('price_overview')
                            steam_price_display = price_info['final_formatted'] if price_info else 'Free'
                            steam_price = (price_info.get('final', 0) / 100) if price_info else 0.0
                            discount_percent = price_info.get('discount_percent', 0) if price_info else 0
                            steam_price_str = f"{steam_price_display}" + (f" (-{discount_percent}%)" if discount_percent > 0 else "")
                            desc = info.get('short_description', 'No description available.')
                            desc = re.sub(r'<[^>]+>', '', desc)
                            header_image = info.get('header_image', '')
                            developers = ', '.join(info.get('developers', [])) or 'Unknown'
                            release_date = info.get('release_date', {}).get('date', 'Unknown')
                            metacritic_score = str(info.get('metacritic', {}).get('score', 'N/A'))
                            recommendations = f"{info.get('recommendations', {}).get('total', 'N/A'):,}" if info.get('recommendations') else 'N/A'
                            genres = ', '.join(g['description'] for g in info.get('genres', [])) or 'N/A'

                            # Fetch review score
                            review_score = "Not rated"
                            try:
                                async with session.get(
                                    f"https://store.steampowered.com/appreviews/{app_id}?json=1",
                                    timeout=aiohttp.ClientTimeout(total=5)
                                ) as review_resp:
                                    if review_resp.status == 200:
                                        review_data = await review_resp.json(content_type=None)
                                        query_summary = review_data.get('query_summary', {})
                                        review_score = query_summary.get('review_score_desc', 'Not rated')
                            except Exception as e:
                                print(f"⚠️ Failed to fetch Steam reviews for app {app_id}: {e}")

                            # CheapShark: Step 1 - Get gameID and current best price
                            best_deal_text = "N/A"
                            historical_text = "N/A"
                            try:
                                async with session.get(
                                    f"https://www.cheapshark.com/api/1.0/games?steamAppID={app_id}",
                                    timeout=aiohttp.ClientTimeout(total=5)
                                ) as cs_resp:
                                    game_id = None
                                    if cs_resp.status == 200:
                                        cs_data = await cs_resp.json(content_type=None)
                                        if cs_data and len(cs_data) > 0:
                                            game_id = cs_data[0].get('gameID')
                                            cheapest_current = float(cs_data[0].get('cheapest', 0))
                                            deal_id = cs_data[0].get('cheapestDealID')
                                            if cheapest_current > 0 and cheapest_current < steam_price:
                                                best_deal_text = f"⚠️ [Cheaper elsewhere for ${cheapest_current:.2f}](https://www.cheapshark.com/redirect?dealID={deal_id})"
                                            else:
                                                best_deal_text = "✅ Steam is currently the best price."

                                    # CheapShark: Step 2 - Get historical low using internal gameID
                                    if game_id:
                                        async with session.get(
                                            f"https://www.cheapshark.com/api/1.0/games?id={game_id}",
                                            timeout=aiohttp.ClientTimeout(total=5)
                                        ) as cs_detail_resp:
                                            if cs_detail_resp.status == 200:
                                                cs_detail = await cs_detail_resp.json(content_type=None)
                                                cheapest_ever = cs_detail.get('cheapestPriceEver', {})
                                                lowest_price = cheapest_ever.get('price')
                                                lowest_date = cheapest_ever.get('date')
                                                if lowest_price is not None and lowest_date:
                                                    historical_text = f"${lowest_price} (Hit on <t:{lowest_date}:d>)"
                            except Exception as e:
                                print(f"❌ Failed to fetch CheapShark data for app {app_id}: {e}")

                            # Fetch current player count
                            current_players_str = "N/A"
                            try:
                                async with session.get(
                                    f"https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/?appid={app_id}",
                                    timeout=aiohttp.ClientTimeout(total=5)
                                ) as players_resp:
                                    if players_resp.status == 200:
                                        players_data = await players_resp.json(content_type=None)
                                        if players_data.get('response', {}).get('result') == 1:
                                            player_count = players_data['response']['player_count']
                                            current_players_str = f"{player_count:,}"
                            except Exception as e:
                                print(f"⚠️ Failed to fetch player count for app {app_id}: {e}")

                            embed = discord.Embed(
                                title=name,
                                description=desc,
                                color=discord.Color.blue(),
                                url=f"https://store.steampowered.com/app/{app_id}"
                            )
                            embed.add_field(name="💰 Steam Price", value=steam_price_str, inline=True)
                            embed.add_field(name="🏷️ Best Current Deal", value=best_deal_text, inline=True)
                            embed.add_field(name="📉 Historical Low", value=historical_text, inline=True)
                            embed.add_field(name="📈 Reviews", value=review_score, inline=True)
                            embed.add_field(name="🎯 Metacritic", value=metacritic_score, inline=True)
                            embed.add_field(name="👍 Recommendations", value=recommendations, inline=True)
                            embed.add_field(name="🎮 Current Players", value=current_players_str, inline=True)
                            embed.add_field(name="🏷️ Genres", value=genres, inline=True)
                            embed.add_field(name="🧑‍💻 Developer", value=developers, inline=True)
                            embed.add_field(name="📅 Release Date", value=release_date, inline=True)
                            if header_image:
                                embed.set_image(url=header_image)
                            await message.reply(embed=embed, mention_author=False)
                            try:
                                await message.edit(suppress=True)
                            except (discord.Forbidden, discord.HTTPException):
                                pass
        except Exception as e:
            print(f"❌ Failed to fetch Steam info: {e}")

    # ===== UTILITY 6B: STEAM DEVELOPER / PUBLISHER INSPECTOR =====
    steam_dev_match = STEAM_DEV_REGEX.search(message.content)
    if steam_dev_match:
        search_type = steam_dev_match.group(1)       # 'developer' or 'publisher'
        search_name = steam_dev_match.group(2)       # URL-encoded name
        display_name = unquote(search_name)          # Human-readable name
        original_url = steam_dev_match.group(0)

        async def fetch_game_embed(session, app_id):
            try:
                details_req = session.get(
                    f"https://store.steampowered.com/api/appdetails?appids={app_id}",
                    timeout=aiohttp.ClientTimeout(total=5)
                )
                reviews_req = session.get(
                    f"https://store.steampowered.com/appreviews/{app_id}?json=1",
                    timeout=aiohttp.ClientTimeout(total=5)
                )
                async with details_req as dr, reviews_req as rr:
                    details_data = await dr.json(content_type=None)
                    reviews_data = await rr.json(content_type=None)

                app_info = details_data.get(str(app_id), {})
                if not app_info.get('success'):
                    return None
                data = app_info.get('data', {})

                name         = data.get('name', 'Unknown')
                header_image = data.get('header_image', '')
                price_obj    = data.get('price_overview')
                if price_obj:
                    price = price_obj.get('final_formatted', 'N/A')
                elif data.get('is_free'):
                    price = 'Free'
                else:
                    price = 'N/A'

                review_desc = (
                    reviews_data.get('query_summary', {}).get('review_score_desc', 'N/A')
                )

                embed = discord.Embed(
                    title=name,
                    url=f"https://store.steampowered.com/app/{app_id}",
                    color=discord.Color.blue()
                )
                if header_image:
                    embed.set_thumbnail(url=header_image)
                embed.add_field(name="💰 Price",   value=price,       inline=True)
                embed.add_field(name="📈 Reviews", value=review_desc, inline=True)
                return embed
            except Exception as e:
                print(f"❌ fetch_game_embed({app_id}): {e}")
                return None

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Referer': 'https://store.steampowered.com/'
            }
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(
                    f"https://store.steampowered.com/search/results/?{search_type}={search_name}&json=1&start=0&count=10&l=english&cc=US",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json(content_type=None)
                        items = data.get('items', [])

                        # Extract app IDs from the logo URLs, e.g. /steam/apps/250900/
                        app_ids = []
                        for item in items:
                            logo = item.get('logo', '')
                            m = re.search(r'/steam/apps/(\d+)/', logo)
                            if m:
                                app_ids.append(m.group(1))
                        top_app_ids = list(dict.fromkeys(app_ids))[:5]

                        if top_app_ids:
                            embeds_list = await asyncio.gather(
                                *[fetch_game_embed(session, aid) for aid in top_app_ids]
                            )
                            embeds_list = [e for e in embeds_list if e is not None]

                        if embeds_list:
                            await message.reply(
                                content=f"🎮 **Top games by {display_name}:**",
                                embeds=embeds_list,
                                mention_author=False
                            )
                            try:
                                await message.edit(suppress=True)
                            except discord.Forbidden:
                                pass
        except Exception as e:
            print(f"❌ Failed to fetch Steam dev/publisher info: {e}")

    # ===== UTILITY 7: WIKIPEDIA TL;DR FETCHER =====
    wiki_match = WIKI_URL_REGEX.search(message.content)
    if wiki_match:
        title = wiki_match.group(1)
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
                        article_url = data.get('content_urls', {}).get('desktop', {}).get('page', f"https://en.wikipedia.org/wiki/{title}")
                        thumbnail_source = data.get('thumbnail', {}).get('source')

                        if extract:
                            # Build description: italic subtitle + summary text
                            desc_parts = []
                            if description:
                                desc_parts.append(f"*{description}*")
                            desc_parts.append(extract)
                            full_description = '\n\n'.join(desc_parts)
                            # Discord embed description limit is 4096 chars
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
                            # Suppress Discord's default link preview if we have permission
                            try:
                                await message.edit(suppress=True)
                            except (discord.Forbidden, discord.HTTPException):
                                pass
        except Exception as e:
            print(f"❌ Failed to fetch Wikipedia summary: {e}")

    # ===== UTILITY 7B: GITHUB REPOSITORY INFO =====
    github_repo_match = GITHUB_REPO_REGEX.search(message.content)
    if github_repo_match:
        user, repo = github_repo_match.group(1), github_repo_match.group(2)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://api.github.com/repos/{user}/{repo}",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        repo_data = await resp.json(content_type=None)
                        description = repo_data.get('description') or 'No description available.'
                        stars = repo_data.get('stargazers_count', 0)
                        forks = repo_data.get('forks_count', 0)
                        language = repo_data.get('language') or 'Unknown'
                        pushed_at = repo_data.get('pushed_at', '')
                        repo_url = repo_data.get('html_url', f"https://github.com/{user}/{repo}")
                        last_updated = pushed_at.split('T')[0] if pushed_at else 'Never'

                        embed = discord.Embed(
                            title=f"📁 {user}/{repo}",
                            description=description,
                            color=discord.Color.dark_theme(),
                            url=repo_url
                        )
                        embed.add_field(name="⭐ Stars", value=str(stars), inline=True)
                        embed.add_field(name="🍴 Forks", value=str(forks), inline=True)
                        embed.add_field(name="💻 Language", value=language, inline=True)
                        embed.add_field(name="📅 Last Updated", value=last_updated, inline=True)
                        embed.set_footer(text="GitHub")
                        await message.reply(embed=embed, mention_author=False)
        except Exception as e:
            print(f"❌ Failed to fetch GitHub repo info: {e}")

    # ===== UTILITY 7C: GITHUB USER PROFILE =====
    # Must be checked AFTER blob and repo — it matches any single-segment GitHub URL
    github_user_match = GITHUB_USER_REGEX.search(message.content)
    if github_user_match:
        username = github_user_match.group(1)
        profile_url = f"https://github.com/{username}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://api.github.com/users/{username}",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        user_data = await resp.json(content_type=None)
                        avatar_url = user_data.get('avatar_url', '')
                        display_name = user_data.get('name') or username
                        bio = user_data.get('bio') or 'No bio available.'
                        public_repos = user_data.get('public_repos', 0)
                        followers = user_data.get('followers', 0)

                        # Fetch 3 most recently pushed repos
                        recent_repos_str = 'N/A'
                        async with session.get(
                            f"https://api.github.com/users/{username}/repos?sort=pushed&per_page=3",
                            timeout=aiohttp.ClientTimeout(total=5)
                        ) as repos_resp:
                            if repos_resp.status == 200:
                                repos_data = await repos_resp.json(content_type=None)
                                recent_repos_str = '\n'.join(
                                    f"`{r['name']}`" for r in repos_data
                                ) or 'No public repos.'

                        embed = discord.Embed(
                            title=f"GitHub: {display_name}",
                            description=bio,
                            color=discord.Color.dark_theme(),
                            url=profile_url
                        )
                        if avatar_url:
                            embed.set_thumbnail(url=avatar_url)
                        embed.add_field(name="👥 Followers", value=str(followers), inline=True)
                        embed.add_field(name="📦 Public Repos", value=str(public_repos), inline=True)
                        embed.add_field(name="🕐 Recent Activity", value=recent_repos_str, inline=False)
                        embed.set_footer(text="GitHub")
                        await message.reply(embed=embed, mention_author=False)
        except Exception as e:
            print(f"❌ Failed to fetch GitHub user profile: {e}")

    # ===== UTILITY 9: DISCORD MESSAGE LINK QUOTING =====
    discord_msg_match = DISCORD_MSG_REGEX.search(message.content)
    if discord_msg_match:
        guild_id   = discord_msg_match.group(1)
        channel_id = discord_msg_match.group(2)
        message_id = discord_msg_match.group(3)
        original_url = discord_msg_match.group(0)
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
        except (discord.NotFound, discord.Forbidden, AttributeError):
            pass

    # ===== UTILITY 10: AMAZON PRODUCT EMBED =====
    amazon_match = AMAZON_URL_REGEX.search(message.content)
    if amazon_match:
        asin = amazon_match.group(1)
        amazon_url = amazon_match.group(0).split('?')[0]  # strip tracking params
        # CamelCamelCamel price history link (free, no API key)
        camel_url = f"https://camelcamelcamel.com/product/{asin}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    amazon_url,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    },
                    timeout=aiohttp.ClientTimeout(total=8)
                ) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        soup = BeautifulSoup(html, 'html.parser')

                        # --- TITLE ---
                        # Amazon omits og: tags for bots; use bond (luxury) or standard DOM
                        og_title = soup.find('meta', property='og:title')
                        bond_title = soup.find('div', id='bond-title-desktop')
                        span_title = soup.find('span', id='productTitle')
                        title_tag = soup.find('title')
                        product_title = (
                            (og_title.get('content') if og_title else None)
                            or (bond_title.get_text(strip=True) if bond_title else None)
                            or (span_title.text.strip() if span_title else None)
                            or (title_tag.string.strip() if title_tag and title_tag.string else None)
                        )

                        # --- IMAGE ---
                        og_image = soup.find('meta', property='og:image')
                        product_image = og_image.get('content') if og_image else None
                        if not product_image:
                            img_tag = soup.find('img', id='landingImage') or soup.find('img', id='imgBlkFront')
                            if img_tag:
                                dynamic_json = img_tag.get('data-a-dynamic-image')
                                if dynamic_json:
                                    try:
                                        dynamic_imgs = _json.loads(dynamic_json)
                                        product_image = max(dynamic_imgs, key=lambda u: dynamic_imgs[u][0] * dynamic_imgs[u][1])
                                    except Exception:
                                        product_image = img_tag.get('src')
                                else:
                                    product_image = img_tag.get('src')

                        # --- PRICE ---
                        # corePrice_desktop has the formatted price; a-offscreen is screen-reader span inside it
                        price_tag = soup.find('span', class_='a-offscreen')
                        price = price_tag.text.strip() if price_tag else ''

                        # --- DESCRIPTION ---
                        # Try bond (luxury) → standard feature-bullets → productDescription
                        description_lines = []
                        bullets_div = (
                            soup.find('div', id='bond-feature-bullets-desktop')
                            or soup.find('div', id='feature-bullets')
                        )
                        if bullets_div:
                            items = bullets_div.find_all('li')
                            for li in items[:4]:  # max 4 bullets
                                text = li.get_text(strip=True)
                                if text:
                                    description_lines.append(f'• {text}')

                        if not description_lines:
                            # Fall back to product description paragraph
                            desc_div = (
                                soup.find('div', id='bond-product-descriptions-desktop')
                                or soup.find('div', id='productDescription')
                            )
                            if desc_div:
                                raw = desc_div.get_text(separator=' ', strip=True)
                                description_lines.append(raw[:500] + ('…' if len(raw) > 500 else ''))

                        description_text = '\n'.join(description_lines) if description_lines else ''

                        # --- PRODUCT SPECS TABLE ---
                        # productOverview_feature_div: Brand | Color | Form | Finish | etc.
                        specs = {}
                        overview_div = soup.find('div', id='productOverview_feature_div')
                        if overview_div:
                            rows = overview_div.find_all('tr')
                            for row in rows:
                                cols = row.find_all(['th', 'td'])
                                if len(cols) >= 2:
                                    key = cols[0].get_text(strip=True)
                                    val = cols[1].get_text(strip=True)
                                    if key and val:
                                        specs[key] = val

                        if product_title:
                            embed = discord.Embed(
                                title=product_title[:256],
                                url=amazon_url,
                                color=discord.Color.orange()
                            )
                            if description_text:
                                embed.description = description_text[:1024]
                            if price:
                                embed.add_field(name="💰 Price", value=price, inline=True)
                            # Show up to 4 spec fields inline
                            for spec_key, spec_val in list(specs.items())[:4]:
                                embed.add_field(name=spec_key, value=spec_val[:100], inline=True)
                            embed.add_field(
                                name="📈 Price History",
                                value=f"[View on CamelCamelCamel]({camel_url})",
                                inline=False
                            )
                            if product_image:
                                embed.set_thumbnail(url=product_image)
                            await message.reply(
                                content=f"🛒 **Cleaned Amazon Link:** {amazon_url}",
                                embed=embed,
                                mention_author=False
                            )
                            try:
                                await message.edit(suppress=True)
                            except (discord.Forbidden, discord.HTTPException):
                                pass
        except Exception as e:
            print(f"❌ Failed to fetch Amazon product info: {e}")

    # ===== UTILITY 11: IMDB MOVIE INSPECTOR =====
    imdb_match = IMDB_URL_REGEX.search(message.content)
    if imdb_match:
        if not OMDB_API_KEY:
            print("❌ OMDB_API_KEY is missing! Cannot fetch IMDb data.")
        else:
            imdb_id = imdb_match.group(1)
            original_url = imdb_match.group(0)
            print(f"🎬 IMDb match: {imdb_id}, key present: True")
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"https://www.omdbapi.com/?i={imdb_id}&apikey={OMDB_API_KEY}",
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as resp:
                        print(f"🎬 OMDb status: {resp.status}")
                        if resp.status == 200:
                            data = await resp.json(content_type=None)
                            if data.get('Response') == 'True':
                                title       = data.get('Title', 'Unknown')
                                year        = data.get('Year', '?')
                                plot        = data.get('Plot', 'No plot available.')
                                poster      = data.get('Poster', '')
                                imdb_rating = data.get('imdbRating', 'N/A')
                                rated       = data.get('Rated', 'N/A')
                                embed = discord.Embed(
                                    title=f"{title} ({year})",
                                    description=plot,
                                    url=original_url,
                                    color=discord.Color.gold()
                                )
                                embed.add_field(name="⭐ IMDb Rating", value=imdb_rating, inline=True)
                                embed.add_field(name="🔞 Age Rating",  value=rated,       inline=True)
                                if poster and poster != 'N/A':
                                    embed.set_thumbnail(url=poster)
                                await message.reply(embed=embed, mention_author=False)
                                try:
                                    await message.edit(suppress=True)
                                except (discord.Forbidden, discord.HTTPException):
                                    pass
                            else:
                                print(f"❌ OMDb API Error: {data.get('Error')}")
            except Exception as e:
                print(f"❌ Failed to fetch IMDb info: {e}")

    # ===== UTILITY 8: URL TRACKING PARAMETER STRIPPER =====
    # Strips known tracking-only params (si, utm_*, fbclid, etc.) while keeping
    # functional params like v= on YouTube. Only fires if the URL isn't already
    # handled by the Shorts converter (which replaces the whole URL anyway).
    tracking_match = TRACKING_URL_REGEX.search(message.content)
    if tracking_match:
        raw_tracking_url = tracking_match.group(0)
        tracking_hostname = urlparse(raw_tracking_url).hostname or ''
        tracking_base = tracking_hostname.removeprefix('www.')

        # Shorts are handled by the link fixer webhook — skip to avoid duplicate reply
        already_handled = YOUTUBE_SHORTS_REGEX.search(message.content) is not None

        if not already_handled:
            parsed = urlparse(raw_tracking_url)
            # Parse and filter query params — drop pure tracking ones, keep the rest
            kept = [(k, v) for k, v in parse_qsl(parsed.query) if k.lower() not in TRACKING_PARAMS]
            stripped_query = urlencode(kept)
            clean_parsed = parsed._replace(query=stripped_query, fragment='')
            clean_url = clean_parsed.geturl()

            # Only reply if we actually removed something
            if clean_url.rstrip('/') != raw_tracking_url.rstrip('/'):
                await message.reply(f"🧹 Clean link without tracking: {clean_url}", mention_author=False)
                try:
                    await message.edit(suppress=True)
                except (discord.Forbidden, discord.HTTPException):
                    pass

    # ===== EASTER EGG 1: Direct Ping Response =====
    if client.user.mentioned_in(message):
        print(f"Bot was mentioned! Responding...")

        # 5% chance for rickroll - checked first, halts all further processing
        if random.random() <= 0.05:
            await message.channel.send(f"HERES A LINK FOR YA {random.choice(RICKROLL_URLS)}")
            return

        # 10% chance for sound, 35% chance for image, 55% chance for text
        rand_response = random.randint(1, 100)

        if rand_response <= 10:  # 10% - Sound
            sounds_dir = "sounds"
            if os.path.exists(sounds_dir):
                sound_files = [f for f in os.listdir(sounds_dir) if f.endswith(('.mp3', '.wav', '.ogg'))]
                if sound_files:
                    sound_file = random.choice(sound_files)
                    await message.channel.send(file=discord.File(os.path.join(sounds_dir, sound_file)))
        elif rand_response <= 45:  # 35% - Image
            images_dir = "images"
            if os.path.exists(images_dir):
                image_files = [f for f in os.listdir(images_dir) if f.endswith(('.png', '.jpg', '.jpeg', '.gif'))]
                if image_files:
                    image_file = random.choice(image_files)
                    await message.channel.send(file=discord.File(os.path.join(images_dir, image_file)))
        else:  # 55% - Text response
            print(f"Sending text response...")
            await message.channel.send(random.choice(ZELDA_TEXT_RESPONSES))

    # ===== EASTER EGG 2: Pot Reaction =====
    if POT_PATTERN.search(message.content):
        try:
            await message.add_reaction('<a:link_spin:1475252964708057118>')
            await message.add_reaction('<:pot:1475279632512188718>')
        except discord.errors.HTTPException:
            pass

    # ===== EASTER EGG 2B: Cucco/Chicken Reaction =====
    if CUCCO_PATTERN.search(message.content):
        try:
            await message.add_reaction('🐔')
            await message.add_reaction('<a:link_spin:1475252964708057118>')
        except discord.errors.HTTPException:
            pass

    # ===== EASTER EGG 2C: Triforce Reaction =====
    if TRIFORCE_PATTERN.search(message.content):
        try:
            await message.add_reaction('<a:link_triforce:1475284641513607338>')
        except discord.errors.HTTPException:
            pass

    # ===== LINK FIXING LOGIC =====
    try:
        matches = list(URL_REGEX.finditer(message.content))
        shorts_match = YOUTUBE_SHORTS_REGEX.search(message.content)

        if matches or shorts_match:
            fixed_content = message.content

            # ===== YOUTUBE SHORTS CONVERTER =====
            if shorts_match:
                fixed_content = YOUTUBE_SHORTS_REGEX.sub(
                    lambda m: f"https://www.youtube.com/watch?v={m.group(1)}",
                    fixed_content
                )

            # Collect (path, lang) pairs for fixupx translation fetches after webhook send
            pending_translations = []  # list of (clean_path, lang_code)

            for match in matches:
                matched_domain = match.group(1)
                fixed_domain = DOMAIN_MAP[matched_domain]
                original_url = match.group(0)  # full URL as typed (may include .translate suffix)
                path = match.group(2)

                # ===== TRANSLATION TAG DETECTION =====
                # Syntax: paste URL with .translate or .translate.spanish appended
                # e.g. https://twitter.com/user/status/123.translate.japanese
                translate_lang = None
                translate_suffix_match = TRANSLATE_SUFFIX_REGEX.search(path)
                if translate_suffix_match:
                    lang_word = (translate_suffix_match.group(1) or 'en').lower()
                    # Bare 2-letter ISO code passes through; full names are looked up
                    if len(lang_word) == 2:
                        translate_lang = lang_word
                    else:
                        translate_lang = LANGUAGE_MAP.get(lang_word, 'en')
                    # Strip the .translate[.lang] suffix from path only
                    # Keep original_url intact — it's used as the search key in fixed_content.replace()
                    path = path[:translate_suffix_match.start()]

                # Build the proxy URL (using the clean path, without .translate suffix)
                fixed_url = f"https://{fixed_domain}{path}"

                # Apply translation routing for supported proxies
                if translate_lang:
                    if fixed_domain == 'fixupx.com':
                        # fixupx: append /lang at the end
                        # e.g. https://fixupx.com/user/status/123 → https://fixupx.com/user/status/123/ja
                        fixed_url = f"{fixed_url}/{translate_lang}"
                        # Queue a translation fetch from fxtwitter API (OG tags don't contain translated text)
                        pending_translations.append((path, translate_lang))
                    elif fixed_domain == 'phixiv.net':
                        # phixiv: insert /lang right after the domain
                        # e.g. https://phixiv.net/artworks/123 → https://phixiv.net/ja/artworks/123
                        fixed_url = f"https://{fixed_domain}/{translate_lang}{path}"
                    # All other domains: translation not supported, use URL as-is

                # Replace the full original URL (including any .translate suffix) with the fixed URL
                fixed_content = fixed_content.replace(original_url, fixed_url)

            # ===== EASTER EGG 3: Rare Item Drop (5% chance) =====
            if random.random() < 0.05:
                fixed_content += "\n\n*Da-da-da-daaa!* 🗝️"

            webhooks = await message.channel.webhooks()
            webhook = discord.utils.get(webhooks, name="LinkFixerWebhook")
            if not webhook:
                webhook = await message.channel.create_webhook(name="LinkFixerWebhook")

            await webhook.send(
                content=fixed_content,
                username=message.author.display_name,
                avatar_url=message.author.display_avatar.url
            )

            # ===== FIXUPX TRANSLATION FETCH =====
            # fixupx does NOT inject translated text into OG meta tags, so we fetch it
            # directly from api.fxtwitter.com and post it as a follow-up message.
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
                                            f"🌐 *(No translation available for this tweet)*"
                                        )
                        except Exception as e:
                            print(f"❌ Translation fetch error: {e}")

            await message.delete()
    except discord.Forbidden:
        print(f"❌ Missing permissions in {message.channel}.")
    except Exception as e:
        print(f"❌ Error processing message: {e}")

# Retrieve bot token from environment variable
bot_token = os.getenv('DISCORD_BOT_TOKEN')
if not bot_token:
    raise ValueError("DISCORD_BOT_TOKEN not found in .env file. Please add your bot token to the .env file.")

client.run(bot_token)