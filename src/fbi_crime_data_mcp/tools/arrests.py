"""Arrest data tool."""

from fastmcp import Context

from ..api_client import AppContext
from ..constants import ARREST_OFFENSES, US_STATES
from ..response_utils import process_crime_response
from ..server import mcp

ARREST_CATEGORIES = {"male", "female", "race", "sex"}


@mcp.tool()
async def get_arrest_data(
    offense: str,
    level: str,
    data_type: str,
    from_date: str,
    to_date: str,
    state: str | None = None,
    ori: str | None = None,
    category: str | None = None,
    aggregate: str = "yearly",
    ctx: Context | None = None,
) -> str:
    """Get arrest statistics by offense, optionally broken down by demographics.

    Args:
        offense: Arrest offense code (e.g., "all", "11" for murder, "30" for robbery, "150" for drug abuse). Use get_reference_data with data_type="offenses" and offense_type="arrest" for full list.
        level: Geographic level — "national", "state", or "agency"
        data_type: "counts" for time series or "totals" for demographic breakdowns
        from_date: Start date in mm-yyyy format (e.g., "01-2020")
        to_date: End date in mm-yyyy format (e.g., "12-2022")
        state: Two-letter state abbreviation (required when level is "state")
        ori: Agency ORI code (required when level is "agency")
        category: Optional demographic breakdown — "male", "female", "race", or "sex"
        aggregate: Aggregation level — "yearly" (default, sums monthly into yearly) or "monthly" (raw monthly data). Only applies when data_type is "counts".
    """
    if aggregate not in ("yearly", "monthly"):
        return "Invalid aggregate. Must be 'yearly' or 'monthly'."
    if offense not in ARREST_OFFENSES:
        return f"Invalid arrest offense code '{offense}'. Common codes: all (All), 11 (Murder), 30 (Robbery), 50 (Assault), 60 (Burglary), 70 (Larceny), 150 (Drug Abuse), 260 (DUI)."
    if level not in ("national", "state", "agency"):
        return "Invalid level. Must be 'national', 'state', or 'agency'."
    if data_type not in ("counts", "totals"):
        return "Invalid data_type. Must be 'counts' or 'totals'."
    if level == "state" and not state:
        return "Parameter 'state' is required when level is 'state'."
    if level == "agency" and not ori:
        return "Parameter 'ori' is required when level is 'agency'."
    if category and category not in ARREST_CATEGORIES:
        return f"Invalid category '{category}'. Must be one of: male, female, race, sex."
    if state and state.upper() not in US_STATES:
        return f"Invalid state '{state}'. Use a two-letter abbreviation."

    if level == "state":
        path = f"/arrest/state/{state.upper()}/{offense}"
    elif level == "agency":
        path = f"/arrest/agency/{ori}/{offense}"
    else:
        path = f"/arrest/national/{offense}"

    if category:
        path += f"/{category}"

    app_ctx: AppContext = ctx.lifespan_context
    raw = await app_ctx.api_get(path, {"type": data_type, "from": from_date, "to": to_date})
    return process_crime_response(raw, aggregate=aggregate if data_type == "counts" else "monthly")
