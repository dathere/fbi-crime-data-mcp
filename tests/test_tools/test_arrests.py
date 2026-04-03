"""Tests for get_arrest_data tool."""

from fbi_crime_data_mcp.tools.arrests import get_arrest_data


class TestArrestData:
    async def test_invalid_offense(self, ctx):
        r = await get_arrest_data("INVALID", "national", "counts", "01-2020", "12-2020", ctx=ctx)
        assert "Invalid arrest offense code" in r

    async def test_invalid_level(self, ctx):
        r = await get_arrest_data("all", "city", "counts", "01-2020", "12-2020", ctx=ctx)
        assert "Invalid level" in r

    async def test_invalid_data_type(self, ctx):
        r = await get_arrest_data("all", "national", "bad", "01-2020", "12-2020", ctx=ctx)
        assert "Invalid data_type" in r

    async def test_state_requires_state(self, ctx):
        r = await get_arrest_data("all", "state", "counts", "01-2020", "12-2020", ctx=ctx)
        assert "'state' is required" in r

    async def test_agency_requires_ori(self, ctx):
        r = await get_arrest_data("all", "agency", "counts", "01-2020", "12-2020", ctx=ctx)
        assert "'ori' is required" in r

    async def test_invalid_category(self, ctx):
        r = await get_arrest_data("all", "national", "counts", "01-2020", "12-2020", category="age", ctx=ctx)
        assert "Invalid category" in r

    async def test_invalid_state(self, ctx):
        r = await get_arrest_data("all", "state", "counts", "01-2020", "12-2020", state="ZZ", ctx=ctx)
        assert "Invalid state" in r

    async def test_national_path(self, ctx, app_ctx):
        await get_arrest_data("all", "national", "counts", "01-2020", "12-2020", ctx=ctx)
        app_ctx.api_get.assert_called_once_with(
            "/arrest/national/all", {"type": "counts", "from": "01-2020", "to": "12-2020"}
        )

    async def test_state_path(self, ctx, app_ctx):
        await get_arrest_data("all", "state", "totals", "01-2020", "12-2020", state="ca", ctx=ctx)
        app_ctx.api_get.assert_called_once_with(
            "/arrest/state/CA/all", {"type": "totals", "from": "01-2020", "to": "12-2020"}
        )

    async def test_agency_path(self, ctx, app_ctx):
        await get_arrest_data("all", "agency", "counts", "01-2020", "12-2020", ori="X123", ctx=ctx)
        app_ctx.api_get.assert_called_once_with(
            "/arrest/agency/X123/all", {"type": "counts", "from": "01-2020", "to": "12-2020"}
        )

    async def test_category_appended(self, ctx, app_ctx):
        await get_arrest_data("all", "national", "counts", "01-2020", "12-2020", category="race", ctx=ctx)
        app_ctx.api_get.assert_called_once_with(
            "/arrest/national/all/race", {"type": "counts", "from": "01-2020", "to": "12-2020"}
        )
