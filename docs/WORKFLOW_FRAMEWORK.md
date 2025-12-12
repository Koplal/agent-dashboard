# Multi-Agent TDD Workflow Framework v2.2

This document describes the Test-Driven Development (TDD) workflow framework implemented in the Agent Dashboard for autonomous Claude Code platforms.

> **Version:** 2.2.1
> **Last Updated:** 2025-01-09
> **Agents:** 20 specialized agents across 3 tiers
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

### Agent Registry (20 Agents)

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

---

## 🎯 End-to-End Example: From Prompt to Parallel Execution

This example demonstrates a complete conversation flow from natural language prompt to parallel multi-agent execution using the TDD workflow.

---

### The Conversation

#### Turn 1: User Initial Prompt

**User:**
```
Help me create a microcontroller-based project for environmental monitoring
```

---

#### Turn 2: Orchestrator Clarification

**Claude (orchestrator):**

Great project idea! Before I create a workflow, I need to understand your requirements better.

**Scope Questions:**

1. **Sensors** — What environmental parameters do you want to monitor?
   - [ ] Temperature & Humidity
   - [ ] Air Quality (CO2, VOCs, PM2.5)
   - [ ] Light levels
   - [ ] Soil moisture
   - [ ] Other: ___

2. **Connectivity** — How should the device communicate?
   - [ ] WiFi (requires power outlet nearby)
   - [ ] Bluetooth LE (phone app, short range)
   - [ ] LoRa (long range, low power, needs gateway)
   - [ ] Cellular (anywhere, higher cost)

3. **Power Source** — How will it be powered?
   - [ ] USB/Wall power (always on)
   - [ ] Battery (how long between charges?)
   - [ ] Solar + battery

4. **Data Backend** — Where should data be stored?
   - [ ] Local only (SD card / display)
   - [ ] Cloud dashboard (I'll set up hosting)
   - [ ] Self-hosted (I have a server)
   - [ ] Third-party IoT platform (ThingsBoard, Home Assistant, etc.)

5. **Output** — What deliverables do you need?
   - [ ] Hardware design files (schematic, PCB, BOM)
   - [ ] Firmware source code
   - [ ] Backend API + database
   - [ ] Web dashboard
   - [ ] Mobile app
   - [ ] Documentation only (I'll build it myself)

**Constraints:**

| Constraint | Your Preference |
|------------|-----------------|
| Budget for AI assistance | $___  (recommended: $2-5 for this scope) |
| Timeline | ___ days/weeks |
| Your experience level | Beginner / Intermediate / Advanced |
| Must-use technologies | e.g., "ESP32", "Python backend", "React" |

---

#### Turn 3: User Provides Requirements

**User:**
```
- Sensors: Temperature, humidity, and air quality (CO2 + PM2.5)
- Connectivity: WiFi with MQTT
- Power: USB powered, will be indoors
- Backend: Self-hosted, I have a Raspberry Pi
- Output: Everything except mobile app

Constraints:
- Budget: $4 for AI assistance
- Timeline: Want a working prototype in 2 weeks
- Experience: Intermediate - I've done Arduino projects before
- Tech preferences: ESP32, Python backend, simple web dashboard (no React)
```

---

#### Turn 4: Orchestrator Proposes Workflow

**Claude (orchestrator):**

Based on your requirements, here's my proposed workflow breakdown:

### 📋 Proposed Workflow: Environmental Monitor v1

**Overview:**

| Metric | Value |
|--------|-------|
| Components | 6 |
| Estimated Cost | $3.20 - $3.80 |
| Parallel Tracks | 3 initial, 2 sequential |
| Estimated Time | 4-6 hours (with parallelization) |

**Component Breakdown:**

| ID | Component | Description | Agent | Tier | Est. Cost | Parallelizable |
|----|-----------|-------------|-------|------|-----------|----------------|
| `hw-design` | Hardware Design | ESP32 + sensor selection, wiring diagram, BOM | planner | Opus | $0.45 | ✅ Track A |
| `fw-sensors` | Sensor Firmware | Drivers for DHT22, SCD40, PM2.5 sensor | implementer | Sonnet | $0.55 | ⏳ After hw-design |
| `fw-mqtt` | MQTT Communication | WiFi setup, MQTT client, message formatting | implementer | Sonnet | $0.40 | ⏳ After hw-design |
| `backend-api` | Python Backend | FastAPI server, SQLite/InfluxDB, MQTT subscriber | implementer | Sonnet | $0.50 | ✅ Track B |
| `dashboard` | Web Dashboard | Simple HTML/JS dashboard with charts | implementer | Sonnet | $0.45 | ✅ Track C |
| `integration` | System Integration | End-to-end testing, deployment scripts, docs | orchestrator | Opus | $0.65 | ⏳ Final |

**Dependency Graph:**
```
     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
     │  hw-design  │     │ backend-api │     │  dashboard  │
     │  (Track A)  │     │  (Track B)  │     │  (Track C)  │
     └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
            │                   │                   │
     ┌──────┴──────┐            │                   │
     │             │            │                   │
┌────▼────┐  ┌─────▼─────┐      │                   │
│fw-sensors│  │ fw-mqtt   │      │                   │
└────┬────┘  └─────┬─────┘      │                   │
     │             │            │                   │
     └──────┬──────┴────────────┴───────────────────┘
            │
     ┌──────▼──────┐
     │ integration │
     └─────────────┘
```

**Budget Allocation:**

```
Total Budget: $4.00
├── hw-design:    $0.45 (11%)  ████░░░░░░
├── fw-sensors:   $0.55 (14%)  █████░░░░░
├── fw-mqtt:      $0.40 (10%)  ████░░░░░░
├── backend-api:  $0.50 (13%)  █████░░░░░
├── dashboard:    $0.45 (11%)  ████░░░░░░
├── integration:  $0.65 (16%)  ██████░░░░
├── Buffer:       $1.00 (25%)  ██████████  ← For revisions/overruns
└── Total:        $4.00
```

**Do you want me to:**

1. ✅ **Proceed** with this workflow as-is
2. ✏️ **Adjust** component scope or budget allocation
3. ➕ **Add** components (e.g., OTA updates, alerts)
4. ➖ **Remove** components to reduce scope/cost
5. 🔄 **Reprioritize** which components to tackle first

---

#### Turn 5: User Confirms with Adjustments

**User:**
```
Looks good! A few adjustments:
1. Combine fw-sensors and fw-mqtt into a single "firmware" component
2. Add a simple alerting system (email when CO2 > threshold)
3. Reduce the buffer to $0.50 - I'm okay with a hard stop at $4

Proceed with these changes.
```

---

#### Turn 6: Orchestrator Confirms and Generates Workflow

**Claude (orchestrator):**

Got it! Here's the updated workflow:

### ✅ Final Workflow: Environmental Monitor v1

**Changes Applied:**
- ✅ Merged `fw-sensors` + `fw-mqtt` → `firmware` ($0.85)
- ✅ Added `alerting` component ($0.35)
- ✅ Reduced buffer to $0.50

**Final Component List:**

| ID | Component | Agent | Tier | Budget | Phase |
|----|-----------|-------|------|--------|-------|
| `hw-design` | Hardware Design | planner | Opus | $0.45 | Ready |
| `firmware` | ESP32 Firmware (sensors + MQTT) | implementer | Sonnet | $0.85 | Blocked by hw-design |
| `backend-api` | Python Backend + MQTT | implementer | Sonnet | $0.50 | Ready |
| `dashboard` | Web Dashboard | implementer | Sonnet | $0.45 | Ready |
| `alerting` | Email Alerts | implementer | Sonnet | $0.35 | Blocked by backend-api |
| `integration` | System Integration | orchestrator | Opus | $0.55 | Final |

**Budget:** $3.50 allocated + $0.50 buffer = $4.00 hard limit

---

**🚀 Generating workflow...**

```bash
curl -X POST http://localhost:4200/api/workflow \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Environmental Monitor v1",
    "task": "ESP32-based environmental monitoring with temp/humidity/CO2/PM2.5 sensors, MQTT communication, Python backend, web dashboard, and email alerts",
    "budget": {
      "limit": 4.00,
      "hard_stop": true,
      "buffer": 0.50
    },
    "components": [
      {
        "id": "hw-design",
        "name": "Hardware Design",
        "description": "ESP32-S3 + DHT22 + SCD40 + PMS5003 sensor selection, wiring diagram, BOM",
        "agent": "planner",
        "model": "opus",
        "budget": 0.45,
        "dependencies": [],
        "deliverables": ["docs/hardware-spec.md", "hardware/wiring-diagram.svg", "hardware/bom.csv"]
      },
      {
        "id": "firmware",
        "name": "ESP32 Firmware",
        "description": "PlatformIO project with sensor drivers, WiFi manager, MQTT client",
        "agent": "implementer",
        "model": "sonnet",
        "budget": 0.85,
        "dependencies": ["hw-design"],
        "deliverables": ["firmware/src/main.cpp", "firmware/platformio.ini", "firmware/README.md"]
      },
      {
        "id": "backend-api",
        "name": "Python Backend",
        "description": "FastAPI + SQLite + MQTT subscriber + REST endpoints",
        "agent": "implementer",
        "model": "sonnet",
        "budget": 0.50,
        "dependencies": [],
        "deliverables": ["backend/main.py", "backend/requirements.txt", "backend/docker-compose.yml"]
      },
      {
        "id": "dashboard",
        "name": "Web Dashboard",
        "description": "HTML/CSS/JS dashboard with Chart.js, auto-refresh, responsive",
        "agent": "implementer",
        "model": "sonnet",
        "budget": 0.45,
        "dependencies": [],
        "deliverables": ["dashboard/index.html", "dashboard/app.js", "dashboard/style.css"]
      },
      {
        "id": "alerting",
        "name": "Email Alerts",
        "description": "Threshold monitoring + email notifications via SMTP",
        "agent": "implementer",
        "model": "sonnet",
        "budget": 0.35,
        "dependencies": ["backend-api"],
        "deliverables": ["backend/alerts.py", "backend/email_templates/"]
      },
      {
        "id": "integration",
        "name": "System Integration",
        "description": "End-to-end testing, deployment scripts, user documentation",
        "agent": "orchestrator",
        "model": "opus",
        "budget": 0.55,
        "dependencies": ["firmware", "backend-api", "dashboard", "alerting"],
        "deliverables": ["docs/deployment-guide.md", "docs/user-manual.md", "scripts/deploy.sh"]
      }
    ],
    "settings": {
      "tdd_phases": ["SPEC", "TEST_DESIGN", "TEST_IMPL", "IMPLEMENT", "VALIDATE", "REVIEW", "DELIVER"],
      "parallel_execution": true,
      "create_worktrees": true,
      "worktree_prefix": "env-monitor"
    }
  }'
```

**Response:**
```json
{
  "workflow_id": "env-mon-2024-01-15-a7b3c9",
  "status": "created",
  "components": 6,
  "ready_to_start": ["hw-design", "backend-api", "dashboard"],
  "blocked": ["firmware", "alerting", "integration"],
  "budget": {
    "limit": 4.00,
    "allocated": 3.50,
    "buffer": 0.50,
    "spent": 0.00
  },
  "worktrees_created": [
    "../env-monitor-hw-design",
    "../env-monitor-backend-api",
    "../env-monitor-dashboard"
  ],
  "next_action": "Start parallel execution in 3 terminals"
}
```

---

### Ready to Execute!

I've created 3 git worktrees for the initial parallel tracks. Open 3 terminal windows:

**Terminal 1 — Hardware Design:**
```bash
cd ../env-monitor-hw-design
AGENT_NAME=planner AGENT_MODEL=opus claude "Execute hw-design component for Environmental Monitor workflow"
```

**Terminal 2 — Backend API:**
```bash
cd ../env-monitor-backend-api
AGENT_NAME=implementer AGENT_MODEL=sonnet claude "Execute backend-api component for Environmental Monitor workflow"
```

**Terminal 3 — Dashboard:**
```bash
cd ../env-monitor-dashboard
AGENT_NAME=implementer AGENT_MODEL=sonnet claude "Execute dashboard component for Environmental Monitor workflow"
```

**Monitor Progress:**
```bash
# Terminal 4 — Dashboard
agent-dashboard --web
# Open http://localhost:4200
```

---

### Step 2: Parallel Execution Begins

The workflow is now active. The dashboard shows real-time progress:

**Dashboard View (http://localhost:4200):**
```
┌─────────────────────────────────────────────────────────────────┐
│ Workflow: Environmental Monitor v1          Budget: $0.42/$4.00 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ hw-design   │  │ backend-api │  │  dashboard  │             │
│  │ ● SPEC      │  │ ● TEST_IMPL │  │ ● IMPLEMENT │             │
│  │ planner     │  │ implementer │  │ implementer │             │
│  │ [████░░] 65%│  │ [██████] 85%│  │ [█████░] 70%│             │
│  └──────┬──────┘  └──────┬──────┘  └─────────────┘             │
│         │                │                                      │
│         ▼                ▼                                      │
│  ┌─────────────┐  ┌─────────────┐                              │
│  │  firmware   │  │  alerting   │                              │
│  │ ○ BLOCKED   │  │ ○ BLOCKED   │                              │
│  │ waiting...  │  │ waiting...  │                              │
│  └──────┬──────┘  └──────┬──────┘                              │
│         │                │                                      │
│         └────────┬───────┘                                      │
│                  ▼                                              │
│           ┌─────────────┐                                       │
│           │ integration │                                       │
│           │ ○ BLOCKED   │                                       │
│           └─────────────┘                                       │
│                                                                 │
│ Active Agents: planner (opus), implementer ×2 (sonnet)         │
│ Tokens: 15,230 in / 9,450 out    Cost: $0.42                   │
└─────────────────────────────────────────────────────────────────┘
```

---

### Step 3: TDD Phase Progression

Each component follows the full TDD workflow phases:

**Example: Hardware Design - Phase Progression:**

| Phase | Agent | Activity | Output |
|-------|-------|----------|--------|
| SPEC | planner | Define requirements | `docs/hardware-spec.md` |
| TEST_DESIGN | test-writer | Define acceptance criteria | `tests/hardware-acceptance.md` |
| TEST_IMPL | test-writer | Create test fixtures | `tests/test_hardware_validation.py` |
| IMPLEMENT | implementer | Create schematics, BOM | `hardware/schematic.svg`, `hardware/bom.csv` |
| VALIDATE | validator | Verify against spec | Validation report |
| REVIEW | critic | Adversarial review | Review comments |
| DELIVER | summarizer | Final documentation | `docs/hardware-final.md` |

**Example TDD Flow for Firmware Component:**

```bash
# Phase 1: SPEC (planner agent)
cd ../env-monitor-firmware
AGENT_NAME=planner AGENT_MODEL=opus claude "
Create specification for firmware:
- Main loop architecture
- Sensor polling intervals
- Data structure for readings
- MQTT message format
"
# Output: docs/firmware-spec.md

# Phase 2: TEST_DESIGN (test-writer agent)
AGENT_NAME=test-writer AGENT_MODEL=sonnet claude "
Review firmware-spec.md and define test criteria:
- Unit test requirements
- Integration test scenarios
- Performance benchmarks
- Edge cases to cover
"
# Output: tests/test-requirements.md

# Phase 3: TEST_IMPL (test-writer agent)
AGENT_NAME=test-writer AGENT_MODEL=haiku claude "
Implement tests based on test-requirements.md:
- Create test stubs that currently fail
- Mock sensor interfaces
- Create test data fixtures
"
# Output: tests/test_firmware.cpp, tests/mocks/

# Phase 4: IMPLEMENT (implementer agent)
AGENT_NAME=implementer AGENT_MODEL=sonnet claude "
Implement firmware to pass all tests:
- Main loop in src/main.cpp
- Sensor drivers in src/drivers/
- MQTT client in src/mqtt/
"
# Output: src/**/*.cpp, src/**/*.h

# Phase 5: VALIDATE (validator agent)
AGENT_NAME=validator AGENT_MODEL=haiku claude "
Run all tests and validate:
- Execute test suite
- Check for TODOs
- Check for mocks in production
- Verify against spec
"
# Output: reports/validation-report.md

# Phase 6: REVIEW (critic agent)
AGENT_NAME=critic AGENT_MODEL=opus claude "
Adversarial review of implementation:
- Security vulnerabilities
- Race conditions
- Resource leaks
- Edge case handling
"
# Output: reviews/firmware-review.md

# Phase 7: DELIVER (summarizer agent)
AGENT_NAME=summarizer AGENT_MODEL=haiku claude "
Synthesize final deliverable:
- Merge all documentation
- Create build instructions
- Generate API documentation
"
# Output: Final firmware package
```

---

### Step 4: Integration & Completion

Once all parallel components complete, integration begins:

```bash
# Return to main repo
cd ../env-monitor

# Merge all feature branches
git merge feature/hw-design
git merge feature/firmware
git merge feature/backend-api
git merge feature/dashboard
git merge feature/alerting

# Run integration
AGENT_NAME=orchestrator AGENT_MODEL=opus claude "Perform system integration:
- End-to-end communication test
- Deploy backend to staging
- Flash firmware to test device
- Verify dashboard displays live data
- Create deployment documentation"

# Cleanup worktrees
git worktree remove ../env-monitor-hw-design
git worktree remove ../env-monitor-backend-api
git worktree remove ../env-monitor-dashboard
git worktree remove ../env-monitor-firmware
git worktree remove ../env-monitor-alerting
```

---

### Final Dashboard Summary

```
┌─────────────────────────────────────────────────────────────────┐
│ Workflow: Environmental Monitor v1               ✓ COMPLETE     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Component          Status      Agent           Cost    Time    │
│  ─────────────────────────────────────────────────────────────  │
│  hw-design          ✓ DONE      planner         $0.42   23min  │
│  backend-api        ✓ DONE      implementer     $0.48   18min  │
│  dashboard          ✓ DONE      implementer     $0.41   22min  │
│  firmware           ✓ DONE      implementer     $0.79   31min  │
│  alerting           ✓ DONE      implementer     $0.32   15min  │
│  integration        ✓ DONE      orchestrator    $0.53   12min  │
│  ─────────────────────────────────────────────────────────────  │
│  TOTAL                                          $2.95   45min* │
│                                                                 │
│  * Wall-clock time (parallel execution)                        │
│    Sequential would have been ~121min                          │
│                                                                 │
│  Budget Status: $2.95 spent of $4.00 (26% buffer remaining)    │
│                                                                 │
│  Agents Used: planner, implementer, test-writer, validator,    │
│               critic, summarizer, orchestrator                  │
│  TDD Phases Completed: 42 (6 components × 7 phases)            │
│  Tests Written: 89                                             │
│  Tests Passing: 89                                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### Deliverables Generated

```
env-monitor/
├── README.md                      # Project overview
├── docs/
│   ├── hardware-spec.md           # Hardware requirements
│   ├── firmware-architecture.md   # Firmware design
│   ├── api-documentation.md       # Backend API
│   ├── deployment-guide.md        # How to deploy
│   └── user-manual.md             # End-user documentation
├── hardware/
│   ├── schematic.svg              # Circuit schematic
│   ├── wiring-diagram.svg         # Wiring diagram
│   └── bom.csv                    # Bill of materials
├── firmware/
│   ├── src/
│   │   ├── main.cpp               # Main firmware
│   │   ├── drivers/               # Sensor drivers
│   │   └── mqtt/                  # MQTT client
│   ├── tests/                     # Firmware tests
│   └── platformio.ini             # Build config
├── backend/
│   ├── main.py                    # FastAPI server
│   ├── alerts.py                  # Email alerting
│   ├── requirements.txt           # Dependencies
│   └── docker-compose.yml         # Deployment config
├── dashboard/
│   ├── index.html                 # Main page
│   ├── app.js                     # JavaScript logic
│   └── style.css                  # Styling
└── scripts/
    └── deploy.sh                  # Deployment script
```

---

## Key Concepts Demonstrated

| Concept | How It's Shown |
|---------|----------------|
| **Natural Language → Workflow** | User prompt decomposed into 6 components through conversation |
| **Parallel Execution** | 3 independent tracks run simultaneously (45min vs 121min) |
| **Git Worktrees** | Each component gets isolated workspace for parallel work |
| **Agent Tiers** | Opus for planning/review, Sonnet for implementation, Haiku for validation |
| **TDD Phases** | Each component goes through 7 phases (SPEC→DELIVER) |
| **Budget Tracking** | Per-component costs monitored, buffer for overruns |
| **Dependency Management** | firmware waits for hw-design, alerting waits for backend-api |
| **Dashboard Monitoring** | Real-time visibility into all active agents |

---

## Changelog

### v2.2 - Documentation Enhancement (Current)

- Updated test count from 61 to 225 (actual count across 8 test files)
- Improved cross-platform documentation for Windows/macOS/Linux
- Standardized Python command references for cross-platform compatibility
- Enhanced docstrings across all source modules
- Unified validation layer terminology (Six-Layer Validation)
- Added version and tier fields to all agent YAML frontmatter
- Created CHANGELOG.md for version tracking

### v2.1 - TDD Workflow Integration

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
- Added six-layer validation stack
- Integrated tiktoken for accurate token counting
- Added 3 new agents: planner, implementer, validator
- Created comprehensive test suite (225 tests across 8 files)

### v1.0 - Initial Release

- Basic event tracking and monitoring
- 14 agent definitions
- Terminal TUI and web dashboard
- SQLite event storage
