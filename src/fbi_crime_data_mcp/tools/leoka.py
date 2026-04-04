"""LEOKA (Law Enforcement Officers Killed and Assaulted) data tool."""

from fastmcp import Context

from ..api_client import AppContext
from ..server import mcp
from ..validators import validate_year_int


@mcp.tool()
async def get_leoka_data(
    report_type: str,
    year: int,
    month: int | None = None,
    ctx: Context | None = None,
) -> str:
    """Get LEOKA data on law enforcement officers killed and assaulted, including weapons used, circumstances, officer demographics, and offender demographics.

    Args:
        report_type: "monthly" for a specific month or "ytd" for year-to-date summary
        year: Year for the data (e.g., 2022)
        month: Month number 1-12 (January=1, December=12). Required when report_type is "monthly".
    """
    if report_type not in ("monthly", "ytd"):
        return "Invalid report_type. Must be 'monthly' or 'ytd'."
    err = validate_year_int(year)
    if err:
        return err
    if report_type == "monthly" and month is None:
        return "Parameter 'month' (1-12) is required when report_type is 'monthly'."
    if report_type == "monthly" and month is not None and not (1 <= month <= 12):
        return "Parameter 'month' must be between 1 (January) and 12 (December)."

    params: dict[str, str] = {"year": str(year)}
    if report_type == "monthly":
        # FBI API uses 0-indexed months (0=January, 11=December)
        params["month"] = str(month - 1)
        path = "/leoka/monthly"
    else:
        path = "/leoka/ytd"

    app_ctx: AppContext = ctx.lifespan_context
    return await app_ctx.api_get(path, params)
