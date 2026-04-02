"""FBI Crime Data Explorer MCP Server."""

from mcp.server.fastmcp import FastMCP

from .api_client import app_lifespan

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
    employment,
    hate_crime,
    homicide,
    leoka,
    lesdc,
    nibrs,
    nibrs_estimation,
    property_data,
    reference,
    summarized,
    trends,
    use_of_force,
)


def main():
    """Entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
