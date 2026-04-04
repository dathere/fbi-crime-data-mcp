# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

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
