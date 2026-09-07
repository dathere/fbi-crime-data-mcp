"""Post-processing utilities for FBI Crime Data API responses."""

from __future__ import annotations

import json
from collections import defaultdict

from .validators import MM_YYYY_RE as _MM_YYYY_RE

# Subsection names where values should be averaged (rates) or use the last
# observed monthly value when collapsed to yearly data (populations)
_RATE_KEYS = {"rates"}
_POPULATION_KEYS = {"population"}

# Top-level key added to yearly-aggregated responses when any year has fewer
# than 12 months of data (requested range not Jan-Dec aligned, or the FBI has
# not published the remaining months). Underscore-prefixed like the synthetic
# ``_pagination_group`` field so it is recognisable as ours, not the API's.
PARTIAL_YEARS_KEY = "_partial_years"
_PARTIAL_YEARS_NOTE = (
    "Yearly values for these years are computed from fewer than 12 months in at least one series: "
    "counts are sums and rates are unweighted averages of the months available, so they are NOT "
    "full-year figures. Coverage may be short because the requested date range does not span "
    "January to December, or because the FBI has not yet published the remaining months. Use a "
    "January-to-December range for complete annual figures, or pass aggregate='monthly' to see "
    "the underlying months. 'incomplete_series' is listed only when some series in the response "
    "are complete and others are not."
)

# year -> series path ("offenses.rates.Agency Offenses") -> set of mm strings
# seen while collapsing that series. Tracked per series, not per response,
# so a complete population series cannot mask an incomplete rates series.
_Coverage = dict[str, dict[str, set[str]]]


def _new_coverage() -> _Coverage:
    return defaultdict(lambda: defaultdict(set))


def process_crime_response(raw_json: str, aggregate: str = "yearly") -> str:
    """Post-process a crime data API response.

    Trims verbose sections (tooltips, participated_population) and optionally
    aggregates monthly mm-yyyy data into yearly totals.

    Args:
        raw_json: JSON string from api_get, or an error/validation string.
        aggregate: "yearly" to aggregate monthly data into yearly totals,
                   "monthly" to keep raw monthly data (still trims).
    """
    try:
        data = json.loads(raw_json)
    except (json.JSONDecodeError, TypeError, ValueError):
        return raw_json

    if not isinstance(data, dict):
        return raw_json

    data = _trim_response(data)

    if aggregate == "yearly":
        coverage = _new_coverage()
        data = _aggregate_yearly(data, coverage)
        partial = _partial_years(coverage)
        if partial:
            # Put the marker first so a reader (human or model) sees it before the numbers.
            data = {PARTIAL_YEARS_KEY: partial, **data}

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
        filtered = [a for a in data if isinstance(a, dict) and needle in a.get("agency_name", "").lower()]
        return json.dumps(filtered, indent=2)

    if isinstance(data, dict):
        # Only filter if this is actually a dict-of-arrays; pass through otherwise
        has_list_groups = any(isinstance(v, list) for v in data.values())
        if not has_list_groups:
            return raw_json
        filtered = {}
        for group, agencies in data.items():
            if not isinstance(agencies, list):
                continue
            matches = [a for a in agencies if isinstance(a, dict) and needle in a.get("agency_name", "").lower()]
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


def _aggregate_yearly(data: dict, coverage: _Coverage | None = None) -> dict:
    """Aggregate monthly mm-yyyy keyed time series into yearly values.

    If *coverage* is given, every ``mm`` seen per year is recorded in it,
    keyed by the dotted path of the series it came from.
    """
    result = {}
    for key, value in data.items():
        if not isinstance(value, dict):
            result[key] = value
            continue
        result[key] = _aggregate_section(value, _strategy_for_key(key), coverage, (key,))
    return result


def _partial_years(coverage: _Coverage) -> dict | None:
    """Build the ``_partial_years`` marker, or None if every series has 12 months in every year.

    A year is flagged when *any* series in it has fewer than 12 months.
    ``months_covered`` is the smallest coverage among the incomplete series and
    ``from``/``to`` span the months those series have. ``incomplete_series`` is
    included only when the incomplete series are a strict subset of all series
    for that year; when every series is short (the usual case, a date range
    that is not January-to-December) the counts alone say so.
    """
    years = {}
    for year in sorted(coverage):
        series = coverage[year]
        incomplete = {path: months for path, months in series.items() if len(months) < 12}
        if not incomplete:
            continue
        span = sorted(set().union(*incomplete.values()))
        entry = {
            "months_covered": min(len(m) for m in incomplete.values()),
            "from": f"{span[0]}-{year}",
            "to": f"{span[-1]}-{year}",
            "series_incomplete": len(incomplete),
            "series_total": len(series),
        }
        if len(incomplete) < len(series):
            entry["incomplete_series"] = sorted(incomplete)
        years[year] = entry
    if not years:
        return None
    return {"note": _PARTIAL_YEARS_NOTE, "years": years}


def _strategy_for_key(key: str) -> str:
    """Determine aggregation strategy from section key name."""
    lower = key.lower()
    if lower in _POPULATION_KEYS:
        return "last"
    if lower in _RATE_KEYS:
        return "avg"
    return "sum"


def _aggregate_section(
    section: dict,
    parent_strategy: str,
    coverage: _Coverage | None = None,
    path: tuple[str, ...] = (),
) -> dict:
    """Recursively walk a section and aggregate any mm-yyyy keyed dicts found.

    Strategy-inheritance invariant: while *parent_strategy* is ``"sum"`` (the
    default), each child key is independently re-classified via
    ``_strategy_for_key`` — this is how we discover nested ``rates`` or
    ``population`` subsections. Once we've descended into a non-sum subtree
    (e.g. inside ``rates``), ALL further descendants inherit that strategy
    so nested rate breakdowns stay averaged rather than reverting to summing.
    """
    if _is_monthly_dict(section):
        return _collapse_monthly(section, parent_strategy, coverage, path)

    result = {}
    for key, value in section.items():
        if not isinstance(value, dict):
            result[key] = value
            continue
        strategy = _strategy_for_key(key) if parent_strategy == "sum" else parent_strategy
        result[key] = _aggregate_section(value, strategy, coverage, (*path, key))
    return result


def _is_monthly_dict(d: dict) -> bool:
    """Check if a dict's keys are mm-yyyy formatted dates."""
    if not d:
        return False
    return all(_MM_YYYY_RE.match(k) for k in d)


def _collapse_monthly(
    monthly: dict,
    strategy: str,
    coverage: _Coverage | None = None,
    path: tuple[str, ...] = (),
) -> dict:
    """Collapse mm-yyyy keyed values into yyyy keyed values.

    Records each ``mm`` seen per year in *coverage* (if given) under this
    series' dotted *path* so the caller can flag years where any series has
    fewer than 12 months of data.
    """
    series_path = ".".join(path)
    years: dict[str, list[tuple[int, float | int | None]]] = defaultdict(list)
    for key, value in monthly.items():
        m = _MM_YYYY_RE.match(key)
        if not m:
            continue
        month_str, year = m.group(1), m.group(2)
        years[year].append((int(month_str), value))
        if coverage is not None:
            coverage[year][series_path].add(month_str)

    result = {}
    for year in sorted(years):
        entries = sorted(years[year])
        values = [v for _, v in entries]
        result[year] = _apply_strategy(values, strategy)
    return result


def _apply_strategy(values: list[float | int | None], strategy: str) -> float | int | None:
    """Reduce a list of monthly values to a single yearly value."""
    non_null = [v for v in values if v is not None]
    if not non_null:
        return None
    if strategy == "sum":
        total = sum(non_null)
        return total if any(isinstance(v, float) for v in non_null) else int(total)
    if strategy == "avg":
        # Unweighted average — acceptable when population is roughly constant
        # within a year. A population-weighted average would be more precise but
        # requires cross-referencing population data from a sibling section.
        return round(sum(non_null) / len(non_null), 2)
    if strategy == "last":
        return non_null[-1]
    raise ValueError(f"Unknown aggregation strategy: {strategy!r}")
