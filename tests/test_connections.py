"""Unit tests for the connection-profile registry and per-profile client cache."""

import json

import pytest

import src.connections as connections
import src.lca_client as lca_client


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    """Isolate env + caches around each test."""
    for var in ("OPENLCA_CONNECTIONS", "OPENLCA_CONNECTIONS_FILE",
                "OPENLCA_HOST", "OPENLCA_PORT", "OPENLCA_READ_ONLY"):
        monkeypatch.delenv(var, raising=False)
    connections.reset_profiles()
    lca_client.reset_client()
    yield
    connections.reset_profiles()
    lca_client.reset_client()


def test_default_profile_synthesized_from_env(monkeypatch):
    monkeypatch.setenv("OPENLCA_HOST", "host.docker.internal")
    monkeypatch.setenv("OPENLCA_PORT", "9000")
    monkeypatch.setenv("OPENLCA_READ_ONLY", "true")
    connections.reset_profiles()

    profile = connections.get_profile(None)
    assert profile.id == "default"
    assert profile.host == "host.docker.internal"
    assert profile.port == 9000
    assert profile.read_only is True
    assert profile.kind == "local"  # host.docker.internal is UI-backed


def test_inline_json_list_adds_profiles_and_keeps_default(monkeypatch):
    monkeypatch.setenv(
        "OPENLCA_CONNECTIONS",
        json.dumps([{"id": "remote", "host": "10.0.0.5", "port": 8080, "kind": "remote"}]),
    )
    connections.reset_profiles()

    profiles = connections.get_profiles()
    assert set(profiles) == {"default", "remote"}
    assert profiles["remote"].host == "10.0.0.5"
    assert profiles["remote"].kind == "remote"


def test_inline_json_map_form(monkeypatch):
    monkeypatch.setenv(
        "OPENLCA_CONNECTIONS",
        json.dumps({"tenant_x": {"host": "tx.local", "port": 8181}}),
    )
    connections.reset_profiles()

    profile = connections.get_profile("tenant_x")
    assert profile.id == "tenant_x"
    assert profile.port == 8181


def test_connections_file_is_read(monkeypatch, tmp_path):
    cfg = tmp_path / "connections.json"
    cfg.write_text(json.dumps([{"id": "fromfile", "host": "f.local"}]), encoding="utf-8")
    monkeypatch.setenv("OPENLCA_CONNECTIONS_FILE", str(cfg))
    connections.reset_profiles()

    assert connections.get_profile("fromfile").host == "f.local"


def test_unknown_profile_raises():
    with pytest.raises(KeyError):
        connections.get_profile("does-not-exist")


def test_get_client_caches_per_profile(monkeypatch):
    monkeypatch.setenv(
        "OPENLCA_CONNECTIONS",
        json.dumps([{"id": "remote", "host": "127.0.0.1", "port": 8080}]),
    )
    connections.reset_profiles()

    default_a = lca_client.get_client()
    default_b = lca_client.get_client("default")
    remote = lca_client.get_client("remote")

    assert default_a is default_b           # same profile -> cached instance
    assert remote is not default_a          # different profile -> distinct client

    lca_client.reset_client()
    assert lca_client.get_client() is not default_a  # cache cleared
