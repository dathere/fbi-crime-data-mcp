"""Crime trends tool."""

from fastmcp import Context

from ..api_client import AppContext
from ..server import mcp


@mcp.tool()
async def get_crime_trends(
    from_year: str | None = None,
    to_year: str | None = None,
    ctx: Context | None = None,
) -> str:
    """Get national crime trend data showing percent changes across 10 crime types (murder, rape, robbery, aggravated assault, violent crime, burglary, larceny, motor vehicle theft, arson, property crime).

    Args:
        from_year: Start year in yyyy format (e.g., "2015"). Optional.
        to_year: End year in yyyy format (e.g., "2022"). Optional.
    """
    params: dict[str, str] = {}
    if from_year:
        params["from"] = from_year
    if to_year:
        params["to"] = to_year

    app_ctx: AppContext = ctx.lifespan_context
    return await app_ctx.api_get("/trends/national", params)
