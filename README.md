# LinkBot - Discord Embed Fixer

A Discord bot that automatically fixes broken social media embeds by replacing domain names with embed-friendly alternatives.

## Supported Platforms

- **Twitter/X** → fixupx.com
- **TikTok** → vxtiktok.com
- **Instagram** → ddinstagram.com
- **Reddit** → rxddit.com
- **Pixiv** → phixiv.net

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

## Troubleshooting

- **Bot not responding?** Ensure the Message Content Intent is enabled in Discord Developer Portal
- **Permission errors?** Check that the bot has the required permissions in your server
- **Token issues?** Regenerate your token in the Discord Developer Portal immediately

## License

MIT
