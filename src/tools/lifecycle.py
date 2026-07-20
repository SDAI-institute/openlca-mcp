"""Utilities — result lifecycle (connection-agnostic; operate on the result store)."""

from __future__ import annotations

from .. import handlers
from ..app import run_offloaded, write_tool


@write_tool(
    "dispose_result",
    "Dispose a calculation result to free server memory. Always call this when finished "
    "with a result_id from calculate_impacts.",
    {"disposed": {"type": "string"}, "message": {"type": "string"}},
)
async def dispose_result(result_id: str) -> dict:
    return await run_offloaded(handlers.handle_dispose_result, {"result_id": result_id})


@write_tool(
    "dispose_all_results",
    "Dispose every tracked calculation result. Useful for cleanup at the end of a session.",
    {"disposed_count": {"type": "integer"}},
)
async def dispose_all_results() -> dict:
    return await run_offloaded(handlers.handle_dispose_all_results, {})
