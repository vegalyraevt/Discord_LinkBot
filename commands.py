"""
commands.py - Slash command definitions for LinkBot v2.

Uses discord.py's app_commands (tree) for slash commands.
Commands are registered to the bot's command tree in main.py.

Permission model:
  - Read-only commands: Everyone
  - Management commands: Manager only (checked via permissions.is_manager())
  - Channel restriction: configurable command_channels per server
  - Cooldown: configurable per-user cooldown between command uses
"""

import discord
from discord import app_commands
from typing import Optional

import keyvault
import config_manager
import permissions
import channel_filter
import stats as stats_module
import moderation
import safety
from safety import scorecard as safety_scorecard
from safety import virustotal as vt_module
from safety import rdap as rdap_module
from enrichment import archive as archive_module


async def _check_manager(interaction: discord.Interaction) -> bool:
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return False
    config = config_manager.load_config(interaction.guild.id)
    if not permissions.is_manager(interaction.user, config, interaction.guild):
        await interaction.response.send_message(
            "You don't have permission to manage LinkBot settings. "
            "You need **Manage Server** permission or a configured manager role.",
            ephemeral=True,
        )
        return False
    return True


async def _check_channel(interaction: discord.Interaction, config: dict) -> bool:
    if not interaction.guild:
        return True
    if not channel_filter.is_command_channel_allowed(interaction.channel_id, config):
        await interaction.response.send_message(
            "Commands are restricted to a specific channel on this server.",
            ephemeral=True,
        )
        return False
    return True


async def _check_cooldown(interaction: discord.Interaction, config: dict) -> bool:
    if not moderation.check_command_cooldown(interaction.user.id, config):
        cooldown = config.get("command_cooldown_seconds", 3)
        await interaction.response.send_message(
            f"Please wait {cooldown}s between commands.", ephemeral=True
        )
        return False
    return True


def _get_config(interaction: discord.Interaction) -> dict:
    if interaction.guild:
        return config_manager.load_config(interaction.guild.id)
    return {}


# ===== USER COMMANDS =====

@app_commands.command(name="scan", description="Run a full safety scan on a URL")
@app_commands.describe(url="The URL to scan")
async def cmd_scan(interaction: discord.Interaction, url: str):
    config = _get_config(interaction)
    if not await _check_channel(interaction, config) or not await _check_cooldown(interaction, config):
        return
    await interaction.response.defer(ephemeral=False)
    score, reasons = safety_scorecard.calculate_score(url)
    vt_result = None
    try:
        vt_result = await vt_module.scan_url(url, config, interaction.guild.id if interaction.guild else None)
        if vt_result:
            await stats_module.increment("vt_scans")
            score, reasons = safety_scorecard.calculate_score(url, vt_result=vt_result)
    except Exception:
        pass
    threshold = config.get("safety_score_threshold", 6)
    embed = safety_scorecard.build_score_embed(url, score, reasons, threshold)
    await interaction.followup.send(embed=embed)
    await stats_module.increment("commands_used")


@app_commands.command(name="safety", description="Quick safety check on a URL (no VT scan)")
@app_commands.describe(url="The URL to check")
async def cmd_safety(interaction: discord.Interaction, url: str):
    config = _get_config(interaction)
    if not await _check_channel(interaction, config) or not await _check_cooldown(interaction, config):
        return
    await interaction.response.defer(ephemeral=False)
    score, reasons = safety_scorecard.calculate_score(url)
    threshold = config.get("safety_score_threshold", 6)
    embed = safety_scorecard.build_score_embed(url, score, reasons, threshold)
    await interaction.followup.send(embed=embed)
    await stats_module.increment("commands_used")


@app_commands.command(name="unshorten", description="Show what's behind a shortened URL")
@app_commands.describe(url="The shortened URL to expand")
async def cmd_unshorten(interaction: discord.Interaction, url: str):
    config = _get_config(interaction)
    if not await _check_channel(interaction, config) or not await _check_cooldown(interaction, config):
        return
    await interaction.response.defer(ephemeral=False)
    from urllib.parse import urlparse
    import aiohttp
    redirect_chain = [url]
    current_url = url
    try:
        async with aiohttp.ClientSession() as session:
            for _ in range(10):
                async with session.get(current_url, allow_redirects=False, timeout=aiohttp.ClientTimeout(total=3)) as resp:
                    if resp.status in (301, 302, 303, 307, 308):
                        location = resp.headers.get('Location', '')
                        if not location:
                            break
                        if location.startswith('/'):
                            parsed = urlparse(current_url)
                            location = f"{parsed.scheme}://{parsed.netloc}{location}"
                        redirect_chain.append(location)
                        current_url = location
                    else:
                        break
        actual_hops = len(redirect_chain) - 1
        numbered = '\n'.join(f"{i+1}. {u}" for i, u in enumerate(redirect_chain))
        last_url = redirect_chain[-1] if redirect_chain else url
        last_host = last_url.split('//')[-1].split('/')[0].lower() if '//' in last_url else ''
        # Check if final destination is also a known shortener
        from shared_constants import SHORTENER_DOMAINS as _SDS
        is_short_end = last_host in _SDS or any(last_host.endswith('.'+d) for d in _SDS)
        desc = f"**{actual_hops} redirects followed:**\n\n{numbered}"
        if is_short_end:
            desc += f"\n\n**Warning:** The final destination ({last_url}) is also a known link shortener. This chain may continue beyond what the bot can follow (JavaScript redirects are invisible to HTTP clients). Do not click unless you trust every link in this chain."
            embed_color = discord.Color.orange()
        else:
            embed_color = discord.Color.blue()
        embed = discord.Embed(
            title="URL Unshortened",
            description=desc,
            color=embed_color,
        )
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"Failed to unshorten: {e}")
    await stats_module.increment("commands_used")


@app_commands.command(name="archive", description="Submit a URL to the Wayback Machine")
@app_commands.describe(url="The URL to archive")
async def cmd_archive(interaction: discord.Interaction, url: str):
    config = _get_config(interaction)
    if not await _check_channel(interaction, config) or not await _check_cooldown(interaction, config):
        return
    await interaction.response.defer(ephemeral=False)
    archived_url = await archive_module.submit_to_archive(url)
    if archived_url:
        embed = discord.Embed(
            title="Submitted to Wayback Machine",
            description=f"**Original:** {url}\n**Archive:** {archived_url}\n\n*It may take a few minutes for the snapshot to become available.*",
            color=discord.Color.dark_green(),
        )
        embed.set_footer(text="Powered by archive.org")
        await interaction.followup.send(embed=embed)
        await stats_module.increment("archive_snapshots")
    else:
        await interaction.followup.send("Failed to archive this URL.")
    await stats_module.increment("commands_used")


@app_commands.command(name="whois", description="Look up domain registration info")
@app_commands.describe(domain="The domain to look up (e.g. example.com)")
async def cmd_whois(interaction: discord.Interaction, domain: str):
    config = _get_config(interaction)
    if not await _check_channel(interaction, config) or not await _check_cooldown(interaction, config):
        return
    whois_access = config.get("whois_access", "mods")
    if whois_access == "mods" and not await _check_manager(interaction):
        return
    await interaction.response.defer(ephemeral=False)
    result = await rdap_module.query_domain(domain)
    if not result:
        await interaction.followup.send(f"Could not look up `{domain}`.")
        return
    age_days = rdap_module.get_domain_age_days(result.get("registered_date"))
    embed = discord.Embed(title=f"WHOIS: {result['domain']}", color=discord.Color.blue())
    embed.add_field(name="Registered", value=result.get("registered_date", "Unknown")[:10], inline=True)
    embed.add_field(name="Age", value=f"{age_days} days" if age_days else "Unknown", inline=True)
    embed.add_field(name="Registrar", value=result.get("registrar", "Unknown"), inline=True)
    if result.get("nameservers"):
        embed.add_field(name="Nameservers", value="\n".join(result["nameservers"][:3]), inline=False)
    embed.set_footer(text="RDAP Lookup - LinkBot")
    await interaction.followup.send(embed=embed)
    await stats_module.increment("whois_lookups")
    await stats_module.increment("commands_used")


@app_commands.command(name="stats", description="Show global LinkBot usage statistics")
async def cmd_stats(interaction: discord.Interaction):
    config = _get_config(interaction)
    if not await _check_channel(interaction, config):
        return
    await interaction.response.defer(ephemeral=False)
    all_stats = stats_module.get_stats()
    embed = discord.Embed(title="LinkBot Statistics", description="Global usage since last restart:", color=discord.Color.dark_theme())
    safety_pairs = [
        ("Links Fixed", "links_fixed"), ("Tracking Stripped", "tracking_stripped"),
        ("URLs Unshortened", "links_unshortened"), ("Malicious Blocked", "malicious_blocked"),
        ("Files Inspected", "files_inspected"), ("VT Scans", "vt_scans"),
        ("New Domains Blocked", "new_domains_blocked"), ("Score Cards Shown", "safety_cards_shown"),
        ("Blacklist Deletions", "blacklist_deletions"), ("Whitelist Blocks", "whitelist_blocks"),
        ("Timeouts Issued", "timeouts_issued"), ("Messages Deleted", "messages_deleted"),
    ]
    enrich_pairs = [
        ("Steam Games", "steam_games"), ("IMDb Movies", "imdb_movies"), ("Music Links", "music_links"),
        ("Wikipedia", "wikipedia_summaries"), ("Amazon Products", "amazon_products"),
        ("Archived", "archive_snapshots"), ("GH Snippets", "github_snippets"),
        ("GH Repos", "github_repos"), ("GH Profiles", "github_profiles"),
        ("Discord Quotes", "discord_quotes"), ("YouTube", "youtube_enrichments"),
        ("Twitch", "twitch_enrichments"),
    ]
    fun_pairs = [("Easter Eggs", "easter_eggs"), ("Rickrolls", "rickrolls_dealt"), ("Rare Drops", "rare_drops")]
    embed.add_field(name="Safety", value="\n".join(f"`{all_stats.get(k, 0):>6,}` {l}" for l, k in safety_pairs) or "No data", inline=True)
    embed.add_field(name="Enrichment", value="\n".join(f"`{all_stats.get(k, 0):>6,}` {l}" for l, k in enrich_pairs) or "No data", inline=True)
    embed.add_field(name="Fun", value="\n".join(f"`{all_stats.get(k, 0):>6,}` {l}" for l, k in fun_pairs) or "No data", inline=True)
    embed.set_footer(text=f"Commands used: {all_stats.get('commands_used', 0)} - LinkBot v2")
    await interaction.followup.send(embed=embed)
    await stats_module.increment("commands_used")


@app_commands.command(name="help", description="Show LinkBot help and available commands")
async def cmd_help(interaction: discord.Interaction):
    config = _get_config(interaction)
    if not await _check_channel(interaction, config):
        return
    await interaction.response.defer(ephemeral=True)
    embed = discord.Embed(title="LinkBot Help", description="*It's dangerous to go alone - take this!*", color=discord.Color.green())
    embed.add_field(name="User Commands", value=(
        "`/scan <url>` - Full safety scan with VirusTotal\n"
        "`/safety <url>` - Quick safety check\n"
        "`/unshorten <url>` - Expand shortened URLs\n"
        "`/archive <url>` - Save to Wayback Machine\n"
        "`/whois <domain>` - Domain registration lookup\n"
        "`/stats` - Global bot statistics\n"
        "`/config show` - View server settings\n"
    ), inline=False)
    embed.add_field(name="Management Commands", value=(
        "`/setup` - Interactive setup wizard\n"
        "`/config toggle <feature>` - Enable/disable features\n"
        "`/config threshold <1-10>` - Set safety alert level\n"
        "`/config notify set #channel` - Set alert channel\n"
        "`/config log set #channel` - Set audit log channel\n"
        "`/config manager add @role` - Delegate management\n"
        "`/blacklist add/remove/list <domain>` - Manage blocked domains\n"
        "`/whitelist add/remove/list <domain>` - Manage allowed domains\n"
        "`/trusted add/remove/list @role` - Safety bypass roles\n"
    ), inline=False)
    embed.set_footer(text="LinkBot v2 - Use /setup to configure your server")
    await interaction.followup.send(embed=embed, ephemeral=True)
    await stats_module.increment("commands_used")


# ===== MANAGEMENT COMMANDS =====

async def config_autocomplete(interaction: discord.Interaction, current: str):
    valid = [
        "easter_eggs", "reactions", "file_warnings", "file_auto_delete",
        "suspicious_tld_warn", "http_downgrade_warn", "domain_age_warn",
        "domain_age_block", "nsfw_warning",
    ]
    return [
        app_commands.Choice(name=n, value=n)
        for n in valid if current.lower() in n.lower()
    ]


@app_commands.command(name="config", description="View or change server configuration")
@app_commands.describe(action="What to do", option="Feature or setting name", value="Value to set")
@app_commands.choices(action=[
    app_commands.Choice(name="Show current config", value="show"),
    app_commands.Choice(name="Toggle a feature on/off", value="toggle"),
    app_commands.Choice(name="Set safety threshold (1-10)", value="threshold"),
    app_commands.Choice(name="Set notification channel", value="notify"),
    app_commands.Choice(name="Set audit log channel", value="log"),
    app_commands.Choice(name="Add a manager role", value="manager_add"),
    app_commands.Choice(name="Remove a manager role", value="manager_remove"),
])
@app_commands.autocomplete(option=config_autocomplete)
async def cmd_config(
    interaction: discord.Interaction,
    action: app_commands.Choice[str],
    option: Optional[str] = None,
    value: Optional[str] = None,
):
    if not await _check_manager(interaction):
        return
    config = _get_config(interaction)
    if not await _check_channel(interaction, config):
        return

    if action.value == "show":
        await interaction.response.defer(ephemeral=False)
        embed = discord.Embed(title="Server Configuration", color=discord.Color.blue())
        settings = [
            ("Easter Eggs", config.get("easter_eggs", True)), ("Reactions", config.get("reactions", True)),
            ("Safety Threshold", f"{config.get('safety_score_threshold', 6)}/10"),
            ("File Warnings", config.get("file_warnings", True)),
            ("File Auto-Delete", config.get("file_auto_delete", False)),
            ("Suspicious TLD Warn", config.get("suspicious_tld_warn", True)),
            ("HTTP Downgrade Warn", config.get("http_downgrade_warn", True)),
            ("Domain Age Warn", config.get("domain_age_warn", True)),
            ("Domain Age Block", config.get("domain_age_block", False)),
            ("NSFW Warning", config.get("nsfw_warning", False)),
            ("Archive Auto", config.get("archive", {}).get("enabled", False)),
            ("Rate Limiting", config.get("ratelimit", {}).get("enabled", True)),
            ("Command Cooldown", f"{config.get('command_cooldown_seconds', 3)}s"),
            ("Blacklist Mode", config.get("blacklist_mode", "blacklist")),
            ("Whois Access", config.get("whois_access", "mods")),
        ]
        for name, val in settings:
            embed.add_field(name=name, value=str(val), inline=True)
        await interaction.followup.send(embed=embed)

    elif action.value == "toggle":
        if not option:
            await interaction.response.send_message("Please specify a feature to toggle.", ephemeral=True)
            return
        valid_toggles = ["easter_eggs", "reactions", "file_warnings", "file_auto_delete",
                         "suspicious_tld_warn", "http_downgrade_warn", "domain_age_warn",
                         "domain_age_block", "nsfw_warning"]
        if option.lower() not in valid_toggles:
            await interaction.response.send_message(f"Unknown feature. Valid: {', '.join(valid_toggles)}", ephemeral=True)
            return
        config[option.lower()] = not config.get(option.lower(), True)
        config_manager.save_config(interaction.guild.id, config)
        await interaction.response.send_message(f"`{option}` is now **{'ON' if config[option.lower()] else 'OFF'}**.", ephemeral=False)

    elif action.value == "threshold":
        if not option or not option.isdigit() or not 1 <= int(option) <= 10:
            await interaction.response.send_message("Please provide a number between 1 and 10.", ephemeral=True)
            return
        config["safety_score_threshold"] = int(option)
        config_manager.save_config(interaction.guild.id, config)
        await interaction.response.send_message(f"Safety score threshold set to **{option}/10**.", ephemeral=False)

    elif action.value == "notify":
        if not option:
            await interaction.response.send_message("Please provide a channel mention (e.g. #mod-log).", ephemeral=True)
            return
        channel_id = option.strip("<#>")
        if not channel_id.isdigit():
            await interaction.response.send_message("Invalid channel. Please mention a text channel.", ephemeral=True)
            return
        config["notification_channel"] = int(channel_id)
        config_manager.save_config(interaction.guild.id, config)
        await interaction.response.send_message("Notification channel set.", ephemeral=False)

    elif action.value == "log":
        if not option:
            await interaction.response.send_message("Please provide a channel mention (e.g. #linkbot-log).", ephemeral=True)
            return
        channel_id = option.strip("<#>")
        if not channel_id.isdigit():
            await interaction.response.send_message("Invalid channel. Please mention a text channel.", ephemeral=True)
            return
        config["logging_channel"] = int(channel_id)
        config_manager.save_config(interaction.guild.id, config)
        await interaction.response.send_message("Audit log channel set.", ephemeral=False)

    elif action.value == "manager_add":
        if not option:
            await interaction.response.send_message("Please mention a role (e.g. @ModRole).", ephemeral=True)
            return
        role_id = option.strip("<@&>")
        if not role_id.isdigit():
            await interaction.response.send_message("Invalid role. Please mention a valid role.", ephemeral=True)
            return
        rid = int(role_id)
        roles = config.get("manager_roles", [])
        if rid not in roles:
            roles.append(rid)
            config["manager_roles"] = roles
            config_manager.save_config(interaction.guild.id, config)
        await interaction.response.send_message(f"<@&{rid}> added as a manager role.", ephemeral=False)

    elif action.value == "manager_remove":
        if not option:
            await interaction.response.send_message("Please mention a role (e.g. @ModRole).", ephemeral=True)
            return
        role_id = option.strip("<@&>")
        if not role_id.isdigit():
            await interaction.response.send_message("Invalid role.", ephemeral=True)
            return
        rid = int(role_id)
        roles = config.get("manager_roles", [])
        if rid in roles:
            roles.remove(rid)
            config["manager_roles"] = roles
            config_manager.save_config(interaction.guild.id, config)
        await interaction.response.send_message(f"<@&{rid}> removed from manager roles.", ephemeral=False)

    await stats_module.increment("commands_used")


@app_commands.command(name="blacklist", description="Manage domain blacklist")
@app_commands.describe(action="Action", domain="Domain name (e.g. example.com)", message="Custom violation message")
@app_commands.choices(action=[
    app_commands.Choice(name="Add a domain", value="add"),
    app_commands.Choice(name="Remove a domain", value="remove"),
    app_commands.Choice(name="List all domains", value="list"),
    app_commands.Choice(name="Set default action", value="action"),
    app_commands.Choice(name="Set custom reply message", value="message"),
])
async def cmd_blacklist(interaction: discord.Interaction, action: app_commands.Choice[str], domain: Optional[str] = None, message: Optional[str] = None):
    if not await _check_manager(interaction):
        return
    config = _get_config(interaction)
    if not await _check_channel(interaction, config):
        return
    bl = config.get("blacklist", {})
    if action.value == "add":
        if not domain:
            await interaction.response.send_message("Please provide a domain name.", ephemeral=True)
            return
        domains = bl.get("domains", {})
        domains[domain.lower()] = True
        bl["domains"] = domains
        config["blacklist"] = bl
        config_manager.save_config(interaction.guild.id, config)
        await interaction.response.send_message(f"`{domain}` added to blacklist.", ephemeral=False)
    elif action.value == "remove":
        if not domain:
            await interaction.response.send_message("Please provide a domain name.", ephemeral=True)
            return
        domains = bl.get("domains", {})
        domains.pop(domain.lower(), None)
        bl["domains"] = domains
        config["blacklist"] = bl
        config_manager.save_config(interaction.guild.id, config)
        await interaction.response.send_message(f"`{domain}` removed from blacklist.", ephemeral=False)
    elif action.value == "list":
        await interaction.response.defer(ephemeral=True)
        domains = bl.get("domains", {})
        await interaction.followup.send(
            f"**Blacklisted domains:**\n" + "\n".join(f"- `{d}`" for d in domains) if domains else "No domains blacklisted.",
            ephemeral=True,
        )
    elif action.value == "action":
        if not domain:
            await interaction.response.send_message("Please specify an action: `delete`, `timeout`, `notify`, or combinations.", ephemeral=True)
            return
        bl["default_action"] = domain.lower()
        config["blacklist"] = bl
        config_manager.save_config(interaction.guild.id, config)
        await interaction.response.send_message(f"Default action set to `{domain}`.", ephemeral=False)
    elif action.value == "message":
        if not message:
            await interaction.response.send_message("Please provide a message string.", ephemeral=True)
            return
        bl["custom_message"] = message
        config["blacklist"] = bl
        config_manager.save_config(interaction.guild.id, config)
        await interaction.response.send_message("Custom violation message updated.", ephemeral=False)
    await stats_module.increment("commands_used")


@app_commands.command(name="whitelist", description="Manage domain whitelist")
@app_commands.describe(action="Action", domain="Domain name (e.g. youtube.com)")
@app_commands.choices(action=[
    app_commands.Choice(name="Add a domain", value="add"),
    app_commands.Choice(name="Remove a domain", value="remove"),
    app_commands.Choice(name="List all domains", value="list"),
    app_commands.Choice(name="Switch to blacklist mode", value="mode_blacklist"),
    app_commands.Choice(name="Switch to whitelist mode", value="mode_whitelist"),
])
async def cmd_whitelist(interaction: discord.Interaction, action: app_commands.Choice[str], domain: Optional[str] = None):
    if not await _check_manager(interaction):
        return
    config = _get_config(interaction)
    if not await _check_channel(interaction, config):
        return
    if action.value in ("mode_blacklist", "mode_whitelist"):
        config["blacklist_mode"] = "blacklist" if action.value == "mode_blacklist" else "whitelist"
        config_manager.save_config(interaction.guild.id, config)
        await interaction.response.send_message(f"Switched to **{config['blacklist_mode']}** mode.", ephemeral=False)
        return
    wl = config.get("whitelist", {})
    if action.value == "add":
        if not domain:
            await interaction.response.send_message("Please provide a domain name.", ephemeral=True)
            return
        domains = wl.get("domains", {})
        domains[domain.lower()] = True
        wl["domains"] = domains
        config["whitelist"] = wl
        config_manager.save_config(interaction.guild.id, config)
        await interaction.response.send_message(f"`{domain}` added to whitelist.", ephemeral=False)
    elif action.value == "remove":
        if not domain:
            await interaction.response.send_message("Please provide a domain name.", ephemeral=True)
            return
        domains = wl.get("domains", {})
        domains.pop(domain.lower(), None)
        wl["domains"] = domains
        config["whitelist"] = wl
        config_manager.save_config(interaction.guild.id, config)
        await interaction.response.send_message(f"`{domain}` removed from whitelist.", ephemeral=False)
    elif action.value == "list":
        await interaction.response.defer(ephemeral=True)
        domains = wl.get("domains", {})
        await interaction.followup.send(
            f"**Whitelisted domains:**\n" + "\n".join(f"- `{d}`" for d in domains) if domains else "No domains whitelisted.",
            ephemeral=True,
        )
    await stats_module.increment("commands_used")


@app_commands.command(name="setup", description="Interactive setup wizard for LinkBot")
async def cmd_setup(interaction: discord.Interaction):
    if not await _check_manager(interaction):
        return
    config = _get_config(interaction)
    if not await _check_channel(interaction, config):
        return
    await interaction.response.defer(ephemeral=True)
    embed = discord.Embed(title="LinkBot Setup Wizard", description=(
        "Welcome to the LinkBot setup!\n\n"
        "**1. Set a notification channel:** `/config notify set #your-channel`\n\n"
        "**2. Set an audit log channel:** `/config log set #your-log-channel`\n\n"
        "**3. Toggle features:** `/config toggle easter_eggs`\n\n"
        "**4. Set safety sensitivity:** `/config threshold 4` (more) or `8` (less)\n\n"
        "**5. Block domains:** `/blacklist add scam-site.com`\n\n"
        "**6. Delegate management:** `/config manager add @ModRole`\n\n"
        "**7. View config:** `/config show`\n\nUse `/help` to see all commands."
    ), color=discord.Color.green())
    embed.set_footer(text="LinkBot v2 - It's dangerous to go alone!")
    await interaction.followup.send(embed=embed, ephemeral=True)
    await stats_module.increment("commands_used")


@app_commands.command(name="trusted", description="Add or remove trusted roles (bypass safety checks)")
@app_commands.describe(action="Add or remove a trusted role", role="The role to add/remove")
@app_commands.choices(action=[
    app_commands.Choice(name="Add a trusted role", value="add"),
    app_commands.Choice(name="Remove a trusted role", value="remove"),
    app_commands.Choice(name="List trusted roles", value="list"),
])
async def cmd_trusted(interaction: discord.Interaction, action: app_commands.Choice[str], role: Optional[discord.Role] = None):
    if not await _check_manager(interaction):
        return
    config = _get_config(interaction)
    if not await _check_channel(interaction, config):
        return
    trusted = config.get("trusted_roles", [])
    if action.value == "add":
        if not role:
            await interaction.response.send_message("Please mention a role to add.", ephemeral=True)
            return
        if role.id in trusted:
            await interaction.response.send_message(f"{role.mention} is already trusted.", ephemeral=True)
            return
        trusted.append(role.id)
        config["trusted_roles"] = trusted
        config_manager.save_config(interaction.guild.id, config)
        await interaction.response.send_message(
            f"{role.mention} added as trusted.\n**Warning:** Members with this role bypass ALL link safety checks including phishing detection.",
            ephemeral=False,
        )
    elif action.value == "remove":
        if not role:
            await interaction.response.send_message("Please mention a role to remove.", ephemeral=True)
            return
        if role.id not in trusted:
            await interaction.response.send_message(f"{role.mention} is not trusted.", ephemeral=True)
            return
        trusted.remove(role.id)
        config["trusted_roles"] = trusted
        config_manager.save_config(interaction.guild.id, config)
        await interaction.response.send_message(f"{role.mention} removed from trusted roles.", ephemeral=False)
    elif action.value == "list":
        await interaction.response.defer(ephemeral=True)
        if not trusted:
            await interaction.followup.send("No trusted roles configured.", ephemeral=True)
        else:
            await interaction.followup.send("**Trusted roles:**\n" + "\n".join(f"- <@&{rid}>" for rid in trusted), ephemeral=True)
    await stats_module.increment("commands_used")


@app_commands.command(name="vtkey", description="Manage VirusTotal API key for this server")
@app_commands.describe(action="Action", key="VirusTotal API key", limit="Hourly scan limit (1-500, 0 to disable)")
@app_commands.choices(action=[
    app_commands.Choice(name="Get setup info", value="info"),
    app_commands.Choice(name="Set/update API key", value="set"),
    app_commands.Choice(name="Remove stored key", value="remove"),
    app_commands.Choice(name="Check status", value="status"),
    app_commands.Choice(name="Set hourly scan limit", value="limit"),
])
async def cmd_vtkey(
    interaction: discord.Interaction,
    action: app_commands.Choice[str],
    key: Optional[str] = None,
    limit: Optional[int] = None,
):
    if not await _check_manager(interaction):
        return
    config = _get_config(interaction)
    if not await _check_channel(interaction, config):
        return

    vt = config.setdefault("vt_settings", {"api_key_encrypted": "", "hourly_limit": 20, "daily_limit": 500})

    if action.value == "info":
        await interaction.response.send_message(embed=discord.Embed(
            title="VirusTotal API Key Setup",
            description=(
                "LinkBot uses VirusTotal to scan URLs against 70+ security engines.\n\n"
                "**Get a free API key:**\n"
                "1. Go to https://www.virustotal.com\n"
                "2. Sign up for a free account\n"
                "3. Go to your profile API key section\n"
                "4. Copy your API key\n\n"
                "**Then use:** `/vtkey set <your-key>`\n\n"
                "Your key is encrypted before storage on LinkBot's host machine.\n"
                "It is never visible after being set, not even to the bot host.\n"
                "You can remove it at any time with `/vtkey remove`.\n\n"
                "Free tier: 500 lookups/day. LinkBot limits to 20/hour by default.\n"
                "Premium users can adjust this with `/vtkey limit <number>`."
            ),
            color=discord.Color.blue(),
        ), ephemeral=True)
        return

    elif action.value == "set":
        if not key:
            await interaction.response.send_message("Please provide your VirusTotal API key after the `key` parameter.", ephemeral=True)
            return
        if len(key) < 30:
            await interaction.response.send_message("That does not look like a valid VirusTotal API key. Keys are 64+ characters.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        encrypted = keyvault.encrypt_value(key.strip())
        vt["api_key_encrypted"] = encrypted
        config["vt_settings"] = vt
        config_manager.save_config(interaction.guild.id, config)
        await interaction.followup.send(embed=discord.Embed(
            title="VirusTotal Key Stored",
            description=(
                "Your API key has been encrypted and stored.\n\n"
                "It is never visible in any chat message or config display.\n"
                "It is used only for VirusTotal lookups on this server.\n\n"
                "You are responsible for API usage under your key.\n"
                "The free tier allows 500 lookups/day.\n"
                "LinkBot will limit scans to protect your quota (default: 20/hour).\n"
                "Premium tier users can disable limits with `/vtkey limit 0`.\n\n"
                "Remove your key at any time with `/vtkey remove`."
            ),
            color=discord.Color.green(),
        ), ephemeral=True)

    elif action.value == "status":
        await interaction.response.defer(ephemeral=True)
        has_key = bool(vt.get("api_key_encrypted", ""))
        hourly = vt.get("hourly_limit", 20)
        if has_key:
            limits_text = f"Hourly limit: {'disabled' if hourly == 0 else f'{hourly}/hour'}, Daily limit: {vt.get('daily_limit', 500)}/day"
            await interaction.followup.send(embed=discord.Embed(
                title="VirusTotal Key Status",
                description=f"Encrypted key is stored and active.\n{limits_text}",
                color=discord.Color.green(),
            ), ephemeral=True)
        else:
            await interaction.followup.send(embed=discord.Embed(
                title="VirusTotal Key Status",
                description="No API key configured for this server.\nVirusTotal scanning is disabled.\n\nUse `/vtkey info` to learn how to get a free key.\nUse `/vtkey set <key>` to configure one.",
                color=discord.Color.orange(),
            ), ephemeral=True)

    elif action.value == "remove":
        await interaction.response.defer(ephemeral=True)
        vt["api_key_encrypted"] = ""
        config["vt_settings"] = vt
        config_manager.save_config(interaction.guild.id, config)
        await interaction.followup.send(embed=discord.Embed(
            title="VirusTotal Key Removed",
            description="Your encrypted API key has been deleted.\nVirusTotal scanning is now disabled for this server.",
            color=discord.Color.orange(),
        ), ephemeral=True)

    elif action.value == "limit":
        if limit is None:
            await interaction.response.send_message("Please provide a number (1-500) or 0 to disable hourly limits.", ephemeral=True)
            return
        if limit < 0 or limit > 500:
            await interaction.response.send_message("Limit must be between 0 (disabled) and 500.", ephemeral=True)
            return
        vt["hourly_limit"] = limit
        config["vt_settings"] = vt
        config_manager.save_config(interaction.guild.id, config)
        if limit == 0:
            await interaction.response.send_message("Hourly scan limit disabled. Your key will be used without restriction (daily cap: 500).", ephemeral=False)
        else:
            await interaction.response.send_message(f"Hourly scan limit set to {limit} lookups/hour.", ephemeral=False)

    await stats_module.increment("commands_used")


# ===== Command Registration =====

def register_commands(tree: app_commands.CommandTree):
    tree.add_command(cmd_scan)
    tree.add_command(cmd_safety)
    tree.add_command(cmd_unshorten)
    tree.add_command(cmd_archive)
    tree.add_command(cmd_whois)
    tree.add_command(cmd_stats)
    tree.add_command(cmd_help)
    tree.add_command(cmd_config)
    tree.add_command(cmd_blacklist)
    tree.add_command(cmd_whitelist)
    tree.add_command(cmd_setup)
    tree.add_command(cmd_trusted)
    tree.add_command(cmd_vtkey)
