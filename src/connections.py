"""
openLCA connection profiles.

A registry of named openLCA IPC endpoints so a single server can target several
instances. The ``default`` profile is synthesized from ``OPENLCA_HOST`` /
``OPENLCA_PORT`` / ``OPENLCA_READ_ONLY`` for backward compatibility and points at
the operator's local desktop openLCA — so entities created through the MCP appear
in the openLCA UI for human verification. Additional profiles let hosted
deployments route to other (remote / headless) instances per request.

Sources (first match wins, then ``default`` is always ensured):
    OPENLCA_CONNECTIONS        inline JSON (list of profiles, or {id: profile})
    OPENLCA_CONNECTIONS_FILE   path to a JSON file (default: config/connections.json)

A profile JSON object: ``{id, host, port, read_only, label, kind}``.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Literal, Optional, Union

from pydantic import BaseModel

logger = logging.getLogger(__name__)

_TRUTHY = {"1", "true", "yes", "on"}

DEFAULT_PROFILE_ID = "default"
#: Hosts treated as "local" (UI-backed, human-verifiable) for the default profile.
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "host.docker.internal"}


class ConnectionProfile(BaseModel):
    """A named openLCA IPC endpoint."""

    id: str
    host: str = "localhost"
    port: int = 8080
    read_only: bool = False
    label: str = ""
    kind: Literal["local", "remote"] = "local"


def _default_profile() -> ConnectionProfile:
    """Build the back-compat ``default`` profile from the OPENLCA_* env vars."""
    host = os.getenv("OPENLCA_HOST", "localhost")
    return ConnectionProfile(
        id=DEFAULT_PROFILE_ID,
        host=host,
        port=int(os.getenv("OPENLCA_PORT", "8080")),
        read_only=os.getenv("OPENLCA_READ_ONLY", "false").strip().lower() in _TRUTHY,
        label="Local desktop openLCA",
        kind="local" if host in _LOCAL_HOSTS else "remote",
    )


def _raw_registry_data() -> Optional[Union[list, dict]]:
    """Return parsed registry JSON from env or file, or None if unconfigured."""
    raw = os.getenv("OPENLCA_CONNECTIONS")
    if raw and raw.strip():
        return json.loads(raw)
    path = Path(os.getenv("OPENLCA_CONNECTIONS_FILE", "config/connections.json"))
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def _coerce_profiles(data: Union[list, dict, None]) -> dict[str, ConnectionProfile]:
    """Normalize the several accepted registry shapes into an id->profile map."""
    profiles: dict[str, ConnectionProfile] = {}
    if isinstance(data, dict):
        # Allow a wrapping {"connections": ...} as well as a bare {id: spec} map.
        items = data.get("connections", data) if "connections" in data else data
        if isinstance(items, dict):
            for pid, spec in items.items():
                profile = ConnectionProfile(**{"id": pid, **spec})
                profiles[profile.id] = profile
            return profiles
        data = items  # fall through to list handling
    if isinstance(data, list):
        for spec in data:
            profile = ConnectionProfile(**spec)
            profiles[profile.id] = profile
    return profiles


def load_profiles() -> dict[str, ConnectionProfile]:
    """Load all connection profiles, always including a ``default``."""
    profiles = _coerce_profiles(_raw_registry_data())
    if DEFAULT_PROFILE_ID not in profiles:
        profiles[DEFAULT_PROFILE_ID] = _default_profile()
    return profiles


_profiles: Optional[dict[str, ConnectionProfile]] = None


def get_profiles() -> dict[str, ConnectionProfile]:
    """Return the cached profile registry (loaded once)."""
    global _profiles
    if _profiles is None:
        _profiles = load_profiles()
        logger.info("Loaded %d openLCA connection profile(s): %s",
                    len(_profiles), ", ".join(sorted(_profiles)))
    return _profiles


def get_profile(profile_id: Optional[str]) -> ConnectionProfile:
    """Resolve a profile id (None -> ``default``). Raises KeyError if unknown."""
    profiles = get_profiles()
    pid = profile_id or DEFAULT_PROFILE_ID
    if pid not in profiles:
        raise KeyError(pid)
    return profiles[pid]


def reset_profiles() -> None:
    """Drop the cached registry (tests / config reload)."""
    global _profiles
    _profiles = None
