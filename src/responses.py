"""
Response envelopes and serializers for MCP tool output.

Every handler returns a single JSON ``TextContent``. Success and error
envelopes both carry a ``success`` boolean (backwards-compatible with the
original server); errors additionally carry the structured agent fields from
:class:`openlca_ipc.agent.errors.OLCAError` (``error_code``, ``recoverable``,
``suggested_next_actions``) so an agent can branch on failures.

Serializers convert openLCA / openlca-ipc objects (``o.Ref``, ``TreeNode``,
``ContributionItem``, ``UncertaintyResult``) into JSON-ready dicts. Non-finite
floats (e.g. a NaN share when a category total is zero) are coerced to ``None``
so the output is always valid JSON.
"""

import json
import math
import logging
from typing import Any, Dict, List

from mcp.types import CallToolResult, TextContent

from openlca_ipc.agent.errors import OLCAError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Envelopes
# ---------------------------------------------------------------------------

def _dump(payload: Dict[str, Any]) -> List[TextContent]:
    return [TextContent(type="text", text=json.dumps(_json_safe(payload), indent=2))]


def success(payload: Dict[str, Any]) -> List[TextContent]:
    """Wrap a payload dict as a successful tool response."""
    body = {"success": True}
    body.update(payload)
    return _dump(body)


def error(exc: Exception, *, error_code: str = "INTERNAL_ERROR") -> List[TextContent]:
    """
    Build an error envelope.

    OLCAError instances contribute their structured fields; any other exception
    becomes a generic, non-recoverable envelope with the given error_code.
    """
    if isinstance(exc, OLCAError):
        body = {"success": False}
        body.update(exc.to_dict())
        return _dump(body)

    body = {
        "success": False,
        "is_error": True,
        "error_code": error_code,
        "message": str(exc),
        "recoverable": False,
        "suggested_next_actions": [],
    }
    return _dump(body)


def parse_json_content(contents: List[TextContent]) -> Dict[str, Any] | None:
    """Parse the first JSON text block emitted by legacy handlers, if present."""
    if not contents:
        return None
    first = contents[0]
    if not isinstance(first, TextContent):
        return None
    try:
        parsed = json.loads(first.text)
    except Exception:
        return None
    return parsed if isinstance(parsed, dict) else None


def to_call_tool_result(contents: List[TextContent]) -> CallToolResult:
    """Adapt legacy ``TextContent`` envelopes to modern MCP ``CallToolResult``."""
    body = parse_json_content(contents)
    is_error = bool(body and body.get("success") is False)
    return CallToolResult(
        content=contents,
        structuredContent=body,
        isError=is_error,
    )


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

def ref_to_dict(ref: Any) -> Any:
    """Compact an o.Ref-like object to {id, name, category}; pass dicts through."""
    if ref is None:
        return None
    if isinstance(ref, dict):
        return ref
    out: Dict[str, Any] = {}
    for attr in ("id", "name", "category"):
        value = getattr(ref, attr, None)
        if value is not None:
            out[attr] = value
    return out or str(ref)


def tree_to_dict(node: Any) -> Dict[str, Any]:
    """Serialize a ContributionAnalyzer.TreeNode (recursively)."""
    return {
        "name": node.name,
        "amount": node.amount,
        "direct": node.direct,
        "share": node.share,
        "ref": ref_to_dict(node.ref),
        "children": [tree_to_dict(child) for child in node.children],
    }


def contribution_to_dict(item: Any) -> Dict[str, Any]:
    """Serialize a ContributionAnalyzer.ContributionItem."""
    return {
        "name": item.name,
        "amount": item.amount,
        "share": item.share,
        "ref": ref_to_dict(item.ref),
    }


def uncertainty_to_dict(name: str, result: Any) -> Dict[str, Any]:
    """Serialize an UncertaintyResult's stats (dropping the raw values array)."""
    return {
        "impact": name,
        "mean": getattr(result, "mean", None),
        "std": getattr(result, "std", None),
        "median": getattr(result, "median", None),
        "percentile_5": getattr(result, "percentile_5", None),
        "percentile_95": getattr(result, "percentile_95", None),
        "cv": getattr(result, "cv", None),
        "iterations": len(getattr(result, "values", []) or []),
    }


# ---------------------------------------------------------------------------
# JSON safety
# ---------------------------------------------------------------------------

def _json_safe(obj: Any) -> Any:
    """Recursively coerce non-finite floats to None so output is valid JSON."""
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    return obj
