"""Tool for reading spillover files saved by ResponseSpilloverMiddleware."""

from __future__ import annotations

import json

from ..constants import SPILLOVER_DIR
from ..server import mcp

_DEFAULT_LIMIT = 50_000


@mcp.tool()
async def read_spillover(
    filename: str,
    offset: int = 0,
    limit: int = _DEFAULT_LIMIT,
) -> str:
    """Read a spillover file that was saved when a tool response exceeded the size limit.

    Use this to retrieve data beyond the preview shown in a truncated response.
    The filename is provided in the spillover notice (e.g., "get_nibrs_data_a1b2c3d4.json").

    Args:
        filename: Name of the spillover file (e.g., "get_nibrs_data_a1b2c3d4.json").
                  Use "list" to see all available spillover files.
        offset: Character position to start reading from (default: 0).
        limit: Maximum number of characters to return (default: 50000).
    """
    if filename == "list":
        return _list_spillover_files()

    # Validate filename to prevent path traversal
    if "/" in filename or "\\" in filename or ".." in filename:
        return "Invalid filename. Use just the filename, not a path."

    filepath = SPILLOVER_DIR / filename
    if not filepath.is_file():
        available = _list_spillover_files()
        return f"File not found: {filename}\n\n{available}"

    try:
        text = filepath.read_text(encoding="utf-8")
    except OSError as e:
        return f"Error reading file: {e}"

    total_chars = len(text)
    chunk = text[offset : offset + limit]
    remaining = total_chars - offset - len(chunk)

    header = f"File: {filename} | Total: {total_chars:,} chars | Showing: {offset:,}-{offset + len(chunk):,}"
    if remaining > 0:
        header += f" | Remaining: {remaining:,} chars (use offset={offset + len(chunk)} to continue)"

    return f"{header}\n\n{chunk}"


def _list_spillover_files() -> str:
    """List all available spillover files."""
    if not SPILLOVER_DIR.is_dir():
        return "No spillover files found."

    files = sorted(SPILLOVER_DIR.glob("*.json"))
    if not files:
        return "No spillover files found."

    entries = []
    for f in files:
        try:
            size = f.stat().st_size
        except OSError:
            size = 0
        entries.append({"filename": f.name, "size_kb": round(size / 1024, 1)})

    return json.dumps({"spillover_files": entries}, indent=2)
