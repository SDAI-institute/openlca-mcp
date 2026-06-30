#!/usr/bin/env python3
"""
OpenLCA MCP Server for Life Cycle Assessment automation.

Exposes openLCA functionality as MCP tools for AI agents, organized by the four
ISO-14040/14044 LCA phases (Goal & Scope, LCI, LCIA, Interpretation) plus
utilities. This module owns transport wiring only; tool schemas live in
``tool_defs``, handlers in ``handlers``, client management in ``lca_client``,
and the result registry in ``result_store``.

Supported transports:
    - ``stdio``            local subprocess clients such as Claude Desktop
    - ``sse``              legacy HTTP+SSE transport at ``/sse`` + ``/messages/``
    - ``streamable-http``  modern MCP HTTP endpoint at ``/mcp``
    - ``http``             serve both ``/mcp`` and legacy ``/sse`` together

Environment Variables:
    OPENLCA_PORT                  openLCA IPC port (default: 8080)
    OPENLCA_HOST                  openLCA IPC host (default: localhost)
    OPENLCA_READ_ONLY             Block all database writes when truthy
    TRANSPORT                     stdio | sse | streamable-http | http
    MCP_HOST / MCP_PORT           HTTP bind for network transports
    MCP_HTTP_PATH                 Streamable HTTP endpoint path (default: /mcp)
    MCP_SSE_PATH                  Legacy SSE endpoint path (default: /sse)
    MCP_MESSAGE_PATH              Legacy SSE POST path (default: /messages/)
    MCP_ENABLE_STREAMABLE_HTTP    Enable /mcp in TRANSPORT=http mode (default: true)
    MCP_ENABLE_SSE                Enable /sse in TRANSPORT=http mode (default: true)
    MCP_STATELESS_HTTP            Use stateless streamable HTTP sessions (default: true)
    MCP_HTTP_JSON_RESPONSE        Prefer JSON responses for streamable HTTP (default: true)
    MCP_SESSION_IDLE_TIMEOUT      Stateful streamable HTTP idle timeout in seconds
    MCP_DNS_REBINDING_PROTECTION  Enable host/origin validation for HTTP transports
    MCP_ALLOWED_HOSTS             Comma-separated Host allowlist when DNS protection is on
    MCP_ALLOWED_ORIGINS           Comma-separated Origin allowlist when DNS protection is on
    LOG_LEVEL                     Logging level (default: INFO)
"""

from __future__ import annotations

import base64
import json
import logging
import os
import time
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Any

import mcp.server.stdio
import mcp.types as types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.sse import SseServerTransport
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.server.transport_security import TransportSecuritySettings

from . import __version__, telemetry
from .lca_client import get_client
from .result_store import store
from .tool_defs import TOOLS
from .handlers import TOOL_HANDLERS
from . import responses

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

_SERVER_NAME = "openlca-lca-server"
_SERVER_INSTRUCTIONS = (
    "Use these tools for openLCA life-cycle assessment workflows. "
    "Start with test_connection or health_check before calculations. "
    "Call dispose_result when finished with a result_id. "
    "Create and export tools mutate the environment; honor the server's read-only mode."
)
_SERVER_WEBSITE = "https://github.com/SDAI-institute/openlca-mcp"

# Self-contained icon (no external asset) advertised in the MCP serverInfo so
# directories/clients (Smithery, ChatGPT) can render a recognizable mark.
_SERVER_ICON_SVG = (
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'>"
    "<rect width='64' height='64' rx='14' fill='#1f7a3d'/>"
    "<path d='M32 14c-9 6-14 13-14 21a14 14 0 0 0 28 0c0-8-5-15-14-21z' fill='#fff'/>"
    "<path d='M32 20v22' stroke='#1f7a3d' stroke-width='2.5' stroke-linecap='round'/>"
    "<path d='M32 30l7-5M32 36l-7-5' stroke='#1f7a3d' stroke-width='2.5' "
    "stroke-linecap='round' fill='none'/>"
    "</svg>"
)
_SERVER_ICON_DATA_URI = (
    "data:image/svg+xml;base64,"
    + base64.b64encode(_SERVER_ICON_SVG.encode("utf-8")).decode("ascii")
)


def _truthy(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _csv_env(name: str) -> list[str]:
    raw = os.getenv(name, "")
    return [part.strip() for part in raw.split(",") if part.strip()]


def _normalize_http_path(path: str, *, trailing_slash: bool = False) -> str:
    path = path.strip() or "/"
    if not path.startswith("/"):
        path = f"/{path}"
    if trailing_slash:
        return path if path.endswith("/") else f"{path}/"
    return path.rstrip("/") or "/"


def _transport_security_settings() -> TransportSecuritySettings | None:
    enabled = _truthy(os.getenv("MCP_DNS_REBINDING_PROTECTION"), default=False)
    hosts = _csv_env("MCP_ALLOWED_HOSTS")
    origins = _csv_env("MCP_ALLOWED_ORIGINS")
    if not enabled and not hosts and not origins:
        return None
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=enabled,
        allowed_hosts=hosts,
        allowed_origins=origins,
    )


def _parse_idle_timeout() -> float | None:
    raw = os.getenv("MCP_SESSION_IDLE_TIMEOUT", "").strip()
    if not raw:
        return None
    return float(raw)


def _http_mode() -> tuple[bool, bool]:
    transport = os.getenv("TRANSPORT", "stdio").strip().lower()
    if transport == "stdio":
        return False, False
    if transport == "sse":
        return False, True
    if transport in {"streamable-http", "streamable_http"}:
        return True, False
    if transport == "http":
        return (
            _truthy(os.getenv("MCP_ENABLE_STREAMABLE_HTTP"), default=True),
            _truthy(os.getenv("MCP_ENABLE_SSE"), default=True),
        )
    raise ValueError(
        "TRANSPORT must be one of: stdio, sse, streamable-http, streamable_http, http"
    )


# Fail fast on the bug class this refactor fixes: every advertised tool must
# have a handler and vice versa.
_missing_handlers = set(TOOLS) - set(TOOL_HANDLERS)
_missing_defs = set(TOOL_HANDLERS) - set(TOOLS)
if _missing_handlers or _missing_defs:
    raise RuntimeError(
        f"Tool/handler mismatch — missing handlers: {sorted(_missing_handlers)}; "
        f"missing defs: {sorted(_missing_defs)}"
    )

server = Server(
    _SERVER_NAME,
    version=__version__,
    instructions=_SERVER_INSTRUCTIONS,
    website_url=_SERVER_WEBSITE,
    icons=[types.Icon(src=_SERVER_ICON_DATA_URI, mimeType="image/svg+xml", sizes=["any"])],
)


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """Advertise exactly the tools that have handlers."""
    return list(TOOLS.values())


@server.call_tool()
async def call_tool(name: str, arguments: Any) -> types.CallToolResult:
    """Dispatch a tool call to its handler and expose structured MCP results."""
    logger.info("Tool called: %s", name)
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        telemetry.record(name, success=False, error_code="UNKNOWN_TOOL", duration_ms=0)
        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": False,
                            "is_error": True,
                            "error_code": "UNKNOWN_TOOL",
                            "message": f"Unknown tool: {name}",
                            "recoverable": False,
                            "suggested_next_actions": ["list_tools"],
                        },
                        indent=2,
                    ),
                )
            ],
            structuredContent={
                "success": False,
                "is_error": True,
                "error_code": "UNKNOWN_TOOL",
                "message": f"Unknown tool: {name}",
                "recoverable": False,
                "suggested_next_actions": ["list_tools"],
            },
            isError=True,
        )

    start = time.monotonic()
    legacy_result = await handler(arguments or {})
    duration_ms = (time.monotonic() - start) * 1000
    payload = responses.parse_json_content(legacy_result) or {}
    success = payload.get("success", True)
    error_code = payload.get("error_code") if success is False else None
    telemetry.record(name, success=bool(success), error_code=error_code, duration_ms=duration_ms)
    return responses.to_call_tool_result(legacy_result)


def _initialization_options() -> Any:
    return server.create_initialization_options(
        notification_options=NotificationOptions(),
        experimental_capabilities={},
    )


async def _run_stdio_server() -> None:
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, _initialization_options())


async def _run_http_server() -> None:
    from starlette.applications import Starlette
    from starlette.middleware import Middleware
    from starlette.middleware.cors import CORSMiddleware
    from starlette.responses import JSONResponse, Response
    from starlette.routing import Mount, Route
    import uvicorn

    enable_streamable_http, enable_sse = _http_mode()
    if not enable_streamable_http and not enable_sse:
        raise RuntimeError(
            "HTTP mode requires at least one of MCP_ENABLE_STREAMABLE_HTTP or MCP_ENABLE_SSE"
        )

    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8000"))
    http_path = _normalize_http_path(os.getenv("MCP_HTTP_PATH", "/mcp"))
    sse_path = _normalize_http_path(os.getenv("MCP_SSE_PATH", "/sse"))
    message_path = _normalize_http_path(
        os.getenv("MCP_MESSAGE_PATH", "/messages/"),
        trailing_slash=True,
    )
    security_settings = _transport_security_settings()
    session_manager = (
        StreamableHTTPSessionManager(
            app=server,
            json_response=_truthy(os.getenv("MCP_HTTP_JSON_RESPONSE"), default=True),
            stateless=_truthy(os.getenv("MCP_STATELESS_HTTP"), default=True),
            security_settings=security_settings,
            session_idle_timeout=_parse_idle_timeout(),
        )
        if enable_streamable_http
        else None
    )
    sse_transport = (
        SseServerTransport(message_path, security_settings=security_settings)
        if enable_sse
        else None
    )

    async def index(request):
        return JSONResponse(
            {
                "status": "ok",
                "server": "openlca-mcp",
                "version": __version__,
                "transport": os.getenv("TRANSPORT", "stdio").strip().lower(),
                "preferred_endpoint": http_path if enable_streamable_http else sse_path,
                "endpoints": {
                    "mcp": http_path if enable_streamable_http else None,
                    "sse": sse_path if enable_sse else None,
                    "messages": message_path if enable_sse else None,
                    "health": "/health",
                },
            }
        )

    async def health(request):
        return JSONResponse(
            {
                "status": "ok",
                "server": "openlca-mcp",
                "version": __version__,
                "endpoints": {
                    "mcp": http_path if enable_streamable_http else None,
                    "sse": sse_path if enable_sse else None,
                },
            }
        )

    async def handle_sse(request):
        assert sse_transport is not None
        async with sse_transport.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await server.run(streams[0], streams[1], _initialization_options())
        return Response()

    async def streamable_http_app(scope, receive, send):
        assert session_manager is not None
        await session_manager.handle_request(scope, receive, send)

    routes = [
        Route("/", endpoint=index, methods=["GET"]),
        Route("/health", endpoint=health, methods=["GET"]),
    ]
    if enable_streamable_http:
        routes.append(Mount(http_path, app=streamable_http_app))
    if enable_sse:
        routes.append(Route(sse_path, endpoint=handle_sse, methods=["GET"]))
        routes.append(Mount(message_path, app=sse_transport.handle_post_message))

    @asynccontextmanager
    async def lifespan(app: Starlette):
        async with AsyncExitStack() as stack:
            if session_manager is not None:
                await stack.enter_async_context(session_manager.run())
            yield

    app = Starlette(
        routes=routes,
        lifespan=lifespan,
        middleware=[
            Middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
                allow_headers=["*"],
                expose_headers=["Mcp-Session-Id"],
            )
        ],
    )

    logger.info("HTTP MCP server -> http://%s:%s%s", host, port, http_path)
    if enable_sse:
        logger.info("Legacy SSE endpoint -> http://%s:%s%s", host, port, sse_path)

    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
    await uvicorn.Server(config).serve()


async def main() -> None:
    """Run the MCP server with the configured transport."""
    transport = os.getenv("TRANSPORT", "stdio").strip().lower()
    logger.info("Starting OpenLCA MCP Server v%s (transport=%s)", __version__, transport)
    logger.info(
        "OpenLCA: %s:%s",
        os.getenv("OPENLCA_HOST", "localhost"),
        os.getenv("OPENLCA_PORT", "8080"),
    )
    telemetry.setup(__version__, transport)

    try:
        if get_client().test_connection():
            logger.info("Successfully connected to openLCA")
        else:
            logger.warning("Could not verify connection to openLCA")
    except Exception as exc:
        logger.error("Failed to connect to openLCA: %s", exc)
        logger.error("Make sure openLCA is running with the IPC server started")

    try:
        if transport == "stdio":
            await _run_stdio_server()
        else:
            await _run_http_server()
    finally:
        disposed = store.dispose_all()
        if disposed:
            logger.info("Disposed %s tracked result(s) on shutdown", disposed)


def run() -> None:
    """Synchronous entry point used by the installed CLI and uvx."""
    import asyncio

    asyncio.run(main())


if __name__ == "__main__":
    run()
