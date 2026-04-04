"""Expanded homicide (SHR) data tool."""

from fastmcp import Context

from ..api_client import AppContext
from ..response_utils import process_crime_response
from ..server import mcp
from ..validators import build_geo_path, effective_aggregate, validate_crime_data_params


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
    err = validate_crime_data_params(
        level=level,
        from_date=from_date,
        to_date=to_date,
        state=state,
        ori=ori,
        data_type=data_type,
        aggregate=aggregate,
    )
    if err:
        return err

    path = build_geo_path("/shr", level, state=state, ori=ori)

    app_ctx: AppContext = ctx.lifespan_context
    raw = await app_ctx.api_get(path, {"type": data_type, "from": from_date, "to": to_date})
    return process_crime_response(raw, aggregate=effective_aggregate(data_type, aggregate))
