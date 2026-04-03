# FBI Crime Data MCP Server

An MCP (Model Context Protocol) server that provides access to the FBI's Crime Data Explorer API. Query crime statistics, arrest data, hate crimes, NIBRS incidents, law enforcement employment, and more — directly from Claude or any MCP-compatible client.

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

## Available Tools (15)

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
| [`get_expanded_property_data`](src/fbi_crime_data_mcp/tools/property_data.py) | Expanded property crime details — stolen/recovered values for burglary, larceny, MVT, robbery |

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
