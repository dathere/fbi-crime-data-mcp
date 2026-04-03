"""Tests for lookup_agency tool."""

from fbi_crime_data_mcp.tools.agency import lookup_agency


class TestLookupAgency:
    async def test_invalid_lookup_type(self, ctx):
        r = await lookup_agency("invalid", ctx=ctx)
        assert "Invalid lookup_type" in r

    # ── by_state ──
    async def test_by_state_missing_state(self, ctx):
        r = await lookup_agency("by_state", ctx=ctx)
        assert "'state' is required" in r

    async def test_by_state_invalid_state(self, ctx):
        r = await lookup_agency("by_state", state="ZZ", ctx=ctx)
        assert "Invalid state" in r

    async def test_by_state_success(self, ctx, app_ctx):
        await lookup_agency("by_state", state="NY", ctx=ctx)
        app_ctx.api_get.assert_called_once_with("/agency/byStateAbbr/NY")

    async def test_by_state_lowercased(self, ctx, app_ctx):
        await lookup_agency("by_state", state="ny", ctx=ctx)
        app_ctx.api_get.assert_called_once_with("/agency/byStateAbbr/NY")

    # ── by_ori ──
    async def test_by_ori_missing_state(self, ctx):
        r = await lookup_agency("by_ori", ori="NY0303000", ctx=ctx)
        assert "'state' and 'ori' are required" in r

    async def test_by_ori_missing_ori(self, ctx):
        r = await lookup_agency("by_ori", state="NY", ctx=ctx)
        assert "'state' and 'ori' are required" in r

    async def test_by_ori_invalid_state(self, ctx):
        r = await lookup_agency("by_ori", state="ZZ", ori="X", ctx=ctx)
        assert "Invalid state" in r

    async def test_by_ori_success(self, ctx, app_ctx):
        await lookup_agency("by_ori", state="NY", ori="NY0303000", ctx=ctx)
        app_ctx.api_get.assert_called_once_with("/agency/NY/NY0303000")

    # ── by_district ──
    async def test_by_district_missing_code(self, ctx):
        r = await lookup_agency("by_district", ctx=ctx)
        assert "'district_code' is required" in r

    async def test_by_district_success(self, ctx, app_ctx):
        await lookup_agency("by_district", district_code="DC1", ctx=ctx)
        app_ctx.api_get.assert_called_once_with("/agency/byDistCode/DC1")
