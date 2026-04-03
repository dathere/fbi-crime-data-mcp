"""Tests for get_nibrs_data tool."""

from fbi_crime_data_mcp.tools.nibrs import get_nibrs_data


class TestNibrsData:
    async def test_invalid_offense(self, ctx):
        r = await get_nibrs_data("INVALID", "national", "01-2020", "12-2020", ctx=ctx)
        assert "Invalid NIBRS offense code" in r

    async def test_invalid_level(self, ctx):
        r = await get_nibrs_data("09A", "city", "01-2020", "12-2020", ctx=ctx)
        assert "Invalid level" in r

    async def test_invalid_data_type(self, ctx):
        r = await get_nibrs_data("09A", "national", "01-2020", "12-2020", data_type="bad", ctx=ctx)
        assert "Invalid data_type" in r

    async def test_state_requires_state(self, ctx):
        r = await get_nibrs_data("09A", "state", "01-2020", "12-2020", ctx=ctx)
        assert "'state' is required" in r

    async def test_agency_requires_ori(self, ctx):
        r = await get_nibrs_data("09A", "agency", "01-2020", "12-2020", ctx=ctx)
        assert "'ori' is required" in r

    async def test_invalid_state(self, ctx):
        r = await get_nibrs_data("09A", "state", "01-2020", "12-2020", state="ZZ", ctx=ctx)
        assert "Invalid state" in r

    async def test_national_path(self, ctx, app_ctx):
        await get_nibrs_data("09A", "national", "01-2020", "12-2020", ctx=ctx)
        app_ctx.api_get.assert_called_once_with(
            "/nibrs/national/09A", {"type": "counts", "from": "01-2020", "to": "12-2020"}
        )

    async def test_state_path(self, ctx, app_ctx):
        await get_nibrs_data("13A", "state", "01-2020", "12-2020", state="tx", ctx=ctx)
        app_ctx.api_get.assert_called_once_with(
            "/nibrs/state/TX/13A", {"type": "counts", "from": "01-2020", "to": "12-2020"}
        )

    async def test_agency_path(self, ctx, app_ctx):
        await get_nibrs_data("120", "agency", "01-2020", "12-2020", ori="X1", ctx=ctx)
        app_ctx.api_get.assert_called_once_with(
            "/nibrs/agency/X1/120", {"type": "counts", "from": "01-2020", "to": "12-2020"}
        )

    async def test_invalid_aggregate(self, ctx):
        r = await get_nibrs_data("09A", "national", "01-2020", "12-2020", aggregate="bad", ctx=ctx)
        assert "Invalid aggregate" in r

    async def test_totals_data_type(self, ctx, app_ctx):
        await get_nibrs_data("09A", "national", "01-2020", "12-2020", data_type="totals", ctx=ctx)
        app_ctx.api_get.assert_called_once_with(
            "/nibrs/national/09A", {"type": "totals", "from": "01-2020", "to": "12-2020"}
        )
