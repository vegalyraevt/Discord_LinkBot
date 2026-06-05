# Contributing to LinkBot

Thanks for your interest in LinkBot! I created this project because I wanted a link safety bot to exist and couldn't find one I liked, not because I'm an expert in security. Discord servers deserve better tools for navigating a web built around obfuscation and tracking and I'm just doing my best to take steps towards that.

## Philosophy

LinkBot aims to be:
- **Safe** Protecting users from phishing, malware, and tracking
- **Helpful** Enriching links with useful previews and context
- **Fun** Adding personality without being intrusive
- **Respectful** Configurable per-server, never spamming

Features should serve these goals. If a feature makes servers less safe or more annoying, it doesn't belong.

## I'm Looking For

### 🔒 Security Professionals
If you have experience with web security, phishing detection, URL analysis, or Discord bot security I would love your review of the implementations here. The bot processes untrusted URLs from user messages, and I want to ensure it does so safely. I also want to expand its capabilities but lack the skills needed to do really deep security checks for users.

### 🐛 Bug Reports
Found something broken? Please [open an issue](https://github.com/vegalyraevt/LinkBot/issues/new?template=bug_report.md) with:
- What you expected to happen
- What actually happened
- Steps to reproduce if you have them
- Discord.py version and Python version. (If you hosted it yourself.)
- Screenshots welcome!

### 💡 Feature Ideas
Have an idea? [Open a feature request](https://github.com/vegalyraevt/LinkBot/issues/new?template=feature_request.md). I can't promise everything gets built (solo dev, limited time), but I will read every suggestion.

### 🛠️ Pull Requests
PRs are welcome! Please:
1. Discuss larger changes in an issue first
2. Keep files modular aim for under 500 lines per file
3. Follow existing code patterns (async/await, aiohttp, discord.py)
4. Use `os.getenv()` for any API keys, PLEASE never hardcode credentials
5. Ensure all HTTP calls have timeouts (`aiohttp.ClientTimeout`)
6. Validate with `python -m ast` before submitting

## Code Style

- Python 3.10+ compatible
- Type hints encouraged but not required
- Docstrings on public functions
- Max ~500 lines per module split into sub-packages when files grow
- All external APIs must be free-tier compatible

## AI Assistance Disclosure

This project was developed with assistance from AI tools:
- **Deepseek** Feature planning and implementation help
- **Qwen** (via local LLM) some code review and debugging
- **Roo** IDE assistance and refactoring
- **Claude** Research into tools/api to impliment

These tools helped accelerate development but all code has been reviewed and tested by a human. If you notice patterns that could be improved, please flag them. AI usage is allowed for contributing, but within reason. All code should be human readable and you should be able to understand the code you have written fully on your own after making it. If you can not contribute to a area at all without AI I ask that you please refrian from working on that area as that defeats the puropse of me getting help. If I wanted just trust the AI to do it fully I would prompt it myself. AI code responsibly please.

## Questions?

Feel free to open a discussion. I'm a solo developer doing this in my spare time, so responses will likely not be instant, but I care about this project and will get back to you.

---

*LinkBot exists because someone needed to build it. Thanks for helping make it better.*
