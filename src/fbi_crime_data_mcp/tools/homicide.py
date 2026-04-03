"""Expanded homicide (SHR) data tool."""

from fastmcp import Context

from ..api_client import AppContext
from ..constants import US_STATES
from ..response_utils import process_crime_response
from ..server import mcp


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
        aggregate: Aggregation level — "yearly" (default, sums monthly into yearly) or "monthly" (raw monthly data). Only applies when data_type is "counts".
    """
    if data_type == "counts" and aggregate not in ("yearly", "monthly"):
        return "Invalid aggregate. Must be 'yearly' or 'monthly'."
    if level not in ("national", "state", "agency"):
        return "Invalid level. Must be 'national', 'state', or 'agency'."
    if data_type not in ("counts", "totals"):
        return "Invalid data_type. Must be 'counts' or 'totals'."
    if level == "state" and not state:
        return "Parameter 'state' is required when level is 'state'."
    if level == "agency" and not ori:
        return "Parameter 'ori' is required when level is 'agency'."
    if state and state.upper() not in US_STATES:
        return f"Invalid state '{state}'."

    if level == "state":
        path = f"/shr/state/{state.upper()}"
    elif level == "agency":
        path = f"/shr/agency/{ori}"
    else:
        path = "/shr/national"

    app_ctx: AppContext = ctx.lifespan_context
    raw = await app_ctx.api_get(path, {"type": data_type, "from": from_date, "to": to_date})
    return process_crime_response(raw, aggregate=aggregate if data_type == "counts" else "monthly")
