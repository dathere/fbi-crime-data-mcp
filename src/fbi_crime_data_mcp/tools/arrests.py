"""Arrest data tool."""

from fastmcp import Context

from ..api_client import AppContext
from ..constants import ARREST_OFFENSES
from ..response_utils import process_crime_response
from ..server import mcp
from ..validators import (
    validate_aggregate,
    validate_data_type,
    validate_level,
    validate_mm_yyyy,
    validate_offense,
    validate_ori_required,
    validate_state,
    validate_state_required,
)

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
        aggregate: Aggregation level — "yearly" (default, sums monthly into yearly) or "monthly" (monthly granularity). Only applies when data_type is "counts".
    """
    for err in (
        validate_aggregate(data_type, aggregate),
        validate_offense(offense, ARREST_OFFENSES, "arrest offense code"),
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

    if category and category not in ARREST_CATEGORIES:
        return f"Invalid category '{category}'. Must be one of: male, female, race, sex."

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
