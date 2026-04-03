"""Agency lookup tool."""

from fastmcp import Context

from ..api_client import AppContext
from ..constants import US_STATES
from ..response_utils import filter_agencies_by_name
from ..server import mcp


@mcp.tool()
async def lookup_agency(
    lookup_type: str,
    state: str | None = None,
    ori: str | None = None,
    district_code: str | None = None,
    name_filter: str | None = None,
    ctx: Context | None = None,
) -> str:
    """Look up law enforcement agencies by state, ORI code, or judicial district code.

    Args:
        lookup_type: How to look up — "by_state" (list agencies in a state), "by_ori" (specific agency by ORI), or "by_district" (agencies by judicial district code)
        state: Two-letter state abbreviation (required for by_state and by_ori)
        ori: Agency ORI identifier (required for by_ori)
        district_code: Judicial district code (required for by_district)
        name_filter: Optional substring to filter results by agency name (case-insensitive). Only applies to by_state and by_district lookups.
    """
    if lookup_type not in ("by_state", "by_ori", "by_district"):
        return "Invalid lookup_type. Must be 'by_state', 'by_ori', or 'by_district'."

    if lookup_type == "by_state":
        if not state:
            return "Parameter 'state' is required for by_state lookup."
        if state.upper() not in US_STATES:
            return f"Invalid state '{state}'. Use a two-letter abbreviation."
        path = f"/agency/byStateAbbr/{state.upper()}"

    elif lookup_type == "by_ori":
        if not state or not ori:
            return "Both 'state' and 'ori' are required for by_ori lookup."
        if state.upper() not in US_STATES:
            return f"Invalid state '{state}'. Use a two-letter abbreviation."
        path = f"/agency/{state.upper()}/{ori}"

    else:  # by_district
        if not district_code:
            return "Parameter 'district_code' is required for by_district lookup."
        path = f"/agency/byDistCode/{district_code}"

    app_ctx: AppContext = ctx.lifespan_context
    raw = await app_ctx.api_get(path)

    if name_filter and lookup_type in ("by_state", "by_district"):
        return filter_agencies_by_name(raw, name_filter)
    return raw
