"""
openLCA MCP tool modules, grouped by ISO-14040 phase.

Importing this package registers every tool on the FastMCP server (each module's
``@ro_tool`` / ``@write_tool`` decorators run on import). The tools are thin typed
wrappers that delegate to the proven handlers in ``src/handlers.py`` via the
``app.call_handler`` bridge (identity gating + connection routing + event-loop
offload), so the openLCA logic and its tests are reused unchanged.
"""

from . import goal_scope, interpretation, inventory, jobs, lca_impact, lifecycle  # noqa: F401
