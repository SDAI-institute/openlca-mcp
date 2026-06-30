"""
Anonymous, opt-out usage telemetry for openlca-mcp.

Two complementary backends run in parallel:

  Grafana / OTLP  — performance & reliability  (latency, error rates, traces)
  PostHog         — product analytics           (tool rankings, funnels, unique installs)

PURPOSE
-------
The maintainer can see aggregate, anonymous usage patterns across all opt-in
installations so the server can be improved for real-world LCA workflows.

WHAT IS SENT  (all anonymous, none of it is personal)
------------------------------------------------------
  tool_name      which tool was called (e.g. "calculate_impacts")
  success        whether the call succeeded (bool)
  error_code     error code on failure, e.g. "SYSTEM_NOT_FOUND"
                   — never the human-readable error message
  duration_ms    execution time in milliseconds
  server_version "0.2.0"
  transport      "stdio" or "sse"
  session_id     random hex, generated at server start,
                   regenerated every restart, never stored to disk

WHAT IS NEVER SENT
-------------------
  Tool arguments — no database IDs, search terms, file paths, or parameter values
  Result content — no LCA data, no impact values, no entity names
  IP addresses or hostnames
  Usernames or any user-specific identifiers
  Error messages (only the error code enum string)
  Any content from the openLCA database

OPT OUT (any one is sufficient)
--------------------------------
  DO_NOT_TRACK=1                 (industry-standard signal, respected by both backends)
  OPENLCA_TELEMETRY=false        (project-specific override)

DEBUG — print the exact payload without sending anything
---------------------------------------------------------
  OPENLCA_TELEMETRY_DEBUG=true

GRAFANA / OTLP  (traces + metrics)
------------------------------------
  OPENLCA_TELEMETRY_ENDPOINT=https://otlp-gateway-prod-<region>.grafana.net/otlp
  OTEL_EXPORTER_OTLP_HEADERS=Authorization=Basic <base64-token>

POSTHOG  (product analytics)
------------------------------
  POSTHOG_API_KEY=phc_...         from posthog.com → Project → API Keys
  POSTHOG_HOST=https://us.i.posthog.com   (default; EU: https://eu.i.posthog.com)

SOURCE
------
  This module is fully open-source — read every line at:
  https://github.com/SDAI-institute/openlca-mcp/blob/main/src/telemetry.py
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Optional

logger = logging.getLogger(__name__)

# ── Ephemeral session identity ────────────────────────────────────────────────
# One random hex id per server process. Not stored to disk, not tied to any
# user or machine. Regenerated on every restart. Used as PostHog distinct_id
# so events within one server-start are grouped, without tracking real users.
_SESSION_ID: str = uuid.uuid4().hex[:16]

_TRUTHY = {"1", "true", "yes", "on"}
_FALSY  = {"0", "false", "no",  "off"}

# ── Module-level state (set once at setup()) ──────────────────────────────────
_server_version: str = "unknown"
_transport: str      = "unknown"
_ready: bool         = False

# OTel objects (None until _init_otel() runs)
_tool_counter  = None
_tool_duration = None

# PostHog lazy client (None until first use)
_ph_client = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def enabled() -> bool:
    """False if the user opted out via DO_NOT_TRACK or OPENLCA_TELEMETRY."""
    if os.getenv("DO_NOT_TRACK", "").strip().lower() in _TRUTHY:
        return False
    return os.getenv("OPENLCA_TELEMETRY", "true").strip().lower() not in _FALSY


def debug_mode() -> bool:
    """True when OPENLCA_TELEMETRY_DEBUG=true."""
    return os.getenv("OPENLCA_TELEMETRY_DEBUG", "").strip().lower() in _TRUTHY


def setup(version: str, transport: str) -> None:
    """
    Initialise both telemetry backends once at server startup.

    Idempotent — safe to call multiple times.
    Silently degrades if SDK packages are not installed.
    """
    global _ready, _server_version, _transport
    if _ready:
        return
    _ready = True
    _server_version = version
    _transport      = transport

    if not enabled() and not debug_mode():
        logger.debug("Telemetry: disabled by environment")
        return

    _setup_otel(version, transport)
    _setup_posthog()

    active = []
    if _tool_counter is not None:
        active.append("grafana/otlp")
    if _ph_client is not None:
        active.append("posthog")
    if debug_mode():
        active.append("debug-console")

    if active:
        logger.debug("Telemetry active: %s  session=%s", ", ".join(active), _SESSION_ID)
    else:
        logger.debug(
            "Telemetry: enabled but no backends configured. "
            "Set OPENLCA_TELEMETRY_ENDPOINT and/or POSTHOG_API_KEY."
        )


def record(
    tool_name: str,
    *,
    success: bool,
    error_code: Optional[str],
    duration_ms: float,
) -> None:
    """
    Record one tool-call event to all active backends.

    Called from call_tool() in server.py after every handler returns.
    Never receives tool arguments or result content.
    """
    if not enabled():
        return

    dur = round(duration_ms, 1)

    _otel_record(tool_name, success, error_code, dur)
    _posthog_record(tool_name, success, error_code, dur)

    if debug_mode():
        _debug_print(tool_name, success, error_code, dur)


# ---------------------------------------------------------------------------
# Grafana / OpenTelemetry backend
# ---------------------------------------------------------------------------

def _setup_otel(version: str, transport: str) -> None:
    """Initialise OTel tracer + meter. No-op if SDK not installed."""
    global _tool_counter, _tool_duration

    endpoint = os.getenv("OPENLCA_TELEMETRY_ENDPOINT", "").strip() or None
    if not endpoint and not debug_mode():
        return

    try:
        from opentelemetry import trace, metrics
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

        resource = Resource.create({
            "service.name":    "openlca-mcp",
            "service.version": version,
            "mcp.transport":   transport,
            "mcp.session_id":  _SESSION_ID,
        })

        # ── Traces ──
        tracer_provider = TracerProvider(resource=resource)
        if endpoint:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            # OTEL_EXPORTER_OTLP_HEADERS env var is read automatically by the exporter
            tracer_provider.add_span_processor(
                BatchSpanProcessor(
                    OTLPSpanExporter(endpoint=f"{endpoint.rstrip('/')}/v1/traces")
                )
            )
        if debug_mode():
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter
            tracer_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

        trace.set_tracer_provider(tracer_provider)

        # ── Metrics ──
        readers = []
        if endpoint:
            from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
            readers.append(
                PeriodicExportingMetricReader(
                    OTLPMetricExporter(endpoint=f"{endpoint.rstrip('/')}/v1/metrics"),
                    export_interval_millis=60_000,
                )
            )
        if debug_mode():
            from opentelemetry.sdk.metrics.export import ConsoleMetricExporter
            readers.append(
                PeriodicExportingMetricReader(
                    ConsoleMetricExporter(), export_interval_millis=30_000
                )
            )

        meter_provider = MeterProvider(resource=resource, metric_readers=readers)
        metrics.set_meter_provider(meter_provider)
        meter = metrics.get_meter("openlca-mcp", version)

        _tool_counter = meter.create_counter(
            "mcp.tool.calls",
            description="Total MCP tool invocations",
            unit="1",
        )
        _tool_duration = meter.create_histogram(
            "mcp.tool.duration_ms",
            description="MCP tool execution time",
            unit="ms",
        )

    except ImportError:
        logger.debug(
            "opentelemetry-sdk not installed — Grafana/OTLP backend inactive. "
            "pip install 'openlca-mcp-server[telemetry]'"
        )
    except Exception as exc:
        logger.debug("OTel setup failed (non-fatal): %s", exc)


def _otel_record(
    tool_name: str, success: bool, error_code: Optional[str], duration_ms: float
) -> None:
    attrs = {
        "mcp.tool.name":       tool_name,
        "mcp.tool.success":    str(success).lower(),
        "mcp.tool.error_code": error_code or "",
    }
    if _tool_counter is not None:
        try:
            _tool_counter.add(1, attrs)
        except Exception:
            pass
    if _tool_duration is not None:
        try:
            _tool_duration.record(duration_ms, attrs)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# PostHog backend
# ---------------------------------------------------------------------------

def _setup_posthog() -> None:
    """Initialise the PostHog client. No-op if SDK or API key not present."""
    global _ph_client

    api_key = os.getenv("POSTHOG_API_KEY", "").strip()
    if not api_key:
        return

    try:
        from posthog import Posthog

        host = os.getenv("POSTHOG_HOST", "https://us.i.posthog.com").rstrip("/")
        _ph_client = Posthog(api_key=api_key, host=host)
        # Silence posthog's own noisy logging
        logging.getLogger("posthog").setLevel(logging.WARNING)

    except ImportError:
        logger.debug(
            "posthog not installed — PostHog backend inactive. "
            "pip install 'openlca-mcp-server[telemetry]'"
        )
    except Exception as exc:
        logger.debug("PostHog setup failed (non-fatal): %s", exc)


def _posthog_record(
    tool_name: str, success: bool, error_code: Optional[str], duration_ms: float
) -> None:
    if _ph_client is None:
        return
    try:
        # distinct_id = ephemeral session_id  →  each server-start is one "user"
        # PostHog counts of distinct_ids ≈ active installations
        _ph_client.capture(
            distinct_id=_SESSION_ID,
            event="mcp_tool_called",
            properties={
                "tool_name":      tool_name,
                "success":        success,
                "error_code":     error_code,
                "duration_ms":    duration_ms,
                "server_version": _server_version,
                "transport":      _transport,
                # PostHog property convention: $lib identifies the SDK source
                "$lib":           "openlca-mcp",
            },
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Debug / transparency
# ---------------------------------------------------------------------------

def _debug_print(
    tool: str, success: bool, error_code: Optional[str], duration_ms: float
) -> None:
    """Print the exact payload sent to all backends. Nothing is actually exported."""
    payload = {
        "backends":       _active_backends(),
        "event":          "mcp_tool_called",
        "distinct_id":    _SESSION_ID,
        "tool_name":      tool,
        "success":        success,
        "error_code":     error_code,
        "duration_ms":    duration_ms,
        "server_version": _server_version,
        "transport":      _transport,
        "_never_sent": [
            "tool arguments",
            "result content",
            "IP address",
            "hostname",
            "username",
            "error message text",
            "openLCA database content",
        ],
    }
    logger.info("[telemetry-debug] %s", json.dumps(payload, indent=2))


def _active_backends() -> list[str]:
    backends = []
    if _tool_counter is not None:
        backends.append("grafana/otlp")
    if _ph_client is not None:
        backends.append("posthog")
    if not backends:
        backends.append("none — debug only")
    return backends
