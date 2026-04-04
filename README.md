# FBI Crime Data MCP Server

An MCP (Model Context Protocol) server that provides access to the [FBI's Crime Data Explorer](https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/home) [API](https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/docApi).

Query crime statistics, arrest data, hate crimes, NIBRS incidents, law enforcement employment, and more — directly from any MCP-compatible client.

Created for data journalists, researchers, and anyone interested in exploring US crime data with the power of language models. Initially created for use by the [Policy Analyst Agent](https://github.com/dathere/qsv/blob/master/.claude/skills/agents/policy-analyst.md) of the [qsv Claude Cowork plugin](https://github.com/dathere/qsv?tab=readme-ov-file#qsv-blazing-fast-data-wrangling-toolkit).

## Features

- **16 tools** covering a wide range of crime data topics
  - Crime trends and Summary Reporting System (SRS) crime data
  - National Incident Based Reporting System (NIBRS) incident-based data and national estimates
  - Arrest statistics with demographic breakdowns
  - Hate crime incidents by bias motivation
  - Expanded homicide and property crime details
  - Police employment, Law Enforcement Officers Killed and Assaulted (LEOKA), Law Enforcement Suicide Data Collection (LESDC), and use of force
  - Agency lookup, reference data, cache management, and spillover reading
- **Three query levels** — national, state, and agency — with automatic parameter validation
- **Smart yearly aggregation** — monthly API data is automatically rolled up into yearly totals (sums for counts, averages for rates, last value for population), with an option for monthly granularity
- **Tiered disk-backed caching** — 90-day time-to-live (TTL) for stable data (trends, reference, summaries) and 30-day TTL for dynamic data (incidents, arrests, agency lookups)
- **Spillover handling** — responses exceeding 128K characters are saved to disk with a preview returned, so large queries are never silently truncated
- **Input validation** — date format/ordering checks, offense and bias code validation, and level-based parameter requirements with clear error messages
- **Sliding-window rate limiting** — 1,000 requests/hour with transparent wait-time feedback
- **Reference tools** for agency lookups (by state, Originating Agency Identifier (ORI), or district with name filtering) and code translations

## Quick Start

1. **Get a free API key** from [api.data.gov](https://api.data.gov/signup/)

2. **Run with Claude Desktop** — add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "fbi-crime-data": {
      "command": "uvx",
      "args": ["fbi-crime-data-mcp"],
      "env": {
        "FBI_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

3. **Or run directly:**

```bash
FBI_API_KEY=your-key uvx fbi-crime-data-mcp
```

## Available Tools (16)

### Core Crime Data
| Tool | Description |
|------|-------------|
| [`get_summarized_crime_data`](src/fbi_crime_data_mcp/tools/summarized.py) | SRS crime data — rates, actuals, clearances for violent crime, property crime, homicide, rape, robbery, assault, burglary, larceny, motor vehicle theft, arson |
| [`get_nibrs_data`](src/fbi_crime_data_mcp/tools/nibrs.py) | NIBRS incident-based data for 70+ offense types |
| [`get_arrest_data`](src/fbi_crime_data_mcp/tools/arrests.py) | Arrest statistics by offense with optional demographic breakdowns (sex, race) |
| [`get_crime_trends`](src/fbi_crime_data_mcp/tools/trends.py) | National crime trend percent changes across 10 crime types |
| [`get_nibrs_estimation`](src/fbi_crime_data_mcp/tools/nibrs_estimation.py) | NIBRS national estimates by state, region, agency type, or population size |

### Specialized Crime Data
| Tool | Description |
|------|-------------|
| [`get_hate_crime_data`](src/fbi_crime_data_mcp/tools/hate_crime.py) | Hate crime incidents by bias motivation (30+ categories) |
| [`get_expanded_homicide_data`](src/fbi_crime_data_mcp/tools/homicide.py) | Supplementary Homicide Reports — victim/offender demographics, weapons, circumstances |
| [`get_expanded_property_data`](src/fbi_crime_data_mcp/tools/property_data.py) | Expanded property crime details — stolen/recovered values for burglary, larceny, motor vehicle theft (MVT), robbery |

### Law Enforcement Data
| Tool | Description |
|------|-------------|
| [`get_police_employment`](src/fbi_crime_data_mcp/tools/employment.py) | Officer and civilian employee counts by gender, rates per 1,000 population |
| [`get_leoka_data`](src/fbi_crime_data_mcp/tools/leoka.py) | Officers killed and assaulted — weapons, circumstances, demographics |
| [`get_lesdc_data`](src/fbi_crime_data_mcp/tools/lesdc.py) | Law enforcement suicide data — demographics, race, duty status, and more |
| [`get_use_of_force_data`](src/fbi_crime_data_mcp/tools/use_of_force.py) | Use of force incidents resulting in death, serious injury, or firearm discharge |

### Reference & Lookup
| Tool | Description |
|------|-------------|
| [`lookup_agency`](src/fbi_crime_data_mcp/tools/agency.py) | Find law enforcement agencies by state, ORI code, or judicial district |
| [`get_reference_data`](src/fbi_crime_data_mcp/tools/reference.py) | State lists, offense/bias code lookups, data refresh dates |
| [`manage_cache`](src/fbi_crime_data_mcp/tools/cache.py) | View cache stats, clear all entries, or clear only expired entries |
| [`read_spillover`](src/fbi_crime_data_mcp/tools/spillover_reader.py) | Read spillover files saved when tool responses exceed the size limit |

## Large Responses

When a tool response exceeds 128,000 characters, the full result is saved to `~/.cache/fbi-crime-data-mcp/spillover/` and a truncated preview is returned with the file path. To avoid this, narrow your query (shorter date range, specific state/agency).

## Data Sources

All data comes from the FBI's [Crime Data Explorer](https://cde.ucr.cjis.gov/) API, which provides Uniform Crime Reporting (UCR) data including both the Summary Reporting System (SRS) and the National Incident-Based Reporting System (NIBRS).

## API Rate Limits

- **Registered key**: 1,000 requests per hour (rolling window)
- **DEMO_KEY**: 30 requests per IP per hour

The server includes a built-in rate limiter (1,000 req/hr). The DEMO_KEY limit is enforced API-side.

## Development

```bash
# Install dependencies
uv sync

# Run the server locally
FBI_API_KEY=your-key uv run fbi-crime-data-mcp

# Run tests
uv run pytest
```

## License

MIT
