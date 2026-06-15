# MCP Server Test and Evaluation Documentation

## Overview

This document provides comprehensive testing and evaluation procedures for the OpenLCA MCP Server and AI Agent integration. It includes test protocols, practical case studies, and evaluation metrics for Life Cycle Assessment (LCA) automation.

## Table of Contents

1. [Testing Framework](#testing-framework)
2. [MCP Server Testing](#mcp-server-testing)
3. [AI Agent Testing](#ai-agent-testing)
4. [Case Studies](#case-studies)
5. [Performance Evaluation](#performance-evaluation)
6. [Validation Procedures](#validation-procedures)
7. [Troubleshooting](#troubleshooting)

---

## Testing Framework

### Test Categories

#### 1. Unit Tests
- Individual tool functionality
- Input validation
- Error handling
- Data type conversions

#### 2. Integration Tests
- MCP server ↔ OpenLCA IPC communication
- End-to-end workflows
- Multi-tool sequences
- Result disposal and memory management

#### 3. System Tests
- Complete LCA workflows
- Real-world case studies
- Performance under load
- Concurrent operations

#### 4. Validation Tests
- Result accuracy vs manual calculations
- Consistency with OpenLCA desktop
- ISO 14040/14044 compliance

### Test Environment Setup

```bash
# 1. Start OpenLCA Desktop
# - Open OpenLCA application
# - Load ecoinvent database (3.7.2 or higher recommended)
# - Start IPC Server: Tools → Developer Tools → IPC Server
# - Verify port (default: 8080)

# 2. Configure MCP Server
cd mcp-server
cp .env.example .env
# Edit .env: Set OPENLCA_PORT=8080

# 3. Install dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio

# 4. Run MCP Server
python -m src.server
```

---

## MCP Server Testing

### Test Suite 1: Connection and Basic Operations

**Test 1.1: Server Startup**
```python
# File: tests/test_connection.py

import asyncio
import pytest
from openlca_ipc import OLCAClient

@pytest.mark.asyncio
async def test_server_startup():
    """Test MCP server starts successfully"""
    client = OLCAClient(port=8080)
    assert client.test_connection() == True
    print("✓ Server startup successful")

@pytest.mark.asyncio
async def test_connection_tool():
    """Test test_connection tool"""
    # Simulate tool call
    result = await handle_test_connection({})
    assert result[0].text contains "success": true
    print("✓ Connection tool working")
```

**Test 1.2: Database Access**
```python
@pytest.mark.asyncio
async def test_list_databases():
    """Test database listing"""
    client = OLCAClient(port=8080)
    databases = client.get_descriptors('Database')
    assert len(databases) > 0
    print(f"✓ Found {len(databases)} database(s)")
```

### Test Suite 2: Search Operations (Phase 1)

**Test 2.1: Flow Search**
```python
@pytest.mark.asyncio
async def test_search_flows():
    """Test flow search functionality"""
    result = await handle_search_flows({
        "keywords": ["polyethylene", "terephthalate"],
        "max_results": 5
    })

    data = json.loads(result[0].text)
    assert data["success"] == True
    assert data["count"] > 0
    assert "flows" in data
    print(f"✓ Found {data['count']} flows")
```

**Test 2.2: Process Search**
```python
@pytest.mark.asyncio
async def test_search_processes():
    """Test process search"""
    result = await handle_search_processes({
        "keywords": ["electricity", "medium", "voltage"],
        "max_results": 10
    })

    data = json.loads(result[0].text)
    assert data["success"] == True
    print(f"✓ Found {data['count']} processes")
```

**Test 2.3: Impact Method Search**
```python
@pytest.mark.asyncio
async def test_search_impact_methods():
    """Test impact method search"""
    result = await handle_search_impact_methods({
        "keywords": ["TRACI"]
    })

    data = json.loads(result[0].text)
    assert data["success"] == True
    assert "method" in data
    print(f"✓ Found method: {data['method']['name']}")
```

**Test 2.4: Provider Search**
```python
@pytest.mark.asyncio
async def test_find_providers():
    """Test provider search"""
    # First search for a flow
    flow_result = await handle_search_flows({
        "keywords": ["steel", "hot", "rolled"],
        "max_results": 1
    })

    flow_data = json.loads(flow_result[0].text)
    flow_id = flow_data["flows"][0]["id"]

    # Find providers
    provider_result = await handle_find_providers({
        "flow_id": flow_id
    })

    provider_data = json.loads(provider_result[0].text)
    assert provider_data["success"] == True
    print(f"✓ Found {provider_data['count']} providers")
```

### Test Suite 3: Data Creation (Phase 2)

**Test 3.1: Create Product Flow**
```python
@pytest.mark.asyncio
async def test_create_product_flow():
    """Test product flow creation"""
    result = await handle_create_product_flow({
        "name": "Test Product Flow",
        "description": "Created by automated test"
    })

    data = json.loads(result[0].text)
    assert data["success"] == True
    assert "flow" in data
    assert "id" in data["flow"]
    print(f"✓ Created flow: {data['flow']['id']}")

    return data["flow"]["id"]
```

**Test 3.2: Create Process**
```python
@pytest.mark.asyncio
async def test_create_process():
    """Test process creation"""
    # Create product flow first
    flow_id = await test_create_product_flow()

    result = await handle_create_process({
        "name": "Test Process",
        "description": "Test process with exchanges",
        "exchanges": [
            {
                "flow_id": flow_id,
                "amount": 1.0,
                "is_input": False,
                "is_quantitative_reference": True
            }
        ]
    })

    data = json.loads(result[0].text)
    assert data["success"] == True
    print(f"✓ Created process: {data['process']['id']}")

    return data["process"]["id"]
```

**Test 3.3: Create Product System**
```python
@pytest.mark.asyncio
async def test_create_product_system():
    """Test product system creation"""
    # Create process first
    process_id = await test_create_process()

    result = await handle_create_product_system({
        "process_id": process_id
    })

    data = json.loads(result[0].text)
    assert data["success"] == True
    print(f"✓ Created system: {data['product_system']['id']}")

    return data["product_system"]["id"]
```

### Test Suite 4: Calculations (Phase 3)

**Test 4.1: Impact Calculation**
```python
@pytest.mark.asyncio
async def test_calculate_impacts():
    """Test impact calculation"""
    # Setup system
    system_id = await test_create_product_system()

    # Find TRACI method
    method_result = await handle_search_impact_methods({
        "keywords": ["TRACI"]
    })
    method_data = json.loads(method_result[0].text)
    method_id = method_data["method"]["id"]

    # Calculate
    result = await handle_calculate_impacts({
        "system_id": system_id,
        "method_id": method_id,
        "amount": 1.0
    })

    data = json.loads(result[0].text)
    assert data["success"] == True
    assert "impacts" in data
    assert "result_id" in data
    print(f"✓ Calculated {len(data['impacts'])} impacts")

    return data["result_id"]
```

**Test 4.2: Result Disposal**
```python
@pytest.mark.asyncio
async def test_dispose_result():
    """Test result disposal"""
    # Calculate first
    result_id = await test_calculate_impacts()

    # Dispose
    result = await handle_dispose_result({
        "result_id": result_id
    })

    data = json.loads(result[0].text)
    assert data["success"] == True
    print("✓ Result disposed successfully")
```

### Test Suite 5: Error Handling

**Test 5.1: Invalid Flow Search**
```python
@pytest.mark.asyncio
async def test_invalid_flow_search():
    """Test error handling for non-existent flows"""
    result = await handle_search_flows({
        "keywords": ["xyznonexistentmaterial123"],
        "max_results": 5
    })

    data = json.loads(result[0].text)
    # Should succeed but return 0 results
    assert data["success"] == True
    assert data["count"] == 0
    print("✓ Handled non-existent flow gracefully")
```

**Test 5.2: Invalid Process Creation**
```python
@pytest.mark.asyncio
async def test_invalid_process():
    """Test error handling for invalid exchanges"""
    result = await handle_create_process({
        "name": "Invalid Process",
        "exchanges": [
            {
                "flow_id": "nonexistent-flow-id",
                "amount": 1.0,
                "is_input": False,
                "is_quantitative_reference": True
            }
        ]
    })

    data = json.loads(result[0].text)
    assert data["success"] == False
    assert "error" in data
    print("✓ Error handled correctly")
```

---

## AI Agent Testing

### Agent Test 1: Complete LCA Workflow

**Objective:** Test AI agent's ability to execute full 4-phase LCA

**Test Procedure:**
1. Agent receives task: "Perform LCA of 1kg steel production"
2. Agent uses tools autonomously
3. Verify all 4 phases completed
4. Check result accuracy

**Expected Tool Sequence:**
```
1. test_connection() → Verify access
2. search_flows(["steel", "production"]) → Find steel
3. find_providers(flow_id) → Get process
4. search_impact_methods(["TRACI"]) → Get method
5. create_product_system(process_id) → Build system
6. calculate_impacts(system_id, method_id) → Calculate
7. export_results(data, "steel_lca.csv") → Export
8. dispose_result(result_id) → Clean up
```

**Success Criteria:**
- All tools called correctly
- No errors in sequence
- Results exported successfully
- Memory cleaned up

### Agent Test 2: Comparative LCA

**Objective:** Test agent's ability to compare alternatives

**Test Procedure:**
1. Task: "Compare PET vs PC bottles"
2. Agent must create 2 systems
3. Calculate impacts for both
4. Generate comparison report

**Expected Behavior:**
- Create 2 separate product systems
- Calculate impacts for both
- Compare results
- Identify which is better for each impact category
- Dispose both results

### Agent Test 3: Error Recovery

**Objective:** Test agent's error handling

**Test Procedure:**
1. Task: "Calculate impacts using nonexistent material"
2. Agent encounters error
3. Agent recovers and suggests alternatives

**Expected Behavior:**
- Try initial search
- Recognize failure
- Search with alternative keywords
- Report to user if still failing
- Don't crash or loop indefinitely

---

## Case Studies

### Case Study 1: PET vs PC Bottles
See: [CASE_STUDY_PET_PC.md](CASE_STUDY_PET_PC.md)

### Case Study 2: Ceramic Cup vs Paper Cup
See: [CASE_STUDY_CUPS.md](CASE_STUDY_CUPS.md)

### Case Study 3: Complete Systems Analysis
See: [SYSTEMS_ANALYSIS_GUIDE.md](SYSTEMS_ANALYSIS_GUIDE.md)

---

## Performance Evaluation

### Metrics

#### 1. Response Time
- Tool call latency: < 100ms for search
- Calculation time: varies by system complexity
- Target: < 5s for typical product systems

#### 2. Accuracy
- Results match manual OpenLCA calculations
- Within 0.1% for deterministic calculations
- Monte Carlo: mean within 5% of analytical

#### 3. Reliability
- Uptime: 99%+ during openLCA availability
- Error rate: < 1% for valid inputs
- Memory leaks: 0 (with proper disposal)

#### 4. Throughput
- Concurrent calculations: 5+
- Tools per second: 10+
- Large systems (1000+ processes): < 30s

### Benchmarking

**Benchmark 1: Simple System**
```
System: 1 process, 5 exchanges
Method: TRACI 2.1
Target: < 2 seconds total
```

**Benchmark 2: Complex System**
```
System: 50 processes, 200 exchanges
Method: ReCiPe 2016
Target: < 15 seconds total
```

**Benchmark 3: Database Search**
```
Search: 1000 flows
Target: < 500ms
```

---

## Validation Procedures

### Validation 1: Result Accuracy

**Procedure:**
1. Perform LCA manually in OpenLCA desktop
2. Perform same LCA via MCP server
3. Compare results

**Acceptance Criteria:**
- Impact values match exactly
- Flow amounts match exactly
- Process contributions match

**Example:**
```python
# Manual calculation in OpenLCA:
# Global Warming Potential = 1.234 kg CO2 eq

# MCP Server calculation:
assert abs(gwp_mcp - 1.234) < 0.001
```

### Validation 2: Database Consistency

**Procedure:**
1. Create data via MCP server
2. Verify in OpenLCA desktop
3. Modify in desktop
4. Verify changes visible to MCP server

**Acceptance Criteria:**
- All created objects visible in desktop
- All properties correctly set
- Changes in desktop reflected in MCP server

### Validation 3: ISO Compliance

**Verify:**
- [ ] Phase 1: Goal & Scope properly defined
- [ ] Phase 2: Complete inventory created
- [ ] Phase 3: LCIA performed correctly
- [ ] Phase 4: Interpretation includes contribution analysis
- [ ] Functional unit clearly defined
- [ ] System boundaries explicit
- [ ] Data quality documented
- [ ] Assumptions stated

---

## Troubleshooting

### Common Issues

#### Issue 1: Connection Fails

**Symptoms:**
```json
{
  "success": false,
  "error": "Could not connect to openLCA"
}
```

**Solutions:**
1. Check OpenLCA is running
2. Verify database loaded
3. Start IPC server in OpenLCA
4. Check port matches (.env vs OpenLCA)
5. Check firewall settings

#### Issue 2: Flow Not Found

**Symptoms:**
```json
{
  "success": true,
  "count": 0,
  "flows": []
}
```

**Solutions:**
1. Try broader keywords
2. Check spelling
3. Try alternative material names
4. Verify database has ecoinvent data
5. Use OpenLCA search to find correct name

#### Issue 3: Calculation Fails

**Symptoms:**
```json
{
  "success": false,
  "error": "Calculation failed"
}
```

**Solutions:**
1. Verify product system complete
2. Check all exchanges linked
3. Verify impact method exists
4. Try calculation in OpenLCA desktop first
5. Check logs for detailed error

#### Issue 4: Memory Issues

**Symptoms:**
- OpenLCA becomes slow
- Calculations take longer over time
- Out of memory errors

**Solutions:**
1. Always call dispose_result()
2. Restart OpenLCA periodically
3. Limit concurrent calculations
4. Close unused databases
5. Increase Java heap size in OpenLCA

---

## Test Execution Checklist

### Pre-Test Setup
- [ ] OpenLCA desktop running
- [ ] Database loaded (ecoinvent recommended)
- [ ] IPC server started
- [ ] MCP server configured
- [ ] Test environment isolated
- [ ] Logging enabled

### During Testing
- [ ] Monitor logs for errors
- [ ] Record response times
- [ ] Document failures
- [ ] Save test results
- [ ] Take screenshots if GUI involved

### Post-Test Validation
- [ ] All results disposed
- [ ] No memory leaks
- [ ] Database unchanged (unless expected)
- [ ] Logs reviewed
- [ ] Results documented

### Test Reporting
- [ ] Test cases executed
- [ ] Pass/fail status
- [ ] Performance metrics
- [ ] Issues identified
- [ ] Recommendations

---

## Continuous Integration

### Automated Test Suite

```bash
# Run all tests
pytest tests/ -v

# Run specific test suite
pytest tests/test_connection.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run performance tests
pytest tests/test_performance.py -v --durations=10
```

### CI/CD Pipeline

```yaml
# .github/workflows/test.yml
name: MCP Server Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.10
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest tests/ -v
```

---

## Conclusion

This test and evaluation framework ensures the MCP server and AI agents work reliably for LCA automation. Regular testing against real case studies validates both functionality and accuracy.

For practical examples, see:
- [Client Test Examples](CLIENT_TEST_EXAMPLES.md)
- [PET vs PC Case Study](CASE_STUDY_PET_PC.md)
- [Cups Case Study](CASE_STUDY_CUPS.md)
- [Systems Analysis Guide](SYSTEMS_ANALYSIS_GUIDE.md)

---

**Last Updated:** 2025-12-04
**Version:** 1.0
**Status:** Production Ready
