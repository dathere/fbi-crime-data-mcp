# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Security
- API key is now sent in the `X-Api-Key` request header instead of the `API_KEY` query parameter, so it never appears in request URLs (httpx debug logs, proxies, or error messages that echo the URL)

### Fixed
- Transient API errors (timeouts, network failures, HTTP 5xx/429, in-process rate-limit messages) are no longer cached. Tools return these as plain strings, and `ResponseCachingMiddleware` stored them for the full 30/90-day TTL, so a single blip was replayed for that argument set until the cache was cleared. New `ErrorAwareCachingMiddleware` (`caching.py`) skips writing results that start with `Error:` or `Rate limit reached`
- CI lint step now uses the `ruff` pinned in the `dev` dependency group via `uv run` instead of an unpinned `uvx ruff`, so local and CI lint results match

### Added
- Yearly aggregation now adds a top-level `_partial_years` marker (note, months covered, from/to) whenever a year has fewer than 12 months of data, so a partial-year sum or rate average is never mistaken for an annual figure. Tool docstrings for the six aggregating tools mention the marker
- README: documented that cached responses hold the spillover preview, so the cache and spillover directory should be cleared together via `manage_cache`
- `ruff` added to the `dev` dependency group
- `tests/test_caching.py` covering cache hit/miss, error bypass, error-then-success recovery, and statistics for `ErrorAwareCachingMiddleware`

## [0.4.0] - 2026-05-31

### Security
- Validate user-supplied URL path segments (`ori`, `district_code`, use-of-force `group`/`spec`) via new `validate_path_segment()`, rejecting `/`, `\`, and `..` to prevent path traversal / endpoint redirection
- Stop surfacing or logging the raw `httpx` exception in `api_get()`'s network-error branch; some httpx errors carry the request URL, which includes the `API_KEY` query parameter. The response is now a generic message and only the exception type is logged

### Fixed
- `manage_cache` runs its blocking filesystem I/O (glob/read/rmtree) via `asyncio.to_thread` so it no longer stalls the event loop, while keeping FastMCP middleware stats reads/resets on the event loop to avoid cross-thread access

### Changed
- `validate_path_segment` error messages now spell out the non-empty and no-`..` constraints rather than implying them via the allowed-character list
- Dependabot now tracks the Python (`pip`) and `github-actions` ecosystems instead of the unused `npm` ecosystem

### Added
- Regression tests for `validate_path_segment`, the `ori` path through `validate_crime_data_params`, malicious-ORI rejection in `get_police_employment`, path-segment rejection in `lookup_agency` and `get_use_of_force_data`, and `_collect_stats` skipping non-caching middleware

## [0.3.1] - 2026-05-23

### Fixed
- `manage_cache action="clear"` now resets in-memory `ResponseCachingMiddleware` hit/miss counters; previously, lifespan shutdown silently re-persisted pre-clear totals, undoing the clear
- Tightened `_MM_YYYY_RE` in `response_utils` to reject impossible months (e.g., `13-2020`); the loose pattern was silently rolling malformed keys into yearly aggregates
- README: corrected cache tier description (added missing 1-day TTL tier for homepage summary; included `get_nibrs_estimation` in the 90-day group)
- README: corrected query-level description (some tools support region/agency-type/size beyond national/state/agency)
- README: corrected `get_arrest_data` demographic breakdown categories (male, female, sex, race)

### Changed
- Unified the strict `mm-yyyy` regex between `validators` and `response_utils` (single source of truth)
- Documented the strategy-inheritance invariant in `_aggregate_section`

### Added
- Regression tests for the cache-clear stats reset (happy path + AttributeError fallback for broken private layout)
- PyPI version badge in README

## [0.3.0] - 2026-04-04

### Added
- `get_crime_trends` tool for querying national/state crime trend data
- `get_cde_homepage_summary` tool for CDE homepage statistics
- `read_spillover` tool for accessing oversized response files saved by spillover middleware
- Persistent cache hit/miss statistics across server restarts
- Codecov integration with coverage badge
- Comprehensive test suite expanded to 392 tests (99% coverage)

### Fixed
- Spillover TOCTOU race condition using atomic file creation
- Dynamic upper bound for year validation (no hardcoded future year)
- `build_geo_path` hardened with assertion for invalid levels
- Spillover middleware excludes `read_spillover` to prevent recursive spilling
- Symlink path traversal protection in `read_spillover`
- Workflow permissions for GitHub Actions security alerts
- OSError tests use mocks instead of chmod (CI compatibility when running as root)

### Changed
- Homepage summary uses 1-day cache TTL
- Default cache TTL for agency/incident data changed to 30-day
- Concurrent API calls in homepage summary tool
- Extracted shared helpers and deduplicated `_load_persisted_stats` and `collection_names`

## [0.2.0] - 2026-04-03

### Added
- Cache management tool (`manage_cache`) for cache status, clear, and clear_expired operations
- Session cache hit-rate reporting
- Response spillover middleware for handling large API responses
- Smart pagination and filtering for API results
- Yearly aggregation of monthly crime data (sums actuals, averages rates, takes last population)
- Case-insensitive agency name filtering via `name_filter` parameter in `lookup_agency`
- Persistent disk-backed response caching with tiered TTLs (90-day for summaries/trends/reference; 30-day for agency/incident data)
- Comprehensive test suite (144+ tests) with `respx` mocking
- CI workflow for Python 3.11, 3.12, and 3.13
- Shared validation module for dates, levels, offenses, states, and ORI codes
- GitHub Actions publish workflow for PyPI and GitHub Releases

### Fixed
- `filter_agencies_by_name` now passes through non-array dicts correctly
- Hardened pagination defaults, spillover stat races, and group key collisions
- Input validation and error handling improvements across all tools
- Orphaned `.info` files when cache collection directory is already absent
- Cache clear uses `shutil.rmtree` to prevent orphaned directories
- Path containment validation and naive datetime safety in cache tool
- Rate limiter edge cases: reject invalid `max_requests`, dynamic window descriptions
- Tightened `mm-yyyy` month regex to reject invalid months

### Changed
- Migrated to fastmcp 3.2+ with `ResponseCachingMiddleware` and `FileTreeStore`
- Extracted shared validators into dedicated `validators.py` module

## [0.1.0] - 2025-03-15

### Added
- Initial release: 15 MCP tools for querying the FBI Crime Data Explorer API
- Tools: crime trends, NIBRS data, arrests, hate crimes, expanded homicide/property data, police employment, LEOKA, LESDC, use of force, summarized crime data, agency lookup, reference data, NIBRS estimation
- Sliding-window rate limiter (1000 requests/hour)
- `httpx.AsyncClient` wrapper with FBI API key management
