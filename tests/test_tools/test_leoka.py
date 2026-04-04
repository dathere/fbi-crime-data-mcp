"""Tests for get_leoka_data tool."""

from fbi_crime_data_mcp.tools.leoka import get_leoka_data


class TestLeoka:
    async def test_invalid_report_type(self, ctx):
        r = await get_leoka_data("invalid", 2022, ctx=ctx)
        assert "Invalid report_type" in r

    async def test_monthly_requires_month(self, ctx):
        r = await get_leoka_data("monthly", 2022, ctx=ctx)
        assert "'month'" in r

    async def test_month_too_low(self, ctx):
        r = await get_leoka_data("monthly", 2022, month=0, ctx=ctx)
        assert "between 1" in r

    async def test_month_too_high(self, ctx):
        r = await get_leoka_data("monthly", 2022, month=13, ctx=ctx)
        assert "between 1" in r

    async def test_monthly_path(self, ctx, app_ctx):
        """Month 1 (January) maps to API month 0."""
        await get_leoka_data("monthly", 2022, month=1, ctx=ctx)
        app_ctx.api_get.assert_called_once_with("/leoka/monthly", {"year": "2022", "month": "0"})

    async def test_ytd_path(self, ctx, app_ctx):
        await get_leoka_data("ytd", 2022, ctx=ctx)
        app_ctx.api_get.assert_called_once_with("/leoka/ytd", {"year": "2022"})

    async def test_month_boundary_12(self, ctx, app_ctx):
        """Month 12 (December) maps to API month 11."""
        await get_leoka_data("monthly", 2022, month=12, ctx=ctx)
        app_ctx.api_get.assert_called_once_with("/leoka/monthly", {"year": "2022", "month": "11"})

    async def test_ytd_ignores_month(self, ctx, app_ctx):
        """Month param should be ignored (not validated) when report_type is ytd."""
        await get_leoka_data("ytd", 2022, month=5, ctx=ctx)
        app_ctx.api_get.assert_called_once_with("/leoka/ytd", {"year": "2022"})

    async def test_invalid_year(self, ctx):
        r = await get_leoka_data("ytd", 1900, ctx=ctx)
        assert "Invalid" in r and "year" in r
