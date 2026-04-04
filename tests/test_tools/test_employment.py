"""Tests for get_police_employment tool."""

from fbi_crime_data_mcp.tools.employment import get_police_employment


class TestPoliceEmployment:
    async def test_invalid_level(self, ctx):
        r = await get_police_employment("city", "2015", "2022", ctx=ctx)
        assert "Invalid level" in r

    async def test_state_requires_state(self, ctx):
        r = await get_police_employment("state", "2015", "2022", ctx=ctx)
        assert "'state' is required" in r

    async def test_agency_requires_state_when_both_missing(self, ctx):
        r = await get_police_employment("agency", "2015", "2022", ctx=ctx)
        assert "'state' is required" in r

    async def test_agency_requires_ori(self, ctx):
        r = await get_police_employment("agency", "2015", "2022", state="NY", ctx=ctx)
        assert "'ori' is required" in r

    async def test_agency_requires_state(self, ctx):
        r = await get_police_employment("agency", "2015", "2022", ori="X1", ctx=ctx)
        assert "'state' is required" in r

    async def test_region_requires_valid_region(self, ctx):
        r = await get_police_employment("region", "2015", "2022", ctx=ctx)
        assert "'region' is required" in r

    async def test_region_invalid(self, ctx):
        r = await get_police_employment("region", "2015", "2022", region="north", ctx=ctx)
        assert "'region' is required" in r

    async def test_invalid_state(self, ctx):
        r = await get_police_employment("state", "2015", "2022", state="ZZ", ctx=ctx)
        assert "Invalid state" in r

    async def test_national_path(self, ctx, app_ctx):
        await get_police_employment("national", "2015", "2022", ctx=ctx)
        app_ctx.api_get.assert_called_once_with("/pe", {"from": "2015", "to": "2022"})

    async def test_state_path(self, ctx, app_ctx):
        await get_police_employment("state", "2015", "2022", state="NY", ctx=ctx)
        app_ctx.api_get.assert_called_once_with("/pe/NY", {"from": "2015", "to": "2022"})

    async def test_agency_path(self, ctx, app_ctx):
        await get_police_employment("agency", "2015", "2022", state="NY", ori="X1", ctx=ctx)
        app_ctx.api_get.assert_called_once_with("/pe/NY/X1", {"from": "2015", "to": "2022"})

    async def test_region_path(self, ctx, app_ctx):
        await get_police_employment("region", "2015", "2022", region="south", ctx=ctx)
        app_ctx.api_get.assert_called_once_with("/pe/region/south", {"from": "2015", "to": "2022"})

    async def test_invalid_from_year(self, ctx):
        r = await get_police_employment("national", "01-2020", "2022", ctx=ctx)
        assert "yyyy" in r

    async def test_invalid_to_year(self, ctx):
        r = await get_police_employment("national", "2015", "bad", ctx=ctx)
        assert "yyyy" in r

    async def test_from_year_after_to_year(self, ctx):
        r = await get_police_employment("national", "2022", "2015", ctx=ctx)
        assert "after" in r
