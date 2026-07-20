"""Phase 3 — Life Cycle Impact Assessment: calculate and read results."""

from __future__ import annotations

from typing import Optional

from .. import handlers
from ..app import call_handler, ro_tool
from ..schemas import IMPACT, REF, arr


@ro_tool(
    "calculate_impacts",
    "Calculate environmental impacts for a product system. Returns a result_id, a "
    "compact ResultSummary (top impacts, suggested next actions), the full impact list, "
    "and any consistency warnings. IMPORTANT: call dispose_result when done with the result_id.",
    {
        "result_id": {"type": "string"},
        "summary": {"type": "object"},
        "impacts": arr(IMPACT),
        "warnings": arr({"type": "string"}),
        "context": {"type": "object"},
        "message": {"type": "string"},
    },
)
async def calculate_impacts(
    system_id: Optional[str] = None, system_name: Optional[str] = None,
    method_id: Optional[str] = None, method_keywords: Optional[list[str]] = None,
    amount: float = 1.0, connection: Optional[str] = None,
) -> dict:
    return await call_handler(
        handlers.handle_calculate_impacts,
        {"system_id": system_id, "system_name": system_name, "method_id": method_id,
         "method_keywords": method_keywords, "amount": amount},
        connection,
    )


@ro_tool(
    "get_inventory_results",
    "Get the life cycle inventory (elementary/environmental flows) for a calculated "
    "result. Requires result_id from calculate_impacts. direction filters input/output/both.",
    {
        "result_id": {"type": "string"},
        "count": {"type": "integer"},
        "inventory": arr({
            "type": "object",
            "properties": {
                "name": {"type": ["string", "null"]}, "flow": REF,
                "amount": {"type": ["number", "null"]}, "unit": {"type": ["string", "null"]},
                "is_input": {"type": ["boolean", "null"]}, "location": {"type": ["string", "null"]},
            },
        }),
    },
)
async def get_inventory_results(
    result_id: str, direction: str = "both", connection: Optional[str] = None
) -> dict:
    return await call_handler(
        handlers.handle_get_inventory_results,
        {"result_id": result_id, "direction": direction},
        connection,
    )


@ro_tool(
    "get_total_requirements",
    "Get the total requirements (scaled technology flows) of a calculated product "
    "system: which processes run and at what amount. Requires result_id.",
    {
        "result_id": {"type": "string"},
        "count": {"type": "integer"},
        "requirements": arr({
            "type": "object",
            "properties": {
                "process": {"type": ["string", "null"]}, "provider": REF,
                "flow": {"type": ["string", "null"]}, "amount": {"type": ["number", "null"]},
            },
        }),
    },
)
async def get_total_requirements(result_id: str, connection: Optional[str] = None) -> dict:
    return await call_handler(
        handlers.handle_get_total_requirements, {"result_id": result_id}, connection
    )


@ro_tool(
    "get_normalized_impacts",
    "Get normalized impact results (relative to the method's normalization set). "
    "Requires result_id. Empty if the method has no normalization set.",
    {"result_id": {"type": "string"}, "normalized": arr(IMPACT)},
)
async def get_normalized_impacts(result_id: str, connection: Optional[str] = None) -> dict:
    return await call_handler(
        handlers.handle_get_normalized_impacts, {"result_id": result_id}, connection
    )


@ro_tool(
    "get_weighted_impacts",
    "Get weighted impact results (after normalization + weighting). Requires result_id. "
    "Empty if the method has no weighting set.",
    {"result_id": {"type": "string"}, "weighted": arr(IMPACT)},
)
async def get_weighted_impacts(result_id: str, connection: Optional[str] = None) -> dict:
    return await call_handler(
        handlers.handle_get_weighted_impacts, {"result_id": result_id}, connection
    )
