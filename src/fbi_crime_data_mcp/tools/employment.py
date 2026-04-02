"""Police employment (PE) data tool."""

from mcp.server.fastmcp import Context

from ..api_client import AppContext
from ..constants import US_STATES
from ..server import mcp

VALID_REGIONS = {"midwest", "south", "northeast", "west"}


@mcp.tool()
async def get_police_employment(
    level: str,
    from_year: str,
    to_year: str,
    state: str | None = None,
    ori: str | None = None,
    region: str | None = None,
    ctx: Context | None = None,
) -> str:
    """Get law enforcement employee data including officer/civilian counts by gender, rates per 1,000 population.

    Args:
        level: Geographic level — "national", "state", "agency", or "region"
        from_year: Start year in yyyy format (e.g., "2015")
        to_year: End year in yyyy format (e.g., "2022")
        state: Two-letter state abbreviation (required for "state" and "agency" levels)
        ori: Agency ORI code (required for "agency" level)
        region: Region name — "midwest", "south", "northeast", or "west" (required for "region" level)
    """
    if level not in ("national", "state", "agency", "region"):
        return "Invalid level. Must be 'national', 'state', 'agency', or 'region'."
    if level == "state" and not state:
        return "Parameter 'state' is required when level is 'state'."
    if level == "agency" and (not state or not ori):
        return "Both 'state' and 'ori' are required when level is 'agency'."
    if level == "region" and (not region or region.lower() not in VALID_REGIONS):
        return f"Parameter 'region' is required. Valid values: {', '.join(VALID_REGIONS)}"
    if state and state.upper() not in US_STATES:
        return f"Invalid state '{state}'."

    if level == "state":
        path = f"/pe/{state.upper()}"
    elif level == "agency":
        path = f"/pe/{state.upper()}/{ori}"
    elif level == "region":
        path = f"/pe/region/{region.lower()}"
    else:
        path = "/pe"

    app_ctx: AppContext = ctx.request_context.lifespan_context
    return await app_ctx.api_get(path, {"from": from_year, "to": to_year})
