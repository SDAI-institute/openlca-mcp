#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smoke check that the MCP server is wired to the openlca-ipc library correctly.

This is a standalone script (not collected by pytest). It verifies imports and
that handlers call the expected library methods, without needing a running
openLCA server. Run: python test_integration.py
"""

import sys
import inspect

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

print("Testing MCP Server Integration with openlca-ipc library\n")
print("=" * 60)

# Test 1: library import
print("\n1. Testing library import...")
try:
    from openlca_ipc import OLCAClient  # noqa: F401
    import openlca_ipc

    print(f"   OK imported OLCAClient (openlca-ipc {openlca_ipc.__version__})")
    assert openlca_ipc.__version__ >= "0.4.0", "expected openlca-ipc >= 0.4.0"
except Exception as e:
    print(f"   FAIL import: {e}")
    sys.exit(1)

# Test 2: agent layer present
print("\n2. Testing agent layer...")
try:
    from openlca_ipc import (  # noqa: F401
        ResultSummary,
        EntitySummary,
        CalculationContext,
        health_check,
        check_result_consistency,
    )

    print("   OK agent layer (ResultSummary, health_check, CalculationContext, ...)")
except Exception as e:
    print(f"   FAIL agent layer: {e}")
    sys.exit(1)

# Test 3: server modules import and tool/handler sets match
print("\n3. Testing server module split...")
try:
    from src.server import list_tools, call_tool  # noqa: F401
    from src.lca_client import get_client  # noqa: F401
    from src.tool_defs import TOOLS
    from src.handlers import TOOL_HANDLERS

    print(f"   OK server imports ({len(TOOLS)} tools)")
    assert set(TOOLS) == set(TOOL_HANDLERS), "tool/handler set mismatch"
    print("   OK every advertised tool has a handler")
except Exception as e:
    print(f"   FAIL server import: {e}")
    sys.exit(1)

# Test 4: handlers call the library
print("\n4. Testing handler integration...")
try:
    from src import handlers

    checks = {
        "handle_search_flows": "client.search.find_flows",
        "handle_calculate_impacts": "client.calculate.simple_calculation",
        "handle_create_process": "client.data.create_process",
        "handle_get_contribution_tree": "client.contributions.get_contribution_tree",
        "handle_get_inventory_results": "client.results.get_inventory",
        "handle_compare_systems": "client.calculate.compare_systems",
    }
    for fn_name, needle in checks.items():
        source = inspect.getsource(getattr(handlers, fn_name))
        assert needle in source, f"{fn_name} should call {needle}"
        print(f"   OK {fn_name} -> {needle}")
except Exception as e:
    print(f"   FAIL handler inspection: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("INTEGRATION VERIFICATION COMPLETE")
print("=" * 60)
print(
    "\nArchitecture:\n"
    "  AI Agents / MCP clients\n"
    "      v\n"
    "  MCP Server (src/server.py -> stdio / streamable HTTP / SSE)\n"
    "      v\n"
    "  Dispatch layer (tool_defs, handlers, responses)\n"
    "      v\n"
    "  openlca-ipc library (managers + agent layer)\n"
    "      v\n"
    "  openLCA IPC Server -> openLCA Desktop"
)
