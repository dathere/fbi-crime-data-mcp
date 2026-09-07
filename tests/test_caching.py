"""Tests for ErrorAwareCachingMiddleware."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastmcp.server.middleware.caching import CallToolSettings, ResponseCachingMiddleware
from fastmcp.server.middleware.middleware import MiddlewareContext
from fastmcp.tools.base import ToolResult
from key_value.aio.stores.memory import MemoryStore
from mcp.types import CallToolRequestParams, TextContent

from fbi_crime_data_mcp.caching import (
    UNCACHEABLE_PREFIXES,
    ErrorAwareCachingMiddleware,
    is_uncacheable_result,
)

TOOL = "get_nibrs_data"


def _make_context(tool_name: str = TOOL, **arguments) -> MiddlewareContext:
    return MiddlewareContext(
        message=CallToolRequestParams(name=tool_name, arguments=arguments or {"offense": "13A"}),
        method="tools/call",
    )


def _make_result(text: str) -> ToolResult:
    return ToolResult(content=[TextContent(type="text", text=text)])


def _make_middleware(included_tools: list[str] | None = None) -> ErrorAwareCachingMiddleware:
    return ErrorAwareCachingMiddleware(
        cache_storage=MemoryStore(),
        call_tool_settings=CallToolSettings(ttl=3600, included_tools=included_tools or [TOOL]),
    )


class TestIsUncacheableResult:
    @pytest.mark.parametrize("prefix", UNCACHEABLE_PREFIXES)
    def test_matches_each_prefix(self, prefix):
        assert is_uncacheable_result(_make_result(f"{prefix} something went wrong"))

    @pytest.mark.parametrize(
        "text",
        [
            '{"ok": true}',
            "Invalid level. Must be 'national', 'state', or 'agency'.",
            "Parameter 'state' is required when level is 'state'.",
            "NOTE: Response was 200,000 characters, which exceeds the limit.",
            "",
        ],
    )
    def test_success_and_validation_strings_are_cacheable(self, text):
        assert not is_uncacheable_result(_make_result(text))

    def test_prefix_must_be_at_start(self):
        assert not is_uncacheable_result(_make_result('{"note": "Error: embedded"}'))

    def test_any_error_block_marks_result(self):
        result = ToolResult(
            content=[
                TextContent(type="text", text='{"ok": true}'),
                TextContent(type="text", text="Error: partial failure"),
            ]
        )
        assert is_uncacheable_result(result)

    def test_non_text_content_ignored(self):
        assert not is_uncacheable_result(ToolResult(content=[]))


class TestErrorAwareCachingMiddleware:
    def test_is_a_response_caching_middleware(self):
        # cache.py and api_client._collect_stats discover cache middleware via isinstance
        assert isinstance(_make_middleware(), ResponseCachingMiddleware)

    async def test_success_is_cached(self):
        mw = _make_middleware()
        call_next = AsyncMock(return_value=_make_result('{"ok": true}'))

        first = await mw.on_call_tool(_make_context(), call_next)
        second = await mw.on_call_tool(_make_context(), call_next)

        assert call_next.await_count == 1
        assert first.content[0].text == second.content[0].text == '{"ok": true}'

    @pytest.mark.parametrize(
        "error_text",
        [
            "Error: Request timed out. The FBI API may be slow — try again.",
            "Error: Network error connecting to FBI API. Check your connection and try again.",
            "Error: FBI API rate limit exceeded (HTTP 429). Wait a few minutes before retrying.",
            "Error: FBI API server error (HTTP 503). Try again later.",
            "Rate limit reached (1000 requests per 1 hour). Try again in ~42 seconds.",
        ],
    )
    async def test_transient_error_is_not_cached(self, error_text):
        mw = _make_middleware()
        call_next = AsyncMock(return_value=_make_result(error_text))

        first = await mw.on_call_tool(_make_context(), call_next)
        second = await mw.on_call_tool(_make_context(), call_next)

        assert call_next.await_count == 2, "error response was served from cache"
        assert first.content[0].text == error_text
        assert second.content[0].text == error_text

    async def test_error_then_success_caches_the_success(self):
        mw = _make_middleware()
        call_next = AsyncMock(
            side_effect=[
                _make_result("Error: FBI API server error (HTTP 500). Try again later."),
                _make_result('{"ok": true}'),
                _make_result("should not be reached"),
            ]
        )

        first = await mw.on_call_tool(_make_context(), call_next)
        second = await mw.on_call_tool(_make_context(), call_next)
        third = await mw.on_call_tool(_make_context(), call_next)

        assert first.content[0].text.startswith("Error:")
        assert second.content[0].text == '{"ok": true}'
        assert third.content[0].text == '{"ok": true}'
        assert call_next.await_count == 2

    async def test_validation_error_is_cached(self):
        # Deterministic, no network: caching is harmless and matches parent behaviour
        mw = _make_middleware()
        call_next = AsyncMock(return_value=_make_result("Invalid level. Must be 'national'."))

        await mw.on_call_tool(_make_context(), call_next)
        await mw.on_call_tool(_make_context(), call_next)

        assert call_next.await_count == 1

    async def test_cache_key_includes_arguments(self):
        mw = _make_middleware()
        call_next = AsyncMock(return_value=_make_result('{"ok": true}'))

        await mw.on_call_tool(_make_context(offense="13A"), call_next)
        await mw.on_call_tool(_make_context(offense="09A"), call_next)

        assert call_next.await_count == 2

    async def test_excluded_tool_bypasses_cache_entirely(self):
        mw = _make_middleware(included_tools=["some_other_tool"])
        call_next = AsyncMock(return_value=_make_result('{"ok": true}'))

        await mw.on_call_tool(_make_context(), call_next)
        await mw.on_call_tool(_make_context(), call_next)

        assert call_next.await_count == 2

    async def test_records_hit_and_miss_statistics(self):
        mw = _make_middleware()
        call_next = AsyncMock(return_value=_make_result('{"ok": true}'))

        await mw.on_call_tool(_make_context(), call_next)
        await mw.on_call_tool(_make_context(), call_next)

        stats = mw.statistics().call_tool
        assert stats is not None
        assert stats.get.miss == 1
        assert stats.get.hit == 1
