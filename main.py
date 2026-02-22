import discord
import re
import os
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
    'instagram.com': 'gginstagram.com',
    'reddit.com': 'rxddit.com',
    'pixiv.net': 'phixiv.net'
}

# Backup proxy domains if primary ones fail (for future use)
BACKUP_DOMAINS = {
    'instagram.com': ['uuinstagram.com', 'd.vxinstagram.com']
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