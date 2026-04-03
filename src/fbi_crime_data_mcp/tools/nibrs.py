"""NIBRS (National Incident-Based Reporting System) data tool."""

from fastmcp import Context

from ..api_client import AppContext
from ..constants import NIBRS_OFFENSES
from ..response_utils import process_crime_response
from ..server import mcp
from ..validators import (
    validate_aggregate,
    validate_data_type,
    validate_level,
    validate_mm_yyyy,
    validate_offense,
    validate_ori_required,
    validate_state,
    validate_state_required,
)


@mcp.tool()
async def get_nibrs_data(
    offense: str,
    level: str,
    from_date: str,
    to_date: str,
    data_type: str = "counts",
    state: str | None = None,
    ori: str | None = None,
    aggregate: str = "yearly",
    ctx: Context | None = None,
) -> str:
    """Get NIBRS incident-based crime data for 70+ offense types.

    Args:
        offense: NIBRS offense code (e.g., "13A" for aggravated assault, "09A" for murder, "11A" for rape, "120" for robbery, "220" for burglary). Use get_reference_data for full list.
        level: Geographic level — "national", "state", or "agency"
        from_date: Start date in mm-yyyy format (e.g., "01-2020")
        to_date: End date in mm-yyyy format (e.g., "12-2022")
        data_type: "counts" for time series data or "totals" for aggregate breakdowns (default: "counts")
        state: Two-letter state abbreviation (required when level is "state")
        ori: Agency ORI code (required when level is "agency")
        aggregate: Aggregation level — "yearly" (default, sums monthly into yearly) or "monthly" (monthly granularity). Only applies when data_type is "counts".
    """
    for err in (
        validate_aggregate(data_type, aggregate),
        validate_offense(offense, NIBRS_OFFENSES, "NIBRS offense code"),
        validate_level(level),
        validate_data_type(data_type),
        validate_state_required(level, state),
        validate_ori_required(level, ori),
        validate_state(state),
        validate_mm_yyyy(from_date, "from_date"),
        validate_mm_yyyy(to_date, "to_date"),
    ):
        if err:
            return err

    if level == "state":
        path = f"/nibrs/state/{state.upper()}/{offense}"
    elif level == "agency":
        path = f"/nibrs/agency/{ori}/{offense}"
    else:
        path = f"/nibrs/national/{offense}"

    app_ctx: AppContext = ctx.lifespan_context
    raw = await app_ctx.api_get(path, {"type": data_type, "from": from_date, "to": to_date})
    return process_crime_response(raw, aggregate=aggregate if data_type == "counts" else "monthly")
