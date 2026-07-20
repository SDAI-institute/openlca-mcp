"""Registration tests for prompts and resources."""

from unittest.mock import MagicMock

import src.app as app


async def test_prompts_registered():
    prompts = await app.mcp.list_prompts()
    names = {p.name for p in prompts}
    assert {
        "lca_calculation_walkthrough",
        "interpret_impact_results",
        "build_product_system_guide",
    } <= names


async def test_resources_registered():
    resources = await app.mcp.list_resources()
    uris = {str(r.uri) for r in resources}
    assert {
        "openlca://connections",
        "openlca://impact-methods",
        "openlca://product-systems",
        "openlca://iso-phases-guide",
    } <= uris


async def test_connections_resource_lists_default():
    from src.resources import connections_resource

    data = connections_resource()
    assert data["default"] == "default"
    assert any(c["id"] == "default" for c in data["connections"])


async def test_impact_methods_resource_offloads(monkeypatch):
    import olca_schema as o

    import src.resources as resources

    fake = MagicMock()
    fake.client.get_descriptors.return_value = [o.Ref(id="m1", name="ReCiPe")]
    monkeypatch.setattr(resources, "resolve_client", lambda _conn: fake)

    data = await resources.impact_methods_resource()
    assert data["count"] == 1
    assert data["impact_methods"][0]["name"] == "ReCiPe"
    fake.client.get_descriptors.assert_called_once_with(o.ImpactMethod)
