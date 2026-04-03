"""Tests for shared validation helpers."""

from fbi_crime_data_mcp.validators import (
    validate_aggregate,
    validate_data_type,
    validate_level,
    validate_mm_yyyy,
    validate_offense,
    validate_ori_required,
    validate_state,
    validate_state_required,
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
