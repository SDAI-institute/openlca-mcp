"""
Reusable JSON-schema fragments for tool output schemas.

Output schemas are intentionally permissive (``additionalProperties: true`` and
only ``success`` required) so the shared error envelope
(``{success: false, error_code, ...}``) validates against the same schema —
strict clients (ChatGPT developer mode) reject a result whose
``structuredContent`` does not conform to the declared ``outputSchema``.
"""

from __future__ import annotations

from typing import Optional


def arr(items: dict) -> dict:
    return {"type": "array", "items": items}


#: Compact openLCA entity reference (see responses.ref_to_dict).
REF = {
    "type": "object",
    "description": "Compact openLCA entity reference.",
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "category": {"type": "string"},
    },
}

#: A single impact result row (see handlers._impact_to_dict).
IMPACT = {
    "type": "object",
    "properties": {
        "name": {"type": ["string", "null"]},
        "category": REF,
        "category_id": {"type": ["string", "null"]},
        "amount": {"type": ["number", "null"]},
        "unit": {"type": ["string", "null"]},
    },
}


def out(properties: Optional[dict] = None) -> dict:
    """Build a strict-but-permissive tool output schema (``success`` + fields)."""
    props = {"success": {"type": "boolean"}}
    if properties:
        props.update(properties)
    return {
        "type": "object",
        "properties": props,
        "required": ["success"],
        "additionalProperties": True,
    }
