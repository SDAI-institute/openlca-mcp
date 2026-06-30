"""
MCP tool schema definitions for the openLCA server.

Tools are organized by the four ISO-14040/14044 LCA phases plus utilities.
``TOOLS`` is the single source of truth for what the server advertises; it is
keyed by tool name and validated against the handler map at import time
(see handlers.py / the regression test) so an advertised tool can never lack a
handler again.

Every tool declares an ``outputSchema`` describing the concrete shape its
handler returns (see handlers.py). The schemas intentionally keep
``additionalProperties: true`` and require only ``success`` so that the shared
error envelope (``{success: false, error_code, message, ...}``) also validates —
strict clients such as ChatGPT developer mode reject a tool result whose
``structuredContent`` does not conform to the declared ``outputSchema``.
"""

from mcp.types import Tool, ToolAnnotations

_MODEL_TYPES = ["Flow", "Process", "ImpactMethod", "ProductSystem", "FlowProperty", "Unit"]


# ---------------------------------------------------------------------------
# Reusable output sub-schemas
# ---------------------------------------------------------------------------

def _arr(items: dict) -> dict:
    return {"type": "array", "items": items}


# A compact openLCA entity reference (see responses.ref_to_dict).
_REF = {
    "type": "object",
    "description": "Compact openLCA entity reference.",
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "category": {"type": "string"},
    },
}

# A single impact result row (see handlers._impact_to_dict).
_IMPACT = {
    "type": "object",
    "properties": {
        "name": {"type": ["string", "null"]},
        "category": _REF,
        "category_id": {"type": ["string", "null"]},
        "amount": {"type": ["number", "null"]},
        "unit": {"type": ["string", "null"]},
    },
}


def _out(properties: dict | None = None) -> dict:
    """Build a tool output schema: a ``success`` flag plus declared fields.

    ``required`` lists only ``success`` and ``additionalProperties`` stays true so
    the same schema validates both success and error envelopes.
    """
    props = {"success": {"type": "boolean"}}
    if properties:
        props.update(properties)
    return {
        "type": "object",
        "properties": props,
        "required": ["success"],
        "additionalProperties": True,
    }


def _tool(
    name: str,
    description: str,
    properties: dict,
    required=None,
    *,
    output: dict | None = None,
    read_only: bool = True,
    destructive: bool = False,
    idempotent: bool = True,
) -> Tool:
    schema = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return Tool(
        name=name,
        title=name.replace("_", " ").title(),
        description=description,
        inputSchema=schema,
        outputSchema=_out(output),
        annotations=ToolAnnotations(
            title=name.replace("_", " ").title(),
            readOnlyHint=read_only,
            destructiveHint=destructive if not read_only else False,
            idempotentHint=idempotent,
            openWorldHint=False,
        ),
    )


# ---------------------------------------------------------------------------
# Utilities / connection
# ---------------------------------------------------------------------------

TOOLS = {}


def _register(tool: Tool) -> None:
    TOOLS[tool.name] = tool


_register(_tool(
    "test_connection",
    "Test connection to the openLCA IPC server. Use this first to verify openLCA "
    "is running and reachable. Returns connection status and port.",
    {},
    output={
        "connected": {"type": "boolean", "description": "Whether openLCA answered"},
        "port": {"type": "integer", "description": "IPC port that was probed"},
    },
))

_register(_tool(
    "health_check",
    "Health probe for the openLCA connection: whether the server is reachable and "
    "how much data the active database holds (process/flow/method/system counts). "
    "Richer than test_connection. Set count_entities=false to skip the (slower) counts.",
    {
        "count_entities": {
            "type": "boolean",
            "description": "Include per-type entity counts (default: true)",
            "default": True,
        }
    },
    output={
        "health": {
            "type": "object",
            "description": "Reachability and per-type entity counts of the active database.",
        }
    },
))

# ---------------------------------------------------------------------------
# Phase 1: Goal & Scope
# ---------------------------------------------------------------------------

_register(_tool(
    "search_flows",
    "Search for material flows in the openLCA database. Keywords are case-insensitive "
    "and use partial matching (all keywords must be present). "
    "Example: keywords=['steel','hot','rolled'] finds 'Steel, hot rolled, coil'.",
    {
        "keywords": {
            "type": "array", "items": {"type": "string"},
            "description": "Keywords to search for (all must match)",
        },
        "max_results": {"type": "integer", "description": "Max results", "default": 10},
        "flow_type": {
            "type": "string",
            "enum": ["PRODUCT_FLOW", "ELEMENTARY_FLOW", "WASTE_FLOW"],
            "description": "Optional filter by flow type",
        },
    },
    required=["keywords"],
    output={
        "count": {"type": "integer", "description": "Number of flows returned"},
        "flows": _arr(_REF),
    },
))

_register(_tool(
    "search_processes",
    "Search for processes (production, transport, ...) in the openLCA database. "
    "Keywords are case-insensitive with partial matching (all must match).",
    {
        "keywords": {
            "type": "array", "items": {"type": "string"},
            "description": "Keywords to search for",
        },
        "max_results": {"type": "integer", "description": "Max results", "default": 10},
    },
    required=["keywords"],
    output={
        "count": {"type": "integer", "description": "Number of processes returned"},
        "processes": _arr(_REF),
    },
))

_register(_tool(
    "search_impact_methods",
    "Search for LCIA methods (TRACI, ReCiPe, CML, ILCD, EF, ...). Returns the matched "
    "method with its impact categories (id + name).",
    {
        "keywords": {
            "type": "array", "items": {"type": "string"},
            "description": "Keywords (e.g. ['TRACI'], ['ReCiPe'])",
        }
    },
    required=["keywords"],
    output={
        "method": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "categories": _arr({
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                    },
                }),
            },
            "description": "The matched impact method and its impact categories.",
        }
    },
))

_register(_tool(
    "find_providers",
    "Find all processes that produce a given flow. Provide flow_id (preferred) or "
    "flow_name. Use after search_flows to identify production processes for linking.",
    {
        "flow_id": {"type": "string", "description": "Flow id to find providers for"},
        "flow_name": {"type": "string", "description": "Flow name (if id not provided)"},
    },
    output={
        "count": {"type": "integer", "description": "Number of providers returned"},
        "providers": _arr(_REF),
    },
))

_register(_tool(
    "get_entity_by_name",
    "Exact-name lookup of a single entity. Faster and more precise than keyword search "
    "when you know the exact name. Returns a compact {id, name, type, category} summary.",
    {
        "model_type": {
            "type": "string", "enum": _MODEL_TYPES,
            "description": "Entity type to look up",
        },
        "name": {"type": "string", "description": "Exact entity name"},
    },
    required=["model_type", "name"],
    output={
        "entity": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "type": {"type": "string"},
                "category": {"type": ["string", "null"]},
            },
            "description": "Compact summary of the matched entity.",
        }
    },
))

# ---------------------------------------------------------------------------
# Phase 2: Life Cycle Inventory (writes)
# ---------------------------------------------------------------------------

_register(_tool(
    "create_product_flow",
    "Create a new product flow (Mass property, kg unit). Use to define the product "
    "under study or intermediate products. WRITE: blocked when OPENLCA_READ_ONLY=true.",
    {
        "name": {"type": "string", "description": "Product flow name"},
        "description": {"type": "string", "description": "Optional description"},
    },
    required=["name"],
    output={
        "flow": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "description": {"type": ["string", "null"]},
            },
            "description": "The newly created product flow.",
        }
    },
    read_only=False,
    destructive=False,
    idempotent=False,
))

_register(_tool(
    "create_process",
    "Create a unit process with inputs and outputs. Each exchange: flow_id (id "
    "preferred, name accepted), amount, is_input, optional is_quantitative_reference, "
    "optional provider_id. WRITE: blocked when OPENLCA_READ_ONLY=true.",
    {
        "name": {"type": "string", "description": "Process name"},
        "description": {"type": "string", "description": "Process description"},
        "exchanges": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "flow_id": {"type": "string", "description": "Flow id (preferred) or name"},
                    "amount": {"type": "number", "description": "Amount in kg"},
                    "is_input": {"type": "boolean", "description": "True if input"},
                    "is_quantitative_reference": {
                        "type": "boolean", "description": "True if main reference output"},
                    "provider_id": {"type": "string", "description": "Optional provider process id"},
                },
                "required": ["flow_id", "amount", "is_input"],
            },
            "description": "Inputs and outputs",
        },
    },
    required=["name", "exchanges"],
    output={
        "process": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "description": {"type": ["string", "null"]},
            },
            "description": "The newly created unit process.",
        }
    },
    read_only=False,
    destructive=False,
    idempotent=False,
))

_register(_tool(
    "create_product_system",
    "Create a product system from a process (auto-links providers). Returns the product "
    "system id for calculations. Provide process_id (preferred) or process_name. "
    "WRITE: blocked when OPENLCA_READ_ONLY=true.",
    {
        "process_id": {"type": "string", "description": "Root process id"},
        "process_name": {"type": "string", "description": "Root process name (if id not provided)"},
    },
    output={
        "product_system": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
            },
            "description": "The created product system (use its id for calculations).",
        }
    },
    read_only=False,
    destructive=False,
    idempotent=False,
))

# ---------------------------------------------------------------------------
# Phase 3: Life Cycle Impact Assessment
# ---------------------------------------------------------------------------

_register(_tool(
    "calculate_impacts",
    "Calculate environmental impacts for a product system. Returns a result_id, a "
    "compact ResultSummary (top impacts, suggested next actions), the full impact list, "
    "and any consistency warnings. IMPORTANT: call dispose_result when done with the result_id.",
    {
        "system_id": {"type": "string", "description": "Product system id"},
        "system_name": {"type": "string", "description": "Product system name (if id not provided)"},
        "method_id": {"type": "string", "description": "Impact method id"},
        "method_keywords": {
            "type": "array", "items": {"type": "string"},
            "description": "Keywords to find the method (if id not provided)",
        },
        "amount": {"type": "number", "description": "Reference amount (default 1.0)", "default": 1.0},
    },
    output={
        "result_id": {
            "type": "string",
            "description": "Handle for follow-up tools; pass to dispose_result when done.",
        },
        "summary": {"type": "object", "description": "Compact ResultSummary (top impacts, next actions)."},
        "impacts": _arr(_IMPACT),
        "warnings": _arr({"type": "string"}),
        "context": {"type": "object", "description": "Calculation context (system, method, unit)."},
        "message": {"type": "string"},
    },
))

_register(_tool(
    "get_inventory_results",
    "Get the life cycle inventory (elementary/environmental flows) for a calculated "
    "result. Requires result_id from calculate_impacts. direction filters input/output/both.",
    {
        "result_id": {"type": "string", "description": "Result id from calculate_impacts"},
        "direction": {
            "type": "string", "enum": ["input", "output", "both"],
            "description": "Flow direction filter (default both)", "default": "both",
        },
    },
    required=["result_id"],
    output={
        "result_id": {"type": "string"},
        "count": {"type": "integer"},
        "inventory": _arr({
            "type": "object",
            "properties": {
                "name": {"type": ["string", "null"]},
                "flow": _REF,
                "amount": {"type": ["number", "null"]},
                "unit": {"type": ["string", "null"]},
                "is_input": {"type": ["boolean", "null"]},
                "location": {"type": ["string", "null"]},
            },
        }),
    },
))

_register(_tool(
    "get_total_requirements",
    "Get the total requirements (scaled technology flows) of a calculated product "
    "system: which processes run and at what amount. Requires result_id.",
    {"result_id": {"type": "string", "description": "Result id from calculate_impacts"}},
    required=["result_id"],
    output={
        "result_id": {"type": "string"},
        "count": {"type": "integer"},
        "requirements": _arr({
            "type": "object",
            "properties": {
                "process": {"type": ["string", "null"]},
                "provider": _REF,
                "flow": {"type": ["string", "null"]},
                "amount": {"type": ["number", "null"]},
            },
        }),
    },
))

_register(_tool(
    "get_normalized_impacts",
    "Get normalized impact results (relative to the method's normalization set). "
    "Requires result_id. Empty if the method has no normalization set.",
    {"result_id": {"type": "string", "description": "Result id from calculate_impacts"}},
    required=["result_id"],
    output={
        "result_id": {"type": "string"},
        "normalized": _arr(_IMPACT),
    },
))

_register(_tool(
    "get_weighted_impacts",
    "Get weighted impact results (after normalization + weighting). Requires result_id. "
    "Empty if the method has no weighting set.",
    {"result_id": {"type": "string", "description": "Result id from calculate_impacts"}},
    required=["result_id"],
    output={
        "result_id": {"type": "string"},
        "weighted": _arr(_IMPACT),
    },
))

# ---------------------------------------------------------------------------
# Phase 4: Interpretation
# ---------------------------------------------------------------------------

_register(_tool(
    "analyze_contributions",
    "Identify which processes (or flows) contribute most to an impact category — the "
    "hotspots. Requires result_id and impact_category_id (from calculate_impacts' impacts). "
    "Returns top contributors with share and absolute amount.",
    {
        "result_id": {"type": "string", "description": "Result id from calculate_impacts"},
        "impact_category_id": {"type": "string", "description": "Impact category id to analyze"},
        "n": {"type": "integer", "description": "Number of top contributors", "default": 10},
        "contribution_type": {
            "type": "string", "enum": ["process", "flow"],
            "description": "Contribution dimension (default process)", "default": "process",
        },
        "min_share": {"type": "number", "description": "Minimum share 0-1", "default": 0.0},
    },
    required=["result_id", "impact_category_id"],
    output={
        "result_id": {"type": "string"},
        "impact_category_id": {"type": "string"},
        "contribution_type": {"type": "string", "enum": ["process", "flow"]},
        "count": {"type": "integer"},
        "contributors": _arr({
            "type": "object",
            "properties": {
                "name": {"type": ["string", "null"]},
                "amount": {"type": ["number", "null"]},
                "share": {"type": ["number", "null"]},
                "ref": _REF,
            },
        }),
    },
))

_register(_tool(
    "get_contribution_tree",
    "Build an upstream contribution (hotspot) tree for an impact category: nested "
    "process nodes with amount, direct contribution, and share. Requires result_id and "
    "impact_category_id. Pruned by max_depth and min_share.",
    {
        "result_id": {"type": "string", "description": "Result id from calculate_impacts"},
        "impact_category_id": {"type": "string", "description": "Impact category id"},
        "max_depth": {"type": "integer", "description": "Max tree depth", "default": 3},
        "min_share": {"type": "number", "description": "Prune branches below this share", "default": 0.01},
    },
    required=["result_id", "impact_category_id"],
    output={
        "result_id": {"type": "string"},
        "impact_category_id": {"type": "string"},
        "tree": _arr({
            "type": "object",
            "description": "Recursive contribution node: name, amount, direct, share, ref, children[].",
            "properties": {
                "name": {"type": ["string", "null"]},
                "amount": {"type": ["number", "null"]},
                "direct": {"type": ["number", "null"]},
                "share": {"type": ["number", "null"]},
                "ref": _REF,
                "children": {"type": "array"},
            },
        }),
    },
))

_register(_tool(
    "get_sankey",
    "Get Sankey-graph data (nodes + edges) for an impact category, suitable for "
    "visualization. Requires result_id and impact_category_id.",
    {
        "result_id": {"type": "string", "description": "Result id from calculate_impacts"},
        "impact_category_id": {"type": "string", "description": "Impact category id"},
        "max_nodes": {"type": "integer", "description": "Max graph nodes", "default": 50},
        "min_share": {"type": "number", "description": "Minimum node share", "default": 0.0},
    },
    required=["result_id", "impact_category_id"],
    output={
        "result_id": {"type": "string"},
        "impact_category_id": {"type": "string"},
        "sankey": {"type": "object", "description": "Graph data with nodes and edges for visualization."},
    },
))

_register(_tool(
    "compare_systems",
    "Compare two product systems on the same impact method. Returns per-category "
    "system1, system2, difference, and percent change. Runs and disposes both "
    "calculations internally (no result_id needed).",
    {
        "system1_id": {"type": "string", "description": "First product system id"},
        "system2_id": {"type": "string", "description": "Second product system id"},
        "method_id": {"type": "string", "description": "Impact method id"},
        "method_keywords": {
            "type": "array", "items": {"type": "string"},
            "description": "Keywords to find the method (if id not provided)",
        },
        "amount": {"type": "number", "description": "Reference amount (default 1.0)", "default": 1.0},
    },
    required=["system1_id", "system2_id"],
    output={
        "comparison": {
            "type": "object",
            "description": "Per-category system1, system2, difference, and percent change.",
        }
    },
))

_register(_tool(
    "run_monte_carlo",
    "Run Monte Carlo uncertainty analysis. Returns per-impact statistics (mean, std, "
    "CV, percentiles). Can be slow for large systems / high iteration counts.",
    {
        "system_id": {"type": "string", "description": "Product system id"},
        "method_id": {"type": "string", "description": "Impact method id"},
        "method_keywords": {
            "type": "array", "items": {"type": "string"},
            "description": "Keywords to find the method (if id not provided)",
        },
        "iterations": {"type": "integer", "description": "Iterations", "default": 100},
    },
    required=["system_id"],
    output={
        "count": {"type": "integer"},
        "uncertainty": _arr({
            "type": "object",
            "properties": {
                "impact": {"type": "string"},
                "mean": {"type": ["number", "null"]},
                "std": {"type": ["number", "null"]},
                "median": {"type": ["number", "null"]},
                "percentile_5": {"type": ["number", "null"]},
                "percentile_95": {"type": ["number", "null"]},
                "cv": {"type": ["number", "null"]},
                "iterations": {"type": "integer"},
            },
        }),
    },
))

_register(_tool(
    "run_scenario_analysis",
    "Vary a single parameter over a list of values and report impacts for each value. "
    "Useful for sensitivity analysis.",
    {
        "system_id": {"type": "string", "description": "Product system id"},
        "method_id": {"type": "string", "description": "Impact method id"},
        "method_keywords": {
            "type": "array", "items": {"type": "string"},
            "description": "Keywords to find the method (if id not provided)",
        },
        "parameter_name": {"type": "string", "description": "Parameter to vary"},
        "values": {
            "type": "array", "items": {"type": "number"},
            "description": "Parameter values to evaluate",
        },
    },
    required=["system_id", "parameter_name", "values"],
    output={
        "parameter": {"type": "string", "description": "The parameter that was varied"},
        "scenarios": {
            "type": "object",
            "description": "Map of parameter value (as string) -> list of impact rows.",
        },
    },
))

_register(_tool(
    "export_results",
    "Export results to a file. With result_id: export its impacts to CSV (format=csv) "
    "or an Excel workbook (format=excel). With data + kind=comparison: export a "
    "compare_systems result to CSV. filepath is the output path on the server host.",
    {
        "result_id": {"type": "string", "description": "Result id to export (impacts)"},
        "data": {"type": "object", "description": "Inline data (impacts list or comparison dict)"},
        "kind": {
            "type": "string", "enum": ["impacts", "comparison"],
            "description": "What 'data' holds (default impacts)", "default": "impacts",
        },
        "filepath": {"type": "string", "description": "Output file path"},
        "format": {
            "type": "string", "enum": ["csv", "excel"],
            "description": "Output format (default csv)", "default": "csv",
        },
    },
    required=["filepath"],
    output={
        "exported": {"type": "boolean"},
        "filepath": {"type": "string"},
        "format": {"type": "string", "enum": ["csv", "excel"]},
    },
    read_only=False,
    destructive=False,
    idempotent=False,
))

# ---------------------------------------------------------------------------
# Utilities: result lifecycle
# ---------------------------------------------------------------------------

_register(_tool(
    "dispose_result",
    "Dispose a calculation result to free server memory. Always call this when finished "
    "with a result_id from calculate_impacts.",
    {"result_id": {"type": "string", "description": "Result id to dispose"}},
    required=["result_id"],
    output={
        "disposed": {"type": "string", "description": "The disposed result_id"},
        "message": {"type": "string"},
    },
    read_only=False,
    destructive=False,
))

_register(_tool(
    "dispose_all_results",
    "Dispose every tracked calculation result. Useful for cleanup at the end of a session.",
    {},
    output={
        "disposed_count": {"type": "integer", "description": "Number of results disposed"},
    },
    read_only=False,
    destructive=False,
))
