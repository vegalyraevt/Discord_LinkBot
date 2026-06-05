# VirusTotal API Key Setup Guide

LinkBot integrates with VirusTotal to scan URLs against 70+ security engines. Each Discord server can provide its own API key for privacy and quota management.

## How It Works

1. A server admin sets their API key using `/vtkey set <key>`
2. The key is **encrypted** (Fernet AES-128) before storage on the host machine
3. The key is **never visible** after being set. Not to users, not to the bot host
4. VirusTotal scans use the server's own key and quota
5. Built-in rate limiting protects free tier quotas

## Getting a Free API Key

1. Go to [virustotal.com](https://www.virustotal.com)
2. Sign up for a free account
3. Navigate to your profile's API key section
4. Copy your API key (64+ character string)
5. In Discord, run: `/vtkey set your-key-here`

## Commands

All `/vtkey` commands require **Manage Server** or a manager role.

| Command | Description |
|---------|-------------|
| `/vtkey info` | Setup instructions and info |
| `/vtkey set <key>` | Encrypt and store your API key |
| `/vtkey status` | Check if a key is configured (does not show the key) |
| `/vtkey remove` | Delete your stored key |
| `/vtkey limit <1-500>` | Set hourly scan limit (0 = disable limits for premium) |

## Rate Limiting

### Free Tier (500 lookups/day)
- Default: 20 lookups per hour
- Prevents accidental quota exhaustion
- Configurable via `/vtkey limit`

### Premium / Paid Tiers
- Disable hourly limits completely: `/vtkey limit 0`
- Daily cap: 500 (set in config)
- Contact your VirusTotal account rep for higher tiers

## Security

- **Encryption**: AES-128 via Fernet (`cryptography` library). Encryption key stored in `keyvault.key` (gitignored, auto-generated)
- **Storage**: Encrypted ciphertext in `config/{server_id}.json`
- **Visibility**: Never shown in `/config show`, never echoed in any message
- **Removal**: `/vtkey remove` permanently deletes the encrypted key

## Privacy

Your API key is used **only** for VirusTotal URL lookups triggered by users in your Discord server. It is never shared, sold, or used for any other purpose. The bot host cannot read your plaintext key.

You can request complete removal at any time with `/vtkey remove`.

## Self-Hosting

If you self-host LinkBot and want a single global VT key:

1. Set `VT_LOCAL_MODE=true` in `.env`
2. Set `VIRUSTOTAL_API_KEY=your-key` in `.env`
3. The key will be used for all servers running on that bot instance

This mode is intended for single-server self-hosted deployments.
