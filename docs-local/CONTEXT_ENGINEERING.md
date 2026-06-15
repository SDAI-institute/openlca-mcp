# Context Engineering for LCA AI Agents

## Overview

This guide provides comprehensive strategies for managing context in AI agent systems performing Life Cycle Assessment tasks. Effective context engineering is critical for maintaining coherent, accurate, and efficient LCA workflows across multi-turn conversations and multi-agent systems.

## Table of Contents

1. [Context Management Fundamentals](#1-context-management-fundamentals)
2. [Context Compression Techniques](#2-context-compression-techniques)
3. [Dynamic Context Windows](#3-dynamic-context-windows)
4. [Knowledge Injection Strategies](#4-knowledge-injection-strategies)
5. [Memory Systems](#5-memory-systems)
6. [Context-Aware Prompting](#6-context-aware-prompting)
7. [Optimization Patterns](#7-optimization-patterns)

---

## 1. Context Management Fundamentals

### 1.1 The Context Challenge in LCA

**Why Context Matters for LCA:**

```
LCA Workflow Context Requirements:

Phase 1 (Goal & Scope)
├─ User requirements (functional unit, boundaries)
├─ Material search results (flows, providers)
├─ Impact method selection
└─ Assumptions and limitations

Phase 2 (LCI)
├─ All Phase 1 context
├─ Process definitions
├─ Exchange linkages
├─ Mass balance data
└─ System structure

Phase 3 (LCIA)
├─ Phases 1-2 context
├─ Calculation parameters
├─ Result IDs (for disposal!)
├─ Impact values
└─ Calculation metadata

Phase 4 (Interpretation)
├─ Phases 1-3 context
├─ Contribution analysis
├─ Sensitivity parameters
├─ Comparison data
└─ Recommendations

Total context: Can exceed 50,000 tokens for complex studies!
```

**Context Types:**

1. **Persistent Context** - Carried through entire workflow
   - Functional unit
   - System boundary
   - Impact method
   - User preferences

2. **Phase-Specific Context** - Needed only in certain phases
   - Material search results (Phase 1-2)
   - Process IDs (Phase 2-3)
   - Result IDs (Phase 3-4)

3. **Ephemeral Context** - Temporary, can be discarded
   - Search iterations
   - Retry attempts
   - Intermediate calculations

4. **Reference Context** - Retrieved on demand
   - Database documentation
   - Method descriptions
   - Material properties

### 1.2 Context Window Economics

**Token Budget Allocation:**

```python
"""
Optimal token allocation for LCA agents
"""

class ContextBudget:
    """
    Manage token budget across context types
    """

    def __init__(self, total_tokens=200000):
        self.total_tokens = total_tokens

        # Allocation strategy
        self.allocation = {
            'system_prompt': 0.05,      # 5% - Agent instructions
            'persistent_context': 0.15,  # 15% - Goal, scope, method
            'working_memory': 0.30,      # 30% - Current phase data
            'tool_responses': 0.25,      # 25% - MCP tool outputs
            'conversation_history': 0.15, # 15% - User interactions
            'output_buffer': 0.10        # 10% - Response generation
        }

    def get_allocation(self, context_type):
        """Get token allocation for context type"""
        return int(self.total_tokens * self.allocation[context_type])

    def prioritize_context(self, contexts, max_tokens):
        """
        Prioritize context elements when approaching limit

        Priority order:
        1. Critical (functional unit, system boundary)
        2. Essential (material IDs, process IDs)
        3. Important (search results, alternatives)
        4. Nice-to-have (metadata, timestamps)
        5. Disposable (search iterations, retries)
        """

        prioritized = []
        token_count = 0

        # Sort by priority
        sorted_contexts = sorted(
            contexts,
            key=lambda x: x.get('priority', 5)
        )

        for context in sorted_contexts:
            context_tokens = self.estimate_tokens(context['content'])

            if token_count + context_tokens <= max_tokens:
                prioritized.append(context)
                token_count += context_tokens
            else:
                # Compress or truncate
                if context['priority'] <= 2:  # Critical/Essential
                    compressed = self.compress_context(context['content'])
                    prioritized.append({
                        **context,
                        'content': compressed,
                        'compressed': True
                    })
                    token_count += self.estimate_tokens(compressed)

        return prioritized

    @staticmethod
    def estimate_tokens(text):
        """Rough token estimate (4 chars ≈ 1 token)"""
        return len(str(text)) // 4

    @staticmethod
    def compress_context(content):
        """Compress context (remove whitespace, abbreviate)"""
        import json
        import re

        if isinstance(content, dict):
            # Remove unnecessary fields
            compressed = {
                k: v for k, v in content.items()
                if k not in ['timestamp', 'metadata', 'warnings']
            }
            # Compact JSON
            return json.dumps(compressed, separators=(',', ':'))
        elif isinstance(content, str):
            # Remove extra whitespace
            return re.sub(r'\s+', ' ', content).strip()
        else:
            return content

# Usage
budget = ContextBudget(total_tokens=200000)

contexts = [
    {'priority': 1, 'type': 'functional_unit', 'content': "1 filled PET bottle (1.065 kg)"},
    {'priority': 1, 'type': 'system_boundary', 'content': "cradle-to-gate"},
    {'priority': 2, 'type': 'material_ids', 'content': {"PET": "abc-123", "HDPE": "def-456"}},
    {'priority': 3, 'type': 'search_results', 'content': [...large list...]},
    {'priority': 4, 'type': 'metadata', 'content': {...}},
    {'priority': 5, 'type': 'search_iterations', 'content': [...]}
]

prioritized = budget.prioritize_context(
    contexts,
    max_tokens=budget.get_allocation('working_memory')
)
```

### 1.3 Context Lifecycle Management

```python
"""
Manage context across agent lifecycle
"""

class ContextLifecycle:
    """
    Track context from creation to disposal
    """

    def __init__(self):
        self.contexts = {}
        self.lifecycle_stages = {
            'created': [],
            'active': [],
            'archived': [],
            'disposed': []
        }

    def create_context(self, context_id, content, ttl=None, priority=3):
        """
        Create new context element

        Args:
            context_id: Unique identifier
            content: Context data
            ttl: Time-to-live in seconds (None = permanent)
            priority: 1 (critical) to 5 (disposable)
        """

        context = {
            'id': context_id,
            'content': content,
            'priority': priority,
            'ttl': ttl,
            'created_at': datetime.now(),
            'last_accessed': datetime.now(),
            'access_count': 0,
            'stage': 'created'
        }

        self.contexts[context_id] = context
        self.lifecycle_stages['created'].append(context_id)

        return context

    def activate_context(self, context_id):
        """Move context to active stage"""
        if context_id in self.contexts:
            self.contexts[context_id]['stage'] = 'active'
            self.lifecycle_stages['active'].append(context_id)

            if context_id in self.lifecycle_stages['created']:
                self.lifecycle_stages['created'].remove(context_id)

    def access_context(self, context_id):
        """Record context access"""
        if context_id in self.contexts:
            context = self.contexts[context_id]
            context['last_accessed'] = datetime.now()
            context['access_count'] += 1
            return context['content']
        return None

    def archive_context(self, context_id):
        """
        Archive context (move to long-term storage)

        Archived contexts:
        - Not in active context window
        - Can be retrieved if needed
        - Lower priority for memory
        """

        if context_id in self.contexts:
            self.contexts[context_id]['stage'] = 'archived'
            self.lifecycle_stages['archived'].append(context_id)

            if context_id in self.lifecycle_stages['active']:
                self.lifecycle_stages['active'].remove(context_id)

    def dispose_context(self, context_id):
        """Permanently remove context"""
        if context_id in self.contexts:
            self.contexts[context_id]['stage'] = 'disposed'
            self.lifecycle_stages['disposed'].append(context_id)

            # Remove from other stages
            for stage in ['created', 'active', 'archived']:
                if context_id in self.lifecycle_stages[stage]:
                    self.lifecycle_stages[stage].remove(context_id)

            # Actually delete after marking
            del self.contexts[context_id]

    def cleanup_expired(self):
        """Remove contexts past TTL"""
        now = datetime.now()

        for context_id, context in list(self.contexts.items()):
            if context['ttl'] is not None:
                age = (now - context['created_at']).total_seconds()
                if age > context['ttl']:
                    print(f"Context {context_id} expired (age: {age:.0f}s, TTL: {context['ttl']}s)")
                    self.dispose_context(context_id)

    def get_active_contexts(self):
        """Get all active contexts ordered by priority"""
        active_ids = self.lifecycle_stages['active']

        active = [
            self.contexts[cid]
            for cid in active_ids
            if cid in self.contexts
        ]

        # Sort by priority (lower number = higher priority)
        return sorted(active, key=lambda x: x['priority'])

# Usage example
lifecycle = ContextLifecycle()

# Create contexts with different lifecycles
lifecycle.create_context(
    'functional_unit',
    content="1 filled PET bottle (1.065 kg)",
    ttl=None,  # Permanent
    priority=1  # Critical
)

lifecycle.create_context(
    'search_results_pet',
    content=[...],
    ttl=3600,  # 1 hour
    priority=3  # Important during search, disposable after
)

lifecycle.create_context(
    'result_id_12345',
    content="result-abc-123",
    ttl=600,  # 10 minutes (must dispose result before this!)
    priority=2  # Essential while calculating
)

# Activate critical contexts
lifecycle.activate_context('functional_unit')
lifecycle.activate_context('result_id_12345')

# Clean up expired
lifecycle.cleanup_expired()
```

---

## 2. Context Compression Techniques

### 2.1 Structured Summarization

```python
"""
Compress context while preserving essential information
"""

class ContextCompressor:
    """
    Intelligent context compression
    """

    @staticmethod
    def compress_material_list(materials):
        """
        Compress long material lists

        From:
        [
          {"name": "PET granulate, bottle grade", "id": "abc-123", "provider": "...long name...", ...},
          {"name": "HDPE granulate", "id": "def-456", "provider": "...long name...", ...}
        ]

        To:
        "PET:abc-123, HDPE:def-456"
        """

        compressed = ", ".join([
            f"{m['name'].split(',')[0]}:{m['id'][:8]}"
            for m in materials
        ])

        return compressed

    @staticmethod
    def compress_process_exchanges(exchanges):
        """
        Compress exchange lists

        From:
        [
          {
            "flow": {"id": "abc", "name": "PET granulate..."},
            "amount": 0.060,
            "unit": "kg",
            "is_input": true,
            "is_quantitative_reference": false,
            "provider": {...}
          },
          ...
        ]

        To:
        "IN: PET(0.060kg), HDPE(0.004kg); OUT: Bottle(1.0kg)*"
        """

        inputs = []
        outputs = []

        for ex in exchanges:
            flow_name = ex['flow']['name'].split(',')[0]  # First part only
            amount = ex['amount']
            unit = ex.get('unit', 'kg')
            is_qref = ex.get('is_quantitative_reference', False)

            formatted = f"{flow_name}({amount}{unit})"
            if is_qref:
                formatted += "*"

            if ex['is_input']:
                inputs.append(formatted)
            else:
                outputs.append(formatted)

        compressed = f"IN: {', '.join(inputs)}; OUT: {', '.join(outputs)}"
        return compressed

    @staticmethod
    def compress_impact_results(impacts):
        """
        Compress impact results to top N

        From: 13 impact categories with full details

        To: Top 3 + summary
        """

        # Sort by absolute value
        sorted_impacts = sorted(
            impacts,
            key=lambda x: abs(x['amount']),
            reverse=True
        )

        # Top 3
        top3 = [
            f"{i['name']}: {i['amount']:.2e} {i['unit']}"
            for i in sorted_impacts[:3]
        ]

        compressed = {
            'top_3': top3,
            'total_categories': len(impacts),
            'full_data_available': True
        }

        return compressed

    @staticmethod
    def compress_search_history(search_history):
        """
        Compress search iterations

        From: Full search history with all results

        To: Final successful search only
        """

        # Get last successful search
        successful = [s for s in search_history if s.get('found', False)]

        if successful:
            last_success = successful[-1]
            return {
                'final_keywords': last_success['keywords'],
                'found': last_success['result'],
                'attempts': len(search_history)
            }
        else:
            return {
                'found': False,
                'attempts': len(search_history),
                'last_keywords': search_history[-1]['keywords'] if search_history else []
            }

# Usage
compressor = ContextCompressor()

# Compress materials
materials_full = [
    {
        "name": "polyethylene terephthalate, granulate, bottle grade",
        "id": "abc-123-def-456",
        "provider": {"id": "prov-789", "name": "Very long provider name..."},
        "category": "plastics/polymers",
        "metadata": {...}
    },
    # ... more materials
]

materials_compressed = compressor.compress_material_list(materials_full)
print(materials_compressed)
# Output: "polyethylene terephthalate:abc-123-, ..."

# Compress impacts
impacts_full = [...]  # 13 categories

impacts_compressed = compressor.compress_impact_results(impacts_full)
print(impacts_compressed)
# Output: {'top_3': ['Global Warming: 2.34e-02 kg CO2 eq', ...], 'total_categories': 13}
```

### 2.2 Differential Context Updates

```python
"""
Send only changes, not full context
"""

class DifferentialContext:
    """
    Track and transmit only context changes
    """

    def __init__(self):
        self.baseline = {}
        self.version = 0

    def set_baseline(self, context_dict):
        """Set baseline context"""
        self.baseline = context_dict.copy()
        self.version = 0

    def get_diff(self, new_context):
        """
        Get difference between baseline and new context

        Returns:
            - added: New keys
            - modified: Changed values
            - removed: Deleted keys
        """

        added = {}
        modified = {}
        removed = {}

        # Find added and modified
        for key, value in new_context.items():
            if key not in self.baseline:
                added[key] = value
            elif self.baseline[key] != value:
                modified[key] = {
                    'old': self.baseline[key],
                    'new': value
                }

        # Find removed
        for key in self.baseline:
            if key not in new_context:
                removed[key] = self.baseline[key]

        self.version += 1

        return {
            'version': self.version,
            'diff': {
                'added': added,
                'modified': modified,
                'removed': removed
            },
            'has_changes': bool(added or modified or removed)
        }

    def apply_diff(self, diff_dict):
        """Apply diff to baseline"""
        diff = diff_dict['diff']

        # Add new keys
        self.baseline.update(diff['added'])

        # Modify existing
        for key, change in diff['modified'].items():
            self.baseline[key] = change['new']

        # Remove deleted
        for key in diff['removed']:
            if key in self.baseline:
                del self.baseline[key]

        self.version = diff_dict['version']

# Usage
diff_context = DifferentialContext()

# Set initial context
baseline = {
    'functional_unit': '1 PET bottle',
    'system_boundary': 'cradle-to-gate',
    'materials_found': 5
}

diff_context.set_baseline(baseline)

# Later, context changes
new_context = {
    'functional_unit': '1 PET bottle',  # Same
    'system_boundary': 'cradle-to-grave',  # Changed
    'materials_found': 7,  # Changed
    'processes_created': 3  # Added
}

# Get diff
diff = diff_context.get_diff(new_context)

print(f"Context diff (version {diff['version']}):")
print(f"  Added: {diff['diff']['added']}")
print(f"  Modified: {diff['diff']['modified']}")
print(f"  Removed: {diff['diff']['removed']}")

# Output:
# Context diff (version 1):
#   Added: {'processes_created': 3}
#   Modified: {'system_boundary': {'old': 'cradle-to-gate', 'new': 'cradle-to-grave'},
#              'materials_found': {'old': 5, 'new': 7}}
#   Removed: {}

# Transmit only diff (much smaller than full context!)
```

### 2.3 Hierarchical Context Pruning

```python
"""
Prune context tree based on relevance
"""

class HierarchicalPruner:
    """
    Prune less relevant branches of context tree
    """

    @staticmethod
    def prune_context_tree(context_tree, current_phase, max_depth=2):
        """
        Prune context tree based on current phase

        Context tree structure:
        {
          'phase_1': {
            'functional_unit': ...,
            'materials': {
              'PET': {'id': ..., 'provider': ..., 'alternatives': [...]},
              'HDPE': {...}
            }
          },
          'phase_2': {...},
          ...
        }

        Pruning rules:
        - Phase 1: Keep detailed
        - Phase 2: Compress alternatives, keep IDs
        - Phase 3: Keep only essential IDs
        - Phase 4: Keep only results
        """

        pruned = {}

        for phase_key, phase_context in context_tree.items():
            phase_num = int(phase_key.split('_')[1])

            if phase_num < current_phase:
                # Past phase: Keep only essential
                pruned[phase_key] = HierarchicalPruner._prune_phase_essential(
                    phase_context,
                    max_depth=1
                )
            elif phase_num == current_phase:
                # Current phase: Keep detailed
                pruned[phase_key] = phase_context
            else:
                # Future phase: Skip
                pass

        return pruned

    @staticmethod
    def _prune_phase_essential(phase_context, max_depth):
        """Keep only essential data from phase"""

        if max_depth == 0:
            return "..."  # Placeholder

        essential = {}

        for key, value in phase_context.items():
            # Keep IDs, amounts, and high-priority data
            if key in ['id', 'ids', 'amount', 'functional_unit',
                       'system_boundary', 'method_id', 'result_id']:
                essential[key] = value

            # Compress lists to length
            elif isinstance(value, list):
                essential[key] = f"[{len(value)} items]"

            # Recurse into dicts
            elif isinstance(value, dict) and max_depth > 1:
                essential[key] = HierarchicalPruner._prune_phase_essential(
                    value,
                    max_depth - 1
                )

        return essential

# Usage
context_tree = {
    'phase_1': {
        'functional_unit': '1 PET bottle',
        'system_boundary': 'cradle-to-gate',
        'materials': {
            'PET': {
                'id': 'abc-123',
                'name': 'PET granulate bottle grade',
                'provider': {'id': 'prov-456', 'name': 'Long provider name...'},
                'alternatives': [
                    {'id': 'alt-1', 'name': '...'},
                    {'id': 'alt-2', 'name': '...'}
                ],
                'metadata': {...}
            },
            'HDPE': {...}
        },
        'search_iterations': [...]
    },
    'phase_2': {
        'processes_created': [...]
    }
}

# When in Phase 3, prune Phase 1 context
pruner = HierarchicalPruner()
pruned = pruner.prune_context_tree(context_tree, current_phase=3)

print(pruned)
# Output:
# {
#   'phase_1': {
#     'functional_unit': '1 PET bottle',
#     'system_boundary': 'cradle-to-gate',
#     'materials': {
#       'PET': {'id': 'abc-123'},
#       'HDPE': {'id': 'def-456'}
#     }
#   },
#   'phase_2': {...}
# }
```

---

## 3. Dynamic Context Windows

### 3.1 Sliding Window Context

```python
"""
Sliding window for conversation history
"""

class SlidingContextWindow:
    """
    Maintain fixed-size context window
    """

    def __init__(self, window_size=10):
        self.window_size = window_size
        self.messages = []
        self.pinned_messages = []

    def add_message(self, role, content, pinned=False):
        """
        Add message to window

        Args:
            role: 'user', 'assistant', or 'system'
            content: Message content
            pinned: If True, message stays in context forever
        """

        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now(),
            'pinned': pinned
        }

        if pinned:
            self.pinned_messages.append(message)
        else:
            self.messages.append(message)

            # Maintain window size
            if len(self.messages) > self.window_size:
                removed = self.messages.pop(0)
                print(f"Removed message from window: {removed['content'][:50]}...")

    def get_context(self):
        """Get full context (pinned + windowed)"""
        return self.pinned_messages + self.messages

    def get_summary(self):
        """Get summary of current window"""
        return {
            'total_messages': len(self.messages) + len(self.pinned_messages),
            'pinned': len(self.pinned_messages),
            'windowed': len(self.messages),
            'oldest_windowed': self.messages[0]['timestamp'] if self.messages else None,
            'newest': self.messages[-1]['timestamp'] if self.messages else None
        }

# Usage
window = SlidingContextWindow(window_size=5)

# Pin critical context
window.add_message(
    'system',
    'Functional Unit: 1 filled PET bottle (1.065 kg). System Boundary: cradle-to-gate.',
    pinned=True
)

# Add conversation messages
window.add_message('user', 'Search for PET granulate')
window.add_message('assistant', 'Found 3 PET flows...')
window.add_message('user', 'Use the bottle grade')
window.add_message('assistant', 'Selected PET bottle grade (id: abc-123)')
window.add_message('user', 'Now search for HDPE')
window.add_message('assistant', 'Found 2 HDPE flows...')

# Window maintains only last 5 messages + 1 pinned
print(f"Context messages: {len(window.get_context())}")  # 6 (1 pinned + 5 windowed)
```

### 3.2 Attention-Based Context Selection

```python
"""
Select context based on attention/relevance to current task
"""

class AttentionContextSelector:
    """
    Select most relevant context using attention mechanism
    """

    def __init__(self):
        self.context_store = {}
        self.attention_weights = {}

    def add_context(self, context_id, content, tags):
        """
        Add context with tags for attention calculation

        Args:
            context_id: Unique ID
            content: Context data
            tags: List of tags for relevance matching
        """

        self.context_store[context_id] = {
            'content': content,
            'tags': set(tags),
            'created_at': datetime.now(),
            'access_count': 0
        }

    def calculate_attention(self, context_id, query_tags, recency_weight=0.3):
        """
        Calculate attention score for context

        Score based on:
        - Tag overlap (70%)
        - Recency (30%)
        """

        if context_id not in self.context_store:
            return 0.0

        context = self.context_store[context_id]

        # Tag similarity (Jaccard)
        query_tags_set = set(query_tags)
        intersection = context['tags'].intersection(query_tags_set)
        union = context['tags'].union(query_tags_set)

        tag_score = len(intersection) / len(union) if union else 0.0

        # Recency (decay over time)
        age_hours = (datetime.now() - context['created_at']).total_seconds() / 3600
        recency_score = 1.0 / (1.0 + age_hours)  # Exponential decay

        # Combined score
        attention_score = (
            (1 - recency_weight) * tag_score +
            recency_weight * recency_score
        )

        self.attention_weights[context_id] = attention_score

        return attention_score

    def select_top_contexts(self, query_tags, top_k=5):
        """
        Select top-k most relevant contexts

        Args:
            query_tags: Tags representing current task
            top_k: Number of contexts to return
        """

        # Calculate attention for all contexts
        for context_id in self.context_store:
            self.calculate_attention(context_id, query_tags)

        # Sort by attention score
        sorted_contexts = sorted(
            self.attention_weights.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Get top-k
        top_context_ids = [cid for cid, score in sorted_contexts[:top_k]]

        # Increment access count
        for cid in top_context_ids:
            self.context_store[cid]['access_count'] += 1

        return [
            {
                'id': cid,
                'content': self.context_store[cid]['content'],
                'attention_score': self.attention_weights[cid]
            }
            for cid in top_context_ids
        ]

# Usage
selector = AttentionContextSelector()

# Add various contexts with tags
selector.add_context(
    'functional_unit',
    '1 filled PET bottle (1.065 kg)',
    tags=['goal', 'scope', 'functional_unit', 'pet', 'bottle']
)

selector.add_context(
    'pet_search_results',
    [{'id': 'abc-123', 'name': 'PET granulate...'}],
    tags=['search', 'materials', 'pet', 'granulate', 'phase_1']
)

selector.add_context(
    'pet_process',
    {'id': 'proc-456', 'name': 'PET bottle production'},
    tags=['process', 'modeling', 'pet', 'bottle', 'phase_2']
)

selector.add_context(
    'impact_results',
    [{'category': 'GWP', 'amount': 0.0234}],
    tags=['results', 'impacts', 'calculation', 'phase_3']
)

# When creating processes (Phase 2), select relevant context
current_task_tags = ['process', 'modeling', 'pet', 'phase_2']
relevant = selector.select_top_contexts(current_task_tags, top_k=3)

print("Most relevant contexts for current task:")
for ctx in relevant:
    print(f"  {ctx['id']}: score={ctx['attention_score']:.3f}")

# Output:
#   pet_process: score=0.812
#   pet_search_results: score=0.654
#   functional_unit: score=0.423
```

### 3.3 Adaptive Window Sizing

```python
"""
Dynamically adjust context window based on task complexity
"""

class AdaptiveContextWindow:
    """
    Adjust window size based on task requirements
    """

    def __init__(self, base_size=10000):
        self.base_size = base_size
        self.current_size = base_size
        self.min_size = 5000
        self.max_size = 50000

    def adjust_for_task(self, task_type, complexity='medium'):
        """
        Adjust window size based on task

        Task types:
        - simple_search: Small window
        - process_modeling: Medium window
        - comparative_analysis: Large window
        - uncertainty_analysis: Very large window
        """

        size_multipliers = {
            'simple': {
                'simple_search': 0.5,
                'process_modeling': 1.0,
                'comparative_analysis': 1.5,
                'uncertainty_analysis': 2.0
            },
            'medium': {
                'simple_search': 0.7,
                'process_modeling': 1.2,
                'comparative_analysis': 2.0,
                'uncertainty_analysis': 2.5
            },
            'high': {
                'simple_search': 1.0,
                'process_modeling': 1.5,
                'comparative_analysis': 2.5,
                'uncertainty_analysis': 3.0
            }
        }

        multiplier = size_multipliers.get(complexity, {}).get(task_type, 1.0)
        self.current_size = int(self.base_size * multiplier)

        # Clamp to bounds
        self.current_size = max(self.min_size, min(self.current_size, self.max_size))

        print(f"Adjusted context window: {self.current_size:,} tokens ({task_type}, {complexity} complexity)")

        return self.current_size

# Usage
adaptive = AdaptiveContextWindow(base_size=10000)

# Simple search task
adaptive.adjust_for_task('simple_search', 'simple')
# Output: "Adjusted context window: 5,000 tokens (simple_search, simple complexity)"

# Complex comparative analysis
adaptive.adjust_for_task('comparative_analysis', 'high')
# Output: "Adjusted context window: 25,000 tokens (comparative_analysis, high complexity)"

# Uncertainty analysis with many iterations
adaptive.adjust_for_task('uncertainty_analysis', 'high')
# Output: "Adjusted context window: 30,000 tokens (uncertainty_analysis, high complexity)"
```

---

## 4. Knowledge Injection Strategies

### 4.1 Just-In-Time Knowledge Retrieval

```python
"""
Retrieve domain knowledge only when needed
"""

class KnowledgeRetriever:
    """
    Retrieve LCA domain knowledge on demand
    """

    def __init__(self):
        self.knowledge_base = {
            'impact_methods': {
                'TRACI': {
                    'full_name': 'Tool for Reduction and Assessment of Chemicals and other environmental Impacts',
                    'developer': 'US EPA',
                    'suitable_for': ['US studies', 'chemicals', 'products'],
                    'categories': 10,
                    'when_to_use': 'Use for US-based studies or when US EPA methodology is required'
                },
                'ReCiPe': {
                    'full_name': 'ReCiPe 2016',
                    'developer': 'RIVM, CML, PRé',
                    'suitable_for': ['European studies', 'global studies'],
                    'categories': 18,
                    'when_to_use': 'Use for European or global studies, comprehensive coverage'
                },
                # ... more methods
            },
            'material_categories': {
                'plastics': {
                    'common_materials': ['PET', 'HDPE', 'LDPE', 'PP', 'PS', 'PVC'],
                    'typical_applications': {
                        'PET': 'bottles, containers',
                        'HDPE': 'containers, pipes',
                        'PP': 'automotive, packaging'
                    },
                    'search_tips': 'Search for "granulate" form, specify grade (bottle, film, etc.)'
                },
                # ... more categories
            },
            'lca_methodology': {
                'functional_unit_guidelines': [
                    'Must be measurable',
                    'Must reflect function, not product',
                    'Must enable fair comparison',
                    'Examples: "1 km of passenger transport", "1 m² painted for 10 years"'
                ],
                'system_boundary_types': {
                    'cradle-to-gate': 'Raw materials → factory gate',
                    'cradle-to-grave': 'Raw materials → end-of-life',
                    'gate-to-gate': 'Factory input → factory output'
                }
            }
        }

    def retrieve_knowledge(self, topic, subtopic=None):
        """
        Retrieve knowledge on-demand

        Args:
            topic: Main topic (e.g., 'impact_methods')
            subtopic: Specific subtopic (e.g., 'TRACI')
        """

        if topic not in self.knowledge_base:
            return None

        if subtopic:
            return self.knowledge_base[topic].get(subtopic)
        else:
            return self.knowledge_base[topic]

    def get_contextual_help(self, user_query):
        """
        Provide contextual help based on query

        Args:
            user_query: User's question or task
        """

        query_lower = user_query.lower()

        # Detect topic
        if 'traci' in query_lower or 'impact method' in query_lower:
            return self.retrieve_knowledge('impact_methods', 'TRACI')

        elif 'functional unit' in query_lower:
            return self.retrieve_knowledge('lca_methodology', 'functional_unit_guidelines')

        elif 'plastic' in query_lower or 'polymer' in query_lower:
            return self.retrieve_knowledge('material_categories', 'plastics')

        else:
            return None

# Usage
kb = KnowledgeRetriever()

# User asks about impact method
user_query = "Should I use TRACI or ReCiPe for my US-based study?"
help_info = kb.get_contextual_help(user_query)

if help_info:
    print(f"Knowledge injection: {help_info}")
    # Inject this into agent's context only when needed!

# Output:
# Knowledge injection: {
#   'full_name': 'Tool for Reduction and Assessment of...',
#   'when_to_use': 'Use for US-based studies...'
# }
```

### 4.2 Template-Based Context Injection

```python
"""
Use templates to inject structured domain knowledge
"""

class ContextTemplates:
    """
    Pre-defined context templates for common scenarios
    """

    @staticmethod
    def get_phase_1_template():
        """Template for Phase 1 (Goal & Scope)"""
        return {
            'role': 'system',
            'content': """
You are performing Goal & Scope Definition for an LCA study.

Key responsibilities:
1. Define clear functional unit (quantified performance)
2. Establish system boundary (cradle-to-gate, cradle-to-grave, etc.)
3. Search ecoinvent database for required materials
4. Select appropriate LCIA method

ecoinvent Search Tips:
- Materials format: "[material], [form], [grade], [region]"
- Example: "polyethylene terephthalate, granulate, bottle grade, RER"
- Regions: RER (Europe), GLO (Global), US, CN, etc.
- Use "market" processes for average supply mix
- Use specific processes for particular technologies

Impact Method Selection:
- TRACI 2.1: US studies, EPA methodology
- ReCiPe 2016: European/global, comprehensive
- ILCD 2011: EU-recommended
- CML-IA: Traditional baseline method

Output required:
- Functional unit (clear, measurable)
- System boundary (explicit scope)
- Materials list (IDs and provider IDs)
- Impact method (ID)
"""
        }

    @staticmethod
    def get_phase_2_template():
        """Template for Phase 2 (LCI)"""
        return {
            'role': 'system',
            'content': """
You are building Life Cycle Inventory for an LCA study.

Key responsibilities:
1. Create product flows for system outputs
2. Model processes with exchanges
3. Link processes via providers
4. Build complete product systems

Process Modeling Guidelines:
- Each process has ONE quantitative reference (main output)
- All inputs must have amounts and units
- Link inputs to providers (background processes)
- Validate mass balance (inputs ≈ outputs ± losses)

Exchange Structure:
{
  "flow": flow_reference,
  "amount": numeric_value,
  "unit": "kg",
  "is_input": true/false,
  "is_quantitative_reference": true/false,
  "provider": provider_process_reference
}

Common Pitfalls:
- ✗ Missing providers (unlinked inputs)
- ✗ No quantitative reference
- ✗ Incorrect units
- ✗ Circular references

Output required:
- Product flows created
- Processes with validated exchanges
- Product system ID
"""
        }

    @staticmethod
    def get_comparative_analysis_template(alternatives):
        """Template for comparative analysis"""
        return {
            'role': 'system',
            'content': f"""
You are performing comparative LCA of {len(alternatives)} alternatives:
{', '.join(alternatives)}

Comparative Analysis Guidelines:
1. Ensure SAME functional unit for all alternatives
2. Use SAME impact method for all
3. Use SAME system boundary for all
4. Calculate all alternatives before comparing

Fair Comparison Checklist:
☐ Functional equivalence verified
☐ System boundaries aligned
☐ Same background database
☐ Same impact method
☐ Same allocation approach

Result Presentation:
- Normalize to reference alternative (usually first)
- Show absolute values AND percentages
- Identify winner per impact category
- Provide overall recommendation

Statistical Rigor:
- Report uncertainty if available
- Highlight significant differences
- Note limitations and assumptions
"""
        }

# Usage in agent prompt
templates = ContextTemplates()

# Inject Phase 1 template when starting Goal & Scope
phase1_context = templates.get_phase_1_template()

# Inject comparative template when doing comparison
comparison_context = templates.get_comparative_analysis_template(
    ['PET Bottle', 'PC Bottle', 'Glass Bottle']
)

# Add to agent's system prompts
```

### 4.3 Example-Based Learning Injection

```python
"""
Inject examples dynamically based on task similarity
"""

class ExampleInjector:
    """
    Provide relevant examples based on current task
    """

    def __init__(self):
        self.example_library = {
            'material_search': {
                'plastics': """
Example: Searching for PET bottle-grade granulate

Step 1: Broad search
Keywords: ['polyethylene', 'terephthalate']
Results: 18 flows (too many)

Step 2: Add form factor
Keywords: ['polyethylene', 'terephthalate', 'granulate']
Results: 8 flows (better)

Step 3: Add grade
Keywords: ['polyethylene', 'terephthalate', 'granulate', 'bottle']
Results: 3 flows (specific)

Step 4: Select best match
Selected: "polyethylene terephthalate, granulate, bottle grade | production | RER"
ID: abc-123-def-456
Provider: First result from find_providers()
""",
                'metals': """
Example: Searching for aluminum sheet

Keywords: ['aluminum', 'sheet']
Results: Multiple alloys and treatments

Best practice:
- Specify alloy if known (e.g., '6061', '5052')
- Specify treatment (e.g., 'cold rolled', 'annealed')
- Specify region for accuracy

Selected: "aluminum, sheet, cold rolled | production | RER"
"""
            },
            'process_modeling': {
                'simple_production': """
Example: Simple production process

Product: PET Bottle (0.025 kg)
Inputs:
- PET granulate: 0.025 kg (from background database)
- Electricity: 0.05 kWh (manufacturing energy)

Process creation:
1. create_product_flow("PET Bottle 0.5L", "Beverage container")
   → bottle_flow_id

2. create_process("PET Bottle Production", exchanges=[
     {flow: bottle_flow_id, amount: 1.0, is_input: false, is_qref: true},
     {flow: pet_granulate_id, amount: 0.025, is_input: true, provider: pet_prov_id},
     {flow: electricity_id, amount: 0.05, is_input: true, provider: elec_prov_id}
   ])
   → process_id

3. create_product_system(process_id)
   → system_id
""",
                'multi_material': """
Example: Multi-material product

Product: Aluminum can with coating
Materials:
- Aluminum sheet: 0.015 kg
- Polymer coating: 0.0005 kg
- Electricity: 0.08 kWh

Create exchanges for each material with appropriate providers.
Ensure mass balance: total inputs ≈ output + losses
"""
            }
        }

    def get_relevant_example(self, task_type, material_category=None):
        """
        Get example relevant to current task

        Args:
            task_type: 'material_search', 'process_modeling', etc.
            material_category: Optional subcategory
        """

        if task_type not in self.example_library:
            return None

        examples = self.example_library[task_type]

        if material_category and material_category in examples:
            return examples[material_category]
        else:
            # Return first example
            return next(iter(examples.values()))

# Usage
injector = ExampleInjector()

# When user asks to search for plastic
task = 'material_search'
category = 'plastics'

example = injector.get_relevant_example(task, category)

# Inject into prompt
prompt = f"""
You need to search for plastic material in ecoinvent.

Here's a similar example:
{example}

Now search for: {{user_requested_material}}
"""
```

---

## 5. Memory Systems

### 5.1 Short-Term Working Memory

```python
"""
Short-term memory for active task
"""

class WorkingMemory:
    """
    Manage short-term working memory for current task
    """

    def __init__(self, capacity=7):  # Miller's Law: 7±2 items
        self.capacity = capacity
        self.items = []

    def add(self, key, value, priority=3):
        """
        Add item to working memory

        Args:
            key: Item identifier
            value: Item content
            priority: 1 (highest) to 5 (lowest)
        """

        item = {
            'key': key,
            'value': value,
            'priority': priority,
            'timestamp': datetime.now()
        }

        # Check if already exists
        existing_idx = next(
            (i for i, item in enumerate(self.items) if item['key'] == key),
            None
        )

        if existing_idx is not None:
            # Update existing
            self.items[existing_idx] = item
        else:
            # Add new
            self.items.append(item)

            # If over capacity, remove lowest priority oldest item
            if len(self.items) > self.capacity:
                # Sort by priority (high to low), then timestamp (old to new)
                self.items.sort(key=lambda x: (x['priority'], x['timestamp']))

                # Remove lowest priority oldest
                removed = self.items.pop(-1)
                print(f"Working memory full, removed: {removed['key']}")

    def get(self, key):
        """Retrieve from working memory"""
        item = next((i for i in self.items if i['key'] == key), None)
        return item['value'] if item else None

    def clear(self):
        """Clear working memory"""
        self.items = []

    def get_active_items(self):
        """Get all active items, sorted by priority"""
        return sorted(self.items, key=lambda x: x['priority'])

# Usage
working_mem = WorkingMemory(capacity=5)

# Add current task items
working_mem.add('current_material', 'PET granulate', priority=1)
working_mem.add('current_search_keywords', ['PET', 'granulate'], priority=2)
working_mem.add('last_search_result', [...], priority=3)
working_mem.add('retry_count', 2, priority=4)
working_mem.add('alternative_keywords', [...], priority=5)

# Add one more (exceeds capacity)
working_mem.add('debug_info', {...}, priority=5)
# Output: "Working memory full, removed: alternative_keywords"

# Retrieve critical item
material = working_mem.get('current_material')
print(material)  # "PET granulate"
```

### 5.2 Long-Term Persistent Memory

```python
"""
Long-term memory persisted across sessions
"""

import json
import os

class PersistentMemory:
    """
    Long-term memory storage for workflow history
    """

    def __init__(self, storage_path='./lca_memory.json'):
        self.storage_path = storage_path
        self.memory = self._load()

    def _load(self):
        """Load memory from disk"""
        if os.path.exists(self.storage_path):
            with open(self.storage_path, 'r') as f:
                return json.load(f)
        else:
            return {
                'workflows': {},
                'common_materials': {},
                'learned_patterns': [],
                'user_preferences': {}
            }

    def _save(self):
        """Save memory to disk"""
        with open(self.storage_path, 'w') as f:
            json.dump(self.memory, f, indent=2, default=str)

    def remember_workflow(self, workflow_id, workflow_data):
        """Remember completed workflow"""
        self.memory['workflows'][workflow_id] = {
            'timestamp': datetime.now().isoformat(),
            'functional_unit': workflow_data.get('functional_unit'),
            'materials_used': workflow_data.get('materials'),
            'result_summary': workflow_data.get('results'),
            'success': workflow_data.get('success', True)
        }
        self._save()

    def remember_material(self, material_name, flow_id, provider_id, search_keywords):
        """Remember successful material searches"""
        if material_name not in self.memory['common_materials']:
            self.memory['common_materials'][material_name] = []

        self.memory['common_materials'][material_name].append({
            'flow_id': flow_id,
            'provider_id': provider_id,
            'keywords': search_keywords,
            'timestamp': datetime.now().isoformat()
        })

        # Keep only most recent 3 searches per material
        self.memory['common_materials'][material_name] = \
            self.memory['common_materials'][material_name][-3:]

        self._save()

    def recall_material(self, material_name):
        """Recall previously found material"""
        if material_name in self.memory['common_materials']:
            # Return most recent
            return self.memory['common_materials'][material_name][-1]
        else:
            return None

    def learn_pattern(self, pattern_description, example):
        """Learn from successful workflows"""
        self.memory['learned_patterns'].append({
            'pattern': pattern_description,
            'example': example,
            'learned_at': datetime.now().isoformat()
        })

        # Keep only last 20 patterns
        self.memory['learned_patterns'] = self.memory['learned_patterns'][-20:]

        self._save()

    def set_preference(self, key, value):
        """Remember user preferences"""
        self.memory['user_preferences'][key] = value
        self._save()

    def get_preference(self, key, default=None):
        """Get user preference"""
        return self.memory['user_preferences'].get(key, default)

# Usage
long_term_mem = PersistentMemory()

# Remember successful material search
long_term_mem.remember_material(
    'PET bottle grade',
    flow_id='abc-123',
    provider_id='prov-456',
    search_keywords=['polyethylene', 'terephthalate', 'granulate', 'bottle']
)

# Later session: Recall material
pet_data = long_term_mem.recall_material('PET bottle grade')
if pet_data:
    print(f"Using cached material: {pet_data['flow_id']}")
    # Skip search, use cached IDs!

# Learn from successful workflow
long_term_mem.learn_pattern(
    'PET bottle production',
    {
        'materials': ['PET', 'HDPE', 'PP'],
        'typical_amounts': {'PET': 0.060, 'HDPE': 0.004, 'PP': 0.001}
    }
)

# Set user preferences
long_term_mem.set_preference('default_impact_method', 'TRACI 2.1')
long_term_mem.set_preference('default_region', 'RER')

# Use preferences
preferred_method = long_term_mem.get_preference('default_impact_method')
```

### 5.3 Episodic Memory (Case-Based Reasoning)

```python
"""
Remember and reuse past similar cases
"""

class EpisodicMemory:
    """
    Case-based reasoning for LCA workflows
    """

    def __init__(self):
        self.cases = []

    def store_case(self, problem, solution, outcome):
        """
        Store successful case

        Args:
            problem: Problem description (tags, parameters)
            solution: Solution steps taken
            outcome: Result and performance metrics
        """

        case = {
            'problem': problem,
            'solution': solution,
            'outcome': outcome,
            'timestamp': datetime.now(),
            'reuse_count': 0
        }

        self.cases.append(case)

    def find_similar_case(self, current_problem, similarity_threshold=0.7):
        """
        Find most similar past case

        Args:
            current_problem: Current problem description
            similarity_threshold: Minimum similarity (0-1)
        """

        if not self.cases:
            return None

        # Calculate similarity for each case
        similarities = []

        for case in self.cases:
            similarity = self._calculate_similarity(
                current_problem,
                case['problem']
            )
            similarities.append((case, similarity))

        # Get most similar
        best_case, best_similarity = max(similarities, key=lambda x: x[1])

        if best_similarity >= similarity_threshold:
            best_case['reuse_count'] += 1
            return {
                'case': best_case,
                'similarity': best_similarity,
                'adaptation_needed': best_similarity < 0.9
            }
        else:
            return None

    def _calculate_similarity(self, problem1, problem2):
        """
        Calculate similarity between two problems

        Uses tag overlap and parameter similarity
        """

        # Tag similarity (Jaccard)
        tags1 = set(problem1.get('tags', []))
        tags2 = set(problem2.get('tags', []))

        if not tags1 and not tags2:
            tag_similarity = 1.0
        elif not tags1 or not tags2:
            tag_similarity = 0.0
        else:
            intersection = tags1.intersection(tags2)
            union = tags1.union(tags2)
            tag_similarity = len(intersection) / len(union)

        # Parameter similarity
        params1 = problem1.get('parameters', {})
        params2 = problem2.get('parameters', {})

        common_params = set(params1.keys()).intersection(set(params2.keys()))

        if not common_params:
            param_similarity = 0.0
        else:
            param_matches = sum(
                1 for p in common_params
                if params1[p] == params2[p]
            )
            param_similarity = param_matches / len(common_params)

        # Combined similarity (70% tags, 30% params)
        total_similarity = 0.7 * tag_similarity + 0.3 * param_similarity

        return total_similarity

# Usage
episodic_mem = EpisodicMemory()

# Store successful case
episodic_mem.store_case(
    problem={
        'tags': ['plastic', 'bottle', 'beverage', 'pet'],
        'parameters': {
            'material_type': 'plastic',
            'product_category': 'packaging',
            'functional_unit_type': 'mass'
        }
    },
    solution={
        'materials_searched': ['PET', 'HDPE', 'PP'],
        'search_strategy': 'hierarchical',
        'processes_created': 3,
        'calculation_method': 'TRACI 2.1'
    },
    outcome={
        'success': True,
        'duration_seconds': 45,
        'gwp_result': 0.0234
    }
)

# Later: Find similar case
new_problem = {
    'tags': ['plastic', 'bottle', 'water', 'pet'],
    'parameters': {
        'material_type': 'plastic',
        'product_category': 'packaging',
        'functional_unit_type': 'mass'
    }
}

similar_case = episodic_mem.find_similar_case(new_problem)

if similar_case:
    print(f"Found similar case (similarity: {similar_case['similarity']:.2f})")
    print(f"Reusing solution strategy: {similar_case['case']['solution']}")

    if similar_case['adaptation_needed']:
        print("Adapting solution for current problem...")
    else:
        print("Using solution as-is")
```

---

## 6. Context-Aware Prompting

### 6.1 Dynamic Prompt Construction

```python
"""
Build prompts dynamically based on available context
"""

class DynamicPromptBuilder:
    """
    Construct prompts with appropriate context
    """

    def __init__(self, base_prompt, max_tokens=4000):
        self.base_prompt = base_prompt
        self.max_tokens = max_tokens

    def build_prompt(self, task, context_elements, priority_order):
        """
        Build prompt with prioritized context

        Args:
            task: Current task description
            context_elements: Dict of available context
            priority_order: List of context keys in priority order
        """

        # Start with base prompt
        prompt_parts = [self.base_prompt]
        token_count = self._estimate_tokens(self.base_prompt)

        # Add task
        task_section = f"\nCurrent Task:\n{task}\n"
        prompt_parts.append(task_section)
        token_count += self._estimate_tokens(task_section)

        # Add context in priority order
        context_section = "\nRelevant Context:\n"
        context_added = []

        for key in priority_order:
            if key in context_elements:
                context_item = f"{key}:\n{context_elements[key]}\n\n"
                item_tokens = self._estimate_tokens(context_item)

                if token_count + item_tokens <= self.max_tokens:
                    context_section += context_item
                    token_count += item_tokens
                    context_added.append(key)
                else:
                    # Try compressed version
                    compressed = self._compress_context(context_elements[key])
                    compressed_item = f"{key} (summarized):\n{compressed}\n\n"
                    compressed_tokens = self._estimate_tokens(compressed_item)

                    if token_count + compressed_tokens <= self.max_tokens:
                        context_section += compressed_item
                        token_count += compressed_tokens
                        context_added.append(f"{key} (compressed)")

        prompt_parts.append(context_section)

        # Final prompt
        final_prompt = "".join(prompt_parts)

        return {
            'prompt': final_prompt,
            'total_tokens': token_count,
            'context_included': context_added
        }

    @staticmethod
    def _estimate_tokens(text):
        """Estimate tokens (rough: 4 chars ≈ 1 token)"""
        return len(str(text)) // 4

    @staticmethod
    def _compress_context(context):
        """Compress context to essentials"""
        if isinstance(context, dict):
            # Keep only IDs and names
            return {
                k: v for k, v in context.items()
                if k in ['id', 'name', 'amount', 'unit']
            }
        elif isinstance(context, str):
            # Truncate long strings
            return context[:200] + "..." if len(context) > 200 else context
        else:
            return str(context)[:100]

# Usage
builder = DynamicPromptBuilder(
    base_prompt="You are an LCA specialist. Use available context to complete the task.",
    max_tokens=4000
)

task = "Calculate environmental impacts for PET bottle system"

context_elements = {
    'functional_unit': '1 filled PET bottle (1.065 kg)',
    'system_boundary': 'cradle-to-gate',
    'materials': {
        'PET': {'id': 'abc-123', 'provider': 'prov-456', 'amount': 0.060},
        'HDPE': {'id': 'def-789', 'provider': 'prov-012', 'amount': 0.004}
    },
    'processes_created': [...long list...],
    'search_history': [...very long...],
    'impact_method': {'id': 'traci-id', 'name': 'TRACI 2.1'}
}

priority_order = [
    'functional_unit',  # Highest priority
    'system_boundary',
    'impact_method',
    'materials',
    'processes_created',
    'search_history'  # Lowest priority (may be dropped)
]

result = builder.build_prompt(task, context_elements, priority_order)

print(f"Prompt tokens: {result['total_tokens']}")
print(f"Context included: {result['context_included']}")
```

### 6.2 Context-Conditioned Generation

```python
"""
Adjust generation parameters based on context
"""

class ContextConditionedGeneration:
    """
    Adapt generation strategy based on context state
    """

    @staticmethod
    def get_generation_config(context_state):
        """
        Get generation config based on context

        Context states:
        - information_rich: Lots of context available
        - information_sparse: Limited context
        - uncertain: Conflicting or ambiguous context
        - routine: Standard, well-known task
        """

        configs = {
            'information_rich': {
                'temperature': 0.3,  # Low temp, stick to facts
                'top_p': 0.8,
                'reasoning': 'Detailed context allows precise generation'
            },
            'information_sparse': {
                'temperature': 0.7,  # Higher temp for exploration
                'top_p': 0.9,
                'reasoning': 'Limited context requires broader exploration'
            },
            'uncertain': {
                'temperature': 0.5,  # Moderate
                'top_p': 0.85,
                'reasoning': 'Balance between exploration and consistency'
            },
            'routine': {
                'temperature': 0.2,  # Very low, deterministic
                'top_p': 0.75,
                'reasoning': 'Standard task, prefer established patterns'
            }
        }

        return configs.get(context_state, configs['uncertain'])

    @staticmethod
    def determine_context_state(context_score, task_novelty):
        """
        Determine context state

        Args:
            context_score: Quality/completeness of context (0-1)
            task_novelty: How novel is the task (0-1)
        """

        if context_score > 0.8 and task_novelty < 0.3:
            return 'routine'
        elif context_score > 0.7:
            return 'information_rich'
        elif context_score < 0.4:
            return 'information_sparse'
        else:
            return 'uncertain'

# Usage
# After assessing context...
context_score = 0.85  # High quality context
task_novelty = 0.2  # Standard PET bottle assessment

state = ContextConditionedGeneration.determine_context_state(
    context_score,
    task_novelty
)

config = ContextConditionedGeneration.get_generation_config(state)

print(f"Context state: {state}")
print(f"Generation config: {config}")
# Output:
# Context state: routine
# Generation config: {'temperature': 0.2, 'top_p': 0.75, ...}
```

---

## 7. Optimization Patterns

### 7.1 Lazy Context Loading

```python
"""
Load context only when actually needed
"""

class LazyContext:
    """
    Lazy-load context to save tokens
    """

    def __init__(self):
        self.context_loaders = {}
        self.loaded_context = {}

    def register_loader(self, context_key, loader_func):
        """
        Register lazy loader for context

        Args:
            context_key: Context identifier
            loader_func: Function that loads context when called
        """

        self.context_loaders[context_key] = loader_func

    def get_context(self, context_key):
        """
        Get context (load if not already loaded)
        """

        # Check if already loaded
        if context_key in self.loaded_context:
            print(f"Using cached context: {context_key}")
            return self.loaded_context[context_key]

        # Load if loader registered
        if context_key in self.context_loaders:
            print(f"Loading context: {context_key}")
            context = self.context_loaders[context_key]()
            self.loaded_context[context_key] = context
            return context

        return None

    def preload(self, context_keys):
        """Preload specific contexts"""
        for key in context_keys:
            self.get_context(key)

    def unload(self, context_key):
        """Unload context to free memory"""
        if context_key in self.loaded_context:
            del self.loaded_context[context_key]
            print(f"Unloaded context: {context_key}")

# Usage
lazy = LazyContext()

# Register loaders (don't load yet)
lazy.register_loader(
    'material_properties',
    lambda: expensive_database_query_for_material_properties()
)

lazy.register_loader(
    'impact_method_details',
    lambda: load_impact_method_documentation()
)

lazy.register_loader(
    'historical_analyses',
    lambda: query_past_workflows_database()
)

# Later: Load only if needed
# If agent needs material properties:
properties = lazy.get_context('material_properties')  # Loads now

# If agent doesn't need historical analyses, never loaded!
# Saves tokens!
```

### 7.2 Progressive Context Refinement

```python
"""
Start with coarse context, refine as needed
"""

class ProgressiveContext:
    """
    Progressively refine context detail level
    """

    def __init__(self):
        self.context_levels = {
            'overview': 1,
            'summary': 2,
            'detailed': 3,
            'comprehensive': 4
        }
        self.current_level = 1

    def get_context_at_level(self, data, level):
        """
        Get context at specified detail level

        Levels:
        1. Overview: Just IDs and names
        2. Summary: + Key parameters
        3. Detailed: + Full specifications
        4. Comprehensive: + Metadata, alternatives, history
        """

        if level == 1:  # Overview
            return self._overview(data)
        elif level == 2:  # Summary
            return self._summary(data)
        elif level == 3:  # Detailed
            return self._detailed(data)
        elif level == 4:  # Comprehensive
            return data  # Full data

    def _overview(self, data):
        """Minimal context: IDs and names only"""
        if isinstance(data, dict):
            return {
                k: v for k, v in data.items()
                if k in ['id', 'name']
            }
        elif isinstance(data, list):
            return [self._overview(item) for item in data[:5]]  # Max 5 items
        else:
            return str(data)[:50]  # Truncate

    def _summary(self, data):
        """Summary: Add key parameters"""
        if isinstance(data, dict):
            return {
                k: v for k, v in data.items()
                if k in ['id', 'name', 'amount', 'unit', 'provider_id']
            }
        elif isinstance(data, list):
            return [self._summary(item) for item in data[:10]]
        else:
            return str(data)[:100]

    def _detailed(self, data):
        """Detailed: Full specification"""
        if isinstance(data, dict):
            # Exclude only metadata and history
            return {
                k: v for k, v in data.items()
                if k not in ['metadata', 'history', 'alternatives']
            }
        elif isinstance(data, list):
            return [self._detailed(item) for item in data[:20]]
        else:
            return data

    def refine_if_needed(self, data, task_success):
        """
        Refine context if task failed

        Strategy: If task fails, provide more detailed context
        """

        if not task_success and self.current_level < 4:
            self.current_level += 1
            print(f"Task failed, refining context to level {self.current_level}")
            return self.get_context_at_level(data, self.current_level)
        else:
            return self.get_context_at_level(data, self.current_level)

# Usage
progressive = ProgressiveContext()

material_data = {
    'id': 'abc-123',
    'name': 'PET granulate bottle grade',
    'amount': 0.060,
    'unit': 'kg',
    'provider_id': 'prov-456',
    'provider_name': 'Very long provider name...',
    'category': 'plastics/polymers',
    'alternatives': [...large list...],
    'metadata': {...},
    'history': [...]
}

# Start with overview
context_v1 = progressive.get_context_at_level(material_data, level=1)
print("Level 1 (overview):", context_v1)
# Output: {'id': 'abc-123', 'name': 'PET granulate bottle grade'}

# Task fails, refine
context_v2 = progressive.refine_if_needed(material_data, task_success=False)
print("Level 2 (summary):", context_v2)
# Output: {'id': 'abc-123', 'name': 'PET granulate...', 'amount': 0.060, ...}
```

---

## Conclusion

Effective context engineering is essential for reliable LCA automation with AI agents. Key strategies include:

**Context Management:**
- ✅ Budget token allocation strategically
- ✅ Prioritize critical context (functional unit, system boundary)
- ✅ Manage context lifecycle (create → activate → archive → dispose)

**Compression:**
- ✅ Compress using structured summarization
- ✅ Send differential updates (only changes)
- ✅ Prune irrelevant branches hierarchically

**Memory Systems:**
- ✅ Working memory for active tasks (7±2 items)
- ✅ Long-term memory for reuse across sessions
- ✅ Episodic memory for case-based reasoning

**Optimization:**
- ✅ Lazy-load context only when needed
- ✅ Progressive refinement (coarse → detailed)
- ✅ Attention-based context selection

**Best Practices:**
1. Always maintain critical context (functional unit, boundaries)
2. Compress historical data aggressively
3. Cache frequently accessed information
4. Use templates for common scenarios
5. Monitor token usage continuously

For implementation examples, see:
- [Multi-Agent Prompt Engineering](MULTI_AGENT_PROMPT_ENGINEERING.md)
- [Case Studies](CASE_STUDY_PET_PC.md)
- [Test Examples](CLIENT_TEST_EXAMPLES.md)

---

**Last Updated:** 2025-12-04
**Version:** 1.0
**Status:** Production Ready
