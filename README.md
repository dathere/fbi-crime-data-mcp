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

## Available Tools (14)

### Core Crime Data
| Tool | Description |
|------|-------------|
| `get_summarized_crime_data` | SRS crime data — rates, actuals, clearances for violent crime, property crime, homicide, rape, robbery, assault, burglary, larceny, motor vehicle theft, arson |
| `get_nibrs_data` | NIBRS incident-based data for 70+ offense types |
| `get_arrest_data` | Arrest statistics by offense with optional demographic breakdowns (sex, race) |
| `get_crime_trends` | National crime trend percent changes across 10 crime types |
| `get_nibrs_estimation` | NIBRS national estimates by state, region, agency type, or population size |

### Specialized Crime Data
| Tool | Description |
|------|-------------|
| `get_hate_crime_data` | Hate crime incidents by bias motivation (30+ categories) |
| `get_expanded_homicide_data` | Supplementary Homicide Reports — victim/offender demographics, weapons, circumstances |
| `get_expanded_property_data` | Expanded property crime details — stolen/recovered values for burglary, larceny, MVT, robbery |

### Law Enforcement Data
| Tool | Description |
|------|-------------|
| `get_police_employment` | Officer and civilian employee counts by gender, rates per 1,000 population |
| `get_leoka_data` | Officers killed and assaulted — weapons, circumstances, demographics |
| `get_lesdc_data` | Law enforcement suicide data — demographics, race, duty status, and more |
| `get_use_of_force_data` | Use of force incidents resulting in death, serious injury, or firearm discharge |

### Reference & Lookup
| Tool | Description |
|------|-------------|
| `lookup_agency` | Find law enforcement agencies by state, ORI code, or judicial district |
| `get_reference_data` | State lists, offense/bias code lookups, data refresh dates |

## Data Sources

All data comes from the FBI's [Crime Data Explorer](https://cde.ucr.cjis.gov/) API, which provides Uniform Crime Reporting (UCR) data including both the Summary Reporting System (SRS) and the National Incident-Based Reporting System (NIBRS).

## API Rate Limits

- **Registered key**: 1,000 requests per hour (rolling window)
- **DEMO_KEY**: 30 requests per IP per hour

The server includes built-in rate limiting to stay within these bounds.

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
