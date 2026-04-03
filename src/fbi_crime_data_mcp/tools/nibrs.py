"""NIBRS (National Incident-Based Reporting System) data tool."""

from fastmcp import Context

from ..api_client import AppContext
from ..constants import NIBRS_OFFENSES, US_STATES
from ..response_utils import process_crime_response
from ..server import mcp


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
        aggregate: Aggregation level — "yearly" (default, sums monthly into yearly) or "monthly" (raw monthly data). Only applies when data_type is "counts".
    """
    if data_type == "counts" and aggregate not in ("yearly", "monthly"):
        return "Invalid aggregate. Must be 'yearly' or 'monthly'."
    if offense not in NIBRS_OFFENSES:
        return f"Invalid NIBRS offense code '{offense}'. Common codes: 09A (Murder), 11A (Rape), 120 (Robbery), 13A (Aggravated Assault), 220 (Burglary), 23H (All Other Larceny), 240 (Motor Vehicle Theft), 200 (Arson), 35A (Drug/Narcotic Violations), 520 (Weapon Law Violations)."
    if level not in ("national", "state", "agency"):
        return "Invalid level. Must be 'national', 'state', or 'agency'."
    if data_type not in ("counts", "totals"):
        return "Invalid data_type. Must be 'counts' or 'totals'."
    if level == "state" and not state:
        return "Parameter 'state' is required when level is 'state'."
    if level == "agency" and not ori:
        return "Parameter 'ori' is required when level is 'agency'."
    if state and state.upper() not in US_STATES:
        return f"Invalid state '{state}'. Use a two-letter abbreviation."

    if level == "state":
        path = f"/nibrs/state/{state.upper()}/{offense}"
    elif level == "agency":
        path = f"/nibrs/agency/{ori}/{offense}"
    else:
        path = f"/nibrs/national/{offense}"

    app_ctx: AppContext = ctx.lifespan_context
    raw = await app_ctx.api_get(path, {"type": data_type, "from": from_date, "to": to_date})
    return process_crime_response(raw, aggregate=aggregate if data_type == "counts" else "monthly")
