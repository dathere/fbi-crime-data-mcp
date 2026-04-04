"""Tests for ResponseSpilloverMiddleware."""

from __future__ import annotations

from unittest.mock import AsyncMock

from fastmcp.server.middleware.middleware import MiddlewareContext
from fastmcp.tools.base import ToolResult
from mcp.types import TextContent

from fbi_crime_data_mcp.spillover import ResponseSpilloverMiddleware


class _FakeParams:
    """Minimal stand-in for CallToolRequestParams."""

    def __init__(self, name: str):
        self.name = name


def _make_context(tool_name: str = "get_nibrs_data") -> MiddlewareContext:
    return MiddlewareContext(
        message=_FakeParams(tool_name),
        method="tools/call",
    )


def _make_result(text: str) -> ToolResult:
    return ToolResult(content=[TextContent(type="text", text=text)])


class TestSpilloverMiddleware:
    async def test_small_response_passes_through(self, tmp_path, monkeypatch):
        import fbi_crime_data_mcp.spillover as mod

        monkeypatch.setattr(mod, "SPILLOVER_DIR", tmp_path / "spillover")

        mw = ResponseSpilloverMiddleware(max_chars=1000)
        small = _make_result('{"data": "small"}')
        call_next = AsyncMock(return_value=small)

        result = await mw.on_call_tool(_make_context(), call_next)

        assert result is small
        assert not (tmp_path / "spillover").exists()

    async def test_large_response_spills_to_file(self, tmp_path, monkeypatch):
        import fbi_crime_data_mcp.spillover as mod

        monkeypatch.setattr(mod, "SPILLOVER_DIR", tmp_path / "spillover")

        mw = ResponseSpilloverMiddleware(max_chars=100, preview_chars=50)
        big_text = "x" * 200
        call_next = AsyncMock(return_value=_make_result(big_text))

        result = await mw.on_call_tool(_make_context(), call_next)

        # Response is truncated with metadata
        text = result.content[0].text
        assert "200 characters" in text
        assert "PREVIEW" in text
        assert str(tmp_path / "spillover") in text

        # Full content is on disk
        spillover_files = list((tmp_path / "spillover").glob("*.json"))
        assert len(spillover_files) == 1
        assert spillover_files[0].read_text() == big_text

    async def test_duplicate_response_reuses_file(self, tmp_path, monkeypatch):
        import fbi_crime_data_mcp.spillover as mod

        monkeypatch.setattr(mod, "SPILLOVER_DIR", tmp_path / "spillover")

        mw = ResponseSpilloverMiddleware(max_chars=100, preview_chars=50)
        big_text = "y" * 200
        call_next = AsyncMock(return_value=_make_result(big_text))

        await mw.on_call_tool(_make_context(), call_next)
        await mw.on_call_tool(_make_context(), call_next)

        # Only one file despite two calls
        spillover_files = list((tmp_path / "spillover").glob("*.json"))
        assert len(spillover_files) == 1

    async def test_excluded_tool_not_spilled(self, tmp_path, monkeypatch):
        import fbi_crime_data_mcp.spillover as mod

        monkeypatch.setattr(mod, "SPILLOVER_DIR", tmp_path / "spillover")

        mw = ResponseSpilloverMiddleware(max_chars=100, excluded_tools={"manage_cache"})
        big = _make_result("z" * 200)
        call_next = AsyncMock(return_value=big)

        result = await mw.on_call_tool(_make_context("manage_cache"), call_next)

        assert result is big
        assert not (tmp_path / "spillover").exists()

    async def test_filename_contains_tool_name(self, tmp_path, monkeypatch):
        import fbi_crime_data_mcp.spillover as mod

        monkeypatch.setattr(mod, "SPILLOVER_DIR", tmp_path / "spillover")

        mw = ResponseSpilloverMiddleware(max_chars=100, preview_chars=50)
        call_next = AsyncMock(return_value=_make_result("a" * 200))

        await mw.on_call_tool(_make_context("lookup_agency"), call_next)

        spillover_files = list((tmp_path / "spillover").glob("*.json"))
        assert len(spillover_files) == 1
        assert spillover_files[0].name.startswith("lookup_agency_")
