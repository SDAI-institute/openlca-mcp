"""
In-memory registry for live calculation results.

openLCA ``Result`` objects live on the IPC server and must be explicitly
disposed. The MCP server hands agents a stable ``result_id`` so follow-up tools
(contributions, inventory, Sankey, normalization, ...) can operate on a stored
result without recomputing.

Replaces the previous ``str(id(result))`` scheme, which was fragile (CPython may
reuse ``id()`` after garbage collection) and carried no calculation context.
"""

import uuid
import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class StoredResult:
    """A live calculation result plus the context needed to interpret it."""

    result_id: str
    result: Any
    impacts: List[Dict[str, Any]] = field(default_factory=list)
    context: Optional[Dict[str, Any]] = None
    system_ref: Any = None
    method: Any = None
    connection_id: Optional[str] = None


class ResultStore:
    """Registry of live results keyed by a generated ``res_<hex>`` id."""

    def __init__(self) -> None:
        self._results: Dict[str, StoredResult] = {}
        self._lock = threading.RLock()

    def add(
        self,
        result: Any,
        *,
        impacts: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
        system_ref: Any = None,
        method: Any = None,
        connection_id: Optional[str] = None,
    ) -> StoredResult:
        """Store a result and return its StoredResult (with a fresh result_id)."""
        if connection_id is None:
            # Lazy import avoids coupling the store to transport setup at module load.
            from .lca_client import get_active_profile_id

            connection_id = get_active_profile_id()
        result_id = f"res_{uuid.uuid4().hex[:12]}"
        stored = StoredResult(
            result_id=result_id,
            result=result,
            impacts=impacts or [],
            context=context,
            system_ref=system_ref,
            method=method,
            connection_id=connection_id,
        )
        with self._lock:
            self._results[result_id] = stored
        return stored

    def get(self, result_id: str, connection_id: Optional[str] = None) -> Optional[StoredResult]:
        """Return a stored result, optionally enforcing connection affinity."""
        with self._lock:
            stored = self._results.get(result_id)
        if stored is None:
            return None
        if connection_id is not None and stored.connection_id not in (None, connection_id):
            return None
        return stored

    def __contains__(self, result_id: str) -> bool:
        with self._lock:
            return result_id in self._results

    def dispose(self, result_id: str, connection_id: Optional[str] = None) -> bool:
        """Dispose one result, optionally only when it belongs to a connection."""
        with self._lock:
            stored = self._results.get(result_id)
            if stored is None:
                return False
            if connection_id is not None and stored.connection_id not in (None, connection_id):
                return False
            self._results.pop(result_id, None)
        _safe_dispose(stored)
        return True

    def dispose_all(self, connection_id: Optional[str] = None) -> int:
        """Dispose all tracked results, optionally scoped to one connection."""
        with self._lock:
            if connection_id is None:
                selected = list(self._results.values())
                self._results.clear()
            else:
                selected = [
                    stored for stored in self._results.values()
                    if stored.connection_id in (None, connection_id)
                ]
                for stored in selected:
                    self._results.pop(stored.result_id, None)
        for stored in selected:
            _safe_dispose(stored)
        return len(selected)


def _safe_dispose(stored: StoredResult) -> None:
    dispose = getattr(stored.result, "dispose", None)
    if callable(dispose):
        try:
            dispose()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Error disposing %s: %s", stored.result_id, exc)


# Process-wide store shared by all handlers.
store = ResultStore()
