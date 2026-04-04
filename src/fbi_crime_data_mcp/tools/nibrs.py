"""NIBRS (National Incident-Based Reporting System) data tool."""

from fastmcp import Context

from ..api_client import AppContext
from ..constants import NIBRS_OFFENSES
from ..response_utils import process_crime_response
from ..server import mcp
from ..validators import build_geo_path, effective_aggregate, validate_crime_data_params


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
        offense=offense,
        offense_codes=NIBRS_OFFENSES,
        offense_label="NIBRS offense code",
        offense_hint="Common codes: 09A (Murder), 11A (Rape), 120 (Robbery), 13A (Aggravated Assault), 220 (Burglary), 23H (All Other Larceny), 240 (Motor Vehicle Theft), 200 (Arson), 35A (Drug/Narcotic Violations), 520 (Weapon Law Violations).",
    )
    if err:
        return err

    path = build_geo_path("/nibrs", level, state=state, ori=ori, suffix=offense)

    app_ctx: AppContext = ctx.lifespan_context
    raw = await app_ctx.api_get(path, {"type": data_type, "from": from_date, "to": to_date})
    return process_crime_response(raw, aggregate=effective_aggregate(data_type, aggregate))
