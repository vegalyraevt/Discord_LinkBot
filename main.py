import discord
import re
import os
import random
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
    "HYYAAAAAA! <:link:1475252964708057118>",
    "Hey! Listen! 🧚",
    "It's dangerous to go alone! Take this. ⚔️ <:link:1475252964708057118>"
]

# Expanded list for Pots/Crime/Destruction - word boundaries only
POT_KEYWORDS = r'\b(pot|pots|smash|break|vase|vases|jar|jars|urn|urns|ceramics|pottery|link|links|rupee|rupees|money|burglary|theft|vandalism|vandalize|steal|stealing|thief|rob|robbery|loot|looting|crime|shatter|trespass|trespassing|crash|destroy|destruction|ransack|pillage)\b'

# Expanded list for Cuccos/Chickens/Swarm - word boundaries only
CUCCO_KEYWORDS = r'\b(cucco|cuccos|cuckoo|cuckoos|chicken|chickens|poultry|peck|pecking|flock|kakariko|rooster|cluck|feathers|swarm|revenge)\b'

# Triforce-themed keywords
TRIFORCE_KEYWORDS = r'\b(wisdom|courage|power|triforce|goddess|goddesses|din|nayru|farore|hylia|sacred realm|master sword|demise|triangle)\b'

# Compile regex patterns with word boundaries
POT_PATTERN = re.compile(POT_KEYWORDS, re.IGNORECASE)
CUCCO_PATTERN = re.compile(CUCCO_KEYWORDS, re.IGNORECASE)
TRIFORCE_PATTERN = re.compile(TRIFORCE_KEYWORDS, re.IGNORECASE)

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

    # ===== EASTER EGG 1: Direct Ping Response =====
    if client.user.mentioned_in(message):
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
            await message.channel.send(random.choice(ZELDA_TEXT_RESPONSES))

    # ===== EASTER EGG 2: Pot Reaction =====
    if POT_PATTERN.search(message.content):
        try:
            # React with custom Link emoji and custom Pot emoji
            await message.add_reaction('<:link:1475252964708057118>')
            await message.add_reaction('<:pot:1475279632512188718>')
        except discord.errors.HTTPException:
            pass  # Ignore permission or connection errors

    # ===== EASTER EGG 2B: Cucco/Chicken Reaction =====
    if CUCCO_PATTERN.search(message.content):
        try:
            # React with two chicken emojis
            await message.add_reaction('🐔')
            await message.add_reaction('<:link:1475252964708057118>')
        except discord.errors.HTTPException:
            pass  # Ignore permission or connection errors

    # ===== EASTER EGG 2C: Triforce Reaction =====
    if TRIFORCE_PATTERN.search(message.content):
        try:
            # React with animated Triforce emoji
            await message.add_reaction('<a:link_triforce:1475284641513607338>')
        except discord.errors.HTTPException:
            pass  # Ignore permission or connection errors

    # ===== LINK FIXING LOGIC (before deleting original message) =====
    try:
        # Find all matching URLs in the message
        matches = list(URL_REGEX.finditer(message.content))
        
        if matches:
            fixed_content = message.content
            
            # Iterate through every found link and replace it
            for match in matches:
                matched_domain = match.group(1)
                fixed_domain = DOMAIN_MAP[matched_domain]
                original_url = match.group(0)
                path = match.group(2)
                
                # Reconstruct the URL with the fixed domain
                fixed_url = f"https://{fixed_domain}{path}"
                fixed_content = fixed_content.replace(original_url, fixed_url)

            # ===== EASTER EGG 3: Rare Item Drop (5% chance) =====
            if random.random() < 0.05:
                fixed_content += "\n\n*Da-da-da-daaa!* 🗝️"

            # Check if a webhook exists
            webhooks = await message.channel.webhooks()
            webhook = discord.utils.get(webhooks, name="LinkFixerWebhook")
            
            # Create webhook if missing
            if not webhook:
                webhook = await message.channel.create_webhook(name="LinkFixerWebhook")

            # Send the modified message via webhook
            await webhook.send(
                content=fixed_content,
                username=message.author.display_name,
                avatar_url=message.author.display_avatar.url
            )
            
            # Delete original message
            await message.delete()
    except discord.Forbidden:
        print(f"❌ Missing permissions in {message.channel}. Ensure the bot has 'Manage Messages' and 'Manage Webhooks' permissions.")
    except Exception as e:
        print(f"❌ Error processing message: {e}")

# Retrieve bot token from environment variable
bot_token = os.getenv('DISCORD_BOT_TOKEN')
if not bot_token:
    raise ValueError("DISCORD_BOT_TOKEN not found in .env file. Please add your bot token to the .env file.")

client.run(bot_token)