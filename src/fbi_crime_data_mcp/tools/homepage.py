"""CDE Homepage summary tool."""

from __future__ import annotations

import asyncio
import json

from fastmcp import Context

from ..api_client import AppContext
from ..server import mcp

# Stable content extracted from CDE homepage, verified across Wayback Machine
# snapshots from 2023-06, 2024-06, and 2026-03.  Update _stable_content_version
# when re-verified.
_STABLE_CONTENT = {
    "mission_statement": (
        "The FBI's Crime Data Explorer (CDE) aims to provide transparency, "
        "create easier access, and expand awareness of criminal, and noncriminal, "
        "law enforcement data sharing; improve accountability for law enforcement; "
        "and provide a foundation to help shape public policy in support of a "
        "safer nation. Use the CDE to discover data through visualizations, "
        "downloads in .csv format, and other large data files."
    ),
    "navigation": {
        "national_data": {
            "label": "National Data",
            "description": "Explore national crime statistics",
            "url": "https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/explorer/crime/crime-trend",
        },
        "state_agency_data": {
            "label": "State & Agency Data",
            "description": "Explore crime data by state or specific agency",
            "url": "https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/explorer/crime/state-crime",
        },
        "data_discovery_tool": {
            "label": "Data Discovery Tool",
            "description": "Search and discover available crime datasets",
            "url": "https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/downloads",
        },
        "documents_downloads": {
            "label": "Documents & Downloads",
            "description": "Download bulk data files and documentation",
            "url": "https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/docdownload",
        },
        "help_center": {
            "label": "Help Center",
            "description": "Help and support for the Crime Data Explorer",
            "url": "https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/home",
        },
    },
    "homepage_url": "https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/home",
    "_stable_content_version": "2026-04",
}


@mcp.tool()
async def get_cde_homepage_summary(ctx: Context | None = None) -> str:
    """Get a summary of the FBI Crime Data Explorer (CDE) homepage.

    Returns the CDE mission statement, navigation structure, data freshness
    (last refresh dates), available data date ranges, and the full national
    crime trends response (percent changes across 10 crime types, matching
    the trends section displayed on the CDE homepage).
    Provides orientation on what the CDE offers and how current its data is.
    """
    app_ctx: AppContext = ctx.lifespan_context

    refresh_raw, properties_raw, trends_raw = await asyncio.gather(
        app_ctx.api_get("/refresh-date"),
        app_ctx.api_get("/lookup/cde_properties"),
        app_ctx.api_get("/trends/national"),
    )

    try:
        refresh_data = json.loads(refresh_raw)
    except (json.JSONDecodeError, TypeError):
        refresh_data = refresh_raw

    try:
        properties_data = json.loads(properties_raw)
    except (json.JSONDecodeError, TypeError):
        properties_data = properties_raw

    try:
        trends_data = json.loads(trends_raw)
    except (json.JSONDecodeError, TypeError):
        trends_data = trends_raw

    summary = {
        **_STABLE_CONTENT,
        "data_refresh_dates": refresh_data,
        "data_properties": properties_data,
        "crime_trends": trends_data,
    }

    return json.dumps(summary, indent=2)
