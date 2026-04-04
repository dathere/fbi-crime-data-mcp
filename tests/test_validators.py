"""Tests for shared validation helpers."""

from fbi_crime_data_mcp.validators import (
    build_geo_path,
    effective_aggregate,
    validate_aggregate,
    validate_crime_data_params,
    validate_data_type,
    validate_date_order_mm_yyyy,
    validate_date_order_yyyy,
    validate_level,
    validate_mm_yyyy,
    validate_offense,
    validate_ori_required,
    validate_state,
    validate_state_required,
    validate_year_int,
    validate_yyyy,
)


class TestValidateLevel:
    def test_valid_defaults(self):
        assert validate_level("national") is None
        assert validate_level("state") is None
        assert validate_level("agency") is None

    def test_invalid(self):
        assert "Invalid level" in validate_level("city")

    def test_custom_valid(self):
        assert validate_level("region", ("national", "state", "region")) is None

    def test_custom_invalid(self):
        assert "Invalid level" in validate_level("agency", ("national", "state"))


class TestValidateDataType:
    def test_valid(self):
        assert validate_data_type("counts") is None
        assert validate_data_type("totals") is None

    def test_invalid(self):
        assert "Invalid data_type" in validate_data_type("bad")


class TestValidateAggregate:
    def test_valid(self):
        assert validate_aggregate("counts", "yearly") is None
        assert validate_aggregate("counts", "monthly") is None

    def test_invalid_for_counts(self):
        assert "Invalid aggregate" in validate_aggregate("counts", "bad")

    def test_ignored_for_totals(self):
        assert validate_aggregate("totals", "bad") is None


class TestValidateState:
    def test_valid(self):
        assert validate_state("CA") is None
        assert validate_state("ny") is None

    def test_invalid(self):
        err = validate_state("ZZ")
        assert "Invalid state" in err
        assert "two-letter" in err

    def test_none_is_fine(self):
        assert validate_state(None) is None


class TestValidateStateRequired:
    def test_state_level_missing(self):
        assert "'state' is required" in validate_state_required("state", None)

    def test_state_level_present(self):
        assert validate_state_required("state", "CA") is None

    def test_other_level(self):
        assert validate_state_required("national", None) is None


class TestValidateOriRequired:
    def test_agency_level_missing(self):
        assert "'ori' is required" in validate_ori_required("agency", None)

    def test_agency_level_present(self):
        assert validate_ori_required("agency", "X1") is None

    def test_other_level(self):
        assert validate_ori_required("national", None) is None


class TestValidateMmYyyy:
    def test_valid(self):
        assert validate_mm_yyyy("01-2020", "from_date") is None
        assert validate_mm_yyyy("12-2022", "to_date") is None

    def test_invalid_format(self):
        assert "mm-yyyy" in validate_mm_yyyy("2020-01", "from_date")
        assert "mm-yyyy" in validate_mm_yyyy("1-2020", "from_date")
        assert "mm-yyyy" in validate_mm_yyyy("2020", "from_date")
        assert "mm-yyyy" in validate_mm_yyyy("January 2020", "from_date")

    def test_invalid_month(self):
        assert validate_mm_yyyy("00-2020", "from_date") is not None
        assert validate_mm_yyyy("13-2020", "from_date") is not None
        assert validate_mm_yyyy("99-9999", "from_date") is not None

    def test_includes_param_name(self):
        err = validate_mm_yyyy("bad", "from_date")
        assert "from_date" in err


class TestValidateYyyy:
    def test_valid(self):
        assert validate_yyyy("2020", "from_year") is None
        assert validate_yyyy("2015", "to_year") is None

    def test_invalid_format(self):
        assert "yyyy" in validate_yyyy("20", "from_year")
        assert "yyyy" in validate_yyyy("01-2020", "from_year")
        assert "yyyy" in validate_yyyy("abcd", "from_year")

    def test_includes_param_name(self):
        err = validate_yyyy("bad", "to_year")
        assert "to_year" in err


class TestValidateOffense:
    def test_valid(self):
        codes = {"A": "Alpha", "B": "Beta"}
        assert validate_offense("A", codes, "test code") is None

    def test_invalid(self):
        codes = {"A": "Alpha", "B": "Beta"}
        err = validate_offense("Z", codes, "test code")
        assert "Invalid test code" in err
        assert "'Z'" in err

    def test_invalid_with_hint(self):
        codes = {"A": "Alpha", "B": "Beta"}
        err = validate_offense("Z", codes, "test code", "Try 'A' or 'B'.")
        assert "Invalid test code" in err
        assert "'Z'" in err
        assert "Try 'A' or 'B'." in err

    def test_valid_ignores_hint(self):
        codes = {"A": "Alpha", "B": "Beta"}
        assert validate_offense("A", codes, "test code", "some hint") is None


class TestValidateCrimeDataParams:
    """Tests for the consolidated validate_crime_data_params helper."""

    def test_all_valid_minimal(self):
        assert (
            validate_crime_data_params(
                level="national",
                from_date="01-2020",
                to_date="12-2020",
            )
            is None
        )

    def test_all_valid_full(self):
        codes = {"09A": "Murder"}
        assert (
            validate_crime_data_params(
                level="national",
                from_date="01-2020",
                to_date="12-2020",
                data_type="counts",
                aggregate="yearly",
                offense="09A",
                offense_codes=codes,
                offense_label="test",
            )
            is None
        )

    def test_invalid_aggregate(self):
        err = validate_crime_data_params(
            level="national",
            from_date="01-2020",
            to_date="12-2020",
            data_type="counts",
            aggregate="bad",
        )
        assert "Invalid aggregate" in err

    def test_invalid_offense(self):
        codes = {"09A": "Murder"}
        err = validate_crime_data_params(
            level="national",
            from_date="01-2020",
            to_date="12-2020",
            offense="ZZZ",
            offense_codes=codes,
            offense_label="test code",
        )
        assert "Invalid test code" in err

    def test_invalid_level(self):
        err = validate_crime_data_params(
            level="city",
            from_date="01-2020",
            to_date="12-2020",
        )
        assert "Invalid level" in err

    def test_invalid_data_type(self):
        err = validate_crime_data_params(
            level="national",
            from_date="01-2020",
            to_date="12-2020",
            data_type="bad",
        )
        assert "Invalid data_type" in err

    def test_state_requires_state(self):
        err = validate_crime_data_params(
            level="state",
            from_date="01-2020",
            to_date="12-2020",
        )
        assert "'state' is required" in err

    def test_agency_requires_ori(self):
        err = validate_crime_data_params(
            level="agency",
            from_date="01-2020",
            to_date="12-2020",
            state="CA",
        )
        assert "'ori' is required" in err

    def test_invalid_state(self):
        err = validate_crime_data_params(
            level="state",
            from_date="01-2020",
            to_date="12-2020",
            state="ZZ",
        )
        assert "Invalid state" in err

    def test_invalid_from_date(self):
        err = validate_crime_data_params(
            level="national",
            from_date="2020",
            to_date="12-2020",
        )
        assert "mm-yyyy" in err

    def test_invalid_to_date(self):
        err = validate_crime_data_params(
            level="national",
            from_date="01-2020",
            to_date="bad",
        )
        assert "mm-yyyy" in err

    def test_aggregate_ignored_without_data_type(self):
        """aggregate validation is skipped when data_type is not provided."""
        assert (
            validate_crime_data_params(
                level="national",
                from_date="01-2020",
                to_date="12-2020",
                aggregate="bad",
            )
            is None
        )

    def test_offense_ignored_without_codes(self):
        """offense validation is skipped when offense_codes is not provided."""
        assert (
            validate_crime_data_params(
                level="national",
                from_date="01-2020",
                to_date="12-2020",
                offense="ZZZ",
            )
            is None
        )

    def test_from_date_after_to_date(self):
        err = validate_crime_data_params(
            level="national",
            from_date="06-2022",
            to_date="01-2020",
        )
        assert "after" in err
        assert "06-2022" in err
        assert "01-2020" in err

    def test_same_date_is_valid(self):
        assert (
            validate_crime_data_params(
                level="national",
                from_date="06-2020",
                to_date="06-2020",
            )
            is None
        )


class TestValidateYearInt:
    def test_valid(self):
        assert validate_year_int(2020) is None
        assert validate_year_int(1985) is None
        assert validate_year_int(2030) is None

    def test_too_low(self):
        err = validate_year_int(1984)
        assert "Invalid" in err
        assert "1985" in err

    def test_too_high(self):
        import datetime

        far_future = datetime.date.today().year + 6
        err = validate_year_int(far_future)
        assert "Invalid" in err
        assert str(datetime.date.today().year + 5) in err

    def test_includes_param_name(self):
        err = validate_year_int(0, "start_year")
        assert "start_year" in err


class TestValidateDateOrderMmYyyy:
    def test_valid_order(self):
        assert validate_date_order_mm_yyyy("01-2020", "12-2020") is None

    def test_same_date(self):
        assert validate_date_order_mm_yyyy("06-2020", "06-2020") is None

    def test_cross_year(self):
        assert validate_date_order_mm_yyyy("12-2019", "01-2020") is None

    def test_reversed(self):
        err = validate_date_order_mm_yyyy("12-2022", "01-2020")
        assert "after" in err

    def test_same_year_reversed_month(self):
        err = validate_date_order_mm_yyyy("06-2020", "01-2020")
        assert "after" in err

    def test_invalid_format_skipped(self):
        assert validate_date_order_mm_yyyy("bad", "01-2020") is None
        assert validate_date_order_mm_yyyy("01-2020", "bad") is None


class TestValidateDateOrderYyyy:
    def test_valid_order(self):
        assert validate_date_order_yyyy("2015", "2022") is None

    def test_same_year(self):
        assert validate_date_order_yyyy("2020", "2020") is None

    def test_reversed(self):
        err = validate_date_order_yyyy("2022", "2015")
        assert "after" in err

    def test_invalid_format_skipped(self):
        assert validate_date_order_yyyy("bad", "2020") is None
        assert validate_date_order_yyyy("2020", "bad") is None


class TestBuildGeoPath:
    def test_national(self):
        assert build_geo_path("/nibrs", "national") == "/nibrs/national"

    def test_national_with_suffix(self):
        assert build_geo_path("/nibrs", "national", suffix="09A") == "/nibrs/national/09A"

    def test_state(self):
        assert build_geo_path("/shr", "state", state="ca") == "/shr/state/CA"

    def test_state_with_suffix(self):
        assert build_geo_path("/arrest", "state", state="ny", suffix="11") == "/arrest/state/NY/11"

    def test_agency(self):
        assert build_geo_path("/shr", "agency", ori="X1") == "/shr/agency/X1"

    def test_agency_with_suffix(self):
        assert build_geo_path("/nibrs", "agency", ori="X1", suffix="09A") == "/nibrs/agency/X1/09A"

    def test_no_suffix(self):
        assert build_geo_path("/hate-crime", "national", suffix="") == "/hate-crime/national"


class TestEffectiveAggregate:
    def test_counts_returns_aggregate(self):
        assert effective_aggregate("counts", "yearly") == "yearly"
        assert effective_aggregate("counts", "monthly") == "monthly"

    def test_totals_returns_monthly(self):
        assert effective_aggregate("totals", "yearly") == "monthly"
        assert effective_aggregate("totals", "bad") == "monthly"
