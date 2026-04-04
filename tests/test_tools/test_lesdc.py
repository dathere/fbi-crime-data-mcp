"""Tests for get_lesdc_data tool."""

from fbi_crime_data_mcp.tools.lesdc import get_lesdc_data


class TestLesdc:
    async def test_invalid_chart_type(self, ctx):
        r = await get_lesdc_data(2022, "invalid", ctx=ctx)
        assert "Invalid chart_type" in r

    async def test_valid_chart_type(self, ctx, app_ctx):
        await get_lesdc_data(2022, "demographics", ctx=ctx)
        app_ctx.api_get.assert_called_once_with("/lesdc", {"year": "2022", "chartType": "demographics"})

    async def test_invalid_year(self, ctx):
        r = await get_lesdc_data(1900, "demographics", ctx=ctx)
        assert "Invalid" in r and "year" in r
