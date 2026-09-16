"""Phase 1 — Goal & Scope: search and lookup tools (read-only)."""

from __future__ import annotations

from typing import Literal, Optional

from .. import handlers
from ..app import call_handler, ro_tool
from ..schemas import REF, arr

FlowType = Literal["PRODUCT_FLOW", "ELEMENTARY_FLOW", "WASTE_FLOW"]
ModelType = Literal["Flow", "Process", "ImpactMethod", "ProductSystem", "FlowProperty", "Unit"]

_MODEL_TYPES = ["Flow", "Process", "ImpactMethod", "ProductSystem", "FlowProperty", "Unit"]


@ro_tool(
    "search_flows",
    "Search for material flows in the openLCA database. Keywords are case-insensitive "
    "and use partial matching (all keywords must be present). "
    "Example: keywords=['steel','hot','rolled'] finds 'Steel, hot rolled, coil'.",
    {"count": {"type": "integer"}, "flows": arr(REF)},
)
async def search_flows(
    keywords: list[str],
    max_results: int = 10,
    flow_type: Optional[FlowType] = None,
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
    keywords: list[str],
    max_results: int = 10,
    connection: Optional[str] = None,
) -> dict:
    return await call_handler(
        handlers.handle_search_processes,
        {"keywords": keywords, "max_results": max_results},
        connection,
    )


@ro_tool(
    "search_product_systems",
    "Browse or search existing product systems in the active openLCA database. "
    "This is read-only and never creates a system. Pass keywords for partial "
    "case-insensitive matching, or omit them to browse existing calculation-ready systems.",
    {"count": {"type": "integer"}, "product_systems": arr(REF)},
)
async def search_product_systems(
    keywords: Optional[list[str]] = None,
    max_results: int = 25,
    connection: Optional[str] = None,
) -> dict:
    return await call_handler(
        handlers.handle_search_product_systems,
        {"keywords": keywords or [], "max_results": max_results},
        connection,
    )


@ro_tool(
    "inspect_product_system",
    "Inspect an existing product system's exact calculation target: reference process/flow, "
    "target amount, unit, and flow property. Use this before calculation to confirm the "
    "functional unit. This tool is read-only.",
    {"product_system": {"type": "object", "description": "Resolved product-system calculation metadata."}},
)
async def inspect_product_system(
    system_id: Optional[str] = None,
    system_name: Optional[str] = None,
    connection: Optional[str] = None,
) -> dict:
    return await call_handler(
        handlers.handle_inspect_product_system,
        {"system_id": system_id, "system_name": system_name},
        connection,
    )


@ro_tool(
    "list_impact_methods",
    "Browse LCIA methods available in the active openLCA database without guessing a method name. "
    "Returns existing method descriptors only and never mutates the database.",
    {"count": {"type": "integer"}, "impact_methods": arr(REF)},
)
async def list_impact_methods(
    max_results: int = 25,
    connection: Optional[str] = None,
) -> dict:
    return await call_handler(
        handlers.handle_list_impact_methods,
        {"max_results": max_results},
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
    flow_id: Optional[str] = None,
    flow_name: Optional[str] = None,
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
async def get_entity_by_name(
    model_type: ModelType,
    name: str,
    connection: Optional[str] = None,
) -> dict:
    return await call_handler(
        handlers.handle_get_entity_by_name, {"model_type": model_type, "name": name}, connection
    )
