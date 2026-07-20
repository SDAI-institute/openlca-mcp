"""
Read-only MCP resources for the openLCA server.

Resources are pullable, addressable data (unlike tools, which take actions):
  * ``openlca://connections``      configured connection profiles (+ default).
  * ``openlca://impact-methods``   LCIA methods in the default connection's database.
  * ``openlca://product-systems``  product systems in the default connection's database.
  * ``openlca://iso-phases-guide`` static ISO 14040/44 phase reference.

Database-backed resources read the **default** connection and offload the blocking
IPC call so they never stall the event loop.
"""

from __future__ import annotations

from typing import Any

import anyio
import olca_schema as o

from . import responses
from .app import mcp, resolve_client
from .connections import get_profiles


@mcp.resource(
    "openlca://connections",
    name="openLCA connections",
    description="Configured openLCA connection profiles this server can target.",
    mime_type="application/json",
)
def connections_resource() -> dict[str, Any]:
    profiles = get_profiles()
    return {
        "default": "default",
        "count": len(profiles),
        "connections": [
            {
                "id": p.id, "host": p.host, "port": p.port,
                "read_only": p.read_only, "kind": p.kind, "label": p.label,
            }
            for p in profiles.values()
        ],
        "note": "Call test_connection to probe a profile's liveness.",
    }


async def _descriptors(model_type) -> list[dict[str, Any]]:
    client = resolve_client(None)  # default connection
    refs = await anyio.to_thread.run_sync(client.client.get_descriptors, model_type)
    return [responses.ref_to_dict(r) for r in refs]


@mcp.resource(
    "openlca://impact-methods",
    name="LCIA methods",
    description="Impact assessment methods available in the default connection's database.",
    mime_type="application/json",
)
async def impact_methods_resource() -> dict[str, Any]:
    methods = await _descriptors(o.ImpactMethod)
    return {"count": len(methods), "impact_methods": methods}


@mcp.resource(
    "openlca://product-systems",
    name="Product systems",
    description="Product systems available in the default connection's database.",
    mime_type="application/json",
)
async def product_systems_resource() -> dict[str, Any]:
    systems = await _descriptors(o.ProductSystem)
    return {"count": len(systems), "product_systems": systems}


@mcp.resource(
    "openlca://iso-phases-guide",
    name="ISO 14040/44 phases",
    description="Reference for the four ISO LCA phases and the tools that map to each.",
    mime_type="text/markdown",
)
def iso_phases_guide() -> str:
    return (
        "# ISO 14040/14044 LCA phases\n\n"
        "1. **Goal & Scope** — define the question, functional unit, and system "
        "boundary. Tools: `search_flows`, `search_processes`, `search_impact_methods`, "
        "`find_providers`, `get_entity_by_name`.\n"
        "2. **Life Cycle Inventory (LCI)** — model processes and flows. Tools: "
        "`create_product_flow`, `create_process`, `create_product_system`, "
        "`get_inventory_results`, `get_total_requirements`.\n"
        "3. **Life Cycle Impact Assessment (LCIA)** — characterize, normalize, weight. "
        "Tools: `calculate_impacts`, `get_normalized_impacts`, `get_weighted_impacts`.\n"
        "4. **Interpretation** — hotspots, comparison, uncertainty, sensitivity. Tools: "
        "`analyze_contributions`, `get_contribution_tree`, `get_sankey`, "
        "`compare_systems`, `run_monte_carlo`, `run_scenario_analysis`, `export_results`.\n"
    )
