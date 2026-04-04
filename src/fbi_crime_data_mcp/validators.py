"""Shared validation helpers for FBI Crime Data MCP tools."""

from __future__ import annotations

import re

from .constants import US_STATES

_MM_YYYY_RE = re.compile(r"^(0[1-9]|1[0-2])-\d{4}$")
_YYYY_RE = re.compile(r"^\d{4}$")


def validate_level(level: str, valid: tuple[str, ...] = ("national", "state", "agency")) -> str | None:
    """Return error string if level is invalid, else None."""
    if level not in valid:
        return f"Invalid level. Must be {_join_options(valid)}."
    return None


def validate_data_type(data_type: str) -> str | None:
    """Return error string if data_type is invalid, else None."""
    if data_type not in ("counts", "totals"):
        return "Invalid data_type. Must be 'counts' or 'totals'."
    return None


def validate_aggregate(data_type: str, aggregate: str) -> str | None:
    """Return error string if aggregate is invalid for counts data, else None."""
    if data_type == "counts" and aggregate not in ("yearly", "monthly"):
        return "Invalid aggregate. Must be 'yearly' or 'monthly'."
    return None


def validate_state(state: str | None) -> str | None:
    """Return error string if state is provided but invalid, else None."""
    if state and state.upper() not in US_STATES:
        return f"Invalid state '{state}'. Use a two-letter abbreviation (e.g., 'CA', 'NY')."
    return None


def validate_state_required(level: str, state: str | None) -> str | None:
    """Return error string if state is required by level but missing, else None."""
    if level == "state" and not state:
        return "Parameter 'state' is required when level is 'state'."
    return None


def validate_ori_required(level: str, ori: str | None) -> str | None:
    """Return error string if ori is required by level but missing, else None."""
    if level == "agency" and not ori:
        return "Parameter 'ori' is required when level is 'agency'."
    return None


def validate_mm_yyyy(value: str, param_name: str) -> str | None:
    """Return error string if value doesn't match mm-yyyy format, else None."""
    if not _MM_YYYY_RE.match(value):
        return f"Invalid {param_name} '{value}'. Must be in mm-yyyy format (e.g., '01-2020')."
    return None


def validate_yyyy(value: str, param_name: str) -> str | None:
    """Return error string if value doesn't match yyyy format, else None."""
    if not _YYYY_RE.match(value):
        return f"Invalid {param_name} '{value}'. Must be in yyyy format (e.g., '2020')."
    return None


def validate_crime_data_params(
    *,
    level: str,
    from_date: str,
    to_date: str,
    state: str | None = None,
    ori: str | None = None,
    data_type: str | None = None,
    aggregate: str | None = None,
    offense: str | None = None,
    offense_codes: dict[str, str] | None = None,
    offense_label: str = "offense code",
    offense_hint: str = "",
) -> str | None:
    """Validate common crime data tool parameters.

    Always validates geo level and date parameters, along with any required
    geographic identifiers for the selected level. Validates ``data_type`` when
    it is provided. Validates ``aggregate`` only when both ``data_type`` and
    ``aggregate`` are provided. Validates ``offense`` only when both
    ``offense`` and ``offense_codes`` are provided.

    Returns an error string on the first validation failure, or None if all pass.
    """
    if data_type is not None and aggregate is not None:
        err = validate_aggregate(data_type, aggregate)
        if err:
            return err
    if offense is not None and offense_codes is not None:
        err = validate_offense(offense, offense_codes, offense_label, offense_hint)
        if err:
            return err
    err = validate_level(level)
    if err:
        return err
    if data_type is not None:
        err = validate_data_type(data_type)
        if err:
            return err
    for err in (
        validate_state_required(level, state),
        validate_ori_required(level, ori),
        validate_state(state),
        validate_mm_yyyy(from_date, "from_date"),
        validate_mm_yyyy(to_date, "to_date"),
    ):
        if err:
            return err
    return None


def validate_offense(code: str, valid_codes: dict[str, str], label: str, hint: str = "") -> str | None:
    """Return error string if offense code is invalid, else None."""
    if code not in valid_codes:
        msg = f"Invalid {label} '{code}'."
        if hint:
            msg = f"{msg} {hint}"
        return msg
    return None


def _join_options(options: tuple[str, ...]) -> str:
    """Format a tuple of options as a quoted, comma-separated list."""
    return ", ".join(f"'{o}'" for o in options)
