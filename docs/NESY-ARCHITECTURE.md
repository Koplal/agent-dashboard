# Neurosymbolic Architecture (v2.6.0)

Comprehensive documentation for the 9 neurosymbolic modules in the experiment/neuro-symbolic branch.

## Table of Contents

1. [Overview](#overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Module Descriptions](#module-descriptions)
   - [NESY-001: Output Validators](#nesy-001-output-validators)
   - [NESY-002: Grammar Constraints](#nesy-002-grammar-constraints)
   - [NESY-003: Heterogeneous Judges](#nesy-003-heterogeneous-judges)
   - [NESY-004: Knowledge Graph](#nesy-004-knowledge-graph)
   - [NESY-005: Z3 Verification](#nesy-005-z3-verification)
   - [NESY-006: Progress Ledger](#nesy-006-progress-ledger)
   - [NESY-007: Formal Specifications](#nesy-007-formal-specifications)
   - [NESY-008: Neurosymbolic Learning](#nesy-008-neurosymbolic-learning)
   - [NESY-009: Audit Trail](#nesy-009-audit-trail)
4. [Dependencies](#dependencies)
5. [Configuration](#configuration)
6. [Integration Patterns](#integration-patterns)
7. [Testing](#testing)

---

## Overview

The neurosymbolic (NESY) modules bridge neural language models with symbolic reasoning systems, providing:

- **Formal Verification**: Prove properties about agent behavior using Z3 SMT solver
- **Structured Outputs**: Enforce schemas and grammars on LLM outputs
- **Knowledge Management**: Build and query knowledge graphs from research
- **Learning from Experience**: Extract and apply rules from successful executions
- **Compliance**: Tamper-evident audit trails for regulatory requirements

### Design Principles

1. **Graceful Degradation**: All modules work without optional dependencies
2. **Separation of Concerns**: Each module handles one aspect of verification/learning
3. **Composability**: Modules can be used independently or combined
4. **Observable**: All operations are logged for debugging and audit

---

## Architecture Diagram

```
                              ┌─────────────────────────────────────┐
                              │         Agent Orchestrator          │
                              └──────────────────┬──────────────────┘
                                                 │
                    ┌────────────────────────────┼────────────────────────────┐
                    │                            │                            │
                    ▼                            ▼                            ▼
    ┌───────────────────────┐    ┌───────────────────────┐    ┌───────────────────────┐
    │   NESY-007            │    │   NESY-001            │    │   NESY-002            │
    │   Specifications      │    │   Validators          │    │   Constraints         │
    │   ─────────────       │    │   ──────────          │    │   ───────────         │
    │   • DSL Parser        │    │   • Pydantic schemas  │    │   • Tool schemas      │
    │   • AST Builder       │    │   • Retry prompts     │    │   • Grammar enforce   │
    │   • Limit Enforcer    │    │   • Field validation  │    │   • Outlines support  │
    └───────────┬───────────┘    └───────────┬───────────┘    └───────────┬───────────┘
                │                            │                            │
                └────────────────────────────┼────────────────────────────┘
                                             │
                                             ▼
                              ┌─────────────────────────────────────┐
                              │        LLM Execution Layer          │
                              └──────────────────┬──────────────────┘
                                                 │
                    ┌────────────────────────────┼────────────────────────────┐
                    │                            │                            │
                    ▼                            ▼                            ▼
    ┌───────────────────────┐    ┌───────────────────────┐    ┌───────────────────────┐
    │   NESY-003            │    │   NESY-005            │    │   NESY-004            │
    │   Judge Panel         │    │   Z3 Verifier         │    │   Knowledge Graph     │
    │   ───────────         │    │   ───────────         │    │   ───────────────     │
    │   • Multi-judge       │    │   • SMT solving       │    │   • Entity storage    │
    │   • Consensus         │    │   • Claim classify    │    │   • Semantic search   │
    │   • Weighted voting   │    │   • Hybrid verify     │    │   • Contradictions    │
    └───────────┬───────────┘    └───────────┬───────────┘    └───────────┬───────────┘
                │                            │                            │
                └────────────────────────────┼────────────────────────────┘
                                             │
                                             ▼
                              ┌─────────────────────────────────────┐
                              │      Post-Execution Processing      │
                              └──────────────────┬──────────────────┘
                                                 │
                    ┌────────────────────────────┼────────────────────────────┐
                    │                            │                            │
                    ▼                            ▼                            ▼
    ┌───────────────────────┐    ┌───────────────────────┐    ┌───────────────────────┐
    │   NESY-006            │    │   NESY-008            │    │   NESY-009            │
    │   Progress Ledger     │    │   Learning            │    │   Audit Trail         │
    │   ───────────────     │    │   ────────            │    │   ───────────         │
    │   • Task lifecycle    │    │   • Rule extraction   │    │   • Hash chains       │
    │   • Loop detection    │    │   • Effectiveness     │    │   • Compliance        │
    │   • Metrics           │    │   • Semantic match    │    │   • Query engine      │
    └───────────────────────┘    └───────────────────────┘    └───────────────────────┘
```

---

## Module Descriptions

### NESY-001: Output Validators

**Location:** `src/validators/`

Validates LLM outputs against Pydantic schemas with automatic retry prompt generation.

#### Key Classes

```python
from src.validators import (
    OutputValidator,      # Main validator class
    ValidationResult,     # Validation result with errors
    create_pydantic_schema,  # Create schema from dict
    SchemaRegistry,       # Registry for reusable schemas
)
```

#### Example Usage

```python
from pydantic import BaseModel, Field
from src.validators import OutputValidator

class ResearchFinding(BaseModel):
    claim: str = Field(description="The main claim being made")
    confidence: float = Field(ge=0.0, le=1.0)
    sources: list[str] = Field(min_length=1)

validator = OutputValidator(schema=ResearchFinding)

# Validate LLM output
result = validator.validate(llm_output_text)

if not result.valid:
    # Get structured retry prompt
    retry_prompt = result.get_retry_prompt()
    print(f"Validation errors: {result.errors}")
```

#### Features

- **Pydantic V2 Support**: Full support for Pydantic V2 validators
- **Nested Schemas**: Validates deeply nested structures
- **Retry Prompts**: Generates specific prompts to fix validation errors
- **JSON Schema Export**: Export schemas for documentation

---

### NESY-002: Grammar Constraints

**Location:** `src/constraints/`

Enforces grammar constraints on LLM outputs using Claude's tool_use feature or Outlines library.

#### Key Classes

```python
from src.constraints import (
    ConstraintEnforcer,   # Enforce output constraints
    ToolSchemaRegistry,   # Registry for tool schemas
    GrammarConstraint,    # Define grammar constraints
)
```

#### Example Usage

```python
from src.constraints import ConstraintEnforcer, ToolSchemaRegistry

# Register tool schemas
registry = ToolSchemaRegistry()
registry.register("search_result", {
    "type": "object",
    "properties": {
        "query": {"type": "string"},
        "results": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["query", "results"]
})

# Enforce constraints via tool_use
enforcer = ConstraintEnforcer(registry)
result = enforcer.enforce(
    llm_client,
    prompt="Search for Python tutorials",
    output_schema="search_result"
)
```

#### Features

- **Claude tool_use**: Native schema enforcement via Anthropic API
- **Outlines Integration**: Optional local model grammar constraints
- **Schema Registry**: Reusable schema definitions
- **Fallback Modes**: Graceful degradation without Outlines

---

### NESY-003: Heterogeneous Judges

**Location:** `src/judges/`

Multi-judge evaluation system with diversified judge configurations and consensus calculation.

#### Key Classes

```python
from src.judges import (
    HeterogeneousPanel,   # Panel orchestrator
    JudgeConfig,          # Judge configuration
    JudgeType,            # Judge type enum
    ConsensusResult,      # Aggregated verdict
)
```

#### Example Usage

```python
from src.judges import HeterogeneousPanel, JudgeConfig, JudgeType

# Configure diverse judges
panel = HeterogeneousPanel(judges=[
    JudgeConfig(JudgeType.ADVERSARIAL, weight=1.5),
    JudgeConfig(JudgeType.RUBRIC, rubric=custom_rubric),
    JudgeConfig(JudgeType.DOMAIN_EXPERT, domain="security"),
    JudgeConfig(JudgeType.SKEPTIC, skepticism_level=0.8),
    JudgeConfig(JudgeType.END_USER),
])

# Evaluate work product
result = await panel.evaluate(
    subject="Authentication redesign proposal",
    content=proposal_document
)

print(f"Verdict: {result.verdict}")
print(f"Consensus: {result.consensus_level:.0%}")
for judge_id, score in result.scores.items():
    print(f"  {judge_id}: {score.verdict} ({score.score}/10)")
```

#### Judge Types

| Type | Description |
|------|-------------|
| `ADVERSARIAL` | Stress-tests and attacks proposals |
| `RUBRIC` | Scores against custom rubric |
| `DOMAIN_EXPERT` | Domain-specific expertise |
| `SKEPTIC` | Questions assumptions |
| `END_USER` | User perspective evaluation |

---

### NESY-004: Knowledge Graph

**Location:** `src/knowledge/`

SQLite-backed knowledge graph with entity extraction, semantic search, and contradiction detection.

#### Key Classes

```python
from src.knowledge import (
    KnowledgeGraph,       # Main graph class
    ClaimStore,           # Claim storage backend
    Entity,               # Entity representation
    Claim,                # Claim with provenance
    Relationship,         # Entity relationship
)
```

#### Example Usage

```python
from src.knowledge import KnowledgeGraph

# Create or open knowledge graph
kg = KnowledgeGraph("./research_kb.db")

# Add entities and claims
python_entity = kg.add_entity("Python", entity_type="programming_language")
kg.add_claim(
    "Python 3.12 introduced pattern matching",
    source="python.org",
    confidence=0.95,
    related_entities=[python_entity.id]
)

# Semantic search
results = kg.search("pattern matching features", limit=10)

# Find contradictions
contradictions = kg.find_contradictions()
for c1, c2, reason in contradictions:
    print(f"Contradiction: '{c1.text}' vs '{c2.text}'")
    print(f"  Reason: {reason}")
```

#### Features

- **FTS5 Search**: SQLite full-text search for efficient querying
- **Embedding Support**: Optional semantic embeddings for similarity
- **Provenance Tracking**: Source and confidence for all claims
- **Relationship Modeling**: Entity-to-entity relationships

---

### NESY-005: Z3 Verification

**Location:** `src/verification/`

Formal verification using Z3 SMT solver with hybrid symbolic/LLM evaluation.

#### Key Classes

```python
from src.verification import (
    Z3Verifier,           # Pure Z3 verification
    HybridVerifier,       # Z3 + LLM verification
    ClaimClassifier,      # Classify claim types
    VerificationResult,   # Verification outcome
)
```

#### Example Usage

```python
from src.verification import HybridVerifier, ClaimClassifier

# Classify claims by verifiability
classifier = ClaimClassifier()
claim_type = classifier.classify("x + y = y + x")
# Returns: ClaimType.MATHEMATICAL

# Hybrid verification
verifier = HybridVerifier(llm_client=client)

result = await verifier.verify([
    "All prime numbers greater than 2 are odd",  # Provable by Z3
    "Python is the most popular language",       # Needs LLM (empirical)
])

for claim, outcome in result.items():
    print(f"{claim}: {outcome.verdict}")
    if outcome.proof:
        print(f"  Proof: {outcome.proof}")
```

#### Claim Classification

| Type | Verification Method |
|------|-------------------|
| `LOGICAL` | Z3 propositional logic |
| `MATHEMATICAL` | Z3 arithmetic solver |
| `EMPIRICAL` | LLM + knowledge base |
| `DEFINITIONAL` | Schema validation |

---

### NESY-006: Progress Ledger

**Location:** `src/ledger/`

Task lifecycle tracking with loop detection and runtime metrics.

#### Key Classes

```python
from src.ledger import (
    ProgressLedger,       # Main ledger class
    TaskEntry,            # Task record
    TaskStatus,           # Status enum
    LoopDetector,         # Detect stuck loops
)
```

#### Example Usage

```python
from src.ledger import ProgressLedger, TaskStatus

ledger = ProgressLedger("./progress.db")

# Track task lifecycle
task_id = ledger.create_task(
    name="Research authentication methods",
    agent="researcher",
    parent_task=None
)

ledger.update_status(task_id, TaskStatus.ACTIVE)
ledger.log_progress(task_id, "Found 3 relevant papers")

# Check for loops
loops = ledger.detect_loops(task_id)
if loops:
    print(f"Warning: Task appears stuck in loop: {loops}")

# Complete task
ledger.update_status(task_id, TaskStatus.COMPLETED, result=findings)

# Get metrics
metrics = ledger.get_metrics(task_id)
print(f"Duration: {metrics.duration}s, Steps: {metrics.step_count}")
```

---

### NESY-007: Formal Specifications

**Location:** `src/specifications/`

Custom DSL for agent behavior constraints with AST representation and runtime enforcement.

#### Key Classes

```python
from src.specifications import (
    SpecificationParser,  # Parse .spec files
    Specification,        # Parsed specification
    SpecificationEnforcedAgent,  # Wrapper with enforcement
    LimitViolation,       # Violation exception
)
```

#### Specification DSL

```
# Example: specs/researcher.spec
agent researcher {
    description: "Research agent with web access"
    model: sonnet

    limits {
        timeout: 300        # 5 minutes max
        tool_calls: 50      # Max tool invocations
        iterations: 10      # Max retry loops
    }

    constraints {
        ALWAYS cite_sources
        ALWAYS verify_claims
        NEVER fabricate_data
        NEVER access_restricted
    }

    tools {
        allow: WebSearch, WebFetch, Read, Grep
        deny: Write, Edit, Bash
    }

    output {
        schema: ResearchOutput
        required_fields: [summary, sources, confidence]
    }
}
```

#### Example Usage

```python
from src.specifications import SpecificationParser, SpecificationEnforcedAgent

# Parse specification
parser = SpecificationParser()
spec = parser.parse_file("specs/researcher.spec")

# Wrap agent with enforcement
wrapped = SpecificationEnforcedAgent(
    agent=my_researcher_agent,
    specification=spec
)

try:
    result = wrapped.run(task="Research quantum computing trends")
except LimitViolation as e:
    print(f"Agent exceeded limits: {e.limit_type} = {e.actual_value}")
```

---

### NESY-008: Neurosymbolic Learning

**Location:** `src/learning/`

Extract and apply rules from successful executions with Bayesian effectiveness tracking.

#### Key Classes

```python
from src.learning import (
    LearningOrchestrator,  # Main orchestrator
    RuleExtractor,         # Extract rules from executions
    RuleStore,             # SQLite/memory rule storage
    ExtractedRule,         # Rule representation
    ExecutionOutcome,      # Execution result
)
```

#### Example Usage

```python
from src.learning import LearningOrchestrator, RuleStore

# Create learning system
store = RuleStore("./learned_rules.db")
orchestrator = LearningOrchestrator(store=store, llm_client=client)

# Record successful execution
outcome = ExecutionOutcome(
    task_type="code_review",
    success=True,
    context={"language": "python", "complexity": "high"},
    actions=execution_trace,
    result=review_output
)

# Extract rules from success
new_rules = await orchestrator.learn_from(outcome)
print(f"Extracted {len(new_rules)} new rules")

# Apply learned rules to new task
applicable_rules = store.find_applicable(
    task_type="code_review",
    context={"language": "python"}
)

for rule in applicable_rules:
    print(f"Rule: {rule.condition} -> {rule.action}")
    print(f"  Effectiveness: {rule.effectiveness:.0%}")
```

#### Features

- **Bayesian Updates**: Rule effectiveness improves with usage
- **Semantic Matching**: Find rules by meaning, not just keywords
- **Automatic Pruning**: Remove low-effectiveness rules
- **Export/Import**: Share learned rules between instances

---

### NESY-009: Audit Trail

**Location:** `src/audit/`

Tamper-evident audit logging with hash chaining and compliance reporting.

#### Key Classes

```python
from src.audit import (
    AuditTrail,           # Main audit class
    AuditEntry,           # Single audit entry
    ComplianceReporter,   # Generate compliance reports
    AuditQuery,           # Query builder
)
```

#### Example Usage

```python
from src.audit import AuditTrail, ComplianceReporter
from datetime import datetime, timedelta

# Create audit trail
trail = AuditTrail(storage_path="./audit.db")

# Log events
trail.log("task_started", {
    "task_id": "task-123",
    "agent": "researcher",
    "description": "Research security protocols"
})

trail.log("decision_made", {
    "task_id": "task-123",
    "decision": "approve",
    "rationale": "Passed all verification checks"
})

# Verify chain integrity
is_valid, invalid_entries = trail.verify_chain()
if not is_valid:
    print(f"Tampering detected in {len(invalid_entries)} entries!")

# Generate compliance report
reporter = ComplianceReporter(trail)
report = reporter.generate(
    start_date=datetime.now() - timedelta(days=30),
    end_date=datetime.now(),
    include_details=True
)

print(f"Total events: {report.total_events}")
print(f"Decision events: {report.decision_count}")
print(f"Chain integrity: {'Valid' if report.chain_valid else 'INVALID'}")
```

---

## Dependencies

### Required (Core)

```
pydantic>=2.0.0     # Schema validation
```

### Optional (Enhanced Features)

```
# NESY-005: Formal verification
z3-solver>=4.12.0

# NESY-007: DSL parsing (recommended)
lark>=1.1.0

# NESY-002/008: Local model constraints
outlines>=0.0.30

# NESY-004: Semantic embeddings
sentence-transformers>=2.2.0
```

### Installation

```bash
# Core only
pip install agent-dashboard

# With all NESY features
pip install agent-dashboard[all]

# Specific extras
pip install agent-dashboard[verification]  # Z3 support
pip install agent-dashboard[learning]      # Learning + embeddings
```

---

## Configuration

### Environment Variables

```bash
# NESY-005: Z3 solver timeout
export NESY_Z3_TIMEOUT=30000  # milliseconds

# NESY-004: Embedding model
export NESY_EMBEDDING_MODEL="all-MiniLM-L6-v2"

# NESY-008: Learning parameters
export NESY_LEARNING_MIN_EFFECTIVENESS=0.3
export NESY_LEARNING_PRUNE_THRESHOLD=0.1

# NESY-009: Audit storage
export NESY_AUDIT_PATH="~/.claude/audit.db"
```

### Programmatic Configuration

```python
from src.nesy_config import NESYConfig

config = NESYConfig(
    z3_timeout_ms=30000,
    embedding_model="all-MiniLM-L6-v2",
    learning_min_effectiveness=0.3,
    audit_storage_path="./audit.db"
)
```

---

## Integration Patterns

### Pattern 1: Validated Research Pipeline

```python
from src.validators import OutputValidator
from src.knowledge import KnowledgeGraph
from src.audit import AuditTrail

# Setup
validator = OutputValidator(schema=ResearchOutput)
kg = KnowledgeGraph("./research.db")
audit = AuditTrail("./audit.db")

async def research_pipeline(query: str):
    audit.log("research_started", {"query": query})

    # Execute research
    raw_output = await researcher_agent.run(query)

    # Validate output
    result = validator.validate(raw_output)
    if not result.valid:
        audit.log("validation_failed", {"errors": result.errors})
        return await retry_with_feedback(result.get_retry_prompt())

    # Store in knowledge graph
    for finding in result.parsed.findings:
        kg.add_claim(finding.claim, source=finding.source)

    audit.log("research_completed", {"findings": len(result.parsed.findings)})
    return result.parsed
```

### Pattern 2: Specification-Enforced Agents

```python
from src.specifications import SpecificationParser, SpecificationEnforcedAgent
from src.ledger import ProgressLedger

parser = SpecificationParser()
ledger = ProgressLedger("./progress.db")

async def run_with_spec(agent, spec_path: str, task: str):
    spec = parser.parse_file(spec_path)
    wrapped = SpecificationEnforcedAgent(agent, spec)

    task_id = ledger.create_task(task, agent=spec.agent_name)

    try:
        ledger.update_status(task_id, TaskStatus.ACTIVE)
        result = await wrapped.run(task)
        ledger.update_status(task_id, TaskStatus.COMPLETED, result=result)
        return result
    except LimitViolation as e:
        ledger.update_status(task_id, TaskStatus.FAILED, error=str(e))
        raise
```

### Pattern 3: Learning from Success

```python
from src.learning import LearningOrchestrator, ExecutionOutcome
from src.verification import HybridVerifier

orchestrator = LearningOrchestrator(store=rule_store, llm_client=client)
verifier = HybridVerifier(llm_client=client)

async def learn_and_apply(task, context):
    # Find applicable rules
    rules = rule_store.find_applicable(task.type, context)

    # Execute with rule guidance
    result = await agent.run(task, rules=rules)

    # Verify result
    verification = await verifier.verify(result.claims)

    if verification.all_valid:
        # Learn from success
        outcome = ExecutionOutcome(
            task_type=task.type,
            success=True,
            context=context,
            actions=result.trace,
            result=result.output
        )
        await orchestrator.learn_from(outcome)

    return result
```

---

## Testing

### Running NESY Tests

```bash
# All NESY tests
python -m pytest tests/test_validators.py tests/test_constraints.py \
  tests/test_judges.py tests/test_knowledge.py tests/test_verification.py \
  tests/test_ledger.py tests/test_specifications.py tests/test_learning.py \
  tests/test_audit.py tests/test_schemas.py -v

# Specific module
python -m pytest tests/test_specifications.py -v

# With coverage
python -m pytest tests/ --cov=src/validators --cov=src/specifications \
  --cov=src/learning --cov-report=html
```

### Test Count by Module

| Module | Tests | Coverage |
|--------|-------|----------|
| NESY-001 Validators | 68 | Schemas, retry, registry |
| NESY-002 Constraints | 52 | Tool schemas, grammar |
| NESY-003 Judges | 48 | Panel, consensus, types |
| NESY-004 Knowledge | 56 | Graph, search, contradictions |
| NESY-005 Verification | 38 | Z3, hybrid, classify |
| NESY-006 Ledger | 45 | Lifecycle, loops, metrics |
| NESY-007 Specifications | 103 | DSL, AST, enforcement |
| NESY-008 Learning | 58 | Extraction, effectiveness |
| NESY-009 Audit | 42 | Hash chains, compliance |
| NESY Schemas | 26 | Output schemas, JSON |
| **Total** | **536** | |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.6.0 | 2025-12-25 | Initial NESY implementation |

---

Built for formal verification and learning in AI workflows.
