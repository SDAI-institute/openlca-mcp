# n8n Integration Guide

Use n8n to orchestrate repeatable openLCA MCP calls while keeping study definition and interpretation under explicit human review.

## Recommended architecture

```text
Approved study input
      ↓
Connection + model verification
      ↓
Optional inventory writes
      ↓
Calculation
      ↓
Consistency check + interpretation tools
      ↓
Human review gate
      ↓
Export + result disposal
```

Do not ask an agent to invent a functional unit, system boundary, allocation rule, provider mapping, LCIA method, or conclusion when those items are missing. Route incomplete study definitions back to a reviewer.

## 1. Connect n8n to MCP

Prefer streamable HTTP for service-to-service use:

```text
http://openlca-mcp:8000/mcp
```

or a protected HTTPS endpoint:

```text
https://mcp.example.com/mcp
```

For a local process integration, launch the current entry point with:

```text
python -m src
```

## 2. Start every workflow with verification

Call:

```text
test_connection
health_check
```

Then verify the intended database/model context. A successful network connection is not evidence that the correct database is open.

## 3. Prefer existing systems when possible

For an analysis-only workflow:

```text
search_product_systems
→ inspect_product_system
→ list_impact_methods / search_impact_methods
→ reviewer confirms target + method
→ calculate_impacts
```

This is safer than creating foreground data inside the same automation when the study already exists.

## 4. Controlled write workflow

When the workflow is authorized to create foreground data:

```text
search_flows
→ find_providers
→ reviewer resolves ambiguous matches
→ create_product_flow
→ create_process
→ create_product_system
```

Use a read/write connection profile only for this stage. A read-only profile should remain the default for inspection and calculation where practical.

## 5. Calculation stage

Call `calculate_impacts` with an approved product-system identifier, LCIA method identifier, and reference amount.

Store the returned:

- `result_id`;
- impact rows and category IDs;
- warnings;
- calculation/reproducibility context;
- study/model identifiers used by the workflow.

Do not silently rerun a changed model if a downstream node fails. Either reuse the same `result_id` or explicitly start a new calculation state.

## 6. Interpretation stage

Recommended sequence:

```text
check_result_consistency
→ get_inventory_results / get_total_requirements
→ analyze_contributions
→ get_contribution_tree or get_sankey when useful
→ optional scenario or Monte Carlo analysis
```

Interpretation nodes should report model outputs and assumptions. They should not convert a hotspot directly into a recommendation without considering system boundary, dataset choice, allocation, geography, uncertainty, and feasibility.

### Uncertainty rule

Monte Carlo spread describes the uncertainty encoded in the modeled distributions. A low coefficient of variation does **not** prove that source data are high quality or that omitted uncertainties are small.

## 7. Human review gate

Before generating a decision-facing report, require an explicit review step that confirms at least:

- correct product system and functional/reference basis;
- intended database and version;
- LCIA method;
- scenario/parameter definitions;
- result consistency warnings reviewed;
- interpretation is proportional to evidence;
- limitations are retained.

## 8. Export and cleanup

After approval, export the required result tables and metadata, then call:

```text
dispose_result(result_id)
```

Use a workflow `finally`/error branch so disposal is attempted even when downstream processing fails.

## Example n8n state object

Keep one structured object between stages:

```json
{
  "study": {
    "functional_basis": "approved externally",
    "system_id": "...",
    "impact_method_id": "...",
    "amount": 1.0
  },
  "calculation": {
    "result_id": "...",
    "warnings": [],
    "context": {}
  },
  "review": {
    "method_confirmed": false,
    "interpretation_approved": false
  }
}
```

The exact functional basis and study text should come from the approved protocol or user input, not be fabricated by the workflow.

## Error handling

Use structured MCP fields where available:

- `error_code`;
- `recoverable`;
- `suggested_next_actions`.

Typical behavior:

- connection failure → stop and request infrastructure correction;
- no search match → broaden/search or request reviewer selection;
- ambiguous matches → do not choose silently;
- write blocked → either keep the workflow read-only or move to an explicitly authorized profile;
- calculation failure → do not produce an interpretation report;
- stale/missing result handle → rerun only as a clearly new calculation state.

## Production controls

- authenticate remote MCP endpoints;
- restrict connection profiles per caller;
- default to read-only where possible;
- isolate demonstration/test databases from production research databases;
- preserve workflow execution logs without publishing private prompts or credentials;
- back up databases before authorized bulk writes;
- keep openLCA and MCP software revisions in the study manifest.

## Related documentation

- [Quick Start](quickstart.md)
- [Tool Reference](tool-reference.md)
- [Client Configuration](client-configs.md)
- [Online Hosting](online-hosting.md)
- [openLCA MCP README](../README.md)
