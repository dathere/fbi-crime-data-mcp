"""Tests for get_use_of_force_data tool."""

from fbi_crime_data_mcp.tools.use_of_force import get_use_of_force_data


class TestUseOfForce:
    async def test_invalid_report_type(self, ctx):
        r = await get_use_of_force_data("invalid", ctx=ctx)
        assert "Invalid report_type" in r

    # ── summary ──
    async def test_summary_requires_year_and_location(self, ctx):
        r = await get_use_of_force_data("summary", ctx=ctx)
        assert "'year' and 'location'" in r

    async def test_summary_invalid_location(self, ctx):
        r = await get_use_of_force_data("summary", year=2022, location="ZZ", ctx=ctx)
        assert "Invalid location" in r

    async def test_summary_invalid_year(self, ctx):
        r = await get_use_of_force_data("summary", year=1900, location="national", ctx=ctx)
        assert "Invalid" in r and "year" in r

    async def test_summary_national(self, ctx, app_ctx):
        await get_use_of_force_data("summary", year=2022, location="national", ctx=ctx)
        app_ctx.api_get.assert_called_once_with("/uof", {"year": "2022", "location": "national"})

    async def test_summary_state(self, ctx, app_ctx):
        await get_use_of_force_data("summary", year=2022, location="ca", ctx=ctx)
        app_ctx.api_get.assert_called_once_with("/uof", {"year": "2022", "location": "CA"})

    # ── questions ──
    async def test_questions_requires_params(self, ctx):
        r = await get_use_of_force_data("questions", ctx=ctx)
        assert "'group', 'year', and 'quarter'" in r

    async def test_questions_invalid_year(self, ctx):
        r = await get_use_of_force_data("questions", group="g1", year=1900, quarter=1, ctx=ctx)
        assert "Invalid" in r and "year" in r

    async def test_questions_invalid_quarter(self, ctx):
        r = await get_use_of_force_data("questions", group="g1", year=2022, quarter=5, ctx=ctx)
        assert "between 1 and 4" in r

    async def test_questions_quarter_zero(self, ctx):
        r = await get_use_of_force_data("questions", group="g1", year=2022, quarter=0, ctx=ctx)
        assert "between 1 and 4" in r

    async def test_questions_path(self, ctx, app_ctx):
        await get_use_of_force_data("questions", group="g1", year=2022, quarter=3, ctx=ctx)
        app_ctx.api_get.assert_called_once_with("/uof/questions/g1/2022/3")

    # ── reports ──
    async def test_reports_requires_params(self, ctx):
        r = await get_use_of_force_data("reports", ctx=ctx)
        assert "'group' and 'spec'" in r

    async def test_reports_path(self, ctx, app_ctx):
        await get_use_of_force_data("reports", group="g1", spec="s1", ctx=ctx)
        app_ctx.api_get.assert_called_once_with("/uof/reports/g1/s1")
