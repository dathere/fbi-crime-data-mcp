# Suggested Commands

## Setup & Run
```bash
uv sync                                            # Install dependencies
FBI_API_KEY=xxx uv run fbi-crime-data-mcp           # Run server (stdio transport)
```

## Testing
```bash
uv run pytest                                       # Run all tests (324 tests)
uv run pytest -x -q                                 # Stop on first failure, quiet
uv run pytest tests/test_validators.py              # Run specific test file
uv run pytest -k "test_name"                        # Run specific test by name
FBI_API_KEY=xxx uv run pytest -m integration         # Integration tests (real API)
```

## Linting & Formatting
```bash
uvx ruff check src/ tests/                          # Lint check
uvx ruff format src/ tests/                         # Auto-format
uvx ruff format --check src/ tests/                 # Check formatting without changing
```

## Git / CI
```bash
git status                                          # Check working tree
gh pr view                                          # View current PR
gh pr create --title "..." --body "..."             # Create PR
```

## Utilities (macOS/Darwin)
```bash
grep -r "pattern" src/                              # Search codebase
find src/ -name "*.py"                              # Find files
```
