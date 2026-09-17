"""
FastMCP application for the openLCA MCP server.

The FastMCP rewrite of the low-level ``server.py``. This module owns the server
object, auth, telemetry, transport, the request→connection bridge, and the two
utility "probe" tools. The remaining tools live in ``src/tools/`` and are
registered (via their ``@mcp.tool`` decorators) when this module imports them at
the bottom.

Design carried over from the low-level server:
  * Strict ``output_schema`` (``additionalProperties: true`` + ``required:
    ["success"]``) so the shared error envelope validates in ChatGPT dev mode.
  * Per-call identity → connection-profile authorization (auth.py + connections.py).
  * Blocking openLCA IPC calls are offloaded with ``anyio.to_thread`` so a slow
    instance never blocks the event loop; identity is resolved in the async
    context *before* offloading.
"""

from __future__ import annotations

import base64
import logging
import os
import time
from typing import Any, Awaitable, Callable, Optional

import anyio
from fastmcp import FastMCP
from fastmcp.server.auth import AccessToken, TokenVerifier
from fastmcp.server.dependencies import get_access_token
from fastmcp.server.middleware import Middleware, MiddlewareContext
from mcp.types import ToolAnnotations
from starlette.middleware import Middleware as StarletteMiddleware

from openlca_ipc import health_check as _health_check

from . import __version__, lca_client, responses, telemetry
from .auth import (
    ANONYMOUS, AuthError, Identity, auth_enabled, resolve_identity, resolve_profile,
)
from .connections import ConnectionProfile, get_profiles
from .lca_client import get_client
from .job_runtime import connection_lock, jobs
from .schemas import out

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

_SERVER_NAME = "openlca-lca-server"
_SERVER_INSTRUCTIONS = (
    "Use these tools for openLCA life-cycle assessment workflows. "
    "Start with test_connection or health_check before calculations. "
    "Modern MCP 2026-07-28 clients may run calculations, product-system creation, "
    "comparisons, Monte Carlo, scenarios, and exports as native Tasks when enabled. "
    "Older clients can use the *_async compatibility tools and poll get_job_status / get_job_result. "
    "Call dispose_result when finished with a result_id. "
    "Create and export tools mutate the environment; honor the server's read-only mode. "
    "Pass an optional `connection` to target a specific openLCA instance."
)
_SERVER_WEBSITE = "https://github.com/SDAI-institute/openlca-mcp"
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

NATIVE_TASKS_ENABLED = os.getenv("OPENLCA_NATIVE_TASKS_ENABLED", "false").strip().lower() in (
    "1", "true", "yes", "on"
)
NATIVE_TASKS_CONCURRENCY = max(1, int(os.getenv("OPENLCA_NATIVE_TASKS_CONCURRENCY", "2")))
NATIVE_TASK_TOOL_NAMES = {
    "calculate_impacts",
    "create_product_system",
    "compare_systems",
    "run_monte_carlo",
    "run_scenario_analysis",
    "export_results",
}


# ---------------------------------------------------------------------------
# Auth: API key -> Identity (only enforced when keys are configured)
# ---------------------------------------------------------------------------

class _OpenLCATokenVerifier(TokenVerifier):
    """Validate a bearer token against the configured API keys."""

    async def verify_token(self, token: str) -> Optional[AccessToken]:
        identity = resolve_identity(token)
        if identity is None or identity.anonymous:
            return None
        return AccessToken(
            token=token, client_id=identity.tenant_id, scopes=[],
            claims={"tenant_id": identity.tenant_id},
        )


def current_identity() -> Identity:
    """Resolve the caller's identity from the bearer token, or ANONYMOUS (open mode)."""
    try:
        token = get_access_token()
    except Exception:
        token = None
    if token is not None:
        identity = resolve_identity(token.token)
        if identity is not None:
            return identity
    return ANONYMOUS


def _resolve(connection: Optional[str]) -> tuple[Any, ConnectionProfile]:
    """Identity-gated (client, profile) for a connection. Raises AuthError on denial."""
    identity = current_identity()
    profile = resolve_profile(identity, connection)  # raises Forbidden/Unknown
    return get_client(profile.id), profile


def resolve_client(connection: Optional[str]):
    """Identity-gated client for a connection profile. Raises AuthError on denial."""
    client, _ = _resolve(connection)
    return client


# ---------------------------------------------------------------------------
# Bridge: run an existing dict-in / TextContent-out handler as a FastMCP tool.
# Identity/profile are resolved in the async context; the (synchronous-bodied)
# handler is then driven inside a worker thread with the active profile set, so a
# slow IPC call never blocks the event loop.
# ---------------------------------------------------------------------------

def _drive(coro) -> Any:
    """Drive a coroutine that contains no awaits to completion, returning its value."""
    try:
        coro.send(None)
    except StopIteration as stop:
        return stop.value
    coro.close()
    raise RuntimeError("handler unexpectedly awaited inside the worker thread")


def _locked_call(connection_id: str, fn: Callable[[], Any]) -> Any:
    """Run a synchronous IPC operation under its connection-profile lock."""
    with connection_lock(connection_id):
        return fn()


def _execute_handler_sync(
    handler: Callable[[dict], Awaitable[list]],
    arguments: dict,
    profile: ConnectionProfile,
    *,
    acquire_lock: bool = True,
) -> dict[str, Any]:
    """Drive one handler under its captured connection profile.

    Foreground calls acquire the profile lock here. Background jobs already hold
    the same lock in ``JobManager`` and pass ``acquire_lock=False``.
    """
    def _invoke() -> dict[str, Any]:
        token = lca_client.set_active_profile(profile.id)
        try:
            contents = _drive(handler(dict(arguments)))
        finally:
            lca_client.reset_active_profile(token)
        body = responses.parse_json_content(contents)
        return body if body is not None else {"success": True}

    if acquire_lock:
        with connection_lock(profile.id):
            return _invoke()
    return _invoke()


async def call_handler(
    handler: Callable[[dict], Awaitable[list]],
    arguments: dict,
    connection: Optional[str],
) -> dict[str, Any]:
    """Gate the connection, then run ``handler(arguments)`` off the event loop."""
    try:
        _, profile = _resolve(connection)
    except AuthError as exc:
        return responses.error_body(exc, error_code=exc.error_code)

    return await anyio.to_thread.run_sync(
        lambda: _execute_handler_sync(handler, arguments, profile)
    )


def submit_handler_job(
    tool_name: str,
    handler: Callable[[dict], Awaitable[list]],
    arguments: dict,
    connection: Optional[str],
) -> dict[str, Any]:
    """Authorize and enqueue a long handler while preserving profile + tenant affinity."""
    identity = current_identity()
    try:
        profile = resolve_profile(identity, connection)
    except AuthError as exc:
        return responses.error_body(exc, error_code=exc.error_code)

    return jobs.submit(
        tool_name,
        profile.id,
        identity.tenant_id,
        lambda: _execute_handler_sync(handler, arguments, profile, acquire_lock=False),
    )


def current_job_owner() -> str:
    """Tenant id used to scope compatibility job handles."""
    return current_identity().tenant_id


async def run_offloaded(
    handler: Callable[[dict], Awaitable[list]], arguments: dict
) -> dict[str, Any]:
    """Run a connection-agnostic handler (e.g. result-store ops) off the event loop."""
    contents = await anyio.to_thread.run_sync(lambda: _drive(handler(dict(arguments))))
    body = responses.parse_json_content(contents)
    return body if body is not None else {"success": True}


# ---------------------------------------------------------------------------
# Tool registration decorators (read-only vs write annotations)
# ---------------------------------------------------------------------------

def _title(name: str) -> str:
    return name.replace("_", " ").title()


def ro_tool(name: str, description: str, output: Optional[dict] = None):
    """Register a read-only tool with strict output schema + annotations."""
    return mcp.tool(
        name=name,
        description=description,
        output_schema=out(output),
        task=NATIVE_TASKS_ENABLED and name in NATIVE_TASK_TOOL_NAMES,
        annotations=ToolAnnotations(
            title=_title(name), readOnlyHint=True, idempotentHint=True, openWorldHint=False
        ),
    )


def write_tool(name: str, description: str, output: Optional[dict] = None, *, idempotent: bool = False):
    """Register a write tool (mutates the openLCA database) with annotations."""
    return mcp.tool(
        name=name,
        description=description,
        output_schema=out(output),
        task=NATIVE_TASKS_ENABLED and name in NATIVE_TASK_TOOL_NAMES,
        annotations=ToolAnnotations(
            title=_title(name), readOnlyHint=False, destructiveHint=False,
            idempotentHint=idempotent, openWorldHint=False,
        ),
    )


# ---------------------------------------------------------------------------
# Telemetry middleware (replaces per-call recording in the low-level server)
# ---------------------------------------------------------------------------

class TelemetryMiddleware(Middleware):
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        name = getattr(context.message, "name", "<unknown>")
        start = time.monotonic()
        try:
            result = await call_next(context)
        except Exception:
            telemetry.record(name, success=False, error_code="EXCEPTION",
                             duration_ms=(time.monotonic() - start) * 1000)
            raise
        duration_ms = (time.monotonic() - start) * 1000
        body = getattr(result, "structured_content", None) or {}
        success = body.get("success", True)
        error_code = body.get("error_code") if success is False else None
        telemetry.record(name, success=bool(success), error_code=error_code, duration_ms=duration_ms)
        return result


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name=_SERVER_NAME,
    version=__version__,
    instructions=_SERVER_INSTRUCTIONS,
    website_url=_SERVER_WEBSITE,
    icons=[{"src": _SERVER_ICON_DATA_URI, "mimeType": "image/svg+xml", "sizes": ["any"]}],
    auth=_OpenLCATokenVerifier() if auth_enabled() else None,
)
mcp.add_middleware(TelemetryMiddleware())
if NATIVE_TASKS_ENABLED:
    from fastmcp_tasks import TasksExtension

    mcp.add_extension(TasksExtension(concurrency=NATIVE_TASKS_CONCURRENCY))


@mcp.custom_route("/health", methods=["GET"])
async def health(_request):
    from starlette.responses import JSONResponse

    return JSONResponse({"status": "ok", "server": _SERVER_NAME})


# ---------------------------------------------------------------------------
# Utility probe tools (kept here; richer tools live in src/tools/)
# ---------------------------------------------------------------------------

@ro_tool(
    "test_connection",
    "Test connection to the openLCA IPC server. Use this first to verify openLCA "
    "is running and reachable. Returns connection status and port.",
    {
        "connected": {"type": "boolean", "description": "Whether openLCA answered"},
        "port": {"type": "integer", "description": "IPC port that was probed"},
        "connection": {"type": "string", "description": "Profile id that was used"},
    },
)
async def test_connection(connection: Optional[str] = None) -> dict[str, Any]:
    try:
        client, profile = _resolve(connection)
    except AuthError as exc:
        return responses.error_body(exc, error_code=exc.error_code)
    try:
        connected = await anyio.to_thread.run_sync(
            lambda: _locked_call(profile.id, client.test_connection)
        )
        return responses.success_body(
            {"connected": connected, "port": client.port, "connection": profile.id}
        )
    except Exception as exc:
        logger.error("test_connection failed: %s", exc, exc_info=True)
        return responses.error_body(exc, error_code="CONNECTION_FAILED")


@ro_tool(
    "health_check",
    "Health probe for the openLCA connection: whether the server is reachable and how "
    "much data the active database holds. Set count_entities=false to skip the counts.",
    {"health": {"type": "object", "description": "Reachability and per-type entity counts."}},
)
async def health_check(count_entities: bool = True, connection: Optional[str] = None) -> dict[str, Any]:
    try:
        client, profile = _resolve(connection)
    except AuthError as exc:
        return responses.error_body(exc, error_code=exc.error_code)
    try:
        # _health_check(client, *, count_entities=...) — count_entities is keyword-only,
        # so wrap in a lambda (anyio.to_thread.run_sync only forwards positional args).
        report = await anyio.to_thread.run_sync(
            lambda: _locked_call(
                profile.id, lambda: _health_check(client, count_entities=count_entities)
            )
        )
        return responses.success_body({"health": report})
    except Exception as exc:
        logger.error("health_check failed: %s", exc, exc_info=True)
        return responses.error_body(exc, error_code="CONNECTION_FAILED")


# Register the remaining tools, prompts, and resources (their decorators run on
# import). Imported here, after `mcp` is defined, to avoid circular imports.
from . import prompts as _prompts  # noqa: E402,F401
from . import resources as _resources  # noqa: E402,F401
from . import tools as _tools  # noqa: E402,F401


class _NormalizeMcpPathMiddleware:
    """Accept both the configured MCP path and its trailing-slash variant.

    Some remote MCP clients preserve a trailing slash in the configured server URL.
    Starlette otherwise answers POST /mcp/ with a 307 redirect to /mcp, which some
    connector transports do not replay. Rewrite only this exact alias internally.
    """

    def __init__(self, app, canonical_path: str) -> None:
        self.app = app
        self.canonical_path = canonical_path.rstrip("/") or "/"
        self.alias_path = self.canonical_path if self.canonical_path == "/" else self.canonical_path + "/"

    async def __call__(self, scope, receive, send) -> None:
        if scope.get("type") == "http" and scope.get("path") == self.alias_path:
            scope = dict(scope)
            scope["path"] = self.canonical_path
            scope["raw_path"] = self.canonical_path.encode("utf-8")
        await self.app(scope, receive, send)

def run() -> None:
    """Run the server with the configured transport."""
    transport = os.getenv("TRANSPORT", "stdio").strip().lower()
    logger.info(
        "Starting OpenLCA FastMCP server (transport=%s, native_tasks=%s, task_concurrency=%s)",
        transport, NATIVE_TASKS_ENABLED, NATIVE_TASKS_CONCURRENCY,
    )
    logger.info("Connection profiles: %s", ", ".join(sorted(get_profiles())))
    telemetry.setup(__version__, transport)

    if transport == "stdio":
        mcp.run()
    else:
        http_path = os.getenv("MCP_HTTP_PATH", "/mcp")
        mcp.run(
            transport="http",
            host=os.getenv("MCP_HOST", "0.0.0.0"),
            port=int(os.getenv("MCP_PORT", "8000")),
            path=http_path,
            stateless_http=True,
            json_response=True,
            middleware=[StarletteMiddleware(_NormalizeMcpPathMiddleware, canonical_path=http_path)],
        )


if __name__ == "__main__":
    run()
