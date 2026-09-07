"""Response caching middleware that refuses to cache transient error results."""

from __future__ import annotations

import mcp.types as mt
from fastmcp.server.middleware.caching import (
    ONE_HOUR_IN_SECONDS,
    CachableToolResult,
    ResponseCachingMiddleware,
    _make_call_tool_cache_key,
)
from fastmcp.server.middleware.middleware import CallNext, MiddlewareContext
from fastmcp.tools.base import ToolResult
from mcp.types import TextContent

__all__ = ["ErrorAwareCachingMiddleware", "is_uncacheable_result"]

# Tools in this project never raise; transport-level failures come back as
# plain strings from api_client.api_get. FastMCP's ResponseCachingMiddleware
# caches every ToolResult it sees, so without this guard a timeout, network
# blip, HTTP 5xx/429, or the in-process rate limiter's message would be
# replayed for the full TTL (30-90 days) for that exact argument set.
#
# Validation errors ("Invalid ...", "Parameter ...") are deterministic and
# never hit the network, so caching them is harmless and they are not listed.
UNCACHEABLE_PREFIXES: tuple[str, ...] = ("Error:", "Rate limit reached")


def is_uncacheable_result(result: ToolResult) -> bool:
    """Return True if any text block in *result* looks like a transient error."""
    for block in result.content:
        if isinstance(block, TextContent) and block.text.startswith(UNCACHEABLE_PREFIXES):
            return True
    return False


class ErrorAwareCachingMiddleware(ResponseCachingMiddleware):
    """``ResponseCachingMiddleware`` that skips storing error responses.

    Mirrors the parent's ``on_call_tool`` exactly, except that a result matching
    ``UNCACHEABLE_PREFIXES`` is returned to the caller without being written to
    the cache. Cache reads are unaffected.

    This relies on the parent's private ``_call_tool_settings``,
    ``_matches_tool_cache_settings``, ``_call_tool_cache`` and the module-level
    ``_make_call_tool_cache_key`` (fastmcp 3.2). ``tests/test_caching.py``
    exercises the full path, so a fastmcp bump that changes that layout will
    fail CI rather than silently re-enabling error caching.
    """

    async def on_call_tool(
        self,
        context: MiddlewareContext[mt.CallToolRequestParams],
        call_next: CallNext[mt.CallToolRequestParams, ToolResult],
    ) -> ToolResult:
        tool_name = context.message.name

        if self._call_tool_settings.get("enabled") is False or not self._matches_tool_cache_settings(
            tool_name=tool_name
        ):
            return await call_next(context=context)

        cache_key = _make_call_tool_cache_key(msg=context.message)

        if cached_value := await self._call_tool_cache.get(key=cache_key):
            return cached_value.unwrap()

        tool_result = await call_next(context=context)

        if is_uncacheable_result(tool_result):
            return tool_result

        cachable = CachableToolResult.wrap(value=tool_result)
        await self._call_tool_cache.put(
            key=cache_key,
            value=cachable,
            ttl=self._call_tool_settings.get("ttl", ONE_HOUR_IN_SECONDS),
        )
        return cachable.unwrap()
