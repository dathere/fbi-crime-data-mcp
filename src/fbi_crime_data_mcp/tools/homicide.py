"""Expanded homicide (SHR) data tool."""

from fastmcp import Context

from ..api_client import AppContext
from ..response_utils import process_crime_response
from ..server import mcp
from ..validators import (
    validate_aggregate,
    validate_data_type,
    validate_level,
    validate_mm_yyyy,
    validate_ori_required,
    validate_state,
    validate_state_required,
)


@mcp.tool()
async def get_expanded_homicide_data(
    level: str,
    data_type: str,
    from_date: str,
    to_date: str,
    state: str | None = None,
    ori: str | None = None,
    aggregate: str = "yearly",
    ctx: Context | None = None,
) -> str:
    """Get Supplementary Homicide Report (SHR) data with expanded details on homicides including victim/offender demographics, weapons, and circumstances.

    Args:
        level: Geographic level — "national", "state", or "agency"
        data_type: "counts" for time series or "totals" for demographic/detail breakdowns
        from_date: Start date in mm-yyyy format (e.g., "01-2020")
        to_date: End date in mm-yyyy format (e.g., "12-2022")
        state: Two-letter state abbreviation (required when level is "state")
        ori: Agency ORI code (required when level is "agency")
        aggregate: Aggregation level — "yearly" (default, sums monthly into yearly) or "monthly" (monthly granularity). Only applies when data_type is "counts".
    """
    for err in (
        validate_aggregate(data_type, aggregate),
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
        path = f"/shr/state/{state.upper()}"
    elif level == "agency":
        path = f"/shr/agency/{ori}"
    else:
        path = "/shr/national"

    app_ctx: AppContext = ctx.lifespan_context
    raw = await app_ctx.api_get(path, {"type": data_type, "from": from_date, "to": to_date})
    return process_crime_response(raw, aggregate=aggregate if data_type == "counts" else "monthly")
