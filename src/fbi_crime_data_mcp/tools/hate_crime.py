"""Hate crime data tool."""

from fastmcp import Context

from ..api_client import AppContext
from ..constants import BIAS_CODES, US_STATES
from ..server import mcp


@mcp.tool()
async def get_hate_crime_data(
    level: str,
    from_date: str,
    to_date: str,
    bias: str | None = None,
    data_type: str = "counts",
    state: str | None = None,
    ori: str | None = None,
    ctx: Context | None = None,
) -> str:
    """Get hate crime statistics, optionally filtered by bias motivation. Returns incident counts, victim types, offense types, offender demographics, and locations.

    Args:
        level: Geographic level — "national", "state", or "agency"
        from_date: Start date in mm-yyyy format (e.g., "01-2020")
        to_date: End date in mm-yyyy format (e.g., "12-2022")
        bias: Bias code to filter by (e.g., "12" for Anti-Black, "21" for Anti-Jewish, "24" for Anti-Islamic). Use get_reference_data with offense_type="hate-crime" for full list. If omitted, returns all biases.
        data_type: "counts" for time series or "totals" for aggregate data (default: "counts")
        state: Two-letter state abbreviation (required when level is "state")
        ori: Agency ORI code (required when level is "agency")
    """
    if level not in ("national", "state", "agency"):
        return "Invalid level. Must be 'national', 'state', or 'agency'."
    if data_type not in ("counts", "totals"):
        return "Invalid data_type. Must be 'counts' or 'totals'."
    if level == "state" and not state:
        return "Parameter 'state' is required when level is 'state'."
    if level == "agency" and not ori:
        return "Parameter 'ori' is required when level is 'agency'."
    if bias and bias not in BIAS_CODES:
        return f"Invalid bias code '{bias}'. Use get_reference_data(data_type='offenses', offense_type='hate-crime') to see valid codes."
    if state and state.upper() not in US_STATES:
        return f"Invalid state '{state}'."

    if level == "state":
        path = f"/hate-crime/state/{state.upper()}"
    elif level == "agency":
        path = f"/hate-crime/agency/{ori}"
    else:
        path = "/hate-crime/national"

    if bias:
        path += f"/{bias}"

    app_ctx: AppContext = ctx.lifespan_context
    return await app_ctx.api_get(path, {"type": data_type, "from": from_date, "to": to_date})
