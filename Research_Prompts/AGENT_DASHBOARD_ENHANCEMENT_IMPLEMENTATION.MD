# Agent-Dashboard Enhancement Implementation Prompt

**Purpose:** Orchestrate the implementation of enhancements identified in the Agent-Dashboard Critical Analysis  
**Execution Model:** Multi-agent parallel workflow with tiered delegation  
**Version:** 1.0.0

---

## Constraints (MANDATORY)

### ALWAYS:
- Delegate research and implementation tasks to appropriate tier agents
- Execute independent tasks in parallel using single Task call with multiple targets
- Enforce handoff compression budgets (Haiku→Opus: 300 tokens, Sonnet→Opus: 500 tokens)
- Validate outputs against required schema before proceeding to next phase
- Track progress against phase completion criteria before advancing

### NEVER:
- Perform research directly when researcher agents are available
- Execute sequential tasks that could run in parallel
- Pass uncompressed research outputs to Opus-tier agents
- Proceed past phase gates without documented completion criteria
- Exceed iteration limits (5 rounds research, 3 rounds critique)

---

## Input Schema

```yaml
required:
  - target_repository: "path to agent-dashboard codebase"
  - implementation_phase: "1|2|3|all"
  - dry_run: "true|false"
optional:
  - priority_agents: "list of agents to prioritize"
  - skip_agents: "list of agents to exclude"
  - budget_limit: "maximum cost in USD"
```

---

## Output Schema

```yaml
required:
  - phase_id: "unique identifier"
  - status: "completed|partial|blocked"
  - agents_modified: "list of agent files changed"
  - validation_results: "summary of quality checks"
  - next_steps: "recommended follow-up actions"
```

---

## Phase 1: Quick Wins (Estimated: 1-2 days)

### Objective
Add constraint sections to role-heavy agents and standardize iteration limits across all agents.

### Execution Strategy

**Step 1.1: Parallel Agent Analysis**

Spawn the following agents simultaneously to analyze current agent definitions:

```
PARALLEL EXECUTION BLOCK 1.1
├── Agent: researcher (Sonnet)
│   Task: "Analyze agents/researcher.md, agents/summarizer.md. 
│          Extract: current constraint count, role description length, 
│          iteration limits present/absent. Output ≤400 tokens."
│
├── Agent: researcher (Sonnet)  
│   Task: "Analyze all 5 panel judge agents (judge-technical.md, 
│          judge-completeness.md, judge-practicality.md, judge-adversarial.md,
│          judge-user.md). Extract: constraint sections, output budgets,
│          iteration limits. Output ≤400 tokens."
│
└── Agent: claude-md-auditor (Sonnet)
    Task: "Audit agents/ directory. For each agent, report:
           - Has explicit ALWAYS/NEVER constraints: Yes/No
           - Has iteration limits: Yes/No  
           - Has output budget: Yes/No
           Output as table, ≤500 tokens."
```

**Completion Criteria for 1.1:**
- All three agents return valid outputs
- Outputs conform to token budgets
- Gap analysis table is complete for all 22 agents

---

**Step 1.2: Constraint Template Generation**

After receiving analysis results, spawn implementation agents:

```
PARALLEL EXECUTION BLOCK 1.2
├── Agent: implementer (Sonnet)
│   Task: "Generate constraint section template for research-focused agents.
│          Include: source citation requirements, confidence level mandates,
│          query limits, freshness thresholds. Follow format:
│          ## Constraints (MANDATORY)
│          ### ALWAYS: [list]
│          ### NEVER: [list]
│          Output: template only, ≤300 tokens."
│
├── Agent: implementer (Sonnet)
│   Task: "Generate constraint section template for evaluation-focused agents
│          (panel judges, research-judge, validator). Include: scoring rubric
│          adherence, verdict format requirements, output budgets.
│          Output: template only, ≤300 tokens."
│
└── Agent: implementer (Sonnet)
    Task: "Generate iteration limit section template. Include:
           - Maximum rounds with tracking format
           - Escalation protocol with trigger conditions
           - Graceful degradation procedure
           Output: template only, ≤300 tokens."
```

**Completion Criteria for 1.2:**
- Three reusable templates generated
- Templates follow established agent definition patterns
- Templates include specific, measurable constraints

---

**Step 1.3: Agent File Modifications**

Apply templates to identified agents. Execute in parallel batches:

```
PARALLEL EXECUTION BLOCK 1.3a (Research Agents)
├── Agent: implementer (Sonnet)
│   Task: "Modify agents/researcher.md. Add constraint section after
│          'Research Process'. Add iteration limit: max 10 queries.
│          Preserve existing content. Output: diff only."
│
└── Agent: implementer (Sonnet)
    Task: "Modify agents/summarizer.md. Add constraint section.
           Add output budget: Executive Summary ≤400 tokens,
           Bullet Summary ≤150 tokens. Output: diff only."

PARALLEL EXECUTION BLOCK 1.3b (Panel Judges)
├── Agent: implementer (Sonnet)
│   Task: "Modify agents/judge-technical.md, agents/judge-completeness.md.
│          Add constraint section with evaluation scope limits.
│          Add output budget: ≤500 tokens. Output: diffs only."
│
└── Agent: implementer (Sonnet)
    Task: "Modify agents/judge-practicality.md, agents/judge-adversarial.md,
           agents/judge-user.md. Add constraint section with evaluation
           scope limits. Add output budget: ≤500 tokens. Output: diffs only."
```

**Completion Criteria for 1.3:**
- All 7 target agents modified
- Modifications preserve existing functionality
- Constraint sections follow template format

---

**Step 1.4: Validation**

```
SEQUENTIAL EXECUTION BLOCK 1.4
└── Agent: validator (Haiku)
    Task: "Validate all modified agent files in agents/ directory.
           Check: YAML frontmatter valid, markdown renders correctly,
           constraint sections present, iteration limits documented.
           Output: pass/fail per file with specific issues."
```

**Phase 1 Gate:**
- All 7 agents pass validation
- No regressions in existing functionality
- Changes documented in CHANGELOG.md

---

## Phase 2: Core Enhancements (Estimated: 3-5 days)

### Objective
Add few-shot examples to priority agents and implement handoff compression validation.

### Execution Strategy

**Step 2.1: Example Research**

Gather example patterns from existing well-documented agents:

```
PARALLEL EXECUTION BLOCK 2.1
├── Agent: researcher (Sonnet)
│   Task: "Analyze few-shot examples in agents/orchestrator.md, 
│          agents/critic.md, agents/synthesis.md. Extract:
│          - Example structure pattern
│          - Input/output format demonstrated
│          - Edge cases covered
│          Output: pattern analysis ≤500 tokens."
│
└── Agent: researcher (Sonnet)
    Task: "Research prompt engineering best practices for few-shot examples.
           Focus on: optimal example count (2-3), example diversity,
           failure case inclusion. Cite sources. Output ≤400 tokens."
```

**Completion Criteria for 2.1:**
- Pattern analysis extracted from existing examples
- Research findings include source citations
- Clear template structure identified

---

**Step 2.2: Example Generation**

Generate examples for priority agents in parallel:

```
PARALLEL EXECUTION BLOCK 2.2a (Tier 1 Priority)
├── Agent: implementer (Sonnet)
│   Task: "Generate 3 few-shot examples for agents/researcher.md:
│          1. Successful multi-source research
│          2. Handling outdated information
│          3. Escalation when information unavailable
│          Follow pattern from orchestrator.md. Output ≤800 tokens total."
│
├── Agent: implementer (Sonnet)
│   Task: "Generate 3 few-shot examples for agents/summarizer.md:
│          1. Executive summary from multiple inputs
│          2. Bullet summary with compression metrics
│          3. Handling low-quality input
│          Output ≤600 tokens total."
│
└── Agent: implementer (Sonnet)
    Task: "Generate 3 few-shot examples for agents/validator.md:
           1. Full validation pass
           2. Validation failure with actionable feedback
           3. Partial pass with warnings
           Output ≤700 tokens total."

PARALLEL EXECUTION BLOCK 2.2b (Tier 2 Priority)
├── Agent: implementer (Sonnet)
│   Task: "Generate 2 few-shot examples for agents/web-search-researcher.md:
│          1. Successful cross-verified research
│          2. Query limit reached with graceful degradation
│          Output ≤500 tokens total."
│
└── Agent: implementer (Sonnet)
    Task: "Generate standardized example template for all 5 panel judges.
           Include: input work product, evaluation process, scored output.
           Template should be adaptable per judge focus. Output ≤400 tokens."
```

**Completion Criteria for 2.2:**
- Examples generated for 4 priority agents
- Panel judge template created
- All examples demonstrate input→process→output flow

---

**Step 2.3: Handoff Validation Implementation**

Implement token counting for handoff compression:

```
SEQUENTIAL EXECUTION BLOCK 2.3
├── Agent: planner (Opus)
│   Task: "Design handoff validation module specification.
│          Requirements:
│          - Token counting for handoff content
│          - Tier-based budget enforcement (Haiku→Opus: 300, Sonnet→Opus: 500)
│          - Rejection with compression guidance
│          - Integration with synthesis_validator.py
│          Output: specification document ≤600 tokens."
│   
│   [CHECKPOINT: Human approval required before implementation]
│
├── Agent: test-writer (Sonnet)
│   Task: "Design test cases for handoff validation from specification.
│          Cover: budget enforcement, rejection messaging, edge cases.
│          Output: test design document ≤400 tokens."
│
├── Agent: test-writer (Haiku)
│   Task: "Implement tests from design in tests/test_handoff_validator.py.
│          Tests must FAIL initially (no implementation yet)."
│
└── Agent: implementer (Sonnet)
    Task: "Implement handoff_validator.py to pass all tests.
           Integrate with existing validation.py patterns.
           NO TODOs. NO mocks in production code."
```

**Completion Criteria for 2.3:**
- Specification approved
- All tests pass
- Integration verified with existing validation stack

---

**Step 2.4: Agent File Updates**

Apply generated examples to agent files:

```
PARALLEL EXECUTION BLOCK 2.4
├── Agent: implementer (Sonnet)
│   Task: "Add few-shot examples to agents/researcher.md.
│          Place after 'Research Process' section, before 'Constraints'.
│          Preserve all existing content. Output: diff only."
│
├── Agent: implementer (Sonnet)
│   Task: "Add few-shot examples to agents/summarizer.md and 
│          agents/validator.md. Place before 'Constraints' section.
│          Output: diffs only."
│
└── Agent: implementer (Sonnet)
    Task: "Add few-shot examples to agents/web-search-researcher.md
           and all 5 panel judge agents. Use template format for judges.
           Output: diffs only."
```

---

**Step 2.5: Phase 2 Validation**

```
PARALLEL EXECUTION BLOCK 2.5
├── Agent: validator (Haiku)
│   Task: "Validate all modified agent files. Check: markdown valid,
│          examples present, constraint sections intact.
│          Output: validation report."
│
├── Agent: critic (Opus)
│   Task: "Review few-shot examples for quality. Evaluate:
│          - Do examples demonstrate expected behavior clearly?
│          - Are edge cases covered?
│          - Is escalation shown appropriately?
│          Output: critique with specific recommendations ≤500 tokens."
│
└── Agent: test-writer (Haiku)
    Task: "Run full test suite including new handoff validation tests.
           Report: pass/fail counts, any regressions."
```

**Phase 2 Gate:**
- All agent files pass validation
- Critic approves example quality (or issues addressed)
- All tests pass (100% required)
- Changes documented in CHANGELOG.md

---

## Phase 3: Optimization (Estimated: 1 week)

### Objective
Optimize tier assignments, add uncertainty protocols, and implement pre-compression layer.

### Execution Strategy

**Step 3.1: Tier Assignment Analysis**

```
PARALLEL EXECUTION BLOCK 3.1
├── Agent: researcher (Sonnet)
│   Task: "Analyze panel judge task complexity. For each judge, assess:
│          - Reasoning depth required
│          - Checklist vs. analysis nature
│          - Recommended tier with justification
│          Output ≤400 tokens."
│
└── Agent: researcher (Sonnet)
    Task: "Analyze test-writer dual-mode feasibility. Assess:
           - Test design complexity (requires reasoning)
           - Test implementation complexity (structured output)
           - Recommended tier split with justification
           Output ≤300 tokens."
```

---

**Step 3.2: Tier Modifications**

Based on analysis, modify agent tier assignments:

```
PARALLEL EXECUTION BLOCK 3.2
├── Agent: implementer (Sonnet)
│   Task: "Modify agents/judge-completeness.md and agents/judge-practicality.md.
│          Change model: sonnet → haiku in frontmatter.
│          Add note explaining tier rationale. Output: diffs only."
│
└── Agent: implementer (Sonnet)
    Task: "Modify agents/test-writer.md. Add dual-mode documentation:
           - TEST_DESIGN mode: Sonnet tier
           - TEST_IMPL mode: Haiku tier
           Update frontmatter and process sections. Output: diff only."
```

---

**Step 3.3: Uncertainty Protocol Implementation**

```
PARALLEL EXECUTION BLOCK 3.3
├── Agent: implementer (Sonnet)
│   Task: "Create uncertainty protocol section for research agents.
│          Include: uncertainty triggers, response format, confidence
│          calibration guidelines. Output: template ≤400 tokens."
│
└── Agent: implementer (Sonnet)
    Task: "Apply uncertainty protocol to: researcher.md, 
           web-search-researcher.md, perplexity-researcher.md, synthesis.md.
           Place after 'Constraints' section. Output: diffs only."
```

---

**Step 3.4: Pre-Compression Layer**

```
SEQUENTIAL EXECUTION BLOCK 3.4
├── Agent: planner (Opus)
│   Task: "Design pre-compression layer specification.
│          Requirements:
│          - Summarizer as mandatory Opus intermediary
│          - Staged context loading pattern
│          - Integration with orchestrator workflow
│          Output: specification ≤500 tokens."
│
│   [CHECKPOINT: Human approval required]
│
├── Agent: implementer (Sonnet)
│   Task: "Update agents/orchestrator.md with pre-compression protocol.
│          Add section: 'Opus Context Protection' with specific instructions
│          for routing through summarizer before Opus handoff."
│
└── Agent: implementer (Sonnet)
    Task: "Update agents/synthesis.md with explicit input validation
           for compressed format. Add rejection protocol for
           uncompressed inputs."
```

---

**Step 3.5: Documentation and Validation**

```
PARALLEL EXECUTION BLOCK 3.5
├── Agent: implementer (Sonnet)
│   Task: "Update docs/WORKFLOW_FRAMEWORK.md with:
│          - Parallel execution patterns
│          - Tier assignment rationale
│          - Pre-compression requirements
│          Output: diff only."
│
├── Agent: implementer (Sonnet)
│   Task: "Update CHANGELOG.md with all Phase 3 changes.
│          Follow existing changelog format. Output: additions only."
│
├── Agent: validator (Haiku)
│   Task: "Run full validation suite on all modified files.
│          Include: syntax check, test suite, TODO check.
│          Output: validation report."
│
└── Agent: critic (Opus)
    Task: "Final review of all Phase 3 changes. Evaluate:
           - Tier assignments are justified
           - Uncertainty protocols are actionable
           - Pre-compression doesn't break existing workflows
           Output: approval or revision requirements ≤400 tokens."
```

**Phase 3 Gate:**
- All modifications validated
- Critic approves changes
- Full test suite passes
- Documentation updated
- CHANGELOG reflects all changes

---

## Quality Gates

### Gate Criteria (Apply at Each Phase Boundary)

Before proceeding to next phase, verify:

1. **Schema Compliance:** All outputs conform to required schema
2. **Test Coverage:** All new functionality has tests; all tests pass
3. **Documentation:** Changes reflected in appropriate docs
4. **No Regressions:** Existing functionality preserved
5. **Budget Compliance:** Token budgets respected for all handoffs

### Escalation Protocol

If any gate criterion fails after 3 attempts:

```markdown
## Phase Gate Failure

**Phase:** [N]
**Criterion Failed:** [specific criterion]
**Attempts:** 3/3

### Failure Details
[Specific issues preventing gate passage]

### Options
1. Proceed with documented gaps (requires human approval)
2. Extend phase timeline for additional fixes
3. Descope phase and move items to next phase

### Recommendation: [Option N]
[Reasoning]
```

---

## Progress Tracking Format

At each major step, log progress:

```markdown
## Progress: Phase [N], Step [X.Y]

**Timestamp:** [ISO-8601]
**Agents Spawned:** [list with tiers]
**Parallel Execution:** [Yes/No]

### Outputs Received
| Agent | Status | Token Count | Schema Valid |
|-------|--------|-------------|--------------|
| [agent] | [complete/pending/failed] | [N] | [Yes/No] |

### Cumulative Progress
- Agents modified: [N]/[total]
- Tests passing: [N]/[total]
- Phase completion: [X]%

### Next Action
[Specific next step or gate check]
```

---

## Few-Shot Execution Example

### Example: Executing Phase 1, Step 1.1

**Input:**
```yaml
target_repository: "/path/to/agent-dashboard"
implementation_phase: "1"
dry_run: false
```

**Execution:**

```
DELEGATION ROUND: 1/5

Spawning parallel agents for Step 1.1:

Task 1: researcher (Sonnet)
  Prompt: "Analyze agents/researcher.md, agents/summarizer.md..."
  
Task 2: researcher (Sonnet)
  Prompt: "Analyze all 5 panel judge agents..."
  
Task 3: claude-md-auditor (Sonnet)
  Prompt: "Audit agents/ directory..."

[All three execute simultaneously]

Results received:
- Task 1: 387 tokens, schema valid ✓
- Task 2: 412 tokens, schema valid ✓
- Task 3: 498 tokens, schema valid ✓

Step 1.1 Complete. Proceeding to Step 1.2.
```

**Output after Phase 1:**
```yaml
phase_id: "phase-1-20251218"
status: "completed"
agents_modified:
  - "agents/researcher.md"
  - "agents/summarizer.md"
  - "agents/judge-technical.md"
  - "agents/judge-completeness.md"
  - "agents/judge-practicality.md"
  - "agents/judge-adversarial.md"
  - "agents/judge-user.md"
validation_results:
  syntax_check: "pass"
  test_suite: "pass (87/87)"
  todo_check: "pass (0 TODOs)"
next_steps:
  - "Proceed to Phase 2"
  - "Human review recommended for constraint sections"
```

---

## Appendix: Agent Selection Reference

| Task Type | Primary Agent | Tier | Parallel Safe |
|-----------|---------------|------|---------------|
| Agent file analysis | researcher | Sonnet | Yes |
| Directory audit | claude-md-auditor | Sonnet | Yes |
| Template generation | implementer | Sonnet | Yes |
| File modification | implementer | Sonnet | Yes (batch by dependency) |
| Specification design | planner | Opus | No (requires approval) |
| Test design | test-writer | Sonnet | Yes |
| Test implementation | test-writer | Haiku | No (sequential after design) |
| Code implementation | implementer | Sonnet | No (sequential after tests) |
| Validation | validator | Haiku | Yes |
| Quality review | critic | Opus | No (final gate) |
| Compression | summarizer | Haiku | Yes |

---

## Termination Conditions

### Successful Completion
All three phases complete with gate criteria satisfied. Final deliverables:
- 22 agent definitions enhanced
- Handoff validation implemented and tested
- Documentation updated
- CHANGELOG reflects all changes

### Partial Completion
One or more phases complete; remaining phases blocked or descoped. Document:
- Completed phases and changes
- Blocked items with specific blockers
- Recommended follow-up actions

### Abort Conditions
- Budget limit exceeded
- Critical test failures after 5 fix attempts
- Human intervention requested and not received within 24 hours