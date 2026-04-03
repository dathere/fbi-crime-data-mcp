"""HTTP client wrapper for the FBI Crime Data Explorer API."""

from __future__ import annotations

import json
import os
import time
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import httpx
from fastmcp import FastMCP

from .constants import BASE_URL


class RateLimiter:
    """Sliding-window rate limiter (1000 requests per hour by default)."""

    def __init__(self, max_requests: int = 1000, window_seconds: int = 3600):
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
            if self._timestamps:
                oldest = self._timestamps[0]
                wait = int(oldest + self.window_seconds - now) + 1
            else:
                wait = self.window_seconds
            return (
                f"Rate limit reached ({self.max_requests} requests per hour). "
                f"Try again in ~{wait} seconds."
            )
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
            return (
                "Error: FBI API rate limit exceeded (HTTP 429). "
                "Wait a few minutes before retrying."
            )
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
        raise ValueError(
            "FBI_API_KEY environment variable is required. "
            "Get a free key at https://api.data.gov/signup/"
        )
    return key


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
