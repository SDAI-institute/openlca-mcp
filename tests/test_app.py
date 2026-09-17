"""Unit tests for the FastMCP app slice (tools, identity gating, envelopes)."""

from unittest.mock import MagicMock

import pytest

import src.app as app
import src.auth as auth
import src.connections as connections


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
    client.test_connection.return_value = True
    monkeypatch.setattr(app, "get_client", lambda profile_id=None: client)
    return client


async def test_test_connection_success_envelope(fake_client):
    body = await app.test_connection()
    assert body == {
        "success": True, "connected": True, "port": 8080, "connection": "default",
    }


async def test_health_check_uses_agent_helper(fake_client, monkeypatch):
    # Mirror the real signature: count_entities is keyword-only.
    def fake_health(client, *, count_entities=True):
        return {"ok": True, "counted": count_entities}

    monkeypatch.setattr(app, "_health_check", fake_health)
    body = await app.health_check(count_entities=False)
    assert body["success"] is True
    assert body["health"] == {"ok": True, "counted": False}


async def test_connection_failure_is_clean_error(monkeypatch):
    bad = MagicMock()
    bad.test_connection.side_effect = ConnectionError("refused")
    bad.port = 8080
    monkeypatch.setattr(app, "get_client", lambda profile_id=None: bad)
    body = await app.test_connection()
    assert body["success"] is False
    assert body["error_code"] == "CONNECTION_FAILED"


async def test_forbidden_connection_is_gated(monkeypatch, fake_client):
    # Identity limited to 'default' asking for another profile -> FORBIDDEN.
    restricted = auth.Identity(tenant_id="t", allowed_profiles=["default"])
    monkeypatch.setattr(app, "current_identity", lambda: restricted)
    body = await app.test_connection(connection="secret")
    assert body["success"] is False
    assert body["error_code"] == "FORBIDDEN_CONNECTION"

async def test_mcp_path_middleware_accepts_trailing_slash():
    seen = {}

    async def inner(scope, receive, send):
        seen["path"] = scope["path"]
        seen["raw_path"] = scope["raw_path"]

    middleware = app._NormalizeMcpPathMiddleware(inner, "/mcp")
    scope = {"type": "http", "path": "/mcp/", "raw_path": b"/mcp/"}

    async def receive():
        return {"type": "http.disconnect"}

    async def send(_message):
        return None

    await middleware(scope, receive, send)
    assert seen == {"path": "/mcp", "raw_path": b"/mcp"}
