"""Phase 4 — Interpretation: contributions, trees, Sankey, comparison, uncertainty, export."""

from __future__ import annotations

from typing import Any, Optional

from .. import handlers
from ..app import call_handler, ro_tool, write_tool
from ..schemas import REF, arr


@ro_tool(
    "check_result_consistency",
    "Sanity-check a stored calculation result: for every impact category, verify that "
    "per-process contributions sum to the reported total (within tolerance). A mismatch "
    "usually signals broken provider linking or a partially-computed result. Run this "
    "after calculate_impacts before trusting the numbers.",
    {
        "consistent": {"type": "boolean", "description": "True if no warnings were found."},
        "warnings": arr({"type": "string", "description": "One string per inconsistency found; empty if consistent."}),
    },
)
async def check_result_consistency(
    result_id: str, rel_tol: float = 1e-3, abs_tol: float = 1e-12,
    connection: Optional[str] = None,
) -> dict:
    return await call_handler(
        handlers.handle_check_result_consistency,
        {"result_id": result_id, "rel_tol": rel_tol, "abs_tol": abs_tol},
        connection,
    )


@ro_tool(
    "analyze_contributions",
    "Identify which processes (or flows) contribute most to an impact category — the "
    "hotspots. Requires result_id and impact_category_id (from calculate_impacts' impacts). "
    "Returns top contributors with share and absolute amount.",
    {
        "result_id": {"type": "string"}, "impact_category_id": {"type": "string"},
        "contribution_type": {"type": "string", "enum": ["process", "flow"]},
        "count": {"type": "integer"},
        "contributors": arr({
            "type": "object",
            "properties": {
                "name": {"type": ["string", "null"]}, "amount": {"type": ["number", "null"]},
                "share": {"type": ["number", "null"]}, "ref": REF,
            },
        }),
    },
)
async def analyze_contributions(
    result_id: str, impact_category_id: str, n: int = 10,
    contribution_type: str = "process", min_share: float = 0.0,
    connection: Optional[str] = None,
) -> dict:
    return await call_handler(
        handlers.handle_analyze_contributions,
        {"result_id": result_id, "impact_category_id": impact_category_id, "n": n,
         "contribution_type": contribution_type, "min_share": min_share},
        connection,
    )


@ro_tool(
    "get_contribution_tree",
    "Build an upstream contribution (hotspot) tree for an impact category: nested "
    "process nodes with amount, direct contribution, and share. Requires result_id and "
    "impact_category_id. Pruned by max_depth and min_share.",
    {
        "result_id": {"type": "string"}, "impact_category_id": {"type": "string"},
        "tree": arr({"type": "object", "description": "Recursive node: name, amount, direct, share, ref, children[]."}),
    },
)
async def get_contribution_tree(
    result_id: str, impact_category_id: str, max_depth: int = 3, min_share: float = 0.01,
    connection: Optional[str] = None,
) -> dict:
    return await call_handler(
        handlers.handle_get_contribution_tree,
        {"result_id": result_id, "impact_category_id": impact_category_id,
         "max_depth": max_depth, "min_share": min_share},
        connection,
    )


@ro_tool(
    "get_sankey",
    "Get Sankey-graph data (nodes + edges) for an impact category, suitable for "
    "visualization. Requires result_id and impact_category_id.",
    {
        "result_id": {"type": "string"}, "impact_category_id": {"type": "string"},
        "sankey": {"type": "object", "description": "Graph data with nodes and edges."},
    },
)
async def get_sankey(
    result_id: str, impact_category_id: str, max_nodes: int = 50, min_share: float = 0.0,
    connection: Optional[str] = None,
) -> dict:
    return await call_handler(
        handlers.handle_get_sankey,
        {"result_id": result_id, "impact_category_id": impact_category_id,
         "max_nodes": max_nodes, "min_share": min_share},
        connection,
    )


@ro_tool(
    "compare_systems",
    "Compare two product systems on the same impact method. Returns per-category "
    "system1, system2, difference, and percent change. Runs and disposes both "
    "calculations internally (no result_id needed).",
    {"comparison": {"type": "object", "description": "Per-category system1, system2, difference, % change."}},
)
async def compare_systems(
    system1_id: str, system2_id: str, method_id: Optional[str] = None,
    method_keywords: Optional[list[str]] = None, amount: float = 1.0,
    connection: Optional[str] = None,
) -> dict:
    return await call_handler(
        handlers.handle_compare_systems,
        {"system1_id": system1_id, "system2_id": system2_id, "method_id": method_id,
         "method_keywords": method_keywords, "amount": amount},
        connection,
    )


@ro_tool(
    "run_monte_carlo",
    "Run Monte Carlo uncertainty analysis. Returns per-impact statistics (mean, std, "
    "CV, percentiles). Can be slow for large systems / high iteration counts.",
    {
        "count": {"type": "integer"},
        "uncertainty": arr({"type": "object", "description": "Per-impact uncertainty stats."}),
    },
)
async def run_monte_carlo(
    system_id: str, method_id: Optional[str] = None,
    method_keywords: Optional[list[str]] = None, iterations: int = 100,
    connection: Optional[str] = None,
) -> dict:
    return await call_handler(
        handlers.handle_run_monte_carlo,
        {"system_id": system_id, "method_id": method_id,
         "method_keywords": method_keywords, "iterations": iterations},
        connection,
    )


@ro_tool(
    "run_scenario_analysis",
    "Vary a single parameter over a list of values and report impacts for each value. "
    "Useful for sensitivity analysis.",
    {
        "parameter": {"type": "string"},
        "scenarios": {"type": "object", "description": "Map of parameter value -> impact rows."},
    },
)
async def run_scenario_analysis(
    system_id: str, parameter_name: str, values: list[float],
    method_id: Optional[str] = None, method_keywords: Optional[list[str]] = None,
    connection: Optional[str] = None,
) -> dict:
    return await call_handler(
        handlers.handle_run_scenario_analysis,
        {"system_id": system_id, "parameter_name": parameter_name, "values": values,
         "method_id": method_id, "method_keywords": method_keywords},
        connection,
    )


@write_tool(
    "export_results",
    "Export results to a file. With result_id: export its impacts to CSV (format=csv) "
    "or an Excel workbook (format=excel). With data + kind=comparison: export a "
    "compare_systems result to CSV. filepath is the output path on the server host.",
    {
        "exported": {"type": "boolean"}, "filepath": {"type": "string"},
        "format": {"type": "string", "enum": ["csv", "excel"]},
    },
)
async def export_results(
    filepath: str, result_id: Optional[str] = None, data: Optional[dict[str, Any]] = None,
    kind: str = "impacts", format: str = "csv", connection: Optional[str] = None,
) -> dict:
    return await call_handler(
        handlers.handle_export_results,
        {"filepath": filepath, "result_id": result_id, "data": data,
         "kind": kind, "format": format},
        connection,
    )
