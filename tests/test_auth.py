"""Unit tests for API-key identity resolution and connection authorization."""

import json

import pytest

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


def _set_keys(monkeypatch, mapping):
    monkeypatch.setenv("OPENLCA_API_KEYS", json.dumps(mapping))
    auth.reset_keys()


def test_open_mode_returns_anonymous_with_default_only():
    assert auth.auth_enabled() is False
    ident = auth.resolve_identity(None)
    assert ident is auth.ANONYMOUS
    assert ident.may_use("default") is True
    assert ident.may_use("other") is False


def test_known_key_resolves_identity(monkeypatch):
    _set_keys(monkeypatch, {
        "sk_acme": {"tenant_id": "acme", "allowed_profiles": ["default", "acme"]},
    })
    assert auth.auth_enabled() is True
    ident = auth.resolve_identity("sk_acme")
    assert ident.tenant_id == "acme"
    assert ident.may_use("acme") is True


def test_unknown_or_missing_key_rejected_when_auth_enabled(monkeypatch):
    _set_keys(monkeypatch, {"sk_acme": {"tenant_id": "acme"}})
    assert auth.resolve_identity("nope") is None
    assert auth.resolve_identity(None) is None


def test_wildcard_allows_any_profile(monkeypatch):
    _set_keys(monkeypatch, {"sk_admin": {"tenant_id": "admin", "allowed_profiles": "*"}})
    ident = auth.resolve_identity("sk_admin")
    assert ident.may_use("anything") is True


def test_resolve_profile_uses_identity_default(monkeypatch):
    monkeypatch.setenv(
        "OPENLCA_CONNECTIONS",
        json.dumps([{"id": "acme", "host": "10.0.0.9"}]),
    )
    connections.reset_profiles()
    _set_keys(monkeypatch, {
        "sk_acme": {"tenant_id": "acme", "allowed_profiles": ["acme"], "default_profile": "acme"},
    })
    ident = auth.resolve_identity("sk_acme")
    profile = auth.resolve_profile(ident, None)  # None -> identity default
    assert profile.id == "acme"
    assert profile.host == "10.0.0.9"


def test_resolve_profile_forbidden(monkeypatch):
    _set_keys(monkeypatch, {"sk_a": {"tenant_id": "a", "allowed_profiles": ["default"]}})
    ident = auth.resolve_identity("sk_a")
    with pytest.raises(auth.ForbiddenConnection):
        auth.resolve_profile(ident, "secret-instance")


def test_resolve_profile_unknown(monkeypatch):
    _set_keys(monkeypatch, {"sk_a": {"tenant_id": "a", "allowed_profiles": "*"}})
    ident = auth.resolve_identity("sk_a")
    with pytest.raises(auth.UnknownConnection):
        auth.resolve_profile(ident, "ghost")
