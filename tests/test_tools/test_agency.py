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

    # ── name_filter ──
    async def test_name_filter_filters_by_state(self, ctx, app_ctx):
        import json

        agencies = [
            {"agency_name": "Secaucus Police Department"},
            {"agency_name": "Union City Police Department"},
        ]
        app_ctx.api_get.return_value = json.dumps(agencies)
        r = await lookup_agency("by_state", state="NJ", name_filter="Secaucus", ctx=ctx)
        result = json.loads(r)
        assert len(result) == 1
        assert result[0]["agency_name"] == "Secaucus Police Department"

    async def test_name_filter_case_insensitive(self, ctx, app_ctx):
        import json

        agencies = [{"agency_name": "Secaucus Police Department"}]
        app_ctx.api_get.return_value = json.dumps(agencies)
        r = await lookup_agency("by_state", state="NJ", name_filter="secaucus", ctx=ctx)
        result = json.loads(r)
        assert len(result) == 1

    async def test_name_filter_ignored_for_by_ori(self, ctx, app_ctx):
        """name_filter should not apply to by_ori lookups."""
        await lookup_agency("by_ori", state="NY", ori="NY0303000", name_filter="test", ctx=ctx)
        app_ctx.api_get.assert_called_once_with("/agency/NY/NY0303000")

    # ── name_filter on nested dicts (by_state) ──
    async def test_name_filter_nested_dict(self, ctx, app_ctx):
        """name_filter should work on by_state grouped responses."""
        import json

        grouped = {
            "HUDSON": [
                {"agency_name": "Secaucus Police Department"},
                {"agency_name": "Union City Police Department"},
            ],
            "ESSEX": [
                {"agency_name": "Newark Police Department"},
            ],
        }
        app_ctx.api_get.return_value = json.dumps(grouped)
        r = await lookup_agency("by_state", state="NJ", name_filter="Secaucus", ctx=ctx)
        result = json.loads(r)
        assert "HUDSON" in result
        assert len(result["HUDSON"]) == 1
        assert "ESSEX" not in result

    # ── pagination ──
    async def test_pagination_flat_list(self, ctx, app_ctx):
        import json

        agencies = [{"agency_name": f"Agency {i}"} for i in range(5)]
        app_ctx.api_get.return_value = json.dumps(agencies)
        r = await lookup_agency("by_state", state="NJ", offset=1, limit=2, ctx=ctx)
        result = json.loads(r)
        assert result["total"] == 5
        assert len(result["data"]) == 2
        assert result["data"][0]["agency_name"] == "Agency 1"

    async def test_pagination_after_filter(self, ctx, app_ctx):
        import json

        agencies = [{"agency_name": f"Police {i}"} for i in range(10)]
        agencies.append({"agency_name": "Fire Department"})
        app_ctx.api_get.return_value = json.dumps(agencies)
        r = await lookup_agency("by_state", state="NJ", name_filter="Police", offset=2, limit=3, ctx=ctx)
        result = json.loads(r)
        assert result["total"] == 10  # 10 police, filtered from 11
        assert len(result["data"]) == 3
        assert result["data"][0]["agency_name"] == "Police 2"

    async def test_pagination_defaults(self, ctx, app_ctx):
        """offset defaults to 0 and limit defaults to 100 when only one is given."""
        import json

        agencies = [{"agency_name": f"Agency {i}"} for i in range(3)]
        app_ctx.api_get.return_value = json.dumps(agencies)
        r = await lookup_agency("by_state", state="NJ", limit=2, ctx=ctx)
        result = json.loads(r)
        assert result["offset"] == 0
        assert result["limit"] == 2
        assert len(result["data"]) == 2
