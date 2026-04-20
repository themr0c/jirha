"""Disk cache for Jira hierarchy context and sprint metadata."""

import json
import time
from datetime import date
from pathlib import Path


def write_cache(cache_dir, category, key, data):
    """Write data to cache. category is 'features' or 'contexts'."""
    path = Path(cache_dir) / category
    path.mkdir(parents=True, exist_ok=True)
    payload = {"data": data, "cached_at": time.time()}
    (path / f"{key}.json").write_text(json.dumps(payload, default=str))


def read_cache(cache_dir, category, key):
    """Read from cache. Returns dict with 'data' and 'cached_at', or None."""
    path = Path(cache_dir) / category / f"{key}.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def cache_age_str(seconds):
    """Format cache age as human-readable string."""
    if seconds < 60:
        return f"{int(seconds)}s"
    if seconds < 3600:
        return f"{int(seconds / 60)}m"
    if seconds < 86400:
        return f"{int(seconds / 3600)}h"
    return f"{int(seconds / 86400)}d"


def read_sprint_cache(cache_dir):
    """Read sprint cache. Returns data dict or None if missing/expired."""
    entry = read_cache(cache_dir, "sprint", "current")
    if not entry:
        return None
    data = entry["data"]
    end_str = data.get("current_sprint", {}).get("end")
    if not end_str:
        return None
    if date.fromisoformat(end_str) < date.today():
        return None
    return data


def write_sprint_cache(cache_dir, data):
    """Write sprint metadata to cache."""
    write_cache(cache_dir, "sprint", "current", data)
