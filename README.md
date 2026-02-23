# LinkBot - Discord Embed Fixer

A lightweight, webhook-powered Discord bot built in Python (`discord.py`) that automatically fixes broken social media embeds by replacing domain names with embed-friendly alternatives.

## Invite me!
[Discord Invite Link](https://discord.com/oauth2/authorize?client_id=1475244291944218715&permissions=2322581411986432&integration_type=0&scope=bot)

## How It Works

1. The bot listens to all messages in channels where it is invited.
2. It detects URLs from supported platforms using regex.
3. It replaces the domain with an embed-friendly alternative.
4. It deletes the original message.
5. It reposts the modified URL using a webhook, perfectly impersonating the original author.

## Supported Platforms

The bot currently listens for and fixes links from the following domains by substituting them with community-hosted proxies:
* **Twitter / X** -> `fixupx.com`
* **TikTok** -> `tnktok.com`
* **Instagram** -> `uuinstagram.com`
* **Reddit** -> `rxddit.com`
* **Pixiv** -> `phixiv.net`

### Backup Proxy Domains
If a primary proxy domain becomes unavailable, these backup alternatives can be swapped into the code:
* **Instagram:** `gginstagram.com`, `d.vxinstagram.com`

## Utility Features

* **Anti-Phishing Protection:** Actively parses posted domains against the live SinkingYachts API. If a known malicious Discord scam link is detected, the bot instantly deletes the message and posts a warning to protect the server.
* **Link Unshortening:** Automatically detects shortened URLs (like `bit.ly` or `tinyurl`) and replies with the true destination link to prevent hidden redirects.
  * *[Insert Link Unshortening Screenshot Here]*
* **Direct File Analysis:** Intercepts direct links to files (`.exe`, `.zip`, `.mp4`, etc.) and performs a secure header check to announce the exact file type and size to the channel before anyone clicks it.
  * *[Insert Download Link Inspection Screenshot Here]*

## Zelda Easter Eggs

The bot includes hidden *Legend of Zelda* references that trigger automatically, adding charm without interrupting normal conversations:

* **Direct Ping Response:** When you mention the bot directly with `@Link`, it responds with one of the following:
  * **55% chance:** Iconic and funny quotes from the Zelda games, the 1989 cartoon, and the CD-i spin-offs.
  * **35% chance:** A random image from the `images/` folder.
  * **10% chance:** A random sound from the `sounds/` folder.
  *(Note: To use the media responses, place `.png`, `.jpg`, and `.gif` files in the `images/` folder, and `.mp3`, `.wav`, and `.ogg` files in the `sounds/` folder.)*

* **Pot Reaction:** If a message contains keywords related to pots, vandalism, or theft, the bot reacts with:
  * Custom Link emoji: `<:link:1475252964708057118>`
  * Custom Pot emoji: `<:pot:1475279632512188718>`

* **Cucco Reaction:** Discussing chickens or cuccos triggers a flock of poultry reactions.
  * Chicken emoji: 🐔
  * Custom Link emoji: `<:link:1475252964708057118>`

* **The Golden Goddesses Reaction:** Discussing the Triforce, courage, wisdom, power, or the Golden Goddesses triggers an animated Triforce reaction: `<a:link_triforce:1475284641513607338>`

* **Rare Item Drop:** When a link is fixed and sent via webhook, there is a 5% chance the bot appends the classic item get text to the embedded post:
  * `*Da-da-da-daaa!* 🗝️`

## Setup and Installation

### Prerequisites
* Python 3.8 or higher.
* A Discord Developer Application with a valid Bot Token.
* The **Message Content Intent** enabled in your bot's Developer Portal settings.

### Installation Steps

1. **Clone the repository:**
   git clone <your-repo-url>
   cd LinkBot

2. **Create and activate a virtual environment:**
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate

3. **Install dependencies:**
    pip install -r requirements.txt

4. **Configure your bot token:**
    cp .env.example .env
    # Edit .env and add your Discord bot token
    nano .env
    
5. **Run the bot:**
    python3 main.py

### Bot Permissions Required
Make sure your bot has at least these permissions in Discord:
(others are asked for, but theyre for planned features later.)

    - Read Messages/View Channels
    - Send Messages
    - Manage Messages (to delete the original posts)
    - Manage Webhooks
    - Read Message History

### Troubleshooting
Bot not responding? Ensure the Message Content Intent is enabled in the Discord Developer Portal.
Permission errors? Check that the bot's role actually has the required permissions in your specific server.
Token issues? If the bot fails to log in, regenerate your token in the Discord Developer Portal immediately.

### License
MIT