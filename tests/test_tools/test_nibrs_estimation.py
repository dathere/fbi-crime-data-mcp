"""Tests for get_nibrs_estimation tool."""

from fbi_crime_data_mcp.tools.nibrs_estimation import get_nibrs_estimation


class TestNibrsEstimation:
    async def test_invalid_offense(self, ctx):
        r = await get_nibrs_estimation("INVALID", "national", 2022, ctx=ctx)
        assert "Invalid NIBRS offense code" in r

    async def test_invalid_level(self, ctx):
        r = await get_nibrs_estimation("09A", "city", 2022, ctx=ctx)
        assert "Invalid level" in r

    async def test_national_path(self, ctx, app_ctx):
        await get_nibrs_estimation("09A", "national", 2022, ctx=ctx)
        app_ctx.api_get.assert_called_once_with(
            "/nibrs-estimation/national/09A", {"year": "2022"}
        )

    # ── state ──
    async def test_state_requires_state(self, ctx):
        r = await get_nibrs_estimation("09A", "state", 2022, ctx=ctx)
        assert "'state' is required" in r

    async def test_state_invalid_state(self, ctx):
        r = await get_nibrs_estimation("09A", "state", 2022, state="ZZ", ctx=ctx)
        assert "Invalid state" in r

    async def test_state_path(self, ctx, app_ctx):
        await get_nibrs_estimation("09A", "state", 2022, state="CA", ctx=ctx)
        app_ctx.api_get.assert_called_once_with(
            "/nibrs-estimation/state/CA/09A", {"year": "2022"}
        )

    # ── region ──
    async def test_region_requires_region(self, ctx):
        r = await get_nibrs_estimation("09A", "region", 2022, ctx=ctx)
        assert "'region' is required" in r

    async def test_region_invalid(self, ctx):
        r = await get_nibrs_estimation("09A", "region", 2022, region="X", ctx=ctx)
        assert "'region' is required" in r

    async def test_region_path(self, ctx, app_ctx):
        await get_nibrs_estimation("09A", "region", 2022, region="S", ctx=ctx)
        app_ctx.api_get.assert_called_once_with(
            "/nibrs-estimation/region/S/09A", {"year": "2022"}
        )

    # ── agency-type ──
    async def test_agency_type_requires_agency_type(self, ctx):
        r = await get_nibrs_estimation("09A", "agency-type", 2022, ctx=ctx)
        assert "'agency_type' is required" in r

    async def test_agency_type_requires_location(self, ctx):
        r = await get_nibrs_estimation("09A", "agency-type", 2022, agency_type="S", ctx=ctx)
        assert "'agency_type_location' is required" in r

    async def test_agency_type_path(self, ctx, app_ctx):
        await get_nibrs_estimation("09A", "agency-type", 2022, agency_type="T", agency_type_location="C", ctx=ctx)
        app_ctx.api_get.assert_called_once_with(
            "/nibrs-estimation/national/agency-type/T/C/09A", {"year": "2022"}
        )

    # ── size ──
    async def test_size_requires_agency_type(self, ctx):
        r = await get_nibrs_estimation("09A", "size", 2022, ctx=ctx)
        assert "'agency_type' is required" in r

    async def test_size_requires_size_group(self, ctx):
        r = await get_nibrs_estimation("09A", "size", 2022, agency_type="S", ctx=ctx)
        assert "'size_group' is required" in r

    async def test_size_invalid_group(self, ctx):
        r = await get_nibrs_estimation("09A", "size", 2022, agency_type="S", size_group="9", ctx=ctx)
        assert "'size_group' is required" in r

    async def test_size_path(self, ctx, app_ctx):
        await get_nibrs_estimation("09A", "size", 2022, agency_type="S", size_group="1", ctx=ctx)
        app_ctx.api_get.assert_called_once_with(
            "/nibrs-estimation/national/size/S/1/09A", {"year": "2022"}
        )
