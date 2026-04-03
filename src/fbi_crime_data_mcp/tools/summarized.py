"""Summarized (SRS) crime data tool."""

from fastmcp import Context

from ..api_client import AppContext
from ..constants import SRS_OFFENSES, US_STATES
from ..server import mcp

_offense_list = ", ".join(f"{k} ({v})" for k, v in SRS_OFFENSES.items())


@mcp.tool()
async def get_summarized_crime_data(
    offense: str,
    level: str,
    from_date: str,
    to_date: str,
    state: str | None = None,
    ori: str | None = None,
    ctx: Context | None = None,
) -> str:
    """Get summarized (SRS) crime data including offense rates, actuals, clearances, and population coverage.

    Args:
        offense: SRS offense code. Valid values: {offenses}
        level: Geographic level — "national", "state", or "agency"
        from_date: Start date in mm-yyyy format (e.g., "01-2020")
        to_date: End date in mm-yyyy format (e.g., "12-2022")
        state: Two-letter state abbreviation (required when level is "state")
        ori: Agency ORI code (required when level is "agency")
    """.format(offenses=_offense_list)
    if offense not in SRS_OFFENSES:
        return f"Invalid offense code '{offense}'. Valid codes: {_offense_list}"
    if level not in ("national", "state", "agency"):
        return "Invalid level. Must be 'national', 'state', or 'agency'."
    if level == "state" and not state:
        return "Parameter 'state' is required when level is 'state'."
    if level == "agency" and not ori:
        return "Parameter 'ori' is required when level is 'agency'."
    if state and state.upper() not in US_STATES:
        return f"Invalid state '{state}'. Use a two-letter abbreviation (e.g., 'CA', 'NY')."

    if level == "state":
        path = f"/summarized/state/{state.upper()}/{offense}"
    elif level == "agency":
        path = f"/summarized/agency/{ori}/{offense}"
    else:
        path = f"/summarized/national/{offense}"

    app_ctx: AppContext = ctx.lifespan_context
    return await app_ctx.api_get(path, {"from": from_date, "to": to_date})
