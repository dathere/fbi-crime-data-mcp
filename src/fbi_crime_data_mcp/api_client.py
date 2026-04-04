"""HTTP client wrapper for the FBI Crime Data Explorer API."""

from __future__ import annotations

import json
import os
import time
from collections import deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

import httpx
from fastmcp import FastMCP
from fastmcp.server.middleware.caching import ResponseCachingMiddleware

from .constants import BASE_URL, CACHE_COLLECTION_NAMES, STATS_FILE


class RateLimiter:
    """Sliding-window rate limiter (1000 requests per hour by default)."""

    def __init__(self, max_requests: int = 1000, window_seconds: int = 3600):
        if max_requests < 1:
            raise ValueError("max_requests must be at least 1")
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._timestamps: deque[float] = deque()

    def check(self) -> str | None:
        """Return an error message if rate limited, else None."""
        now = time.monotonic()
        cutoff = now - self.window_seconds
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()
        if len(self._timestamps) >= self.max_requests:
            oldest = self._timestamps[0]
            wait = int(oldest + self.window_seconds - now) + 1
            if self.window_seconds % 3600 == 0:
                hours = self.window_seconds // 3600
                window_desc = f"{hours} {'hour' if hours == 1 else 'hours'}"
            elif self.window_seconds % 60 == 0:
                window_desc = f"{self.window_seconds // 60} minutes"
            else:
                window_desc = f"{self.window_seconds} seconds"
            return f"Rate limit reached ({self.max_requests} requests per {window_desc}). Try again in ~{wait} seconds."
        return None

    def record(self) -> None:
        self._timestamps.append(time.monotonic())


@dataclass
class AppContext:
    """Shared application context available to all tools via lifespan."""

    client: httpx.AsyncClient
    rate_limiter: RateLimiter = field(default_factory=RateLimiter)

    async def api_get(self, path: str, params: dict[str, Any] | None = None) -> str:
        """Make a GET request to the CDE API and return formatted JSON string."""
        error = self.rate_limiter.check()
        if error:
            return error

        self.rate_limiter.record()

        try:
            response = await self.client.get(path, params=params or {})
        except httpx.TimeoutException:
            return "Error: Request timed out. The FBI API may be slow — try again."
        except httpx.HTTPError as e:
            return f"Error: Network error connecting to FBI API: {e}"

        if response.status_code == 429:
            return "Error: FBI API rate limit exceeded (HTTP 429). Wait a few minutes before retrying."
        if response.status_code == 400:
            try:
                body = response.json()
                msg = body.get("message", body.get("error", response.text))
            except Exception:
                msg = response.text
            return f"Error: Bad request — {msg}"
        if response.status_code == 404:
            return f"Error: Endpoint not found — {path}"
        if response.status_code >= 500:
            return f"Error: FBI API server error (HTTP {response.status_code}). Try again later."
        if response.status_code != 200:
            return f"Error: Unexpected HTTP {response.status_code}: {response.text[:500]}"

        try:
            data = response.json()
        except Exception:
            return f"Error: Could not parse API response as JSON: {response.text[:500]}"

        return json.dumps(data, indent=2)


def _get_api_key() -> str:
    key = os.environ.get("FBI_API_KEY", "")
    if not key:
        raise ValueError("FBI_API_KEY environment variable is required. Get a free key at https://api.data.gov/signup/")
    return key


def _collect_stats(server: FastMCP) -> dict[str, dict[str, int]]:
    """Aggregate cache hit/miss stats from all caching middleware."""
    collection_names = CACHE_COLLECTION_NAMES
    totals: dict[str, dict[str, int]] = {}
    for mw in server.middleware:
        if not isinstance(mw, ResponseCachingMiddleware):
            continue
        stats = mw.statistics()
        for name in collection_names:
            col_stats = getattr(stats, name, None)
            if col_stats is None:
                continue
            if name not in totals:
                totals[name] = {"hits": 0, "misses": 0}
            totals[name]["hits"] += col_stats.get.hit
            totals[name]["misses"] += col_stats.get.miss
    return totals


def _save_stats(server: FastMCP) -> None:
    """Save aggregated cache stats to disk."""
    current = _collect_stats(server)
    # Merge with any previously persisted stats
    persisted = _load_persisted_stats()
    for name, counts in current.items():
        if name in persisted:
            persisted[name]["hits"] += counts["hits"]
            persisted[name]["misses"] += counts["misses"]
        else:
            persisted[name] = dict(counts)
    try:
        STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATS_FILE.write_text(json.dumps(persisted, indent=2))
    except OSError:
        pass


def _load_persisted_stats() -> dict[str, dict[str, int]]:
    """Load persisted cache stats from disk."""
    if not STATS_FILE.is_file():
        return {}
    try:
        data = json.loads(STATS_FILE.read_text())
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return {}


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage the shared httpx client and rate limiter."""
    api_key = _get_api_key()
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        params={"API_KEY": api_key},
        timeout=30.0,
        headers={"Accept": "application/json"},
    ) as client:
        yield AppContext(client=client)
        _save_stats(server)
