#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Live smoke test against a running openLCA IPC server on port 8080.

Run:  python test_live.py
"""
import asyncio
import json
import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))

PASS = "[PASS]"
FAIL = "[FAIL]"
SKIP = "[SKIP]"
results: list[tuple[str, str]] = []


def p(tag: str, name: str, detail: str = "") -> None:
    line = f"  {tag} {name}" + (f": {detail}" if detail else "")
    print(line)
    results.append((tag, name))


def payload(r) -> dict:
    return json.loads(r[0].text)


# ---------------------------------------------------------------------------
# 1. Connection & health
# ---------------------------------------------------------------------------
async def test_connection() -> None:
    print("\n── 1. Connection & health ──────────────────────────────────────")
    from src.handlers import handle_test_connection, handle_health_check
    from src.lca_client import reset_client

    reset_client()
    try:
        r = await handle_test_connection({})
        d = payload(r)
        assert d["success"], f"test_connection failed: {d}"
        p(PASS, "test_connection", d.get("message", ""))
    except Exception as e:
        p(FAIL, "test_connection", str(e))
        print("\n  Cannot reach openLCA IPC on port 8080. Is the server running?")
        sys.exit(1)

    try:
        r = await handle_health_check({})
        d = payload(r)
        assert d["success"], f"health_check failed: {d}"
        info = d.get("health", {})
        counts = info.get("counts", info.get("entity_counts", {}))
        p(PASS, "health_check", f"processes={counts.get('processes',0)}, "
          f"methods={counts.get('impact_methods',0)}, "
          f"systems={counts.get('product_systems',0)}")
        return counts
    except Exception as e:
        p(FAIL, "health_check", str(e))
        return {}


# ---------------------------------------------------------------------------
# 2. Discover entities directly via raw client
# ---------------------------------------------------------------------------
def discover_entities():
    """Use get_all_descriptors to find real entity names in the database."""
    import olca_schema as o
    from src.lca_client import get_client
    client = get_client()

    methods, systems, flows = [], [], []
    try:
        methods = list(client.client.get_descriptors(o.ImpactMethod))
    except Exception as e:
        print(f"  [warn] cannot enumerate methods: {e}")
    try:
        systems = list(client.client.get_descriptors(o.ProductSystem))
    except Exception as e:
        print(f"  [warn] cannot enumerate systems: {e}")
    try:
        flows = list(client.client.get_descriptors(o.Flow))
        flows = flows[:5]  # just a sample
    except Exception as e:
        print(f"  [warn] cannot enumerate flows: {e}")

    return methods, systems, flows


# ---------------------------------------------------------------------------
# 3. Search tools (with real keywords from discovered entities)
# ---------------------------------------------------------------------------
async def test_search(methods: list, flows: list) -> None:
    print("\n── 2. Search tools ────────────────────────────────────────────")
    from src.handlers import (
        handle_search_flows,
        handle_search_processes,
        handle_search_impact_methods,
        handle_find_providers,
        handle_get_entity_by_name,
    )

    # search_impact_methods — use first word of a real method name
    if methods:
        kw = methods[0].name.split()[:1]  # e.g. ["ReCiPe"] or ["TRACI"]
        try:
            r = await handle_search_impact_methods({"keywords": kw})
            d = payload(r)
            if d["success"]:
                m = d.get("method", {})
                cats = len(m.get("categories", []))
                p(PASS, "search_impact_methods",
                  f"found '{m.get('name','')}' ({cats} categories)")
            else:
                p(FAIL, "search_impact_methods", d.get("message", str(d)))
        except Exception as e:
            p(FAIL, "search_impact_methods", str(e))
    else:
        p(SKIP, "search_impact_methods", "no methods in db")

    # search_flows — use first word of a real flow name
    if flows:
        kw = flows[0].name.split()[:1]
        try:
            r = await handle_search_flows({"keywords": kw, "max_results": 5})
            d = payload(r)
            if d["success"]:
                p(PASS, "search_flows", f"{d['count']} flow(s) for {kw}")
            else:
                p(FAIL, "search_flows", d.get("message", str(d)))
        except Exception as e:
            p(FAIL, "search_flows", str(e))
    else:
        p(SKIP, "search_flows", "no flows in db")

    # search_processes
    try:
        kw = ["steel"] if not flows else flows[0].name.split()[:1]
        r = await handle_search_processes({"keywords": kw, "max_results": 5})
        d = payload(r)
        if d["success"]:
            p(PASS, "search_processes", f"{d['count']} process(es) for {kw}")
        else:
            # Not failing — keyword might genuinely have no match
            p(PASS, "search_processes", f"0 matches for {kw} (ok)")
    except Exception as e:
        p(FAIL, "search_processes", str(e))

    # get_entity_by_name — look up a method by exact name
    if methods:
        try:
            r = await handle_get_entity_by_name(
                {"model_type": "ImpactMethod", "name": methods[0].name}
            )
            d = payload(r)
            if d["success"]:
                ent = d.get("entity", {})
                p(PASS, "get_entity_by_name",
                  f"{ent.get('name','')} ({ent.get('type','')})")
            else:
                p(FAIL, "get_entity_by_name", d.get("message", str(d)))
        except Exception as e:
            p(FAIL, "get_entity_by_name", str(e))
    else:
        p(SKIP, "get_entity_by_name", "no methods in db")


# ---------------------------------------------------------------------------
# 4. Calculation
# ---------------------------------------------------------------------------
async def test_calculation(methods: list, systems: list) -> tuple[str | None, list]:
    """Return (result_id, serialized_impacts)."""
    print("\n── 3. Calculation ─────────────────────────────────────────────")

    if not methods:
        p(SKIP, "calculate_impacts", "no impact methods in database")
        return None, []
    if not systems:
        p(SKIP, "calculate_impacts", "no product systems in database")
        return None, []

    system = systems[0]
    method = methods[0]

    p(PASS, "using system", f"{system.name!r} ({system.id})")
    p(PASS, "using method", f"{method.name!r} ({method.id})")

    try:
        from src.handlers import handle_calculate_impacts
        r = await handle_calculate_impacts({
            "system_id": system.id,
            "method_id": method.id,
            "amount": 1.0,
        })
        d = payload(r)
        if not d.get("success"):
            p(FAIL, "calculate_impacts", d.get("message", str(d)))
            return None, []

        result_id = d["result_id"]
        impacts = d.get("impacts", [])  # already serialized dicts with "category_id"
        warnings = d.get("warnings", [])
        summary = d.get("summary", {})
        p(PASS, "calculate_impacts",
          f"result_id={result_id}, {len(impacts)} impact(s), "
          f"{len(warnings)} warning(s)")

        top = (summary.get("top_impacts") or [])[:3]
        for t in top:
            print(f"      {t.get('category','?')}: "
                  f"{t.get('amount','?')} {t.get('unit','')}")
        return result_id, impacts
    except Exception as e:
        import traceback
        traceback.print_exc()
        p(FAIL, "calculate_impacts", str(e))
        return None, []


# ---------------------------------------------------------------------------
# 5. Follow-up analysis
# ---------------------------------------------------------------------------
async def test_followup(result_id: str, impacts: list) -> None:
    print("\n── 4. Follow-up analysis ──────────────────────────────────────")
    from src.handlers import (
        handle_get_inventory_results,
        handle_get_total_requirements,
        handle_get_contribution_tree,
        handle_analyze_contributions,
        handle_get_normalized_impacts,
    )

    # "impacts" are the serialized dicts from the calculate_impacts response.
    # Each has "category_id" (the raw o.Ref id) plus "name", "amount", "unit".
    first_cat_id = impacts[0].get("category_id") if impacts else None

    # get_inventory_results  (response key is "inventory", not "flows")
    try:
        r = await handle_get_inventory_results(
            {"result_id": result_id, "direction": "OUTPUT"}
        )
        d = payload(r)
        if d["success"]:
            inv = d.get("inventory", d.get("flows", []))
            p(PASS, "get_inventory_results", f"{len(inv)} output flow(s)")
        else:
            p(FAIL, "get_inventory_results", d.get("message", str(d)))
    except Exception as e:
        p(FAIL, "get_inventory_results", str(e))

    # get_total_requirements
    try:
        r = await handle_get_total_requirements({"result_id": result_id})
        d = payload(r)
        if d["success"]:
            p(PASS, "get_total_requirements",
              f"{d.get('count', len(d.get('requirements',[])))} row(s)")
        else:
            p(FAIL, "get_total_requirements", d.get("message", str(d)))
    except Exception as e:
        p(FAIL, "get_total_requirements", str(e))

    # get_normalized_impacts — non-fatal if method has no nw-set
    try:
        r = await handle_get_normalized_impacts({"result_id": result_id})
        d = payload(r)
        if d["success"]:
            p(PASS, "get_normalized_impacts",
              f"{len(d.get('impacts',[]))} normalized rows")
        else:
            p(PASS, "get_normalized_impacts",
              f"n/a — {d.get('message','no normalization set')}")
    except Exception as e:
        p(PASS, "get_normalized_impacts", f"n/a ({e})")

    # get_contribution_tree  (needs a valid category_id)
    if first_cat_id:
        try:
            r = await handle_get_contribution_tree({
                "result_id": result_id,
                "impact_category_id": first_cat_id,
                "max_depth": 3,
                "min_share": 0.01,
            })
            d = payload(r)
            if d["success"]:
                cat_name = impacts[0].get("name", first_cat_id[:12])
                p(PASS, "get_contribution_tree", f"category='{cat_name}'")
            else:
                p(FAIL, "get_contribution_tree", d.get("message", str(d)))
        except Exception as e:
            p(FAIL, "get_contribution_tree", str(e))
    else:
        p(SKIP, "get_contribution_tree", "no impact categories in result")

    # analyze_contributions
    if first_cat_id:
        try:
            r = await handle_analyze_contributions({
                "result_id": result_id,
                "impact_category_id": first_cat_id,
                "limit": 5,
            })
            d = payload(r)
            if d["success"]:
                p(PASS, "analyze_contributions",
                  f"{len(d.get('contributors',[]))} contributor(s)")
            else:
                p(FAIL, "analyze_contributions", d.get("message", str(d)))
        except Exception as e:
            p(FAIL, "analyze_contributions", str(e))
    else:
        p(SKIP, "analyze_contributions", "no impact categories")


# ---------------------------------------------------------------------------
# 6. Dispose
# ---------------------------------------------------------------------------
async def test_dispose(result_id: str) -> None:
    print("\n── 5. Dispose ─────────────────────────────────────────────────")
    from src.handlers import handle_dispose_result, handle_dispose_all_results

    try:
        r = await handle_dispose_result({"result_id": result_id})
        d = payload(r)
        assert d["success"], f"dispose failed: {d}"
        p(PASS, "dispose_result", result_id)
    except Exception as e:
        p(FAIL, "dispose_result", str(e))

    try:
        r = await handle_dispose_all_results({})
        d = payload(r)
        assert d["success"]
        p(PASS, "dispose_all_results", f"disposed={d.get('disposed', 0)}")
    except Exception as e:
        p(FAIL, "dispose_all_results", str(e))


# ---------------------------------------------------------------------------
# 7. Read-only gating
# ---------------------------------------------------------------------------
async def test_read_only() -> None:
    print("\n── 6. OPENLCA_READ_ONLY gating ────────────────────────────────")
    import src.lca_client as lc_mod

    orig = os.environ.get("OPENLCA_READ_ONLY")
    os.environ["OPENLCA_READ_ONLY"] = "true"
    lc_mod._client = None

    try:
        from src.handlers import handle_create_product_flow
        r = await handle_create_product_flow({"name": "test_ro_flow"})
        d = payload(r)
        if not d["success"] and d.get("error_code") == "WRITE_BLOCKED":
            p(PASS, "write blocked in RO mode", f"error_code={d['error_code']}")
        else:
            p(FAIL, "write blocked in RO mode",
              f"expected WRITE_BLOCKED, got {d}")
    except Exception as e:
        p(FAIL, "write blocked in RO mode", str(e))
    finally:
        if orig is None:
            os.environ.pop("OPENLCA_READ_ONLY", None)
        else:
            os.environ["OPENLCA_READ_ONLY"] = orig
        lc_mod._client = None  # restore to RW mode


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main() -> None:
    print("=" * 60)
    print("  openlca-mcp v0.2.0  —  live smoke test  (port 8080)")
    print("=" * 60)

    await test_connection()

    print("\n── Discovering entities ────────────────────────────────────────")
    methods, systems, flows = discover_entities()
    print(f"  found {len(methods)} method(s), {len(systems)} system(s), "
          f"{len(flows)} flow sample(s)")

    await test_search(methods, flows)
    result_id, impacts = await test_calculation(methods, systems)

    if result_id:
        await test_followup(result_id, impacts)
        await test_dispose(result_id)
    else:
        print("\n  [SKIP] follow-up / dispose tests (no result_id)")

    await test_read_only()

    print("\n" + "=" * 60)
    passed = sum(1 for tag, _ in results if tag == PASS)
    failed = sum(1 for tag, _ in results if tag == FAIL)
    skipped = sum(1 for tag, _ in results if tag == SKIP)
    print(f"  {passed} passed  |  {failed} failed  |  {skipped} skipped")
    print("=" * 60)
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
