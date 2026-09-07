"""Tests for manage_cache tool."""

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from fbi_crime_data_mcp.api_client import _load_persisted_stats, _save_stats
from fbi_crime_data_mcp.tools.cache import manage_cache


@pytest.fixture
def fake_cache(tmp_path, monkeypatch):
    """Create a fake cache directory with test entries."""
    import fbi_crime_data_mcp.api_client as api_client_mod
    import fbi_crime_data_mcp.tools.cache as cache_mod

    stats_file = tmp_path / "stats.json"

    monkeypatch.setattr(cache_mod, "_CACHE_DIR", tmp_path)
    monkeypatch.setattr(cache_mod, "_STATS_FILE", stats_file)
    monkeypatch.setattr(api_client_mod, "STATS_FILE", stats_file)

    # Create a collection directory and info file
    col_dir = tmp_path / "S_tools_call-abc123"
    col_dir.mkdir()
    info = {
        "version": 1,
        "collection": "tools/call",
        "created_at": "2026-01-01T00:00:00+00:00",
        "directory": str(col_dir),
    }
    (tmp_path / "S_tools_call-abc123-info.json").write_text(json.dumps(info))

    now = datetime.now(tz=UTC)

    # Active entry (expires in 30 days)
    active = {
        "version": 1,
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(days=30)).isoformat(),
        "value": {"result": "active data"},
    }
    (col_dir / "active_entry.json").write_text(json.dumps(active))

    # Expired entry (expired 1 day ago)
    expired = {
        "version": 1,
        "created_at": (now - timedelta(days=31)).isoformat(),
        "expires_at": (now - timedelta(days=1)).isoformat(),
        "value": {"result": "expired data"},
    }
    (col_dir / "expired_entry.json").write_text(json.dumps(expired))

    return tmp_path


class TestManageCache:
    async def test_invalid_action(self):
        r = await manage_cache("bad")
        assert "Invalid action" in r

    async def test_status(self, fake_cache):
        r = await manage_cache("status")
        data = json.loads(r)
        assert data["total_entries"] == 2
        assert data["active_entries"] == 1
        assert data["expired_entries"] == 1
        assert "tools/call" in data["collections"]
        # hit_rate is present; no middleware in tests → zero totals
        hr = data["hit_rate"]
        assert hr["total"] == 0
        assert hr["hit_rate_pct"] is None
        # spillover stats present
        assert data["spillover"]["files"] == 0

    async def test_clear_expired(self, fake_cache):
        r = await manage_cache("clear_expired")
        data = json.loads(r)
        assert data["removed"] == 1
        assert data["kept"] == 1
        # Active entry still exists
        col_dir = fake_cache / "S_tools_call-abc123"
        assert (col_dir / "active_entry.json").exists()
        assert not (col_dir / "expired_entry.json").exists()

    async def test_clear_all(self, fake_cache):
        r = await manage_cache("clear")
        data = json.loads(r)
        assert data["removed"] == 2
        assert data["kept"] == 0
        # Collection directory should be removed
        col_dir = fake_cache / "S_tools_call-abc123"
        assert not col_dir.exists()

    async def test_no_cache_dir(self, tmp_path, monkeypatch):
        import fbi_crime_data_mcp.tools.cache as cache_mod

        monkeypatch.setattr(cache_mod, "_CACHE_DIR", tmp_path / "nonexistent")
        r = await manage_cache("status")
        assert "does not exist" in r

    async def test_empty_directory_in_info_skipped(self, tmp_path, monkeypatch):
        """Info file with empty directory should not scan CWD."""
        import fbi_crime_data_mcp.tools.cache as cache_mod

        monkeypatch.setattr(cache_mod, "_CACHE_DIR", tmp_path)
        info = {"version": 1, "collection": "bad", "directory": ""}
        (tmp_path / "S_bad-info.json").write_text(json.dumps(info))
        r = await manage_cache("status")
        data = json.loads(r)
        assert data["total_entries"] == 0

    async def test_directory_outside_cache_skipped(self, tmp_path, monkeypatch):
        """Info file pointing outside cache dir should be ignored."""
        import fbi_crime_data_mcp.tools.cache as cache_mod

        monkeypatch.setattr(cache_mod, "_CACHE_DIR", tmp_path)
        info = {"version": 1, "collection": "escape", "directory": "/tmp"}
        (tmp_path / "S_escape-info.json").write_text(json.dumps(info))
        r = await manage_cache("status")
        data = json.loads(r)
        assert data["total_entries"] == 0

    async def test_naive_datetime_handled(self, tmp_path, monkeypatch):
        """Naive ISO datetimes (no timezone) should not crash comparisons."""
        import fbi_crime_data_mcp.tools.cache as cache_mod

        monkeypatch.setattr(cache_mod, "_CACHE_DIR", tmp_path)
        col_dir = tmp_path / "S_naive-abc"
        col_dir.mkdir()
        info = {"version": 1, "collection": "naive", "directory": str(col_dir)}
        (tmp_path / "S_naive-abc-info.json").write_text(json.dumps(info))
        # Naive datetime (no +00:00 suffix), expired
        entry = {
            "version": 1,
            "created_at": "2020-01-01T00:00:00",
            "expires_at": "2020-02-01T00:00:00",
            "value": {},
        }
        (col_dir / "naive_entry.json").write_text(json.dumps(entry))
        r = await manage_cache("status")
        data = json.loads(r)
        assert data["total_entries"] == 1
        assert data["expired_entries"] == 1

    async def test_status_reports_spillover(self, tmp_path, monkeypatch):
        """Spillover files are counted in status output."""
        import fbi_crime_data_mcp.tools.cache as cache_mod

        monkeypatch.setattr(cache_mod, "_CACHE_DIR", tmp_path)
        monkeypatch.setattr(cache_mod, "_SPILLOVER_DIR", tmp_path / "spillover")

        spillover = tmp_path / "spillover"
        spillover.mkdir()
        (spillover / "tool_abc123.json").write_text('{"big": "data"}')
        (spillover / "tool_def456.json").write_text('{"more": "data"}')

        r = await manage_cache("status")
        data = json.loads(r)
        assert data["spillover"]["files"] == 2
        assert data["spillover"]["size_kb"] >= 0

    async def test_clear_removes_spillover(self, fake_cache, monkeypatch):
        """Full clear removes spillover directory."""
        import fbi_crime_data_mcp.tools.cache as cache_mod

        spillover = fake_cache / "spillover"
        spillover.mkdir()
        (spillover / "tool_abc123.json").write_text("big data")
        monkeypatch.setattr(cache_mod, "_SPILLOVER_DIR", spillover)

        r = await manage_cache("clear")
        data = json.loads(r)
        assert data["spillover_removed"] == 1
        assert not spillover.exists()

    async def test_status_includes_persisted_stats(self, fake_cache, monkeypatch):
        """Persisted stats from previous sessions are merged into hit_rate."""
        import fbi_crime_data_mcp.api_client as api_mod
        import fbi_crime_data_mcp.tools.cache as cache_mod

        stats_file = fake_cache / "stats.json"
        stats_file.write_text(json.dumps({"call_tool": {"hits": 10, "misses": 5}}))
        monkeypatch.setattr(cache_mod, "_STATS_FILE", stats_file)
        monkeypatch.setattr(api_mod, "STATS_FILE", stats_file)

        r = await manage_cache("status")
        data = json.loads(r)
        hr = data["hit_rate"]
        assert hr["hits"] == 10
        assert hr["misses"] == 5
        assert hr["total"] == 15

    async def test_clear_removes_stats_file(self, fake_cache, monkeypatch):
        """Full clear removes the persisted stats file."""
        import fbi_crime_data_mcp.api_client as api_client_mod
        import fbi_crime_data_mcp.tools.cache as cache_mod

        stats_file = fake_cache / "stats.json"
        stats_file.write_text(json.dumps({"call_tool": {"hits": 10, "misses": 5}}))
        monkeypatch.setattr(cache_mod, "_STATS_FILE", stats_file)
        monkeypatch.setattr(api_client_mod, "STATS_FILE", stats_file)

        await manage_cache("clear")
        assert not stats_file.exists()

    async def test_clear_resets_in_memory_middleware_stats(self, fake_cache, monkeypatch):
        """Full clear zeroes the in-memory hit/miss counters AND prevents a
        subsequent _save_stats from re-persisting the pre-clear totals.

        Regression for roborev job 2374: without _reset_middleware_stats(),
        the StatisticsWrapper retains its hit/miss counters across a clear,
        and the next lifespan shutdown re-persists those (now-stale) totals
        into the just-cleared stats file, silently undoing the clear.
        """
        from fastmcp.server.middleware.caching import ResponseCachingMiddleware
        from key_value.aio.stores.memory import MemoryStore
        from key_value.aio.wrappers.statistics.wrapper import KVStoreCollectionStatistics

        import fbi_crime_data_mcp.api_client as api_client_mod
        import fbi_crime_data_mcp.tools.cache as cache_mod

        # Build a real middleware so the isinstance() guard in
        # _reset_middleware_stats passes.
        mw = ResponseCachingMiddleware(cache_storage=MemoryStore())
        # Pre-populate the in-memory stats with non-zero counters under the
        # "tools/call" collection — that's what surfaces as `call_tool` in
        # ResponseCachingStatistics and CACHE_COLLECTION_NAMES.
        col_stats = KVStoreCollectionStatistics()
        col_stats.get.hit = 42
        col_stats.get.miss = 7
        mw._stats._statistics.collections["tools/call"] = col_stats

        monkeypatch.setattr(cache_mod.mcp, "middleware", [mw])

        stats_file = fake_cache / "stats.json"
        monkeypatch.setattr(cache_mod, "_STATS_FILE", stats_file)
        monkeypatch.setattr(api_client_mod, "STATS_FILE", stats_file)

        await manage_cache("clear")

        # In-memory counters cleared.
        assert mw._stats._statistics.collections == {}

        # A subsequent _save_stats must NOT re-introduce the pre-clear
        # totals. Without the reset, this would write hits=42, misses=7.
        _save_stats(cache_mod.mcp)
        persisted = _load_persisted_stats()
        assert persisted.get("call_tool", {"hits": 0, "misses": 0})["hits"] == 0
        assert persisted.get("call_tool", {"hits": 0, "misses": 0})["misses"] == 0

    async def test_clear_middleware_stats_tolerates_broken_internals(self, fake_cache, monkeypatch):
        """The reset is best-effort: if the private fastmcp/py-key-value
        layout changes and the expected ``_stats._statistics.collections``
        chain raises AttributeError, the clear must still succeed instead
        of crashing. Exercises the AttributeError fallback in
        _reset_middleware_stats.
        """
        from fastmcp.server.middleware.caching import ResponseCachingMiddleware
        from key_value.aio.stores.memory import MemoryStore

        import fbi_crime_data_mcp.tools.cache as cache_mod

        mw = ResponseCachingMiddleware(cache_storage=MemoryStore())
        # Swap _stats with an object that doesn't expose _statistics —
        # simulates a future refactor of the wrapper layout.
        mw._stats = object()

        monkeypatch.setattr(cache_mod.mcp, "middleware", [mw])

        # Must not raise.
        result = await manage_cache("clear")
        data = json.loads(result)
        assert data["action"] == "Cleared all entries"

    async def test_clear_expired_keeps_stats_file(self, fake_cache, monkeypatch):
        """Clearing expired entries does not remove persisted stats."""
        import fbi_crime_data_mcp.api_client as api_client_mod
        import fbi_crime_data_mcp.tools.cache as cache_mod

        stats_file = fake_cache / "stats.json"
        stats_file.write_text(json.dumps({"call_tool": {"hits": 10, "misses": 5}}))
        monkeypatch.setattr(cache_mod, "_STATS_FILE", stats_file)
        monkeypatch.setattr(api_client_mod, "STATS_FILE", stats_file)

        await manage_cache("clear_expired")
        assert stats_file.exists()

    async def test_clear_expired_keeps_spillover(self, fake_cache, monkeypatch):
        """Clearing expired entries does not touch spillover."""
        import fbi_crime_data_mcp.tools.cache as cache_mod

        spillover = fake_cache / "spillover"
        spillover.mkdir()
        (spillover / "tool_abc123.json").write_text("big data")
        monkeypatch.setattr(cache_mod, "_SPILLOVER_DIR", spillover)

        await manage_cache("clear_expired")
        assert spillover.exists()
        assert (spillover / "tool_abc123.json").exists()


class TestCacheEdgeCases:
    """Cover error/edge-case paths in cache status and clear."""

    async def test_corrupt_info_file_skipped(self, tmp_path, monkeypatch):
        """Corrupt JSON in info file is silently skipped."""
        import fbi_crime_data_mcp.tools.cache as cache_mod

        monkeypatch.setattr(cache_mod, "_CACHE_DIR", tmp_path)
        (tmp_path / "S_bad-info.json").write_text("not json{{")
        r = await manage_cache("status")
        data = json.loads(r)
        assert data["total_entries"] == 0

    async def test_corrupt_entry_file_skipped(self, tmp_path, monkeypatch):
        """Corrupt JSON in cache entry is silently skipped."""
        import fbi_crime_data_mcp.tools.cache as cache_mod

        monkeypatch.setattr(cache_mod, "_CACHE_DIR", tmp_path)
        col_dir = tmp_path / "S_col-abc"
        col_dir.mkdir()
        info = {"version": 1, "collection": "col", "directory": str(col_dir)}
        (tmp_path / "S_col-abc-info.json").write_text(json.dumps(info))
        (col_dir / "bad_entry.json").write_text("{{corrupt")
        r = await manage_cache("status")
        data = json.loads(r)
        assert data["total_entries"] == 0

    async def test_invalid_created_at_skipped(self, tmp_path, monkeypatch):
        """Invalid created_at datetime doesn't crash status."""
        import fbi_crime_data_mcp.tools.cache as cache_mod

        monkeypatch.setattr(cache_mod, "_CACHE_DIR", tmp_path)
        col_dir = tmp_path / "S_col-abc"
        col_dir.mkdir()
        info = {"version": 1, "collection": "col", "directory": str(col_dir)}
        (tmp_path / "S_col-abc-info.json").write_text(json.dumps(info))
        entry = {"created_at": "not-a-date", "expires_at": "also-bad"}
        (col_dir / "entry.json").write_text(json.dumps(entry))
        r = await manage_cache("status")
        data = json.loads(r)
        assert data["total_entries"] == 1
        assert data["oldest_entry"] is None

    async def test_entry_without_expires_kept_in_clear_expired(self, tmp_path, monkeypatch):
        """Entries without expires_at are kept during clear_expired."""
        import fbi_crime_data_mcp.tools.cache as cache_mod

        monkeypatch.setattr(cache_mod, "_CACHE_DIR", tmp_path)
        col_dir = tmp_path / "S_col-abc"
        col_dir.mkdir()
        info = {"version": 1, "collection": "col", "directory": str(col_dir)}
        (tmp_path / "S_col-abc-info.json").write_text(json.dumps(info))
        entry = {"created_at": "2026-01-01T00:00:00+00:00"}
        (col_dir / "no_expiry.json").write_text(json.dumps(entry))
        r = await manage_cache("clear_expired")
        data = json.loads(r)
        assert data["kept"] == 1
        assert data["removed"] == 0

    async def test_clear_expired_with_corrupt_entry(self, tmp_path, monkeypatch):
        """Corrupt entry during clear_expired is kept (not removed)."""
        import fbi_crime_data_mcp.tools.cache as cache_mod

        monkeypatch.setattr(cache_mod, "_CACHE_DIR", tmp_path)
        col_dir = tmp_path / "S_col-abc"
        col_dir.mkdir()
        info = {"version": 1, "collection": "col", "directory": str(col_dir)}
        (tmp_path / "S_col-abc-info.json").write_text(json.dumps(info))
        (col_dir / "corrupt.json").write_text("{{bad json")
        r = await manage_cache("clear_expired")
        data = json.loads(r)
        assert data["kept"] == 1
        assert data["removed"] == 0

    async def test_clear_corrupt_info_file_skipped(self, tmp_path, monkeypatch):
        """Corrupt info file during clear is skipped."""
        import fbi_crime_data_mcp.tools.cache as cache_mod

        monkeypatch.setattr(cache_mod, "_CACHE_DIR", tmp_path)
        (tmp_path / "S_bad-info.json").write_text("not json")
        r = await manage_cache("clear")
        data = json.loads(r)
        assert data["removed"] == 0

    async def test_spillover_dir_missing_returns_zero(self, tmp_path, monkeypatch):
        """_spillover_stats returns zeros when dir doesn't exist."""
        import fbi_crime_data_mcp.tools.cache as cache_mod

        monkeypatch.setattr(cache_mod, "_CACHE_DIR", tmp_path)
        monkeypatch.setattr(cache_mod, "_SPILLOVER_DIR", tmp_path / "nonexistent")
        r = await manage_cache("status")
        data = json.loads(r)
        assert data["spillover"] == {"files": 0, "size_kb": 0}


class TestSaveAndLoadPersistedStats:
    """Tests for _save_stats and _load_persisted_stats in api_client."""

    def test_save_stats_creates_file(self, tmp_path, monkeypatch):
        """_save_stats writes current session stats merged with persisted stats."""
        import fbi_crime_data_mcp.api_client as api_mod

        stats_file = tmp_path / "stats.json"
        monkeypatch.setattr(api_mod, "STATS_FILE", stats_file)

        monkeypatch.setattr(
            api_mod,
            "_collect_stats",
            lambda server: {"call_tool": {"hits": 5, "misses": 3}},
        )

        mock_server = MagicMock()
        _save_stats(mock_server)

        assert stats_file.exists()
        data = json.loads(stats_file.read_text())
        assert data["call_tool"]["hits"] == 5
        assert data["call_tool"]["misses"] == 3

    def test_save_stats_merges_with_existing(self, tmp_path, monkeypatch):
        """_save_stats merges current stats with previously persisted stats."""
        import fbi_crime_data_mcp.api_client as api_mod

        stats_file = tmp_path / "stats.json"
        # Pre-populate with existing stats
        stats_file.write_text(json.dumps({"call_tool": {"hits": 10, "misses": 5}}))
        monkeypatch.setattr(api_mod, "STATS_FILE", stats_file)

        # Mock _collect_stats to return current session stats
        monkeypatch.setattr(
            api_mod,
            "_collect_stats",
            lambda server: {"call_tool": {"hits": 3, "misses": 2}},
        )

        mock_server = MagicMock()
        _save_stats(mock_server)

        data = json.loads(stats_file.read_text())
        assert data["call_tool"]["hits"] == 13  # 10 + 3
        assert data["call_tool"]["misses"] == 7  # 5 + 2

    def test_save_stats_merges_new_collection(self, tmp_path, monkeypatch):
        """_save_stats adds new collections alongside existing ones."""
        import fbi_crime_data_mcp.api_client as api_mod

        stats_file = tmp_path / "stats.json"
        stats_file.write_text(json.dumps({"call_tool": {"hits": 10, "misses": 5}}))
        monkeypatch.setattr(api_mod, "STATS_FILE", stats_file)

        monkeypatch.setattr(
            api_mod,
            "_collect_stats",
            lambda server: {"list_tools": {"hits": 1, "misses": 1}},
        )

        mock_server = MagicMock()
        _save_stats(mock_server)

        data = json.loads(stats_file.read_text())
        assert data["call_tool"] == {"hits": 10, "misses": 5}
        assert data["list_tools"] == {"hits": 1, "misses": 1}

    def test_load_persisted_stats_missing_file(self, tmp_path, monkeypatch):
        """_load_persisted_stats returns empty dict when file doesn't exist."""
        import fbi_crime_data_mcp.api_client as api_mod

        monkeypatch.setattr(api_mod, "STATS_FILE", tmp_path / "nonexistent.json")
        assert _load_persisted_stats() == {}

    def test_load_persisted_stats_invalid_json(self, tmp_path, monkeypatch):
        """_load_persisted_stats returns empty dict on invalid JSON."""
        import fbi_crime_data_mcp.api_client as api_mod

        stats_file = tmp_path / "stats.json"
        stats_file.write_text("not json")
        monkeypatch.setattr(api_mod, "STATS_FILE", stats_file)
        assert _load_persisted_stats() == {}

    def test_load_persisted_stats_non_dict_counts(self, tmp_path, monkeypatch):
        """Non-dict counts values are dropped during normalization."""
        import fbi_crime_data_mcp.api_client as api_mod

        stats_file = tmp_path / "stats.json"
        stats_file.write_text(json.dumps({"col": "not_a_dict"}))
        monkeypatch.setattr(api_mod, "STATS_FILE", stats_file)
        assert _load_persisted_stats() == {}

    def test_load_persisted_stats_non_int_hits_misses(self, tmp_path, monkeypatch):
        """Non-int hit/miss values are coerced to zero."""
        import fbi_crime_data_mcp.api_client as api_mod

        stats_file = tmp_path / "stats.json"
        stats_file.write_text(json.dumps({"col": {"hits": "bad", "misses": None}}))
        monkeypatch.setattr(api_mod, "STATS_FILE", stats_file)
        assert _load_persisted_stats() == {"col": {"hits": 0, "misses": 0}}

    def test_load_persisted_stats_negative_values_clamped(self, tmp_path, monkeypatch):
        """Negative hit/miss values are clamped to zero."""
        import fbi_crime_data_mcp.api_client as api_mod

        stats_file = tmp_path / "stats.json"
        stats_file.write_text(json.dumps({"col": {"hits": -3, "misses": -1}}))
        monkeypatch.setattr(api_mod, "STATS_FILE", stats_file)
        assert _load_persisted_stats() == {"col": {"hits": 0, "misses": 0}}

    def test_load_persisted_stats_non_dict_root(self, tmp_path, monkeypatch):
        """Non-dict root value returns empty dict."""
        import fbi_crime_data_mcp.api_client as api_mod

        stats_file = tmp_path / "stats.json"
        stats_file.write_text(json.dumps([1, 2, 3]))
        monkeypatch.setattr(api_mod, "STATS_FILE", stats_file)
        assert _load_persisted_stats() == {}

    def test_save_stats_handles_oserror(self, tmp_path, monkeypatch):
        """_save_stats doesn't crash when write fails."""
        from unittest.mock import patch

        import fbi_crime_data_mcp.api_client as api_mod

        stats_file = tmp_path / "stats.json"
        monkeypatch.setattr(api_mod, "STATS_FILE", stats_file)
        monkeypatch.setattr(api_mod, "_collect_stats", lambda s: {})

        with patch.object(type(stats_file), "write_text", side_effect=OSError("disk full")):
            _save_stats(MagicMock())  # should not raise

    def test_load_persisted_stats_mixed_valid_invalid(self, tmp_path, monkeypatch):
        """Valid entries are kept while invalid ones are dropped."""
        import fbi_crime_data_mcp.api_client as api_mod

        stats_file = tmp_path / "stats.json"
        stats_file.write_text(
            json.dumps(
                {
                    "good": {"hits": 10, "misses": 5},
                    "bad_counts": "string",
                    "bad_values": {"hits": [], "misses": {}},
                }
            )
        )
        monkeypatch.setattr(api_mod, "STATS_FILE", stats_file)
        result = _load_persisted_stats()
        assert result == {
            "good": {"hits": 10, "misses": 5},
            "bad_values": {"hits": 0, "misses": 0},
        }


class TestCacheOSErrorPaths:
    """Cover OSError paths that require mocking (stat, unlink, rmtree)."""

    async def test_stat_oserror_in_status_skips_entry(self, tmp_path, monkeypatch):
        """OSError on entry stat during status is silently skipped."""
        from unittest.mock import patch

        import fbi_crime_data_mcp.tools.cache as cache_mod

        monkeypatch.setattr(cache_mod, "_CACHE_DIR", tmp_path)
        col_dir = tmp_path / "S_col-abc"
        col_dir.mkdir()
        info = {"version": 1, "collection": "col", "directory": str(col_dir)}
        (tmp_path / "S_col-abc-info.json").write_text(json.dumps(info))
        entry = {"created_at": "2026-01-01T00:00:00+00:00", "expires_at": "2027-01-01T00:00:00+00:00"}
        entry_file = col_dir / "entry.json"
        entry_file.write_text(json.dumps(entry))

        def failing_stat(*a, **kw):
            raise OSError("stat failed")

        with patch.object(type(entry_file), "stat", new=property(lambda self: failing_stat)):
            # stat is called as method, need different approach
            pass

        # Simpler: make entry valid JSON but stat fails via monkeypatch
        import pathlib

        original_path_stat = pathlib.Path.stat

        def patched_stat(self, *args, **kwargs):
            if self.name == "entry.json":
                raise OSError("stat failed")
            return original_path_stat(self, *args, **kwargs)

        with patch.object(pathlib.Path, "stat", patched_stat):
            r = await manage_cache("status")
            data = json.loads(r)
            # Entry was read (JSON parsed) but stat failed, so it's skipped
            assert data["total_entries"] == 0

    async def test_safe_collection_dir_not_a_dir(self, tmp_path, monkeypatch):
        """_safe_collection_dir returns None when path exists but is a file, not dir."""
        import fbi_crime_data_mcp.tools.cache as cache_mod

        monkeypatch.setattr(cache_mod, "_CACHE_DIR", tmp_path)
        # Create a file where a directory is expected
        fake_dir = tmp_path / "S_col-abc"
        fake_dir.write_text("not a directory")
        info = {"version": 1, "collection": "col", "directory": str(fake_dir)}
        (tmp_path / "S_col-abc-info.json").write_text(json.dumps(info))
        r = await manage_cache("status")
        data = json.loads(r)
        assert data["total_entries"] == 0

    async def test_unlink_oserror_in_clear(self, tmp_path, monkeypatch):
        """OSError on entry unlink during clear continues gracefully."""
        import pathlib
        from unittest.mock import patch

        import fbi_crime_data_mcp.tools.cache as cache_mod

        monkeypatch.setattr(cache_mod, "_CACHE_DIR", tmp_path)
        monkeypatch.setattr(cache_mod, "_SPILLOVER_DIR", tmp_path / "no_spillover")
        monkeypatch.setattr(cache_mod, "_STATS_FILE", tmp_path / "no_stats.json")
        col_dir = tmp_path / "S_col-abc"
        col_dir.mkdir()
        info = {"version": 1, "collection": "col", "directory": str(col_dir)}
        (tmp_path / "S_col-abc-info.json").write_text(json.dumps(info))
        (col_dir / "entry.json").write_text(json.dumps({"data": 1}))

        original_unlink = pathlib.Path.unlink

        def patched_unlink(self, *args, **kwargs):
            if self.name == "entry.json":
                raise OSError("cannot unlink")
            return original_unlink(self, *args, **kwargs)

        with patch.object(pathlib.Path, "unlink", patched_unlink):
            r = await manage_cache("clear")
            data = json.loads(r)
            assert data["removed"] == 0  # unlink failed

    async def test_rmtree_oserror_in_clear(self, tmp_path, monkeypatch):
        """OSError on rmtree during clear doesn't crash."""
        from unittest.mock import patch

        import fbi_crime_data_mcp.tools.cache as cache_mod

        monkeypatch.setattr(cache_mod, "_CACHE_DIR", tmp_path)
        monkeypatch.setattr(cache_mod, "_SPILLOVER_DIR", tmp_path / "no_spillover")
        monkeypatch.setattr(cache_mod, "_STATS_FILE", tmp_path / "no_stats.json")
        col_dir = tmp_path / "S_col-abc"
        col_dir.mkdir()
        info = {"version": 1, "collection": "col", "directory": str(col_dir)}
        (tmp_path / "S_col-abc-info.json").write_text(json.dumps(info))

        with patch("fbi_crime_data_mcp.tools.cache.shutil.rmtree", side_effect=OSError("rmtree failed")):
            r = await manage_cache("clear")
            # Should complete without raising
            data = json.loads(r)
            assert data["removed"] == 0

    async def test_spillover_rmtree_oserror(self, tmp_path, monkeypatch):
        """OSError on spillover rmtree during clear doesn't crash."""
        from unittest.mock import patch

        import fbi_crime_data_mcp.tools.cache as cache_mod

        monkeypatch.setattr(cache_mod, "_CACHE_DIR", tmp_path)
        monkeypatch.setattr(cache_mod, "_STATS_FILE", tmp_path / "no_stats.json")
        spillover = tmp_path / "spillover"
        spillover.mkdir()
        (spillover / "file.json").write_text("data")
        monkeypatch.setattr(cache_mod, "_SPILLOVER_DIR", spillover)

        original_rmtree = __import__("shutil").rmtree

        def patched_rmtree(path, *args, **kwargs):
            if "spillover" in str(path):
                raise OSError("rmtree failed")
            return original_rmtree(path, *args, **kwargs)

        with patch("fbi_crime_data_mcp.tools.cache.shutil.rmtree", side_effect=patched_rmtree):
            r = await manage_cache("clear")
            data = json.loads(r)
            assert data["spillover_removed"] == 0

    async def test_stats_unlink_oserror(self, tmp_path, monkeypatch):
        """OSError on stats file unlink during clear doesn't crash."""
        import pathlib
        from unittest.mock import patch

        import fbi_crime_data_mcp.tools.cache as cache_mod

        monkeypatch.setattr(cache_mod, "_CACHE_DIR", tmp_path)
        monkeypatch.setattr(cache_mod, "_SPILLOVER_DIR", tmp_path / "no_spillover")
        stats_file = tmp_path / "stats.json"
        stats_file.write_text("{}")
        monkeypatch.setattr(cache_mod, "_STATS_FILE", stats_file)

        original_unlink = pathlib.Path.unlink

        def patched_unlink(self, *args, **kwargs):
            if self.name == "stats.json":
                raise OSError("cannot unlink")
            return original_unlink(self, *args, **kwargs)

        with patch.object(pathlib.Path, "unlink", patched_unlink):
            r = await manage_cache("clear")
            # Should complete without raising
            json.loads(r)

    async def test_spillover_safe_size_oserror(self, tmp_path, monkeypatch):
        """OSError in _safe_size returns 0 for that file."""
        import pathlib
        from unittest.mock import patch

        import fbi_crime_data_mcp.tools.cache as cache_mod

        monkeypatch.setattr(cache_mod, "_CACHE_DIR", tmp_path)
        spillover = tmp_path / "spillover"
        spillover.mkdir()
        (spillover / "file.json").write_text("data")
        monkeypatch.setattr(cache_mod, "_SPILLOVER_DIR", spillover)

        original_stat = pathlib.Path.stat

        def patched_stat(self, *args, **kwargs):
            if self.parent == spillover and self.suffix == ".json":
                raise OSError("stat failed")
            return original_stat(self, *args, **kwargs)

        with patch.object(pathlib.Path, "stat", patched_stat):
            r = await manage_cache("status")
            data = json.loads(r)
            assert data["spillover"]["files"] == 1
            assert data["spillover"]["size_kb"] == 0

    async def test_clear_invalid_collection_dir_skipped(self, tmp_path, monkeypatch):
        """Clear skips info files with invalid collection directories."""
        import fbi_crime_data_mcp.tools.cache as cache_mod

        monkeypatch.setattr(cache_mod, "_CACHE_DIR", tmp_path)
        monkeypatch.setattr(cache_mod, "_SPILLOVER_DIR", tmp_path / "no_spillover")
        monkeypatch.setattr(cache_mod, "_STATS_FILE", tmp_path / "no_stats.json")
        # Valid JSON but directory doesn't exist
        info = {"version": 1, "collection": "col", "directory": str(tmp_path / "nonexistent")}
        (tmp_path / "S_col-info.json").write_text(json.dumps(info))
        r = await manage_cache("clear")
        data = json.loads(r)
        assert data["removed"] == 0


class TestHitRateSessionStats:
    """_hit_rate merges live middleware counters with persisted history."""

    async def test_session_counters_merge_with_persisted(self, fake_cache, monkeypatch):
        from fastmcp.server.middleware.caching import ResponseCachingMiddleware
        from key_value.aio.stores.memory import MemoryStore
        from key_value.aio.wrappers.statistics.wrapper import KVStoreCollectionStatistics

        import fbi_crime_data_mcp.tools.cache as cache_mod

        # Persisted history from a previous session
        (fake_cache / "stats.json").write_text(json.dumps({"call_tool": {"hits": 10, "misses": 5}}))

        # Live middleware: tools/call has traffic, tools/list is present but idle
        mw = ResponseCachingMiddleware(cache_storage=MemoryStore())
        busy = KVStoreCollectionStatistics()
        busy.get.hit = 42
        busy.get.miss = 7
        idle = KVStoreCollectionStatistics()
        mw._stats._statistics.collections["tools/call"] = busy
        mw._stats._statistics.collections["tools/list"] = idle
        monkeypatch.setattr(cache_mod.mcp, "middleware", [mw])

        data = json.loads(await manage_cache("status"))
        hit_rate = data["hit_rate"]

        assert hit_rate["collections"]["call_tool"] == {
            "hits": 52,
            "misses": 12,
            "total": 64,
            "hit_rate_pct": 81.2,
        }
        # Idle collections contribute nothing and are not listed
        assert "list_tools" not in hit_rate["collections"]
        assert (hit_rate["hits"], hit_rate["misses"], hit_rate["total"]) == (52, 12, 64)

    async def test_session_counters_without_persisted_history(self, fake_cache, monkeypatch):
        from fastmcp.server.middleware.caching import ResponseCachingMiddleware
        from key_value.aio.stores.memory import MemoryStore
        from key_value.aio.wrappers.statistics.wrapper import KVStoreCollectionStatistics

        import fbi_crime_data_mcp.tools.cache as cache_mod

        mw = ResponseCachingMiddleware(cache_storage=MemoryStore())
        col = KVStoreCollectionStatistics()
        col.get.hit = 3
        col.get.miss = 1
        mw._stats._statistics.collections["tools/call"] = col
        monkeypatch.setattr(cache_mod.mcp, "middleware", [mw])

        data = json.loads(await manage_cache("status"))
        assert data["hit_rate"]["collections"]["call_tool"]["hits"] == 3
        assert data["hit_rate"]["collections"]["call_tool"]["misses"] == 1


class TestInfoFileUnlinkOSError:
    async def test_info_file_unlink_oserror_in_clear(self, fake_cache, monkeypatch):
        """OSError unlinking the collection info file during a full clear is swallowed."""
        import pathlib
        from unittest.mock import patch

        import fbi_crime_data_mcp.tools.cache as cache_mod

        monkeypatch.setattr(cache_mod, "_SPILLOVER_DIR", fake_cache / "no_spillover")

        original_unlink = pathlib.Path.unlink

        def patched_unlink(self, *args, **kwargs):
            if self.name.endswith("-info.json"):
                raise OSError("cannot unlink info file")
            return original_unlink(self, *args, **kwargs)

        with patch.object(pathlib.Path, "unlink", patched_unlink):
            data = json.loads(await manage_cache("clear"))

        # Entries were still removed; only the info file survived
        assert data["removed"] == 2
        assert (fake_cache / "S_tools_call-abc123-info.json").exists()
