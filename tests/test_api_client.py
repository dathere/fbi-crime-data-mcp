"""Tests for the API client: RateLimiter, AppContext.api_get, and helpers."""

from __future__ import annotations

import json
import os
import time
from unittest.mock import patch

import httpx
import pytest
import respx

from fbi_crime_data_mcp.api_client import AppContext, RateLimiter, _get_api_key


# ── RateLimiter ──────────────────────────────────────────────────────────────


class TestRateLimiter:
    def test_under_limit_returns_none(self):
        rl = RateLimiter(max_requests=5, window_seconds=60)
        assert rl.check() is None

    def test_at_limit_returns_error(self):
        rl = RateLimiter(max_requests=2, window_seconds=60)
        rl.record()
        rl.record()
        msg = rl.check()
        assert msg is not None
        assert "Rate limit reached" in msg

    def test_old_timestamps_expire(self):
        rl = RateLimiter(max_requests=1, window_seconds=1)
        rl.record()
        assert rl.check() is not None  # at limit
        # Simulate time passing
        rl._timestamps[0] = time.monotonic() - 2
        assert rl.check() is None  # old timestamp expired

    def test_zero_max_requests_empty_deque(self):
        rl = RateLimiter(max_requests=0)
        msg = rl.check()
        assert msg is not None
        assert "Rate limit reached" in msg

    def test_record_appends_timestamp(self):
        rl = RateLimiter()
        assert len(rl._timestamps) == 0
        rl.record()
        assert len(rl._timestamps) == 1
        rl.record()
        assert len(rl._timestamps) == 2


# ── _get_api_key ─────────────────────────────────────────────────────────────


class TestGetApiKey:
    def test_returns_key_when_set(self):
        with patch.dict(os.environ, {"FBI_API_KEY": "test-key-123"}):
            assert _get_api_key() == "test-key-123"

    def test_raises_when_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("FBI_API_KEY", None)
            with pytest.raises(ValueError, match="FBI_API_KEY"):
                _get_api_key()


# ── AppContext.api_get ───────────────────────────────────────────────────────


@pytest.fixture
async def mock_client():
    """Return a respx-mocked httpx.AsyncClient."""
    with respx.mock(base_url="https://api.usa.gov/crime/fbi/cde") as mock:
        client = httpx.AsyncClient(
            base_url="https://api.usa.gov/crime/fbi/cde",
            params={"API_KEY": "test"},
            timeout=5.0,
        )
        yield client, mock
        await client.aclose()


class TestApiGet:
    async def test_successful_json_response(self, mock_client):
        client, mock = mock_client
        mock.get("/test").respond(200, json={"data": [1, 2, 3]})
        ctx = AppContext(client=client)
        result = await ctx.api_get("/test")
        assert json.loads(result) == {"data": [1, 2, 3]}

    async def test_passes_params(self, mock_client):
        client, mock = mock_client
        route = mock.get("/test").respond(200, json={})
        ctx = AppContext(client=client)
        await ctx.api_get("/test", {"from": "01-2020", "to": "12-2022"})
        assert route.called
        req = route.calls[0].request
        assert b"from=01-2020" in req.url.query
        assert b"to=12-2022" in req.url.query

    async def test_rate_limited(self, mock_client):
        client, _ = mock_client
        ctx = AppContext(client=client, rate_limiter=RateLimiter(max_requests=0))
        result = await ctx.api_get("/test")
        assert "Rate limit reached" in result

    async def test_timeout_error(self, mock_client):
        client, mock = mock_client
        mock.get("/test").mock(side_effect=httpx.TimeoutException("timed out"))
        ctx = AppContext(client=client)
        result = await ctx.api_get("/test")
        assert "timed out" in result.lower()

    async def test_network_error(self, mock_client):
        client, mock = mock_client
        mock.get("/test").mock(side_effect=httpx.ConnectError("refused"))
        ctx = AppContext(client=client)
        result = await ctx.api_get("/test")
        assert "Network error" in result

    async def test_http_429(self, mock_client):
        client, mock = mock_client
        mock.get("/test").respond(429)
        ctx = AppContext(client=client)
        result = await ctx.api_get("/test")
        assert "429" in result

    async def test_http_400_with_json_message(self, mock_client):
        client, mock = mock_client
        mock.get("/test").respond(400, json={"message": "bad param"})
        ctx = AppContext(client=client)
        result = await ctx.api_get("/test")
        assert "bad param" in result

    async def test_http_400_with_error_key(self, mock_client):
        client, mock = mock_client
        mock.get("/test").respond(400, json={"error": "invalid"})
        ctx = AppContext(client=client)
        result = await ctx.api_get("/test")
        assert "invalid" in result

    async def test_http_400_plain_text(self, mock_client):
        client, mock = mock_client
        mock.get("/test").respond(400, text="plain error")
        ctx = AppContext(client=client)
        result = await ctx.api_get("/test")
        assert "plain error" in result

    async def test_http_404(self, mock_client):
        client, mock = mock_client
        mock.get("/missing").respond(404)
        ctx = AppContext(client=client)
        result = await ctx.api_get("/missing")
        assert "not found" in result.lower()

    async def test_http_503(self, mock_client):
        client, mock = mock_client
        mock.get("/test").respond(503)
        ctx = AppContext(client=client)
        result = await ctx.api_get("/test")
        assert "503" in result

    async def test_unexpected_status(self, mock_client):
        client, mock = mock_client
        mock.get("/test").respond(418, text="I'm a teapot")
        ctx = AppContext(client=client)
        result = await ctx.api_get("/test")
        assert "418" in result

    async def test_invalid_json_response(self, mock_client):
        client, mock = mock_client
        mock.get("/test").respond(200, content=b"not json", headers={"content-type": "text/plain"})
        ctx = AppContext(client=client)
        result = await ctx.api_get("/test")
        assert "Could not parse" in result

    async def test_records_rate_limit_on_success(self, mock_client):
        client, mock = mock_client
        mock.get("/test").respond(200, json={})
        ctx = AppContext(client=client)
        assert len(ctx.rate_limiter._timestamps) == 0
        await ctx.api_get("/test")
        assert len(ctx.rate_limiter._timestamps) == 1
