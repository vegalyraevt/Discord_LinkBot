# LinkBot - Discord Embed Fixer

A lightweight, webhook-powered Discord bot built in Python (`discord.py`) that automatically fixes broken social media embeds by replacing domain names with embed-friendly alternatives.

## Invite me!
[Discord Invite Link](https://discord.com/oauth2/authorize?client_id=1475244291944218715&permissions=2322581411986432&integration_type=0&scope=bot)

<img width="779" height="326" alt="derp-link-meme-7" src="https://github.com/user-attachments/assets/c964ce38-30a7-420b-bb84-a0cea7f67c89" />

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
  * <img width="994" height="832" alt="Screenshot 2026-02-22 225601" src="https://github.com/user-attachments/assets/22e0cdfa-0dd6-4cf7-a20d-d05a80901645" />

* **Direct File Analysis:** Intercepts direct links to files (`.exe`, `.zip`, `.mp4`, etc.) and performs a secure header check to announce the exact file type and size to the channel before anyone clicks it.
  * <img width="940" height="516" alt="Capture" src="https://github.com/user-attachments/assets/fadb7f4a-9ef6-454d-8869-182f81618b04" />


## Zelda Easter Eggs

The bot includes hidden *Legend of Zelda* references that trigger automatically, adding charm without interrupting normal conversations:

* **Direct Ping Response:** When you mention the bot directly with `@Link`, it responds with one of the following:
  * **55% chance:** Iconic and funny quotes from the Zelda games, the 1989 cartoon, and the CD-i spin-offs.
  * **35% chance:** A random image from the `images/` folder.
  * **10% chance:** A random sound from the `sounds/` folder.
  *(Note: To use the media responses, place `.png`, `.jpg`, and `.gif` files in the `images/` folder, and `.mp3`, `.wav`, and `.ogg` files in the `sounds/` folder.)*

  <img width="727" height="452" alt="Screenshot 2026-02-22 225851" src="https://github.com/user-attachments/assets/66cbe57c-905b-42f9-a226-7eb009e49546" />

  <img width="501" height="240" alt="Screenshot 2026-02-22 225953" src="https://github.com/user-attachments/assets/a70b0bca-2d05-4ea3-b14f-5d77a3abfef4" />


* **Pot Reaction:** If a message contains keywords related to pots, vandalism, or theft, the bot reacts with:
  * Custom Link emoji: `<:link:1475252964708057118>`
  * Custom Pot emoji: `<:pot:1475279632512188718>`
    
<img width="313" height="133" alt="Screenshot 2026-02-22 230053" src="https://github.com/user-attachments/assets/9081a076-8800-484a-8750-9c8ae42d0088" />

* **Cucco Reaction:** Discussing chickens or cuccos triggers a flock of poultry reactions.
  * Chicken emoji: 🐔
  * Custom Link emoji: `<:link:1475252964708057118>`
    
<img width="229" height="87" alt="Screenshot 2026-02-22 230204" src="https://github.com/user-attachments/assets/f8c23af4-2e26-46ac-9194-f55b8162d8a3" />

* **The Golden Goddesses Reaction:** Discussing the Triforce, courage, wisdom, power, or the Golden Goddesses triggers an animated Triforce reaction: `<a:link_triforce:1475284641513607338>`

<img width="172" height="76" alt="Screenshot 2026-02-22 230222" src="https://github.com/user-attachments/assets/233cba1d-0fb4-4cb5-96dc-9e8918b1b9fa" />

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
