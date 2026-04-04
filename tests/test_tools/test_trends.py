"""Tests for get_crime_trends tool."""

from fbi_crime_data_mcp.tools.trends import get_crime_trends


class TestCrimeTrends:
    async def test_no_params(self, ctx, app_ctx):
        await get_crime_trends(ctx=ctx)
        app_ctx.api_get.assert_called_once_with("/trends/national", {})

    async def test_from_year_only(self, ctx, app_ctx):
        await get_crime_trends(from_year="2015", ctx=ctx)
        app_ctx.api_get.assert_called_once_with("/trends/national", {"from": "2015"})

    async def test_to_year_only(self, ctx, app_ctx):
        await get_crime_trends(to_year="2022", ctx=ctx)
        app_ctx.api_get.assert_called_once_with("/trends/national", {"to": "2022"})

    async def test_both_years(self, ctx, app_ctx):
        await get_crime_trends(from_year="2015", to_year="2022", ctx=ctx)
        app_ctx.api_get.assert_called_once_with("/trends/national", {"from": "2015", "to": "2022"})

    async def test_invalid_from_year(self, ctx):
        r = await get_crime_trends(from_year="01-2020", ctx=ctx)
        assert "yyyy" in r

    async def test_invalid_to_year(self, ctx):
        r = await get_crime_trends(to_year="bad", ctx=ctx)
        assert "yyyy" in r

    async def test_from_year_after_to_year(self, ctx):
        r = await get_crime_trends(from_year="2022", to_year="2015", ctx=ctx)
        assert "after" in r
