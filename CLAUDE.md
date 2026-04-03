# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FBI Crime Data MCP Server — a Python MCP server providing 14 tools for querying the FBI Crime Data Explorer API (`https://api.usa.gov/crime/fbi/cde`). Built with `fastmcp` (v3.2+) and `httpx`, deployable via `uvx fbi-crime-data-mcp`.

## Build & Run

```bash
uv sync                                           # install deps
FBI_API_KEY=xxx uv run fbi-crime-data-mcp          # run server (stdio)
uv run pytest                                      # run tests
FBI_API_KEY=xxx uv run pytest -m integration        # integration tests (hits real API)
```

## Architecture

- `src/fbi_crime_data_mcp/server.py` — FastMCP server entry point with lifespan context. Imports all tool modules. Configures two `ResponseCachingMiddleware` instances with `FileTreeStore` for tiered disk-backed caching (90-day TTL for summaries/trends/reference; 30-day TTL for agency/incident data). Cache persists to `~/.cache/fbi-crime-data-mcp/`.
- `src/fbi_crime_data_mcp/api_client.py` — Shared `httpx.AsyncClient` wrapper with sliding-window rate limiter (1000 req/hr). `AppContext` dataclass is the lifespan context available to all tools via `ctx.lifespan_context`.
- `src/fbi_crime_data_mcp/constants.py` — All validation enums: SRS offenses, NIBRS codes, arrest offenses, bias codes, LESDC chart types, states.
- `src/fbi_crime_data_mcp/tools/` — One module per tool, each registers via `@mcp.tool()` decorator on the shared `mcp` instance imported from `server.py`.

## Key Patterns

- Tools return strings (JSON or error messages), never raise exceptions to the MCP client.
- Date format varies by endpoint: `mm-yyyy` (most crime data), `yyyy` (PE, trends), or `year=YYYY` param (LEOKA, LESDC, UoF).
- Most tools use a `level` param (national/state/agency) with conditional `state`/`ori` requirements.
- API key is passed via `FBI_API_KEY` env var, appended as query param to all requests.
