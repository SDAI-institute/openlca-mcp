# Complete Systems Analysis Guide for LCA Automation

## Overview

This guide provides comprehensive methodology for complete systems analysis using the OpenLCA MCP Server and AI agents. It covers the full spectrum from simple product assessments to complex supply chain analyses using the ecoinvent database.

## Table of Contents

1. [Systems Analysis Framework](#1-systems-analysis-framework)
2. [Database Navigation](#2-database-navigation)
3. [System Construction Strategies](#3-system-construction-strategies)
4. [Analysis Techniques](#4-analysis-techniques)
5. [Practical Workflows](#5-practical-workflows)
6. [Advanced Topics](#6-advanced-topics)

---

## 1. Systems Analysis Framework

### 1.1 LCA Phases and System Thinking

**ISO 14040/14044 Four-Phase Framework:**

```
┌─────────────────────────────────────────────────────────┐
│                     LCA FRAMEWORK                        │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │   Phase 1: Goal and Scope Definition             │  │
│  │   • Define system boundaries                      │  │
│  │   • Select functional unit                        │  │
│  │   • Choose impact method                          │  │
│  └──────────────┬───────────────────────────────────┘  │
│                 │                                        │
│  ┌──────────────▼───────────────────────────────────┐  │
│  │   Phase 2: Life Cycle Inventory (LCI)           │  │
│  │   • Data collection                              │  │
│  │   • System modeling                              │  │
│  │   • Process linking                              │  │
│  └──────────────┬───────────────────────────────────┘  │
│                 │                                        │
│  ┌──────────────▼───────────────────────────────────┐  │
│  │   Phase 3: Life Cycle Impact Assessment (LCIA)  │  │
│  │   • Impact calculation                           │  │
│  │   • Characterization                             │  │
│  │   • Normalization (optional)                     │  │
│  └──────────────┬───────────────────────────────────┘  │
│                 │                                        │
│  ┌──────────────▼───────────────────────────────────┐  │
│  │   Phase 4: Interpretation                        │  │
│  │   • Contribution analysis                        │  │
│  │   • Sensitivity analysis                         │  │
│  │   • Conclusions and recommendations              │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│        ↑                                        ↓         │
│   Iterations and Refinements                             │
└─────────────────────────────────────────────────────────┘
```

### 1.2 System Boundaries

**Three Common Boundary Types:**

1. **Cradle-to-Gate**
   ```
   [Raw Material Extraction] → [Processing] → [Manufacturing] → [Factory Gate]
   ```
   - Use for: Material comparisons, B2B products
   - Excludes: Distribution, use, end-of-life

2. **Cradle-to-Grave**
   ```
   [Raw Materials] → [Production] → [Distribution] → [Use] → [End-of-Life]
   ```
   - Use for: Complete product assessments
   - Includes: Full life cycle

3. **Gate-to-Gate**
   ```
                    [Factory Input] → [Manufacturing] → [Factory Output]
   ```
   - Use for: Process improvement, single-facility
   - Excludes: Upstream and downstream

### 1.3 Functional Unit Selection

**Functional Unit = Quantified Performance of Product System**

**Examples:**

| Product | Poor FU | Better FU | Best FU |
|---------|---------|-----------|---------|
| Bottle | 1 bottle | 1 bottle of water | 1L water delivered, ensuring food safety |
| Cup | 1 cup | 1 cup for coffee | 1 serving of 250ml hot beverage |
| Paint | 1 kg paint | 1 m² painted | 1 m² protected for 10 years |
| Light bulb | 1 bulb | 1000 hours lighting | 1000 lumen-hours of illumination |
| Transport | 1 trip | 1 km traveled | 1 ton×km of freight transported |

**Functional Unit Checklist:**
- ☐ Measurable quantity
- ☐ Performance level specified
- ☐ Quality requirements stated
- ☐ Duration/lifetime included
- ☐ Enables fair comparison between alternatives

---

## 2. Database Navigation

### 2.1 Understanding ecoinvent Database

**ecoinvent Structure:**

```
ecoinvent Database
├── Flows (Materials and Energy)
│   ├── Products (51,000+)
│   ├── Elementary flows (4,500+)
│   └── Waste flows
├── Processes (19,000+)
│   ├── Unit processes
│   ├── System processes
│   └── Market processes
├── Impact Methods
│   ├── TRACI
│   ├── ReCiPe
│   ├── ILCD
│   └── EF 3.0
└── Flow Properties & Units
```

### 2.2 Search Strategies

#### Strategy 1: Material-Based Search

```python
"""
Find materials by composition and form
"""

from openlca_ipc import OLCAClient

client = OLCAClient(port=8080)

# Hierarchical search: Broad → Specific
def find_material_hierarchical(material_name):
    """
    Search with increasing specificity
    """

    # Level 1: Broad material type
    print(f"\n=== Searching for: {material_name} ===")

    level1 = client.search.find_flows([material_name], max_results=20)
    print(f"Level 1 (broad): {len(level1)} results")

    # Level 2: Add form factor
    level2 = client.search.find_flows(
        [material_name, 'granulate'],
        max_results=10
    )
    print(f"Level 2 (+ form): {len(level2)} results")

    # Level 3: Add grade/quality
    level3 = client.search.find_flows(
        [material_name, 'granulate', 'bottle'],
        max_results=5
    )
    print(f"Level 3 (+ grade): {len(level3)} results")

    # Level 4: Add region
    level4 = client.search.find_flows(
        [material_name, 'granulate', 'bottle', 'RER'],
        max_results=3
    )
    print(f"Level 4 (+ region): {len(level4)} results")

    return level4[0] if level4 else None

# Example usage
pet = find_material_hierarchical('polyethylene terephthalate')
```

**Output:**
```
=== Searching for: polyethylene terephthalate ===
Level 1 (broad): 18 results
Level 2 (+ form): 8 results
Level 3 (+ grade): 3 results
Level 4 (+ region): 1 results
```

#### Strategy 2: Process-Based Search

```python
"""
Find processes by activity and geography
"""

def find_process_by_activity(product_name, activity, geography=None):
    """
    Search for processes producing specific products
    Example: Steel production in Europe
    """

    # Build keyword list
    keywords = [product_name, activity]
    if geography:
        keywords.append(geography)

    # Search flows first
    flows = client.search.find_flows(keywords, max_results=5)

    if not flows:
        print(f"No flows found for: {keywords}")
        return None

    print(f"Found {len(flows)} flows matching: {keywords}")

    # Find providers for best flow match
    flow = flows[0]
    providers = client.search.find_providers(flow)

    print(f"\nProviders for '{flow.name}':")
    for i, provider in enumerate(providers[:5], 1):
        print(f"  {i}. {provider.name}")

    return providers[0] if providers else None

# Examples
steel_rer = find_process_by_activity('steel', 'production', 'RER')
steel_glo = find_process_by_activity('steel', 'production', 'GLO')
```

#### Strategy 3: Market Process vs Unit Process

```python
"""
Understanding the difference between market and unit processes
"""

def compare_market_vs_unit(product_keywords):
    """
    Compare market process (aggregated) vs unit process (specific)
    """

    # Search for market process
    market_kw = product_keywords + ['market']
    market_procs = client.search.find_processes(market_kw, max_results=5)

    # Search for unit processes
    unit_kw = product_keywords + ['production']
    unit_procs = client.search.find_processes(unit_kw, max_results=10)

    print(f"\nMarket processes ({len(market_procs)}):")
    for proc in market_procs[:3]:
        print(f"  • {proc.name}")

    print(f"\nUnit processes ({len(unit_procs)}):")
    for proc in unit_procs[:5]:
        print(f"  • {proc.name}")

    print("\nKey Differences:")
    print("  Market = Average of all suppliers + transport")
    print("  Unit = Specific technology/location")

    return market_procs[0] if market_procs else unit_procs[0]

# Example
steel_proc = compare_market_vs_unit(['steel', 'hot', 'rolled'])
```

### 2.3 Database Exploration Tools

```python
"""
Tools for exploring database structure
"""

def explore_database():
    """
    Get overview of database contents
    """

    print("="*70)
    print("DATABASE EXPLORATION")
    print("="*70)

    # Count entities
    flows = list(client.client.get_descriptors(o.Flow))
    processes = list(client.client.get_descriptors(o.Process))
    methods = list(client.client.get_descriptors(o.ImpactMethod))

    print(f"\nDatabase Statistics:")
    print(f"  Flows: {len(flows):,}")
    print(f"  Processes: {len(processes):,}")
    print(f"  Impact Methods: {len(methods):,}")

    # Sample categories
    print(f"\nFlow Categories (sample):")
    categories = set()
    for flow in flows[:1000]:
        if hasattr(flow, 'category') and flow.category:
            categories.add(flow.category)

    for cat in sorted(list(categories))[:10]:
        print(f"  • {cat}")

    # Impact methods
    print(f"\nImpact Methods Available:")
    for method in methods[:10]:
        print(f"  • {method.name}")

explore_database()
```

---

## 3. System Construction Strategies

### 3.1 Top-Down Construction

**Approach:** Start with final product, work backward to raw materials

```python
"""
Top-down system construction
Example: Smartphone LCA
"""

def construct_system_topdown(product_name):
    """
    Build product system from finished product backwards
    """

    print(f"\n=== TOP-DOWN CONSTRUCTION: {product_name} ===")

    # Step 1: Define finished product
    print("\nStep 1: Define finished product")
    finished_product = client.data.create_product_flow(
        f"{product_name}",
        f"Final assembled {product_name}"
    )

    # Step 2: Identify major subassemblies
    print("\nStep 2: Identify subassemblies")
    subassemblies = {
        'screen': ['lcd', 'display'],
        'battery': ['lithium', 'battery'],
        'circuit_board': ['printed', 'wiring', 'board'],
        'housing': ['polycarbonate', 'housing']
    }

    components = {}
    for name, keywords in subassemblies.items():
        flows = client.search.find_flows(keywords, max_results=1)
        if flows:
            components[name] = flows[0]
            print(f"  ✓ {name}: {flows[0].name}")

    # Step 3: Create assembly process
    print("\nStep 3: Create assembly process")
    exchanges = [
        client.data.create_exchange(
            o.Ref(id=finished_product.id),
            amount=1.0,
            is_input=False,
            is_quantitative_reference=True
        )
    ]

    # Add component inputs (example weights)
    component_weights = {
        'screen': 0.050,  # 50g
        'battery': 0.040,  # 40g
        'circuit_board': 0.030,  # 30g
        'housing': 0.080   # 80g
    }

    for comp_name, weight in component_weights.items():
        if comp_name in components:
            exchanges.append(
                client.data.create_exchange(
                    components[comp_name],
                    amount=weight,
                    is_input=True
                )
            )

    assembly_process = client.data.create_process(
        f"{product_name} Assembly",
        "Final assembly of all components",
        exchanges
    )

    # Step 4: Create product system
    print("\nStep 4: Create product system")
    system = client.systems.create_product_system(
        o.Ref(id=assembly_process.id)
    )

    print(f"\n✓ System created: {system.name}")
    return system

# Example
smartphone_system = construct_system_topdown("Smartphone")
```

### 3.2 Bottom-Up Construction

**Approach:** Start with raw materials, build up to final product

```python
"""
Bottom-up system construction
Example: Plastic bottle from petrochemicals
"""

def construct_system_bottomup(final_product_name, material_chain):
    """
    Build product system from raw materials upward
    """

    print(f"\n=== BOTTOM-UP CONSTRUCTION: {final_product_name} ===")

    # Step 1: Identify raw materials
    print("\nStep 1: Identify raw materials")

    materials = {}
    for material_name, keywords in material_chain.items():
        flows = client.search.find_flows(keywords, max_results=1)
        if flows:
            materials[material_name] = flows[0]
            providers = client.search.find_providers(flows[0])
            materials[f"{material_name}_provider"] = providers[0] if providers else None
            print(f"  ✓ {material_name}: {flows[0].name}")

    # Step 2: Create intermediate products
    print("\nStep 2: Create intermediate products")

    # Polymer granulate (intermediate)
    granulate = client.data.create_product_flow(
        f"{final_product_name} - Granulate",
        "Polymer granulate ready for molding"
    )

    # Step 3: Create transformation processes
    print("\nStep 3: Create processes")

    # Process 1: Polymerization
    poly_exchanges = [
        client.data.create_exchange(
            o.Ref(id=granulate.id),
            amount=1.0,
            is_input=False,
            is_quantitative_reference=True
        ),
        client.data.create_exchange(
            materials['monomer'],
            amount=1.02,  # 2% loss in polymerization
            is_input=True,
            provider=materials['monomer_provider']
        )
    ]

    poly_process = client.data.create_process(
        "Polymerization",
        "Convert monomer to polymer granulate",
        poly_exchanges
    )

    # Process 2: Molding
    final_product = client.data.create_product_flow(
        final_product_name,
        "Final molded product"
    )

    mold_exchanges = [
        client.data.create_exchange(
            o.Ref(id=final_product.id),
            amount=1.0,
            is_input=False,
            is_quantitative_reference=True
        ),
        client.data.create_exchange(
            o.Ref(id=granulate.id),
            amount=0.025,  # 25g
            is_input=True,
            provider=o.Ref(id=poly_process.id)
        )
    ]

    mold_process = client.data.create_process(
        "Injection Molding",
        "Mold granulate into bottle",
        mold_exchanges
    )

    # Step 4: Create system
    print("\nStep 4: Create product system")
    system = client.systems.create_product_system(
        o.Ref(id=mold_process.id)
    )

    print(f"\n✓ System created: {system.name}")
    return system

# Example
bottle_chain = {
    'crude_oil': ['crude', 'oil'],
    'ethylene': ['ethylene'],
    'monomer': ['polyethylene', 'terephthalate', 'resin']
}

bottle_system = construct_system_bottomup(
    "PET Bottle",
    bottle_chain
)
```

### 3.3 Hybrid Construction

**Approach:** Combine database processes with custom processes

```python
"""
Hybrid system construction
Example: Custom product with standard materials
"""

def construct_system_hybrid(product_spec):
    """
    Mix database processes with custom modeling
    """

    print(f"\n=== HYBRID CONSTRUCTION: {product_spec['name']} ===")

    # Part 1: Use database processes for standard materials
    print("\nPart 1: Link to database materials")

    db_materials = {}
    for mat_name, mat_keywords in product_spec['database_materials'].items():
        flows = client.search.find_flows(mat_keywords, max_results=1)
        if flows:
            providers = client.search.find_providers(flows[0])
            db_materials[mat_name] = {
                'flow': flows[0],
                'provider': providers[0] if providers else None,
                'amount': product_spec['amounts'][mat_name]
            }
            print(f"  ✓ {mat_name}: {flows[0].name}")

    # Part 2: Create custom processes for unique steps
    print("\nPart 2: Create custom processes")

    # Custom process: Special assembly
    custom_product = client.data.create_product_flow(
        product_spec['name'],
        product_spec['description']
    )

    exchanges = [
        # Output
        client.data.create_exchange(
            o.Ref(id=custom_product.id),
            amount=1.0,
            is_input=False,
            is_quantitative_reference=True
        )
    ]

    # Add database material inputs
    for mat_name, mat_data in db_materials.items():
        exchanges.append(
            client.data.create_exchange(
                mat_data['flow'],
                amount=mat_data['amount'],
                is_input=True,
                provider=mat_data['provider']
            )
        )

    # Add custom energy inputs
    if 'custom_energy' in product_spec:
        energy_flows = client.search.find_flows(
            ['electricity', 'medium', 'voltage'],
            max_results=1
        )
        if energy_flows:
            exchanges.append(
                client.data.create_exchange(
                    energy_flows[0],
                    amount=product_spec['custom_energy'],
                    is_input=True
                )
            )

    custom_process = client.data.create_process(
        f"{product_spec['name']} Production",
        "Custom production process with database linkages",
        exchanges
    )

    # Create system
    system = client.systems.create_product_system(
        o.Ref(id=custom_process.id)
    )

    print(f"\n✓ Hybrid system created: {system.name}")
    return system

# Example: Custom electronics device
device_spec = {
    'name': 'Custom IoT Sensor',
    'description': 'Battery-powered environmental sensor',
    'database_materials': {
        'aluminum_housing': ['aluminum', 'sheet'],
        'circuit_board': ['printed', 'wiring', 'board'],
        'battery': ['lithium', 'ion', 'battery']
    },
    'amounts': {
        'aluminum_housing': 0.050,  # 50g
        'circuit_board': 0.015,     # 15g
        'battery': 0.025            # 25g
    },
    'custom_energy': 2.5  # kWh for assembly
}

sensor_system = construct_system_hybrid(device_spec)
```

---

## 4. Analysis Techniques

### 4.1 Contribution Analysis

```python
"""
Identify hotspots in product system
"""

def perform_contribution_analysis(system, method, threshold=0.01):
    """
    Analyze which processes/flows contribute most to impacts

    Args:
        system: Product system reference
        method: Impact method
        threshold: Minimum contribution share to report (default 1%)
    """

    print(f"\n=== CONTRIBUTION ANALYSIS ===")

    # Calculate impacts
    result = client.calculate.simple_calculation(
        system_ref=system,
        method=method,
        amount=1.0
    )

    # Get total impacts
    total_impacts = client.results.get_total_impacts(result)

    # Analyze each impact category
    for impact in total_impacts[:5]:  # Top 5 categories
        print(f"\n{impact['name']} ({impact['unit']}):")
        print(f"  Total: {impact['amount']:.6e}")

        # Get process contributions
        contributions = client.results.get_process_contributions(
            result,
            impact['category']
        )

        print(f"\n  Top Contributors (>{threshold*100}%):")
        for contrib in contributions:
            if contrib['share'] >= threshold:
                print(f"    {contrib['share']*100:5.1f}% - {contrib['process']}")

    # Clean up
    result.dispose()

    return total_impacts

# Example usage
pet_system = # ... created system
traci = client.search.find_impact_method(['TRACI'])
contributions = perform_contribution_analysis(pet_system, traci, threshold=0.05)
```

### 4.2 Comparative Analysis

```python
"""
Compare multiple product alternatives
"""

def compare_alternatives(systems_dict, method, reference_name=None):
    """
    Compare environmental impacts of multiple alternatives

    Args:
        systems_dict: Dict of {name: system_ref}
        method: Impact method
        reference_name: Name of reference alternative for normalization
    """

    print(f"\n=== COMPARATIVE ANALYSIS ===")
    print(f"Comparing {len(systems_dict)} alternatives")

    # Calculate impacts for all alternatives
    results = {}
    impacts_all = {}

    for name, system in systems_dict.items():
        result = client.calculate.simple_calculation(
            system_ref=system,
            method=method,
            amount=1.0
        )
        impacts = client.results.get_total_impacts(result)

        results[name] = result
        impacts_all[name] = impacts
        print(f"  ✓ {name}")

    # Extract reference values
    if reference_name:
        ref_impacts = impacts_all[reference_name]
    else:
        # Use first alternative as reference
        reference_name = list(impacts_all.keys())[0]
        ref_impacts = impacts_all[reference_name]

    # Create comparison table
    print(f"\n{'Category':<25} | ", end='')
    for name in systems_dict.keys():
        print(f"{name:<15} | ", end='')
    print("Best")
    print("-" * 100)

    # Compare each impact category
    for i, ref_impact in enumerate(ref_impacts):
        cat_name = ref_impact['name'][:24]
        unit = ref_impact['unit']

        print(f"{cat_name:<25} | ", end='')

        # Get values for all alternatives
        values = {}
        for name in systems_dict.keys():
            alt_impacts = impacts_all[name]
            alt_value = alt_impacts[i]['amount']
            values[name] = alt_value

            # Print value
            if alt_value != 0:
                pct_diff = ((alt_value - ref_impacts[i]['amount']) / ref_impacts[i]['amount']) * 100
                print(f"{alt_value:9.3e} ({pct_diff:+.0f}%) | ", end='')
            else:
                print(f"{alt_value:9.3e}        | ", end='')

        # Identify best
        best = min(values, key=lambda k: abs(values[k]))
        print(f"{best}")

    # Clean up
    for result in results.values():
        result.dispose()

    return impacts_all

# Example usage
alternatives = {
    'PET Bottle': pet_system,
    'PC Bottle': pc_system,
    'Glass Bottle': glass_system,
    'Aluminum Can': alu_system
}

comparison = compare_alternatives(alternatives, traci, reference_name='PET Bottle')
```

### 4.3 Sensitivity Analysis

```python
"""
Test robustness of results to parameter changes
"""

def sensitivity_analysis(base_system, method, parameters, variations):
    """
    Perform sensitivity analysis on key parameters

    Args:
        base_system: Base case product system
        method: Impact method
        parameters: Dict of {param_name: base_value}
        variations: List of multipliers to test (e.g., [0.5, 0.75, 1.0, 1.25, 1.5])
    """

    print(f"\n=== SENSITIVITY ANALYSIS ===")

    # Calculate base case
    base_result = client.calculate.simple_calculation(
        system_ref=base_system,
        method=method,
        amount=1.0
    )
    base_impacts = client.results.get_total_impacts(base_result)
    base_gwp = next(i['amount'] for i in base_impacts if 'climate' in i['name'].lower())

    print(f"Base case GWP: {base_gwp:.6f} kg CO2 eq")

    # Test each parameter
    results_matrix = {}

    for param_name, base_value in parameters.items():
        print(f"\nTesting parameter: {param_name} (base: {base_value})")

        param_results = []

        for multiplier in variations:
            test_value = base_value * multiplier

            # Recalculate with modified parameter
            # (Simplified - in reality, would need to modify process exchanges)

            # Estimate impact change (linear assumption for demonstration)
            estimated_gwp = base_gwp * (1 + (multiplier - 1) * 0.3)  # 30% influence

            param_results.append({
                'multiplier': multiplier,
                'value': test_value,
                'gwp': estimated_gwp,
                'change_pct': ((estimated_gwp - base_gwp) / base_gwp) * 100
            })

            print(f"  {multiplier:4.1f}x ({test_value:6.2f}): "
                  f"{estimated_gwp:.6f} kg CO2 eq ({param_results[-1]['change_pct']:+.1f}%)")

        results_matrix[param_name] = param_results

    # Identify most sensitive parameters
    print(f"\nParameter Sensitivity Ranking:")
    sensitivities = {}
    for param_name, results in results_matrix.items():
        # Calculate total variation range
        gwp_values = [r['gwp'] for r in results]
        variation = (max(gwp_values) - min(gwp_values)) / base_gwp
        sensitivities[param_name] = variation

    for i, (param, sens) in enumerate(sorted(sensitivities.items(), key=lambda x: x[1], reverse=True), 1):
        print(f"  {i}. {param}: {sens*100:.1f}% total variation")

    # Clean up
    base_result.dispose()

    return results_matrix

# Example usage
parameters = {
    'transport_distance_km': 500,
    'electricity_kwh': 10.5,
    'material_weight_kg': 2.5,
    'recycled_content_pct': 0.30
}

variations = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]

sensitivity_results = sensitivity_analysis(
    pet_system,
    traci,
    parameters,
    variations
)
```

### 4.4 Uncertainty Analysis

```python
"""
Monte Carlo simulation for uncertainty quantification
"""

def uncertainty_analysis(system, method, iterations=1000):
    """
    Perform Monte Carlo uncertainty analysis

    Args:
        system: Product system
        method: Impact method
        iterations: Number of Monte Carlo iterations
    """

    print(f"\n=== UNCERTAINTY ANALYSIS ===")
    print(f"Running Monte Carlo simulation ({iterations} iterations)...")

    # Run Monte Carlo simulation
    mc_result = client.calculate.monte_carlo(
        system_ref=system,
        method=method,
        iterations=iterations
    )

    # Get impact category (e.g., Climate Change)
    gwp_category = next(c for c in method.impact_categories if 'climate' in c.name.lower())

    # Extract results distribution
    gwp_values = mc_result.get_impact_values(gwp_category)

    # Calculate statistics
    import statistics
    import numpy as np

    mean = statistics.mean(gwp_values)
    median = statistics.median(gwp_values)
    stdev = statistics.stdev(gwp_values)
    cv = (stdev / mean) * 100  # Coefficient of variation

    percentiles = {
        '5th': np.percentile(gwp_values, 5),
        '25th': np.percentile(gwp_values, 25),
        '75th': np.percentile(gwp_values, 75),
        '95th': np.percentile(gwp_values, 95)
    }

    # Report results
    print(f"\nClimate Change Impact Distribution:")
    print(f"  Mean:   {mean:.6f} kg CO2 eq")
    print(f"  Median: {median:.6f} kg CO2 eq")
    print(f"  Std Dev: {stdev:.6f} ({cv:.1f}% CV)")
    print(f"\n  Percentiles:")
    print(f"    5th:  {percentiles['5th']:.6f}")
    print(f"    25th: {percentiles['25th']:.6f}")
    print(f"    75th: {percentiles['75th']:.6f}")
    print(f"    95th: {percentiles['95th']:.6f}")
    print(f"\n  90% Confidence Interval: [{percentiles['5th']:.6f}, {percentiles['95th']:.6f}]")

    # Visualize distribution
    import matplotlib.pyplot as plt

    plt.figure(figsize=(10, 6))
    plt.hist(gwp_values, bins=50, density=True, alpha=0.7, color='blue', edgecolor='black')
    plt.axvline(mean, color='red', linestyle='--', linewidth=2, label=f'Mean: {mean:.4f}')
    plt.axvline(median, color='green', linestyle='--', linewidth=2, label=f'Median: {median:.4f}')
    plt.axvline(percentiles['5th'], color='orange', linestyle=':', linewidth=1.5, label='5th/95th percentile')
    plt.axvline(percentiles['95th'], color='orange', linestyle=':', linewidth=1.5)

    plt.xlabel('Climate Change Impact (kg CO2 eq)', fontsize=12)
    plt.ylabel('Probability Density', fontsize=12)
    plt.title(f'Monte Carlo Uncertainty Analysis ({iterations} iterations)', fontsize=14, fontweight='bold')
    plt.legend(fontsize=10)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('uncertainty_analysis.png', dpi=300)

    print(f"\n✓ Visualization saved: uncertainty_analysis.png")

    return {
        'mean': mean,
        'median': median,
        'stdev': stdev,
        'cv': cv,
        'percentiles': percentiles,
        'raw_values': gwp_values
    }

# Example usage
uncertainty = uncertainty_analysis(pet_system, traci, iterations=1000)
```

---

## 5. Practical Workflows

### 5.1 Complete Workflow: Product Comparison

```python
"""
Complete workflow for comparing product alternatives
"""

def complete_product_comparison_workflow(alternatives_spec, method_keywords):
    """
    End-to-end workflow for product comparison LCA

    Args:
        alternatives_spec: Dict of alternative specifications
        method_keywords: Keywords to find impact method
    """

    print("="*70)
    print("COMPLETE PRODUCT COMPARISON WORKFLOW")
    print("="*70)

    # PHASE 1: GOAL & SCOPE
    print("\n### PHASE 1: GOAL AND SCOPE DEFINITION ###")

    print(f"\nGoal: Compare environmental impacts of {len(alternatives_spec)} alternatives")
    print(f"Alternatives: {', '.join(alternatives_spec.keys())}")
    print(f"Impact Method: {' '.join(method_keywords)}")

    # Find impact method
    method = client.search.find_impact_method(method_keywords)
    if not method:
        print(f"✗ Impact method not found: {method_keywords}")
        return None

    print(f"✓ Method: {method.name}")

    # PHASE 2: LIFE CYCLE INVENTORY
    print("\n### PHASE 2: LIFE CYCLE INVENTORY ###")

    systems = {}
    for alt_name, alt_spec in alternatives_spec.items():
        print(f"\nBuilding system: {alt_name}")

        # Search for materials
        materials = {}
        for mat_name, mat_keywords in alt_spec['materials'].items():
            flows = client.search.find_flows(mat_keywords, max_results=1)
            if flows:
                providers = client.search.find_providers(flows[0])
                materials[mat_name] = {
                    'flow': flows[0],
                    'provider': providers[0] if providers else None
                }
                print(f"  ✓ {mat_name}")

        # Create product flow
        product = client.data.create_product_flow(
            alt_name,
            alt_spec['description']
        )

        # Create exchanges
        exchanges = [
            client.data.create_exchange(
                o.Ref(id=product.id),
                amount=1.0,
                is_input=False,
                is_quantitative_reference=True
            )
        ]

        for mat_name, amount in alt_spec['amounts'].items():
            if mat_name in materials:
                exchanges.append(
                    client.data.create_exchange(
                        materials[mat_name]['flow'],
                        amount=amount,
                        is_input=True,
                        provider=materials[mat_name]['provider']
                    )
                )

        # Create process
        process = client.data.create_process(
            f"{alt_name} Production",
            f"Production of {alt_name}",
            exchanges
        )

        # Create system
        system = client.systems.create_product_system(o.Ref(id=process.id))
        systems[alt_name] = system
        print(f"  ✓ System created: {system.name}")

    # PHASE 3: IMPACT ASSESSMENT
    print("\n### PHASE 3: LIFE CYCLE IMPACT ASSESSMENT ###")

    impacts_all = {}
    results = {}

    for alt_name, system in systems.items():
        print(f"\nCalculating: {alt_name}")
        result = client.calculate.simple_calculation(
            system_ref=system,
            method=method,
            amount=1.0
        )
        impacts = client.results.get_total_impacts(result)
        impacts_all[alt_name] = impacts
        results[alt_name] = result
        print(f"  ✓ {len(impacts)} impact categories calculated")

    # PHASE 4: INTERPRETATION
    print("\n### PHASE 4: INTERPRETATION ###")

    # Comparison table
    print("\nComparative Results:")
    print(f"{'Impact Category':<30} | ", end='')
    for name in systems.keys():
        print(f"{name:<15} | ", end='')
    print("Winner")
    print("-" * 100)

    winners = {}
    for i in range(len(impacts_all[list(systems.keys())[0]])):
        cat_name = impacts_all[list(systems.keys())[0]][i]['name'][:29]

        print(f"{cat_name:<30} | ", end='')

        values = {}
        for alt_name in systems.keys():
            value = impacts_all[alt_name][i]['amount']
            values[alt_name] = value
            print(f"{value:10.3e}    | ", end='')

        winner = min(values, key=lambda k: abs(values[k]))
        winners[cat_name] = winner
        print(f"{winner}")

    # Summary
    print("\n### SUMMARY ###")
    print("\nOverall Performance:")
    winner_counts = {}
    for winner in winners.values():
        winner_counts[winner] = winner_counts.get(winner, 0) + 1

    for alt_name, count in sorted(winner_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / len(winners)) * 100
        print(f"  {alt_name}: Best in {count}/{len(winners)} categories ({pct:.0f}%)")

    # Recommendation
    overall_winner = max(winner_counts, key=winner_counts.get)
    print(f"\n✓ Recommendation: {overall_winner} (best overall environmental performance)")

    # Clean up
    print("\n### CLEANUP ###")
    for result in results.values():
        result.dispose()
    print("✓ All results disposed")

    return {
        'systems': systems,
        'impacts': impacts_all,
        'winners': winners,
        'recommendation': overall_winner
    }

# Example usage
bottles_spec = {
    'PET Bottle': {
        'description': 'Polyethylene terephthalate water bottle',
        'materials': {
            'pet': ['polyethylene', 'terephthalate', 'granulate'],
            'water': ['tap', 'water']
        },
        'amounts': {
            'pet': 0.025,
            'water': 1.0
        }
    },
    'Glass Bottle': {
        'description': 'Glass water bottle',
        'materials': {
            'glass': ['glass', 'bottle'],
            'water': ['tap', 'water']
        },
        'amounts': {
            'glass': 0.400,
            'water': 1.0
        }
    },
    'Aluminum Can': {
        'description': 'Aluminum beverage can',
        'materials': {
            'aluminum': ['aluminum', 'sheet'],
            'water': ['tap', 'water']
        },
        'amounts': {
            'aluminum': 0.015,
            'water': 0.330
        }
    }
}

comparison_results = complete_product_comparison_workflow(
    bottles_spec,
    ['ReCiPe', '2016', 'Midpoint']
)
```

### 5.2 AI Agent Workflow Template

```
PROMPT TEMPLATE FOR AI AGENT:

Perform a complete LCA comparing [ALTERNATIVES] using the following workflow:

PHASE 1: GOAL AND SCOPE
- Objective: [STATE OBJECTIVE]
- Functional Unit: [DEFINE FU]
- System Boundary: [SPECIFY BOUNDARY]
- Impact Method: [METHOD NAME]

PHASE 2: LIFE CYCLE INVENTORY
For each alternative:
1. Search for required materials using keywords
2. Find providers for each material
3. Create product flow for the alternative
4. Create process with material exchanges
5. Create product system

Materials needed:
[LIST MATERIALS AND AMOUNTS]

PHASE 3: IMPACT ASSESSMENT
1. Calculate impacts for all alternatives
2. Extract results for all impact categories
3. Store result IDs for later disposal

PHASE 4: INTERPRETATION
1. Compare impacts across alternatives
2. Identify winner for each category
3. Perform contribution analysis for top impacts
4. Generate summary and recommendation
5. Dispose all results

Please execute this workflow and provide:
- Comparison table showing all impacts
- Overall winner and recommendation
- Key insights and hotspots
```

---

## 6. Advanced Topics

### 6.1 Multi-Functional Processes

```python
"""
Handle processes with multiple outputs (co-products)
"""

def handle_multifunctional_process(process_name, allocation_method='economic'):
    """
    Model multi-functional process with allocation

    Allocation methods:
    - 'economic': Based on economic value of products
    - 'mass': Based on mass of products
    - 'energy': Based on energy content
    """

    print(f"\n=== MULTI-FUNCTIONAL PROCESS: {process_name} ===")
    print(f"Allocation method: {allocation_method}")

    # Example: Refinery producing multiple products
    # Crude oil → [Refinery] → Gasoline + Diesel + Heating Oil

    # Create output products
    gasoline = client.data.create_product_flow("Gasoline", "Motor fuel")
    diesel = client.data.create_product_flow("Diesel", "Diesel fuel")
    heating_oil = client.data.create_product_flow("Heating oil", "Residential heating")

    # Create process with multiple outputs
    exchanges = [
        # Outputs (co-products)
        client.data.create_exchange(
            o.Ref(id=gasoline.id),
            amount=0.45,  # 45% by mass
            is_input=False,
            is_quantitative_reference=True  # Choose one as reference
        ),
        client.data.create_exchange(
            o.Ref(id=diesel.id),
            amount=0.35,  # 35% by mass
            is_input=False
        ),
        client.data.create_exchange(
            o.Ref(id=heating_oil.id),
            amount=0.20,  # 20% by mass
            is_input=False
        )
    ]

    # Add inputs (crude oil, energy, etc.)
    crude_flows = client.search.find_flows(['crude', 'oil'], max_results=1)
    if crude_flows:
        exchanges.append(
            client.data.create_exchange(
                crude_flows[0],
                amount=1.0,  # 1 kg crude input
                is_input=True
            )
        )

    process = client.data.create_process(
        process_name,
        "Multi-functional refinery process",
        exchanges
    )

    print(f"✓ Multi-functional process created: {process.name}")
    print(f"  Outputs: Gasoline (45%), Diesel (35%), Heating oil (20%)")

    # Note: Allocation factors can be adjusted based on:
    # - Economic value ($/kg)
    # - Mass (kg/kg)
    # - Energy content (MJ/kg)

    return process

refinery = handle_multifunctional_process("Oil Refinery", "mass")
```

### 6.2 Consequential LCA

```python
"""
Consequential LCA modeling (system expansion)
"""

def consequential_lca_system_expansion(product_name, byproduct_replacement):
    """
    Model consequential LCA using system expansion

    Instead of allocation, include credits for avoided products

    Args:
        product_name: Main product being assessed
        byproduct_replacement: What the byproduct replaces in the market
    """

    print(f"\n=== CONSEQUENTIAL LCA: {product_name} ===")
    print(f"System expansion: Byproduct replaces {byproduct_replacement}")

    # Example: Bioethanol production
    # Corn → [Fermentation] → Ethanol + Animal Feed (DDGS)

    # Main product
    ethanol = client.data.create_product_flow("Bioethanol", "Fuel ethanol")

    # Byproduct
    ddgs = client.data.create_product_flow("DDGS", "Distillers grains (animal feed)")

    # Create process
    exchanges = [
        # Output: Ethanol (main product)
        client.data.create_exchange(
            o.Ref(id=ethanol.id),
            amount=1.0,
            is_input=False,
            is_quantitative_reference=True
        ),
        # Output: DDGS (byproduct)
        client.data.create_exchange(
            o.Ref(id=ddgs.id),
            amount=0.3,  # 0.3 kg per 1 kg ethanol
            is_input=False
        )
    ]

    # Input: Corn
    corn_flows = client.search.find_flows(['corn', 'grain'], max_results=1)
    if corn_flows:
        exchanges.append(
            client.data.create_exchange(
                corn_flows[0],
                amount=2.5,
                is_input=True
            )
        )

    # SYSTEM EXPANSION: Credit for avoided animal feed
    # DDGS replaces conventional animal feed (e.g., soy meal)
    soy_flows = client.search.find_flows(['soy', 'meal'], max_results=1)
    if soy_flows:
        soy_providers = client.search.find_providers(soy_flows[0])
        exchanges.append(
            client.data.create_exchange(
                soy_flows[0],
                amount=-0.3,  # Negative = avoided production (credit)
                is_input=True,
                provider=soy_providers[0] if soy_providers else None
            )
        )
        print(f"  System expansion: -0.3 kg soy meal (avoided)")

    process = client.data.create_process(
        f"{product_name} Production (System Expansion)",
        "Consequential LCA with credits for byproduct",
        exchanges
    )

    print(f"✓ Consequential system created: {process.name}")

    return process

bioethanol_conseq = consequential_lca_system_expansion(
    "Bioethanol",
    "Soy meal"
)
```

### 6.3 Dynamic LCA (Time-Dependent Impacts)

```python
"""
Dynamic LCA considering timing of emissions
"""

def dynamic_lca_time_dependent(product_name, emission_timeline):
    """
    Model dynamic LCA with time-dependent emissions

    Useful for:
    - Carbon sequestration (forests)
    - Delayed emissions (landfills)
    - Time-dependent damage (radioactive waste)

    Args:
        product_name: Product being assessed
        emission_timeline: Dict of {year: emissions} for key substances
    """

    print(f"\n=== DYNAMIC LCA: {product_name} ===")

    # Example: Forestry product
    # Year 0: Tree planting (CO2 uptake starts)
    # Years 1-20: Growth (net CO2 sequestration)
    # Year 20: Harvest (some CO2 release)
    # Year 21-50: Product use (carbon storage)
    # Year 50: End-of-life (CO2 release)

    print("\nEmission Timeline:")
    cumulative = 0
    for year, emissions in sorted(emission_timeline.items()):
        cumulative += emissions
        symbol = "↓" if emissions < 0 else "↑"
        print(f"  Year {year:3d}: {emissions:+.2f} kg CO2 {symbol} (cumulative: {cumulative:.2f})")

    # Calculate discounted impacts (optional)
    # Time preference: future impacts valued less than present
    discount_rate = 0.03  # 3% per year
    discounted_emissions = sum(
        emissions / ((1 + discount_rate) ** year)
        for year, emissions in emission_timeline.items()
    )

    print(f"\nTotal emissions (undiscounted): {sum(emission_timeline.values()):.2f} kg CO2")
    print(f"Total emissions (discounted @{discount_rate*100:.0f}%): {discounted_emissions:.2f} kg CO2")

    # Note: Dynamic LCA requires specialized tools
    # This is a simplified demonstration

    return {
        'total_undiscounted': sum(emission_timeline.values()),
        'total_discounted': discounted_emissions,
        'timeline': emission_timeline
    }

# Example: Wood product with carbon sequestration
wood_timeline = {
    0: -50.0,   # Tree planting (CO2 uptake in first year)
    5: -30.0,   # Growth phase
    10: -20.0,
    15: -10.0,
    20: +15.0,  # Harvesting and processing
    21: 0.0,    # Product use (carbon stored)
    50: +80.0   # End-of-life combustion
}

wood_dynamic = dynamic_lca_time_dependent("Wood Furniture", wood_timeline)
```

---

## Conclusion

This systems analysis guide provides comprehensive methodologies for conducting Life Cycle Assessments using the OpenLCA MCP Server and AI agents. Key takeaways:

**System Construction:**
- Use **top-down** for complex assembled products
- Use **bottom-up** for material-focused studies
- Use **hybrid** for practical efficiency

**Analysis Techniques:**
- **Contribution analysis** identifies hotspots
- **Comparative analysis** ranks alternatives
- **Sensitivity analysis** tests robustness
- **Uncertainty analysis** quantifies confidence

**Best Practices:**
1. Always start with clear goal and scope
2. Document all assumptions and limitations
3. Use ecoinvent database systematically
4. Perform sensitivity checks on key parameters
5. Present results with uncertainty ranges
6. Make recommendations context-specific

**Advanced Capabilities:**
- Multi-functional processes with allocation
- Consequential LCA with system expansion
- Dynamic LCA for time-dependent impacts

For practical implementation examples, see:
- [PET vs PC Case Study](CASE_STUDY_PET_PC.md)
- [Ceramic vs Paper Cups Case Study](CASE_STUDY_CUPS.md)
- [Client Test Examples](CLIENT_TEST_EXAMPLES.md)

---

**Document Version:** 1.0
**Last Updated:** 2025-12-04
**Author:** OpenLCA MCP Server Documentation Team
