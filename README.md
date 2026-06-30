# OpenLCA MCP Server for AI Agent Automation

Model Context Protocol (MCP) server that exposes openLCA functionality as tools for AI agents to automate Life Cycle Assessment (LCA) workflows.

## Overview

This MCP server enables AI agents (like those in n8n workflows) to interact with openLCA programmatically. Tools are organized by the 4 phases of ISO-14040/14044 LCA methodology:

1. **Goal & Scope Definition** - Search for materials, processes, and impact methods
2. **Life Cycle Inventory (LCI)** - Create flows, processes, and product systems
3. **Life Cycle Impact Assessment (LCIA)** - Calculate environmental impacts
4. **Interpretation** - Analyze contributions, uncertainty, and export results

## Features

- ✅ **24 specialized LCA tools** for AI agents, covering the full openlca-ipc v0.4 surface
- ✅ **Phase-organized** following ISO LCA standards
- ✅ **Structured agent responses** — compact `ResultSummary`, reproducibility context, and
  recoverable error envelopes (`error_code`, `recoverable`, `suggested_next_actions`)
- ✅ **Read-only safe mode** (`OPENLCA_READ_ONLY=true`) to protect databases from writes
- ✅ **Stable result handles** with a `result_id` registry for follow-up analysis
- ✅ **n8n compatible** for workflow automation
- ✅ **Async support** for concurrent operations

Built on **openlca-ipc ≥ 0.4.0** and its agent layer.

## Prerequisites

Before running the MCP server:

1. **openLCA Desktop**
   - Version 2.x installed and running
   - Database loaded
   - IPC server started (Tools → Developer Tools → IPC Server)

2. **Python Environment**
   - Python 3.11 or higher
   - openlca-ipc ≥ 0.4.0 installed

3. **For n8n Integration**
   - n8n instance running
   - MCP integration enabled in n8n

## Installation

### 1. Install Dependencies

```bash
cd mcp-server
pip install -r requirements.txt
```

This will install:
- MCP SDK
- openlca-ipc library (from parent directory)
- Pydantic for validation
- python-dotenv for configuration

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` file:

```bash
# OpenLCA IPC Server Configuration
OPENLCA_PORT=8080          # Match your IPC server port
OPENLCA_HOST=localhost

# Safe mode: when true, all database writes are blocked (WRITE_BLOCKED).
# Reads, searches, and calculations still work. Default: false.
OPENLCA_READ_ONLY=false

# Logging Configuration
LOG_LEVEL=INFO             # DEBUG, INFO, WARNING, ERROR
```

### 3. Test the Server

```bash
python -m src.server
```

You should see:
```
Starting OpenLCA MCP Server...
OpenLCA port: 8080
✓ Successfully connected to openLCA
MCP Server running...
```

## Available Tools

All 24 tools are advertised only if they have a working handler (enforced at startup and by
a regression test), so there are no "dead" tools.

### Connection & health

| Tool | Purpose | Inputs |
|------|---------|--------|
| `test_connection` | Test openLCA connection | None |
| `health_check` | Connection status + entity counts | count_entities? |

### Phase 1: Goal & Scope Definition

| Tool | Purpose | Inputs |
|------|---------|--------|
| `search_flows` | Find material flows | keywords, max_results?, flow_type? |
| `search_processes` | Find processes | keywords, max_results? |
| `search_impact_methods` | Find LCIA methods (+ categories) | keywords |
| `find_providers` | Find production processes for a flow | flow_id or flow_name |
| `get_entity_by_name` | Exact-name lookup → EntitySummary | model_type, name |

### Phase 2: Life Cycle Inventory (LCI) — writes

| Tool | Purpose | Inputs |
|------|---------|--------|
| `create_product_flow` | Create a product flow | name, description? |
| `create_process` | Create a unit process | name, description?, exchanges |
| `create_product_system` | Build a product system | process_id or process_name |

> Write tools return a `WRITE_BLOCKED` error when `OPENLCA_READ_ONLY=true`.

### Phase 3: Life Cycle Impact Assessment (LCIA)

| Tool | Purpose | Inputs |
|------|---------|--------|
| `calculate_impacts` | Calculate impacts → result_id + ResultSummary | system_id or system_name, method_id or method_keywords, amount? |
| `get_inventory_results` | Full LCI (elementary flows) | result_id, direction? |
| `get_total_requirements` | Scaled technology flows | result_id |
| `get_normalized_impacts` | Normalized impacts | result_id |
| `get_weighted_impacts` | Weighted impacts | result_id |

### Phase 4: Interpretation

| Tool | Purpose | Inputs |
|------|---------|--------|
| `analyze_contributions` | Top process/flow contributors | result_id, impact_category_id, n?, contribution_type?, min_share? |
| `get_contribution_tree` | Upstream hotspot tree | result_id, impact_category_id, max_depth?, min_share? |
| `get_sankey` | Sankey graph data | result_id, impact_category_id, max_nodes?, min_share? |
| `compare_systems` | Compare two systems on one method | system1_id, system2_id, method_id or method_keywords, amount? |
| `run_monte_carlo` | Uncertainty analysis (stats) | system_id, method_id or method_keywords, iterations? |
| `run_scenario_analysis` | Vary a parameter over values | system_id, method_id or method_keywords, parameter_name, values |
| `export_results` | Export impacts/comparison to CSV/Excel | result_id or data, filepath, format?, kind? |

### Utilities

| Tool | Purpose | Inputs |
|------|---------|--------|
| `dispose_result` | Free one calculation result | result_id |
| `dispose_all_results` | Free all tracked results | None |

### The `result_id` workflow

`calculate_impacts` runs the calculation, stores the live result, and returns a `result_id`
plus a compact `ResultSummary` and any consistency warnings. Follow-up tools
(`analyze_contributions`, `get_contribution_tree`, `get_inventory_results`, `get_sankey`,
`get_normalized_impacts`, ...) take that `result_id` so the result is reused, not recomputed.
Call `dispose_result` when finished (all results are also disposed on shutdown).

## Usage Examples

### Example 1: Complete LCA Workflow (AI Agent Perspective)

An AI agent would call tools in this sequence:

```
1. test_connection()
   → Verify openLCA is accessible

2. search_flows(keywords=["steel"])
   → Find steel flow ID

3. find_providers(flow_id="...")
   → Find steel production process ID

4. create_product_flow(name="My Widget")
   → Create product flow, get ID

5. create_process(
     name="Widget Production",
     exchanges=[
       {flow_id: "widget_id", amount: 1.0, is_input: false, is_quantitative_reference: true},
       {flow_id: "steel_id", amount: 2.0, is_input: true, provider_id: "provider_id"}
     ]
   )
   → Create process, get ID

6. create_product_system(process_id="...")
   → Build product system, get ID

7. search_impact_methods(keywords=["TRACI"])
   → Find impact method ID

8. calculate_impacts(system_id="...", method_id="...")
   → Get impacts + result_id

9. analyze_contributions(result_id="...", impact_category_id="...")
   → Identify hotspots

10. dispose_result(result_id="...")
    → Clean up memory
```

### Example 2: Search and Discovery

```json
// Tool: search_flows
{
  "keywords": ["polyethylene", "terephthalate"],
  "max_results": 5,
  "flow_type": "PRODUCT_FLOW"
}

// Response:
{
  "success": true,
  "count": 2,
  "flows": [
    {
      "id": "abc-123",
      "name": "polyethylene terephthalate, granulate, bottle grade",
      "category": "plastics"
    }
  ]
}
```

### Example 3: Create Process

```json
// Tool: create_process
{
  "name": "PET Bottle Production",
  "description": "Produces 1 PET bottle from granulate",
  "exchanges": [
    {
      "flow_id": "bottle_flow_id",
      "amount": 1.0,
      "is_input": false,
      "is_quantitative_reference": true
    },
    {
      "flow_id": "pet_granulate_id",
      "amount": 0.025,
      "is_input": true,
      "provider_id": "pet_production_id"
    }
  ]
}

// Response:
{
  "success": true,
  "process": {
    "id": "process-123",
    "name": "PET Bottle Production",
    "description": "Produces 1 PET bottle from granulate"
  }
}
```

### Example 4: Calculate Impacts

```json
// Tool: calculate_impacts
{
  "system_id": "system-123",
  "method_id": "traci-method-id",
  "amount": 1.0
}

// Response (abridged):
{
  "success": true,
  "result_id": "res_a1b2c3d4e5f6",
  "summary": {
    "result_id": "res_a1b2c3d4e5f6",
    "top_impacts": [
      {"category": "Global warming", "amount": 0.05, "unit": "kg CO2 eq"}
    ],
    "next_actions": ["inspect_contribution_tree", "compare_scenario", "export_report"],
    "warnings": []
  },
  "impacts": [
    {"name": "Global warming", "category": {"id": "gwp-id", "name": "Global warming"},
     "category_id": "gwp-id", "amount": 0.05, "unit": "kg CO2 eq"}
  ],
  "warnings": [],
  "context": { "result_id": "res_a1b2c3d4e5f6", "timestamp": "...", "package_version": "0.4.0" },
  "message": "Call dispose_result with this result_id when finished."
}
```

Feed `impacts[].category_id` into `analyze_contributions` / `get_contribution_tree` /
`get_sankey` as `impact_category_id`.

## n8n Integration

### Setup Steps

1. **Install MCP Integration in n8n**
   - Install MCP nodes in your n8n instance
   - Configure MCP connection

2. **Configure MCP Server Connection**
   ```json
   {
     "name": "OpenLCA LCA Server",
     "serverType": "sse",
     "url": "http://localhost:8000/sse"
   }
   ```

3. **Create n8n Workflow**

   See [examples/n8n-workflows/](examples/n8n-workflows/) for complete workflow templates.

### 4-Phase LCA Workflow Template

Your n8n workflow should have 4 agent phases:

**Phase 1 Agent: Goal & Scope**
- Use: `test_connection`, `search_flows`, `search_processes`, `search_impact_methods`
- Output: List of required materials, processes, and impact method

**Phase 2 Agent: Life Cycle Inventory**
- Use: `create_product_flow`, `create_process`, `create_product_system`
- Output: Product system ID ready for calculation

**Phase 3 Agent: Impact Assessment**
- Use: `calculate_impacts`, `get_inventory_results`
- Output: Impact results with result_id

**Phase 4 Agent: Interpretation**
- Use: `analyze_contributions`, `export_results`, `dispose_result`
- Output: Analysis report and exported files

See [docs/n8n-integration.md](docs/n8n-integration.md) for detailed setup.

## Architecture

```
┌─────────────────────────────────────────┐
│         n8n Workflow Agents             │
│  ┌────────┬────────┬────────┬────────┐  │
│  │Phase 1 │Phase 2 │Phase 3 │Phase 4 │  │
│  │ Goal & │  LCI   │  LCIA  │Interp. │  │
│  │ Scope  │        │        │        │  │
│  └───┬────┴───┬────┴───┬────┴───┬────┘  │
│      │        │        │        │       │
│      └────────┴────────┴────────┘       │
│               MCP Protocol               │
└──────────────────┬──────────────────────┘
                   │
          ┌────────▼────────┐
          │   MCP Server    │
          │  (this server)  │
          └────────┬────────┘
                   │
          ┌────────▼────────┐
          │ openlca-ipc lib │
          └────────┬────────┘
                   │
          ┌────────▼────────┐
          │  openLCA IPC    │
          │     Server      │
          └────────┬────────┘
                   │
          ┌────────▼────────┐
          │openLCA Desktop  │
          │   Application   │
          └─────────────────┘
```

## Error Handling

Every response carries a `success` boolean. Failures additionally carry the structured
agent fields so an AI agent can branch programmatically:

```json
// Success response
{
  "success": true,
  "...": "tool-specific payload"
}

// Error response
{
  "success": false,
  "is_error": true,
  "error_code": "IMPACT_METHOD_NOT_FOUND",
  "message": "No impact method matched ['nope'].",
  "recoverable": true,
  "suggested_next_actions": ["search_impact_methods"]
}
```

Error codes include `CONNECTION_FAILED`, `IMPACT_METHOD_NOT_FOUND`, `SYSTEM_NOT_FOUND`,
`ENTITY_NOT_FOUND`, `CALCULATION_FAILED`, `WRITE_BLOCKED`, `UNKNOWN_TOOL`, and
`INTERNAL_ERROR`.

| Error code | Cause | Suggested recovery |
|-----------|-------|--------------------|
| `CONNECTION_FAILED` | IPC server not running | Start the IPC server in openLCA |
| `ENTITY_NOT_FOUND` | Flow/process/result not found | Try different keywords; verify the id |
| `SYSTEM_NOT_FOUND` | No matching product system | Search or create the product system |
| `IMPACT_METHOD_NOT_FOUND` | No matching LCIA method | Use `search_impact_methods` |
| `WRITE_BLOCKED` | Write attempted in read-only mode | Set `OPENLCA_READ_ONLY=false` |

## Best Practices for AI Agents

### 1. Always Test Connection First
```
Step 1: Call test_connection()
Step 2: If connected, proceed with workflow
```

### 2. Check Search Results
```
Step 1: Call search_flows(keywords=[...])
Step 2: If count > 0, use first result
Step 3: If count == 0, try alternative keywords
```

### 3. Always Dispose Results
```
Step 1: Call calculate_impacts() → get result_id
Step 2: Use result_id for analysis
Step 3: Call dispose_result(result_id) when done
```

### 4. Handle Missing Data Gracefully
```
If search returns empty:
  - Try broader keywords
  - Try alternative spellings
  - Create the needed data
  - Report to user
```

## Development

### Running in Development Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run server
python -m src.server
```

### Testing Tools

Use MCP inspector or direct tool calls:

```bash
# Install MCP inspector
npm install -g @modelcontextprotocol/inspector

# Inspect server
mcp-inspector python -m src.server
```

The server is split into focused modules; `src/server.py` stays the entry point:

| Module | Responsibility |
|--------|----------------|
| `src/server.py` | Server setup, dispatch, stdio + streamable HTTP + legacy SSE transports, `main`/`run` |
| `src/tool_defs.py` | `TOOLS` — all tool schema definitions |
| `src/handlers.py` | Async handlers + `TOOL_HANDLERS` map |
| `src/lca_client.py` | `get_client()` singleton, env config, read-only mode |
| `src/result_store.py` | `result_id` registry for live results |
| `src/responses.py` | Success/error envelopes + serializers |

To add a tool:

1. Register its schema in `src/tool_defs.py` (via the `_register(_tool(...))` helper).
2. Implement `async def handle_<name>(arguments)` in `src/handlers.py` and add it to
   `TOOL_HANDLERS`.

`TOOLS` and `TOOL_HANDLERS` must stay in sync — the server raises at startup and a test
fails otherwise, so an advertised tool can never lack a handler.

## Troubleshooting

### Server Won't Start

**Problem:** Server fails to start

**Check:**
1. Is Python 3.11+ installed? `python --version`
2. Are dependencies installed? `pip list | grep -E "mcp|openlca-ipc"`
3. Is .env file configured? `cat .env`

### Can't Connect to openLCA

**Problem:** `test_connection` returns false

**Check:**
1. Is openLCA running?
2. Is database loaded?
3. Is IPC server started?
4. Does port in .env match IPC server?

### Tool Calls Fail

**Problem:** Tools return errors

**Check:**
1. Review error message in response
2. Check server logs (LOG_LEVEL=DEBUG)
3. Verify inputs match schema
4. Test with MCP inspector

## Logging

View logs to debug issues:

```bash
# Set log level
export LOG_LEVEL=DEBUG

# Run server and view logs
python -m src.server 2>&1 | tee server.log
```

Log levels:
- **DEBUG**: All operations and data
- **INFO**: Major operations (default)
- **WARNING**: Issues that don't stop operation
- **ERROR**: Failures and exceptions

## Performance

### Resource Usage

- **Memory**: ~50-100 MB baseline
- **CPU**: Minimal (most work in openLCA)
- **Network**: Localhost only (IPC)

### Optimization Tips

1. **Dispose results promptly** - Prevents memory leaks
2. **Limit search results** - Use max_results parameter
3. **Cache impact methods** - Reuse method IDs
4. **Batch operations** - Create multiple processes before calculating

## Security

### Local Only

This server is designed for **local use only**:
- Connects to localhost openLCA
- No network exposure
- No authentication required

### Production Deployment

For production use:
- Add authentication
- Restrict tool access
- Audit tool calls
- Limit concurrent connections

### Remote access & the optional auth token

When you expose the server to a remote client (ChatGPT, Claude) through the
streaming gateway (`docker-compose.gateway.yml`), authentication is **optional**:

- **No token (simplest):** leave `MCP_AUTH_TOKEN` empty in `.env`. The gateway
  runs open — anyone who can reach your tunnel/VPN can call it. Fine when the
  tunnel itself already restricts access. Connect with the bare URL:
  `https://<your-host>/mcp`
- **With a token:** set `MCP_AUTH_TOKEN` to a long random secret. The gateway
  then requires it on every request. Because ChatGPT's connector UI can't send
  custom headers, pass it as a query parameter:
  `https://<your-host>/mcp?api_key=<MCP_AUTH_TOKEN>`

**Generate a token** (any one of these), then paste it into `MCP_AUTH_TOKEN` in `.env`:

```bash
# macOS / Linux (or Git Bash on Windows)
openssl rand -hex 32

# Windows PowerShell
python -c "import secrets; print(secrets.token_hex(32))"
```

```env
# .env  — leave empty to run the gateway open, or paste a generated secret here
MCP_AUTH_TOKEN=
```

> The token is enforced **only** by the gateway (`gateway/Caddyfile`). It does
> nothing in stdio mode or when you run the bare server without the gateway.
> See [docs/online-hosting.md](docs/online-hosting.md) for the full remote setup.

## Contributing

Contributions welcome! See main project [CONTRIBUTING.md](../CONTRIBUTING.md).

## License

MIT License - See [LICENSE](../LICENSE) for details.

## Support

- **Documentation**: [Full docs](docs/)
- **Issues**: [GitHub Issues](https://github.com/SDAI-institute/openlca-mcp/issues)
- **Email**: dernestbanksch@gmail.com

## Acknowledgments

Built on:
- [MCP Protocol](https://modelcontextprotocol.io/) by Anthropic
- [openlca-ipc](https://github.com/SDAI-institute/openlca-ipc)
- [openLCA](https://www.openlca.org/) by GreenDelta

---

**Ready to automate your LCA workflows with AI agents!**
