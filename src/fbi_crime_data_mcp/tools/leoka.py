"""LEOKA (Law Enforcement Officers Killed and Assaulted) data tool."""

from fastmcp import Context

from ..api_client import AppContext
from ..server import mcp


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
        month: Month number 0-11 (January=0). Required when report_type is "monthly".
    """
    if report_type not in ("monthly", "ytd"):
        return "Invalid report_type. Must be 'monthly' or 'ytd'."
    if report_type == "monthly" and month is None:
        return "Parameter 'month' (0-11) is required when report_type is 'monthly'."
    if report_type == "monthly" and month is not None and not (0 <= month <= 11):
        return "Parameter 'month' must be between 0 (January) and 11 (December)."

    params: dict[str, str] = {"year": str(year)}
    if report_type == "monthly":
        params["month"] = str(month)
        path = "/leoka/monthly"
    else:
        path = "/leoka/ytd"

    app_ctx: AppContext = ctx.lifespan_context
    return await app_ctx.api_get(path, params)
