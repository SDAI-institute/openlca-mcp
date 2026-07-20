"""Phase 1 — Goal & Scope: search and lookup tools (read-only)."""

from __future__ import annotations

from typing import Optional

from .. import handlers
from ..app import call_handler, ro_tool
from ..schemas import REF, arr

_MODEL_TYPES = ["Flow", "Process", "ImpactMethod", "ProductSystem", "FlowProperty", "Unit"]


@ro_tool(
    "search_flows",
    "Search for material flows in the openLCA database. Keywords are case-insensitive "
    "and use partial matching (all keywords must be present). "
    "Example: keywords=['steel','hot','rolled'] finds 'Steel, hot rolled, coil'.",
    {"count": {"type": "integer"}, "flows": arr(REF)},
)
async def search_flows(
    keywords: list[str], max_results: int = 10, flow_type: Optional[str] = None,
    connection: Optional[str] = None,
) -> dict:
    return await call_handler(
        handlers.handle_search_flows,
        {"keywords": keywords, "max_results": max_results, "flow_type": flow_type},
        connection,
    )


@ro_tool(
    "search_processes",
    "Search for processes (production, transport, ...) in the openLCA database. "
    "Keywords are case-insensitive with partial matching (all must match).",
    {"count": {"type": "integer"}, "processes": arr(REF)},
)
async def search_processes(
    keywords: list[str], max_results: int = 10, connection: Optional[str] = None,
) -> dict:
    return await call_handler(
        handlers.handle_search_processes,
        {"keywords": keywords, "max_results": max_results},
        connection,
    )


@ro_tool(
    "search_impact_methods",
    "Search for LCIA methods (TRACI, ReCiPe, CML, ILCD, EF, ...). Returns the matched "
    "method with its impact categories (id + name).",
    {"method": {"type": "object", "description": "Matched impact method + its categories."}},
)
async def search_impact_methods(keywords: list[str], connection: Optional[str] = None) -> dict:
    return await call_handler(
        handlers.handle_search_impact_methods, {"keywords": keywords}, connection
    )


@ro_tool(
    "find_providers",
    "Find all processes that produce a given flow. Provide flow_id (preferred) or "
    "flow_name. Use after search_flows to identify production processes for linking.",
    {"count": {"type": "integer"}, "providers": arr(REF)},
)
async def find_providers(
    flow_id: Optional[str] = None, flow_name: Optional[str] = None,
    connection: Optional[str] = None,
) -> dict:
    return await call_handler(
        handlers.handle_find_providers, {"flow_id": flow_id, "flow_name": flow_name}, connection
    )


@ro_tool(
    "get_entity_by_name",
    "Exact-name lookup of a single entity. Faster and more precise than keyword search "
    "when you know the exact name. Returns a compact {id, name, type, category} summary.",
    {"entity": {"type": "object", "description": "Compact summary of the matched entity."}},
)
async def get_entity_by_name(model_type: str, name: str, connection: Optional[str] = None) -> dict:
    return await call_handler(
        handlers.handle_get_entity_by_name, {"model_type": model_type, "name": name}, connection
    )
