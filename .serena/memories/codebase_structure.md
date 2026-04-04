# Codebase Structure

```
src/fbi_crime_data_mcp/
├── __init__.py
├── server.py              # FastMCP entry point, middleware config, tool imports
├── api_client.py          # httpx client, RateLimiter, AppContext, lifespan, stats persistence
├── response_utils.py      # process_crime_response(), filter_agencies_by_name(), paginate_response()
├── validators.py          # All shared validators (level, dates, state, ORI, offense, date ordering)
├── constants.py           # Enums: SRS_OFFENSES, NIBRS_OFFENSES, ARREST_OFFENSES, BIAS_CODES, etc.
├── spillover.py           # ResponseSpilloverMiddleware (oversized responses → disk)
└── tools/
    ├── __init__.py
    ├── agency.py           # lookup_agency (by_state, by_ori, by_district)
    ├── arrests.py          # get_arrest_data (offense + demographics)
    ├── cache.py            # manage_cache (status, clear, clear_expired)
    ├── employment.py       # get_police_employment (national/state/agency/region, yyyy dates)
    ├── hate_crime.py       # get_hate_crime_data (bias filtering)
    ├── homicide.py         # get_expanded_homicide_data (SHR)
    ├── leoka.py            # get_leoka_data (officers killed/assaulted, year+month)
    ├── lesdc.py            # get_lesdc_data (law enforcement suicide, year+chart_type)
    ├── nibrs.py            # get_nibrs_data (70+ offense types)
    ├── nibrs_estimation.py # get_nibrs_estimation (national estimates, multiple levels)
    ├── property_data.py    # get_expanded_property_data (stolen/recovered values)
    ├── reference.py        # get_reference_data (states, offenses, biases, dates)
    ├── spillover_reader.py # read_spillover (retrieve spilled files with pagination)
    ├── summarized.py       # get_summarized_crime_data (SRS, no type param)
    ├── trends.py           # get_crime_trends (national, yyyy dates, optional)
    └── use_of_force.py     # get_use_of_force_data (summary/questions/reports)

tests/
├── conftest.py             # Shared fixtures: FakeAppContext, FakeContext
├── test_api_client.py      # RateLimiter, AppContext, api_get, error handling
├── test_response_utils.py  # Aggregation, filtering, pagination
├── test_spillover.py       # SpilloverMiddleware
├── test_validators.py      # All validator functions + date ordering
└── test_tools/
    ├── test_agency.py
    ├── test_arrests.py
    ├── test_cache.py
    ├── test_nibrs.py
    ├── test_nibrs_estimation.py
    ├── test_remaining.py   # trends, employment, hate_crime, homicide, property, leoka, lesdc, reference, uof
    ├── test_spillover_reader.py
    └── test_summarized.py
```
