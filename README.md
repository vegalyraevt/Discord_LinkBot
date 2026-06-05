# LinkBot - Discord Link Safety & Embed Fixer

[![Invite LinkBot](https://img.shields.io/badge/Invite-LinkBot-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.com/oauth2/authorize?client_id=1475244291944218715&permissions=2322581411986432&integration_type=0&scope=bot)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-F16061?style=for-the-badge&logo=ko-fi&logoColor=white)](https://ko-fi.com/vegalyrae)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

A modular, $0-cost Discord bot that makes links safer, smarter, and more fun - with a Legend of Zelda theme.

> *In a society built around obfuscation and tracking, LinkBot helps make Discord servers just a bit more safe, private, and enjoyable without being intrusive.*

<img width="779" height="326" alt="derp-link-meme-7" src="https://github.com/user-attachments/assets/c964ce38-30a7-420b-bb84-a0cea7f67c89" />

---

## What It Does

| 🛡️ Safety | 📋 Link Enrichment | ⚙️ Server Management | 🎮 Fun |
|------------|-------------------|-----------------------|--------|
| Phishing detection (SinkingYachts) | YouTube/Twitch info embeds | Per-server JSON config | Zelda Easter eggs |
| VirusTotal scanning (70+ engines) | Steam game deals & pricing | Domain blacklist/whitelist | Keyword reactions |
| Suspicious TLD detection (.tk, .xyz, etc.) | Amazon product previews | Rate limiting & spam protection | Pot smashing animations |
| HTTP downgrade warnings | IMDb movie details | Duplicate link detection | Cucco swarm reactions |
| Domain age check (RDAP) | Wikipedia summaries | Trusted role bypass | Triforce reactions |
| Executable file danger alerts | GitHub repo/code previews | Notification & audit channels | Rare item drops |
| Redirect chain inspection | Music link aggregation (Odesli) | Command cooldowns | 5% Rickroll chance |
| Safety score card (0-10) | Wayback Machine archiving | NSFW content warnings | |
| URL unshortening | Academic papers (DOI, arXiv) | Manager role delegation | |
| | npm / PyPI package info | Disabled/opt-in channels | |
| | Stack Overflow question previews | | |
| | Hacker News, Dev.to, Bluesky | | |

---

## Slash Commands

### 🔍 Everyone
| Command | Description |
|---------|-------------|
| `/scan <url>` | Full safety scan with VirusTotal |
| `/safety <url>` | Quick safety score check |
| `/unshorten <url>` | Expand shortened URLs (show all hops) |
| `/archive <url>` | Submit to Wayback Machine |
| `/whois <domain>` | Domain registration lookup (configurable) |
| `/stats` | Global bot usage statistics |
| `/help` | Feature overview & command list |
| `/config show` | View current server settings |

### ⚙️ Management (Manage Server or manager role required)
| Command | Description |
|---------|-------------|
| `/setup` | Interactive setup wizard |
| `/config toggle <feature>` | Enable/disable any feature |
| `/config threshold <1-10>` | Set safety alert sensitivity |
| `/config notify set #channel` | Set mod notification channel |
| `/config log set #channel` | Set audit log channel |
| `/config manager add @role` | Delegate management to a role |
| `/blacklist add/remove/list <domain>` | Block unwanted domains |
| `/whitelist add/remove/list <domain>` | Allow-only mode |
| `/trusted add/remove/list @role` | Safety bypass roles |

---

## Supported Embed-Fix Platforms

LinkBot detects links from these platforms and replaces them with embed-friendly proxies, then reposts via webhook - perfectly impersonating the original author:

| Platform | Proxy | Notes |
|----------|-------|-------|
| Twitter / X | `fixupx.com` | Supports `.translate.spanish` suffix |
| TikTok | `tnktok.com` | |
| Instagram | `uuinstagram.com` | Backup: `gginstagram.com`, `d.vxinstagram.com` |
| Reddit | `rxddit.com` | |
| Pixiv | `phixiv.net` | Supports `.translate.japanese` suffix |
| Bluesky | `bskyx.app` | |
| Threads | `vxthreads.net` | |

YouTube Shorts are automatically converted to regular `youtube.com/watch?v=` URLs.

---

## How It Works - 15-Stage Pipeline

Every message runs through this pipeline:

```
Channel Filter → Rate Limiting → Duplicate Check → Trusted Bypass
→ Blacklist/Whitelist → Unshorten → Phishing Check → File Inspection
→ Suspicious TLD → HTTP Downgrade → Domain Age → VirusTotal
→ Safety Score Card → Enrichment → Tracking Strip → NSFW → Easter Eggs
→ Embed Fixer (webhook repost, delete original)
```

---

## Quick Start

### Prerequisites
- Python 3.10+
- Discord bot token with **Message Content Intent** enabled
- (Optional) [VirusTotal API key](https://virustotal.com) (free, 500 req/day)
- (Optional) [OMDb API key](https://omdbapi.com) (free, 1000/day)

### Installation

```bash
git clone https://github.com/vegalyraevt/LinkBot.git
cd LinkBot
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your DISCORD_BOT_TOKEN
python main.py
```

**Bot Permissions Required:** Read Messages, Send Messages, Manage Messages, Manage Webhooks, Read Message History, Timeout Members (optional)

---

## Project Structure

```
linkbot/
├── main.py                    # Discord Bot + 15-stage message router
├── commands.py                # 12 slash command definitions
├── moderation.py              # Rate limiting, duplicates, logging, cooldowns
├── config_manager.py          # Per-server JSON config (config/{id}.json)
├── permissions.py             # RBAC (owner / Manage Server / manager roles)
├── stats.py                   # Global usage tracker (stats.json)
├── blacklist.py               # Domain blacklist/whitelist enforcement
├── channel_filter.py          # Channel allow/deny/command restriction
├── embeds.py                  # Link fixer, tracking stripper, NSFW detection
├── easter_eggs.py             # Zelda responses, reactions, rare drops
├── safety/
│   ├── __init__.py            # 7 safety check functions
│   ├── rdap.py                # Domain age lookup (free RDAP)
│   ├── virustotal.py          # VirusTotal API integration
│   └── scorecard.py           # 0-10 composite safety scoring
├── enrichment/
│   ├── __init__.py            # Router + music + Wikipedia + Discord quotes
│   ├── github.py              # GitHub blob/repo/user previews
│   ├── storefronts.py         # Steam, Amazon, IMDb
│   ├── multimedia.py          # YouTube, Twitch (oEmbed)
│   ├── academic.py            # DOI, arXiv, npm, PyPI, Stack Overflow, Gist
│   ├── social.py              # Hacker News, Dev.to, Bluesky
│   └── archive.py             # Wayback Machine auto-snapshot
├── config/
│   └── defaults.json          # Global defaults (30+ settings)
├── requirements.txt
├── README.md
├── CONTRIBUTING.md
└── SECURITY.md
```

---

## Easter Eggs

The bot includes hidden *Legend of Zelda* references that trigger automatically, adding charm without interrupting normal conversations:

### Direct Ping Response
Mention the bot with `@LinkBot` for one of:
- **55% chance:** Iconic quotes from Zelda games, the 1989 cartoon, and CD-i spin-offs
- **35% chance:** A random image from the `images/` folder
- **10% chance:** A random sound from the `sounds/` folder
- **5% chance (on top):** Special Youtube Video! 

> **Setting up media responses:** Create two folders in the bot root directory: `images/` (accepts .png, .jpg, .jpeg, .gif) and `sounds/` (accepts .mp3, .wav, .ogg). These folders are gitignored. The bot picks randomly from whatever you place there. No files = text responses only.

<img width="727" height="452" alt="Screenshot 2026-02-22 225851" src="https://github.com/user-attachments/assets/66cbe57c-905b-42f9-a226-7eb009e49546" />

<img width="501" height="240" alt="Screenshot 2026-02-22 225953" src="https://github.com/user-attachments/assets/a70b0bca-2d05-4ea3-b14f-5d77a3abfef4" />

### Pot Reaction
Keywords like *pot, smash, vase, burglary, loot, destroy* trigger custom Link + Pot emoji reactions.

<img width="313" height="133" alt="Screenshot 2026-02-22 230053" src="https://github.com/user-attachments/assets/9081a076-8800-484a-8750-9c8ae42d0088" />

### Cucco Reaction
Keywords like *cucco, chicken, peck, flock, revenge* trigger chicken + Link emoji reactions.

<img width="229" height="87" alt="Screenshot 2026-02-22 230204" src="https://github.com/user-attachments/assets/f8c23af4-2e26-46ac-9194-f55b8162d8a3" />

### Triforce Reaction
Keywords like *wisdom, courage, power, triforce, goddess* trigger an animated Triforce emoji.

<img width="172" height="76" alt="Screenshot 2026-02-22 230222" src="https://github.com/user-attachments/assets/233cba1d-0fb4-4cb5-96dc-9e8918b1b9fa" />

### Rare Item Drop
When a link is fixed and reposted via webhook, there's a 5% chance of:
> *Da-da-da-daaa!* 🗝️

---

## Troubleshooting

- **Bot not responding?** Ensure **Message Content Intent** is enabled in the Discord Developer Portal.
- **Permission errors?** Verify the bot's role has the required permissions in your server.
- **Token issues?** Regenerate your token in the Discord Developer Portal.
- **Slash commands not appearing?** Wait up to 1 hour for Discord to cache, or kick + re-invite the bot to force a refresh.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines. Security professionals are especially welcome to review implementations and suggest improvements.

---

## Security

See [SECURITY.md](SECURITY.md) for vulnerability reporting and safe harbor.

---

## Disclaimer

The Legend of Zelda, Link, and all related properties are trademarks of Nintendo Co., Ltd. This project is not affiliated with, endorsed by, or sponsored by Nintendo. All Zelda-related references are used as fan tribute only in a free, non-commercial project.

---

## License

MIT

---

<sub>This project was developed by me, a solo developer who wanted this project to exist not because I'm an expert in security, but because Discord servers deserve better link safety. Also note AI tools (Deepseek, Qwen via local LLM, and Cursor) were used to assist with some feature implementations and debugging.</sub>
