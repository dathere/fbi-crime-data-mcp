"""Tests for get_reference_data tool."""

from fbi_crime_data_mcp.tools.reference import get_reference_data


class TestReferenceData:
    async def test_invalid_data_type(self, ctx):
        r = await get_reference_data("invalid", ctx=ctx)
        assert "Invalid data_type" in r

    async def test_offenses_requires_offense_type(self, ctx):
        r = await get_reference_data("offenses", ctx=ctx)
        assert "'offense_type' is required" in r

    async def test_offenses_invalid_offense_type(self, ctx):
        r = await get_reference_data("offenses", offense_type="bad", ctx=ctx)
        assert "'offense_type' is required" in r

    async def test_states_path(self, ctx, app_ctx):
        await get_reference_data("states", ctx=ctx)
        app_ctx.api_get.assert_called_once_with("/lookup/states", {})

    async def test_offenses_path(self, ctx, app_ctx):
        await get_reference_data("offenses", offense_type="arrest", ctx=ctx)
        app_ctx.api_get.assert_called_once_with("/lookup/offenses", {"type": "arrest"})

    async def test_cde_properties_path(self, ctx, app_ctx):
        await get_reference_data("cde_properties", ctx=ctx)
        app_ctx.api_get.assert_called_once_with("/lookup/cde_properties", {})

    async def test_refresh_date_path(self, ctx, app_ctx):
        await get_reference_data("refresh_date", ctx=ctx)
        app_ctx.api_get.assert_called_once_with("/refresh-date", {})
