"""Summarized (SRS) crime data tool."""

from fastmcp import Context

from ..api_client import AppContext
from ..constants import SRS_OFFENSES
from ..response_utils import process_crime_response
from ..server import mcp
from ..validators import build_geo_path, validate_crime_data_params

_offense_list = ", ".join(f"{k} ({v})" for k, v in SRS_OFFENSES.items())


@mcp.tool()
async def get_summarized_crime_data(
    offense: str,
    level: str,
    from_date: str,
    to_date: str,
    state: str | None = None,
    ori: str | None = None,
    aggregate: str = "yearly",
    ctx: Context | None = None,
) -> str:
    """Get summarized (SRS) crime data including offense rates, actuals, clearances, and population coverage.

    Args:
        offense: SRS offense code (e.g., "V" for Violent Crime, "P" for Property Crime, "HOM", "RPE", "ROB", "ASS", "BUR", "LAR", "MVT", "ARS"). Use get_reference_data for full list.
        level: Geographic level — "national", "state", or "agency"
        from_date: Start date in mm-yyyy format (e.g., "01-2020")
        to_date: End date in mm-yyyy format (e.g., "12-2022")
        state: Two-letter state abbreviation (required when level is "state")
        ori: Agency ORI code (required when level is "agency")
        aggregate: Aggregation level — "yearly" (default, sums monthly into yearly) or "monthly" (monthly granularity)
    """

    err = validate_crime_data_params(
        level=level,
        from_date=from_date,
        to_date=to_date,
        state=state,
        ori=ori,
        data_type="counts",
        aggregate=aggregate,
        offense=offense,
        offense_codes=SRS_OFFENSES,
        offense_label="offense code",
        offense_hint=f"Valid codes: {_offense_list}",
    )
    if err:
        return err

    path = build_geo_path("/summarized", level, state=state, ori=ori, suffix=offense)

    app_ctx: AppContext = ctx.lifespan_context
    # SRS/summarized endpoint always returns both counts and rates together;
    # it does not accept a "type" query parameter unlike NIBRS/arrests endpoints.
    raw = await app_ctx.api_get(path, {"from": from_date, "to": to_date})
    return process_crime_response(raw, aggregate=aggregate)
