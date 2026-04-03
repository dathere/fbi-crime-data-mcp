"""Cache management tool."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from fastmcp.server.middleware.caching import ResponseCachingMiddleware

from ..constants import CACHE_DIR as _CACHE_DIR, SPILLOVER_DIR as _SPILLOVER_DIR
from ..server import mcp


def _parse_aware_dt(iso_str: str) -> datetime:
    """Parse an ISO datetime string, assuming UTC if naive."""
    dt = datetime.fromisoformat(iso_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _safe_collection_dir(info: dict) -> Path | None:
    """Extract and validate a collection directory from an info dict.

    Returns None if the directory is missing, empty, not under _CACHE_DIR,
    or doesn't exist.
    """
    raw = info.get("directory")
    if not isinstance(raw, str) or not raw.strip():
        return None
    collection_dir = Path(raw)
    try:
        resolved = collection_dir.resolve()
        resolved.relative_to(_CACHE_DIR.resolve())
    except (OSError, ValueError):
        return None
    if not resolved.is_dir():
        return None
    return resolved


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
        collection_dir = _safe_collection_dir(info)
        if collection_dir is None:
            continue

        col_total = 0
        col_expired = 0
        col_bytes = 0

        for entry_file in collection_dir.glob("*.json"):
            try:
                entry = json.loads(entry_file.read_text())
            except (json.JSONDecodeError, OSError):
                continue

            try:
                file_size = entry_file.stat().st_size
            except OSError:
                continue
            col_bytes += file_size

            created_str = entry.get("created_at")
            expires_str = entry.get("expires_at")

            if created_str:
                try:
                    created = _parse_aware_dt(created_str)
                    if oldest is None or created < oldest:
                        oldest = created
                    if newest is None or created > newest:
                        newest = created
                except ValueError:
                    pass

            col_total += 1
            if expires_str:
                try:
                    expires_at = _parse_aware_dt(expires_str)
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
        "session_hit_rate": _session_hit_rate(),
        "spillover": _spillover_stats(),
    }
    return json.dumps(result, indent=2)


def _spillover_stats() -> dict:
    """Count spillover files and their total size."""
    if not _SPILLOVER_DIR.is_dir():
        return {"files": 0, "size_kb": 0}
    files = list(_SPILLOVER_DIR.glob("*.json"))
    total_bytes = sum(f.stat().st_size for f in files)
    return {
        "files": len(files),
        "size_kb": round(total_bytes / 1024, 1),
    }


def _session_hit_rate() -> dict:
    """Gather in-memory cache hit/miss stats from middleware (current session only)."""
    collection_names = [
        "list_tools",
        "list_resources",
        "list_prompts",
        "read_resource",
        "get_prompt",
        "call_tool",
    ]
    totals: dict[str, dict[str, int]] = {}
    for mw in mcp.middleware:
        if not isinstance(mw, ResponseCachingMiddleware):
            continue
        stats = mw.statistics()
        for name in collection_names:
            col_stats = getattr(stats, name, None)
            if col_stats is None:
                continue
            hits = col_stats.get.hit
            misses = col_stats.get.miss
            if hits == 0 and misses == 0:
                continue
            if name not in totals:
                totals[name] = {"hits": 0, "misses": 0}
            totals[name]["hits"] += hits
            totals[name]["misses"] += misses

    total_hits = sum(c["hits"] for c in totals.values())
    total_misses = sum(c["misses"] for c in totals.values())
    total_requests = total_hits + total_misses

    per_collection = {}
    for name, counts in totals.items():
        col_total = counts["hits"] + counts["misses"]
        per_collection[name] = {
            **counts,
            "total": col_total,
            "hit_rate_pct": round(counts["hits"] / col_total * 100, 1),
        }

    return {
        "note": "In-memory stats for current server session only (resets on restart)",
        "hits": total_hits,
        "misses": total_misses,
        "total": total_requests,
        "hit_rate_pct": round(total_hits / total_requests * 100, 1)
        if total_requests
        else None,
        "collections": per_collection,
    }


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

        collection_dir = _safe_collection_dir(info)
        if collection_dir is None:
            continue

        for entry_file in collection_dir.glob("*.json"):
            if expired_only:
                try:
                    entry = json.loads(entry_file.read_text())
                    expires_str = entry.get("expires_at")
                    if not expires_str:
                        kept += 1
                        continue
                    expires_at = _parse_aware_dt(expires_str)
                    if expires_at > now:
                        kept += 1
                        continue
                except (json.JSONDecodeError, OSError, ValueError):
                    kept += 1
                    continue

            try:
                freed_bytes += entry_file.stat().st_size
                entry_file.unlink()
            except OSError:
                continue
            removed += 1

        if not expired_only:
            # Remove the collection directory and info file
            try:
                shutil.rmtree(collection_dir)
            except OSError:
                pass
            try:
                info_file.unlink(missing_ok=True)
            except OSError:
                pass

    # Clear spillover files on full clear
    spillover_removed = 0
    if not expired_only and _SPILLOVER_DIR.is_dir():
        spillover_removed = len(list(_SPILLOVER_DIR.glob("*.json")))
        try:
            shutil.rmtree(_SPILLOVER_DIR)
        except OSError:
            pass

    action = "expired entries" if expired_only else "all entries"
    result = {
        "action": f"Cleared {action}",
        "removed": removed,
        "kept": kept if expired_only else 0,
        "freed_kb": round(freed_bytes / 1024, 1),
        "spillover_removed": spillover_removed,
    }
    return json.dumps(result, indent=2)
