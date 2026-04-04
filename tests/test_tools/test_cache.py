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
