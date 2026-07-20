"""Tests for the FastMCP tool bridge and the delegated tool modules."""

from unittest.mock import MagicMock

import olca_schema as o
import pytest

import src.app as app
import src.auth as auth
import src.connections as connections
import src.handlers as handlers
from src.tools import goal_scope, lifecycle


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    for var in ("OPENLCA_API_KEYS", "OPENLCA_API_KEYS_FILE",
                "OPENLCA_CONNECTIONS", "OPENLCA_CONNECTIONS_FILE",
                "OPENLCA_HOST", "OPENLCA_PORT", "OPENLCA_READ_ONLY"):
        monkeypatch.delenv(var, raising=False)
    auth.reset_keys()
    connections.reset_profiles()
    yield
    auth.reset_keys()
    connections.reset_profiles()


@pytest.fixture
def fake_client(monkeypatch):
    client = MagicMock(name="OLCAClient")
    client.port = 8080
    # _resolve() (app) and the handler (handlers) both call get_client.
    monkeypatch.setattr(app, "get_client", lambda profile_id=None: client)
    monkeypatch.setattr(handlers, "get_client", lambda profile_id=None: client)
    return client


async def test_search_flows_bridge_delegates_and_offloads(fake_client):
    fake_client.search.find_flows.return_value = [o.Ref(id="f1", name="Steel, hot rolled")]
    body = await goal_scope.search_flows(keywords=["steel"], max_results=5)
    assert body["success"] is True
    assert body["count"] == 1
    assert body["flows"][0]["name"] == "Steel, hot rolled"
    # args threaded through to the handler
    fake_client.search.find_flows.assert_called_once_with(["steel"], 5, None)


async def test_store_tool_runs_without_connection(monkeypatch):
    monkeypatch.setattr(handlers.store, "dispose_all", lambda: 3)
    body = await lifecycle.dispose_all_results()
    assert body == {"success": True, "disposed_count": 3}


async def test_connection_gating_blocks_unauthorized(monkeypatch, fake_client):
    restricted = auth.Identity(tenant_id="t", allowed_profiles=["default"])
    monkeypatch.setattr(app, "current_identity", lambda: restricted)
    body = await goal_scope.search_flows(keywords=["x"], connection="secret")
    assert body["success"] is False
    assert body["error_code"] == "FORBIDDEN_CONNECTION"
    fake_client.search.find_flows.assert_not_called()
