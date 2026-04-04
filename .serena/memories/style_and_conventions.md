# Code Style & Conventions

## General
- **Line length:** 120 characters (configured in pyproject.toml)
- **Formatter/Linter:** ruff (E501 line-length rule ignored since line-length is set)
- **Python version:** 3.11+ (uses `str | None` union syntax, not `Optional[str]`)
- **Imports:** `from __future__ import annotations` used in core modules

## Naming
- **Files:** snake_case (e.g., `api_client.py`, `hate_crime.py`)
- **Functions:** snake_case (e.g., `get_arrest_data`, `validate_mm_yyyy`)
- **Classes:** PascalCase (e.g., `AppContext`, `ResponseSpilloverMiddleware`)
- **Constants:** UPPER_SNAKE_CASE (e.g., `NIBRS_OFFENSES`, `BASE_URL`)
- **Private helpers:** prefixed with underscore (e.g., `_trim_response`, `_apply_strategy`)

## Type Hints
- All function signatures have type hints
- Return types always specified
- `str | None` union style (not Optional)
- Validators return `str | None` (error message or None)

## Docstrings
- Module-level docstrings on all files (one-line, in triple quotes)
- Function docstrings with Args sections on public/tool functions
- No docstrings on private helpers unless complex

## Tool Pattern
Each tool in `src/fbi_crime_data_mcp/tools/`:
1. Decorated with `@mcp.tool()`
2. Async function taking typed params + `ctx: Context | None = None`
3. Returns `str` always — JSON on success, error message on failure
4. Never raises exceptions to the MCP client
5. Validates params first, builds URL path, calls `app_ctx.api_get()`, post-processes with `process_crime_response()`

## Error Handling
- Tools return error strings, never raise
- Validators return error string on failure, None on success
- `validate_crime_data_params()` is the consolidated validator for most crime data tools
- API errors caught and formatted in `api_client.py`

## Testing
- pytest-asyncio with `asyncio_mode = "auto"` (no @pytest.mark.asyncio needed)
- Mock fixtures in `tests/conftest.py` (FakeAppContext, FakeContext)
- respx for HTTP mocking in api_client tests
- Tests follow pattern: validation tests first, then happy-path API call verification
