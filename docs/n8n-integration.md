# n8n Integration Guide

Complete guide to integrating the OpenLCA MCP Server with n8n for automated LCA workflows.

## Overview

This guide shows you how to:
1. Set up the MCP server for n8n
2. Configure n8n to connect to the MCP server
3. Create a 4-phase multi-agent LCA workflow
4. Handle errors and edge cases

## Prerequisites

### Required

- ✅ n8n instance (self-hosted or cloud)
- ✅ Python 3.10+ with MCP server installed
- ✅ openLCA desktop running with IPC server
- ✅ MCP support in n8n (version with MCP integration)

### Knowledge

- Basic n8n workflow creation
- Understanding of LCA methodology (4 phases)
- Familiarity with AI agent patterns

## Setup

### Step 1: Install MCP Server

```bash
cd mcp-server
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Set OPENLCA_PORT to match your setup
```

### Step 2: Test MCP Server

```bash
# Start the server
python -m src.server

# You should see:
# ✓ Successfully connected to openLCA
# MCP Server running...
```

### Step 3: Configure n8n MCP Connection

In n8n, add MCP server configuration:

**Settings → Credentials → Add Credential → MCP Server**

```json
{
  "name": "OpenLCA LCA Server",
  "type": "stdio",
  "command": "python",
  "args": ["-m", "src.server"],
  "cwd": "D:/01code/Projects/openlca_library/mcp-server",
  "env": {
    "OPENLCA_PORT": "8080",
    "LOG_LEVEL": "INFO"
  }
}
```

Adjust paths for your system:
- **Windows**: `D:/path/to/mcp-server`
- **macOS/Linux**: `/path/to/mcp-server`

### Step 4: Test Connection in n8n

Create a simple test workflow:

1. Add **MCP Tool Call** node
2. Select "OpenLCA LCA Server" credential
3. Choose tool: `test_connection`
4. Execute workflow

Expected output:
```json
{
  "success": true,
  "connected": true,
  "port": 8080
}
```

## 4-Phase LCA Workflow Architecture

### Workflow Overview

```
User Input → Phase 1 Agent → Phase 2 Agent → Phase 3 Agent → Phase 4 Agent → Final Report
             (Goal & Scope)   (LCI)          (LCIA)         (Interpretation)
```

### Phase Responsibilities

**Phase 1: Goal & Scope Definition**
- Understand user's LCA goal
- Search for required materials
- Validate database content
- Define functional unit

**Phase 2: Life Cycle Inventory (LCI)**
- Create product flows
- Build unit processes
- Link exchanges with providers
- Create product system

**Phase 3: Life Cycle Impact Assessment (LCIA)**
- Select appropriate impact method
- Run calculations
- Collect impact results

**Phase 4: Interpretation**
- Analyze contribution hotspots
- Run sensitivity/uncertainty analysis
- Export results
- Generate recommendations

## Creating the 4-Phase Workflow

### Workflow Structure

```
1. [Trigger] Manual/Webhook
   │
2. [Set Variables] Store user input
   │
3. [Agent 1: Goal & Scope]
   │  Tools: test_connection, search_flows, search_processes, search_impact_methods
   │  Output: material_ids, process_ids, method_id, system_boundaries
   │
4. [Decision] All materials found?
   │  Yes → Continue
   │  No → Ask user for alternatives
   │
5. [Agent 2: Life Cycle Inventory]
   │  Tools: create_product_flow, create_process, create_product_system
   │  Output: product_system_id
   │
6. [Agent 3: Impact Assessment]
   │  Tools: calculate_impacts, get_inventory_results
   │  Output: impacts, result_id
   │
7. [Agent 4: Interpretation]
   │  Tools: analyze_contributions, export_results
   │  Output: analysis_report, export_files
   │
8. [Cleanup] dispose_result
   │
9. [Output] Send report to user
```

### Node Details

#### Node 1: Trigger (Manual/Webhook)

Collect user input:
```json
{
  "product_name": "PET Water Bottle",
  "functional_unit": "1 bottle",
  "materials": [
    {"name": "PET granulate", "amount": 0.025},
    {"name": "polypropylene", "amount": 0.003}
  ],
  "impact_method": "TRACI",
  "analysis_requirements": ["contribution", "uncertainty"]
}
```

#### Node 2-3: Phase 1 Agent - Goal & Scope

**Agent Configuration:**
```
Name: LCA Goal & Scope Specialist
System Prompt: |
  You are an LCA expert specializing in defining study goals and scope.
  Your tasks:
  1. Validate the user's LCA goal
  2. Search for required materials in the database
  3. Find appropriate impact assessment methods
  4. Define system boundaries

  Always use test_connection first to verify openLCA is accessible.
  Search for materials using broad keywords first, then narrow down.

Available Tools:
  - test_connection
  - search_flows
  - search_processes
  - search_impact_methods
  - find_providers

Instructions:
  1. Test connection to openLCA
  2. For each material in user input, search database
  3. Find providers for each material
  4. Search for requested impact method
  5. Return structured data for next phase
```

**Expected Output:**
```json
{
  "phase": "goal_and_scope",
  "status": "complete",
  "findings": {
    "materials_found": [
      {
        "name": "polyethylene terephthalate, granulate",
        "id": "abc-123",
        "provider_id": "provider-456",
        "amount": 0.025
      }
    ],
    "materials_missing": ["polypropylene"],
    "impact_method": {
      "name": "TRACI 2.1",
      "id": "traci-789"
    },
    "system_boundaries": "cradle-to-gate"
  },
  "next_action": "proceed_to_lci" | "request_user_input"
}
```

#### Node 4: Decision - Check Materials

```javascript
// Check if all materials found
if ($json.findings.materials_missing.length > 0) {
  // Ask user for alternatives or create materials
  return [{"json": {"action": "request_alternatives"}}];
} else {
  // Proceed to Phase 2
  return [{"json": {"action": "proceed_to_lci"}}];
}
```

#### Node 5-6: Phase 2 Agent - Life Cycle Inventory

**Agent Configuration:**
```
Name: LCA Inventory Specialist
System Prompt: |
  You are an LCA expert specializing in life cycle inventory modeling.
  Your tasks:
  1. Create the product flow being assessed
  2. Build unit processes with inputs and outputs
  3. Link exchanges to provider processes
  4. Create the product system

  Be meticulous about:
  - Setting one exchange as quantitative reference
  - Linking all product flows to providers
  - Using correct amounts and units (kg)

Available Tools:
  - create_product_flow
  - create_process
  - create_product_system

Input Data: {{ $node["Phase 1 Agent"].json.findings }}

Instructions:
  1. Create product flow for: {{ $node["Trigger"].json.product_name }}
  2. Create process with:
     - Output: 1 unit of product (quantitative reference)
     - Inputs: All materials from Phase 1 with amounts
  3. Create product system from process
  4. Return product_system_id for calculation
```

**Expected Output:**
```json
{
  "phase": "life_cycle_inventory",
  "status": "complete",
  "created": {
    "product_flow_id": "new-product-123",
    "process_id": "new-process-456",
    "product_system_id": "new-system-789"
  },
  "summary": {
    "process_name": "PET Water Bottle Production",
    "inputs_count": 2,
    "outputs_count": 1
  }
}
```

#### Node 7-8: Phase 3 Agent - Impact Assessment

**Agent Configuration:**
```
Name: LCA Impact Assessment Specialist
System Prompt: |
  You are an LCA expert specializing in impact assessment.
  Your tasks:
  1. Run LCIA calculations
  2. Retrieve total impacts
  3. Organize results for interpretation

  Important:
  - Use the product_system_id from Phase 2
  - Use the impact_method_id from Phase 1
  - Store the result_id for cleanup

Available Tools:
  - calculate_impacts
  - get_inventory_results

Input Data:
  - System ID: {{ $node["Phase 2 Agent"].json.created.product_system_id }}
  - Method ID: {{ $node["Phase 1 Agent"].json.findings.impact_method.id }}

Instructions:
  1. Calculate impacts for product system
  2. Extract and organize impact results
  3. Return results with result_id for Phase 4
```

**Expected Output:**
```json
{
  "phase": "impact_assessment",
  "status": "complete",
  "result_id": "result-abc-123",
  "impacts": [
    {
      "name": "Global warming",
      "amount": 0.05,
      "unit": "kg CO2 eq",
      "category_id": "gwp-id"
    },
    {
      "name": "Acidification",
      "amount": 0.0001,
      "unit": "mol H+ eq",
      "category_id": "acid-id"
    }
  ],
  "total_impacts": 18
}
```

#### Node 9-10: Phase 4 Agent - Interpretation

**Agent Configuration:**
```
Name: LCA Interpretation Specialist
System Prompt: |
  You are an LCA expert specializing in results interpretation.
  Your tasks:
  1. Analyze contribution hotspots
  2. Run uncertainty analysis if requested
  3. Export results
  4. Generate insights and recommendations

  Focus on:
  - Identifying processes with >5% contribution
  - Providing actionable recommendations
  - Clear communication of uncertainty

Available Tools:
  - analyze_contributions
  - run_monte_carlo (if requested)
  - export_results

Input Data:
  - Result ID: {{ $node["Phase 3 Agent"].json.result_id }}
  - Impacts: {{ $node["Phase 3 Agent"].json.impacts }}
  - User Requirements: {{ $node["Trigger"].json.analysis_requirements }}

Instructions:
  1. For each major impact category (>0.01):
     - Analyze top 5 contributors
     - Identify hotspots (>10% contribution)
  2. If uncertainty requested:
     - Run Monte Carlo with 100 iterations
  3. Export results to CSV
  4. Generate interpretation report
  5. DO NOT dispose result yet (done in cleanup node)
```

**Expected Output:**
```json
{
  "phase": "interpretation",
  "status": "complete",
  "hotspots": [
    {
      "impact": "Global warming",
      "top_contributor": "PET granulate production",
      "contribution_percent": 78.5,
      "amount": 0.03925,
      "unit": "kg CO2 eq"
    }
  ],
  "uncertainty": {
    "performed": true,
    "iterations": 100,
    "summary": {
      "mean": 0.051,
      "std_dev": 0.008,
      "cv_percent": 15.7
    }
  },
  "exports": {
    "impacts_csv": "results/impacts_20250110.csv",
    "contributions_csv": "results/contributions_20250110.csv"
  },
  "recommendations": [
    "Focus improvement efforts on PET granulate sourcing (78.5% of GWP)",
    "Consider recycled PET content to reduce impacts",
    "Uncertainty (CV=15.7%) indicates good data quality"
  ]
}
```

#### Node 11: Cleanup - Dispose Result

**MCP Tool Call Node:**
```
Tool: dispose_result
Arguments:
{
  "result_id": "{{ $node['Phase 3 Agent'].json.result_id }}"
}
```

This is critical to prevent memory leaks in openLCA.

#### Node 12: Generate Final Report

**Code Node (JavaScript):**
```javascript
const trigger = $node["Trigger"].json;
const phase1 = $node["Phase 1 Agent"].json;
const phase2 = $node["Phase 2 Agent"].json;
const phase3 = $node["Phase 3 Agent"].json;
const phase4 = $node["Phase 4 Agent"].json;

const report = {
  title: `LCA Report: ${trigger.product_name}`,
  date: new Date().toISOString(),
  functional_unit: trigger.functional_unit,

  goal_and_scope: {
    product: trigger.product_name,
    method: phase1.findings.impact_method.name,
    system_boundaries: phase1.findings.system_boundaries
  },

  inventory: {
    materials: phase1.findings.materials_found.length,
    processes: 1,
    system_id: phase2.created.product_system_id
  },

  impact_results: phase3.impacts.map(impact => ({
    category: impact.name,
    value: impact.amount,
    unit: impact.unit
  })),

  interpretation: {
    hotspots: phase4.hotspots,
    recommendations: phase4.recommendations
  },

  exports: phase4.exports
};

return { json: report };
```

## Error Handling

### Connection Errors

```javascript
// In Phase 1 Agent, first action
if (!$json.success || !$json.connected) {
  return {
    error: "Cannot connect to openLCA",
    solution: "Check if openLCA is running and IPC server is started",
    stop_workflow: true
  };
}
```

### Missing Materials

```javascript
// After Phase 1 Agent
if ($json.findings.materials_missing.length > 0) {
  // Option 1: Ask user
  // Option 2: Create materials programmatically
  // Option 3: Substitute with similar materials
}
```

### Calculation Failures

```javascript
// After Phase 3 Agent
if (!$json.success) {
  return {
    error: "Calculation failed",
    details: $json.error,
    troubleshooting: [
      "Check if product system has providers for all inputs",
      "Verify impact method is compatible with database",
      "Check openLCA console for errors"
    ],
    stop_workflow: true
  };
}
```

## Advanced Patterns

### Parallel Material Search

Instead of sequential searches, search in parallel:

```
[Split In Batches] → [MCP: search_flows] × N → [Merge]
```

### Caching Impact Methods

Store frequently used method IDs in n8n variables:

```javascript
// Store
$vars.traci_method_id = "method-123";

// Reuse
const methodId = $vars.traci_method_id || search_for_method();
```

### Progress Updates

Send webhooks at each phase completion:

```
[Phase 1 Complete] → [Webhook: Update Dashboard]
[Phase 2 Complete] → [Webhook: Update Dashboard]
...
```

## Testing

### Test Each Phase Separately

Create individual workflows for each phase:

1. **test_phase1.json** - Just Goal & Scope
2. **test_phase2.json** - Just LCI (with mock inputs)
3. **test_phase3.json** - Just LCIA (with mock system_id)
4. **test_phase4.json** - Just Interpretation (with mock result_id)

### Sample Test Data

```json
{
  "product_name": "Test Widget",
  "materials": [
    {"name": "steel", "amount": 1.0}
  ],
  "impact_method": "TRACI",
  "analysis_requirements": ["contribution"]
}
```

## Performance Optimization

### 1. Limit Search Results

```json
{
  "tool": "search_flows",
  "arguments": {
    "keywords": ["steel"],
    "max_results": 5  // Don't search entire database
  }
}
```

### 2. Reuse Searches

Store search results in workflow variables:

```javascript
// First time
$vars.steel_flow = search_flows(["steel"]);

// Reuse
const steel = $vars.steel_flow;
```

### 3. Dispose Results Promptly

Always dispose in the same workflow execution:

```
[Calculate] → [Analyze] → [Export] → [Dispose]
```

## Troubleshooting

### MCP Server Not Found

**Error:** "Cannot start MCP server"

**Solutions:**
1. Check `cwd` path is absolute
2. Verify Python in PATH
3. Test command manually: `python -m src.server`

### Tools Not Showing

**Error:** "No tools available"

**Solutions:**
1. Check MCP server logs
2. Verify server started successfully
3. Test with `mcp-inspector`

### Calculation Takes Forever

**Error:** Workflow times out during calculation

**Solutions:**
1. Check product system size (may be very large)
2. Increase n8n timeout
3. Add progress monitoring
4. Simplify system boundaries

## Production Deployment

### n8n Cloud

1. Use n8n cloud with custom MCP server
2. Deploy MCP server on same network
3. Use environment variables for config

### Self-Hosted n8n

1. Run n8n and MCP server on same machine
2. Use Docker Compose for both services
3. Configure persistent storage for exports

### Docker Compose Example

```yaml
version: '3.8'

services:
  n8n:
    image: n8nio/n8n
    ports:
      - "5678:5678"
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=admin
      - N8N_BASIC_AUTH_PASSWORD=password
    volumes:
      - n8n_data:/home/node/.n8n
      - ./mcp-server:/mcp-server

  openlca-mcp:
    build: ./mcp-server
    environment:
      - OPENLCA_PORT=8080
    volumes:
      - ./exports:/exports

volumes:
  n8n_data:
```

## Example Workflows

See [examples/n8n-workflows/](../examples/n8n-workflows/) for:

- `basic_lca_workflow.json` - Simple 4-phase workflow
- `comparative_lca.json` - Compare multiple products
- `batch_processing.json` - Process multiple LCAs
- `interactive_lca.json` - User feedback loops

## Next Steps

1. Import example workflow
2. Test with simple product
3. Customize for your use case
4. Add error handling
5. Deploy to production

## Resources

- [MCP Documentation](https://modelcontextprotocol.io/)
- [n8n Documentation](https://docs.n8n.io/)
- [MCP Server README](../README.md)
- [Tool Reference](tool-reference.md)

## Support

- **Issues**: [GitHub Issues](https://github.com/dernestbank/openlca-ipc/issues)
- **Discussions**: Tag with `mcp-server` or `n8n`
- **Email**: dernestbanksch@gmail.com
