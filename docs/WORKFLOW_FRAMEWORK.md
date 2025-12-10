# Multi-Agent TDD Workflow Framework v2.1

This document describes the Test-Driven Development (TDD) workflow framework implemented in the Agent Dashboard for autonomous Claude Code platforms.

> **Version:** 2.1.0
> **Last Updated:** 2025-01-09
> **Agents:** 14 specialized agents across 3 tiers
> **Philosophy:** Test-Driven Development

## TDD Philosophy

The framework implements a strict Test-Driven Development approach:

```
┌─────────────────────────────────────────────────────────────────┐
│                    TDD CORE PRINCIPLES                          │
├─────────────────────────────────────────────────────────────────┤
│  1. Tests define correctness - Code must pass ALL tests         │
│  2. Tests are IMMUTABLE - After lock, tests CANNOT change       │
│  3. NO TODOs - Production code must be complete                 │
│  4. NO mocks in production - Mocks only in test files           │
│  5. Auto-iterate - Keep implementing until ALL tests pass       │
└─────────────────────────────────────────────────────────────────┘
```

### The TDD Cycle

1. **Design the feature** - Define WHAT it does (not how)
2. **Create specifications** - Detailed requirements and success criteria
3. **Design tests** - Unit tests, integration tests, edge cases
4. **Write tests FIRST** - Tests become IMMUTABLE after approval
5. **Implement code** - Must pass ALL tests, cannot modify tests
6. **Validate** - Verify no TODOs, no mocks, all tests pass

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    TDD WORKFLOW ENGINE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  SPEC → TEST_DESIGN → TEST_IMPL → IMPLEMENT → VALIDATE → ...   │
│                            ↓                                    │
│                      TESTS LOCKED                               │
│                      (immutable)                                │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ PLANNER  │  │TEST-WRITER│  │IMPLEMENTER│  │VALIDATOR │       │
│  │  (Opus)  │  │(Sonnet/H) │  │ (Sonnet)  │  │ (Haiku)  │       │
│  │SPEC MODE │  │TEST DESIGN│  │IMPL MODE  │  │VALIDATE  │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────┐    │
│  │              COST CIRCUIT BREAKER                       │    │
│  │         Budget Enforcement & Tracking                   │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐    │
│  │           TDD VALIDATION STACK (6 Layers)               │    │
│  │  Layer 1: Static Analysis (types, lint)                 │    │
│  │  Layer 2: Test Suite (100% pass required)               │    │
│  │  Layer 3: TODO/FIXME Check (must be zero)               │    │
│  │  Layer 4: Mock Detection (must be zero in prod)         │    │
│  │  Layer 5: Integration Sandbox                           │    │
│  │  Layer 6: Behavioral Diff                               │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## Workflow Phases (TDD Locked Gate Pattern)

```
SPEC → TEST_DESIGN → TEST_IMPL → IMPLEMENT → VALIDATE → REVIEW → DELIVER
  │         │            │            │           │         │        │
  ▼         ▼            ▼            ▼           ▼         ▼        ▼
Approval  Approval   LOCK TESTS   All Pass    TDD Check  Review   Done
                    (immutable)   Required    Required
```

### Phase 1: SPEC (Feature Specification)

| Property | Value |
|----------|-------|
| Agent | planner (Opus) |
| Mode | Read-only, SPEC MODE |
| Actions | Analyze requirements, define WHAT (not how), create product spec |
| Checkpoint | **Requires human approval** |
| Output | Product specification document |

**Key Responsibilities:**
- Define what the feature does (not how it's implemented)
- Specify success criteria and acceptance requirements
- Document edge cases and error conditions
- Provide test design guidance

### Phase 2: TEST_DESIGN (Test Case Design)

| Property | Value |
|----------|-------|
| Agent | test-writer (Sonnet) |
| Mode | Design mode |
| Actions | Design unit tests, integration tests, edge case tests from spec |
| Checkpoint | **Requires human approval** |
| Output | Test design document |

**Key Responsibilities:**
- Design test cases that guarantee requirements
- Cover happy paths, edge cases, error conditions
- Design integration tests for system boundaries
- Create test coverage matrix

### Phase 3: TEST_IMPL (Test Implementation)

| Property | Value |
|----------|-------|
| Agent | test-writer (Haiku) |
| Mode | Implementation mode |
| Actions | Write tests exactly as designed, verify tests FAIL |
| Checkpoint | **CRITICAL: Requires approval to LOCK TESTS** |
| Output | Test files (become IMMUTABLE after approval) |

**Key Responsibilities:**
- Implement tests exactly as designed
- Verify all tests FAIL (no implementation yet)
- No TODOs or skipped tests
- After approval: **TESTS ARE LOCKED AND IMMUTABLE**

```
⚠️ AFTER TEST_IMPL APPROVAL:
   - Tests CANNOT be modified
   - Tests CANNOT be deleted
   - Tests CANNOT be skipped
   - Implementation MUST make tests pass
```

### Phase 4: IMPLEMENT (Code Implementation)

| Property | Value |
|----------|-------|
| Agent | implementer (Sonnet) |
| Mode | IMPLEMENT MODE |
| Actions | Write code to pass LOCKED tests |
| Checkpoint | **Auto-proceed when ALL tests pass** |
| Constraints | CANNOT modify tests, NO TODOs, NO mocks in production |

**Key Responsibilities:**
- Write minimum code to pass each test
- Iterate until ALL tests pass (100% required)
- Follow existing code patterns
- **NEVER modify tests**
- **NEVER add TODO comments**
- **NEVER add mocks to production code**

### Phase 5: VALIDATE (TDD Validation)

| Property | Value |
|----------|-------|
| Agent | validator (Haiku) |
| Mode | VALIDATE MODE |
| Actions | Run 6-layer TDD validation stack |
| Checkpoint | **Auto-proceed if all validations pass** |

**Validation Layers:**

| Layer | Check | Requirement |
|-------|-------|-------------|
| 1 | Static Analysis | Zero type errors |
| 2 | Test Suite | 100% passing |
| 3 | TODO/FIXME Check | Zero in production |
| 4 | Mock Detection | Zero in production |
| 5 | Integration Sandbox | Pass or skip |
| 6 | Behavioral Diff | Complete |

### Phase 6: REVIEW (Quality Assurance)

| Property | Value |
|----------|-------|
| Agent | critic (Opus) |
| Mode | Review mode |
| Actions | Critical review, verify spec compliance |
| Checkpoint | **Requires human approval** |

### Phase 7: DELIVER (Final Delivery)

| Property | Value |
|----------|-------|
| Agent | summarizer (Haiku) |
| Mode | Delivery mode |
| Actions | Generate summary, document limitations |
| Checkpoint | None (completion) |

## Cost Governance

### Budget Circuit Breaker

```python
circuit_breaker = CostCircuitBreaker(budget_limit=1.0)

# Warning thresholds
WARNING_THRESHOLDS = [0.5, 0.75, 0.9]  # 50%, 75%, 90%

# Circuit breaks when budget exhausted
if projected > budget_limit:
    circuit_broken = True
    # Manual reset required
```

### Model Pricing (per million tokens)

| Model | Tier | Input | Output | Use Cases |
|-------|------|-------|--------|-----------|
| Opus | 1 | $15.00 | $75.00 | Spec, review |
| Sonnet | 2 | $3.00 | $15.00 | Test design, implementation |
| Haiku | 3 | $0.25 | $1.25 | Test impl, validation |

### Agent Tier Assignments

| Phase | Agent | Tier | Rationale |
|-------|-------|------|-----------|
| SPEC | planner | Opus | Strategic thinking required |
| TEST_DESIGN | test-writer | Sonnet | Design thinking required |
| TEST_IMPL | test-writer | Haiku | Routine implementation |
| IMPLEMENT | implementer | Sonnet | Code generation |
| VALIDATE | validator | Haiku | Routine checks |
| REVIEW | critic | Opus | Quality judgment |
| DELIVER | summarizer | Haiku | Routine synthesis |

## TDD Rules Summary

### NON-NEGOTIABLE Rules

| Rule | Description | Enforced By |
|------|-------------|-------------|
| Tests define correctness | Code must pass ALL tests | validator |
| Tests are IMMUTABLE | After lock, cannot change | workflow engine |
| NO TODOs | Zero in production code | validator |
| NO mocks in production | Only in test files | validator |
| Auto-iterate | Continue until all pass | implementer |

### Validation Requirements

| Check | Requirement | Failure Action |
|-------|-------------|----------------|
| Test Suite | 100% passing | Block delivery |
| TODOs | Zero count | Block delivery |
| Mocks in prod | Zero count | Block delivery |
| Static Analysis | Zero errors | Block delivery |

## API Reference

### Workflow Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `POST /api/workflow` | Create | Create TDD workflow from task |
| `GET /api/workflow` | List | List all workflows |
| `GET /api/workflow/{id}` | Status | Get workflow status |
| `GET /api/workflow/{id}/prompt` | Prompt | Get orchestrator prompt |
| `GET /api/workflow/{id}/governance` | Governance | Get CLAUDE.md |
| `GET /api/budget` | Budget | Get budget status |

### Agent Registry (14 Agents)

| Tier | Agents | Model |
|------|--------|-------|
| 1 (Strategic) | orchestrator, synthesis, critic, planner | Opus |
| 2 (Analysis) | researcher, perplexity-researcher, research-judge, claude-md-auditor, implementer | Sonnet |
| 3 (Execution) | web-search-researcher, summarizer, test-writer, installer, validator | Haiku |

## CLI Usage

```bash
# Create TDD workflow from task
python3 src/workflow_engine.py from-task "Add user authentication"

# Check budget status
python3 src/workflow_engine.py budget

# Generate governance document
python3 src/workflow_engine.py governance <workflow_id> -o CLAUDE.md
```

## Testing

### Running Tests

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run specific test file
python3 -m pytest tests/test_workflow_engine.py -v

# Run with coverage
python3 -m pytest tests/ --cov=src --cov-report=html
```

### Test Coverage Areas

| Module | Tests | Coverage Areas |
|--------|-------|----------------|
| workflow_engine | 39 | Circuit breaker, tasks, phases, validation |
| send_event | 22 | Token estimation, cost calculation |

## Troubleshooting

### Common Issues

**Tests not locking:**
- Ensure TEST_IMPL phase is approved
- Check workflow status via API

**Implementation failing:**
- Read test failure messages carefully
- DO NOT modify tests
- Iterate until all pass

**Validation failing:**
- Check for TODOs: `grep -rn "TODO" src/`
- Check for mocks: `grep -rn "Mock" src/`
- Run full test suite

### Verification Commands

```bash
# Verify TDD compliance
python3 -m pytest -v                           # All tests pass
grep -rn "TODO\|FIXME" src/                    # Zero TODOs
grep -rn "Mock\|MagicMock" src/ --include="*.py"  # Zero mocks in prod

# Check API
curl http://localhost:4200/health
curl http://localhost:4200/api/budget
```

## Changelog

### v2.1 - TDD Workflow Integration (Current)

- Implemented Test-Driven Development philosophy
- Added 7-phase TDD workflow (SPEC → TEST_DESIGN → TEST_IMPL → IMPLEMENT → VALIDATE → REVIEW → DELIVER)
- Added test immutability after TEST_IMPL approval
- Added TODO/FIXME detection in validation
- Added mock detection in production code
- Updated planner for SPEC MODE (define WHAT, not HOW)
- Updated test-writer for TDD design and implementation
- Updated implementer with strict TDD rules (cannot modify tests)
- Updated validator with 6-layer TDD validation stack
- Enhanced governance generation with TDD rules

### v2.0 - Multi-Agent Workflow Framework

- Added workflow engine with six-phase execution
- Implemented cost circuit breaker with budget enforcement
- Added four-layer validation stack
- Integrated tiktoken for accurate token counting
- Added 3 new agents: planner, implementer, validator
- Created comprehensive test suite (61 tests)

### v1.0 - Initial Release

- Basic event tracking and monitoring
- 14 agent definitions
- Terminal TUI and web dashboard
- SQLite event storage
