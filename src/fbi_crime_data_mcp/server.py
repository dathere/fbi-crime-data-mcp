"""FBI Crime Data Explorer MCP Server."""

from fastmcp import FastMCP
from fastmcp.server.middleware.caching import (
    CallToolSettings,
    ResponseCachingMiddleware,
)
from key_value.aio.stores.filetree import (
    FileTreeStore,
    FileTreeV1CollectionSanitizationStrategy,
    FileTreeV1KeySanitizationStrategy,
)

from .api_client import app_lifespan
from .constants import CACHE_DIR
from .spillover import ResponseSpilloverMiddleware

mcp = FastMCP(
    "FBI Crime Data Explorer",
    instructions=(
        "Query FBI crime statistics from the Crime Data Explorer API. "
        "Data includes crime trends, NIBRS incidents, arrests, hate crimes, "
        "expanded homicide/property data, police employment, LEOKA, LESDC, "
        "and use of force. Use get_reference_data to look up valid offense codes, "
        "bias codes, and state abbreviations. Most date parameters use mm-yyyy format "
        "(e.g., '01-2020'), except police employment and trends which use yyyy format."
    ),
    lifespan=app_lifespan,
)

# Import tool modules to register them with the server
from .tools import (  # noqa: E402, F401
    agency,
    arrests,
    cache,
    employment,
    hate_crime,
    homicide,
    leoka,
    lesdc,
    nibrs,
    nibrs_estimation,
    property_data,
    reference,
    spillover_reader,
    summarized,
    trends,
    use_of_force,
)

# --- Response caching with tiered TTLs ---
_cache_dir = CACHE_DIR
_cache_dir.mkdir(parents=True, exist_ok=True)

_cache_store = FileTreeStore(
    data_directory=_cache_dir,
    key_sanitization_strategy=FileTreeV1KeySanitizationStrategy(_cache_dir),
    collection_sanitization_strategy=FileTreeV1CollectionSanitizationStrategy(_cache_dir),
)

_TTL_90_DAYS = 90 * 24 * 3600
_TTL_30_DAYS = 30 * 24 * 3600

# Long TTL (90 days) — summaries, trends, reference data (rarely changes)
mcp.add_middleware(
    ResponseCachingMiddleware(
        cache_storage=_cache_store,
        call_tool_settings=CallToolSettings(
            ttl=_TTL_90_DAYS,
            included_tools=[
                "get_summarized_crime_data",
                "get_crime_trends",
                "get_reference_data",
                "get_nibrs_estimation",
            ],
        ),
    )
)

# Short TTL (30 days) — agency lookups, granular incident data
mcp.add_middleware(
    ResponseCachingMiddleware(
        cache_storage=_cache_store,
        call_tool_settings=CallToolSettings(
            ttl=_TTL_30_DAYS,
            included_tools=[
                "lookup_agency",
                "get_nibrs_data",
                "get_arrest_data",
                "get_hate_crime_data",
                "get_expanded_homicide_data",
                "get_expanded_property_data",
                "get_police_employment",
                "get_leoka_data",
                "get_lesdc_data",
                "get_use_of_force_data",
            ],
        ),
    )
)

# Spillover: save oversized tool responses to disk instead of truncating
mcp.add_middleware(ResponseSpilloverMiddleware())


def main():
    """Entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
