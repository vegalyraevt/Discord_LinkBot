"""
permissions.py - Role-based access control for management commands.

A user is considered a "manager" if they:
  1. Have the Discord 'Manage Server' permission, OR
  2. Hold a role listed in the server config's manager_roles

Server owners (guild.owner) always have full access.
"""

import discord
from typing import Dict, Any


def is_manager(
    member: discord.Member,
    config: Dict[str, Any],
    guild: discord.Guild,
) -> bool:
    """
    Check if a member has permission to manage bot settings.
    
    Args:
        member: The Discord member to check.
        config: The server's config dict.
        guild: The guild the member belongs to.
    
    Returns:
        True if the member can manage the bot.
    """
    # Server owner always has full access
    if member.id == guild.owner_id:
        return True

    # Check Discord native Manage Server permission
    if member.guild_permissions.manage_guild:
        return True

    # Check configured manager roles
    manager_roles = config.get("manager_roles", [])
    if manager_roles:
        member_role_ids = {role.id for role in member.roles}
        if any(role_id in member_role_ids for role_id in manager_roles):
            return True

    return False


def is_trusted(
    member: discord.Member,
    config: Dict[str, Any],
) -> bool:
    """
    Check if a member has a trusted role (bypasses all safety checks).
    
    Args:
        member: The Discord member to check.
        config: The server's config dict.
    
    Returns:
        True if the member has a trusted role.
    """
    trusted_roles = config.get("trusted_roles", [])
    if not trusted_roles:
        return False

    member_role_ids = {role.id for role in member.roles}
    return any(role_id in member_role_ids for role_id in trusted_roles)
