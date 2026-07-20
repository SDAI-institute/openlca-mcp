"""
Guided LCA prompts for the openLCA MCP server.

Prompts are reusable, parameterized instructions an MCP client can surface to the
user/agent — here, walkthroughs for the common openLCA workflows. They reference
the server's own tools by name so the agent knows the call sequence.
"""

from __future__ import annotations

from typing import Optional

from .app import mcp


@mcp.prompt(
    name="lca_calculation_walkthrough",
    description="Step-by-step guide to run a full LCA calculation in openLCA via these tools.",
)
def lca_calculation_walkthrough(product: str = "the product under study") -> str:
    return (
        f"Goal: calculate the life-cycle impacts of {product} using openLCA.\n\n"
        "Follow these steps, using the server's tools:\n"
        "1. `health_check` — confirm openLCA is reachable and a database is loaded.\n"
        "2. `search_processes` (or `get_entity_by_name`) — find the process that "
        f"represents {product}. Note its id.\n"
        "3. `search_impact_methods` — pick an LCIA method (e.g. ReCiPe, TRACI, EF). "
        "Note the method id and its impact categories.\n"
        "4. `create_product_system` — build a product system from the process id "
        "(auto-links providers). Note the product_system id.\n"
        "5. `calculate_impacts` — run with the system id + method id. Keep the "
        "returned `result_id`.\n"
        "6. `analyze_contributions` / `get_contribution_tree` — find the hotspots for "
        "the impact categories that matter.\n"
        "7. `dispose_result` — free server memory when done with the result_id.\n\n"
        "Tip: pass `connection` on any tool to target a specific openLCA instance; "
        "omit it to use the default (your local desktop openLCA)."
    )


@mcp.prompt(
    name="interpret_impact_results",
    description="Guide for interpreting calculate_impacts output and identifying hotspots.",
)
def interpret_impact_results(result_id: Optional[str] = None) -> str:
    rid = result_id or "<result_id from calculate_impacts>"
    return (
        "Interpret an LCA result rigorously:\n\n"
        f"1. Review the impact list from `calculate_impacts` (result_id={rid}). "
        "Identify the largest-magnitude categories, but do not compare across "
        "categories with different units.\n"
        "2. For each key category, call `analyze_contributions` with its "
        "`impact_category_id` to rank the processes/flows driving it.\n"
        "3. Use `get_contribution_tree` to trace hotspots upstream through the supply "
        "chain.\n"
        "4. Check the result's `warnings` for consistency issues (e.g. unlinked "
        "exchanges) before drawing conclusions.\n"
        "5. If comparing alternatives, prefer `compare_systems`; for robustness, run "
        "`run_monte_carlo` (uncertainty) or `run_scenario_analysis` (sensitivity).\n"
        "6. State assumptions (functional unit, method, system boundary) alongside any "
        "conclusion."
    )


@mcp.prompt(
    name="build_product_system_guide",
    description="Guide to model a new process and product system from scratch in openLCA.",
)
def build_product_system_guide() -> str:
    return (
        "Model a new product system (writes require a writable connection):\n\n"
        "1. `create_product_flow` — define the reference product flow.\n"
        "2. `search_flows` / `find_providers` — locate input flows and their providers.\n"
        "3. `create_process` — define the unit process with exchanges. Mark exactly one "
        "output as the quantitative reference (`is_quantitative_reference=true`).\n"
        "4. `create_product_system` — build the system from the process; providers are "
        "auto-linked.\n"
        "5. Inspect the result in the openLCA UI (default/local connection) to verify "
        "the model before calculating.\n"
        "6. Proceed to `calculate_impacts`.\n\n"
        "Note: writes are blocked on read-only connections and return a structured "
        "WRITE_BLOCKED error."
    )
