# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in LinkBot, please report it responsibly.

**Do not open a public issue.** Instead, contact the maintainer directly:

- GitHub: Open a security advisory via the [Security tab](https://github.com/vegalyraevt/LinkBot/security)
- Discord: Reach out to `vegalyrae`

Please include:
- A clear description of the vulnerability
- Steps to reproduce
- Affected component(s)
- Potential impact
- Feel free to include a solution if you are qualified to do so and want to. I always welcome experienced help.

I will aim to acknowledge your report within 72 hours and aim to provide a fix within 14 days, depending on severity. Please if its a major issue of security come to me first so we can fix it before disclosing it to prevent explotation. We will list the issue once it is fixed and suspend the bots actions if needed till then.

## Scope

LinkBot processes untrusted user content (URLs from Discord messages). Security-relevant areas include:

| Area | Risk |
|------|------|
| **URL handling** | The bot fetches and follows URLs from user messages. SSRF, redirect loops, or accessing internal services |
| **HTML parsing** | BeautifulSoup parses Amazon product pages. Malicious HTML payloads |
| **API integrations** | API keys (VirusTotal, OMDb) must never be logged or exposed |
| **Config system** | Per-server JSON configs in `config/`. Path traversal or injection via config values |
| **Webhook creation** | Bot creates webhooks in channels. Permission escalation risks |
| **User content in embeds** | Message content, usernames, and URLs appear in Discord embeds |

## What's Out of Scope

- Denial of service via rate limit exhaustion (free API tiers have hard caps)
- Issues in Discord.py itself (report those [upstream](https://github.com/Rapptz/discord.py))
- Social engineering or phishing of bot administrators
- Config file tampering by server administrators (they own the files)

## Safe Harbor

If you research security in good faith and follow this policy, I will:
- Keep your report confidential
- Credit you in the fix (unless you prefer anonymity)
- Work with you to promptly understand and resolve the issue.

## Dependencies

LinkBot depends on these packages (see `requirements.txt`):
- `discord.py` - Discord API wrapper
- `aiohttp` - Async HTTP client
- `beautifulsoup4` - HTML parsing (Amazon)
- `python-dotenv` - Environment variable loading

Keep them updated. Dependabot or similar tooling is recommended for monitoring CVEs.
