import discord
import re
import os
import random
import aiohttp
from urllib.parse import urlparse
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
    "HYYAAAAAA! <a:link_spin:1475252964708057118>",
    "Hey! Listen! 🧚",
    "It's dangerous to go alone! Take this. ⚔️ <a:link_spin:1475252964708057118>"
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
GENERAL_URL_REGEX = re.compile(r'https?://(?:www\.)?([^/\s]+)(/[^\s]*)?')

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
    for raw_url in re.findall(r'https?://[^\s]+', message.content):
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