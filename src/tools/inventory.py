"""Phase 2 — Life Cycle Inventory: database write tools.

Writes are blocked when the targeted connection profile is read-only (the
OLCAClient enforces it via WriteBlocked). Creating on the local default profile
lets you inspect/verify the new entity in the openLCA UI.
"""

from __future__ import annotations

from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from .. import handlers
from ..app import call_handler, write_tool
from ..schemas import arr


class ProcessExchange(BaseModel):
    """Validated exchange payload for process creation."""

    model_config = ConfigDict(extra="forbid")

    flow_id: str
    amount: float
    is_input: bool
    is_quantitative_reference: bool = False
    provider_id: Optional[str] = None
    formula: Optional[str] = None
    unit_id: Optional[str] = None
    flow_property_id: Optional[str] = None


ProviderPolicy = Literal["prefer", "only", "ignore"]
PreferredProcessType = Literal["LCI_RESULT", "UNIT_PROCESS"]
Cutoff = Annotated[float, Field(ge=0.0, le=1.0)]


@write_tool(
    "create_product_flow",
    "Create a new product flow (Mass property, kg unit). Use to define the product "
    "under study or intermediate products. WRITE: blocked on read-only connections.",
    {"flow": {"type": "object", "description": "The newly created product flow."}},
)
async def create_product_flow(
    name: str, description: str = "", connection: Optional[str] = None
) -> dict:
    return await call_handler(
        handlers.handle_create_product_flow, {"name": name, "description": description}, connection
    )


@write_tool(
    "create_process",
    "Create a unit process with inputs and outputs. Each exchange: flow_id (id "
    "preferred, name accepted), amount, is_input, optional is_quantitative_reference, "
    "optional provider_id. The exchange amount is interpreted in the flow's REFERENCE "
    "unit (e.g. t*km for transport, kg for mass); pass optional 'formula' (e.g. "
    "'0.065*500') to store an amount formula, or 'unit_id'/'flow_property_id' to record "
    "the amount in a non-reference property the flow defines. Returns 'warnings' if the "
    "process's Mass-property inputs and outputs don't balance (openLCA does not check "
    "this automatically). WRITE: blocked on read-only connections.",
    {
        "process": {"type": "object", "description": "The newly created unit process."},
        "warnings": arr(
            {"type": "string", "description": "Mass-balance warnings, if any; empty if balanced."}
        ),
    },
)
async def create_process(
    name: str,
    exchanges: list[ProcessExchange],
    description: str = "",
    connection: Optional[str] = None,
) -> dict:
    return await call_handler(
        handlers.handle_create_process,
        {
            "name": name,
            "description": description,
            "exchanges": [exchange.model_dump(exclude_none=True) for exchange in exchanges],
        },
        connection,
    )


@write_tool(
    "create_product_system",
    "Create a product system from a process (auto-links providers). Returns the product "
    "system id for calculations and explicitly reports any unlinked product-input exchanges "
    "that would truncate upstream burdens. Provide process_id (preferred) or process_name. "
    "Optional cutoff (0-1, e.g. 0.05 for a 5% cut-off), default_providers "
    "('prefer'|'only'|'ignore') and preferred_type ('LCI_RESULT'|'UNIT_PROCESS'). "
    "WRITE: blocked on read-only connections.",
    {
        "product_system": {"type": "object", "description": "The created product system."},
        "unlinked_exchanges": arr({"type": "object", "description": "Unlinked product input exchange."}),
        "warnings": arr({"type": "string", "description": "Scientific boundary warnings."}),
    },
)
async def create_product_system(
    process_id: Optional[str] = None,
    process_name: Optional[str] = None,
    cutoff: Optional[Cutoff] = None,
    default_providers: ProviderPolicy = "prefer",
    preferred_type: PreferredProcessType = "LCI_RESULT",
    connection: Optional[str] = None,
) -> dict:
    return await call_handler(
        handlers.handle_create_product_system,
        {
            "process_id": process_id,
            "process_name": process_name,
            "cutoff": cutoff,
            "default_providers": default_providers,
            "preferred_type": preferred_type,
        },
        connection,
    )
