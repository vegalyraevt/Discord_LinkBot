"""
main.py - LinkBot v2 routing.
"""

import os

import discord
from discord.ext import commands as ext_commands
from dotenv import load_dotenv

import config_manager
import permissions
import stats
import channel_filter
import blacklist
import safety
import enrichment
import embeds
import easter_eggs
import moderation
import commands as bot_commands

load_dotenv()

# Debug logging: only log full message content when explicitly enabled
DEBUG_LOG = os.getenv("LINKBOT_DEBUG", "").lower() == "true"

if DEBUG_LOG:
    print("DEBUG LOGGING ENABLED - message content will be printed")

intents = discord.Intents.default()
intents.message_content = True
bot = ext_commands.Bot(command_prefix="lb!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    bot_commands.register_commands(bot.tree)
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    await stats.start_stats()


@bot.event
async def on_guild_join(guild: discord.Guild):
    welcome_channel = None
    for name in ['general', 'welcome', 'chat', 'main', 'lobby']:
        for channel in guild.text_channels:
            if channel.name.lower() == name and channel.permissions_for(guild.me).send_messages:
                welcome_channel = channel
                break
        if welcome_channel:
            break
    if not welcome_channel:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                welcome_channel = channel
                break
    if welcome_channel:
        embed = discord.Embed(
            title="HYYAAAAAA! LinkBot has arrived!",
            description=(
                "Thanks for adding me to your server!\n"
                "• `/setup` - Interactive setup wizard\n"
                "• `/help` - All commands\n"
                "• `/config show` - View settings\n\n"
                "Server owners and **Manage Server** members can configure all features."
            ),
            color=discord.Color.green()
        )
        await welcome_channel.send(embed=embed)


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    await bot.process_commands(message)
    if DEBUG_LOG:
        print(f"Message from {message.author}: {message.content}")

    config = None
    if message.guild:
        config = config_manager.load_config(message.guild.id)
        if not channel_filter.is_channel_allowed(message, config):
            return
        rate_warning = moderation.check_rate_limit(message, config)
        if rate_warning:
            await message.channel.send(rate_warning, delete_after=10)
            await stats.increment("rate_limits_enforced")
            return
        dup_warning = await moderation.check_duplicate_links(message, config)
        if dup_warning:
            await message.channel.send(dup_warning, delete_after=10)
            return

    # ===== SAFETY PIPELINE =====
    if message.guild and config:
        if not permissions.is_trusted(message.author, config):
            for raw_url in message.content.split():
                if raw_url.startswith('http://') or raw_url.startswith('https://'):
                    blocked = await blacklist.check_url(message, config, raw_url)
                    if blocked:
                        await moderation.log_action(message, config,
                            "Domain Blocked", f"Blocked: {raw_url}", discord.Color.red())
                        return

            # FIX #2: Unshorten FIRST so phishing checks resolved destinations
            await safety.unshorten_links(message)

            malicious = await safety.check_phishing(message)
            if malicious:
                await moderation.log_action(message, config,
                    "Malicious Link Deleted", "Flagged by SinkingYachts API", discord.Color.red())
                return

            if config.get("file_warnings", True):
                await safety.inspect_files(message, config)
            await safety.warn_suspicious_tld(message, config)
            await safety.warn_http_downgrade(message, config)
            blocked_by_age = await safety.warn_new_domain(message, config)
            if blocked_by_age:
                await moderation.log_action(message, config,
                    "New Domain Blocked", "Domain age < 30 days", discord.Color.red())
                return
            await safety.virustotal.warn_virustotal(message, config)
            await safety.scorecard.maybe_show_scorecard(message, config)

    # ===== ENRICHMENT =====
    await enrichment.run_all_enrichment(message, bot, config)
    # ===== TRACKING STRIPPING =====
    await embeds.strip_tracking(message)
    # ===== NSFW DETECTION =====
    if message.guild and config:
        await embeds.warn_nsfw(message, config)
    # ===== EASTER EGGS =====
    if message.guild and config:
        if config.get("easter_eggs", True):
            handled = await easter_eggs.handle_mention(message, bot)
            if handled:
                return
        await easter_eggs.handle_reactions(message, config)
    # ===== EMBED FIXING (deletes original, runs LAST) =====
    await embeds.handle_link_fixer(message)


@bot.event
async def on_disconnect():
    await stats.stop_stats()


if __name__ == '__main__':
    bot_token = os.getenv('DISCORD_BOT_TOKEN')
    if not bot_token:
        raise ValueError("DISCORD_BOT_TOKEN not found in .env file.")
    bot.run(bot_token)
