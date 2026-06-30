# Changelog

All notable changes to **openlca-mcp** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-06-25

Modernized the server onto **openlca-ipc v0.4.0** and its agent layer.

### Fixed
- **Advertised tools that had no handler now work.** `analyze_contributions`,
  `run_monte_carlo`, and `export_results` were listed to clients but absent from the
  dispatch map, so calling them returned `"Unknown tool"`. All are implemented.
- **`calculate_impacts` with `system_name`** no longer stuffs the name into an id field;
  it resolves the system via `search.get_by_name` with a descriptor-scan fallback and a
  clean `SYSTEM_NOT_FOUND` error if absent.
- **`create_process` flow resolution** is now id-first (`client.get(Flow, id)`), falling
  back to a name search, instead of silently wrapping a keyword as an id.
- **`requires-python`** corrected to `>=3.11` (matches olca-ipc's real requirement).
- Project URLs point to `github.com/SDAI-institute/openlca-mcp`.

### Added
- **Agent-layer adoption.** `calculate_impacts` returns a compact `ResultSummary`
  (top impacts + suggested next actions), a reproducibility `CalculationContext`, and
  `check_result_consistency` warnings alongside the raw impacts.
- **Structured error envelopes.** Failures carry `error_code`, `recoverable`, and
  `suggested_next_actions` (from `openlca_ipc.agent.errors.OLCAError`) in addition to the
  existing `success` flag.
- **Read-only safe mode.** `OPENLCA_READ_ONLY=true` blocks every write tool with a
  `WRITE_BLOCKED` envelope; reads/calculations are unaffected. Default is read-write.
- **New tools:** `health_check`, `get_entity_by_name`, `get_contribution_tree`,
  `get_total_requirements`, `get_normalized_impacts`, `get_weighted_impacts`,
  `get_sankey`, `compare_systems`, `run_scenario_analysis`, `dispose_all_results`.
  Implemented the previously-orphaned `get_inventory_results`. Removed `list_databases`
  (no backing API).
- **Stable result handles.** A UUID-keyed result registry (`res_<hex>`) replaces the
  fragile `str(id(result))` scheme and stores calculation context so follow-up tools
  (contributions, tree, inventory, Sankey, normalization) operate on a result without
  recomputing. All tracked results are disposed on shutdown.
- **Mocked test suite** (`tests/`, pytest + pytest-asyncio): per-handler success/error
  envelopes, the result registry, read-only gating, serializers, and a **regression guard**
  asserting `list_tools()` matches the handler map (so an advertised tool can never lack a
  handler again). 27 tests.

### Changed
- **Module split (single entry point preserved).** `src/server.py` is now an orchestrator
  (transports, dispatch); tool schemas live in `src/tool_defs.py`, handlers in
  `src/handlers.py`, client/config in `src/lca_client.py`, the result registry in
  `src/result_store.py`, and response/serialization helpers in `src/responses.py`.
  `python -m src.server` and the `openlca-mcp` entry point are unchanged.
- `openlca-ipc` dependency bumped to `>=0.4.0`; `/health` reports the package version.
- Non-localhost (Docker) client redirection now rebinds all managers, not just the bare
  client, so remote connections route correctly.

## [0.1.0] - 2025

### Added
- Initial MCP server: phase-organized LCA tools over openlca-ipc, stdio + SSE transports,
  Docker deployment, and client configuration docs.
