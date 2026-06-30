"""Behavior tests for the tool handlers (mocked client)."""

from unittest.mock import MagicMock

import pytest
import olca_schema as o
from openlca_ipc.contributions import TreeNode, ContributionItem

import src.handlers as handlers
from src.result_store import store
from tests.conftest import payload


# ---------------------------------------------------------------------------
# Search / lookup
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_flows_success(patch_client):
    patch_client.search.find_flows.return_value = [
        o.Ref(id="f1", name="Steel"),
        o.Ref(id="f2", name="Steel, low alloy"),
    ]
    body = payload(await handlers.handle_search_flows({"keywords": ["steel"]}))
    assert body["success"] is True
    assert body["count"] == 2
    assert body["flows"][0] == {"id": "f1", "name": "Steel"}


@pytest.mark.asyncio
async def test_search_flows_error_envelope(patch_client):
    patch_client.search.find_flows.side_effect = RuntimeError("ipc down")
    body = payload(await handlers.handle_search_flows({"keywords": ["steel"]}))
    assert body["success"] is False
    assert body["error_code"] == "INTERNAL_ERROR"


@pytest.mark.asyncio
async def test_search_impact_methods_not_found(patch_client):
    patch_client.search.find_impact_method.return_value = None
    body = payload(await handlers.handle_search_impact_methods({"keywords": ["nope"]}))
    assert body["success"] is False
    assert body["error_code"] == "IMPACT_METHOD_NOT_FOUND"
    assert "search_impact_methods" in body["suggested_next_actions"]


@pytest.mark.asyncio
async def test_get_entity_by_name_found_and_missing(patch_client):
    patch_client.search.get_by_name.return_value = o.Ref(id="x", name="Steel")
    body = payload(
        await handlers.handle_get_entity_by_name({"model_type": "Flow", "name": "Steel"})
    )
    assert body["success"] is True
    assert body["entity"]["id"] == "x"
    assert body["entity"]["type"] == "Flow"

    patch_client.search.get_by_name.return_value = None
    body = payload(
        await handlers.handle_get_entity_by_name({"model_type": "Flow", "name": "Nope"})
    )
    assert body["success"] is False
    assert body["error_code"] == "ENTITY_NOT_FOUND"


# ---------------------------------------------------------------------------
# Calculate
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_calculate_impacts_stores_and_summarizes(
    patch_client, sample_impacts, monkeypatch
):
    monkeypatch.setattr(handlers, "check_result_consistency", lambda r: [])
    patch_client.search.find_impact_method.return_value = o.Ref(id="m", name="EF 3.1")
    patch_client.calculate.simple_calculation.return_value = MagicMock(name="Result")
    patch_client.results.get_total_impacts.return_value = sample_impacts

    body = payload(
        await handlers.handle_calculate_impacts(
            {"system_id": "sys1", "method_keywords": ["EF"], "amount": 1.0}
        )
    )
    assert body["success"] is True
    assert body["result_id"].startswith("res_")
    assert body["result_id"] in store
    # ResultSummary carries the top impact.
    assert body["summary"]["top_impacts"][0]["category"] == "Climate change"
    # Normalized impacts include a category_id for follow-up tools.
    assert body["impacts"][0]["category_id"] == "GW"


@pytest.mark.asyncio
async def test_calculate_impacts_missing_system(patch_client):
    body = payload(await handlers.handle_calculate_impacts({"method_keywords": ["EF"]}))
    assert body["success"] is False
    assert body["error_code"] == "SYSTEM_NOT_FOUND"


@pytest.mark.asyncio
async def test_calculate_impacts_method_not_found(patch_client):
    patch_client.search.find_impact_method.return_value = None
    body = payload(
        await handlers.handle_calculate_impacts(
            {"system_id": "sys1", "method_keywords": ["nope"]}
        )
    )
    assert body["success"] is False
    assert body["error_code"] == "IMPACT_METHOD_NOT_FOUND"


# ---------------------------------------------------------------------------
# Interpretation (operate on a stored result)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_analyze_contributions(patch_client, sample_impacts):
    stored = store.add(MagicMock(), impacts=sample_impacts)
    patch_client.contributions.get_top_contributors.return_value = [
        ContributionItem(name="Furnace", amount=2.0, share=0.8, ref=o.Ref(id="p", name="Furnace")),
    ]
    body = payload(
        await handlers.handle_analyze_contributions(
            {"result_id": stored.result_id, "impact_category_id": "GW", "n": 5}
        )
    )
    assert body["success"] is True
    assert body["contributors"][0]["name"] == "Furnace"


@pytest.mark.asyncio
async def test_contribution_tree(patch_client, sample_impacts):
    stored = store.add(MagicMock(), impacts=sample_impacts)
    patch_client.contributions.get_contribution_tree.return_value = [
        TreeNode(name="A", amount=2.5, direct=1.0, share=1.0, ref=o.Ref(id="a", name="A"),
                 children=[TreeNode(name="B", amount=1.5, direct=1.5, share=0.6, ref=None)])
    ]
    body = payload(
        await handlers.handle_get_contribution_tree(
            {"result_id": stored.result_id, "impact_category_id": "GW"}
        )
    )
    assert body["success"] is True
    assert body["tree"][0]["children"][0]["name"] == "B"


@pytest.mark.asyncio
async def test_interpretation_unknown_result_id(patch_client):
    body = payload(
        await handlers.handle_get_contribution_tree(
            {"result_id": "res_missing", "impact_category_id": "GW"}
        )
    )
    assert body["success"] is False
    assert body["error_code"] == "ENTITY_NOT_FOUND"


@pytest.mark.asyncio
async def test_contribution_unknown_category(patch_client, sample_impacts):
    stored = store.add(MagicMock(), impacts=sample_impacts)
    body = payload(
        await handlers.handle_analyze_contributions(
            {"result_id": stored.result_id, "impact_category_id": "ZZZ"}
        )
    )
    assert body["success"] is False
    assert body["error_code"] == "ENTITY_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_inventory_results(patch_client, sample_impacts):
    stored = store.add(MagicMock(), impacts=sample_impacts)
    patch_client.results.get_inventory.return_value = [
        {"name": "CO2", "flow": o.Ref(id="co2", name="CO2"), "amount": 3.0,
         "unit": "kg", "is_input": False, "location": None},
    ]
    body = payload(
        await handlers.handle_get_inventory_results(
            {"result_id": stored.result_id, "direction": "output"}
        )
    )
    assert body["success"] is True
    assert body["inventory"][0]["flow"] == {"id": "co2", "name": "CO2"}
    patch_client.results.get_inventory.assert_called_once()


@pytest.mark.asyncio
async def test_dispose_result(patch_client):
    result = MagicMock()
    stored = store.add(result)
    body = payload(await handlers.handle_dispose_result({"result_id": stored.result_id}))
    assert body["success"] is True
    result.dispose.assert_called_once()

    body = payload(await handlers.handle_dispose_result({"result_id": "res_gone"}))
    assert body["success"] is False
    assert body["error_code"] == "ENTITY_NOT_FOUND"


# ---------------------------------------------------------------------------
# Read-only gating
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_read_only_blocks_writes(patch_client, monkeypatch):
    monkeypatch.setenv("OPENLCA_READ_ONLY", "true")
    body = payload(await handlers.handle_create_product_flow({"name": "Widget"}))
    assert body["success"] is False
    assert body["error_code"] == "WRITE_BLOCKED"
    assert "disable_read_only_mode" in body["suggested_next_actions"]
    # A read still works under read-only mode.
    patch_client.search.find_flows.return_value = [o.Ref(id="f", name="Steel")]
    body = payload(await handlers.handle_search_flows({"keywords": ["steel"]}))
    assert body["success"] is True
