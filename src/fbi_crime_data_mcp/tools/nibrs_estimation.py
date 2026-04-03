"""NIBRS estimation data tool."""

from fastmcp import Context

from ..api_client import AppContext
from ..constants import NIBRS_OFFENSES, NIBRS_REGIONS, NIBRS_SIZE_GROUPS
from ..server import mcp
from ..validators import validate_offense, validate_state


@mcp.tool()
async def get_nibrs_estimation(
    offense: str,
    level: str,
    year: int,
    state: str | None = None,
    region: str | None = None,
    agency_type: str | None = None,
    agency_type_location: str | None = None,
    size_group: str | None = None,
    ctx: Context | None = None,
) -> str:
    """Get NIBRS national crime estimates derived from incident data. Supports breakdowns by state, region, agency type, and population size.

    Args:
        offense: NIBRS offense code (e.g., "13A", "09A"). Use get_nibrs_data docs for codes.
        level: "national", "state", "region", "agency-type", or "size"
        year: Year for estimation data
        state: Two-letter state abbreviation (required when level is "state")
        region: Region code — "M" (Midwest), "N" (Northeast), "S" (South), "W" (West). Required when level is "region".
        agency_type: "S" (Size) or "T" (Agency Type). Required when level is "agency-type" or "size".
        agency_type_location: "C" (City) or "N" (County). Required when level is "agency-type".
        size_group: Size group "1"-"8" (1=Cities 250K+, 6=Cities under 10K, 7=MSA Counties, 8=Non-MSA Counties). Required when level is "size".
    """
    err = validate_offense(offense, NIBRS_OFFENSES, "NIBRS offense code")
    if err:
        return err
    if level not in ("national", "state", "region", "agency-type", "size"):
        return "Invalid level. Must be 'national', 'state', 'region', 'agency-type', or 'size'."

    if level == "national":
        path = f"/nibrs-estimation/national/{offense}"
    elif level == "state":
        if not state:
            return "Parameter 'state' is required when level is 'state'."
        err = validate_state(state)
        if err:
            return err
        path = f"/nibrs-estimation/state/{state.upper()}/{offense}"
    elif level == "region":
        if not region or region not in NIBRS_REGIONS:
            return f"Parameter 'region' is required. Valid values: {', '.join(f'{k} ({v})' for k, v in NIBRS_REGIONS.items())}"
        path = f"/nibrs-estimation/region/{region}/{offense}"
    elif level == "agency-type":
        if not agency_type or agency_type not in ("S", "T"):
            return "Parameter 'agency_type' is required ('S' for Size, 'T' for Agency Type)."
        if not agency_type_location or agency_type_location not in ("C", "N"):
            return "Parameter 'agency_type_location' is required ('C' for City, 'N' for County)."
        path = f"/nibrs-estimation/national/agency-type/{agency_type}/{agency_type_location}/{offense}"
    elif level == "size":
        if not agency_type or agency_type not in ("S", "T"):
            return "Parameter 'agency_type' is required ('S' for Size, 'T' for Agency Type)."
        if not size_group or size_group not in NIBRS_SIZE_GROUPS:
            return f"Parameter 'size_group' is required. Valid values: {', '.join(f'{k} ({v})' for k, v in NIBRS_SIZE_GROUPS.items())}"
        path = f"/nibrs-estimation/national/size/{agency_type}/{size_group}/{offense}"

    app_ctx: AppContext = ctx.lifespan_context
    return await app_ctx.api_get(path, {"year": str(year)})
