"""
moderation.py - Server management features.

Phase 8c: Trusted role bypass - roles that skip ALL safety checks
Phase 8d: Rate limiting - per-user message tracking
Phase 8e: Duplicate link detection - catch same URL in recent messages
Phase 8f: Logging channel - audit log for bot actions
Phase 8g: Command cooldown - per-user command rate limiting

All features read from per-server config and are toggleable.
"""

import re
import time
from collections import defaultdict, deque
from typing import Dict, Optional

import discord
import stats


# ===== Phase 8d: Rate Limiting =====

# Per-channel message tracking: channel_id -> deque of (user_id, timestamp)
_rate_limit_cache: Dict[int, deque] = defaultdict(lambda: deque(maxlen=100))


def check_rate_limit(message: discord.Message, config: dict) -> Optional[str]:
    """
    Check if a user has exceeded the rate limit for this channel.
    Returns a warning message string if exceeded, None if OK.
    """
    rl_config = config.get("ratelimit", {})
    if not rl_config.get("enabled", True):
        return None

    max_msgs = rl_config.get("messages_per_window", 5)
    window = rl_config.get("window_seconds", 10)

    channel_id = message.channel.id
    user_id = message.author.id
    now = time.time()

    # Clean old entries
    entries = _rate_limit_cache[channel_id]
    entries = deque(
        (uid, ts) for uid, ts in entries if now - ts < window
    )
    _rate_limit_cache[channel_id] = entries

    # Count user's recent messages
    user_count = sum(1 for uid, ts in entries if uid == user_id)

    if user_count >= max_msgs:
        return (
            f"⚠️ {message.author.mention}, you're sending messages too quickly! "
            f"Please wait {window} seconds between messages."
        )

    # Add this message
    entries.append((user_id, now))
    return None


# ===== Phase 8e: Duplicate Link Detection =====

# Per-channel recent URL cache: channel_id -> deque of (url, timestamp, message_id)
_duplicate_cache: Dict[int, deque] = defaultdict(lambda: deque(maxlen=100))


async def check_duplicate_links(message: discord.Message, config: dict) -> Optional[str]:
    """
    Check if any URLs in this message were recently posted in the same channel.
    Returns a warning message string if duplicate found, None if OK.
    """
    window = config.get("duplicate_link_window", 5)
    if window <= 0:
        return None

    channel_id = message.channel.id
    entries = _duplicate_cache[channel_id]
    now = time.time()

    # Extract URLs from message
    urls = re.findall(r'https?://[^\s\\)>]+', message.content)
    if not urls:
        # Still record this message for ordering (no URLs, but counts toward window)
        entries.append(("", now, message.id))
        # Trim to window size
        while len(entries) > window:
            entries.popleft()
        return None

    # Check each URL against recent cache
    cached_urls = {url for url, ts, mid in entries if url}
    for url in urls:
        # Strip trailing punctuation for comparison
        clean = url.rstrip('.,;:!?)\]}')
        if clean in cached_urls:
            await stats.increment("duplicate_links_caught")
            return (
                f"🔄 {message.author.mention}, this link was recently posted "
                f"in this channel. No need to repost!"
            )

    # Add all URLs from this message
    for url in urls:
        entries.append((url.rstrip('.,;:!?)\]}'), now, message.id))

    # Trim to window size
    while len(entries) > window:
        entries.popleft()

    return None


# ===== Phase 8f: Logging Channel =====

async def log_action(
    message: discord.Message,
    config: dict,
    action_type: str,
    details: str = "",
    color: discord.Color = discord.Color.dark_theme(),
) -> None:
    """
    Log a bot action to the server's configured logging channel.
    
    Args:
        message: The Discord message that triggered the action.
        config: Server config dict.
        action_type: Short label (e.g. "Malicious Link Deleted", "Safety Card Shown").
        details: Additional details to include.
        color: Embed color for the log entry.
    """
    logging_channel_id = config.get("logging_channel")
    if not logging_channel_id or not message.guild:
        return

    try:
        log_channel = message.guild.get_channel(int(logging_channel_id))
        if not log_channel:
            return

        embed = discord.Embed(
            title=f"📋 {action_type}",
            description=(
                f"**User:** {message.author.mention} (`{message.author.id}`)\n"
                f"**Channel:** {message.channel.mention}\n"
                f"**Message ID:** {message.id}\n"
                + (f"\n{details}" if details else "")
            ),
            color=color,
            timestamp=discord.utils.utcnow(),
        )
        if message.content:
            content_preview = message.content[:500] + ("..." if len(message.content) > 500 else "")
            embed.add_field(name="Content", value=content_preview, inline=False)

        await log_channel.send(embed=embed)
    except (discord.Forbidden, discord.HTTPException):
        pass


# ===== Phase 8g: Command Cooldown =====

# Per-user command cooldown tracking: user_id -> last_command_timestamp
_command_cooldowns: Dict[int, float] = {}


def check_command_cooldown(user_id: int, config: dict) -> bool:
    """
    Check if a user is on command cooldown.
    Returns True if the user can use a command (not on cooldown).
    Records the command timestamp on success.
    """
    cooldown = config.get("command_cooldown_seconds", 3)
    if cooldown <= 0:
        return True

    now = time.time()
    last_used = _command_cooldowns.get(user_id, 0)

    if now - last_used < cooldown:
        return False  # On cooldown

    _command_cooldowns[user_id] = now
    return True
