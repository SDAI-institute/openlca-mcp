"""Contract tests for machine-enforced FastMCP tool schemas."""

from __future__ import annotations

from typing import Any

import pytest

import src
from src.app import mcp
from src.tools import inventory


async def tool_parameters(name: str) -> dict[str, Any]:
    tools = {tool.name: tool for tool in await mcp.list_tools()}
    return tools[name].parameters


def property_schema(parameters: dict[str, Any], name: str) -> dict[str, Any]:
    return parameters["properties"][name]


def non_null_schema(schema: dict[str, Any]) -> dict[str, Any]:
    if "anyOf" not in schema:
        return schema
    candidates = [candidate for candidate in schema["anyOf"] if candidate != {"type": "null"}]
    assert len(candidates) == 1
    return candidates[0]


def test_package_and_runtime_versions_match() -> None:
    assert src.__version__ == "0.5.0"


@pytest.mark.asyncio
async def test_generated_string_enums_are_machine_enforced() -> None:
    contributions = await tool_parameters("analyze_contributions")
    assert property_schema(contributions, "contribution_type")["enum"] == ["process", "flow"]

    export = await tool_parameters("export_results")
    assert property_schema(export, "kind")["enum"] == ["impacts", "comparison"]
    assert property_schema(export, "format")["enum"] == ["csv", "excel"]

    entity = await tool_parameters("get_entity_by_name")
    assert property_schema(entity, "model_type")["enum"] == [
        "Flow",
        "Process",
        "ImpactMethod",
        "ProductSystem",
        "FlowProperty",
        "Unit",
    ]

    inventory_results = await tool_parameters("get_inventory_results")
    assert property_schema(inventory_results, "direction")["enum"] == [
        "input",
        "output",
        "both",
    ]

    flows = await tool_parameters("search_flows")
    assert non_null_schema(property_schema(flows, "flow_type"))["enum"] == [
        "PRODUCT_FLOW",
        "ELEMENTARY_FLOW",
        "WASTE_FLOW",
    ]


@pytest.mark.asyncio
async def test_create_product_system_constraints_are_in_schema() -> None:
    parameters = await tool_parameters("create_product_system")

    cutoff = non_null_schema(property_schema(parameters, "cutoff"))
    assert cutoff["minimum"] == 0.0
    assert cutoff["maximum"] == 1.0
    assert property_schema(parameters, "default_providers")["enum"] == [
        "prefer",
        "only",
        "ignore",
    ]
    assert property_schema(parameters, "preferred_type")["enum"] == [
        "LCI_RESULT",
        "UNIT_PROCESS",
    ]


@pytest.mark.asyncio
async def test_create_process_exchange_schema_is_explicit_and_closed() -> None:
    parameters = await tool_parameters("create_process")
    exchange = property_schema(parameters, "exchanges")["items"]

    assert exchange["additionalProperties"] is False
    assert exchange["required"] == ["flow_id", "amount", "is_input"]
    assert set(exchange["properties"]) == {
        "flow_id",
        "amount",
        "is_input",
        "is_quantitative_reference",
        "provider_id",
        "formula",
        "unit_id",
        "flow_property_id",
    }


@pytest.mark.asyncio
async def test_create_process_converts_exchange_models_before_handler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    async def fake_call_handler(
        handler: Any,
        arguments: dict[str, Any],
        connection: str | None,
    ) -> dict[str, Any]:
        captured.update(arguments)
        captured["connection"] = connection
        return {"success": True}

    monkeypatch.setattr(inventory, "call_handler", fake_call_handler)
    result = await inventory.create_process(
        name="Schema test process",
        exchanges=[
            inventory.ProcessExchange(
                flow_id="flow-1",
                amount=1.0,
                is_input=False,
                formula="0.5*2",
            )
        ],
        connection="test-profile",
    )

    assert result == {"success": True}
    assert captured["exchanges"] == [
        {
            "flow_id": "flow-1",
            "amount": 1.0,
            "is_input": False,
            "is_quantitative_reference": False,
            "formula": "0.5*2",
        }
    ]
    assert captured["connection"] == "test-profile"
