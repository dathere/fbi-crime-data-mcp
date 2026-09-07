"""Integration tests that hit the live FBI Crime Data Explorer API.

Deselected from the default test run (see ``addopts`` in pyproject.toml).
Run them explicitly with a real key::

    FBI_API_KEY=DEMO_KEY uv run pytest -m integration

``DEMO_KEY`` is capped at 30 requests per IP per hour, so this module is
deliberately kept to ~6 requests.  Tests skip (rather than fail) when the
quota is exhausted, so a burned quota is never mistaken for a regression.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx
import pytest

from fbi_crime_data_mcp.api_client import AppContext
from fbi_crime_data_mcp.constants import BASE_URL
from fbi_crime_data_mcp.tools.agency import lookup_agency
from fbi_crime_data_mcp.tools.nibrs import get_nibrs_data
from fbi_crime_data_mcp.tools.reference import get_reference_data
from fbi_crime_data_mcp.tools.summarized import get_summarized_crime_data
from fbi_crime_data_mcp.tools.trends import get_crime_trends

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.environ.get("FBI_API_KEY"),
        reason="FBI_API_KEY not set — integration tests need a real (or DEMO_KEY) API key",
    ),
]

# Years chosen to sit well inside the FBI's published coverage so the
# assertions test our post-processing, not the freshness of CDE releases.
FROM_DATE = "01-2020"
TO_DATE = "12-2021"

YEAR_RE = re.compile(r"^\d{4}$")
MONTH_RE = re.compile(r"^\d{2}-\d{4}$")

# Prefixes of every non-JSON string the tools can return (api_client error
# messages plus tool-level validation messages).  Tools never raise, so
# without this check a 404 or a 400 would sail through as a passing test.
_ERROR_PREFIXES = ("Error:", "Invalid", "Parameter", "Both ", "Rate limit")

# Lower-cased substrings marking a quota rejection rather than a code defect.
# Covers api_client's HTTP 429 branch, the in-process sliding-window
# RateLimiter, and api.data.gov's 403/OVER_RATE_LIMIT body, which falls
# through to the generic "Unexpected HTTP" branch.
_QUOTA_MARKERS = (
    "rate limit exceeded",
    "rate limit reached",
    "over_rate_limit",
)


class _LiveContext:
    """Context stand-in carrying a real AppContext as lifespan_context."""

    def __init__(self, app_ctx: AppContext):
        self.lifespan_context = app_ctx


@pytest.fixture
async def live_ctx():
    """A Context backed by a real httpx client, built the way app_lifespan builds it.

    Deliberately does not go through ``app_lifespan``: that needs a FastMCP
    instance and writes cache stats to disk on teardown.  Function-scoped to
    match pytest-asyncio's function-scoped event loop.
    """
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        params={"API_KEY": os.environ["FBI_API_KEY"]},
        timeout=30.0,
        headers={"Accept": "application/json"},
    ) as client:
        yield _LiveContext(AppContext(client=client))


def unwrap(response: str) -> Any:
    """Assert a tool response is a real JSON payload and return it parsed.

    Skips (does not fail) when the API quota is exhausted, so a burned
    DEMO_KEY is distinguishable from a genuine regression.
    """
    assert isinstance(response, str), f"tool returned {type(response).__name__}, expected str"

    if response.startswith(_ERROR_PREFIXES):
        # Quota rejections are detected by content, not status code:
        # api.data.gov has used both 429 and 403/OVER_RATE_LIMIT for
        # over-quota, and only the former maps to a dedicated api_get branch.
        lowered = response.lower()
        if any(marker in lowered for marker in _QUOTA_MARKERS):
            pytest.skip(f"API quota exhausted: {response[:200]}")
        pytest.fail(f"tool returned an error string: {response[:300]}")

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pytest.fail(f"tool response was not JSON: {response[:300]}")


def collect_keys(node: Any, found: set[str] | None = None) -> set[str]:
    """Recursively collect every dict key in a nested structure."""
    if found is None:
        found = set()
    if isinstance(node, dict):
        for key, value in node.items():
            found.add(key)
            collect_keys(value, found)
    elif isinstance(node, list):
        for item in node:
            collect_keys(item, found)
    return found


class TestLiveReference:
    async def test_cde_properties_returns_date_ranges(self, live_ctx):
        """The reference endpoint that documents CDE's available data ranges."""
        data = unwrap(await get_reference_data("cde_properties", ctx=live_ctx))
        assert data, "cde_properties returned an empty payload"


class TestLiveSummarized:
    async def test_yearly_aggregation_and_trimming(self, live_ctx):
        """Highest-value live check: process_crime_response against a real payload.

        Unit tests only ever feed it hand-built fixtures, so this is the only
        place the yearly rollup and section-trimming meet the real response shape.
        """
        data = unwrap(
            await get_summarized_crime_data("V", "national", FROM_DATE, TO_DATE, ctx=live_ctx)
        )
        assert isinstance(data, dict), f"expected a JSON object, got {type(data).__name__}"

        # Trimming
        assert "tooltips" not in data, "tooltips should have been trimmed"
        populations = data.get("populations")
        if isinstance(populations, dict):
            assert "participated_population" not in populations, (
                "participated_population should have been trimmed"
            )

        # Aggregation: monthly mm-yyyy keys collapsed into yyyy keys
        keys = collect_keys(data)
        year_keys = {k for k in keys if YEAR_RE.match(k)}
        month_keys = {k for k in keys if MONTH_RE.match(k)}
        assert year_keys, f"expected yyyy keys after yearly aggregation; saw {sorted(keys)[:40]}"
        assert not month_keys, f"mm-yyyy keys survived yearly aggregation: {sorted(month_keys)}"

    async def test_monthly_aggregate_preserves_month_keys(self, live_ctx):
        """Counterpart to the above — proves the rollup is ours, not the API's."""
        data = unwrap(
            await get_summarized_crime_data(
                "V", "national", FROM_DATE, TO_DATE, aggregate="monthly", ctx=live_ctx
            )
        )
        keys = collect_keys(data)
        assert {k for k in keys if MONTH_RE.match(k)}, (
            f"expected mm-yyyy keys with aggregate='monthly'; saw {sorted(keys)[:40]}"
        )


class TestLiveNibrs:
    async def test_national_counts(self, live_ctx):
        """A different response shape than the SRS summarized endpoint."""
        data = unwrap(
            await get_nibrs_data("13A", "national", FROM_DATE, TO_DATE, ctx=live_ctx)
        )
        assert isinstance(data, dict), f"expected a JSON object, got {type(data).__name__}"
        assert "tooltips" not in data, "tooltips should have been trimmed"


class TestLiveAgency:
    async def test_by_state_with_name_filter(self, live_ctx):
        """Exercises filter_agencies_by_name against a real agency list."""
        data = unwrap(
            await lookup_agency("by_state", state="DE", name_filter="police", ctx=live_ctx)
        )

        names = [
            agency.get("agency_name", "")
            for group in (data.values() if isinstance(data, dict) else [data])
            if isinstance(group, list)
            for agency in group
            if isinstance(agency, dict)
        ]
        assert names, "name_filter matched nothing — filter or response shape changed"
        assert all("police" in name.lower() for name in names), (
            f"name_filter let through non-matching agencies: {names[:5]}"
        )


class TestLiveTrends:
    async def test_yyyy_date_format(self, live_ctx):
        """Trends uses yyyy rather than mm-yyyy — a distinct date-format path."""
        data = unwrap(await get_crime_trends(from_year="2019", to_year="2021", ctx=live_ctx))
        assert data, "trends returned an empty payload"
