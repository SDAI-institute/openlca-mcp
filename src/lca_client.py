"""
OpenLCA client management for the MCP server.

Owns the process-wide :class:`~openlca_ipc.OLCAClient` singleton and the
environment-driven configuration (port, host, read-only safe mode). Kept
separate from the server/transport code so handlers and tests can import the
client accessor without pulling in the whole MCP stack.

Environment variables:
    OPENLCA_PORT       IPC server port (default: 8080)
    OPENLCA_HOST       IPC server host (default: localhost)
    OPENLCA_READ_ONLY  If truthy, connect in safe mode so every database
                       mutation raises WriteBlocked (default: false).
"""

import os
import logging
from typing import Optional

from openlca_ipc import OLCAClient

logger = logging.getLogger(__name__)

# Process-wide client singleton.
_client: Optional[OLCAClient] = None

_TRUTHY = {"1", "true", "yes", "on"}

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


def get_client() -> OLCAClient:
    """
    Get or create the shared OpenLCA client.

    Honors OPENLCA_PORT / OPENLCA_HOST / OPENLCA_READ_ONLY. For non-localhost
    hosts (e.g. the MCP server in Docker, openLCA on the host machine) the
    underlying ipc.Client is redirected to the explicit URL.
    """
    global _client
    if _client is None:
        port = int(os.getenv("OPENLCA_PORT", "8080"))
        host = os.getenv("OPENLCA_HOST", "localhost")
        read_only = read_only_enabled()

        _client = OLCAClient(port=port, read_only=read_only)

        # OLCAClient connects to localhost; redirect for remote/Docker hosts.
        if host not in ("localhost", "127.0.0.1"):
            import olca_ipc as ipc

            url = f"http://{host}:{port}"
            # olca_ipc.Client(endpoint) uses a str endpoint verbatim as the URL
            # and treats an int as a localhost port. Pass the full URL as a
            # positional str — there is no `url=` keyword, and the old
            # try/except silently fell back to localhost inside Docker.
            raw = ipc.Client(url)
            _rebind_client(_client, raw, read_only)
            logger.info("OpenLCA IPC client redirected -> %s", url)

        # Bound every IPC call so an unreachable host fails fast (no 502 hangs).
        _apply_session_timeout(_client._raw_client, _DEFAULT_TIMEOUT_S)

        logger.info(
            "Connected to openLCA at %s:%s (read_only=%s)", host, port, read_only
        )
    return _client


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
    """Drop the cached client (used by tests and on shutdown)."""
    global _client
    _client = None
