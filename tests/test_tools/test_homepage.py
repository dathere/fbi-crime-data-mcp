"""Tests for get_cde_homepage_summary tool."""

import json

from fbi_crime_data_mcp.tools.homepage import get_cde_homepage_summary


class TestGetCdeHomepageSummary:
    async def test_returns_valid_json(self, ctx, app_ctx):
        app_ctx.api_get.return_value = '{"last_refresh": "2026-03-15"}'
        result = await get_cde_homepage_summary(ctx=ctx)
        data = json.loads(result)
        assert isinstance(data, dict)

    async def test_contains_stable_sections(self, ctx, app_ctx):
        app_ctx.api_get.return_value = "{}"
        result = await get_cde_homepage_summary(ctx=ctx)
        data = json.loads(result)
        assert "mission_statement" in data
        assert "navigation" in data
        assert "homepage_url" in data
        assert "_stable_content_version" in data

    async def test_contains_dynamic_sections(self, ctx, app_ctx):
        app_ctx.api_get.return_value = '{"some": "data"}'
        result = await get_cde_homepage_summary(ctx=ctx)
        data = json.loads(result)
        assert "data_refresh_dates" in data
        assert "data_properties" in data

    async def test_calls_both_api_endpoints(self, ctx, app_ctx):
        app_ctx.api_get.return_value = "{}"
        await get_cde_homepage_summary(ctx=ctx)
        calls = [c.args[0] for c in app_ctx.api_get.call_args_list]
        assert "/refresh-date" in calls
        assert "/lookup/cde_properties" in calls

    async def test_handles_api_error_gracefully(self, ctx, app_ctx):
        app_ctx.api_get.return_value = "Error: Request timed out."
        result = await get_cde_homepage_summary(ctx=ctx)
        data = json.loads(result)
        assert data["data_refresh_dates"] == "Error: Request timed out."
        assert "mission_statement" in data

    async def test_navigation_has_expected_keys(self, ctx, app_ctx):
        app_ctx.api_get.return_value = "{}"
        result = await get_cde_homepage_summary(ctx=ctx)
        data = json.loads(result)
        nav = data["navigation"]
        assert "national_data" in nav
        assert "state_agency_data" in nav
        assert "data_discovery_tool" in nav
        assert "documents_downloads" in nav
        assert "about" in nav
        for entry in nav.values():
            assert "label" in entry
            assert "url" in entry
