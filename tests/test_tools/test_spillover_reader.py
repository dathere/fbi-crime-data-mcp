"""Tests for read_spillover tool."""

import json
import os

import pytest

from fbi_crime_data_mcp.tools.spillover_reader import read_spillover


@pytest.fixture
def spillover_dir(tmp_path, monkeypatch):
    """Create a fake spillover directory with test files."""
    import fbi_crime_data_mcp.tools.spillover_reader as mod

    spillover = tmp_path / "spillover"
    spillover.mkdir()
    monkeypatch.setattr(mod, "SPILLOVER_DIR", spillover)

    # Create a sample spillover file
    content = "A" * 1000 + "B" * 1000 + "C" * 500
    (spillover / "get_nibrs_data_abc12345.json").write_text(content)

    return spillover


class TestReadSpillover:
    @pytest.mark.anyio
    async def test_list_files(self, spillover_dir):
        result = await read_spillover(filename="list")
        parsed = json.loads(result)
        assert len(parsed["spillover_files"]) == 1
        assert parsed["spillover_files"][0]["filename"] == "get_nibrs_data_abc12345.json"

    @pytest.mark.anyio
    async def test_list_empty(self, tmp_path, monkeypatch):
        import fbi_crime_data_mcp.tools.spillover_reader as mod

        empty = tmp_path / "empty_spillover"
        empty.mkdir()
        monkeypatch.setattr(mod, "SPILLOVER_DIR", empty)
        result = await read_spillover(filename="list")
        assert "No spillover files found" in result

    @pytest.mark.anyio
    async def test_read_full_file(self, spillover_dir):
        result = await read_spillover(filename="get_nibrs_data_abc12345.json")
        assert "Total: 2,500 chars" in result
        assert "AAAA" in result

    @pytest.mark.anyio
    async def test_read_with_offset(self, spillover_dir):
        result = await read_spillover(
            filename="get_nibrs_data_abc12345.json", offset=1000, limit=500
        )
        assert "Showing: 1,000-1,500" in result
        # offset=1000 lands in the B section
        assert "BBB" in result

    @pytest.mark.anyio
    async def test_read_with_remaining(self, spillover_dir):
        result = await read_spillover(
            filename="get_nibrs_data_abc12345.json", offset=0, limit=100
        )
        assert "Remaining:" in result
        assert "use offset=100 to continue" in result

    @pytest.mark.anyio
    async def test_file_not_found(self, spillover_dir):
        result = await read_spillover(filename="nonexistent.json")
        assert "File not found" in result
        # Should also show available files
        assert "spillover_files" in result

    @pytest.mark.anyio
    async def test_path_traversal_slash(self, spillover_dir):
        result = await read_spillover(filename="../etc/passwd")
        assert "Invalid filename" in result

    @pytest.mark.anyio
    async def test_path_traversal_backslash(self, spillover_dir):
        result = await read_spillover(filename="..\\etc\\passwd")
        # On POSIX, backslash is a valid filename char, so this resolves
        # inside SPILLOVER_DIR but the file doesn't exist
        assert "File not found" in result or "Invalid filename" in result

    @pytest.mark.anyio
    async def test_path_traversal_resolve(self, spillover_dir):
        # Even without explicit .. or /, symlinks or odd names should fail
        # if they resolve outside SPILLOVER_DIR
        result = await read_spillover(filename="..%2F..%2Fetc%2Fpasswd")
        # This won't resolve outside, but the file won't exist
        assert "File not found" in result or "Invalid filename" in result

    @pytest.mark.anyio
    async def test_path_traversal_symlink(self, spillover_dir, tmp_path):
        """Symlink inside spillover dir pointing outside must be rejected by resolve()+relative_to()."""
        outside_file = tmp_path / "secret.txt"
        outside_file.write_text("sensitive data")
        symlink_path = spillover_dir / "legit_looking.json"
        os.symlink(outside_file, symlink_path)
        result = await read_spillover(filename="legit_looking.json")
        assert "Invalid filename" in result

    @pytest.mark.anyio
    async def test_negative_offset(self, spillover_dir):
        result = await read_spillover(
            filename="get_nibrs_data_abc12345.json", offset=-1
        )
        assert "Invalid offset" in result

    @pytest.mark.anyio
    async def test_zero_limit(self, spillover_dir):
        result = await read_spillover(
            filename="get_nibrs_data_abc12345.json", limit=0
        )
        assert "Invalid limit" in result

    @pytest.mark.anyio
    async def test_negative_limit(self, spillover_dir):
        result = await read_spillover(
            filename="get_nibrs_data_abc12345.json", limit=-5
        )
        assert "Invalid limit" in result

    @pytest.mark.anyio
    async def test_offset_past_end(self, spillover_dir):
        result = await read_spillover(
            filename="get_nibrs_data_abc12345.json", offset=999_999
        )
        assert "past end of file" in result
        assert "Total: 2,500 chars" in result

    @pytest.mark.anyio
    async def test_limit_capped_at_max(self, spillover_dir):
        """Requesting more than _MAX_LIMIT should be capped, not rejected."""
        result = await read_spillover(
            filename="get_nibrs_data_abc12345.json", limit=999_999
        )
        # Should succeed (file is only 2500 chars anyway)
        assert "Total: 2,500 chars" in result
