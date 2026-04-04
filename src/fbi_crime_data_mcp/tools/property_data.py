"""Expanded property crime (supplemental) data tool."""

from fastmcp import Context

from ..api_client import AppContext
from ..constants import SUPPLEMENTAL_OFFENSES
from ..response_utils import process_crime_response
from ..server import mcp
from ..validators import validate_crime_data_params

_offense_list = ", ".join(f"{k} ({v})" for k, v in SUPPLEMENTAL_OFFENSES.items())


@mcp.tool()
async def get_expanded_property_data(
    offense: str,
    level: str,
    data_type: str,
    from_date: str,
    to_date: str,
    state: str | None = None,
    ori: str | None = None,
    aggregate: str = "yearly",
    ctx: Context | None = None,
) -> str:
    """Get expanded property crime data with details on stolen/recovered property values.

    Args:
        offense: Property offense code (e.g., "burglary", "larceny", "motor-vehicle-theft", "arson"). Use get_reference_data for full list.
        level: Geographic level — "national", "state", or "agency"
        data_type: "counts" for time series or "totals" for property value breakdowns
        from_date: Start date in mm-yyyy format (e.g., "01-2020")
        to_date: End date in mm-yyyy format (e.g., "12-2022")
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
        offense_codes=SUPPLEMENTAL_OFFENSES,
        offense_label="offense code",
        offense_hint=f"Valid codes: {_offense_list}",
    )
    if err:
        return err

    if level == "state":
        path = f"/supplemental/state/{state.upper()}/{offense}"
    elif level == "agency":
        path = f"/supplemental/agency/{ori}/{offense}"
    else:
        path = f"/supplemental/national/{offense}"

    app_ctx: AppContext = ctx.lifespan_context
    raw = await app_ctx.api_get(path, {"type": data_type, "from": from_date, "to": to_date})
    return process_crime_response(raw, aggregate=aggregate if data_type == "counts" else "monthly")
