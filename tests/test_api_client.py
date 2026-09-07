"""Tests for the API client: RateLimiter, AppContext.api_get, and helpers."""

from __future__ import annotations

import json
import os
import time
from unittest.mock import patch

import httpx
import pytest
import respx

from fbi_crime_data_mcp.api_client import AppContext, RateLimiter, _collect_stats, _get_api_key, app_lifespan

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

    def test_zero_max_requests_raises(self):
        with pytest.raises(ValueError, match="max_requests must be at least 1"):
            RateLimiter(max_requests=0)

    def test_negative_max_requests_raises(self):
        with pytest.raises(ValueError, match="max_requests must be at least 1"):
            RateLimiter(max_requests=-1)

    def test_message_reflects_window(self):
        rl = RateLimiter(max_requests=1, window_seconds=60)
        rl.record()
        msg = rl.check()
        assert "60 seconds" in msg
        assert "per hour" not in msg

    def test_message_reflects_window_hours(self):
        rl = RateLimiter(max_requests=1, window_seconds=3600)
        rl.record()
        msg = rl.check()
        assert "1 hour" in msg
        assert "hour(s)" not in msg  # no awkward "hour(s)"

    def test_message_reflects_window_multiple_hours(self):
        rl = RateLimiter(max_requests=1, window_seconds=7200)
        rl.record()
        msg = rl.check()
        assert "2 hours" in msg

    def test_message_reflects_window_non_round_hours(self):
        rl = RateLimiter(max_requests=1, window_seconds=5400)  # 90 minutes
        rl.record()
        msg = rl.check()
        assert "90 minutes" in msg

    def test_message_reflects_window_odd_seconds(self):
        rl = RateLimiter(max_requests=1, window_seconds=3700)  # not divisible by 60
        rl.record()
        msg = rl.check()
        assert "3700 seconds" in msg

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
            headers={"X-Api-Key": "test"},
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
        rl = RateLimiter(max_requests=1)
        rl.record()  # exhaust the single allowed request
        ctx = AppContext(client=client, rate_limiter=rl)
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

    @pytest.mark.parametrize("code", ["API_KEY_MISSING", "API_KEY_INVALID", "API_KEY_DISABLED"])
    async def test_http_403_bad_key_is_actionable(self, mock_client, code):
        client, mock = mock_client
        mock.get("/test").respond(403, json={"error": {"code": code, "message": "Your API key is not valid."}})
        ctx = AppContext(client=client)
        result = await ctx.api_get("/test")
        assert result.startswith("Error:")
        assert code in result
        assert "Your API key is not valid." in result
        assert "FBI_API_KEY" in result

    async def test_http_403_over_rate_limit_reads_as_rate_limit(self, mock_client):
        # api.data.gov has sent OVER_RATE_LIMIT as 403 as well as 429; both
        # must produce the same "rate limit exceeded" wording so callers (and
        # the integration suite's quota skip) treat them alike.
        client, mock = mock_client
        mock.get("/test").respond(403, json={"error": {"code": "OVER_RATE_LIMIT", "message": "slow down"}})
        ctx = AppContext(client=client)
        result = await ctx.api_get("/test")
        assert "rate limit exceeded" in result.lower()
        assert "OVER_RATE_LIMIT" in result
        assert "FBI_API_KEY" not in result

    async def test_http_403_unknown_code_passes_message_through(self, mock_client):
        client, mock = mock_client
        mock.get("/test").respond(403, json={"error": {"code": "HTTPS_REQUIRED", "message": "use https"}})
        ctx = AppContext(client=client)
        result = await ctx.api_get("/test")
        assert result == "Error: FBI API returned HTTP 403 HTTPS_REQUIRED: use https"

    async def test_http_403_non_json_body(self, mock_client):
        client, mock = mock_client
        mock.get("/test").respond(403, text="Forbidden by proxy")
        ctx = AppContext(client=client)
        result = await ctx.api_get("/test")
        assert result == "Error: FBI API returned HTTP 403: Forbidden by proxy"

    async def test_http_403_json_without_error_object(self, mock_client):
        client, mock = mock_client
        mock.get("/test").respond(403, json={"detail": "nope"})
        ctx = AppContext(client=client)
        result = await ctx.api_get("/test")
        assert result.startswith("Error: FBI API returned HTTP 403: ")
        assert "nope" in result

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


# ── _collect_stats ──────────────────────────────────────────────────────────


class TestCollectStats:
    def test_no_middleware(self):
        from unittest.mock import MagicMock

        server = MagicMock()
        server.middleware = []
        assert _collect_stats(server) == {}

    def test_with_caching_middleware(self, monkeypatch):
        from unittest.mock import MagicMock

        from fbi_crime_data_mcp.api_client import CACHE_COLLECTION_NAMES

        # Build a fake middleware with statistics
        fake_mw = MagicMock(spec=["statistics"])
        fake_mw.__class__ = type("FakeCachingMW", (), {})

        # Make isinstance check pass

        monkeypatch.setattr(
            "fbi_crime_data_mcp.api_client.ResponseCachingMiddleware",
            type(fake_mw),
        )

        # Build fake stats object
        stats = MagicMock()
        for name in CACHE_COLLECTION_NAMES:
            col = MagicMock()
            col.get.hit = 3
            col.get.miss = 1
            setattr(stats, name, col)
        fake_mw.statistics.return_value = stats

        server = MagicMock()
        server.middleware = [fake_mw]
        result = _collect_stats(server)
        for name in CACHE_COLLECTION_NAMES:
            assert result[name]["hits"] == 3
            assert result[name]["misses"] == 1

    def test_skips_none_col_stats(self, monkeypatch):
        from unittest.mock import MagicMock

        fake_mw = MagicMock()
        monkeypatch.setattr(
            "fbi_crime_data_mcp.api_client.ResponseCachingMiddleware",
            type(fake_mw),
        )
        # Build stats where getattr returns None for all collection names
        stats = MagicMock(spec=[])
        fake_mw.statistics.return_value = stats

        server = MagicMock()
        server.middleware = [fake_mw]
        result = _collect_stats(server)
        assert result == {}

    def test_skips_non_caching_middleware(self, monkeypatch):
        """Non-caching middleware (e.g. the spillover middleware) is skipped,
        not queried for statistics.

        Uses real, distinct fake classes rather than reassigning a mock's
        ``__class__`` so the ``isinstance`` check is unambiguous and the test
        does not depend on MagicMock spoofing internals.
        """
        from unittest.mock import MagicMock

        from fbi_crime_data_mcp.api_client import CACHE_COLLECTION_NAMES

        def _fake_stats():
            stats = MagicMock()
            for name in CACHE_COLLECTION_NAMES:
                col = MagicMock()
                col.get.hit = 2
                col.get.miss = 0
                setattr(stats, name, col)
            return stats

        class FakeCachingMW:
            def statistics(self):
                return _fake_stats()

        class FakeOtherMW:
            def statistics(self):  # pragma: no cover - must never be called
                raise AssertionError("statistics() called on non-caching middleware")

        monkeypatch.setattr(
            "fbi_crime_data_mcp.api_client.ResponseCachingMiddleware",
            FakeCachingMW,
        )

        server = MagicMock()
        server.middleware = [FakeOtherMW(), FakeCachingMW()]
        result = _collect_stats(server)

        for name in CACHE_COLLECTION_NAMES:
            assert result[name]["hits"] == 2
            assert result[name]["misses"] == 0


# ── app_lifespan ────────────────────────────────────────────────────────────


class TestAppLifespan:
    async def test_yields_app_context_and_saves_stats(self, monkeypatch):
        """app_lifespan yields an AppContext and saves stats on exit."""
        from unittest.mock import MagicMock

        monkeypatch.setenv("FBI_API_KEY", "test-key")
        # Mock _save_stats to verify it's called
        save_calls = []
        monkeypatch.setattr(
            "fbi_crime_data_mcp.api_client._save_stats",
            lambda server: save_calls.append(server),
        )

        mock_server = MagicMock()
        async with app_lifespan(mock_server) as ctx:
            assert isinstance(ctx, AppContext)
            assert ctx.client is not None
            # Key is sent as a header, never as a URL query parameter
            assert ctx.client.headers["X-Api-Key"] == "test-key"
            assert "API_KEY" not in ctx.client.params
            assert "test-key" not in str(ctx.client.build_request("GET", "/x").url)

        assert len(save_calls) == 1
