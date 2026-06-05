"""
channel_filter.py - Channel-based filtering for bot activity.

Supports three modes (configurable per server):
  1. Disabled channels: Bot ignores these channels entirely.
  2. Opt-in mode: If enabled_channels is non-empty, bot ONLY runs there.
  3. Command channels: Slash commands are restricted to these channels.

All checks use channel IDs and server config.
"""

import discord
from typing import Dict, Any, Optional


def is_channel_allowed(
    message: discord.Message,
    config: Dict[str, Any],
) -> bool:
    """
    Check if the bot should process messages in this channel.
    
    Args:
        message: The Discord message to check.
        config: The server's config dict.
    
    Returns:
        True if the bot should process this channel.
    """
    if not message.guild:
        return True  # DMs are always allowed

    channel_id = message.channel.id

    # Check disabled channels first
    disabled = config.get("disabled_channels", [])
    if channel_id in disabled:
        return False

    # Check opt-in mode
    enabled = config.get("enabled_channels", [])
    if enabled and channel_id not in enabled:
        return False

    return True


def is_command_channel_allowed(
    channel_id: int,
    config: Dict[str, Any],
) -> bool:
    """
    Check if slash commands can be used in this channel.
    
    Args:
        channel_id: The channel ID where the command was invoked.
        config: The server's config dict.
    
    Returns:
        True if commands are allowed in this channel.
    """
    command_channels = config.get("command_channels", [])
    if not command_channels:
        return True  # Not restricted

    return channel_id in command_channels
