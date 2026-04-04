"""Tests for get_expanded_homicide_data tool."""

from fbi_crime_data_mcp.tools.homicide import get_expanded_homicide_data


class TestHomicide:
    async def test_invalid_level(self, ctx):
        r = await get_expanded_homicide_data("city", "counts", "01-2020", "12-2020", ctx=ctx)
        assert "Invalid level" in r

    async def test_invalid_data_type(self, ctx):
        r = await get_expanded_homicide_data("national", "bad", "01-2020", "12-2020", ctx=ctx)
        assert "Invalid data_type" in r

    async def test_state_requires_state(self, ctx):
        r = await get_expanded_homicide_data("state", "counts", "01-2020", "12-2020", ctx=ctx)
        assert "'state' is required" in r

    async def test_agency_requires_ori(self, ctx):
        r = await get_expanded_homicide_data("agency", "counts", "01-2020", "12-2020", ctx=ctx)
        assert "'ori' is required" in r

    async def test_invalid_state(self, ctx):
        r = await get_expanded_homicide_data("state", "counts", "01-2020", "12-2020", state="ZZ", ctx=ctx)
        assert "Invalid state" in r

    async def test_national_path(self, ctx, app_ctx):
        await get_expanded_homicide_data("national", "counts", "01-2020", "12-2020", ctx=ctx)
        app_ctx.api_get.assert_called_once_with("/shr/national", {"type": "counts", "from": "01-2020", "to": "12-2020"})

    async def test_state_path(self, ctx, app_ctx):
        await get_expanded_homicide_data("state", "totals", "01-2020", "12-2020", state="TX", ctx=ctx)
        app_ctx.api_get.assert_called_once_with("/shr/state/TX", {"type": "totals", "from": "01-2020", "to": "12-2020"})

    async def test_agency_path(self, ctx, app_ctx):
        await get_expanded_homicide_data("agency", "counts", "01-2020", "12-2020", ori="X1", ctx=ctx)
        app_ctx.api_get.assert_called_once_with(
            "/shr/agency/X1", {"type": "counts", "from": "01-2020", "to": "12-2020"}
        )

    async def test_invalid_aggregate(self, ctx):
        r = await get_expanded_homicide_data("national", "counts", "01-2020", "12-2020", aggregate="bad", ctx=ctx)
        assert "Invalid aggregate" in r

    async def test_totals_ignores_invalid_aggregate(self, ctx, app_ctx):
        await get_expanded_homicide_data("national", "totals", "01-2020", "12-2020", aggregate="bad", ctx=ctx)
        app_ctx.api_get.assert_called_once_with("/shr/national", {"type": "totals", "from": "01-2020", "to": "12-2020"})

    async def test_invalid_from_date(self, ctx):
        r = await get_expanded_homicide_data("national", "counts", "2020", "12-2020", ctx=ctx)
        assert "mm-yyyy" in r

    async def test_invalid_to_date(self, ctx):
        r = await get_expanded_homicide_data("national", "counts", "01-2020", "bad", ctx=ctx)
        assert "mm-yyyy" in r
