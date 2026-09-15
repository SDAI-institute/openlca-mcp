"""Runtime dependency contracts required by the MCP handler layer."""

import inspect

from openlca_ipc.data import DataBuilder


def test_openlca_ipc_create_exchange_supports_extended_metadata():
    """The process MCP passes optional unit/property/formula metadata."""
    parameters = inspect.signature(DataBuilder.create_exchange).parameters
    required = {"unit", "flow_property", "formula"}
    missing = required.difference(parameters)
    assert not missing, (
        "Installed openlca-ipc is incompatible with create_process; "
        f"missing DataBuilder.create_exchange parameters: {sorted(missing)}"
    )
