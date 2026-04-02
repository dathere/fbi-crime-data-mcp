"""Reference and metadata tools."""

from mcp.server.fastmcp import Context

from ..api_client import AppContext
from ..server import mcp


@mcp.tool()
async def get_reference_data(
    data_type: str,
    offense_type: str | None = None,
    ctx: Context | None = None,
) -> str:
    """Get reference data: state lists, offense/bias code lookups, data properties, or data refresh dates.

    Args:
        data_type: Type of reference data — "states" (list of states/territories), "offenses" (offense or bias code lookup), "cde_properties" (data date ranges), or "refresh_date" (last data refresh dates)
        offense_type: Required when data_type is "offenses" — "arrest" for arrest offense codes or "hate-crime" for hate crime bias codes
    """
    if data_type not in ("states", "offenses", "cde_properties", "refresh_date"):
        return "Invalid data_type. Must be 'states', 'offenses', 'cde_properties', or 'refresh_date'."

    if data_type == "states":
        path = "/lookup/states"
        params = {}
    elif data_type == "offenses":
        if not offense_type or offense_type not in ("arrest", "hate-crime"):
            return "Parameter 'offense_type' is required and must be 'arrest' or 'hate-crime'."
        path = "/lookup/offenses"
        params = {"type": offense_type}
    elif data_type == "cde_properties":
        path = "/lookup/cde_properties"
        params = {}
    else:  # refresh_date
        path = "/refresh-date"
        params = {}

    app_ctx: AppContext = ctx.request_context.lifespan_context
    return await app_ctx.api_get(path, params)
