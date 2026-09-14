# openLCA MCP Quick Start

Run the current FastMCP server against an openLCA Desktop database and verify the tool surface before connecting an AI client.

## Requirements

- Python 3.11+
- openLCA Desktop 2.x with the intended database open
- openLCA IPC Server started, normally on port 8080
- `openlca-mcp` source or installed package

The reviewed package version is 0.4.1 and depends on `openlca-ipc>=0.4.0`.

## 1. Install

```bash
git clone https://github.com/SDAI-institute/openlca-mcp.git
cd openlca-mcp
pip install -e .
```

For repository development dependencies:

```bash
pip install -e ".[dev]"
```

## 2. Configure openLCA

In openLCA Desktop:

1. Open the database you intend to use.
2. Open **Tools → Developer Tools → IPC Server**.
3. Start the server, normally on port `8080`.
4. Keep the IPC Server dialog/session active while using MCP.

Optional environment variables include:

```text
OPENLCA_HOST=localhost
OPENLCA_PORT=8080
OPENLCA_READ_ONLY=true
LOG_LEVEL=INFO
```

Use read-only mode for inspection, calculations, and demonstrations that should not mutate the database.

## 3. Start the MCP server

```bash
python -m src
```

Do not use `python -m src.app`; the package entry point intentionally uses `python -m src` so all tool modules register on the same FastMCP instance.

The installed console script is also:

```bash
openlca-mcp
```

## 4. Verify the connection

The first MCP call should be one of:

```text
test_connection()
health_check(count_entities=true)
```

A successful connection verifies reachability. Separately confirm the active database and study entities before calculating.

## 5. Verify the tool surface

The current source registers 28 tools:

- 2 connection/health tools
- 8 goal-and-scope/search tools
- 3 inventory/write tools
- 5 impact/result tools
- 8 interpretation/analysis tools
- 2 result-lifecycle tools

See [Tool Reference](tool-reference.md) for the complete list.

## 6. First read-only workflow

A safe first workflow uses an existing product system:

```text
1. test_connection
2. search_product_systems
3. inspect_product_system
4. list_impact_methods or search_impact_methods
5. calculate_impacts
6. check_result_consistency
7. analyze_contributions or get_inventory_results
8. dispose_result
```

This pattern avoids creating database entities and keeps the calculation result lifecycle explicit.

## 7. Write workflow

When writes are intentionally enabled:

```text
search_flows → find_providers → create_product_flow → create_process → create_product_system
```

Then calculate and interpret the resulting product system. Write tools return a structured `WRITE_BLOCKED` error when the selected connection is read-only.

## Result lifecycle

`calculate_impacts` returns a `result_id`. Reuse it for inventory, contributions, trees, Sankey data, normalization, weighting, and exports. Call `dispose_result(result_id)` when finished.

## Client connection

For local clients, use stdio. For ChatGPT and other remote clients, run with streamable HTTP and connect to the `/mcp` endpoint. See [Client Configuration](client-configs.md) and [Online Hosting](online-hosting.md).

## Troubleshooting

If openLCA tools fail:

1. confirm openLCA is running;
2. confirm the intended database is open;
3. confirm the IPC server is started and the port matches;
4. run `test_connection`;
5. use broader search terms before assuming an entity is missing;
6. inspect structured `error_code`, `recoverable`, and `suggested_next_actions` fields;
7. dispose stale results before restarting a workflow.

## Next

- [Tool Reference](tool-reference.md)
- [Client Configuration](client-configs.md)
- [n8n Integration](n8n-integration.md)
- [Online Hosting](online-hosting.md)
- [Repository README](../README.md)
