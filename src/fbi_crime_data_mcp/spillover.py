"""Response spillover middleware — saves oversized tool results to disk."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re

import mcp.types as mt
from fastmcp.server.middleware.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.tools.base import ToolResult
from mcp.types import TextContent

from .constants import SPILLOVER_CHAR_LIMIT, SPILLOVER_DIR, SPILLOVER_PREVIEW_CHARS

__all__ = ["ResponseSpilloverMiddleware"]

logger = logging.getLogger(__name__)


class ResponseSpilloverMiddleware(Middleware):
    """Middleware that saves oversized tool responses to disk.

    When a tool response exceeds *max_chars*, the full text is written to a
    content-addressed file under *spillover_dir* and the client receives a
    truncated preview with the file path.  Subsequent identical responses
    reuse the same file (no duplicates).
    """

    def __init__(
        self,
        *,
        max_chars: int = SPILLOVER_CHAR_LIMIT,
        preview_chars: int = SPILLOVER_PREVIEW_CHARS,
        excluded_tools: set[str] | None = None,
    ) -> None:
        if max_chars <= 0:
            raise ValueError(f"max_chars must be positive, got {max_chars}")
        self.max_chars = max_chars
        self.preview_chars = preview_chars
        self.excluded_tools = excluded_tools or {"manage_cache", "read_spillover"}

    async def on_call_tool(
        self,
        context: MiddlewareContext[mt.CallToolRequestParams],
        call_next: CallNext[mt.CallToolRequestParams, ToolResult],
    ) -> ToolResult:
        result = await call_next(context)

        tool_name = context.message.name
        if tool_name in self.excluded_tools:
            return result

        texts = [block.text for block in result.content if isinstance(block, TextContent)]
        if not texts:
            return result

        full_text = "\n\n".join(texts)
        if len(full_text) <= self.max_chars:
            return result

        # Content-addressed filename avoids duplicates across repeated calls
        safe_name = re.sub(r"[^A-Za-z0-9_-]", "_", tool_name)
        hash_hex = hashlib.sha256(full_text.encode()).hexdigest()[:8]
        filename = f"{safe_name}_{hash_hex}.json"
        spillover_path = SPILLOVER_DIR / filename

        preview = full_text[: self.preview_chars]

        def _write_spillover() -> bool:
            """Atomically create and write the spillover file in a worker thread."""
            SPILLOVER_DIR.mkdir(parents=True, exist_ok=True)
            try:
                with spillover_path.open("x", encoding="utf-8") as spillover_file:
                    spillover_file.write(full_text)
                return True
            except FileExistsError:
                return False

        try:
            written = await asyncio.to_thread(_write_spillover)
            if written:
                logger.info(
                    "Tool %r response spilled to %s (%d chars)",
                    tool_name,
                    spillover_path,
                    len(full_text),
                )
        except OSError:
            logger.warning(
                "Failed to spill tool %r response to %s; returning preview only",
                tool_name,
                spillover_path,
                exc_info=True,
            )
            truncated = (
                f"NOTE: Response was {len(full_text):,} characters, which exceeds the "
                f"{self.max_chars:,}-character limit. The full response could not be "
                f"saved due to a filesystem error, so only a preview is shown below.\n"
                f"\n"
                f"To work with this data, narrow your query (shorter date range, "
                f"specific state/agency) or retry after resolving disk/permissions issues.\n"
                f"\n"
                f"--- PREVIEW (first {self.preview_chars:,} chars) ---\n"
                f"{preview}"
            )
            return ToolResult(content=[TextContent(type="text", text=truncated)])

        truncated = (
            f"NOTE: Response was {len(full_text):,} characters, which exceeds the "
            f"{self.max_chars:,}-character limit. The full response has been saved to:\n"
            f"  {spillover_path}\n"
            f"\n"
            f"To read the full data, call the read_spillover tool with "
            f'filename="{filename}". Use offset/limit to page through large results.\n'
            f"Alternatively, narrow your query (shorter date range, specific state/agency).\n"
            f"\n"
            f"--- PREVIEW (first {self.preview_chars:,} chars) ---\n"
            f"{preview}"
        )
        return ToolResult(content=[TextContent(type="text", text=truncated)])
