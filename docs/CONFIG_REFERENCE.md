# Configuration Reference

Complete reference for all configurable parameters in Agent Dashboard v2.7.0.

## Table of Contents

1. [Hybrid Retrieval](#hybrid-retrieval)
2. [Output Validation](#output-validation)
3. [Audit Trail](#audit-trail)
4. [Knowledge Graph](#knowledge-graph)

---

## Hybrid Retrieval

### HybridRetrieverConfig

Configuration for hybrid vector+graph retrieval.

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `vector_weight` | float | 0.6 | 0.0-inf | Weight for vector similarity score |
| `graph_weight` | float | 0.4 | 0.0-inf | Weight for graph-based score |
| `max_hops` | int | 2 | 1-inf | Maximum hops for graph expansion |
| `min_similarity` | float | 0.3 | 0.0-1.0 | Minimum vector similarity threshold |
| `min_graph_score` | float | 0.1 | 0.0-1.0 | Minimum graph score threshold |
| `temporal_filter` | bool | False | - | Whether to filter by entity validity |
| `as_of` | datetime | None | - | Datetime for temporal filtering (None = current time) |

**Example:**

```python
from src.knowledge.retriever import HybridRetrieverConfig

# Default balanced configuration
config = HybridRetrieverConfig()

# Semantic-focused (for research queries)
semantic_config = HybridRetrieverConfig(
    vector_weight=0.8,
    graph_weight=0.2,
)

# Relationship-focused (for entity queries)
graph_config = HybridRetrieverConfig(
    vector_weight=0.4,
    graph_weight=0.6,
    max_hops=3,
)

# With temporal filtering
temporal_config = HybridRetrieverConfig(
    temporal_filter=True,
    as_of=None,  # Uses current time
)
```

**Validation:**

- `vector_weight` must be >= 0
- `graph_weight` must be >= 0
- `max_hops` must be > 0
- `min_similarity` must be between 0.0 and 1.0
- `min_graph_score` must be between 0.0 and 1.0

---

## Output Validation

### OutputValidator

Configuration for agent output validation.

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `strict_mode` | bool | True | - | If True, reject any unexpected fields |
| `max_error_history` | int | 1000 | 1-inf | Maximum errors to keep in history |
| `retry_budget` | int | 3 | 1-inf | Default retry attempts for validation failures |

**Example:**

```python
from src.validators.output_validator import OutputValidator

# Default strict validation
validator = OutputValidator()

# Lenient validation with more retries
lenient_validator = OutputValidator(
    strict_mode=False,
    retry_budget=5,
)

# Minimal history for memory-constrained environments
minimal_validator = OutputValidator(
    max_error_history=100,
)
```

---

## Audit Trail

### AuditEntry

Audit trail entries are created with the following configuration options.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `entry_id` | str | auto-generated UUID | Unique identifier |
| `timestamp` | datetime | current UTC time | When the decision was made |
| `decision_type` | DecisionType | OUTPUT_GENERATION | Type of decision |
| `confidence_score` | float | 0.0 | Confidence in the decision (0.0-1.0) |

**DecisionType Values:**

- `TASK_ROUTING` - Task routing decisions
- `AGENT_SELECTION` - Agent selection decisions
- `TOOL_INVOCATION` - Tool invocation decisions
- `OUTPUT_GENERATION` - Output generation decisions
- `VERIFICATION` - Verification decisions
- `HUMAN_ESCALATION` - Human escalation decisions
- `RULE_APPLICATION` - Rule application decisions
- `PANEL_SELECTION` - Panel selection decisions
- `JUDGE_VERDICT` - Judge verdict decisions

---

## Knowledge Graph

### SQLiteGraphBackend

Configuration for SQLite-based knowledge graph storage.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `db_path` | str | required | Path to SQLite database file |

**Example:**

```python
from src.knowledge.storage import SQLiteGraphBackend

# Create backend with specified path
backend = SQLiteGraphBackend("~/.claude/knowledge.db")

# Store and retrieve claims
claim_id = backend.store_claim(claim)
retrieved = backend.get_claim(claim_id)
```

### MemoryGraphBackend

In-memory storage for testing (no configuration required).

```python
from src.knowledge.storage import MemoryGraphBackend

# Create in-memory backend
backend = MemoryGraphBackend()
```

---

## Environment Variables

The following environment variables can override defaults:

| Variable | Config | Description |
|----------|--------|-------------|
| `NESY_LOG_LEVEL` | Logging | Logging level (DEBUG, INFO, WARNING, ERROR) |

---

*Auto-generated from codebase. Last updated: v2.7.0*
