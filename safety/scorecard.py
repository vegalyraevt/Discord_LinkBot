"""
safety.scorecard.py - Composite safety score for URLs.

Scores each link on a 0-10 scale based on multiple risk factors.
The score card only auto-displays when the total meets or exceeds
the server's configured threshold (default: 6).

Individual checks are fast (regex/TLD matching); heavy checks
(RDAP, VirusTotal) are referenced from results collected earlier
in the on_message pipeline.

Scoring weights:
  +10  Phishing domain (SinkingYachts) - instant delete, card not shown
  +8   VirusTotal >= 3 engines flagged
  +5   Domain registered < 30 days ago
  +4   Suspicious TLD (.tk, .xyz, etc.)
  +3   Plain HTTP on HTTPS-capable site
  +3   Redirect chain >= 3 hops
  +2   VirusTotal 1-2 engines flagged
  +1   Known URL shortener domain
  +1   Non-standard port in URL
"""

import re
from urllib.parse import urlparse
from typing import Dict, Optional, List, Tuple

import discord
import stats


# Known URL shortener domains (for scoring)
SHORTENER_DOMAINS = {
    'bit.ly', 'tinyurl.com', 't.co', 'goo.gl', 'ow.ly', 'is.gd', 'buff.ly',
    'j.mp', 'cutt.ly', 'rb.gy', 'shrtco.de', 'v.gd', 'bl.ink', 't2m.io',
    'qr.ae', 'snip.ly', 'clk.im', 'rebrand.ly', 'short.gy', 'cutt.us',
    'soo.gd', 's.id', 'adf.ly', 'lnkd.in', 'amzn.to', 'wp.me',
    't.me', 'b.link', 'tiny.cc', 'shorturl.at', 'cli.re'
}

# Suspicious TLDs
SUSPICIOUS_TLDS = {
    '.tk', '.ml', '.ga', '.cf', '.gq',
    '.xyz', '.top', '.click', '.work',
    '.bar', '.rest', '.hair', '.makeup',
    '.cyou', '.cfd', '.sbs', '.icu',
}

# Non-standard ports that raise suspicion
SUSPICIOUS_PORTS = {21, 22, 23, 25, 445, 1433, 3306, 3389, 4444, 5555, 5900, 6379, 8080, 8443, 8888, 9000}


def calculate_score(url: str, vt_result: Optional[Dict] = None, domain_age_days: Optional[int] = None, redirect_hops: int = 0) -> Tuple[int, List[str]]:
    """
    Calculate a safety score for a URL (0-10, higher = more suspicious).
    Returns (score, list_of_reasons).
    """
    score = 0
    reasons: List[str] = []

    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower().removeprefix("www.")
    tld = "." + hostname.rsplit(".", 1)[-1] if "." in hostname else ""

    # +4: Suspicious TLD
    if tld in SUSPICIOUS_TLDS:
        score += 4
        reasons.append(f"Suspicious TLD (`{tld}`)")

    # +3: Plain HTTP on a known-HTTPS site
    if url.startswith("http://") and not url.startswith("http://localhost") and not url.startswith("http://192.168.") and not url.startswith("http://127.0.0.1"):
        if hostname and (hostname.endswith('.com') or hostname.endswith('.org') or hostname.endswith('.net') or hostname.endswith('.io') or hostname.endswith('.dev') or hostname.endswith('.app')):
            score += 3
            reasons.append("Unencrypted HTTP connection")

    # +3: Redirect chain >= 3 hops
    if redirect_hops >= 3:
        score += 3
        reasons.append(f"Redirect chain ({redirect_hops} hops)")

    # +1: Known URL shortener
    if hostname in SHORTENER_DOMAINS:
        score += 1
        reasons.append("URL shortener detected")

    # +1: Non-standard port
    if parsed.port and parsed.port in SUSPICIOUS_PORTS:
        score += 1
        reasons.append(f"Non-standard port (:{{parsed.port}})")

    # +5: Domain registered < 30 days ago
    if domain_age_days is not None and domain_age_days < 30:
        score += 5
        reasons.append(f"Domain only {domain_age_days} day(s) old")

    # VirusTotal results
    if vt_result:
        malicious = vt_result.get("malicious", 0)
        if malicious >= 3:
            score += 8
            reasons.append(f"{malicious} VT engines flagged as malicious")
        elif malicious >= 1:
            score += 2
            reasons.append(f"{malicious} VT engine(s) flagged")

    return min(score, 10), reasons


def build_score_embed(url: str, score: int, reasons: List[str], threshold: int = 6) -> discord.Embed:
    """
    Build a Discord embed for the safety score card.
    """
    if score >= 8:
        color = discord.Color.red()
        verdict = "🔴 High Risk"
    elif score >= threshold:
        color = discord.Color.orange()
        verdict = "🟠 Caution Advised"
    elif score >= 3:
        color = discord.Color.yellow()
        verdict = "🟡 Low Risk"
    else:
        color = discord.Color.green()
        verdict = "🟢 Appears Safe"

    bar = "█" * score + "░" * (10 - score)

    description_parts = [
        f"**Score:** {score}/10  |  {verdict}",
        f"`[{bar}]`",
    ]

    if reasons:
        description_parts.append("\n**Risk Factors:**")
        for reason in reasons:
            description_parts.append(f"• {reason}")
    else:
        description_parts.append("\n✅ No risk factors detected.")

    description_parts.append(f"\n🔗 `{url}`")
    description_parts.append(f"\n*Threshold for auto-warning: {threshold}/10*")

    embed = discord.Embed(
        title="🛡️ LinkBot Safety Score",
        description="\n".join(description_parts),
        color=color,
    )
    embed.set_footer(text="LinkBot Safety • /scan for manual checks")

    return embed


async def maybe_show_scorecard(message: discord.Message, config: dict = None) -> None:
    """
    Calculate safety scores for URLs in a message and show the card
    ONLY if the score meets or exceeds the configured threshold.
    Silently skips clean URLs.

    If a notification_channel is configured for the server, a severity-level
    notification is also sent there (for mod visibility).
    If a logging_channel is configured, all score-triggering events are logged.
    """
    if config is None:
        config = {}

    threshold = config.get("safety_score_threshold", 6)
    notification_channel_id = config.get("notification_channel")
    logging_channel_id = config.get("logging_channel")

    scored_domains = set()
    for raw_url in re.findall(r'https?://[^\s\)\]>]+', message.content):
        hostname = urlparse(raw_url).hostname
        if not hostname:
            continue
        hostname_clean = hostname.lower().removeprefix("www.")
        if hostname_clean in scored_domains:
            continue
        scored_domains.add(hostname_clean)

        # Calculate score (synchronous checks only for auto-trigger)
        score, reasons = calculate_score(raw_url)

        # Only show if score meets threshold
        if score >= threshold:
            # 1. Reply in the current channel
            embed = build_score_embed(raw_url, score, reasons, threshold)
            await message.channel.send(embed=embed)
            await stats.increment("safety_cards_shown")

            # 2. Notify mod channel if configured (for scores >= 8 or notification_channel set)
            if notification_channel_id and message.guild:
                try:
                    notif_channel = message.guild.get_channel(int(notification_channel_id))
                    if notif_channel:
                        notif_embed = discord.Embed(
                            title=f"🛡️ Safety Alert - Score {score}/10",
                            description=(
                                f"**User:** {message.author.mention} (`{message.author.id}`)\n"
                                f"**Channel:** {message.channel.mention}\n"
                                f"**Score:** {score}/10\n"
                                f"**URL:** `{raw_url}`\n\n"
                                + ("\n".join(f"• {r}" for r in reasons) if reasons else "No specific risks flagged.")
                            ),
                            color=discord.Color.red() if score >= 8 else discord.Color.orange(),
                        )
                        await notif_channel.send(embed=notif_embed)
                except (discord.Forbidden, discord.HTTPException):
                    pass

            # 3. Log to logging channel if configured
            if logging_channel_id and message.guild:
                try:
                    log_channel = message.guild.get_channel(int(logging_channel_id))
                    if log_channel and log_channel.id != notification_channel_id:
                        log_embed = discord.Embed(
                            title="📋 Safety Score Log",
                            description=(
                                f"User `{message.author}` ({message.author.id}) "
                                f"in {message.channel.mention} posted a link scoring {score}/10\n"
                                f"URL: `{raw_url}`\n"
                                f"Threshold: {threshold}/10"
                            ),
                            color=discord.Color.dark_theme(),
                        )
                        await log_channel.send(embed=log_embed)
                except (discord.Forbidden, discord.HTTPException):
                    pass
