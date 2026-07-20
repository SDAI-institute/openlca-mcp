"""
OpenLCA client management for the MCP server.

Owns one :class:`~openlca_ipc.OLCAClient` per connection profile (see
``connections.py``) so a single server can talk to several openLCA instances.
Clients are cached by profile id; ``get_client()`` with no argument returns the
``default`` profile's client for backward compatibility. Kept separate from the
server/transport code so handlers and tests can import the accessor without
pulling in the whole MCP stack.

Environment variables:
    OPENLCA_PORT       default profile IPC port (default: 8080)
    OPENLCA_HOST       default profile IPC host (default: localhost)
    OPENLCA_READ_ONLY  default profile safe mode — every database mutation
                       raises WriteBlocked (default: false).
    OPENLCA_TIMEOUT    per-call IPC timeout in seconds (default: 15).
    OPENLCA_CONNECTIONS[_FILE]  extra named profiles (see connections.py).
"""

import os
import logging
from contextvars import ContextVar
from typing import Optional

from openlca_ipc import OLCAClient

from .connections import get_profile

logger = logging.getLogger(__name__)

# Cache of live clients, keyed by connection-profile id.
_clients: dict[str, OLCAClient] = {}

# The profile id a no-argument ``get_client()`` should resolve to. Set per request
# by the tool layer so the existing handlers (which call ``get_client()``) target
# the caller's chosen connection without changing their signatures.
_active_profile: ContextVar[Optional[str]] = ContextVar("openlca_active_profile", default=None)

_TRUTHY = {"1", "true", "yes", "on"}


def set_active_profile(profile_id: Optional[str]):
    """Set the active profile for the current context; returns a reset token."""
    return _active_profile.set(profile_id)


def reset_active_profile(token) -> None:
    """Restore the active profile from a token returned by set_active_profile."""
    _active_profile.reset(token)

#: Default (connect + read) timeout, in seconds, applied to every IPC HTTP call.
#: olca_ipc issues blocking ``requests`` calls with no timeout, so an
#: unreachable or black-holed openLCA host would otherwise hang the caller
#: indefinitely — which, behind a reverse proxy/tunnel, surfaces to clients as a
#: 502. A bounded timeout lets handlers return a clean CONNECTION_FAILED instead.
_DEFAULT_TIMEOUT_S = float(os.getenv("OPENLCA_TIMEOUT", "15"))


def read_only_enabled() -> bool:
    """Return True when OPENLCA_READ_ONLY requests safe (write-blocking) mode."""
    return os.getenv("OPENLCA_READ_ONLY", "false").strip().lower() in _TRUTHY


def _apply_session_timeout(raw_client, timeout: float) -> None:
    """Force a default timeout on a raw ``ipc.Client``'s HTTP session.

    olca_ipc's ``rpc_call`` does ``self._s.post(url, ...)`` with no timeout.
    Wrapping ``Session.request`` (which every verb funnels through) injects a
    default ``timeout`` so a stalled connection fails fast rather than blocking
    the server's event loop until a proxy gives up with a 502.
    """
    session = getattr(raw_client, "_s", None)
    if session is None or getattr(session, "_olca_timeout_applied", False):
        return
    original_request = session.request

    def request_with_timeout(method, url, **kwargs):
        kwargs.setdefault("timeout", timeout)
        return original_request(method, url, **kwargs)

    session.request = request_with_timeout
    session._olca_timeout_applied = True


def get_client(profile_id: Optional[str] = None) -> OLCAClient:
    """
    Get or create the OpenLCA client for a connection profile.

    ``profile_id`` defaults to the ``default`` profile (built from OPENLCA_HOST /
    OPENLCA_PORT / OPENLCA_READ_ONLY), preserving the original no-argument call.
    For non-localhost hosts (e.g. the MCP server in Docker, openLCA on the host
    machine, or a remote instance) the underlying ipc.Client is redirected to
    the explicit URL. Clients are cached per profile.
    """
    if profile_id is None:
        profile_id = _active_profile.get()
    profile = get_profile(profile_id)
    cached = _clients.get(profile.id)
    if cached is not None:
        return cached

    client = OLCAClient(port=profile.port, read_only=profile.read_only)

    # OLCAClient connects to localhost; redirect for remote/Docker hosts.
    if profile.host not in ("localhost", "127.0.0.1"):
        import olca_ipc as ipc

        url = f"http://{profile.host}:{profile.port}"
        # olca_ipc.Client(endpoint) uses a str endpoint verbatim as the URL and
        # treats an int as a localhost port. Pass the full URL as a positional
        # str — there is no `url=` keyword, and the old try/except silently fell
        # back to localhost inside Docker.
        raw = ipc.Client(url)
        _rebind_client(client, raw, profile.read_only)
        logger.info("OpenLCA IPC client[%s] redirected -> %s", profile.id, url)

    # Bound every IPC call so an unreachable host fails fast (no 502 hangs).
    _apply_session_timeout(client._raw_client, _DEFAULT_TIMEOUT_S)

    logger.info(
        "Connected to openLCA[%s] at %s:%s (read_only=%s)",
        profile.id, profile.host, profile.port, profile.read_only,
    )
    _clients[profile.id] = client
    return client


#: Manager attributes on OLCAClient that capture the IPC client at construction.
_MANAGER_ATTRS = (
    "search",
    "data",
    "systems",
    "calculate",
    "results",
    "contributions",
    "uncertainty",
    "parameters",
    "export",
)


def _rebind_client(olca_client: OLCAClient, raw, read_only: bool) -> None:
    """
    Point an OLCAClient (and all its managers) at a new raw ipc.Client.

    Managers capture ``self.client`` at construction, so reassigning only
    ``OLCAClient.client`` would leave them bound to the original connection.
    This rebinds the effective (guarded when read_only) client everywhere.
    """
    if read_only:
        from openlca_ipc.client import _ReadOnlyGuard

        effective = _ReadOnlyGuard(raw)
    else:
        effective = raw

    olca_client._raw_client = raw
    olca_client.client = effective
    for attr in _MANAGER_ATTRS:
        manager = getattr(olca_client, attr, None)
        if manager is not None and hasattr(manager, "client"):
            manager.client = effective


def reset_client() -> None:
    """Drop all cached clients (used by tests and on shutdown)."""
    _clients.clear()
