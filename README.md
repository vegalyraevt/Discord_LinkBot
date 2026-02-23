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

## � Zelda Easter Eggs

The bot includes hidden *Legend of Zelda* references that trigger automatically, adding charm without interrupting normal conversations:

* **Direct Ping Response:** When you mention the bot directly with `@Link`, it responds with one of the following:
  * **55% chance:** Random text like "HYYAAAAAA! <:link:1475252964708057118>", "Hey! Listen! �", or "It's dangerous to go alone! Take this. ⚔️ <:link:1475252964708057118>"
  * **35% chance:** A random image from the `images/` folder.
  * **10% chance:** A random sound from the `sounds/` folder.
  *(Note: To use the media responses, place `.png`, `.jpg`, and `.gif` files in the `images/` folder, and `.mp3`, `.wav`, and `.ogg` files in the `sounds/` folder.)*

* **Pot Reaction:** If a message contains the keywords `pot`, `pots`, `smash`, `break`, `vase`, `vases`, `jar`, `jars`, `urn`, `urns`, `ceramics`, `pottery`, `link`, `links`, `rupee`, `rupees`, `money`, `burglary`, `theft`, `vandalism`, `vandalize`, `steal`, `stealing`, `thief`, `rob`, `robbery`, `loot`, `looting`, `crime`, `shatter`, `trespass`, `trespassing`, `crash`, `destroy`, `destruction`, `ransack`, or `pillage`, the bot reacts with:
  * Custom Link emoji: `<:link:1475252964708057118>`
  * Custom Pot emoji: `<:pot:1475279632512188718>`

* **Cucco Reaction:** If a message contains the keywords `cucco`, `cuccos`, `cuckoo`, `cuckoos`, `chicken`, `chickens`, `poultry`, `peck`, `pecking`, `flock`, `kakariko`, `rooster`, `cluck`, `feathers`, `swarm`, or `revenge`, the bot reacts with:
  * Chicken emoji: �
  * Custom Link emoji: `<:link:1475252964708057118>`

* **The Golden Goddesses Reaction:** Discussing the Triforce, courage, wisdom, power, or the Golden Goddesses triggers an animated Triforce reaction: `<a:link_triforce:1475284641513607338>`

* **Rare Item Drop:** When a link is fixed and sent via webhook, there is a 5% chance the bot appends the classic item get text to the embedded post:
  * `*Da-da-da-daaa!* �️`

## Setup and Installation

### Prerequisites
* Python 3.8 or higher.
* A Discord Developer Application with a valid Bot Token.
* The **Message Content Intent** enabled in your bot's Developer Portal settings.

### Installation Steps

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd LinkBot
