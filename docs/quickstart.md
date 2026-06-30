# MCP Server Quick Start Guide

Get your OpenLCA MCP server running with AI agents in 10 minutes.

## Prerequisites Checklist

Before starting, ensure you have:

- [ ] Python 3.11+ installed (`python --version`)
- [ ] openLCA desktop application installed
- [ ] A database loaded in openLCA
- [ ] IPC server running in openLCA (Tools → Developer Tools → IPC Server)
- [ ] n8n instance (optional, for workflow automation)

## 5-Minute Setup

### Step 1: Install (2 minutes)

```bash
# Navigate to mcp-server directory
cd mcp-server

# Install dependencies
pip install -r requirements.txt
```

Expected output:
```
Successfully installed mcp-0.9.0 pydantic-2.5.0 python-dotenv-1.0.0
```

### Step 2: Configure (1 minute)

```bash
# Copy example config
cp .env.example .env

# Edit if needed (optional - defaults work for standard setup)
# nano .env
```

Default configuration:
```bash
OPENLCA_PORT=8080          # Standard openLCA IPC port
LOG_LEVEL=INFO             # Logging verbosity
```

### Step 3: Test Connection (1 minute)

```bash
# Start the MCP server
python -m src.server
```

Expected output:
```
Starting OpenLCA MCP Server...
OpenLCA port: 8080
✓ Successfully connected to openLCA
MCP Server running...
```

If you see ✓, you're ready to go!

### Step 4: Test with Inspector (1 minute)

In a new terminal:

```bash
# Install MCP inspector (first time only)
npm install -g @modelcontextprotocol/inspector

# Inspect server
mcp-inspector python -m src.server
```

This opens a web interface showing all available tools.

## First Tool Call

Let's test the server manually:

### Using Python

Create `test_client.py`:

```python
import asyncio
import json

async def test_connection():
    # Note: This is a simplified example
    # Real MCP client setup would use the MCP SDK

    print("Testing OpenLCA MCP Server...")
    print("\nAvailable tools:")
    print("- test_connection")
    print("- search_flows")
    print("- calculate_impacts")
    print("- and 12 more...")

    print("\n✓ Server is ready for AI agents!")

if __name__ == "__main__":
    asyncio.run(test_connection())
```

Run:
```bash
python test_client.py
```

### Using n8n

1. **Open n8n**
2. **Create new workflow**
3. **Add MCP Tool Call node**
4. **Configure:**
   - Server: "OpenLCA LCA Server"
   - Tool: `test_connection`
   - Arguments: (none)
5. **Execute**

Expected result:
```json
{
  "success": true,
  "connected": true,
  "port": 8080
}
```

## Your First LCA with AI

Let's automate a simple LCA using an AI agent:

### Example: Search for Materials

**Prompt to AI agent (in n8n or your AI tool):**

```
Using the OpenLCA MCP server tools:

1. Test connection to openLCA
2. Search for steel flows
3. Find providers for the first steel flow found
4. Report the results
```

**Agent will use tools:**
1. `test_connection()` → Verify connection
2. `search_flows(keywords=["steel"])` → Find steel
3. `find_providers(flow_id=...)` → Find producers
4. Return structured report

**Expected output:**
```
Connection Status: ✓ Connected
Steel Flows Found: 15
Example: "Steel, chromium steel 18/8, hot rolled"
Providers: 3
- Steel production, converter, chromium steel
- Steel production, electric, chromium steel
- Steel production, blast furnace
```

### Example: Complete LCA Workflow

**Prompt to AI agent:**

```
Perform a Life Cycle Assessment for a simple widget:

Product: Steel Widget
Materials: 2 kg of steel
Impact Method: TRACI

Follow the 4 LCA phases:
1. Goal & Scope: Find steel and TRACI method
2. LCI: Create process for widget production
3. LCIA: Calculate impacts
4. Interpretation: Analyze top contributors

Clean up results when done.
```

**Agent will orchestrate ~10 tool calls automatically!**

See complete example in `examples/n8n-workflows/basic_lca_workflow.json`.

## Common Tasks

### Task 1: Search for Materials

**Tool:** `search_flows`

```json
{
  "keywords": ["polyethylene", "terephthalate"],
  "max_results": 5
}
```

**Returns:**
```json
{
  "success": true,
  "count": 2,
  "flows": [
    {
      "id": "abc-123",
      "name": "polyethylene terephthalate, granulate, bottle grade"
    }
  ]
}
```

### Task 2: Calculate Impacts

**Prerequisite:** Have a product system ID

**Tool:** `calculate_impacts`

```json
{
  "system_id": "your-system-id",
  "method_keywords": ["TRACI"],
  "amount": 1.0
}
```

**Returns:**
```json
{
  "success": true,
  "result_id": "result-789",
  "impacts": [
    {
      "name": "Global warming",
      "amount": 1.23,
      "unit": "kg CO2 eq"
    }
  ],
  "message": "IMPORTANT: Call dispose_result when done"
}
```

### Task 3: Analyze Contributors

**Tool:** `analyze_contributions`

```json
{
  "result_id": "result-789",
  "impact_category_id": "gwp-id",
  "n": 5
}
```

**Returns:**
```json
{
  "success": true,
  "contributors": [
    {
      "name": "Steel production",
      "share": 0.78,
      "amount": 0.96
    }
  ]
}
```

### Task 4: Cleanup

**IMPORTANT:** Always call this after calculations!

**Tool:** `dispose_result`

```json
{
  "result_id": "result-789"
}
```

## Integrating with n8n

### Quick Setup

1. **Import Workflow:**
   ```bash
   # In n8n
   Workflows → Import → Select basic_lca_workflow.json
   ```

2. **Configure MCP Server:**
   ```
   Settings → Credentials → Add → MCP Server

   Name: OpenLCA LCA Server
   Command: python
   Args: -m src.server
   CWD: /path/to/mcp-server
   Env: OPENLCA_PORT=8080
   ```

3. **Test:**
   ```
   Open workflow → Execute workflow
   ```

See [docs/n8n-integration.md](n8n-integration.md) for detailed guide.

## Troubleshooting

### Issue: "Could not connect to openLCA"

**Symptoms:**
```
✗ Failed to connect to openLCA
Connection test failed
```

**Solutions:**

1. **Check openLCA is running:**
   ```
   → Open openLCA application
   ```

2. **Check database is loaded:**
   ```
   → File → Open Database → Select database
   ```

3. **Check IPC server is started:**
   ```
   → Tools → Developer Tools → IPC Server
   → Click "Start"
   ```

4. **Check port matches:**
   ```
   → Look at IPC server window for port number
   → Update .env: OPENLCA_PORT=8080
   ```

### Issue: "Module not found"

**Symptoms:**
```
ModuleNotFoundError: No module named 'mcp'
```

**Solution:**
```bash
pip install -r requirements.txt
```

### Issue: Tools return errors

**Symptoms:**
```json
{
  "success": false,
  "error": "Flow not found"
}
```

**Common causes:**
1. Material doesn't exist in database
2. Wrong keywords
3. Database not loaded

**Solutions:**
1. Try broader keywords
2. Check database content
3. Create missing data

## Next Steps

### Learn More

1. **Read Documentation:**
   - [Full README](../README.md)
   - [n8n Integration Guide](n8n-integration.md)
   - [Tool Reference](tool-reference.md)

2. **Try Examples:**
   - Basic LCA workflow
   - Comparative LCA
   - Batch processing

3. **Build Your Workflow:**
   - Start with template
   - Customize for your use case
   - Add error handling

### Advanced Usage

- **Multi-product comparison:** Compare multiple products in one workflow
- **Batch processing:** Process many LCAs automatically
- **Uncertainty analysis:** Add Monte Carlo simulations
- **Custom tools:** Extend with your own tools

## Tips for AI Agents

When prompting AI agents to use this MCP server:

### ✓ Good Prompts

```
"Search for steel flows and find the top provider"
"Calculate impacts for product system ID abc-123 using TRACI"
"Analyze contribution hotspots for global warming"
```

### ✗ Avoid

```
"Do LCA" (too vague)
"Calculate everything" (no specific system)
"Find materials" (no keywords)
```

### Best Practice Pattern

```
1. Be specific about inputs
2. Specify which tools to use
3. Request structured output
4. Include cleanup steps
```

**Example:**
```
Using OpenLCA MCP tools:

1. test_connection() - verify access
2. search_flows(keywords=["aluminum"]) - find material
3. find_providers(flow_id=...) - find producer
4. Report: {material_name, provider_name, database_id}
```

## Getting Help

- **Documentation:** [Full docs](../README.md)
- **Examples:** `examples/` folder
- **Issues:** [GitHub Issues](https://github.com/SDAI-institute/openlca-ipc/issues)
- **Email:** dernestbanksch@gmail.com

## Checklist: Ready for Production?

Before deploying to production:

- [ ] Server starts without errors
- [ ] test_connection returns true
- [ ] Can search for materials
- [ ] Can calculate impacts
- [ ] Results are disposed properly
- [ ] Error handling in place
- [ ] Logging configured
- [ ] n8n workflow tested end-to-end
- [ ] Backup database before bulk operations
- [ ] Monitor server logs

## Summary

You've learned:
- ✓ How to install and configure MCP server
- ✓ How to test connection and tools
- ✓ How to integrate with AI agents
- ✓ How to handle common issues
- ✓ Best practices for automation

**You're ready to automate LCA with AI!**

---

**Time to completion: ~10 minutes**

**Next:** Try the [basic n8n workflow](../examples/n8n-workflows/basic_lca_workflow.json)
