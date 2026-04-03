"""Cache management tool."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ..server import mcp

_CACHE_DIR = Path.home() / ".cache" / "fbi-crime-data-mcp"


@mcp.tool()
async def manage_cache(action: str) -> str:
    """Manage the FBI Crime Data response cache.

    Args:
        action: "status" (show cache stats), "clear" (wipe entire cache), or "clear_expired" (remove only expired entries)
    """
    if action not in ("status", "clear", "clear_expired"):
        return "Invalid action. Must be 'status', 'clear', or 'clear_expired'."

    if not _CACHE_DIR.exists():
        return "Cache directory does not exist. No cached data."

    if action == "status":
        return _cache_status()
    elif action == "clear":
        return _clear_cache(expired_only=False)
    else:
        return _clear_cache(expired_only=True)


def _cache_status() -> str:
    """Gather cache statistics."""
    now = datetime.now(tz=timezone.utc)
    total_entries = 0
    expired_entries = 0
    active_entries = 0
    total_bytes = 0
    oldest: datetime | None = None
    newest: datetime | None = None
    collections: dict[str, dict] = {}

    for info_file in _CACHE_DIR.glob("*-info.json"):
        try:
            info = json.loads(info_file.read_text())
        except (json.JSONDecodeError, OSError):
            continue

        collection_name = info.get("collection", info_file.stem)
        collection_dir = Path(info.get("directory", ""))
        if not collection_dir.exists():
            continue

        col_total = 0
        col_expired = 0
        col_bytes = 0

        for entry_file in collection_dir.glob("*.json"):
            try:
                entry = json.loads(entry_file.read_text())
            except (json.JSONDecodeError, OSError):
                continue

            file_size = entry_file.stat().st_size
            col_bytes += file_size

            created_str = entry.get("created_at")
            expires_str = entry.get("expires_at")

            if created_str:
                try:
                    created = datetime.fromisoformat(created_str)
                    if oldest is None or created < oldest:
                        oldest = created
                    if newest is None or created > newest:
                        newest = created
                except ValueError:
                    pass

            col_total += 1
            if expires_str:
                try:
                    expires_at = datetime.fromisoformat(expires_str)
                    if expires_at <= now:
                        col_expired += 1
                except ValueError:
                    pass

        collections[collection_name] = {
            "entries": col_total,
            "expired": col_expired,
            "size_kb": round(col_bytes / 1024, 1),
        }
        total_entries += col_total
        expired_entries += col_expired
        active_entries += col_total - col_expired
        total_bytes += col_bytes

    result = {
        "cache_directory": str(_CACHE_DIR),
        "total_entries": total_entries,
        "active_entries": active_entries,
        "expired_entries": expired_entries,
        "total_size_kb": round(total_bytes / 1024, 1),
        "oldest_entry": oldest.isoformat() if oldest else None,
        "newest_entry": newest.isoformat() if newest else None,
        "collections": collections,
    }
    return json.dumps(result, indent=2)


def _clear_cache(expired_only: bool) -> str:
    """Clear cache entries. If expired_only, remove only expired entries."""
    now = datetime.now(tz=timezone.utc)
    removed = 0
    kept = 0
    freed_bytes = 0

    for info_file in _CACHE_DIR.glob("*-info.json"):
        try:
            info = json.loads(info_file.read_text())
        except (json.JSONDecodeError, OSError):
            continue

        collection_dir = Path(info.get("directory", ""))
        if not collection_dir.exists():
            continue

        for entry_file in collection_dir.glob("*.json"):
            if expired_only:
                try:
                    entry = json.loads(entry_file.read_text())
                    expires_str = entry.get("expires_at")
                    if not expires_str:
                        kept += 1
                        continue
                    expires_at = datetime.fromisoformat(expires_str)
                    if expires_at > now:
                        kept += 1
                        continue
                except (json.JSONDecodeError, OSError, ValueError):
                    kept += 1
                    continue

            freed_bytes += entry_file.stat().st_size
            entry_file.unlink()
            removed += 1

        if not expired_only:
            # Remove the collection directory and info file
            try:
                collection_dir.rmdir()
            except OSError:
                pass
            info_file.unlink(missing_ok=True)

    action = "expired entries" if expired_only else "all entries"
    result = {
        "action": f"Cleared {action}",
        "removed": removed,
        "kept": kept if expired_only else 0,
        "freed_kb": round(freed_bytes / 1024, 1),
    }
    return json.dumps(result, indent=2)
