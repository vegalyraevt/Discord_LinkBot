# LinkBot - Discord Embed Fixer

A Discord bot that automatically fixes broken social media embeds by replacing domain names with embed-friendly alternatives.

## Invite me!
[Discord Invite Link](https://discord.com/oauth2/authorize?client_id=1475244291944218715&permissions=2322581411986432&integration_type=0&scope=bot)

## Supported Platforms

- **Twitter/X** → fixupx.com
- **TikTok** → tnktok.com
- **Instagram** → uuinstagram.com
- **Reddit** → rxddit.com
- **Pixiv** → phixiv.net

## Backup Proxy Domains

If a primary proxy domain becomes unavailable, these backup alternatives can be used:
- **Instagram:** gginstagram.com, d.vxinstagram.com

## Setup Instructions

### 1. Clone the repository
```bash
git clone <your-repo-url>
cd LinkBot
```

### 2. Create a virtual environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure your bot token
```bash
cp .env.example .env
# Edit .env and add your Discord bot token
nano .env
```

### 5. Run the bot
```bash
python3 main.py
```

## Bot Permissions Required

Make sure your bot has these permissions in Discord:
- ✅ Read Messages/View Channels
- ✅ Send Messages
- ✅ Manage Messages (to delete originals)
- ✅ Manage Webhooks

## How It Works

1. Bot listens to all messages in channels where it's invited
2. Detects URLs from supported platforms using regex
3. Replaces the domain with an embed-friendly alternative
4. Deletes the original message
5. Reposts the modified URL using a webhook, impersonating the original author

## 🎮 Zelda Easter Eggs

The bot includes hidden Legend of Zelda references that trigger automatically:

### 1. Direct Ping Response (55% text, 35% image, 10% sound)
When you mention the bot with `@Link`, it responds with:
- **55% of the time:** Random text like "HYYAAAAAA! <:link:1475252964708057118>", "Hey! Listen! 🧚", or "It's dangerous to go alone! Take this. ⚔️ <:link:1475252964708057118>"
- **35% of the time:** A random image from the `images/` folder
- **10% of the time:** A random sound from the `sounds/` folder

**To use:** Place `.png`, `.jpg`, `.gif` files in the `images/` folder and `.mp3`, `.wav`, `.ogg` files in the `sounds/` folder.

### 2. Pot Reaction
Message contains "pot", "pots", or "smash"? The bot reacts with:
- Custom Link emoji: `<:link:1475252964708057118>`
- Pot emoji: 🍲

### 3. Rare Item Drop (5% chance)
When a link is fixed and sent via webhook, there's a 5% chance the bot appends:
```
*Da-da-da-daaa!* 🗝️
```

## Troubleshooting

- **Bot not responding?** Ensure the Message Content Intent is enabled in Discord Developer Portal
- **Permission errors?** Check that the bot has the required permissions in your server
- **Token issues?** Regenerate your token in the Discord Developer Portal immediately

## License

MIT
