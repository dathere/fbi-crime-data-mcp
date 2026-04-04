"""Tests for manage_cache tool."""

import json
from datetime import UTC, datetime, timedelta

import pytest

from fbi_crime_data_mcp.tools.cache import manage_cache


@pytest.fixture
def fake_cache(tmp_path, monkeypatch):
    """Create a fake cache directory with test entries."""
    import fbi_crime_data_mcp.tools.cache as cache_mod

    monkeypatch.setattr(cache_mod, "_CACHE_DIR", tmp_path)

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
        # session_hit_rate is present; no middleware in tests → zero totals
        hr = data["session_hit_rate"]
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
