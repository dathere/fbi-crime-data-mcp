"""Tests for manage_cache tool."""

import json
from datetime import datetime, timedelta, timezone

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

    now = datetime.now(tz=timezone.utc)

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
