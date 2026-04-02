"""LESDC (Law Enforcement Suicide Data Collection) tool."""

from mcp.server.fastmcp import Context

from ..api_client import AppContext
from ..constants import LESDC_CHART_TYPES
from ..server import mcp

_chart_list = ", ".join(LESDC_CHART_TYPES.keys())


@mcp.tool()
async def get_lesdc_data(
    year: int,
    chart_type: str,
    ctx: Context | None = None,
) -> str:
    """Get law enforcement suicide data with breakdowns by demographics, race, location, duty status, and more.

    Args:
        year: Year for the data (e.g., 2022)
        chart_type: Chart/breakdown type — {charts}
    """.format(charts=_chart_list)
    if chart_type not in LESDC_CHART_TYPES:
        return f"Invalid chart_type '{chart_type}'. Valid values: {_chart_list}"

    app_ctx: AppContext = ctx.request_context.lifespan_context
    return await app_ctx.api_get("/lesdc", {"year": str(year), "chartType": chart_type})
