"""
stats.py - Global bot-wide usage counter.

Tracks how many times each feature has been used since bot startup.
Persisted to stats.json via atomic writes (prevents data loss on crash).

Thread-safe using asyncio locks.
"""

import json
import os
import tempfile
import asyncio
from typing import Dict


STATS_PATH = "stats.json"
SAVE_INTERVAL_SECONDS = 300  # Auto-save every 5 minutes


# All tracked stat keys with initial values
_stats: Dict[str, int] = {
    "links_fixed": 0,
    "tracking_stripped": 0,
    "links_unshortened": 0,
    "malicious_blocked": 0,
    "files_inspected": 0,
    "steam_games": 0,
    "steam_devs": 0,
    "imdb_movies": 0,
    "music_links": 0,
    "wikipedia_summaries": 0,
    "npm_packages": 0,
    "pypi_packages": 0,
    "arxiv_papers": 0,
    "doi_papers": 0,
    "github_snippets": 0,
    "github_repos": 0,
    "github_profiles": 0,
    "github_gists": 0,
    "archive_snapshots": 0,
    "vt_scans": 0,
    "easter_eggs": 0,
    "blacklist_deletions": 0,
    "whitelist_blocks": 0,
    "domain_age_checks": 0,
    "discord_quotes": 0,
    "safety_cards_shown": 0,
    "duplicate_links_caught": 0,
    "rate_limits_enforced": 0,
    "new_domains_blocked": 0,
    "whois_lookups": 0,
    "amazon_products": 0,
    "youtube_enrichments": 0,
    "twitch_enrichments": 0,
    "hacker_news_enrichments": 0,
    "stack_overflow_enrichments": 0,
    "dev_to_enrichments": 0,
    "bluesky_enrichments": 0,
    "nsfw_warnings": 0,
    "timeouts_issued": 0,
    "messages_deleted": 0,
    "commands_used": 0,
    "rickrolls_dealt": 0,
    "rare_drops": 0,
}

_lock = asyncio.Lock()
_save_task: asyncio.Task = None


def _load_stats() -> None:
    """Load existing stats from disk if available."""
    global _stats
    if os.path.exists(STATS_PATH):
        try:
            with open(STATS_PATH, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            # Merge loaded values into defaults (in case new keys were added)
            for key, value in loaded.items():
                if key in _stats and isinstance(value, int):
                    _stats[key] = value
        except (json.JSONDecodeError, IOError):
            pass


def _save_stats() -> None:
    """Write current stats to disk atomically."""
    try:
        fd, temp_path = tempfile.mkstemp(
            dir=os.path.dirname(STATS_PATH) or '.', suffix='.json')
        with open(fd, 'w', encoding='utf-8') as f:
            json.dump(_stats, f, indent=2)
        os.replace(temp_path, STATS_PATH)
    except IOError:
        pass


async def increment(key: str, amount: int = 1) -> None:
    """Increment a stat counter. Thread-safe."""
    async with _lock:
        if key in _stats:
            _stats[key] += amount


def get_stats() -> Dict[str, int]:
    """Return a copy of all current stats."""
    return _stats.copy()


async def auto_save_loop() -> None:
    """Background task that periodically saves stats to disk."""
    while True:
        await asyncio.sleep(SAVE_INTERVAL_SECONDS)
        async with _lock:
            _save_stats()


async def start_stats() -> None:
    """Initialize stats system: load from disk and start auto-save loop."""
    _load_stats()
    global _save_task
    _save_task = asyncio.create_task(auto_save_loop())


async def stop_stats() -> None:
    """Shutdown: cancel auto-save and do a final save."""
    global _save_task
    if _save_task:
        _save_task.cancel()
        try:
            await _save_task
        except asyncio.CancelledError:
            pass
    async with _lock:
        _save_stats()
