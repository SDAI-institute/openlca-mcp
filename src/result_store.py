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


class ResultStore:
    """Registry of live results keyed by a generated ``res_<hex>`` id."""

    def __init__(self) -> None:
        self._results: Dict[str, StoredResult] = {}

    def add(
        self,
        result: Any,
        *,
        impacts: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
        system_ref: Any = None,
        method: Any = None,
    ) -> StoredResult:
        """Store a result and return its StoredResult (with a fresh result_id)."""
        result_id = f"res_{uuid.uuid4().hex[:12]}"
        stored = StoredResult(
            result_id=result_id,
            result=result,
            impacts=impacts or [],
            context=context,
            system_ref=system_ref,
            method=method,
        )
        self._results[result_id] = stored
        return stored

    def get(self, result_id: str) -> Optional[StoredResult]:
        """Return the StoredResult for an id, or None if unknown."""
        return self._results.get(result_id)

    def __contains__(self, result_id: str) -> bool:
        return result_id in self._results

    def dispose(self, result_id: str) -> bool:
        """
        Dispose one result and drop it from the registry.

        Returns True if the id was known, False otherwise. Disposal errors are
        logged but do not prevent removal from the registry.
        """
        stored = self._results.pop(result_id, None)
        if stored is None:
            return False
        _safe_dispose(stored)
        return True

    def dispose_all(self) -> int:
        """Dispose every stored result. Returns the count disposed."""
        count = 0
        for stored in list(self._results.values()):
            _safe_dispose(stored)
            count += 1
        self._results.clear()
        return count


def _safe_dispose(stored: StoredResult) -> None:
    dispose = getattr(stored.result, "dispose", None)
    if callable(dispose):
        try:
            dispose()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Error disposing %s: %s", stored.result_id, exc)


# Process-wide store shared by all handlers.
store = ResultStore()
