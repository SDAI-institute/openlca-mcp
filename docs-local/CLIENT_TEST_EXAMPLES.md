# MCP Server Client Test Examples

## Overview

This document provides practical client test examples for the OpenLCA MCP Server. These examples demonstrate how to test the MCP server tools from both Python clients and AI agents.

## Table of Contents

1. [Direct Python Client Tests](#direct-python-client-tests)
2. [MCP Tool Call Examples](#mcp-tool-call-examples)
3. [AI Agent Test Scenarios](#ai-agent-test-scenarios)
4. [Integration Tests](#integration-tests)
5. [Performance Tests](#performance-tests)

---

## Direct Python Client Tests

### Test 1: Basic Connection Test

```python
"""
Test basic connection to OpenLCA via MCP server
"""

import asyncio
import json
from openlca_ipc import OLCAClient

async def test_basic_connection():
    """Test connection to OpenLCA IPC server"""
    print("="*70)
    print("TEST 1: Basic Connection")
    print("="*70)

    # Create client
    client = OLCAClient(port=8080)

    # Test connection
    try:
        is_connected = client.test_connection()
        if is_connected:
            print("✓ Successfully connected to OpenLCA IPC server")
            print(f"  Port: {client.port}")
            return True
        else:
            print("✗ Connection failed")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_basic_connection())
```

**Expected Output:**
```
======================================================================
TEST 1: Basic Connection
======================================================================
✓ Successfully connected to OpenLCA IPC server
  Port: 8080
```

### Test 2: Search Flows Test

```python
"""
Test flow search functionality
"""

import asyncio
from openlca_ipc import OLCAClient
import olca_schema as o

async def test_search_flows():
    """Test searching for flows in database"""
    print("\n" + "="*70)
    print("TEST 2: Search Flows")
    print("="*70)

    client = OLCAClient(port=8080)

    # Test 1: Search for PET
    print("\n--- Test 2.1: Search PET ---")
    keywords = ["polyethylene", "terephthalate", "granulate"]
    flows = client.search.find_flows(keywords, max_results=5)

    print(f"Search keywords: {keywords}")
    print(f"Results found: {len(flows)}")
    for flow in flows[:3]:
        print(f"  • {flow.name}")

    assert len(flows) > 0, "Should find at least one PET flow"
    print("✓ PET flows found")

    # Test 2: Search for steel
    print("\n--- Test 2.2: Search Steel ---")
    keywords = ["steel", "hot", "rolled"]
    flows = client.search.find_flows(keywords, max_results=5)

    print(f"Search keywords: {keywords}")
    print(f"Results found: {len(flows)}")
    for flow in flows[:3]:
        print(f"  • {flow.name}")

    assert len(flows) > 0, "Should find steel flows"
    print("✓ Steel flows found")

    # Test 3: Search with no results
    print("\n--- Test 2.3: Search Non-existent ---")
    keywords = ["xyznonexistentmaterial123"]
    flows = client.search.find_flows(keywords, max_results=5)

    print(f"Search keywords: {keywords}")
    print(f"Results found: {len(flows)}")

    assert len(flows) == 0, "Should find no flows"
    print("✓ Correctly returned 0 results")

    return True

if __name__ == "__main__":
    asyncio.run(test_search_flows())
```

**Expected Output:**
```
======================================================================
TEST 2: Search Flows
======================================================================

--- Test 2.1: Search PET ---
Search keywords: ['polyethylene', 'terephthalate', 'granulate']
Results found: 3
  • polyethylene terephthalate, granulate, amorphous
  • polyethylene terephthalate, granulate, bottle grade
  • polyethylene terephthalate, granulate, textile grade
✓ PET flows found

--- Test 2.2: Search Steel ---
Search keywords: ['steel', 'hot', 'rolled']
Results found: 5
  • steel, hot rolled, coil
  • steel, hot rolled, plate
  • steel, hot rolled, beam
✓ Steel flows found

--- Test 2.3: Search Non-existent ---
Search keywords: ['xyznonexistentmaterial123']
Results found: 0
✓ Correctly returned 0 results
```

### Test 3: Find Providers Test

```python
"""
Test finding providers for flows
"""

import asyncio
from openlca_ipc import OLCAClient
import olca_schema as o

async def test_find_providers():
    """Test finding providers for flows"""
    print("\n" + "="*70)
    print("TEST 3: Find Providers")
    print("="*70)

    client = OLCAClient(port=8080)

    # Search for PET flow
    print("\n--- Finding PET providers ---")
    flows = client.search.find_flows(
        ["polyethylene", "terephthalate", "granulate"],
        max_results=1
    )

    if not flows:
        print("✗ No PET flows found")
        return False

    flow = flows[0]
    print(f"Flow: {flow.name}")

    # Find providers
    providers = client.search.find_providers(flow)

    print(f"Providers found: {len(providers)}")
    for i, provider in enumerate(providers[:5], 1):
        print(f"  {i}. {provider.name}")

    assert len(providers) > 0, "Should find at least one provider"
    print("✓ Providers found successfully")

    return True

if __name__ == "__main__":
    asyncio.run(test_find_providers())
```

### Test 4: Create Product Flow Test

```python
"""
Test creating new product flows
"""

import asyncio
from openlca_ipc import OLCAClient
import olca_schema as o
import uuid

async def test_create_product_flow():
    """Test creating product flows"""
    print("\n" + "="*70)
    print("TEST 4: Create Product Flow")
    print("="*70)

    client = OLCAClient(port=8080)

    # Create unique flow name
    flow_name = f"Test Product Flow {uuid.uuid4().hex[:8]}"
    description = "Created by automated test"

    print(f"\nCreating flow: {flow_name}")

    # Create flow
    flow = client.data.create_product_flow(flow_name, description)

    print(f"✓ Flow created")
    print(f"  ID: {flow.id}")
    print(f"  Name: {flow.name}")
    print(f"  Type: {flow.flow_type}")

    # Verify flow exists
    retrieved = client.client.get(o.Flow, flow.id)
    assert retrieved is not None, "Flow should exist in database"
    assert retrieved.name == flow_name, "Name should match"

    print("✓ Flow verified in database")

    return flow.id

if __name__ == "__main__":
    asyncio.run(test_create_product_flow())
```

### Test 5: Complete Workflow Test

```python
"""
Test complete LCA workflow from search to calculation
"""

import asyncio
from openlca_ipc import OLCAClient
import olca_schema as o

async def test_complete_workflow():
    """Test complete LCA workflow"""
    print("\n" + "="*70)
    print("TEST 5: Complete LCA Workflow")
    print("="*70)

    client = OLCAClient(port=8080)

    # Phase 1: Goal & Scope
    print("\n--- Phase 1: Goal & Scope ---")
    print("Goal: Calculate impacts of 1kg steel production")
    print("Functional Unit: 1 kg steel")
    print("Method: TRACI 2.1")

    # Search for steel flow
    print("\nSearching for steel flow...")
    flows = client.search.find_flows(["steel", "market"], max_results=1)
    if not flows:
        print("✗ Steel flow not found")
        return False

    steel_flow = flows[0]
    print(f"✓ Found: {steel_flow.name}")

    # Find provider
    print("\nFinding steel production process...")
    providers = client.search.find_providers(steel_flow)
    if not providers:
        print("✗ No providers found")
        return False

    steel_process = providers[0]
    print(f"✓ Found: {steel_process.name}")

    # Find impact method
    print("\nSearching for TRACI method...")
    method = client.search.find_impact_method(["TRACI"])
    if not method:
        print("✗ TRACI method not found")
        return False

    print(f"✓ Found: {method.name}")
    print(f"  Categories: {len(method.impact_categories)}")

    # Phase 2: Life Cycle Inventory
    print("\n--- Phase 2: Life Cycle Inventory ---")
    print("Creating product system...")

    system = client.systems.create_product_system(steel_process)
    print(f"✓ System created: {system.name}")
    print(f"  ID: {system.id}")

    # Phase 3: Life Cycle Impact Assessment
    print("\n--- Phase 3: Impact Assessment ---")
    print("Calculating impacts...")

    result = client.calculate.simple_calculation(
        system_ref=o.Ref(id=system.id),
        method=method,
        amount=1.0
    )

    impacts = client.results.get_total_impacts(result)

    print(f"✓ Calculation complete")
    print(f"  Impact categories: {len(impacts)}")

    # Phase 4: Interpretation
    print("\n--- Phase 4: Interpretation ---")
    print("Top 5 Impact Categories:")

    # Sort by absolute value
    sorted_impacts = sorted(
        impacts,
        key=lambda x: abs(x['amount']),
        reverse=True
    )

    for i, impact in enumerate(sorted_impacts[:5], 1):
        print(f"  {i}. {impact['name']}")
        print(f"     {impact['amount']:.6e} {impact['unit']}")

    # Clean up
    print("\n--- Cleanup ---")
    result.dispose()
    print("✓ Results disposed")

    print("\n" + "="*70)
    print("TEST COMPLETE: All phases successful")
    print("="*70)

    return True

if __name__ == "__main__":
    asyncio.run(test_complete_workflow())
```

---

## MCP Tool Call Examples

### Example 1: test_connection Tool

```json
{
  "tool": "test_connection",
  "arguments": {}
}
```

**Response:**
```json
{
  "success": true,
  "connected": true,
  "port": 8080
}
```

### Example 2: search_flows Tool

```json
{
  "tool": "search_flows",
  "arguments": {
    "keywords": ["polyethylene", "terephthalate"],
    "max_results": 5,
    "flow_type": "PRODUCT_FLOW"
  }
}
```

**Response:**
```json
{
  "success": true,
  "count": 3,
  "flows": [
    {
      "id": "abc123",
      "name": "polyethylene terephthalate, granulate, bottle grade",
      "category": "plastics"
    },
    {
      "id": "def456",
      "name": "polyethylene terephthalate, granulate, amorphous",
      "category": "plastics"
    }
  ]
}
```

### Example 3: find_providers Tool

```json
{
  "tool": "find_providers",
  "arguments": {
    "flow_id": "abc123"
  }
}
```

**Response:**
```json
{
  "success": true,
  "count": 2,
  "providers": [
    {
      "id": "proc123",
      "name": "polyethylene terephthalate, granulate, bottle grade | production | RER"
    },
    {
      "id": "proc456",
      "name": "polyethylene terephthalate, granulate, bottle grade | production | GLO"
    }
  ]
}
```

### Example 4: create_product_flow Tool

```json
{
  "tool": "create_product_flow",
  "arguments": {
    "name": "PET Bottle 0.5L",
    "description": "Polyethylene terephthalate bottle, 0.5 liter capacity"
  }
}
```

**Response:**
```json
{
  "success": true,
  "flow": {
    "id": "new-flow-123",
    "name": "PET Bottle 0.5L",
    "description": "Polyethylene terephthalate bottle, 0.5 liter capacity"
  }
}
```

### Example 5: create_process Tool

```json
{
  "tool": "create_process",
  "arguments": {
    "name": "PET Bottle Production",
    "description": "Production of 1 PET bottle from granulate",
    "exchanges": [
      {
        "flow_id": "new-flow-123",
        "amount": 1.0,
        "is_input": false,
        "is_quantitative_reference": true
      },
      {
        "flow_id": "abc123",
        "amount": 0.025,
        "is_input": true,
        "provider_id": "proc123"
      }
    ]
  }
}
```

**Response:**
```json
{
  "success": true,
  "process": {
    "id": "new-proc-123",
    "name": "PET Bottle Production",
    "description": "Production of 1 PET bottle from granulate"
  }
}
```

### Example 6: calculate_impacts Tool

```json
{
  "tool": "calculate_impacts",
  "arguments": {
    "system_id": "system-123",
    "method_keywords": ["TRACI"],
    "amount": 1.0
  }
}
```

**Response:**
```json
{
  "success": true,
  "result_id": "result-789",
  "impacts": [
    {
      "name": "Global warming",
      "amount": 0.0234,
      "unit": "kg CO2 eq",
      "category": "gwp-id"
    },
    {
      "name": "Acidification",
      "amount": 0.000123,
      "unit": "mol H+ eq",
      "category": "acid-id"
    },
    {
      "name": "Eutrophication",
      "amount": 0.0000567,
      "unit": "kg N eq",
      "category": "eutro-id"
    }
  ],
  "message": "IMPORTANT: Call dispose_result when done with this result_id"
}
```

### Example 7: dispose_result Tool

```json
{
  "tool": "dispose_result",
  "arguments": {
    "result_id": "result-789"
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Result result-789 disposed successfully"
}
```

---

## AI Agent Test Scenarios

### Scenario 1: Simple Material Lookup

**User Query:**
"What is the carbon footprint of producing 1kg of steel?"

**Expected Agent Behavior:**
```
1. test_connection()
   → Verify access

2. search_flows(["steel"])
   → Find steel flow

3. find_providers(flow_id)
   → Get production process

4. search_impact_methods(["TRACI"])
   → Get impact method

5. create_product_system(process_id)
   → Build system

6. calculate_impacts(system_id, method_id, amount=1.0)
   → Calculate impacts

7. Extract Global Warming Potential from results

8. Report to user: "1kg of steel production results in X kg CO2 eq"

9. dispose_result(result_id)
   → Clean up
```

### Scenario 2: Comparative Analysis

**User Query:**
"Which has lower environmental impact: PET or glass bottles?"

**Expected Agent Behavior:**
```
Phase 1: Search for materials
1. search_flows(["polyethylene", "terephthalate"])
2. search_flows(["glass", "bottle"])
3. find_providers for both

Phase 2: Create systems
4. create_product_flow("PET Bottle 1L")
5. create_product_flow("Glass Bottle 1L")
6. create_process for PET bottle
7. create_process for glass bottle
8. create_product_system for both

Phase 3: Calculate impacts
9. search_impact_methods(["ReCiPe"])
10. calculate_impacts for PET system
11. calculate_impacts for glass system

Phase 4: Compare and report
12. Compare impacts across categories
13. Determine winner for each category
14. Report findings to user
15. dispose_result for both results
```

### Scenario 3: Custom Product LCA

**User Query:**
"Calculate the environmental impact of a product made from 2kg aluminum and 0.5kg plastic, with electricity consumption of 10 kWh"

**Expected Agent Behavior:**
```
1. test_connection()

2. Search for materials:
   - search_flows(["aluminum", "primary"])
   - search_flows(["plastic"]) → needs clarification
   - Ask user: "What type of plastic?"
   - search_flows(["polypropylene"])
   - search_flows(["electricity"])

3. Find providers for all materials

4. Create product system:
   - create_product_flow("Custom Product")
   - create_process with exchanges:
     * Output: 1 Custom Product
     * Input: 2 kg aluminum
     * Input: 0.5 kg PP
     * Input: 10 kWh electricity

5. create_product_system(process_id)

6. search_impact_methods(["TRACI"])

7. calculate_impacts(system_id, method_id)

8. Report all impact categories

9. Highlight top 3 impacts

10. dispose_result(result_id)
```

---

## Integration Tests

### Integration Test 1: n8n Workflow

```javascript
// n8n workflow node configuration

{
  "nodes": [
    {
      "type": "AI Agent",
      "name": "LCA Agent",
      "tools": ["mcp-openlca"],
      "prompt": "Calculate the carbon footprint of 1kg steel production using TRACI method"
    }
  ]
}
```

**Test Procedure:**
1. Start n8n workflow
2. Trigger with test input
3. Verify all MCP tools called
4. Check output contains impact results
5. Verify result disposed

**Success Criteria:**
- Workflow completes without errors
- Results are accurate
- Memory cleaned up
- Execution time < 30 seconds

### Integration Test 2: Claude Desktop

```json
// claude_desktop_config.json

{
  "mcpServers": {
    "openlca": {
      "command": "python",
      "args": ["-m", "mcp-server.src.server"],
      "env": {
        "OPENLCA_PORT": "8080"
      }
    }
  }
}
```

**Test Procedure:**
1. Start Claude Desktop
2. Ask: "Calculate impacts of PET bottle production"
3. Verify Claude uses MCP tools
4. Check result accuracy
5. Verify cleanup

---

## Performance Tests

### Performance Test 1: Search Speed

```python
import asyncio
import time
from openlca_ipc import OLCAClient

async def test_search_performance():
    """Test search performance"""
    client = OLCAClient(port=8080)

    keywords_list = [
        ["steel"],
        ["aluminum"],
        ["electricity"],
        ["transport"],
        ["plastic"]
    ]

    times = []

    for keywords in keywords_list:
        start = time.time()
        flows = client.search.find_flows(keywords, max_results=10)
        end = time.time()

        duration = end - start
        times.append(duration)

        print(f"Search {keywords}: {duration:.3f}s ({len(flows)} results)")

    avg_time = sum(times) / len(times)
    print(f"\nAverage search time: {avg_time:.3f}s")

    assert avg_time < 0.5, "Searches should average < 500ms"
    print("✓ Performance test passed")

asyncio.run(test_search_performance())
```

### Performance Test 2: Calculation Speed

```python
import asyncio
import time
from openlca_ipc import OLCAClient
import olca_schema as o

async def test_calculation_performance():
    """Test calculation performance"""
    client = OLCAClient(port=8080)

    # Setup
    flows = client.search.find_flows(["steel", "market"], max_results=1)
    providers = client.search.find_providers(flows[0])
    system = client.systems.create_product_system(providers[0])
    method = client.search.find_impact_method(["TRACI"])

    # Time calculation
    start = time.time()
    result = client.calculate.simple_calculation(
        o.Ref(id=system.id),
        method,
        1.0
    )
    impacts = client.results.get_total_impacts(result)
    end = time.time()

    duration = end - start
    print(f"Calculation time: {duration:.3f}s")
    print(f"Impact categories: {len(impacts)}")

    result.dispose()

    assert duration < 10, "Simple calculation should complete in < 10s"
    print("✓ Performance test passed")

asyncio.run(test_calculation_performance())
```

### Performance Test 3: Concurrent Operations

```python
import asyncio
import time
from openlca_ipc import OLCAClient

async def search_task(client, keywords, task_id):
    """Single search task"""
    start = time.time()
    flows = client.search.find_flows(keywords, max_results=5)
    duration = time.time() - start
    return task_id, duration, len(flows)

async def test_concurrent_searches():
    """Test concurrent search operations"""
    client = OLCAClient(port=8080)

    search_tasks = [
        (["steel"], 1),
        (["aluminum"], 2),
        (["plastic"], 3),
        (["electricity"], 4),
        (["transport"], 5)
    ]

    start = time.time()

    # Run all searches concurrently
    results = await asyncio.gather(*[
        search_task(client, keywords, task_id)
        for keywords, task_id in search_tasks
    ])

    total_duration = time.time() - start

    print("Concurrent search results:")
    for task_id, duration, count in results:
        print(f"  Task {task_id}: {duration:.3f}s ({count} results)")

    print(f"\nTotal time: {total_duration:.3f}s")

    # Should be much faster than sequential
    sequential_estimate = sum(r[1] for r in results)
    speedup = sequential_estimate / total_duration

    print(f"Estimated sequential time: {sequential_estimate:.3f}s")
    print(f"Speedup: {speedup:.2f}x")

    assert speedup > 1.5, "Concurrent operations should be faster"
    print("✓ Concurrent operations test passed")

asyncio.run(test_concurrent_searches())
```

---

## Test Runner Script

```python
"""
Complete test runner for MCP server
"""

import asyncio
import sys

async def run_all_tests():
    """Run all test suites"""
    print("="*70)
    print("MCP SERVER TEST SUITE")
    print("="*70)

    tests = [
        ("Connection Test", test_basic_connection),
        ("Search Flows Test", test_search_flows),
        ("Find Providers Test", test_find_providers),
        ("Create Flow Test", test_create_product_flow),
        ("Complete Workflow Test", test_complete_workflow),
        ("Search Performance", test_search_performance),
        ("Calculation Performance", test_calculation_performance),
        ("Concurrent Operations", test_concurrent_searches),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            print(f"\nRunning: {name}")
            result = await test_func()
            if result != False:
                passed += 1
                print(f"✓ {name} PASSED")
            else:
                failed += 1
                print(f"✗ {name} FAILED")
        except Exception as e:
            failed += 1
            print(f"✗ {name} FAILED with exception: {e}")

    print("\n" + "="*70)
    print(f"TEST SUMMARY")
    print("="*70)
    print(f"Passed: {passed}/{passed+failed}")
    print(f"Failed: {failed}/{passed+failed}")

    if failed == 0:
        print("\n✓ ALL TESTS PASSED")
        return 0
    else:
        print(f"\n✗ {failed} TEST(S) FAILED")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
```

**Run all tests:**
```bash
python CLIENT_TEST_EXAMPLES.md
```

---

## Conclusion

These client test examples provide comprehensive coverage of MCP server functionality. Use them to:

1. Verify MCP server installation
2. Test individual tools
3. Validate AI agent behavior
4. Benchmark performance
5. Debug issues

For complete case studies using these tests, see:
- [PET vs PC Case Study](CASE_STUDY_PET_PC.md)
- [Cups Case Study](CASE_STUDY_CUPS.md)

---

**Last Updated:** 2025-12-04
**Version:** 1.0
