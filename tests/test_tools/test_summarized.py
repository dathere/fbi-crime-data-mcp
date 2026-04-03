"""Tests for get_summarized_crime_data tool."""

from fbi_crime_data_mcp.tools.summarized import get_summarized_crime_data


class TestSummarizedCrimeData:
    async def test_invalid_offense(self, ctx):
        r = await get_summarized_crime_data("INVALID", "national", "01-2020", "12-2020", ctx=ctx)
        assert "Invalid offense code" in r

    async def test_invalid_level(self, ctx):
        r = await get_summarized_crime_data("V", "city", "01-2020", "12-2020", ctx=ctx)
        assert "Invalid level" in r

    async def test_state_requires_state_param(self, ctx):
        r = await get_summarized_crime_data("V", "state", "01-2020", "12-2020", ctx=ctx)
        assert "'state' is required" in r

    async def test_agency_requires_ori(self, ctx):
        r = await get_summarized_crime_data("V", "agency", "01-2020", "12-2020", ctx=ctx)
        assert "'ori' is required" in r

    async def test_invalid_state(self, ctx):
        r = await get_summarized_crime_data("V", "state", "01-2020", "12-2020", state="ZZ", ctx=ctx)
        assert "Invalid state" in r

    async def test_national_path(self, ctx, app_ctx):
        await get_summarized_crime_data("HOM", "national", "01-2020", "12-2022", ctx=ctx)
        app_ctx.api_get.assert_called_once_with(
            "/summarized/national/HOM", {"from": "01-2020", "to": "12-2022"}
        )

    async def test_state_path(self, ctx, app_ctx):
        await get_summarized_crime_data("ROB", "state", "01-2020", "12-2020", state="CA", ctx=ctx)
        app_ctx.api_get.assert_called_once_with(
            "/summarized/state/CA/ROB", {"from": "01-2020", "to": "12-2020"}
        )

    async def test_agency_path(self, ctx, app_ctx):
        await get_summarized_crime_data("V", "agency", "01-2021", "12-2025", ori="NY0303000", ctx=ctx)
        app_ctx.api_get.assert_called_once_with(
            "/summarized/agency/NY0303000/V", {"from": "01-2021", "to": "12-2025"}
        )

    async def test_all_srs_offenses_accepted(self, ctx, app_ctx):
        for code in ("V", "P", "HOM", "RPE", "ROB", "ASS", "BUR", "LAR", "MVT", "ARS"):
            app_ctx.api_get.reset_mock()
            r = await get_summarized_crime_data(code, "national", "01-2020", "12-2020", ctx=ctx)
            assert "Invalid" not in r
