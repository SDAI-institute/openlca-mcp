"""
Async tool handlers for the openLCA MCP server.

Each handler takes the tool ``arguments`` dict and returns a single JSON
``TextContent`` via the helpers in :mod:`src.responses`. ``TOOL_HANDLERS`` maps
tool name -> handler and is the second half of the single-source-of-truth pair
(with ``tool_defs.TOOLS``); the server only advertises tools that appear in both.
"""

import logging
from typing import Any, Dict, List, Optional

import olca_schema as o
from mcp.types import TextContent

from openlca_ipc import (
    ResultSummary,
    EntitySummary,
    CalculationContext,
    health_check as _health_check,
    check_result_consistency,
)
from openlca_ipc.agent.errors import (
    ImpactMethodNotFound,
    SystemNotFound,
    EntityNotFound,
    CalculationFailed,
    WriteBlocked,
)

from . import responses
from .lca_client import get_client, read_only_enabled
from .result_store import store

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared resolution helpers
# ---------------------------------------------------------------------------

def _require_writable(operation: str) -> None:
    """Raise WriteBlocked if the server is configured read-only."""
    if read_only_enabled():
        raise WriteBlocked(operation=operation)


def _resolve_method(client, arguments: dict):
    """Resolve an impact method from method_id or method_keywords, or raise."""
    if arguments.get("method_id"):
        method = client.client.get(o.ImpactMethod, arguments["method_id"])
        if not method:
            raise ImpactMethodNotFound(
                message=f"No impact method with id '{arguments['method_id']}'."
            )
        return method
    if arguments.get("method_keywords"):
        method = client.search.find_impact_method(arguments["method_keywords"])
        if not method:
            raise ImpactMethodNotFound(
                message=f"No impact method matched {arguments['method_keywords']}."
            )
        return method
    raise ImpactMethodNotFound(
        message="Provide either method_id or method_keywords."
    )


def _resolve_system_ref(client, arguments: dict) -> o.Ref:
    """Resolve a product-system Ref from system_id or system_name, or raise."""
    if arguments.get("system_id"):
        return o.Ref(id=arguments["system_id"])
    name = arguments.get("system_name")
    if name:
        ref = client.search.get_by_name(o.ProductSystem, name)
        if ref is not None:
            return ref
        # Fall back to a descriptor scan by exact name.
        for desc in client.client.get_descriptors(o.ProductSystem):
            if desc.name == name:
                return desc
        raise SystemNotFound(message=f"No product system named '{name}'.")
    raise SystemNotFound(message="Provide either system_id or system_name.")


def _impact_to_dict(impact: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a library impact dict to a JSON-ready shape with category_id."""
    category = impact.get("category")
    return {
        "name": impact.get("name"),
        "category": responses.ref_to_dict(category),
        "category_id": getattr(category, "id", None),
        "amount": impact.get("amount"),
        "unit": impact.get("unit"),
    }


def _impacts_payload(impacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [_impact_to_dict(i) for i in impacts]


def _stored_or_raise(result_id: str):
    """Fetch a StoredResult or raise EntityNotFound."""
    stored = store.get(result_id)
    if stored is None:
        raise EntityNotFound(
            message=f"Unknown result_id '{result_id}'. Call calculate_impacts first."
        )
    return stored


def _category_ref(stored, impact_category_id: str) -> o.Ref:
    """Find the impact-category Ref on a stored result by id, or raise."""
    for impact in stored.impacts:
        category = impact.get("category")
        if getattr(category, "id", None) == impact_category_id:
            return category
    raise EntityNotFound(
        message=f"Impact category '{impact_category_id}' not in result "
        f"'{stored.result_id}'."
    )


# ---------------------------------------------------------------------------
# Utilities / connection
# ---------------------------------------------------------------------------

async def handle_test_connection(arguments: dict) -> List[TextContent]:
    try:
        client = get_client()
        return responses.success(
            {"connected": client.test_connection(), "port": client.port}
        )
    except Exception as exc:
        logger.error("test_connection failed: %s", exc, exc_info=True)
        return responses.error(exc, error_code="CONNECTION_FAILED")


async def handle_health_check(arguments: dict) -> List[TextContent]:
    try:
        client = get_client()
        count_entities = arguments.get("count_entities", True)
        report = _health_check(client, count_entities=count_entities)
        return responses.success({"health": report})
    except Exception as exc:
        logger.error("health_check failed: %s", exc, exc_info=True)
        return responses.error(exc, error_code="CONNECTION_FAILED")


# ---------------------------------------------------------------------------
# Phase 1: Goal & Scope
# ---------------------------------------------------------------------------

async def handle_search_flows(arguments: dict) -> List[TextContent]:
    try:
        client = get_client()
        flow_type = None
        if arguments.get("flow_type"):
            flow_type = getattr(o.FlowType, arguments["flow_type"])
        flows = client.search.find_flows(
            arguments["keywords"], arguments.get("max_results", 10), flow_type
        )
        results = [responses.ref_to_dict(f) for f in flows]
        return responses.success({"count": len(results), "flows": results})
    except Exception as exc:
        logger.error("search_flows failed: %s", exc, exc_info=True)
        return responses.error(exc)


async def handle_search_processes(arguments: dict) -> List[TextContent]:
    try:
        client = get_client()
        processes = client.search.find_processes(
            arguments["keywords"], arguments.get("max_results", 10)
        )
        results = [responses.ref_to_dict(p) for p in processes]
        return responses.success({"count": len(results), "processes": results})
    except Exception as exc:
        logger.error("search_processes failed: %s", exc, exc_info=True)
        return responses.error(exc)


async def handle_search_impact_methods(arguments: dict) -> List[TextContent]:
    try:
        client = get_client()
        method = client.search.find_impact_method(arguments["keywords"])
        if not method:
            raise ImpactMethodNotFound(
                message=f"No impact method matched {arguments['keywords']}."
            )
        return responses.success(
            {
                "method": {
                    "id": method.id,
                    "name": method.name,
                    "categories": [
                        {"id": c.id, "name": c.name}
                        for c in (method.impact_categories or [])
                    ],
                }
            }
        )
    except Exception as exc:
        logger.error("search_impact_methods failed: %s", exc, exc_info=True)
        return responses.error(exc)


async def handle_find_providers(arguments: dict) -> List[TextContent]:
    try:
        client = get_client()
        if arguments.get("flow_id"):
            flow_ref = o.Ref(id=arguments["flow_id"])
        elif arguments.get("flow_name"):
            flows = client.search.find_flows([arguments["flow_name"]], max_results=1)
            if not flows:
                raise EntityNotFound(
                    message=f"Flow not found: {arguments['flow_name']}."
                )
            flow_ref = flows[0]
        else:
            raise EntityNotFound(message="Provide either flow_id or flow_name.")
        providers = client.search.find_providers(flow_ref)
        results = [responses.ref_to_dict(p) for p in providers]
        return responses.success({"count": len(results), "providers": results})
    except Exception as exc:
        logger.error("find_providers failed: %s", exc, exc_info=True)
        return responses.error(exc)


async def handle_get_entity_by_name(arguments: dict) -> List[TextContent]:
    try:
        client = get_client()
        model_type = arguments["model_type"]
        model_cls = getattr(o, model_type, None)
        if model_cls is None:
            raise EntityNotFound(message=f"Unknown model_type '{model_type}'.")
        ref = client.search.get_by_name(model_cls, arguments["name"])
        if ref is None:
            raise EntityNotFound(
                message=f"No {model_type} named '{arguments['name']}'."
            )
        return responses.success(
            {"entity": EntitySummary.from_ref(ref, type_name=model_type).to_dict()}
        )
    except Exception as exc:
        logger.error("get_entity_by_name failed: %s", exc, exc_info=True)
        return responses.error(exc)


# ---------------------------------------------------------------------------
# Phase 2: Life Cycle Inventory (writes)
# ---------------------------------------------------------------------------

async def handle_create_product_flow(arguments: dict) -> List[TextContent]:
    try:
        _require_writable("create_product_flow")
        client = get_client()
        flow = client.data.create_product_flow(
            arguments["name"], arguments.get("description", "")
        )
        return responses.success(
            {"flow": {"id": flow.id, "name": flow.name, "description": flow.description}}
        )
    except Exception as exc:
        logger.error("create_product_flow failed: %s", exc, exc_info=True)
        return responses.error(exc)


async def handle_create_process(arguments: dict) -> List[TextContent]:
    try:
        _require_writable("create_process")
        client = get_client()
        exchanges = []
        for ex_data in arguments["exchanges"]:
            flow_ref = _resolve_flow_ref(client, ex_data["flow_id"])
            provider = None
            if ex_data.get("provider_id"):
                provider = o.Ref(id=ex_data["provider_id"])
            exchanges.append(
                client.data.create_exchange(
                    flow_ref,
                    ex_data["amount"],
                    ex_data["is_input"],
                    ex_data.get("is_quantitative_reference", False),
                    provider,
                )
            )
        process = client.data.create_process(
            arguments["name"], arguments.get("description", ""), exchanges
        )
        return responses.success(
            {
                "process": {
                    "id": process.id,
                    "name": process.name,
                    "description": process.description,
                }
            }
        )
    except Exception as exc:
        logger.error("create_process failed: %s", exc, exc_info=True)
        return responses.error(exc)


def _resolve_flow_ref(client, flow_id: str) -> o.Ref:
    """Resolve an exchange flow id-first, then by exact/keyword name search."""
    # Treat as an id first (the precise case).
    try:
        flow = client.client.get(o.Flow, flow_id)
    except Exception:
        flow = None
    if flow is not None:
        return o.Ref(id=flow.id, name=flow.name, ref_type=o.RefType.Flow)
    # Fall back to a name search.
    matches = client.search.find_flows([flow_id], max_results=1)
    if matches:
        return matches[0]
    # Last resort: assume it is an id the server will resolve at link time.
    return o.Ref(id=flow_id)


async def handle_create_product_system(arguments: dict) -> List[TextContent]:
    try:
        _require_writable("create_product_system")
        client = get_client()
        if arguments.get("process_id"):
            process_ref = o.Ref(id=arguments["process_id"])
        elif arguments.get("process_name"):
            procs = client.search.find_processes(
                [arguments["process_name"]], max_results=1
            )
            if not procs:
                raise EntityNotFound(
                    message=f"Process not found: {arguments['process_name']}."
                )
            process_ref = procs[0]
        else:
            raise EntityNotFound(message="Provide either process_id or process_name.")

        system = client.systems.create_product_system(process_ref)
        if system is None:
            raise CalculationFailed(
                message="Could not create product system (see server logs)."
            )
        return responses.success(
            {"product_system": {"id": system.id, "name": system.name}}
        )
    except Exception as exc:
        logger.error("create_product_system failed: %s", exc, exc_info=True)
        return responses.error(exc)


# ---------------------------------------------------------------------------
# Phase 3: Life Cycle Impact Assessment
# ---------------------------------------------------------------------------

async def handle_calculate_impacts(arguments: dict) -> List[TextContent]:
    try:
        client = get_client()
        system_ref = _resolve_system_ref(client, arguments)
        method = _resolve_method(client, arguments)
        amount = arguments.get("amount", 1.0)

        result = client.calculate.simple_calculation(system_ref, method, amount)
        impacts = client.results.get_total_impacts(result)
        warnings = check_result_consistency(result)

        context = CalculationContext.capture(
            server_port=getattr(client, "port", None),
            product_system=system_ref,
            impact_method=method,
            functional_unit={"amount": amount},
        )
        stored = store.add(
            result,
            impacts=impacts,
            context=context.to_dict(),
            system_ref=system_ref,
            method=method,
        )
        summary = ResultSummary.from_impacts(
            impacts,
            result_id=stored.result_id,
            product_system=system_ref,
            impact_method=method,
            functional_unit={"amount": amount},
            warnings=warnings,
        )
        return responses.success(
            {
                "result_id": stored.result_id,
                "summary": summary.to_dict(),
                "impacts": _impacts_payload(impacts),
                "warnings": warnings,
                "context": stored.context,
                "message": "Call dispose_result with this result_id when finished.",
            }
        )
    except Exception as exc:
        logger.error("calculate_impacts failed: %s", exc, exc_info=True)
        code = exc.error_code if hasattr(exc, "error_code") else "CALCULATION_FAILED"
        return responses.error(exc, error_code=code)


async def handle_get_inventory_results(arguments: dict) -> List[TextContent]:
    try:
        stored = _stored_or_raise(arguments["result_id"])
        client = get_client()
        direction = arguments.get("direction", "both")
        inventory = client.results.get_inventory(stored.result, direction=direction)
        flows = [
            {
                "name": f.get("name"),
                "flow": responses.ref_to_dict(f.get("flow")),
                "amount": f.get("amount"),
                "unit": f.get("unit"),
                "is_input": f.get("is_input"),
                "location": f.get("location"),
            }
            for f in inventory
        ]
        return responses.success(
            {"result_id": stored.result_id, "count": len(flows), "inventory": flows}
        )
    except Exception as exc:
        logger.error("get_inventory_results failed: %s", exc, exc_info=True)
        return responses.error(exc)


async def handle_get_total_requirements(arguments: dict) -> List[TextContent]:
    try:
        stored = _stored_or_raise(arguments["result_id"])
        client = get_client()
        reqs = client.results.get_total_requirements(stored.result)
        rows = [
            {
                "process": r.get("process"),
                "provider": responses.ref_to_dict(r.get("provider")),
                "flow": r.get("flow"),
                "amount": r.get("amount"),
            }
            for r in reqs
        ]
        return responses.success(
            {"result_id": stored.result_id, "count": len(rows), "requirements": rows}
        )
    except Exception as exc:
        logger.error("get_total_requirements failed: %s", exc, exc_info=True)
        return responses.error(exc)


async def handle_get_normalized_impacts(arguments: dict) -> List[TextContent]:
    try:
        stored = _stored_or_raise(arguments["result_id"])
        client = get_client()
        impacts = client.results.get_normalized_impacts(stored.result)
        return responses.success(
            {"result_id": stored.result_id, "normalized": _impacts_payload(impacts)}
        )
    except Exception as exc:
        logger.error("get_normalized_impacts failed: %s", exc, exc_info=True)
        return responses.error(exc)


async def handle_get_weighted_impacts(arguments: dict) -> List[TextContent]:
    try:
        stored = _stored_or_raise(arguments["result_id"])
        client = get_client()
        impacts = client.results.get_weighted_impacts(stored.result)
        return responses.success(
            {"result_id": stored.result_id, "weighted": _impacts_payload(impacts)}
        )
    except Exception as exc:
        logger.error("get_weighted_impacts failed: %s", exc, exc_info=True)
        return responses.error(exc)


# ---------------------------------------------------------------------------
# Phase 4: Interpretation
# ---------------------------------------------------------------------------

async def handle_analyze_contributions(arguments: dict) -> List[TextContent]:
    try:
        stored = _stored_or_raise(arguments["result_id"])
        client = get_client()
        category = _category_ref(stored, arguments["impact_category_id"])
        n = arguments.get("n", 10)
        ctype = arguments.get("contribution_type", "process")
        contributors = client.contributions.get_top_contributors(
            stored.result, category, n=n, contribution_type=ctype
        )
        min_share = arguments.get("min_share", 0.0)
        items = [
            responses.contribution_to_dict(c)
            for c in contributors
            if not (min_share and abs(c.share) < min_share)
        ]
        return responses.success(
            {
                "result_id": stored.result_id,
                "impact_category_id": arguments["impact_category_id"],
                "contribution_type": ctype,
                "count": len(items),
                "contributors": items,
            }
        )
    except Exception as exc:
        logger.error("analyze_contributions failed: %s", exc, exc_info=True)
        return responses.error(exc)


async def handle_get_contribution_tree(arguments: dict) -> List[TextContent]:
    try:
        stored = _stored_or_raise(arguments["result_id"])
        client = get_client()
        category = _category_ref(stored, arguments["impact_category_id"])
        tree = client.contributions.get_contribution_tree(
            stored.result,
            category,
            max_depth=arguments.get("max_depth", 3),
            min_share=arguments.get("min_share", 0.01),
        )
        nodes = [responses.tree_to_dict(n) for n in tree]
        return responses.success(
            {
                "result_id": stored.result_id,
                "impact_category_id": arguments["impact_category_id"],
                "tree": nodes,
            }
        )
    except Exception as exc:
        logger.error("get_contribution_tree failed: %s", exc, exc_info=True)
        return responses.error(exc)


async def handle_get_sankey(arguments: dict) -> List[TextContent]:
    try:
        stored = _stored_or_raise(arguments["result_id"])
        client = get_client()
        category = _category_ref(stored, arguments["impact_category_id"])
        graph = client.results.get_sankey(
            stored.result,
            category,
            max_nodes=arguments.get("max_nodes", 50),
            min_share=arguments.get("min_share", 0.0),
        )
        return responses.success(
            {
                "result_id": stored.result_id,
                "impact_category_id": arguments["impact_category_id"],
                "sankey": graph,
            }
        )
    except Exception as exc:
        logger.error("get_sankey failed: %s", exc, exc_info=True)
        return responses.error(exc)


async def handle_compare_systems(arguments: dict) -> List[TextContent]:
    try:
        client = get_client()
        method = _resolve_method(client, arguments)
        comparison = client.calculate.compare_systems(
            o.Ref(id=arguments["system1_id"]),
            o.Ref(id=arguments["system2_id"]),
            method,
            arguments.get("amount", 1.0),
        )
        return responses.success({"comparison": comparison})
    except Exception as exc:
        logger.error("compare_systems failed: %s", exc, exc_info=True)
        return responses.error(exc)


async def handle_run_monte_carlo(arguments: dict) -> List[TextContent]:
    try:
        client = get_client()
        method = _resolve_method(client, arguments)
        results = client.uncertainty.run_monte_carlo(
            o.Ref(id=arguments["system_id"]),
            method,
            iterations=arguments.get("iterations", 100),
        )
        stats = [responses.uncertainty_to_dict(name, ur) for name, ur in results.items()]
        return responses.success({"count": len(stats), "uncertainty": stats})
    except Exception as exc:
        logger.error("run_monte_carlo failed: %s", exc, exc_info=True)
        return responses.error(exc)


async def handle_run_scenario_analysis(arguments: dict) -> List[TextContent]:
    try:
        client = get_client()
        method = _resolve_method(client, arguments)
        scenarios = client.parameters.run_scenario_analysis(
            o.Ref(id=arguments["system_id"]),
            method,
            arguments["parameter_name"],
            arguments["values"],
        )
        out = {
            str(value): _impacts_payload(impacts)
            for value, impacts in scenarios.items()
        }
        return responses.success(
            {"parameter": arguments["parameter_name"], "scenarios": out}
        )
    except Exception as exc:
        logger.error("run_scenario_analysis failed: %s", exc, exc_info=True)
        return responses.error(exc)


async def handle_export_results(arguments: dict) -> List[TextContent]:
    try:
        client = get_client()
        filepath = arguments["filepath"]
        fmt = arguments.get("format", "csv")

        if arguments.get("result_id"):
            stored = _stored_or_raise(arguments["result_id"])
            if fmt == "excel":
                ok = client.export.export_to_excel(stored.result, filepath)
            else:
                ok = client.export.export_impacts_to_csv(stored.impacts, filepath)
        elif arguments.get("data") is not None:
            data = arguments["data"]
            if arguments.get("kind") == "comparison":
                ok = client.export.export_comparison_to_csv(data, filepath)
            else:
                ok = client.export.export_impacts_to_csv(data, filepath)
        else:
            raise EntityNotFound(message="Provide either result_id or data to export.")

        if not ok:
            raise CalculationFailed(message=f"Export to '{filepath}' failed.")
        return responses.success({"exported": True, "filepath": filepath, "format": fmt})
    except Exception as exc:
        logger.error("export_results failed: %s", exc, exc_info=True)
        return responses.error(exc)


# ---------------------------------------------------------------------------
# Utilities: result lifecycle
# ---------------------------------------------------------------------------

async def handle_dispose_result(arguments: dict) -> List[TextContent]:
    try:
        result_id = arguments["result_id"]
        if store.dispose(result_id):
            return responses.success(
                {"disposed": result_id, "message": "Result disposed."}
            )
        raise EntityNotFound(message=f"Unknown result_id '{result_id}'.")
    except Exception as exc:
        logger.error("dispose_result failed: %s", exc, exc_info=True)
        return responses.error(exc)


async def handle_dispose_all_results(arguments: dict) -> List[TextContent]:
    try:
        count = store.dispose_all()
        return responses.success({"disposed_count": count})
    except Exception as exc:
        logger.error("dispose_all_results failed: %s", exc, exc_info=True)
        return responses.error(exc)


# ---------------------------------------------------------------------------
# Name -> handler map (single source of truth, paired with tool_defs.TOOLS)
# ---------------------------------------------------------------------------

TOOL_HANDLERS = {
    "test_connection": handle_test_connection,
    "health_check": handle_health_check,
    "search_flows": handle_search_flows,
    "search_processes": handle_search_processes,
    "search_impact_methods": handle_search_impact_methods,
    "find_providers": handle_find_providers,
    "get_entity_by_name": handle_get_entity_by_name,
    "create_product_flow": handle_create_product_flow,
    "create_process": handle_create_process,
    "create_product_system": handle_create_product_system,
    "calculate_impacts": handle_calculate_impacts,
    "get_inventory_results": handle_get_inventory_results,
    "get_total_requirements": handle_get_total_requirements,
    "get_normalized_impacts": handle_get_normalized_impacts,
    "get_weighted_impacts": handle_get_weighted_impacts,
    "analyze_contributions": handle_analyze_contributions,
    "get_contribution_tree": handle_get_contribution_tree,
    "get_sankey": handle_get_sankey,
    "compare_systems": handle_compare_systems,
    "run_monte_carlo": handle_run_monte_carlo,
    "run_scenario_analysis": handle_run_scenario_analysis,
    "export_results": handle_export_results,
    "dispose_result": handle_dispose_result,
    "dispose_all_results": handle_dispose_all_results,
}
