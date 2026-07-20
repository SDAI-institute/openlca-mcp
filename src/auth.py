"""
API-key identity and connection authorization.

Maps an API key to an :class:`Identity` (a tenant plus the connection profiles it
may target), so a single hosted server can serve several tenants and gate which
openLCA instances each one may reach. This unifies auth (#3) with per-request
instance selection (#4): the identity decides which profiles a caller can pass as
a tool's ``connection`` argument.

Sources (first match wins):
    OPENLCA_API_KEYS        inline JSON: {api_key: {tenant_id, allowed_profiles, ...}}
    OPENLCA_API_KEYS_FILE   path to that JSON (default: config/api_keys.json)

**Open mode**: when no keys are configured, auth is disabled and every caller is an
anonymous identity allowed only the ``default`` profile — so local/stdio and
single-user gateway deployments keep working with zero configuration.

Key record::

    {"sk_live_abc": {"tenant_id": "acme",
                     "allowed_profiles": ["default", "acme-remote"],
                     "default_profile": "acme-remote"}}

``allowed_profiles`` may be ``"*"`` (or contain ``"*"``) to allow every profile.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional, Union

from pydantic import BaseModel, field_validator

from .connections import DEFAULT_PROFILE_ID, ConnectionProfile, get_profile

logger = logging.getLogger(__name__)


class Identity(BaseModel):
    """A resolved caller: a tenant and the profiles it may use."""

    tenant_id: str
    allowed_profiles: list[str] = [DEFAULT_PROFILE_ID]
    default_profile: str = DEFAULT_PROFILE_ID
    anonymous: bool = False

    @field_validator("allowed_profiles", mode="before")
    @classmethod
    def _coerce_wildcard(cls, v):
        # Accept the convenience form allowed_profiles: "*".
        if isinstance(v, str):
            return [v]
        return v

    def may_use(self, profile_id: str) -> bool:
        return "*" in self.allowed_profiles or profile_id in self.allowed_profiles


#: The implicit identity used when auth is disabled (no keys configured).
ANONYMOUS = Identity(
    tenant_id="anonymous",
    allowed_profiles=[DEFAULT_PROFILE_ID],
    default_profile=DEFAULT_PROFILE_ID,
    anonymous=True,
)


class AuthError(Exception):
    """Base class for auth failures, carrying a structured error code."""

    error_code = "AUTH_ERROR"


class InvalidApiKey(AuthError):
    error_code = "INVALID_API_KEY"


class ForbiddenConnection(AuthError):
    error_code = "FORBIDDEN_CONNECTION"


class UnknownConnection(AuthError):
    error_code = "UNKNOWN_CONNECTION"


def _raw_keys() -> Optional[Union[dict, list]]:
    raw = os.getenv("OPENLCA_API_KEYS")
    if raw and raw.strip():
        return json.loads(raw)
    path = Path(os.getenv("OPENLCA_API_KEYS_FILE", "config/api_keys.json"))
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def _load_keys() -> dict[str, Identity]:
    data = _raw_keys()
    keys: dict[str, Identity] = {}
    if isinstance(data, dict):
        for api_key, spec in data.items():
            keys[api_key] = Identity(**spec)
    return keys


_keys: Optional[dict[str, Identity]] = None


def _key_map() -> dict[str, Identity]:
    global _keys
    if _keys is None:
        _keys = _load_keys()
        if _keys:
            logger.info("Loaded %d API key(s); auth ENABLED", len(_keys))
        else:
            logger.info("No API keys configured; auth DISABLED (open mode)")
    return _keys


def reset_keys() -> None:
    """Drop the cached key map (tests / config reload)."""
    global _keys
    _keys = None


def auth_enabled() -> bool:
    """True when at least one API key is configured."""
    return bool(_key_map())


def resolve_identity(api_key: Optional[str]) -> Optional[Identity]:
    """
    Resolve an API key to an :class:`Identity`.

    Open mode (no keys configured) → :data:`ANONYMOUS`. Otherwise a known key →
    its identity; a missing/unknown key → ``None`` (caller should reject).
    """
    if not auth_enabled():
        return ANONYMOUS
    if not api_key:
        return None
    return _key_map().get(api_key)


def resolve_profile(
    identity: Identity, requested_connection: Optional[str]
) -> ConnectionProfile:
    """
    Resolve the connection profile a caller may use for this request.

    ``requested_connection`` of ``None`` falls back to the identity's default
    profile. Raises :class:`ForbiddenConnection` if the identity may not use the
    profile, or :class:`UnknownConnection` if no such profile exists.
    """
    profile_id = requested_connection or identity.default_profile
    if not identity.may_use(profile_id):
        raise ForbiddenConnection(
            f"Identity '{identity.tenant_id}' may not use connection '{profile_id}'."
        )
    try:
        return get_profile(profile_id)
    except KeyError as exc:
        raise UnknownConnection(f"Unknown connection profile '{profile_id}'.") from exc
