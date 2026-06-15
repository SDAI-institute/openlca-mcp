# Multi-Agent Prompt Engineering for LCA Automation

## Overview

This guide provides comprehensive strategies for designing multi-agent systems to automate Life Cycle Assessment workflows using the OpenLCA MCP Server. It covers prompt engineering techniques, agent orchestration patterns, and best practices for reliable LCA automation.

## Table of Contents

1. [Multi-Agent Architecture](#1-multi-agent-architecture)
2. [Agent Role Design](#2-agent-role-design)
3. [Prompt Engineering Patterns](#3-prompt-engineering-patterns)
4. [Agent Communication Protocols](#4-agent-communication-protocols)
5. [Error Handling and Recovery](#5-error-handling-and-recovery)
6. [Optimization Techniques](#6-optimization-techniques)
7. [Production Deployment](#7-production-deployment)

---

## 1. Multi-Agent Architecture

### 1.1 Why Multi-Agent for LCA?

**Single Agent Limitations:**
- Long context windows → information loss
- Complex decision trees → unreliable execution
- Multiple objectives → conflicting priorities
- Single failure point → brittle systems

**Multi-Agent Advantages:**
- ✅ **Specialization:** Each agent expert in one LCA phase
- ✅ **Modularity:** Easy to debug and improve individual agents
- ✅ **Parallel execution:** Multiple analyses simultaneously
- ✅ **Robustness:** Failure isolation and recovery
- ✅ **Maintainability:** Clear separation of concerns

### 1.2 Architecture Patterns

#### Pattern 1: Sequential Pipeline (ISO 14044 Aligned)

```
┌─────────────────────────────────────────────────────────────┐
│                    SEQUENTIAL PIPELINE                       │
└─────────────────────────────────────────────────────────────┘

User Request
    │
    ▼
┌─────────────────────┐
│  Coordinator Agent  │  • Parse user request
│                     │  • Define study parameters
│                     │  • Route to Phase 1
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Phase 1 Agent      │  • Goal & Scope Definition
│  (Goal & Scope)     │  • Search materials/processes
│                     │  • Select impact method
└──────────┬──────────┘
           │
           │ [Materials List, Method ID]
           ▼
┌─────────────────────┐
│  Phase 2 Agent      │  • Life Cycle Inventory
│  (LCI Builder)      │  • Create flows & processes
│                     │  • Build product systems
└──────────┬──────────┘
           │
           │ [System ID]
           ▼
┌─────────────────────┐
│  Phase 3 Agent      │  • Life Cycle Impact Assessment
│  (Calculator)       │  • Calculate impacts
│                     │  • Extract results
└──────────┬──────────┘
           │
           │ [Result ID, Impacts]
           ▼
┌─────────────────────┐
│  Phase 4 Agent      │  • Interpretation
│  (Analyst)          │  • Contribution analysis
│                     │  • Generate report
│                     │  • Dispose results
└──────────┬──────────┘
           │
           ▼
       Final Report
```

**Advantages:**
- Clear handoffs between phases
- Easy to debug (know exactly where failure occurred)
- Matches ISO 14044 methodology
- Predictable execution flow

**Disadvantages:**
- No parallelism
- Slower for multiple scenarios
- Each agent waits for previous

**Best For:**
- Single product assessments
- Educational/training systems
- Auditable workflows

#### Pattern 2: Parallel Comparison

```
┌─────────────────────────────────────────────────────────────┐
│                    PARALLEL COMPARISON                       │
└─────────────────────────────────────────────────────────────┘

User Request: "Compare PET vs PC vs Glass"
    │
    ▼
┌─────────────────────┐
│  Coordinator Agent  │  • Identify alternatives
│                     │  • Spawn parallel workers
│                     │  • Aggregate results
└─────┬───────┬───────┘
      │       │       │
      │       │       └──────────────┐
      │       └─────────┐            │
      │                 │            │
      ▼                 ▼            ▼
┌──────────┐      ┌──────────┐ ┌──────────┐
│ Worker 1 │      │ Worker 2 │ │ Worker 3 │
│   PET    │      │    PC    │ │  Glass   │
│          │      │          │ │          │
│ Phase 1-4│      │ Phase 1-4│ │ Phase 1-4│
└────┬─────┘      └────┬─────┘ └────┬─────┘
     │                 │            │
     │  [PET Results]  │ [PC Results] │ [Glass Results]
     └────────┬────────┴────────┬────┘
              │                 │
              ▼                 ▼
        ┌──────────────────────────┐
        │   Comparison Agent       │
        │  • Compare impacts       │
        │  • Rank alternatives     │
        │  • Generate recommendation│
        └──────────┬───────────────┘
                   │
                   ▼
           Comparative Report
```

**Advantages:**
- Fast (parallel execution)
- Scalable to many alternatives
- Independent failure handling

**Disadvantages:**
- More complex coordination
- Higher resource usage
- Result synchronization needed

**Best For:**
- Product comparisons
- Scenario analysis
- High-volume screening

#### Pattern 3: Hierarchical Specialist

```
┌─────────────────────────────────────────────────────────────┐
│                  HIERARCHICAL SPECIALIST                     │
└─────────────────────────────────────────────────────────────┘

User Request
    │
    ▼
┌──────────────────────┐
│   Master Agent       │  • High-level strategy
│   (Strategic)        │  • Task decomposition
│                      │  • Quality control
└────────┬─────────────┘
         │
         ├─────────────┬─────────────┬─────────────┐
         ▼             ▼             ▼             ▼
┌────────────┐  ┌────────────┐ ┌──────────┐ ┌──────────┐
│ Search     │  │ Modeling   │ │Calculation│ │ Analysis │
│ Specialist │  │ Specialist │ │ Specialist│ │Specialist│
│            │  │            │ │           │ │          │
│• Database  │  │• Flows     │ │• Systems  │ │• Contrib.│
│  queries   │  │• Processes │ │• Impacts  │ │• Sensitivity│
│• Provider  │  │• Exchanges │ │• Results  │ │• Reports │
│  finding   │  │• Linking   │ │           │ │          │
└─────┬──────┘  └─────┬──────┘ └─────┬─────┘ └─────┬────┘
      │               │              │             │
      └───────────────┴──────────────┴─────────────┘
                           │
                           ▼
                    Master Agent
                    (Synthesis)
```

**Advantages:**
- Deep expertise per domain
- Reusable specialists
- Better error handling (specialist retry)
- Scalable complexity

**Disadvantages:**
- Complex orchestration
- More agents to manage
- Higher latency (more handoffs)

**Best For:**
- Complex systems
- Reusable workflows
- Production environments

### 1.3 Hybrid Architecture (Recommended)

```
┌─────────────────────────────────────────────────────────────┐
│                    HYBRID ARCHITECTURE                       │
│            (Sequential Phases + Parallel Scenarios)          │
└─────────────────────────────────────────────────────────────┘

                    ┌─────────────────┐
                    │  Orchestrator   │
                    │    Agent        │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  Scenario A   │    │  Scenario B   │    │  Scenario C   │
│   Pipeline    │    │   Pipeline    │    │   Pipeline    │
│               │    │               │    │               │
│ Phase 1 Agent │    │ Phase 1 Agent │    │ Phase 1 Agent │
│      ↓        │    │      ↓        │    │      ↓        │
│ Phase 2 Agent │    │ Phase 2 Agent │    │ Phase 2 Agent │
│      ↓        │    │      ↓        │    │      ↓        │
│ Phase 3 Agent │    │ Phase 3 Agent │    │ Phase 3 Agent │
│      ↓        │    │      ↓        │    │      ↓        │
│ Phase 4 Agent │    │ Phase 4 Agent │    │ Phase 4 Agent │
└───────┬───────┘    └───────┬───────┘    └───────┬───────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   Synthesis     │
                    │     Agent       │
                    └─────────────────┘
```

**Combines Best of Both:**
- Sequential within each scenario (reliable)
- Parallel across scenarios (fast)
- Centralized orchestration (controllable)

---

## 2. Agent Role Design

### 2.1 Phase-Based Agent Roles

#### Agent 1: Goal & Scope Specialist

**Responsibilities:**
1. Interpret user requirements
2. Define functional unit
3. Set system boundaries
4. Search for materials and processes
5. Select impact assessment method

**Required Capabilities:**
- Natural language understanding
- Domain knowledge (LCA methodology)
- Database search skills
- Requirement clarification

**Prompt Template:**
```
You are a Goal & Scope Definition specialist for Life Cycle Assessment.

Your responsibilities:
1. Understand the user's assessment objectives
2. Define a clear functional unit
3. Establish system boundaries
4. Search the ecoinvent database for required materials and processes
5. Select an appropriate LCIA method

Available MCP Tools:
- test_connection: Verify OpenLCA access
- search_flows: Find materials and products
- search_processes: Find production processes
- find_providers: Get process providers
- search_impact_methods: Find LCIA methods

Input from user:
{user_request}

Your task:
1. Parse the request and identify:
   - Product(s) to assess
   - Functional unit
   - Required materials
   - System boundary (cradle-to-gate, cradle-to-grave, etc.)
   - Preferred impact method

2. Search for all required materials using search_flows
3. Find providers for each material using find_providers
4. Search for appropriate LCIA method using search_impact_methods

Output format:
Return a JSON object with:
{
  "functional_unit": "Description",
  "system_boundary": "Type and scope",
  "materials": [
    {"name": "Material", "flow_id": "ID", "provider_id": "ID", "amount": 0.0}
  ],
  "impact_method": {"name": "Method name", "id": "ID"},
  "notes": "Any assumptions or clarifications"
}

Be thorough and ask for clarification if requirements are ambiguous.
```

#### Agent 2: LCI Builder Specialist

**Responsibilities:**
1. Create product flows
2. Create processes with exchanges
3. Link processes via providers
4. Build product systems

**Required Capabilities:**
- Data structure understanding
- Process modeling
- Mass balance validation
- Exchange linking

**Prompt Template:**
```
You are a Life Cycle Inventory (LCI) Builder specialist.

Your responsibilities:
1. Create product flows for the system
2. Model processes with correct exchanges
3. Link processes via default providers
4. Build complete product systems

Available MCP Tools:
- create_product_flow: Define new products
- create_process: Model unit processes with exchanges
- create_product_system: Build calculable systems

Input from Phase 1 Agent:
{materials_and_providers}

Your task:
1. For each unique product in the system:
   - Create a product_flow (if not in database)

2. For each transformation step:
   - Create a process with:
     * One quantitative reference (main output)
     * All material inputs (linked to providers)
     * Energy/transport inputs if applicable

3. Create product system from final process

Critical requirements:
- All exchanges must have amounts in kg
- All inputs must have valid provider_id
- Quantitative reference must be clearly defined
- Mass balance should be reasonable

Output format:
{
  "flows_created": [{"name": "...", "id": "..."}],
  "processes_created": [{"name": "...", "id": "...", "exchanges_count": 0}],
  "product_system": {"name": "...", "id": "..."},
  "validation": {
    "mass_balance": "OK/Warning",
    "all_linked": true/false
  }
}

Validate your work before passing to calculation phase.
```

#### Agent 3: LCIA Calculator Specialist

**Responsibilities:**
1. Execute impact calculations
2. Extract results
3. Store result IDs for later disposal

**Required Capabilities:**
- Calculation execution
- Result extraction
- Error handling

**Prompt Template:**
```
You are a Life Cycle Impact Assessment (LCIA) Calculator specialist.

Your responsibilities:
1. Execute impact calculations for product systems
2. Extract and structure impact results
3. Manage result lifecycle (store IDs for disposal)

Available MCP Tools:
- calculate_impacts: Run LCIA calculations
- get_inventory_results: Extract detailed inventory (optional)

Input from Phase 2 Agent:
{product_system_id}
{impact_method_id}

Your task:
1. Calculate impacts using calculate_impacts tool
   - Use system_id from Phase 2
   - Use method_id from Phase 1
   - Amount: 1.0 (per functional unit)

2. Extract all impact results

3. Store result_id for cleanup

Critical requirements:
- Always check for calculation errors
- Verify all impact categories returned
- Store result_id for Phase 4 disposal
- Handle units correctly

Output format:
{
  "result_id": "...",
  "calculation_status": "success/failed",
  "impacts": [
    {
      "category": "Global Warming",
      "amount": 0.0234,
      "unit": "kg CO2 eq"
    },
    ...
  ],
  "inventory_flows_count": 1234,
  "calculation_time_seconds": 5.2
}

IMPORTANT: Pass result_id to Phase 4 for proper cleanup.
```

#### Agent 4: Interpretation Specialist

**Responsibilities:**
1. Perform contribution analysis
2. Identify hotspots
3. Generate insights and recommendations
4. Dispose calculation results

**Required Capabilities:**
- Data analysis
- Pattern recognition
- Recommendation generation
- Resource cleanup

**Prompt Template:**
```
You are an LCA Interpretation specialist.

Your responsibilities:
1. Analyze impact results to identify hotspots
2. Perform contribution analysis
3. Generate actionable insights
4. Clean up calculation results

Available MCP Tools:
- analyze_contributions: Identify top contributors (if available)
- export_results: Save results to files
- dispose_result: Clean up calculation results (CRITICAL)

Input from Phase 3 Agent:
{result_id}
{impacts}

Your task:
1. Analyze impact results:
   - Identify highest impact categories
   - Determine which are most concerning
   - Look for patterns

2. Generate insights:
   - What are the environmental hotspots?
   - Which life cycle stages dominate?
   - What improvement opportunities exist?

3. Create recommendations:
   - Material substitutions
   - Process improvements
   - Design changes

4. CRITICAL: Dispose result using dispose_result tool

Output format:
{
  "summary": {
    "highest_impacts": ["Category 1", "Category 2", "Category 3"],
    "hotspots": ["Process/material with biggest contribution"],
    "total_categories_analyzed": 13
  },
  "detailed_analysis": {
    "by_impact_category": [
      {
        "category": "Global Warming",
        "amount": 0.0234,
        "ranking": 1,
        "top_contributors": [
          {"process": "...", "share_percent": 67.2}
        ]
      }
    ]
  },
  "recommendations": [
    "Use recycled aluminum instead of primary (save 45% GWP)",
    "Optimize transport distance (current: 500km)",
    "Consider renewable electricity source"
  ],
  "result_disposed": true
}

NEVER forget to dispose results - memory leaks are unacceptable!
```

### 2.2 Specialist Agent Roles

#### Database Search Specialist

**Expertise:** Efficiently finding materials and processes in ecoinvent

**Prompt Template:**
```
You are a Database Search specialist for ecoinvent.

Expertise:
- Understanding ecoinvent naming conventions
- Multi-level search strategies (broad → specific)
- Regional geography codes (RER, GLO, US, etc.)
- Material grades and forms

Search strategy:
1. Start broad, get specific
2. Use hierarchical keywords
3. Understand geography codes
4. Know common material names

Examples:
- "polyethylene terephthalate" → "PET granulate bottle grade"
- "steel" → "steel hot rolled RER"
- "electricity" → "electricity medium voltage production ENTSO-E"

When searching:
1. Try broad keywords first
2. Add form factor (granulate, sheet, etc.)
3. Add grade/application (bottle, industrial, etc.)
4. Add geography (RER, GLO, US, etc.)
5. Return top 3 matches with justification

Your goal: Find the MOST APPROPRIATE flow/process, not just any match.
```

#### Validation Specialist

**Expertise:** Checking model validity and data quality

**Prompt Template:**
```
You are a Model Validation specialist.

Your responsibilities:
1. Validate mass balances
2. Check process linkages
3. Verify data quality
4. Flag potential errors

Validation checks:
□ Mass balance: Inputs ≈ Outputs (within 10%)
□ All exchanges have valid units
□ All inputs have providers
□ Functional unit clearly defined
□ System boundary consistent
□ No circular references
□ Impact method appropriate

Input:
{product_system_structure}

Output validation report:
{
  "validation_status": "PASS/FAIL/WARNING",
  "checks": [
    {
      "check": "Mass balance",
      "status": "PASS",
      "details": "Inputs: 1.05 kg, Outputs: 1.02 kg (3% loss)"
    },
    ...
  ],
  "errors": [],
  "warnings": [
    "Material X not regionally specific (using GLO)"
  ],
  "recommendations": [
    "Consider using regional electricity mix"
  ]
}

Be thorough but practical - minor warnings are OK, errors must be fixed.
```

---

## 3. Prompt Engineering Patterns

### 3.1 Structured Prompts

#### Pattern: Role-Task-Format (RTF)

```
[ROLE]
You are a {specialist_type} for Life Cycle Assessment.
Your expertise: {domain_knowledge}

[TASK]
Your specific task:
1. {step_1}
2. {step_2}
3. {step_3}

[CONTEXT]
Input data:
{input_data}

Constraints:
- {constraint_1}
- {constraint_2}

[FORMAT]
Output format:
{expected_structure}

Examples:
{example_output}

[ERROR_HANDLING]
If you encounter:
- {error_type_1}: {recovery_action_1}
- {error_type_2}: {recovery_action_2}
```

**Example:**
```
[ROLE]
You are a Material Search specialist for LCA databases.
Your expertise: ecoinvent database structure, material naming conventions, regional variations.

[TASK]
Your specific task:
1. Parse the material request
2. Generate appropriate search keywords
3. Execute search using search_flows tool
4. Select best match based on region and quality
5. Return material ID and provider ID

[CONTEXT]
Material requested: "aluminum for beverage cans in Europe"

Constraints:
- Must be European region (RER) if available
- Must be appropriate form (sheet/rolled)
- Must be food-grade quality

[FORMAT]
Output format:
{
  "material_found": true,
  "flow_id": "...",
  "flow_name": "...",
  "provider_id": "...",
  "provider_name": "...",
  "confidence": "high/medium/low",
  "alternatives": ["...", "..."]
}

[ERROR_HANDLING]
If you encounter:
- No exact match: Return top 3 alternatives with explanation
- Multiple matches: Select most specific, note alternatives
- Wrong region: Use global (GLO) and note substitution
```

### 3.2 Few-Shot Learning

#### Pattern: Example-Based Prompting

```
You are an LCI modeling specialist. Learn from these examples:

EXAMPLE 1:
Input: "Create process for PET bottle production from granulate"
Actions:
1. create_product_flow("PET bottle 0.5L", "Bottle product")
2. create_process("PET bottle production", exchanges=[
     {flow: "PET bottle 0.5L", amount: 1.0, is_input: false, is_qref: true},
     {flow: "PET granulate", amount: 0.025, is_input: true, provider: "PET_prod_id"}
   ])
Output: {process_id: "...", validation: "PASS"}

EXAMPLE 2:
Input: "Create process for aluminum can with multiple materials"
Actions:
1. create_product_flow("Aluminum can 330ml", "Beverage can")
2. create_process("Can production", exchanges=[
     {flow: "Aluminum can 330ml", amount: 1.0, is_input: false, is_qref: true},
     {flow: "Aluminum sheet", amount: 0.015, is_input: true, provider: "Al_rolling_id"},
     {flow: "Coating polymer", amount: 0.0005, is_input: true, provider: "Polymer_id"},
     {flow: "Electricity", amount: 0.08, is_input: true, provider: "Elec_id"}
   ])
Output: {process_id: "...", validation: "PASS"}

Now handle this request:
{user_request}

Follow the same pattern: create flows, model exchanges, validate.
```

### 3.3 Chain-of-Thought Prompting

#### Pattern: Reasoning Steps

```
You are calculating environmental impacts. Think step-by-step:

STEP 1: UNDERSTAND THE SYSTEM
- What product are we assessing?
- What is the functional unit?
- What system boundaries are included?

Reasoning: {your_analysis}

STEP 2: VERIFY INPUTS
- Do we have a valid product_system_id?
- Do we have a valid impact_method_id?
- Are we calculating per functional unit (amount=1.0)?

Verification: {your_checks}

STEP 3: EXECUTE CALCULATION
- Call calculate_impacts with verified parameters
- Check for errors in response
- Extract result_id

Execution: {your_actions}

STEP 4: VALIDATE RESULTS
- Do all impact categories have values?
- Are values reasonable (not 0 or extremely high)?
- Are units correct?

Validation: {your_assessment}

STEP 5: PREPARE OUTPUT
- Structure results in required format
- Store result_id for cleanup
- Add metadata (calculation time, data quality)

Output: {structured_results}

By thinking through each step, you ensure reliable calculations.
```

### 3.4 Error Recovery Prompting

#### Pattern: Resilient Execution

```
You are a robust LCA agent with error recovery capabilities.

EXECUTION PATTERN:

try:
    Primary approach: {ideal_method}

except MaterialNotFound:
    Recovery strategy:
    1. Search with broader keywords
    2. Try alternative spellings
    3. Search in different regions (GLO instead of RER)
    4. Document substitution made

except ProviderNotFound:
    Recovery strategy:
    1. Check if elementary flow (no provider needed)
    2. Search for alternative providers
    3. Use market average if available
    4. Create custom process if necessary

except CalculationFailed:
    Recovery strategy:
    1. Verify product system is complete
    2. Check all exchanges linked
    3. Try with different solver settings
    4. Report detailed error to user

except ResultsUnreasonable:
    Recovery strategy:
    1. Compare with reference values
    2. Check units and conversions
    3. Verify input amounts
    4. Request validation from user

IMPORTANT: Always try to recover, but know when to escalate to user.

Log all recovery actions for transparency.
```

---

## 4. Agent Communication Protocols

### 4.1 Message Passing Format

#### Standard Message Structure

```json
{
  "message_id": "uuid-v4",
  "timestamp": "2025-12-04T10:30:00Z",
  "from_agent": "phase_1_goal_scope",
  "to_agent": "phase_2_lci_builder",
  "message_type": "HANDOFF",
  "status": "SUCCESS",
  "data": {
    "functional_unit": "1 filled PET bottle (1.065 kg)",
    "system_boundary": "cradle-to-gate",
    "materials": [
      {
        "name": "PET granulate",
        "flow_id": "abc-123",
        "provider_id": "def-456",
        "amount": 0.060,
        "unit": "kg"
      },
      {
        "name": "HDPE granulate",
        "flow_id": "ghi-789",
        "provider_id": "jkl-012",
        "amount": 0.004,
        "unit": "kg"
      }
    ],
    "impact_method": {
      "name": "TRACI 2.1",
      "id": "mno-345"
    }
  },
  "metadata": {
    "confidence": "high",
    "assumptions": [
      "Using European average processes (RER)"
    ],
    "warnings": [
      "Water source not specified, using tap water"
    ]
  }
}
```

#### Message Types

1. **HANDOFF** - Normal phase transition
2. **ERROR** - Recoverable error occurred
3. **FATAL** - Unrecoverable error, abort workflow
4. **QUERY** - Request clarification
5. **RESPONSE** - Answer to query
6. **VALIDATION** - Request validation check
7. **COMPLETE** - Workflow complete

### 4.2 State Management

#### Centralized State Store

```python
"""
Centralized state management for multi-agent workflows
"""

class WorkflowState:
    """
    Maintains state across agent handoffs
    """

    def __init__(self, workflow_id):
        self.workflow_id = workflow_id
        self.current_phase = 1
        self.status = "RUNNING"

        self.goal_scope = {}
        self.inventory = {}
        self.impacts = {}
        self.interpretation = {}

        self.result_ids = []  # For cleanup
        self.errors = []
        self.warnings = []

    def update_phase_1(self, data):
        """Phase 1: Goal & Scope"""
        self.goal_scope = data
        self.current_phase = 2

    def update_phase_2(self, data):
        """Phase 2: LCI"""
        self.inventory = data
        self.current_phase = 3

    def update_phase_3(self, data):
        """Phase 3: LCIA"""
        self.impacts = data
        if 'result_id' in data:
            self.result_ids.append(data['result_id'])
        self.current_phase = 4

    def update_phase_4(self, data):
        """Phase 4: Interpretation"""
        self.interpretation = data
        self.status = "COMPLETE"

    def get_context_for_phase(self, phase_number):
        """Get relevant context for agent"""
        context = {
            'workflow_id': self.workflow_id,
            'current_phase': phase_number,
            'errors': self.errors,
            'warnings': self.warnings
        }

        if phase_number >= 2:
            context['goal_scope'] = self.goal_scope
        if phase_number >= 3:
            context['inventory'] = self.inventory
        if phase_number >= 4:
            context['impacts'] = self.impacts

        return context

    def add_error(self, phase, error_msg):
        """Record error"""
        self.errors.append({
            'phase': phase,
            'message': error_msg,
            'timestamp': datetime.now().isoformat()
        })

    def add_warning(self, phase, warning_msg):
        """Record warning"""
        self.warnings.append({
            'phase': phase,
            'message': warning_msg,
            'timestamp': datetime.now().isoformat()
        })

    def cleanup(self, client):
        """Dispose all results"""
        for result_id in self.result_ids:
            try:
                client.results.dispose(result_id)
            except Exception as e:
                print(f"Failed to dispose {result_id}: {e}")
```

### 4.3 Orchestration Patterns

#### Pattern 1: Linear Orchestrator

```python
"""
Linear orchestrator for sequential agent execution
"""

class LinearOrchestrator:
    """
    Orchestrates agents in sequential order
    """

    def __init__(self, agents):
        self.agents = agents  # List of agent functions
        self.state = WorkflowState(str(uuid.uuid4()))

    async def execute(self, user_request):
        """
        Execute workflow sequentially
        """

        # Phase 1: Goal & Scope
        print("=== PHASE 1: GOAL & SCOPE ===")
        phase1_result = await self.agents[0](
            request=user_request,
            context=self.state.get_context_for_phase(1)
        )

        if phase1_result['status'] != 'SUCCESS':
            return {'error': 'Phase 1 failed', 'details': phase1_result}

        self.state.update_phase_1(phase1_result['data'])

        # Phase 2: LCI
        print("=== PHASE 2: LIFE CYCLE INVENTORY ===")
        phase2_result = await self.agents[1](
            materials=phase1_result['data']['materials'],
            context=self.state.get_context_for_phase(2)
        )

        if phase2_result['status'] != 'SUCCESS':
            return {'error': 'Phase 2 failed', 'details': phase2_result}

        self.state.update_phase_2(phase2_result['data'])

        # Phase 3: LCIA
        print("=== PHASE 3: IMPACT ASSESSMENT ===")
        phase3_result = await self.agents[2](
            system_id=phase2_result['data']['product_system']['id'],
            method_id=phase1_result['data']['impact_method']['id'],
            context=self.state.get_context_for_phase(3)
        )

        if phase3_result['status'] != 'SUCCESS':
            return {'error': 'Phase 3 failed', 'details': phase3_result}

        self.state.update_phase_3(phase3_result['data'])

        # Phase 4: Interpretation
        print("=== PHASE 4: INTERPRETATION ===")
        phase4_result = await self.agents[3](
            result_id=phase3_result['data']['result_id'],
            impacts=phase3_result['data']['impacts'],
            context=self.state.get_context_for_phase(4)
        )

        if phase4_result['status'] != 'SUCCESS':
            return {'error': 'Phase 4 failed', 'details': phase4_result}

        self.state.update_phase_4(phase4_result['data'])

        # Cleanup
        print("=== CLEANUP ===")
        self.state.cleanup(client)

        return {
            'status': 'SUCCESS',
            'workflow_id': self.state.workflow_id,
            'results': self.state.interpretation,
            'warnings': self.state.warnings,
            'errors': self.state.errors
        }
```

#### Pattern 2: Parallel Orchestrator

```python
"""
Parallel orchestrator for concurrent scenario execution
"""

import asyncio

class ParallelOrchestrator:
    """
    Orchestrates multiple scenarios in parallel
    """

    def __init__(self, scenario_agents):
        self.scenario_agents = scenario_agents
        self.states = {}

    async def execute_scenario(self, scenario_name, scenario_spec):
        """
        Execute one scenario (full 4-phase workflow)
        """

        state = WorkflowState(f"{scenario_name}_{uuid.uuid4()}")
        self.states[scenario_name] = state

        try:
            # Phase 1
            phase1_result = await self.scenario_agents['phase1'](
                request=scenario_spec,
                context=state.get_context_for_phase(1)
            )
            state.update_phase_1(phase1_result['data'])

            # Phase 2
            phase2_result = await self.scenario_agents['phase2'](
                materials=phase1_result['data']['materials'],
                context=state.get_context_for_phase(2)
            )
            state.update_phase_2(phase2_result['data'])

            # Phase 3
            phase3_result = await self.scenario_agents['phase3'](
                system_id=phase2_result['data']['product_system']['id'],
                method_id=phase1_result['data']['impact_method']['id'],
                context=state.get_context_for_phase(3)
            )
            state.update_phase_3(phase3_result['data'])

            # Phase 4
            phase4_result = await self.scenario_agents['phase4'](
                result_id=phase3_result['data']['result_id'],
                impacts=phase3_result['data']['impacts'],
                context=state.get_context_for_phase(4)
            )
            state.update_phase_4(phase4_result['data'])

            return {
                'scenario': scenario_name,
                'status': 'SUCCESS',
                'results': state.interpretation
            }

        except Exception as e:
            state.add_error(state.current_phase, str(e))
            return {
                'scenario': scenario_name,
                'status': 'FAILED',
                'error': str(e)
            }

    async def execute_all(self, scenarios):
        """
        Execute all scenarios in parallel
        """

        print(f"=== EXECUTING {len(scenarios)} SCENARIOS IN PARALLEL ===")

        # Create tasks for all scenarios
        tasks = [
            self.execute_scenario(name, spec)
            for name, spec in scenarios.items()
        ]

        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Cleanup all states
        print("=== CLEANUP ===")
        for state in self.states.values():
            state.cleanup(client)

        # Aggregate results
        successful = [r for r in results if r.get('status') == 'SUCCESS']
        failed = [r for r in results if r.get('status') == 'FAILED']

        return {
            'total_scenarios': len(scenarios),
            'successful': len(successful),
            'failed': len(failed),
            'results': successful,
            'errors': failed
        }

# Usage
orchestrator = ParallelOrchestrator(scenario_agents)

scenarios = {
    'PET_Bottle': {...},
    'PC_Bottle': {...},
    'Glass_Bottle': {...}
}

results = await orchestrator.execute_all(scenarios)
```

---

## 5. Error Handling and Recovery

### 5.1 Error Categories

#### Category 1: Data Not Found

```python
"""
Handle missing data gracefully
"""

class DataNotFoundHandler:
    """
    Strategies for handling missing materials/processes
    """

    @staticmethod
    def handle_material_not_found(material_name, original_keywords):
        """
        Try alternative search strategies
        """

        strategies = [
            # Strategy 1: Broader keywords
            {
                'name': 'Broader search',
                'keywords': original_keywords[:-1],  # Remove most specific
                'reason': 'Try less specific search'
            },

            # Strategy 2: Alternative spellings
            {
                'name': 'Alternative spelling',
                'keywords': get_alternative_spellings(material_name),
                'reason': 'Try different naming conventions'
            },

            # Strategy 3: Different region
            {
                'name': 'Global region',
                'keywords': original_keywords[:-1] + ['GLO'],
                'reason': 'Try global instead of regional'
            },

            # Strategy 4: Generic category
            {
                'name': 'Generic category',
                'keywords': get_material_category(material_name),
                'reason': 'Try generic material category'
            }
        ]

        for strategy in strategies:
            print(f"Trying strategy: {strategy['name']}")
            print(f"  Reason: {strategy['reason']}")
            print(f"  Keywords: {strategy['keywords']}")

            flows = client.search.find_flows(
                strategy['keywords'],
                max_results=5
            )

            if flows:
                print(f"  ✓ Found {len(flows)} matches")
                return {
                    'success': True,
                    'flows': flows,
                    'strategy_used': strategy['name'],
                    'substitution_note': f"Used {strategy['name']}: {flows[0].name}"
                }

        # All strategies failed
        return {
            'success': False,
            'error': f"Could not find {material_name} after {len(strategies)} strategies",
            'suggestion': "User should specify material more precisely or add to database"
        }
```

#### Category 2: Calculation Failures

```python
"""
Handle calculation errors
"""

class CalculationErrorHandler:
    """
    Recover from calculation failures
    """

    @staticmethod
    def handle_calculation_error(error_details, system_id, method_id):
        """
        Diagnose and recover from calculation errors
        """

        # Diagnostic checks
        checks = []

        # Check 1: System completeness
        system = client.client.get(o.ProductSystem, system_id)
        if not system:
            checks.append({
                'check': 'System exists',
                'status': 'FAIL',
                'action': 'Recreate product system'
            })
        else:
            checks.append({
                'check': 'System exists',
                'status': 'PASS'
            })

        # Check 2: Process linkages
        # (Would need to inspect system structure)

        # Check 3: Impact method validity
        method = client.client.get(o.ImpactMethod, method_id)
        if not method:
            checks.append({
                'check': 'Method exists',
                'status': 'FAIL',
                'action': 'Search for alternative method'
            })

        # Recovery actions
        if any(c['status'] == 'FAIL' for c in checks):
            print("Calculation diagnostics:")
            for check in checks:
                print(f"  {check['check']}: {check['status']}")
                if 'action' in check:
                    print(f"    → Action: {check['action']}")

            return {
                'can_recover': True,
                'recovery_actions': [c['action'] for c in checks if 'action' in c]
            }
        else:
            return {
                'can_recover': False,
                'reason': 'All diagnostic checks passed but calculation still fails',
                'suggestion': 'Check OpenLCA logs for detailed error'
            }
```

### 5.2 Retry Logic

```python
"""
Intelligent retry with exponential backoff
"""

import time
import random

class RetryHandler:
    """
    Retry failed operations with backoff
    """

    @staticmethod
    async def retry_with_backoff(
        operation,
        max_attempts=3,
        base_delay=1.0,
        max_delay=10.0,
        exponential=True
    ):
        """
        Retry operation with exponential backoff

        Args:
            operation: Async function to retry
            max_attempts: Maximum retry attempts
            base_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            exponential: Use exponential backoff
        """

        for attempt in range(1, max_attempts + 1):
            try:
                print(f"Attempt {attempt}/{max_attempts}")
                result = await operation()
                print(f"✓ Success on attempt {attempt}")
                return result

            except Exception as e:
                print(f"✗ Attempt {attempt} failed: {e}")

                if attempt < max_attempts:
                    # Calculate delay
                    if exponential:
                        delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    else:
                        delay = base_delay

                    # Add jitter to prevent thundering herd
                    delay += random.uniform(0, 0.5)

                    print(f"  Retrying in {delay:.1f} seconds...")
                    await asyncio.sleep(delay)
                else:
                    print(f"✗ All {max_attempts} attempts failed")
                    raise Exception(f"Operation failed after {max_attempts} attempts: {e}")

# Usage
result = await RetryHandler.retry_with_backoff(
    lambda: client.calculate.simple_calculation(system, method, 1.0),
    max_attempts=3,
    base_delay=2.0
)
```

### 5.3 Fallback Strategies

```python
"""
Fallback strategies for graceful degradation
"""

class FallbackStrategies:
    """
    Implement fallback options when primary approach fails
    """

    @staticmethod
    def get_impact_method_fallback(preferred_method_keywords):
        """
        Fallback chain for impact methods

        Preference order:
        1. User-specified method
        2. Regional default (e.g., TRACI for US, ReCiPe for Europe)
        3. Global standard (e.g., ILCD)
        4. Any available method
        """

        fallback_chain = [
            {
                'name': 'User preference',
                'keywords': preferred_method_keywords
            },
            {
                'name': 'TRACI 2.1',
                'keywords': ['TRACI', '2.1']
            },
            {
                'name': 'ReCiPe 2016',
                'keywords': ['ReCiPe', '2016', 'Midpoint']
            },
            {
                'name': 'ILCD 2011',
                'keywords': ['ILCD', '2011', 'Midpoint']
            },
            {
                'name': 'CML-IA',
                'keywords': ['CML']
            }
        ]

        for fallback in fallback_chain:
            print(f"Trying: {fallback['name']}")
            method = client.search.find_impact_method(fallback['keywords'])

            if method:
                if fallback['name'] != 'User preference':
                    print(f"  ⚠ Using fallback: {fallback['name']}")
                return {
                    'method': method,
                    'fallback_used': fallback['name'] != 'User preference',
                    'fallback_level': fallback_chain.index(fallback)
                }

        raise Exception("No impact method available in database")
```

---

## 6. Optimization Techniques

### 6.1 Caching Strategies

```python
"""
Cache frequently accessed data
"""

from functools import lru_cache
import hashlib

class LCACache:
    """
    Cache database searches and calculations
    """

    def __init__(self):
        self.flow_cache = {}
        self.process_cache = {}
        self.method_cache = {}

    def cache_key(self, *args):
        """Generate cache key from arguments"""
        key_str = str(args)
        return hashlib.md5(key_str.encode()).hexdigest()

    def search_flows_cached(self, keywords, max_results=10):
        """Cached flow search"""
        cache_key = self.cache_key('flows', tuple(keywords), max_results)

        if cache_key in self.flow_cache:
            print(f"  ⚡ Cache hit: {keywords}")
            return self.flow_cache[cache_key]

        print(f"  🔍 Cache miss: {keywords}")
        results = client.search.find_flows(keywords, max_results)
        self.flow_cache[cache_key] = results
        return results

    def find_providers_cached(self, flow_ref):
        """Cached provider search"""
        cache_key = self.cache_key('providers', flow_ref.id)

        if cache_key in self.process_cache:
            print(f"  ⚡ Cache hit: providers for {flow_ref.name}")
            return self.process_cache[cache_key]

        print(f"  🔍 Cache miss: providers for {flow_ref.name}")
        results = client.search.find_providers(flow_ref)
        self.process_cache[cache_key] = results
        return results

    def search_method_cached(self, keywords):
        """Cached method search"""
        cache_key = self.cache_key('method', tuple(keywords))

        if cache_key in self.method_cache:
            print(f"  ⚡ Cache hit: method {keywords}")
            return self.method_cache[cache_key]

        print(f"  🔍 Cache miss: method {keywords}")
        result = client.search.find_impact_method(keywords)
        self.method_cache[cache_key] = result
        return result

# Usage
cache = LCACache()
pet_flows = cache.search_flows_cached(['polyethylene', 'terephthalate'])
pet_providers = cache.find_providers_cached(pet_flows[0])
traci = cache.search_method_cached(['TRACI', '2.1'])
```

### 6.2 Batch Operations

```python
"""
Batch operations for efficiency
"""

class BatchOperations:
    """
    Execute multiple operations in batches
    """

    @staticmethod
    async def search_materials_batch(material_specs):
        """
        Search for multiple materials in one go

        Args:
            material_specs: List of dicts with 'name' and 'keywords'
        """

        results = {}

        # Execute all searches (can be parallelized)
        for spec in material_specs:
            name = spec['name']
            keywords = spec['keywords']

            flows = client.search.find_flows(keywords, max_results=3)

            if flows:
                providers = client.search.find_providers(flows[0])
                results[name] = {
                    'flow': flows[0],
                    'provider': providers[0] if providers else None,
                    'alternatives': flows[1:] if len(flows) > 1 else []
                }
            else:
                results[name] = {
                    'flow': None,
                    'provider': None,
                    'error': 'Not found'
                }

        # Summary
        found = sum(1 for r in results.values() if r['flow'] is not None)
        print(f"\nBatch search results: {found}/{len(material_specs)} found")

        return results

    @staticmethod
    async def create_processes_batch(process_specs):
        """
        Create multiple processes efficiently
        """

        created_processes = []

        for spec in process_specs:
            # Create flow
            flow = client.data.create_product_flow(
                spec['name'],
                spec['description']
            )

            # Create process
            process = client.data.create_process(
                spec['process_name'],
                spec['process_description'],
                spec['exchanges']
            )

            created_processes.append({
                'name': spec['name'],
                'flow_id': flow.id,
                'process_id': process.id
            })

        print(f"Created {len(created_processes)} processes in batch")

        return created_processes
```

### 6.3 Progressive Enhancement

```python
"""
Progressive enhancement: Quick results first, detailed later
"""

class ProgressiveAnalysis:
    """
    Get quick estimates, then refine
    """

    @staticmethod
    async def quick_assessment(product_spec, method_keywords):
        """
        Phase 1: Quick screening assessment
        - Use market averages
        - Single impact category (GWP)
        - Rough estimates
        """

        print("=== QUICK ASSESSMENT ===")

        # Use market processes (pre-aggregated)
        materials_quick = {}
        for mat_name, mat_keywords in product_spec['materials'].items():
            keywords_market = mat_keywords + ['market']
            flows = client.search.find_flows(keywords_market, max_results=1)
            if flows:
                materials_quick[mat_name] = flows[0]

        # Simple system
        # ... create simple system ...

        # Calculate only GWP
        method = client.search.find_impact_method(method_keywords)
        result = client.calculate.simple_calculation(system, method, 1.0)
        impacts = client.results.get_total_impacts(result)

        gwp = next(i for i in impacts if 'climate' in i['name'].lower())

        result.dispose()

        print(f"Quick GWP estimate: {gwp['amount']:.4f} {gwp['unit']}")

        return gwp['amount']

    @staticmethod
    async def detailed_assessment(product_spec, method_keywords):
        """
        Phase 2: Detailed assessment
        - Specific processes
        - All impact categories
        - Contribution analysis
        """

        print("=== DETAILED ASSESSMENT ===")

        # Use specific regional processes
        # ... full modeling ...

        # All impact categories
        result = client.calculate.simple_calculation(system, method, 1.0)
        impacts = client.results.get_total_impacts(result)

        # Contribution analysis
        contributions = {}
        for impact in impacts[:5]:  # Top 5
            contribs = client.results.get_process_contributions(result, impact['category'])
            contributions[impact['name']] = contribs

        result.dispose()

        return {
            'impacts': impacts,
            'contributions': contributions
        }

    @staticmethod
    async def progressive_workflow(product_spec, method_keywords):
        """
        Combined: Quick first, detailed second
        """

        # Phase 1: Quick estimate
        quick_gwp = await ProgressiveAnalysis.quick_assessment(
            product_spec,
            method_keywords
        )

        print(f"\n✓ Quick assessment complete: {quick_gwp:.4f} kg CO2 eq")
        print("Proceeding to detailed assessment...\n")

        # Phase 2: Detailed analysis
        detailed = await ProgressiveAnalysis.detailed_assessment(
            product_spec,
            method_keywords
        )

        detailed_gwp = next(
            i['amount'] for i in detailed['impacts']
            if 'climate' in i['name'].lower()
        )

        # Compare
        difference = abs(detailed_gwp - quick_gwp)
        difference_pct = (difference / quick_gwp) * 100

        print(f"\n=== COMPARISON ===")
        print(f"Quick estimate:    {quick_gwp:.4f} kg CO2 eq")
        print(f"Detailed result:   {detailed_gwp:.4f} kg CO2 eq")
        print(f"Difference:        {difference:.4f} ({difference_pct:.1f}%)")

        return detailed
```

---

## 7. Production Deployment

### 7.1 Monitoring and Logging

```python
"""
Production-ready logging and monitoring
"""

import logging
from datetime import datetime

class LCAWorkflowLogger:
    """
    Structured logging for LCA workflows
    """

    def __init__(self, workflow_id):
        self.workflow_id = workflow_id
        self.logger = logging.getLogger(f"LCA.{workflow_id}")
        self.start_time = datetime.now()

        # Configure logger
        handler = logging.FileHandler(f"lca_workflow_{workflow_id}.log")
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def log_phase_start(self, phase_number, phase_name):
        """Log phase start"""
        self.logger.info(f"=== PHASE {phase_number}: {phase_name} START ===")

    def log_phase_complete(self, phase_number, phase_name, duration_seconds):
        """Log phase completion"""
        self.logger.info(
            f"=== PHASE {phase_number}: {phase_name} COMPLETE "
            f"({duration_seconds:.2f}s) ==="
        )

    def log_tool_call(self, tool_name, arguments):
        """Log MCP tool call"""
        self.logger.debug(f"Tool call: {tool_name}({arguments})")

    def log_tool_response(self, tool_name, success, duration_ms):
        """Log tool response"""
        status = "SUCCESS" if success else "FAILED"
        self.logger.info(f"Tool {tool_name}: {status} ({duration_ms:.0f}ms)")

    def log_material_search(self, material_name, found, flow_id=None):
        """Log material search result"""
        if found:
            self.logger.info(f"Material found: {material_name} → {flow_id}")
        else:
            self.logger.warning(f"Material not found: {material_name}")

    def log_calculation(self, system_id, method_id, num_impacts, duration_s):
        """Log impact calculation"""
        self.logger.info(
            f"Calculation: system={system_id}, method={method_id}, "
            f"impacts={num_impacts}, duration={duration_s:.2f}s"
        )

    def log_error(self, phase, error_msg, exception=None):
        """Log error"""
        self.logger.error(f"Phase {phase} error: {error_msg}")
        if exception:
            self.logger.exception(exception)

    def log_warning(self, phase, warning_msg):
        """Log warning"""
        self.logger.warning(f"Phase {phase} warning: {warning_msg}")

    def log_workflow_complete(self, status, total_duration_s):
        """Log workflow completion"""
        self.logger.info(
            f"=== WORKFLOW COMPLETE: {status} "
            f"(total: {total_duration_s:.2f}s) ==="
        )
```

### 7.2 Health Checks

```python
"""
Health monitoring for production systems
"""

class HealthMonitor:
    """
    Monitor system health
    """

    @staticmethod
    async def check_openlca_connection():
        """Check OpenLCA availability"""
        try:
            is_connected = client.test_connection()
            return {
                'component': 'OpenLCA IPC',
                'status': 'UP' if is_connected else 'DOWN',
                'response_time_ms': 0  # Would measure actual time
            }
        except Exception as e:
            return {
                'component': 'OpenLCA IPC',
                'status': 'DOWN',
                'error': str(e)
            }

    @staticmethod
    async def check_database_access():
        """Check database accessibility"""
        try:
            flows = client.search.find_flows(['steel'], max_results=1)
            return {
                'component': 'Database Access',
                'status': 'UP' if flows else 'DEGRADED',
                'details': f"Test search returned {len(flows)} results"
            }
        except Exception as e:
            return {
                'component': 'Database Access',
                'status': 'DOWN',
                'error': str(e)
            }

    @staticmethod
    async def check_mcp_server():
        """Check MCP server status"""
        try:
            # Would ping MCP server health endpoint
            return {
                'component': 'MCP Server',
                'status': 'UP'
            }
        except Exception as e:
            return {
                'component': 'MCP Server',
                'status': 'DOWN',
                'error': str(e)
            }

    @staticmethod
    async def full_health_check():
        """Complete system health check"""
        checks = await asyncio.gather(
            HealthMonitor.check_openlca_connection(),
            HealthMonitor.check_database_access(),
            HealthMonitor.check_mcp_server()
        )

        all_up = all(c['status'] == 'UP' for c in checks)

        return {
            'overall_status': 'HEALTHY' if all_up else 'UNHEALTHY',
            'timestamp': datetime.now().isoformat(),
            'checks': checks
        }
```

### 7.3 Performance Metrics

```python
"""
Track and report performance metrics
"""

class PerformanceTracker:
    """
    Track workflow performance
    """

    def __init__(self):
        self.metrics = {
            'workflows_total': 0,
            'workflows_successful': 0,
            'workflows_failed': 0,
            'phase_durations': {1: [], 2: [], 3: [], 4: []},
            'tool_calls': {},
            'errors_by_type': {}
        }

    def record_workflow_start(self):
        """Record workflow start"""
        self.metrics['workflows_total'] += 1

    def record_workflow_complete(self, success):
        """Record workflow completion"""
        if success:
            self.metrics['workflows_successful'] += 1
        else:
            self.metrics['workflows_failed'] += 1

    def record_phase_duration(self, phase_number, duration_seconds):
        """Record phase duration"""
        self.metrics['phase_durations'][phase_number].append(duration_seconds)

    def record_tool_call(self, tool_name, duration_ms, success):
        """Record tool call"""
        if tool_name not in self.metrics['tool_calls']:
            self.metrics['tool_calls'][tool_name] = {
                'count': 0,
                'successes': 0,
                'failures': 0,
                'durations_ms': []
            }

        self.metrics['tool_calls'][tool_name]['count'] += 1
        if success:
            self.metrics['tool_calls'][tool_name]['successes'] += 1
        else:
            self.metrics['tool_calls'][tool_name]['failures'] += 1
        self.metrics['tool_calls'][tool_name]['durations_ms'].append(duration_ms)

    def record_error(self, error_type):
        """Record error occurrence"""
        if error_type not in self.metrics['errors_by_type']:
            self.metrics['errors_by_type'][error_type] = 0
        self.metrics['errors_by_type'][error_type] += 1

    def get_summary(self):
        """Get performance summary"""
        import statistics

        summary = {
            'workflows': {
                'total': self.metrics['workflows_total'],
                'successful': self.metrics['workflows_successful'],
                'failed': self.metrics['workflows_failed'],
                'success_rate_pct': (
                    self.metrics['workflows_successful'] /
                    self.metrics['workflows_total'] * 100
                    if self.metrics['workflows_total'] > 0 else 0
                )
            },
            'phase_performance': {}
        }

        for phase, durations in self.metrics['phase_durations'].items():
            if durations:
                summary['phase_performance'][f'phase_{phase}'] = {
                    'mean_seconds': statistics.mean(durations),
                    'median_seconds': statistics.median(durations),
                    'min_seconds': min(durations),
                    'max_seconds': max(durations)
                }

        summary['tool_performance'] = {}
        for tool, data in self.metrics['tool_calls'].items():
            if data['durations_ms']:
                summary['tool_performance'][tool] = {
                    'calls': data['count'],
                    'success_rate_pct': data['successes'] / data['count'] * 100,
                    'mean_duration_ms': statistics.mean(data['durations_ms'])
                }

        summary['errors'] = self.metrics['errors_by_type']

        return summary
```

---

## Conclusion

Multi-agent prompt engineering for LCA automation requires careful consideration of:

1. **Architecture**: Choose the right pattern (sequential, parallel, or hybrid)
2. **Role Design**: Clear agent responsibilities aligned with LCA phases
3. **Prompt Engineering**: Structured, example-based, resilient prompts
4. **Communication**: Well-defined protocols and state management
5. **Error Handling**: Recovery strategies and fallbacks
6. **Optimization**: Caching, batching, progressive enhancement
7. **Production**: Monitoring, health checks, performance tracking

**Key Principles:**
- ✅ Specialize agents by LCA phase or domain
- ✅ Use structured message passing
- ✅ Implement comprehensive error recovery
- ✅ Cache frequently accessed data
- ✅ Monitor and log everything
- ✅ Design for graceful degradation

For implementation examples, see:
- [Context Engineering Guide](CONTEXT_ENGINEERING.md)
- [Test Examples](CLIENT_TEST_EXAMPLES.md)
- [Case Studies](CASE_STUDY_PET_PC.md)

---

**Last Updated:** 2025-12-04
**Version:** 1.0
**Status:** Production Ready
