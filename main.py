import discord
import re
import os
import random
import aiohttp
from urllib.parse import urlparse, quote
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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
    'pixiv.net': 'phixiv.net'
}

# Backup proxy domains if primary ones fail (for future use)
BACKUP_DOMAINS = {
    'instagram.com': ['gginstagram.com', 'd.vxinstagram.com']
}

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
    'soo.gd', 's.id', 'adf.ly', 'lnkd.in', 'amzn.to', 'youtu.be', 'wp.me',
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

# Wikipedia article URL
WIKI_URL_REGEX = re.compile(
    r'https?://en\.wikipedia\.org/wiki/([^\s\)\]>#?]+)'
)

# Domains notorious for tracking parameters
TRACKING_DOMAINS = {
    'amazon.com', 'amazon.co.uk', 'amazon.ca', 'amazon.de', 'amazon.co.jp',
    'twitter.com', 'x.com', 'tiktok.com', 'facebook.com', 'instagram.com',
    'youtube.com', 'youtu.be', 'aliexpress.com', 'ebay.com',
}
TRACKING_URL_REGEX = re.compile(
    r'(https?://(?:www\.)?(?:' +
    '|'.join(re.escape(d) for d in TRACKING_DOMAINS) +
    r')/[^\s\)\]>?]*)\?[^\s\)\]>]+'
)

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
                            price = price_info['final_formatted'] if price_info else 'Free / Not Available'
                            discount_percent = price_info.get('discount_percent', 0) if price_info else 0
                            discount_str = f"(-{discount_percent}%)" if discount_percent > 0 else ""
                            desc = info.get('short_description', 'No description available.')
                            # Strip any HTML tags from Steam's description
                            desc = re.sub(r'<[^>]+>', '', desc)
                            
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
                            
                            await message.reply(
                                f"🎮 **{name}**\n💰 Price: {price} {discount_str}\n📈 Reviews: {review_score}\n📝 {desc}",
                                mention_author=False
                            )
        except Exception as e:
            print(f"❌ Failed to fetch Steam info: {e}")

    # ===== UTILITY 7: WIKIPEDIA TL;DR FETCHER =====
    wiki_match = WIKI_URL_REGEX.search(message.content)
    if wiki_match:
        title = wiki_match.group(1)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&exintro=true&explaintext=true&format=json&redirects=1&titles={title}",
                    headers={'User-Agent': 'DiscordBot (https://github.com/vegalyraevt/Discord_LinkBot)'},
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json(content_type=None)
                        pages = data.get('query', {}).get('pages', {})
                        for page_id, page_data in pages.items():
                            if page_id == '-1':
                                break
                            extract = page_data.get('extract', '')
                            if extract:
                                # Truncate to ~450 chars at a sentence boundary
                                if len(extract) > 450:
                                    cut = extract[:450].rfind('.')
                                    extract = extract[:cut + 1] if cut > 200 else extract[:450]
                                    extract += '...'
                                await message.reply(
                                    f"📖 **Wikipedia Summary:**\n{extract}",
                                    mention_author=False
                                )
                            break  # Only process the first page result
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
                        description = repo_data.get('description', 'No description available.')
                        stars = repo_data.get('stargazers_count', 0)
                        forks = repo_data.get('forks_count', 0)
                        language = repo_data.get('language', 'Unknown')
                        pushed_at = repo_data.get('pushed_at', '')
                        
                        # Format the pushed_at timestamp to YYYY-MM-DD
                        if pushed_at:
                            last_updated = pushed_at.split('T')[0]
                        else:
                            last_updated = 'Never'
                        
                        await message.reply(
                            f"📁 **GitHub Repository: {user}/{repo}**\n⭐ Stars: {stars} | 🍴 Forks: {forks} | 💻 {language} | 📅 Last Updated: {last_updated}\n{description}",
                            mention_author=False
                        )
        except Exception as e:
            print(f"❌ Failed to fetch GitHub repo info: {e}")

    # ===== UTILITY 8: URL TRACKING PARAMETER STRIPPER =====
    tracking_match = TRACKING_URL_REGEX.search(message.content)
    if tracking_match:
        clean_url = tracking_match.group(1)
        await message.reply(f"🧹 Clean link without tracking: {clean_url}", mention_author=False)

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

        if matches:
            fixed_content = message.content

            for match in matches:
                matched_domain = match.group(1)
                fixed_domain = DOMAIN_MAP[matched_domain]
                original_url = match.group(0)
                path = match.group(2)
                fixed_url = f"https://{fixed_domain}{path}"
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