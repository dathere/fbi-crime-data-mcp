"""Tests for get_expanded_property_data tool."""

from fbi_crime_data_mcp.tools.property_data import get_expanded_property_data


class TestPropertyData:
    async def test_invalid_offense(self, ctx):
        r = await get_expanded_property_data("INVALID", "national", "counts", "01-2020", "12-2020", ctx=ctx)
        assert "Invalid offense code" in r

    async def test_invalid_level(self, ctx):
        r = await get_expanded_property_data("NB", "city", "counts", "01-2020", "12-2020", ctx=ctx)
        assert "Invalid level" in r

    async def test_invalid_data_type(self, ctx):
        r = await get_expanded_property_data("NB", "national", "bad", "01-2020", "12-2020", ctx=ctx)
        assert "Invalid data_type" in r

    async def test_state_requires_state(self, ctx):
        r = await get_expanded_property_data("NB", "state", "counts", "01-2020", "12-2020", ctx=ctx)
        assert "'state' is required" in r

    async def test_agency_requires_ori(self, ctx):
        r = await get_expanded_property_data("NB", "agency", "counts", "01-2020", "12-2020", ctx=ctx)
        assert "'ori' is required" in r

    async def test_invalid_state(self, ctx):
        r = await get_expanded_property_data("NB", "state", "counts", "01-2020", "12-2020", state="ZZ", ctx=ctx)
        assert "Invalid state" in r

    async def test_national_path(self, ctx, app_ctx):
        await get_expanded_property_data("NB", "national", "counts", "01-2020", "12-2020", ctx=ctx)
        app_ctx.api_get.assert_called_once_with(
            "/supplemental/national/NB", {"type": "counts", "from": "01-2020", "to": "12-2020"}
        )

    async def test_invalid_aggregate(self, ctx):
        r = await get_expanded_property_data("NB", "national", "counts", "01-2020", "12-2020", aggregate="bad", ctx=ctx)
        assert "Invalid aggregate" in r

    async def test_totals_ignores_invalid_aggregate(self, ctx, app_ctx):
        await get_expanded_property_data("NB", "national", "totals", "01-2020", "12-2020", aggregate="bad", ctx=ctx)
        app_ctx.api_get.assert_called_once_with(
            "/supplemental/national/NB", {"type": "totals", "from": "01-2020", "to": "12-2020"}
        )

    async def test_all_supplemental_offenses(self, ctx, app_ctx):
        for code in ("NB", "NL", "NMVT", "NROB"):
            app_ctx.api_get.reset_mock()
            r = await get_expanded_property_data(code, "national", "counts", "01-2020", "12-2020", ctx=ctx)
            assert "Invalid" not in r

    async def test_invalid_from_date(self, ctx):
        r = await get_expanded_property_data("NB", "national", "counts", "2020", "12-2020", ctx=ctx)
        assert "mm-yyyy" in r

    async def test_invalid_to_date(self, ctx):
        r = await get_expanded_property_data("NB", "national", "counts", "01-2020", "bad", ctx=ctx)
        assert "mm-yyyy" in r
