"""Tests for remaining tools: trends, employment, hate_crime, homicide, property_data, leoka, lesdc, reference, use_of_force."""

from fbi_crime_data_mcp.tools.trends import get_crime_trends
from fbi_crime_data_mcp.tools.employment import get_police_employment
from fbi_crime_data_mcp.tools.hate_crime import get_hate_crime_data
from fbi_crime_data_mcp.tools.homicide import get_expanded_homicide_data
from fbi_crime_data_mcp.tools.property_data import get_expanded_property_data
from fbi_crime_data_mcp.tools.leoka import get_leoka_data
from fbi_crime_data_mcp.tools.lesdc import get_lesdc_data
from fbi_crime_data_mcp.tools.reference import get_reference_data
from fbi_crime_data_mcp.tools.use_of_force import get_use_of_force_data


# ── Crime Trends ─────────────────────────────────────────────────────────────


class TestCrimeTrends:
    async def test_no_params(self, ctx, app_ctx):
        await get_crime_trends(ctx=ctx)
        app_ctx.api_get.assert_called_once_with("/trends/national", {})

    async def test_from_year_only(self, ctx, app_ctx):
        await get_crime_trends(from_year="2015", ctx=ctx)
        app_ctx.api_get.assert_called_once_with("/trends/national", {"from": "2015"})

    async def test_to_year_only(self, ctx, app_ctx):
        await get_crime_trends(to_year="2022", ctx=ctx)
        app_ctx.api_get.assert_called_once_with("/trends/national", {"to": "2022"})

    async def test_both_years(self, ctx, app_ctx):
        await get_crime_trends(from_year="2015", to_year="2022", ctx=ctx)
        app_ctx.api_get.assert_called_once_with(
            "/trends/national", {"from": "2015", "to": "2022"}
        )


# ── Police Employment ────────────────────────────────────────────────────────


class TestPoliceEmployment:
    async def test_invalid_level(self, ctx):
        r = await get_police_employment("city", "2015", "2022", ctx=ctx)
        assert "Invalid level" in r

    async def test_state_requires_state(self, ctx):
        r = await get_police_employment("state", "2015", "2022", ctx=ctx)
        assert "'state' is required" in r

    async def test_agency_requires_both(self, ctx):
        r = await get_police_employment("agency", "2015", "2022", state="NY", ctx=ctx)
        assert "'state' and 'ori' are required" in r

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
        app_ctx.api_get.assert_called_once_with(
            "/pe/region/south", {"from": "2015", "to": "2022"}
        )


# ── Hate Crime ───────────────────────────────────────────────────────────────


class TestHateCrime:
    async def test_invalid_level(self, ctx):
        r = await get_hate_crime_data("city", "01-2020", "12-2020", ctx=ctx)
        assert "Invalid level" in r

    async def test_invalid_data_type(self, ctx):
        r = await get_hate_crime_data("national", "01-2020", "12-2020", data_type="bad", ctx=ctx)
        assert "Invalid data_type" in r

    async def test_state_requires_state(self, ctx):
        r = await get_hate_crime_data("state", "01-2020", "12-2020", ctx=ctx)
        assert "'state' is required" in r

    async def test_agency_requires_ori(self, ctx):
        r = await get_hate_crime_data("agency", "01-2020", "12-2020", ctx=ctx)
        assert "'ori' is required" in r

    async def test_invalid_bias(self, ctx):
        r = await get_hate_crime_data("national", "01-2020", "12-2020", bias="INVALID", ctx=ctx)
        assert "Invalid bias code" in r

    async def test_invalid_state(self, ctx):
        r = await get_hate_crime_data("state", "01-2020", "12-2020", state="ZZ", ctx=ctx)
        assert "Invalid state" in r

    async def test_national_path(self, ctx, app_ctx):
        await get_hate_crime_data("national", "01-2020", "12-2020", ctx=ctx)
        app_ctx.api_get.assert_called_once_with(
            "/hate-crime/national", {"type": "counts", "from": "01-2020", "to": "12-2020"}
        )

    async def test_bias_appended(self, ctx, app_ctx):
        await get_hate_crime_data("national", "01-2020", "12-2020", bias="all", ctx=ctx)
        app_ctx.api_get.assert_called_once_with(
            "/hate-crime/national/all", {"type": "counts", "from": "01-2020", "to": "12-2020"}
        )

    async def test_state_path(self, ctx, app_ctx):
        await get_hate_crime_data("state", "01-2020", "12-2020", state="CA", ctx=ctx)
        app_ctx.api_get.assert_called_once_with(
            "/hate-crime/state/CA", {"type": "counts", "from": "01-2020", "to": "12-2020"}
        )

    async def test_agency_path(self, ctx, app_ctx):
        await get_hate_crime_data("agency", "01-2020", "12-2020", ori="X1", ctx=ctx)
        app_ctx.api_get.assert_called_once_with(
            "/hate-crime/agency/X1", {"type": "counts", "from": "01-2020", "to": "12-2020"}
        )

    async def test_invalid_aggregate(self, ctx):
        r = await get_hate_crime_data("national", "01-2020", "12-2020", aggregate="bad", ctx=ctx)
        assert "Invalid aggregate" in r


# ── Expanded Homicide ────────────────────────────────────────────────────────


class TestHomicide:
    async def test_invalid_level(self, ctx):
        r = await get_expanded_homicide_data("city", "counts", "01-2020", "12-2020", ctx=ctx)
        assert "Invalid level" in r

    async def test_invalid_data_type(self, ctx):
        r = await get_expanded_homicide_data("national", "bad", "01-2020", "12-2020", ctx=ctx)
        assert "Invalid data_type" in r

    async def test_state_requires_state(self, ctx):
        r = await get_expanded_homicide_data("state", "counts", "01-2020", "12-2020", ctx=ctx)
        assert "'state' is required" in r

    async def test_agency_requires_ori(self, ctx):
        r = await get_expanded_homicide_data("agency", "counts", "01-2020", "12-2020", ctx=ctx)
        assert "'ori' is required" in r

    async def test_invalid_state(self, ctx):
        r = await get_expanded_homicide_data("state", "counts", "01-2020", "12-2020", state="ZZ", ctx=ctx)
        assert "Invalid state" in r

    async def test_national_path(self, ctx, app_ctx):
        await get_expanded_homicide_data("national", "counts", "01-2020", "12-2020", ctx=ctx)
        app_ctx.api_get.assert_called_once_with(
            "/shr/national", {"type": "counts", "from": "01-2020", "to": "12-2020"}
        )

    async def test_state_path(self, ctx, app_ctx):
        await get_expanded_homicide_data("state", "totals", "01-2020", "12-2020", state="TX", ctx=ctx)
        app_ctx.api_get.assert_called_once_with(
            "/shr/state/TX", {"type": "totals", "from": "01-2020", "to": "12-2020"}
        )

    async def test_agency_path(self, ctx, app_ctx):
        await get_expanded_homicide_data("agency", "counts", "01-2020", "12-2020", ori="X1", ctx=ctx)
        app_ctx.api_get.assert_called_once_with(
            "/shr/agency/X1", {"type": "counts", "from": "01-2020", "to": "12-2020"}
        )

    async def test_invalid_aggregate(self, ctx):
        r = await get_expanded_homicide_data("national", "counts", "01-2020", "12-2020", aggregate="bad", ctx=ctx)
        assert "Invalid aggregate" in r


# ── Expanded Property Data ───────────────────────────────────────────────────


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

    async def test_all_supplemental_offenses(self, ctx, app_ctx):
        for code in ("NB", "NL", "NMVT", "NROB"):
            app_ctx.api_get.reset_mock()
            r = await get_expanded_property_data(code, "national", "counts", "01-2020", "12-2020", ctx=ctx)
            assert "Invalid" not in r


# ── LEOKA ────────────────────────────────────────────────────────────────────


class TestLeoka:
    async def test_invalid_report_type(self, ctx):
        r = await get_leoka_data("invalid", 2022, ctx=ctx)
        assert "Invalid report_type" in r

    async def test_monthly_requires_month(self, ctx):
        r = await get_leoka_data("monthly", 2022, ctx=ctx)
        assert "'month'" in r

    async def test_month_too_low(self, ctx):
        r = await get_leoka_data("monthly", 2022, month=-1, ctx=ctx)
        assert "between 0" in r

    async def test_month_too_high(self, ctx):
        r = await get_leoka_data("monthly", 2022, month=12, ctx=ctx)
        assert "between 0" in r

    async def test_monthly_path(self, ctx, app_ctx):
        await get_leoka_data("monthly", 2022, month=0, ctx=ctx)
        app_ctx.api_get.assert_called_once_with(
            "/leoka/monthly", {"year": "2022", "month": "0"}
        )

    async def test_ytd_path(self, ctx, app_ctx):
        await get_leoka_data("ytd", 2022, ctx=ctx)
        app_ctx.api_get.assert_called_once_with("/leoka/ytd", {"year": "2022"})

    async def test_month_boundary_11(self, ctx, app_ctx):
        await get_leoka_data("monthly", 2022, month=11, ctx=ctx)
        app_ctx.api_get.assert_called_once_with(
            "/leoka/monthly", {"year": "2022", "month": "11"}
        )


# ── LESDC ────────────────────────────────────────────────────────────────────


class TestLesdc:
    async def test_invalid_chart_type(self, ctx):
        r = await get_lesdc_data(2022, "invalid", ctx=ctx)
        assert "Invalid chart_type" in r

    async def test_valid_chart_type(self, ctx, app_ctx):
        await get_lesdc_data(2022, "demographics", ctx=ctx)
        app_ctx.api_get.assert_called_once_with(
            "/lesdc", {"year": "2022", "chartType": "demographics"}
        )


# ── Reference Data ───────────────────────────────────────────────────────────


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


# ── Use of Force ─────────────────────────────────────────────────────────────


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

    async def test_summary_national(self, ctx, app_ctx):
        await get_use_of_force_data("summary", year=2022, location="national", ctx=ctx)
        app_ctx.api_get.assert_called_once_with(
            "/uof", {"year": "2022", "location": "national"}
        )

    async def test_summary_state(self, ctx, app_ctx):
        await get_use_of_force_data("summary", year=2022, location="ca", ctx=ctx)
        app_ctx.api_get.assert_called_once_with(
            "/uof", {"year": "2022", "location": "CA"}
        )

    # ── questions ──
    async def test_questions_requires_params(self, ctx):
        r = await get_use_of_force_data("questions", ctx=ctx)
        assert "'group', 'year', and 'quarter'" in r

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
