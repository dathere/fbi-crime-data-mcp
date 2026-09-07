"""Tests for response_utils module."""

import json

from fbi_crime_data_mcp.response_utils import (
    PARTIAL_YEARS_KEY,
    filter_agencies_by_name,
    paginate_response,
    process_crime_response,
)

# --- Fixtures: realistic API response structures ---

MONTHLY_RESPONSE = {
    "offenses": {
        "rates": {
            "Agency Offenses": {
                "01-2023": 10.0,
                "02-2023": 20.0,
                "03-2023": 30.0,
                "01-2024": 15.0,
                "02-2024": 25.0,
            }
        },
        "actuals": {
            "Agency Offenses": {
                "01-2023": 5,
                "02-2023": 3,
                "03-2023": 7,
                "01-2024": 4,
                "02-2024": 6,
            },
            "Agency Clearances": {
                "01-2023": 2,
                "02-2023": 1,
                "03-2023": 3,
                "01-2024": 2,
                "02-2024": 4,
            },
        },
    },
    "tooltips": {
        "leftYAxisHeaders": {"yAxisHeaderRates": "Offenses per 100,000"},
        "Percent of Population Coverage": {"State": {"01-2023": 50.0}},
    },
    "populations": {
        "population": {
            "Agency": {
                "01-2023": 50000,
                "02-2023": 50000,
                "03-2023": 50000,
                "01-2024": 51000,
                "02-2024": 51000,
            }
        },
        "participated_population": {
            "State": {
                "01-2023": 8000000,
                "02-2023": 8000000,
            }
        },
    },
    "cde_properties": {"max_data_date": {"UCR": "03/2026"}},
}

AGENCY_LIST = [
    {"ori": "NJ0090900", "agency_name": "Secaucus Police Department", "state_abbr": "NJ"},
    {"ori": "NJ0091000", "agency_name": "Union City Police Department", "state_abbr": "NJ"},
    {"ori": "NJ0090100", "agency_name": "Bayonne Police Department", "state_abbr": "NJ"},
    {"ori": "NJ0090200", "agency_name": "East Newark Police Department", "state_abbr": "NJ"},
]


class TestProcessCrimeResponse:
    def test_error_string_passthrough(self):
        assert process_crime_response("Error: timeout") == "Error: timeout"

    def test_rate_limit_passthrough(self):
        msg = "Rate limit reached (1000 requests per 1 hour). Try again in ~30 seconds."
        assert process_crime_response(msg) == msg

    def test_validation_error_passthrough(self):
        msg = "Invalid offense code 'XYZ'."
        assert process_crime_response(msg) == msg

    def test_non_json_passthrough(self):
        assert process_crime_response("not json at all") == "not json at all"

    def test_trimming_removes_tooltips(self):
        raw = json.dumps(MONTHLY_RESPONSE)
        result = json.loads(process_crime_response(raw, aggregate="monthly"))
        assert "tooltips" not in result

    def test_trimming_removes_participated_population(self):
        raw = json.dumps(MONTHLY_RESPONSE)
        result = json.loads(process_crime_response(raw, aggregate="monthly"))
        assert "participated_population" not in result["populations"]

    def test_trimming_keeps_population(self):
        raw = json.dumps(MONTHLY_RESPONSE)
        result = json.loads(process_crime_response(raw, aggregate="monthly"))
        assert "population" in result["populations"]

    def test_trimming_keeps_cde_properties(self):
        raw = json.dumps(MONTHLY_RESPONSE)
        result = json.loads(process_crime_response(raw, aggregate="monthly"))
        assert "cde_properties" in result

    def test_monthly_preserves_mm_yyyy_keys(self):
        raw = json.dumps(MONTHLY_RESPONSE)
        result = json.loads(process_crime_response(raw, aggregate="monthly"))
        actuals = result["offenses"]["actuals"]["Agency Offenses"]
        assert "01-2023" in actuals

    def test_yearly_sums_actuals(self):
        raw = json.dumps(MONTHLY_RESPONSE)
        result = json.loads(process_crime_response(raw, aggregate="yearly"))
        actuals = result["offenses"]["actuals"]["Agency Offenses"]
        assert actuals["2023"] == 15  # 5 + 3 + 7
        assert actuals["2024"] == 10  # 4 + 6

    def test_yearly_sums_clearances(self):
        raw = json.dumps(MONTHLY_RESPONSE)
        result = json.loads(process_crime_response(raw, aggregate="yearly"))
        clearances = result["offenses"]["actuals"]["Agency Clearances"]
        assert clearances["2023"] == 6  # 2 + 1 + 3
        assert clearances["2024"] == 6  # 2 + 4

    def test_yearly_averages_rates(self):
        raw = json.dumps(MONTHLY_RESPONSE)
        result = json.loads(process_crime_response(raw, aggregate="yearly"))
        rates = result["offenses"]["rates"]["Agency Offenses"]
        assert rates["2023"] == 20.0  # avg(10, 20, 30)
        assert rates["2024"] == 20.0  # avg(15, 25)

    def test_yearly_population_uses_last(self):
        raw = json.dumps(MONTHLY_RESPONSE)
        result = json.loads(process_crime_response(raw, aggregate="yearly"))
        pop = result["populations"]["population"]["Agency"]
        assert pop["2023"] == 50000
        assert pop["2024"] == 51000

    def test_null_values_skipped_in_sum(self):
        data = {
            "offenses": {
                "actuals": {
                    "Series": {
                        "01-2023": 5,
                        "02-2023": None,
                        "03-2023": 3,
                    }
                }
            }
        }
        raw = json.dumps(data)
        result = json.loads(process_crime_response(raw, aggregate="yearly"))
        assert result["offenses"]["actuals"]["Series"]["2023"] == 8

    def test_all_null_year_returns_null(self):
        data = {
            "offenses": {
                "actuals": {
                    "Series": {
                        "01-2023": None,
                        "02-2023": None,
                    }
                }
            }
        }
        raw = json.dumps(data)
        result = json.loads(process_crime_response(raw, aggregate="yearly"))
        assert result["offenses"]["actuals"]["Series"]["2023"] is None

    def test_partial_year_sums_available_months(self):
        data = {
            "offenses": {
                "actuals": {
                    "Series": {
                        "01-2024": 10,
                        "02-2024": 10,
                        "03-2024": 10,
                        "04-2024": 10,
                        "05-2024": 10,
                        "06-2024": 10,
                        "07-2024": 10,
                        "08-2024": 10,
                        "09-2024": 10,
                        "10-2024": 10,
                        "11-2024": 10,
                        "12-2024": 10,
                        "01-2025": 5,
                        "02-2025": 5,
                        "03-2025": 5,
                    }
                }
            }
        }
        raw = json.dumps(data)
        result = json.loads(process_crime_response(raw, aggregate="yearly"))
        series = result["offenses"]["actuals"]["Series"]
        assert series["2024"] == 120
        assert series["2025"] == 15  # only 3 months

    def test_non_monthly_dict_preserved(self):
        data = {
            "cde_properties": {"max_data_date": {"UCR": "03/2026"}},
            "offenses": {"actuals": {"Series": {"01-2023": 5, "02-2023": 3}}},
        }
        raw = json.dumps(data)
        result = json.loads(process_crime_response(raw, aggregate="yearly"))
        assert result["cde_properties"]["max_data_date"]["UCR"] == "03/2026"

    def test_simple_json_without_monthly_keys(self):
        """Non-crime responses (e.g. mock '{"ok": true}') pass through gracefully."""
        raw = '{"ok": true}'
        result = json.loads(process_crime_response(raw, aggregate="yearly"))
        assert result == {"ok": True}

    def test_actuals_integers_stay_integers(self):
        data = {"offenses": {"actuals": {"Series": {"01-2023": 5, "02-2023": 3}}}}
        raw = json.dumps(data)
        result = json.loads(process_crime_response(raw, aggregate="yearly"))
        val = result["offenses"]["actuals"]["Series"]["2023"]
        assert val == 8
        assert isinstance(val, int)


class TestFilterAgenciesByName:
    def test_exact_match(self):
        raw = json.dumps(AGENCY_LIST)
        result = json.loads(filter_agencies_by_name(raw, "Secaucus"))
        assert len(result) == 1
        assert result[0]["ori"] == "NJ0090900"

    def test_case_insensitive(self):
        raw = json.dumps(AGENCY_LIST)
        result = json.loads(filter_agencies_by_name(raw, "secaucus"))
        assert len(result) == 1

    def test_substring_match(self):
        raw = json.dumps(AGENCY_LIST)
        result = json.loads(filter_agencies_by_name(raw, "Newark"))
        assert len(result) == 1
        assert result[0]["agency_name"] == "East Newark Police Department"

    def test_multiple_matches(self):
        raw = json.dumps(AGENCY_LIST)
        result = json.loads(filter_agencies_by_name(raw, "Police"))
        assert len(result) == 4

    def test_no_matches(self):
        raw = json.dumps(AGENCY_LIST)
        result = json.loads(filter_agencies_by_name(raw, "Hoboken"))
        assert result == []

    def test_error_passthrough(self):
        assert filter_agencies_by_name("Error: timeout", "test") == "Error: timeout"

    def test_nested_dict_filtering(self):
        """by_state responses are dicts of county → agency arrays."""
        grouped = {
            "HUDSON": [
                {"agency_name": "Secaucus Police Department"},
                {"agency_name": "Union City Police Department"},
            ],
            "ESSEX": [
                {"agency_name": "Newark Police Department"},
            ],
        }
        raw = json.dumps(grouped)
        result = json.loads(filter_agencies_by_name(raw, "Newark"))
        assert "ESSEX" in result
        assert len(result["ESSEX"]) == 1
        assert "HUDSON" not in result

    def test_nested_dict_multiple_groups(self):
        grouped = {
            "HUDSON": [{"agency_name": "Secaucus Police Department"}],
            "ESSEX": [{"agency_name": "East Newark Police Department"}],
        }
        raw = json.dumps(grouped)
        result = json.loads(filter_agencies_by_name(raw, "Police"))
        assert len(result) == 2

    def test_nested_dict_no_matches(self):
        grouped = {
            "HUDSON": [{"agency_name": "Secaucus Police Department"}],
        }
        raw = json.dumps(grouped)
        result = json.loads(filter_agencies_by_name(raw, "Hoboken"))
        assert result == {}

    def test_non_dict_non_list_passthrough(self):
        raw = '"just a string"'
        assert filter_agencies_by_name(raw, "test") == raw


class TestPaginateResponse:
    def test_flat_array_pagination(self):
        items = [{"name": f"item_{i}"} for i in range(10)]
        raw = json.dumps(items)
        result = json.loads(paginate_response(raw, offset=2, limit=3))
        assert result["total"] == 10
        assert result["offset"] == 2
        assert result["limit"] == 3
        assert len(result["data"]) == 3
        assert result["data"][0]["name"] == "item_2"

    def test_flat_array_offset_beyond_end(self):
        items = [{"name": "a"}, {"name": "b"}]
        raw = json.dumps(items)
        result = json.loads(paginate_response(raw, offset=5, limit=10))
        assert result["total"] == 2
        assert result["data"] == []

    def test_nested_dict_pagination(self):
        grouped = {
            "GROUP_A": [{"agency_name": "A1"}, {"agency_name": "A2"}],
            "GROUP_B": [{"agency_name": "B1"}],
        }
        raw = json.dumps(grouped)
        result = json.loads(paginate_response(raw, offset=0, limit=2))
        assert result["total"] == 3
        assert len(result["data"]) == 2
        # Flattened items get _pagination_group key
        assert "_pagination_group" in result["data"][0]

    def test_nested_dict_offset(self):
        grouped = {
            "GROUP_A": [{"agency_name": "A1"}, {"agency_name": "A2"}],
            "GROUP_B": [{"agency_name": "B1"}],
        }
        raw = json.dumps(grouped)
        result = json.loads(paginate_response(raw, offset=2, limit=10))
        assert result["total"] == 3
        assert len(result["data"]) == 1
        assert result["data"][0]["agency_name"] == "B1"

    def test_error_passthrough(self):
        assert paginate_response("Error: timeout", 0, 10) == "Error: timeout"

    def test_negative_offset(self):
        result = paginate_response(json.dumps([1, 2, 3]), -1, 10)
        assert "Invalid offset" in result

    def test_zero_limit(self):
        result = paginate_response(json.dumps([1, 2, 3]), 0, 0)
        assert "Invalid limit" in result

    def test_non_list_non_dict_passthrough(self):
        raw = json.dumps("just a string")
        assert paginate_response(raw, 0, 10) == raw

    def test_dict_with_non_list_values_passthrough(self):
        raw = json.dumps({"key": "not_a_list"})
        assert paginate_response(raw, 0, 10) == raw

    def test_dict_with_empty_flat_passthrough(self):
        """Dict of lists but no dict entries inside produces empty flat list → passthrough."""
        raw = json.dumps({"group": [42, "string"]})
        assert paginate_response(raw, 0, 10) == raw


class TestProcessCrimeResponseEdgeCases:
    def test_non_dict_data_passthrough(self):
        """Array response passes through unchanged."""
        raw = json.dumps([1, 2, 3])
        assert process_crime_response(raw) == raw

    def test_non_json_passthrough(self):
        assert process_crime_response("Error: bad request") == "Error: bad request"


class TestFilterAgenciesEdgeCases:
    def test_dict_without_lists_passthrough(self):
        """Dict where no values are lists passes through unchanged."""
        raw = json.dumps({"key": "value", "count": 42})
        assert filter_agencies_by_name(raw, "test") == raw

    def test_non_list_groups_skipped(self):
        """Non-list values in dict-of-groups are skipped during filtering."""
        raw = json.dumps({"GROUP_A": [{"agency_name": "Test PD"}], "metadata": "info"})
        result = json.loads(filter_agencies_by_name(raw, "test"))
        assert "GROUP_A" in result
        assert "metadata" not in result

    def test_non_dict_non_list_passthrough(self):
        raw = json.dumps("just a string")
        assert filter_agencies_by_name(raw, "test") == raw


class TestAggregationInternalEdgeCases:
    """Cover internal edge cases in _collapse_monthly, _is_monthly_dict, _apply_strategy."""

    def test_unknown_strategy_raises(self):
        import pytest

        from fbi_crime_data_mcp.response_utils import _apply_strategy

        with pytest.raises(ValueError, match="Unknown aggregation strategy"):
            _apply_strategy([1, 2, 3], "unknown")

    def test_is_monthly_dict_empty(self):
        from fbi_crime_data_mcp.response_utils import _is_monthly_dict

        assert _is_monthly_dict({}) is False

    def test_collapse_monthly_non_matching_key_skipped(self):
        from fbi_crime_data_mcp.response_utils import _collapse_monthly

        # Mix of valid and invalid keys — invalid keys are skipped
        result = _collapse_monthly({"01-2023": 10, "bad-key": 5, "02-2023": 20}, "sum")
        assert "2023" in result
        assert result["2023"] == 30  # bad-key is ignored


class TestPartialYearsMarker:
    """Yearly aggregation flags years with fewer than 12 months of data."""

    @staticmethod
    def _series(months: dict) -> str:
        return json.dumps({"offenses": {"actuals": {"Series": months}}})

    def test_full_years_have_no_marker(self):
        months = {f"{m:02d}-2024": 1 for m in range(1, 13)}
        result = json.loads(process_crime_response(self._series(months), aggregate="yearly"))
        assert PARTIAL_YEARS_KEY not in result

    def test_partial_year_is_flagged_with_coverage(self):
        months = {f"{m:02d}-2024": 1 for m in range(1, 13)}
        months.update({"01-2025": 1, "02-2025": 1, "03-2025": 1})
        result = json.loads(process_crime_response(self._series(months), aggregate="yearly"))

        marker = result[PARTIAL_YEARS_KEY]
        assert "note" in marker and "unweighted" in marker["note"]
        assert marker["years"] == {
            "2025": {
                "months_covered": 3,
                "from": "01-2025",
                "to": "03-2025",
                "series_incomplete": 1,
                "series_total": 1,
            }
        }
        # The yearly values themselves are unchanged
        assert result["offenses"]["actuals"]["Series"] == {"2024": 12, "2025": 3}

    def test_marker_comes_first(self):
        result = json.loads(process_crime_response(self._series({"06-2024": 1}), aggregate="yearly"))
        assert next(iter(result)) == PARTIAL_YEARS_KEY

    def test_non_contiguous_months_report_from_to(self):
        result = json.loads(process_crime_response(self._series({"02-2024": 1, "11-2024": 1}), aggregate="yearly"))
        assert result[PARTIAL_YEARS_KEY]["years"]["2024"] == {
            "months_covered": 2,
            "from": "02-2024",
            "to": "11-2024",
            "series_incomplete": 1,
            "series_total": 1,
        }

    def test_complete_series_cannot_mask_incomplete_one(self):
        # rates only has Jan; population has all 12. The year must still be
        # flagged, and the marker must say which series is short.
        data = {
            "offenses": {"rates": {"S": {"01-2024": 1.0}}},
            "populations": {"population": {"S": {f"{m:02d}-2024": 100 for m in range(1, 13)}}},
        }
        result = json.loads(process_crime_response(json.dumps(data), aggregate="yearly"))
        assert result[PARTIAL_YEARS_KEY]["years"]["2024"] == {
            "months_covered": 1,
            "from": "01-2024",
            "to": "01-2024",
            "series_incomplete": 1,
            "series_total": 2,
            "incomplete_series": ["offenses.rates.S"],
        }

    def test_months_covered_is_minimum_across_incomplete_series(self):
        # Two short series with different coverage: report the worst, span the union
        data = {
            "offenses": {
                "actuals": {
                    "A": {"01-2024": 1, "02-2024": 1, "03-2024": 1},
                    "B": {"06-2024": 1},
                }
            }
        }
        result = json.loads(process_crime_response(json.dumps(data), aggregate="yearly"))
        entry = result[PARTIAL_YEARS_KEY]["years"]["2024"]
        assert entry["months_covered"] == 1
        assert (entry["from"], entry["to"]) == ("01-2024", "06-2024")
        assert entry["series_incomplete"] == entry["series_total"] == 2
        assert "incomplete_series" not in entry  # all short → counts suffice

    def test_incomplete_series_listed_only_when_subset(self):
        data = {
            "offenses": {
                "actuals": {
                    "A": {f"{m:02d}-2024": 1 for m in range(1, 13)},
                    "B": {f"{m:02d}-2024": 1 for m in range(1, 13)},
                    "C": {"12-2024": 1},
                }
            }
        }
        result = json.loads(process_crime_response(json.dumps(data), aggregate="yearly"))
        entry = result[PARTIAL_YEARS_KEY]["years"]["2024"]
        assert entry["incomplete_series"] == ["offenses.actuals.C"]
        assert (entry["series_incomplete"], entry["series_total"]) == (1, 3)

    def test_partial_year_in_one_series_only_flags_that_year(self):
        data = {
            "offenses": {
                "actuals": {
                    "A": {f"{m:02d}-2024": 1 for m in range(1, 13)} | {"01-2025": 1},
                    "B": {f"{m:02d}-2024": 1 for m in range(1, 13)},
                }
            }
        }
        result = json.loads(process_crime_response(json.dumps(data), aggregate="yearly"))
        assert list(result[PARTIAL_YEARS_KEY]["years"]) == ["2025"]

    def test_null_months_still_count_as_covered(self):
        # A published-but-null month is coverage; only absent keys make a year partial
        months = {f"{m:02d}-2024": (None if m % 2 else 1) for m in range(1, 13)}
        result = json.loads(process_crime_response(self._series(months), aggregate="yearly"))
        assert PARTIAL_YEARS_KEY not in result

    def test_monthly_aggregate_adds_no_marker(self):
        result = json.loads(process_crime_response(self._series({"06-2024": 1}), aggregate="monthly"))
        assert PARTIAL_YEARS_KEY not in result

    def test_fixture_response_flags_both_partial_years(self):
        result = json.loads(process_crime_response(json.dumps(MONTHLY_RESPONSE), aggregate="yearly"))
        years = result[PARTIAL_YEARS_KEY]["years"]
        assert years["2023"]["months_covered"] == 3
        assert years["2024"]["months_covered"] == 2
