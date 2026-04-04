"""Tests for get_hate_crime_data tool."""

from fbi_crime_data_mcp.tools.hate_crime import get_hate_crime_data


class TestHateCrime:
    async def test_invalid_level(self, ctx):
        r = await get_hate_crime_data("city", "01-2020", "12-2020", ctx=ctx)
        assert "Invalid level" in r

    async def test_invalid_data_type(self, ctx):
        r = await get_hate_crime_data("national", "01-2020", "12-2020", data_type="bad", ctx=ctx)
        assert "Invalid data_type" in r

    async def test_state_requires_state(self, ctx):
        r = await get_hate_crime_data("state", "01-2020", "12-2020", ctx=ctx)
        assert "'state' is required" in r

    async def test_agency_requires_ori(self, ctx):
        r = await get_hate_crime_data("agency", "01-2020", "12-2020", ctx=ctx)
        assert "'ori' is required" in r

    async def test_invalid_bias(self, ctx):
        r = await get_hate_crime_data("national", "01-2020", "12-2020", bias="INVALID", ctx=ctx)
        assert "Invalid bias code" in r

    async def test_invalid_state(self, ctx):
        r = await get_hate_crime_data("state", "01-2020", "12-2020", state="ZZ", ctx=ctx)
        assert "Invalid state" in r

    async def test_national_path(self, ctx, app_ctx):
        await get_hate_crime_data("national", "01-2020", "12-2020", ctx=ctx)
        app_ctx.api_get.assert_called_once_with(
            "/hate-crime/national", {"type": "counts", "from": "01-2020", "to": "12-2020"}
        )

    async def test_bias_appended(self, ctx, app_ctx):
        await get_hate_crime_data("national", "01-2020", "12-2020", bias="all", ctx=ctx)
        app_ctx.api_get.assert_called_once_with(
            "/hate-crime/national/all", {"type": "counts", "from": "01-2020", "to": "12-2020"}
        )

    async def test_state_path(self, ctx, app_ctx):
        await get_hate_crime_data("state", "01-2020", "12-2020", state="CA", ctx=ctx)
        app_ctx.api_get.assert_called_once_with(
            "/hate-crime/state/CA", {"type": "counts", "from": "01-2020", "to": "12-2020"}
        )

    async def test_agency_path(self, ctx, app_ctx):
        await get_hate_crime_data("agency", "01-2020", "12-2020", ori="X1", ctx=ctx)
        app_ctx.api_get.assert_called_once_with(
            "/hate-crime/agency/X1", {"type": "counts", "from": "01-2020", "to": "12-2020"}
        )

    async def test_invalid_aggregate(self, ctx):
        r = await get_hate_crime_data("national", "01-2020", "12-2020", aggregate="bad", ctx=ctx)
        assert "Invalid aggregate" in r

    async def test_totals_ignores_invalid_aggregate(self, ctx, app_ctx):
        await get_hate_crime_data(
            "national",
            "01-2020",
            "12-2020",
            data_type="totals",
            aggregate="bad",
            ctx=ctx,
        )
        app_ctx.api_get.assert_called_once_with(
            "/hate-crime/national", {"type": "totals", "from": "01-2020", "to": "12-2020"}
        )

    async def test_invalid_from_date(self, ctx):
        r = await get_hate_crime_data("national", "2020", "12-2020", ctx=ctx)
        assert "mm-yyyy" in r

    async def test_invalid_to_date(self, ctx):
        r = await get_hate_crime_data("national", "01-2020", "2020", ctx=ctx)
        assert "mm-yyyy" in r

    async def test_from_date_after_to_date(self, ctx):
        r = await get_hate_crime_data("national", "06-2022", "01-2020", ctx=ctx)
        assert "after" in r
