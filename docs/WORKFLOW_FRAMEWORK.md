# Multi-Agent Workflow Framework

This document describes the workflow orchestration framework implemented in the Agent Dashboard, based on the design patterns for autonomous Claude Code platforms.

## Overview

The framework implements five fundamental design shifts that enable reliable multi-agent workflows without requiring line-by-line code review:

1. **Constitutional Constraints** - Executable governance via positive framing
2. **Ephemeral Task Sandboxes** - Context isolation per task
3. **Verified Incrementalism** - Micro-generation with interleaved verification
4. **Subagent Orchestration** - Multi-agent delegation patterns
5. **Defense-in-Depth Validation** - Four-layer validation stack

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    WORKFLOW ENGINE                               │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   PLANNER    │  │ IMPLEMENTER  │  │  VALIDATOR   │          │
│  │   (Opus)     │──│   (Sonnet)   │──│   (Haiku)    │          │
│  │  PLAN MODE   │  │IMPLEMENT MODE│  │VALIDATE MODE │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│         │                 │                 │                   │
│  ┌──────┴─────────────────┴─────────────────┴──────┐           │
│  │              COST CIRCUIT BREAKER                │           │
│  │         Budget Enforcement & Tracking            │           │
│  └──────────────────────────────────────────────────┘           │
│                              │                                   │
│  ┌──────────────────────────┴────────────────────────┐         │
│  │            FOUR-LAYER VALIDATION STACK             │         │
│  │  Layer 1: Static Analysis (types, lint)            │         │
│  │  Layer 2: Unit Tests (coverage thresholds)         │         │
│  │  Layer 3: Integration Sandbox (isolated exec)      │         │
│  │  Layer 4: Behavioral Diff (human-readable)         │         │
│  └────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

## Workflow Phases (Locked Gate Pattern)

Each workflow progresses through phases with explicit checkpoints:

```
PLAN → TEST → IMPLEMENT → VALIDATE → REVIEW → DELIVER
  │      │        │          │         │        │
  └──────┴────────┴──────────┴─────────┴────────┘
         Human-in-the-Loop Checkpoints
```

### Phase 1: PLAN
- **Agent**: planner (Opus)
- **Mode**: Read-only exploration
- **Actions**: Analyze requirements, explore codebase, create detailed plan
- **Checkpoint**: Requires human approval of plan

### Phase 2: TEST
- **Agent**: test-writer (Haiku)
- **Mode**: Test-Driven Generation
- **Actions**: Write test specifications before implementation
- **Checkpoint**: Auto-proceed if test coverage meets threshold

### Phase 3: IMPLEMENT
- **Agent**: implementer (Sonnet)
- **Mode**: Execute approved plan
- **Actions**: Write code to pass tests, follow existing patterns
- **Checkpoint**: Requires approval for significant changes

### Phase 4: VALIDATE
- **Agent**: validator (Haiku)
- **Mode**: Four-layer validation stack
- **Actions**: Static analysis, tests, integration, behavioral diff
- **Checkpoint**: Auto-proceed if all validations pass

### Phase 5: REVIEW
- **Agent**: critic (Opus)
- **Mode**: Quality assurance
- **Actions**: Challenge implementation, find weaknesses
- **Checkpoint**: Advisory (issues noted but not blocking)

### Phase 6: DELIVER
- **Agent**: synthesis/summarizer (Opus/Haiku)
- **Mode**: Final synthesis
- **Actions**: Generate summary, recommendations
- **Checkpoint**: None (delivery)

## Cost Governance

### Budget Circuit Breaker

The framework enforces budget limits with automatic circuit breaking:

```python
circuit_breaker = CostCircuitBreaker(budget_limit=1.0)

# Check before operations
allowed, message = circuit_breaker.check_budget(estimated_cost)
if not allowed:
    # Circuit broken - manual reset required
    raise BudgetExhausted(message)

# Record usage
cost = circuit_breaker.record_usage(tokens_in, tokens_out, model)
```

### Warning Thresholds
- **50%**: First warning
- **75%**: Second warning
- **90%**: Final warning before circuit break

### Tier-Based Cost Optimization

| Tier | Model | Input ($/1M) | Output ($/1M) | Use For |
|------|-------|--------------|---------------|---------|
| 1 | Opus | $15.00 | $75.00 | Strategic, quality-critical |
| 2 | Sonnet | $3.00 | $15.00 | Analysis, implementation |
| 3 | Haiku | $0.25 | $1.25 | Routine, validation |

## Agent Roles

### Tier 1 - Opus (Strategic)
- **orchestrator** - Coordinates multi-agent workflows
- **synthesis** - Combines research into coherent insights
- **critic** - Challenges conclusions, finds weaknesses
- **planner** - Creates detailed implementation plans

### Tier 2 - Sonnet (Analysis)
- **researcher** - Documentation and structured research
- **perplexity-researcher** - Real-time search with citations
- **research-judge** - Evaluates research quality
- **claude-md-auditor** - Audits documentation files
- **implementer** - Executes approved implementation plans

### Tier 3 - Haiku (Execution)
- **web-search-researcher** - Broad web searches
- **summarizer** - Compression and distillation
- **test-writer** - Test generation
- **installer** - Setup and configuration
- **validator** - Four-layer validation stack

## Usage

### Creating a Workflow

```python
from workflow_engine import WorkflowEngine

# Initialize with budget limit
engine = WorkflowEngine(budget_limit=1.0)

# Create workflow from task description
workflow = engine.create_workflow_from_task(
    "Add user authentication to the API"
)

# Generate governance document
governance = engine.generate_claude_md_governance(workflow)

# Generate orchestrator prompt
prompt = engine.generate_orchestrator_prompt(workflow)
```

### CLI Usage

```bash
# Create a workflow from task
python workflow_engine.py from-task "Add user authentication"

# Check budget status
python workflow_engine.py budget

# Generate governance file
python workflow_engine.py governance <workflow_id> -o CLAUDE.md
```

### Running the Orchestrator

1. Start the dashboard:
```bash
agent-dashboard --web
```

2. Set the orchestrator as active agent:
```bash
export AGENT_NAME=orchestrator
export AGENT_MODEL=opus
```

3. Provide the workflow prompt to Claude:
```
Execute this workflow: [paste orchestrator prompt]
```

## Constitutional Constraints (CLAUDE.md)

The framework generates CLAUDE.md governance documents with positive framing:

### Positive Action Patterns (Effective)
```markdown
ALWAYS explore the codebase before proposing changes
ALWAYS create a detailed plan before implementation
ALWAYS wait for plan approval before proceeding
ALWAYS run type checks after each file modification
```

### Negative Prohibition Patterns (Avoid)
```markdown
NEVER commit without testing        ← Less effective
NEVER push directly to main         ← Less effective
```

## Hook Configuration

The framework provides hook configurations for automatic governance:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "python3 -m py_compile \"$CLAUDE_FILE_PATHS\""
          }
        ]
      }
    ]
  }
}
```

## Four-Layer Validation Stack

### Layer 1: Static Analysis
- TypeScript: `npx tsc --noEmit`
- Python: `python -m py_compile`
- ESLint/Prettier checks

### Layer 2: Unit Tests
- pytest / jest / npm test
- Coverage threshold enforcement

### Layer 3: Integration Sandbox
- Isolated execution environment
- Network restrictions
- Database fixtures

### Layer 4: Behavioral Diff
- Human-readable change summary
- Functional impact description
- Git diff analysis

## Best Practices

### For Orchestrators
1. Always start with a plan
2. Delegate to appropriate tiers
3. Use checkpoints for human oversight
4. Monitor budget throughout workflow

### For Implementers
1. Read tests before implementing
2. Match existing patterns exactly
3. Validate after every file change
4. Never deviate from approved plan

### For Validators
1. Run all four layers
2. Collect all issues (don't stop at first)
3. Provide actionable recommendations
4. Distinguish blocking vs warning issues

## Integration with Agent Dashboard

The workflow engine integrates with the Agent Dashboard for monitoring:

- Real-time task status tracking
- Token usage per agent/phase
- Cost accumulation visualization
- Event timeline with phase transitions

Access the dashboard at `http://localhost:4200` after starting with `agent-dashboard --web`.
