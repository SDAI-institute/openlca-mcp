"""Server-level dispatch and the tool/handler single-source-of-truth guard."""

import pytest

from src.server import list_tools, call_tool
from src.tool_defs import TOOLS
from src.handlers import TOOL_HANDLERS
from tests.conftest import payload


def test_tools_and_handlers_match():
    """Regression guard: every advertised tool has a handler and vice versa.

    This is the exact bug class the refactor fixed (3 advertised stub tools
    had no handler and returned 'Unknown tool').
    """
    assert set(TOOLS) == set(TOOL_HANDLERS)


@pytest.mark.asyncio
async def test_list_tools_returns_all():
    tools = await list_tools()
    assert {t.name for t in tools} == set(TOOL_HANDLERS)
    assert all(t.outputSchema is not None for t in tools)


@pytest.mark.asyncio
async def test_unknown_tool_envelope():
    result = await call_tool("does_not_exist", {})
    body = payload(result)
    assert result.isError is True
    assert body["success"] is False
    assert body["error_code"] == "UNKNOWN_TOOL"
    assert "list_tools" in body["suggested_next_actions"]


@pytest.mark.asyncio
async def test_call_tool_dispatches(patch_client):
    patch_client.test_connection.return_value = True
    result = await call_tool("test_connection", {})
    body = payload(result)
    assert result.isError is False
    assert result.structuredContent == body
    assert body["success"] is True
    assert body["connected"] is True
    assert body["port"] == 8080
