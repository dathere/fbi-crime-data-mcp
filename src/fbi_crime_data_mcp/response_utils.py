"""Post-processing utilities for FBI Crime Data API responses."""

from __future__ import annotations

import json
import re
from collections import defaultdict

_MM_YYYY_RE = re.compile(r"^(\d{2})-(\d{4})$")

# Subsection names where values should be averaged (rates) or use the last
# observed monthly value when collapsed to yearly data (populations)
_RATE_KEYS = {"rates"}
_POPULATION_KEYS = {"population"}


def process_crime_response(raw_json: str, aggregate: str = "yearly") -> str:
    """Post-process a crime data API response.

    Trims verbose sections (tooltips, participated_population) and optionally
    aggregates monthly mm-yyyy data into yearly totals.

    Args:
        raw_json: JSON string from api_get, or an error/validation string.
        aggregate: "yearly" to aggregate monthly data into yearly totals,
                   "monthly" to keep raw monthly data (still trims).
    """
    if not raw_json.startswith("{"):
        return raw_json

    try:
        data = json.loads(raw_json)
    except (json.JSONDecodeError, TypeError):
        return raw_json

    if not isinstance(data, dict):
        return raw_json

    data = _trim_response(data)

    if aggregate == "yearly":
        data = _aggregate_yearly(data)

    return json.dumps(data, indent=2)


def filter_agencies_by_name(raw_json: str, name_filter: str) -> str:
    """Filter agency list by case-insensitive substring match on agency_name.

    Handles both flat arrays and nested dicts (by_state returns
    ``{"COUNTY": [agencies...], ...}``).

    Args:
        raw_json: JSON string from api_get — a JSON array or a dict of arrays.
        name_filter: Substring to match against agency_name field.
    """
    try:
        data = json.loads(raw_json)
    except (json.JSONDecodeError, TypeError):
        return raw_json

    needle = name_filter.lower()

    if isinstance(data, list):
        filtered = [
            a
            for a in data
            if isinstance(a, dict)
            and needle in a.get("agency_name", "").lower()
        ]
        return json.dumps(filtered, indent=2)

    if isinstance(data, dict):
        filtered = {}
        for group, agencies in data.items():
            if not isinstance(agencies, list):
                continue
            matches = [
                a
                for a in agencies
                if isinstance(a, dict)
                and needle in a.get("agency_name", "").lower()
            ]
            if matches:
                filtered[group] = matches
        return json.dumps(filtered, indent=2)

    return raw_json


def paginate_response(raw_json: str, offset: int, limit: int) -> str:
    """Apply offset/limit pagination to a JSON array or dict-of-arrays response.

    For flat arrays, slices the list directly.  For dicts (by_state grouped
    responses), flattens all agencies across groups, slices, and returns the
    page with a metadata wrapper.

    Args:
        raw_json: JSON string — array or dict of arrays.
        offset: Number of items to skip (must be >= 0).
        limit: Maximum number of items to return (must be > 0).
    """
    if offset < 0:
        return f"Invalid offset ({offset}). Must be >= 0."
    if limit <= 0:
        return f"Invalid limit ({limit}). Must be > 0."

    try:
        data = json.loads(raw_json)
    except (json.JSONDecodeError, TypeError):
        return raw_json

    if isinstance(data, list):
        total = len(data)
        page = data[offset : offset + limit]
        result = {"total": total, "offset": offset, "limit": limit, "data": page}
        return json.dumps(result, indent=2)

    if isinstance(data, dict):
        # Flatten grouped agencies, preserving group info
        flat: list[dict] = []
        for group, agencies in data.items():
            if not isinstance(agencies, list):
                continue
            for agency in agencies:
                if isinstance(agency, dict):
                    entry = {**agency, "_pagination_group": group}
                    flat.append(entry)
        if not flat:
            return raw_json
        total = len(flat)
        page = flat[offset : offset + limit]
        result = {"total": total, "offset": offset, "limit": limit, "data": page}
        return json.dumps(result, indent=2)

    return raw_json


def _trim_response(data: dict) -> dict:
    """Remove tooltips and participated_population from response."""
    data.pop("tooltips", None)

    populations = data.get("populations")
    if isinstance(populations, dict):
        populations.pop("participated_population", None)

    return data


def _aggregate_yearly(data: dict) -> dict:
    """Aggregate monthly mm-yyyy keyed time series into yearly values."""
    result = {}
    for key, value in data.items():
        if not isinstance(value, dict):
            result[key] = value
            continue
        result[key] = _aggregate_section(value, _strategy_for_key(key))
    return result


def _strategy_for_key(key: str) -> str:
    """Determine aggregation strategy from section key name."""
    lower = key.lower()
    if lower in _POPULATION_KEYS:
        return "last"
    if lower in _RATE_KEYS:
        return "avg"
    return "sum"


def _aggregate_section(section: dict, parent_strategy: str) -> dict:
    """Recursively walk a section and aggregate any mm-yyyy keyed dicts found."""
    if _is_monthly_dict(section):
        return _collapse_monthly(section, parent_strategy)

    result = {}
    for key, value in section.items():
        if not isinstance(value, dict):
            result[key] = value
            continue
        strategy = _strategy_for_key(key) if parent_strategy == "sum" else parent_strategy
        result[key] = _aggregate_section(value, strategy)
    return result


def _is_monthly_dict(d: dict) -> bool:
    """Check if a dict's keys are mm-yyyy formatted dates."""
    if not d:
        return False
    return all(_MM_YYYY_RE.match(k) for k in d)


def _collapse_monthly(monthly: dict, strategy: str) -> dict:
    """Collapse mm-yyyy keyed values into yyyy keyed values."""
    years: dict[str, list[tuple[int, float | int | None]]] = defaultdict(list)
    for key, value in monthly.items():
        m = _MM_YYYY_RE.match(key)
        if not m:
            continue
        month_num, year = int(m.group(1)), m.group(2)
        years[year].append((month_num, value))

    result = {}
    for year in sorted(years):
        entries = sorted(years[year])
        values = [v for _, v in entries]
        result[year] = _apply_strategy(values, strategy)
    return result


def _apply_strategy(
    values: list[float | int | None], strategy: str
) -> float | int | None:
    """Reduce a list of monthly values to a single yearly value."""
    non_null = [v for v in values if v is not None]
    if not non_null:
        return None
    if strategy == "sum":
        total = sum(non_null)
        return total if any(isinstance(v, float) for v in non_null) else int(total)
    if strategy == "avg":
        return round(sum(non_null) / len(non_null), 2)
    if strategy == "last":
        return non_null[-1]
    raise ValueError(f"Unknown aggregation strategy: {strategy!r}")
