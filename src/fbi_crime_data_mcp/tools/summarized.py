"""Summarized (SRS) crime data tool."""

from fastmcp import Context

from ..api_client import AppContext
from ..constants import SRS_OFFENSES
from ..response_utils import process_crime_response
from ..server import mcp
from ..validators import (
    validate_level,
    validate_mm_yyyy,
    validate_offense,
    validate_ori_required,
    validate_state,
    validate_state_required,
)

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
        offense: SRS offense code. Valid values: {offenses}
        level: Geographic level — "national", "state", or "agency"
        from_date: Start date in mm-yyyy format (e.g., "01-2020")
        to_date: End date in mm-yyyy format (e.g., "12-2022")
        state: Two-letter state abbreviation (required when level is "state")
        ori: Agency ORI code (required when level is "agency")
        aggregate: Aggregation level — "yearly" (default, sums monthly into yearly) or "monthly" (monthly granularity)
    """.format(offenses=_offense_list)
    if aggregate not in ("yearly", "monthly"):
        return "Invalid aggregate. Must be 'yearly' or 'monthly'."

    for err in (
        validate_offense(offense, SRS_OFFENSES, "offense code"),
        validate_level(level),
        validate_state_required(level, state),
        validate_ori_required(level, ori),
        validate_state(state),
        validate_mm_yyyy(from_date, "from_date"),
        validate_mm_yyyy(to_date, "to_date"),
    ):
        if err:
            return err

    if level == "state":
        path = f"/summarized/state/{state.upper()}/{offense}"
    elif level == "agency":
        path = f"/summarized/agency/{ori}/{offense}"
    else:
        path = f"/summarized/national/{offense}"

    app_ctx: AppContext = ctx.lifespan_context
    raw = await app_ctx.api_get(path, {"from": from_date, "to": to_date})
    return process_crime_response(raw, aggregate=aggregate)
