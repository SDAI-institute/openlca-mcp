# openLCA MCP Tool Reference

Current reviewed source: openLCA MCP v0.4.1. The server registers **28 tools**. The owning source modules are authoritative for exact schemas.

## Connection and health — 2 tools

| Tool | Purpose |
|---|---|
| `test_connection` | Verify the selected openLCA IPC connection and report the profile/port. |
| `health_check` | Check reachability and optionally count entities in the active database. |

## Goal and scope / discovery — 8 tools

| Tool | Purpose |
|---|---|
| `search_flows` | Keyword search for product, elementary, or waste flows. |
| `search_processes` | Keyword search for processes. |
| `search_product_systems` | Browse/search existing product systems without creating one. |
| `inspect_product_system` | Inspect reference process/flow, target amount, unit, and flow property. |
| `list_impact_methods` | Browse LCIA methods in the active database. |
| `search_impact_methods` | Search LCIA methods and return matched categories. |
| `find_providers` | Find provider processes for a flow. |
| `get_entity_by_name` | Exact-name lookup for supported entity types. |

## Life cycle inventory / writes — 3 tools

| Tool | Purpose |
|---|---|
| `create_product_flow` | Create a product flow. |
| `create_process` | Create a unit process from validated exchanges. |
| `create_product_system` | Build and auto-link a product system from a process. |

These operations mutate the active openLCA database and are blocked on read-only connections.

## Impact assessment and result access — 5 tools

| Tool | Purpose |
|---|---|
| `calculate_impacts` | Calculate impacts and return a reusable `result_id`, summary, impacts, warnings, and context. |
| `get_inventory_results` | Retrieve total elementary-flow inventory from a stored result. |
| `get_total_requirements` | Retrieve scaled technology requirements from a stored result. |
| `get_normalized_impacts` | Retrieve normalized impacts when supported by the method. |
| `get_weighted_impacts` | Retrieve weighted impacts when supported by the method. |

## Interpretation and analysis — 8 tools

| Tool | Purpose |
|---|---|
| `check_result_consistency` | Check whether per-process contributions reconcile with category totals. |
| `analyze_contributions` | Rank process or flow contributions for an impact category. |
| `get_contribution_tree` | Build a pruned upstream contribution tree. |
| `get_sankey` | Return Sankey graph data for an impact category. |
| `compare_systems` | Compare two product systems on the same impact method. |
| `run_monte_carlo` | Run uncertainty analysis and summarize impact distributions. |
| `run_scenario_analysis` | Vary a named parameter over explicit values. |
| `export_results` | Export impacts or comparison data to CSV/Excel on the server host. |

## Result lifecycle — 2 tools

| Tool | Purpose |
|---|---|
| `dispose_result` | Free one stored calculation result. |
| `dispose_all_results` | Free every result tracked by the server. |

## Recommended call discipline

1. Start with `test_connection` or `health_check`.
2. Inspect/search entities instead of guessing IDs.
3. Confirm the functional basis with `inspect_product_system` before calculation when using an existing system.
4. Call `calculate_impacts` once and reuse its `result_id` for follow-up analysis.
5. Run `check_result_consistency` before presenting decision-relevant numbers.
6. Preserve model, database, method, amount, connection profile, package version, and source revision in the study record.
7. Call `dispose_result` when the analysis is finished.

## Safety boundary

Typed MCP schemas reduce malformed calls, but they do not validate the scientific appropriateness of a functional unit, boundary, provider, allocation method, background dataset, LCIA method, scenario, or interpretation. Those remain human-reviewed LCA decisions.