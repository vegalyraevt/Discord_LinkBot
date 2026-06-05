"""
blacklist.py - Per-server domain blacklisting and whitelisting.

Two modes (toggleable per server):
  - Blacklist mode: Block listed domains.
  - Whitelist mode: Block ALL domains except whitelisted ones.

Violation actions: delete message, timeout user, send ephemeral reply, ping mod channel.
"""

import discord
import asyncio
from typing import Dict, Any, Optional, Literal
from urllib.parse import urlparse

import stats


async def check_url(
    message: discord.Message,
    config: Dict[str, Any],
    raw_url: str,
) -> Optional[bool]:
    """
    Check if a URL's domain is blocked by blacklist or not in whitelist.
    
    Returns:
        None if the URL is allowed.
        True if the URL was blocked and handled.
    """
    hostname = urlparse(raw_url).hostname
    if not hostname:
        return None

    hostname = hostname.lower().removeprefix("www.")

    mode = config.get("blacklist_mode", "blacklist")

    if mode == "whitelist":
        whitelist_domains = config.get("whitelist", {}).get("domains", {})
        if hostname not in whitelist_domains:
            await _apply_action(message, config, hostname, "whitelist")
            return True
        return None

    # Blacklist mode
    blacklist_domains = config.get("blacklist", {}).get("domains", {})
    if hostname in blacklist_domains:
        await _apply_action(message, config, hostname, "blacklist")
        return True

    return None


async def _apply_action(
    message: discord.Message,
    config: Dict[str, Any],
    domain: str,
    mode: str,
) -> None:
    """Apply the configured action for a blocked domain."""
    bl_conf = config.get("blacklist", {})
    action = bl_conf.get("default_action", "delete")
    custom_msg = bl_conf.get(
        "custom_message",
        "Your link was removed because that domain is not allowed here."
    )
    timeout_duration = bl_conf.get("timeout_duration", 5)
    notification_channel_id = config.get("notification_channel")

    # Always delete the message
    try:
        await message.delete()
        await stats.increment("messages_deleted")
    except (discord.Forbidden, discord.NotFound, discord.HTTPException):
        pass

    if mode == "whitelist":
        await stats.increment("whitelist_blocks")
    else:
        await stats.increment("blacklist_deletions")

    # Send ephemeral-style reply (actually a channel message since
    # we can't DM effectively after deleting; use a temp message or DM)
    try:
        await message.channel.send(
            f"⚠️ {message.author.mention}: {custom_msg}",
            delete_after=10
        )
    except (discord.Forbidden, discord.HTTPException):
        pass

    # Timeout the user if configured
    if "timeout" in action and message.guild:
        try:
            await message.author.timeout(
                discord.utils.utcnow() + asyncio.timedelta(minutes=timeout_duration),
                reason=f"Posted link to blocked domain: {domain}"
            )
            await stats.increment("timeouts_issued")
        except (discord.Forbidden, discord.HTTPException):
            pass

    # Notify mod channel
    if "notify" in action and notification_channel_id:
        try:
            notif_channel = message.guild.get_channel(int(notification_channel_id))
            if notif_channel:
                await notif_channel.send(
                    f"🛡️ **Link blocked** in {message.channel.mention}\n"
                    f"User: {message.author.mention} (`{message.author.id}`)\n"
                    f"Domain: `{domain}`\n"
                    f"Mode: {mode}"
                )
        except (discord.Forbidden, discord.HTTPException):
            pass
