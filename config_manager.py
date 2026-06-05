"""
config_manager.py - JSON file-based per-server configuration.

Each server's config is stored in config/{server_id}.json.
When no file exists, defaults are used.
Configs are cached in memory for 60 seconds to avoid disk thrashing.
"""

import json
import os
import time
from typing import Dict, Any, Optional


CONFIG_DIR = "config"
DEFAULTS_PATH = os.path.join(CONFIG_DIR, "defaults.json")
CACHE_TTL_SECONDS = 60

# In-memory cache: {server_id: (config_dict, timestamp)}
_config_cache: Dict[str, tuple] = {}


DEFAULT_CONFIG: Dict[str, Any] = {
    "manager_roles": [],
    "trusted_roles": [],
    "vt_settings": {
        "api_key_encrypted": "",
        "hourly_limit": 20,
        "daily_limit": 500
    },
    "channel_mode": "all",
    "disabled_channels": [],
    "enabled_channels": [],
    "command_channels": [],
    "easter_eggs": True,
    "reactions": True,
    "embed_fix": {
        "twitter": True, "tiktok": True, "instagram": True,
        "reddit": True, "pixiv": True, "bluesky": True, "threads": True
    },
    "enrichment": {
        "youtube": True, "twitch": True, "github_gist": True,
        "hacker_news": True, "stack_overflow": True, "dev_to": True,
        "npm": True, "pypi": True, "doi": True, "arxiv": True
    },
    "nsfw_warning": False,
    "nsfw_exempt_channels": [],
    "safety_score_threshold": 6,
    "updates_channel": None,
    "notification_channel": None,
    "logging_channel": None,
    "archive": {
        "enabled": False,
        "channels": [],
        "link_types": ["all"]
    },
    "whois_access": "mods",
    "blacklist_mode": "blacklist",
    "blacklist": {
        "domains": {},
        "default_action": "delete",
        "custom_message": "Your link was removed because that domain is not allowed here.",
        "timeout_duration": 5
    },
    "whitelist": {
        "domains": {}
    },
    "ratelimit": {
        "enabled": True,
        "messages_per_window": 5,
        "window_seconds": 10
    },
    "command_cooldown_seconds": 3,
    "duplicate_link_window": 5,
    "file_warnings": True,
    "file_auto_delete": False,
    "suspicious_tld_warn": True,
    "http_downgrade_warn": True,
    "domain_age_warn": True,
    "domain_age_block": False
}


def _ensure_config_dir() -> None:
    """Create the config directory if it doesn't exist."""
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR, exist_ok=True)


def load_defaults() -> Dict[str, Any]:
    """Load global defaults from config/defaults.json, or return built-in defaults."""
    _ensure_config_dir()
    if os.path.exists(DEFAULTS_PATH):
        try:
            with open(DEFAULTS_PATH, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                # Deep merge with DEFAULT_CONFIG to ensure all keys exist
            return _deep_merge(DEFAULT_CONFIG.copy(), loaded)
        except (json.JSONDecodeError, IOError):
            pass
    return DEFAULT_CONFIG.copy()


def load_config(server_id: int) -> Dict[str, Any]:
    """
    Load the config for a given server.
    Falls back to defaults if no per-server file exists.
    Results are cached for CACHE_TTL_SECONDS.
    """
    sid = str(server_id)
    now = time.time()
    # Check cache
    if sid in _config_cache:
        cached_config, cached_time = _config_cache[sid]
        if now - cached_time < CACHE_TTL_SECONDS:
            return cached_config.copy()
    # Load from file or use defaults
    _ensure_config_dir()
    config = load_defaults()
    server_path = os.path.join(CONFIG_DIR, f"{sid}.json")
    if os.path.exists(server_path):
        try:
            with open(server_path, 'r', encoding='utf-8') as f:
                server_overrides = json.load(f)
            config = _deep_merge(config, server_overrides)
        except (json.JSONDecodeError, IOError):
            pass
    _config_cache[sid] = (config, now)
    return config.copy()


def save_config(server_id: int, config: Dict[str, Any]) -> bool:
    """
    Save the config for a given server to disk.
    Returns True on success, False on failure.
    """
    sid = str(server_id)
    _ensure_config_dir()
    server_path = os.path.join(CONFIG_DIR, f"{sid}.json")
    try:
        with open(server_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        _config_cache[sid] = (config.copy(), time.time())
        return True
    except IOError:
        return False


def invalidate_cache(server_id: Optional[int] = None) -> None:
    """
    Clear the in-memory cache.
    If server_id is None, clears all cached configs.
    """
    if server_id is None:
        _config_cache.clear()
    else:
        _config_cache.pop(str(server_id), None)


def _deep_merge(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively merge override dict into base dict.
    Values from overrides take precedence.
    Nested dicts are merged; non-dict values are replaced.
    """
    result = base.copy()
    for key, value in overrides.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
