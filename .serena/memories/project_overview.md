# FBI Crime Data MCP Server — Project Overview

## Purpose
An MCP (Model Context Protocol) server providing 16 tools for querying the FBI Crime Data Explorer API (`https://api.usa.gov/crime/fbi/cde`). Built for use with AI assistants via the MCP protocol, deployable via `uvx fbi-crime-data-mcp`.

## Tech Stack
- **Language:** Python 3.11+
- **MCP Framework:** FastMCP v3.2+
- **HTTP Client:** httpx (async)
- **Package Manager:** uv (with hatch build backend)
- **Testing:** pytest + pytest-asyncio + respx (HTTP mocking)
- **Linting/Formatting:** ruff
- **CI:** GitHub Actions (Python 3.11/3.12/3.13 matrix)

## Architecture
- `src/fbi_crime_data_mcp/server.py` — FastMCP server entry point, middleware setup (tiered caching + spillover), tool imports
- `src/fbi_crime_data_mcp/api_client.py` — httpx AsyncClient wrapper, sliding-window rate limiter (1000 req/hr), AppContext dataclass, cache stats persistence
- `src/fbi_crime_data_mcp/response_utils.py` — Response post-processing: trimming, monthly-to-yearly aggregation, agency filtering, pagination
- `src/fbi_crime_data_mcp/validators.py` — Shared validation helpers (level, dates, state, ORI, offense codes, date ordering)
- `src/fbi_crime_data_mcp/constants.py` — All validation enums (SRS/NIBRS/arrest offenses, bias codes, states, LESDC chart types), path constants
- `src/fbi_crime_data_mcp/spillover.py` — ResponseSpilloverMiddleware: saves oversized responses (>128K chars) to disk with content-addressed filenames
- `src/fbi_crime_data_mcp/tools/` — One module per tool (16 total), each registers via `@mcp.tool()` decorator

## Caching
Two `ResponseCachingMiddleware` instances with `FileTreeStore`:
- 90-day TTL: summarized, trends, reference data
- 30-day TTL: agency, incident-level data (NIBRS, arrests, etc.)
- Persists to `~/.cache/fbi-crime-data-mcp/`

## API Key
Required via `FBI_API_KEY` environment variable. Free key from https://api.data.gov/signup/
