# Agent Dashboard v2.1

> **Quick Install:** `git clone https://github.com/Koplal/agent-dashboard.git && cd agent-dashboard && ./scripts/install.sh`
>
> **Platform-specific instructions:** See [INSTALL.md](INSTALL.md)
> **Troubleshooting:** See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

**Real-time monitoring and orchestration for Claude Code multi-agent workflows.**

A comprehensive multi-agent workflow framework implementing **Test-Driven Development (TDD)** with tiered model architecture (Opus/Sonnet/Haiku), cost governance, and six-layer validation. Built for production-grade AI workflows where tests define correctness.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.9+-green.svg)
![Claude](https://img.shields.io/badge/Claude-Code-purple.svg)

---

## Table of Contents

- [Features](#-features)
- [TDD Philosophy](#-tdd-philosophy)
- [Quick Start](#-quick-start)
- [Architecture](#-architecture)
- [Agent Registry](#-agent-registry-14-agents)
- [Repository Structure](#-repository-structure)
- [Dependencies](#-dependencies)
- [Configuration](#-configuration)
- [Workflow Engine](#-workflow-engine)
- [API Reference](#-api-reference)
- [Dashboard Features](#-dashboard-features)
- [Testing](#-testing)
- [Best Practices](#-best-practices)
- [Troubleshooting](#-troubleshooting)
- [Documentation](#-documentation)
- [Contributing](#-contributing)
- [License](#-license)

---

## Features

### Core Capabilities

| Feature | Description |
|---------|-------------|
| **TDD Workflow** | Test-Driven Development with immutable tests |
| **Multi-Agent Orchestration** | 14 specialized agents across 3 tiers (Opus/Sonnet/Haiku) |
| **Real-time Monitoring** | Terminal TUI (Rich) and Web Dashboard with WebSocket updates |
| **7-Phase Workflow** | SPEC → TEST_DESIGN → TEST_IMPL → IMPLEMENT → VALIDATE → REVIEW → DELIVER |
| **Cost Governance** | Circuit breaker pattern with budget enforcement |
| **Six-Layer Validation** | Static analysis, tests, TODO check, mock detection, integration, diff |

### What's New in v2.1

- **TDD Workflow Integration** - Tests define correctness, code must pass ALL tests
- **Test Immutability** - Tests become LOCKED after approval (cannot be modified)
- **7-Phase TDD Workflow** - SPEC → TEST_DESIGN → TEST_IMPL → IMPLEMENT → VALIDATE → REVIEW → DELIVER
- **TODO/Mock Detection** - Validation ensures NO TODOs and NO mocks in production code
- **Enhanced Agent Definitions** - TDD-focused planner, test-writer, implementer, validator
- **VS Code Integration** - Step-by-step instructions for IDE usage
- **61 Unit Tests** - Comprehensive test coverage across all components

---

## TDD Philosophy

The Agent Dashboard implements a strict Test-Driven Development workflow:

### Core Principles

```
┌─────────────────────────────────────────────────────────────────┐
│                    TDD CORE RULES                               │
├─────────────────────────────────────────────────────────────────┤
│  1. Tests define correctness - Code must pass ALL tests         │
│  2. Tests are IMMUTABLE - After lock, tests CANNOT change       │
│  3. NO TODOs - Production code must be complete                 │
│  4. NO mocks in production - Mocks only in test files           │
│  5. Auto-iterate - Keep implementing until ALL tests pass       │
└─────────────────────────────────────────────────────────────────┘
```

### The TDD Cycle

1. **Design the feature** - Define WHAT it does (SPEC phase)
2. **Design tests** - Create test cases from specification (TEST_DESIGN phase)
3. **Write tests FIRST** - Implement tests, they become IMMUTABLE (TEST_IMPL phase)
4. **Implement code** - Must pass ALL tests, cannot modify tests (IMPLEMENT phase)
5. **Validate** - Verify no TODOs, no mocks, all tests pass (VALIDATE phase)

### TDD Workflow Diagram

```
SPEC → TEST_DESIGN → TEST_IMPL → IMPLEMENT → VALIDATE → REVIEW → DELIVER
  │         │            │            │           │         │        │
  ▼         ▼            ▼            ▼           ▼         ▼        ▼
Define   Design      Write tests   Write code  Verify    Review   Ship
WHAT     tests       (LOCK them)   (pass tests) TDD rules quality
```

### Test Immutability

After the TEST_IMPL phase is approved, tests are **LOCKED**:

- Tests CANNOT be modified
- Tests CANNOT be deleted
- Tests CANNOT be skipped
- Implementation MUST make tests pass
- If tests are wrong, start a NEW workflow cycle

For detailed documentation, see [docs/WORKFLOW_FRAMEWORK.md](docs/WORKFLOW_FRAMEWORK.md).

---

## Quick Start

### Prerequisites

| Requirement | Version | Check Command |
|-------------|---------|---------------|
| Python | 3.9+ | `python3 --version` |
| pip or uv | Latest | `pip3 --version` or `uv --version` |
| Claude Code CLI | Latest | `claude --version` |

### Terminal Support

| Terminal | Platform | Support |
|----------|----------|---------|
| Bash | Linux, macOS, WSL | Full |
| Zsh | macOS (default), Linux | Full |
| Git Bash | Windows | Full |
| WSL2 | Windows | Full |
| PowerShell | Windows | Not supported (use WSL2/Git Bash) |
| CMD.exe | Windows | Not supported (use WSL2/Git Bash) |

### Installation

**Bash/Zsh Terminal:**
```bash
# Clone the repository
git clone https://github.com/your-username/agent-dashboard.git
cd agent-dashboard

# Run the automated installer
./scripts/install.sh
```

**VS Code Integrated Terminal:**
1. Open VS Code in the agent-dashboard directory
2. Open terminal: `Ctrl+`` (backtick) or `Cmd+`` on macOS
3. Select Bash/Zsh from terminal dropdown (not PowerShell)
4. Run: `./scripts/install.sh`

**Manual Installation:**
```bash
pip install rich aiohttp tiktoken
```

### Launch the Dashboard

```bash
# Terminal TUI dashboard
agent-dashboard

# Web dashboard (recommended)
agent-dashboard --web
# Open http://localhost:4200
```

### Quick Test

```bash
# Send a test event
agent-dashboard test

# Or manually test the API
curl http://localhost:4200/health
```

### See It In Action

Want to see how a simple prompt becomes a parallel multi-agent workflow?

**Example:** Turn "Help me create a microcontroller-based environmental monitoring project" into:
- 6 parallel workstreams with dependency management
- 7 specialized agents (planner, implementer, test-writer, validator, critic, summarizer, orchestrator)
- 42 TDD phase completions (6 components × 7 phases)
- 45 minutes wall-clock time (vs ~121min sequential)

See the [Complete Workflow Example](docs/WORKFLOW_FRAMEWORK.md#-end-to-end-example-from-prompt-to-parallel-execution)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        AGENT DASHBOARD                               │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │  Web Dashboard  │  │  Terminal TUI   │  │  REST API       │     │
│  │  (port 4200)    │  │  (Rich)         │  │  + WebSocket    │     │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘     │
│           └────────────────────┼────────────────────┘               │
│                                │                                     │
│  ┌─────────────────────────────┴─────────────────────────────┐     │
│  │                    WORKFLOW ENGINE                         │     │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │     │
│  │  │ Planner  │→ │ Tester   │→ │Implementer│→ │ Validator│   │     │
│  │  │ (Opus)   │  │ (Haiku)  │  │ (Sonnet)  │  │ (Haiku)  │   │     │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │     │
│  │                                                            │     │
│  │  ┌──────────────────────────────────────────────────────┐ │     │
│  │  │  Cost Circuit Breaker │ Four-Layer Validation Stack  │ │     │
│  │  └──────────────────────────────────────────────────────┘ │     │
│  └────────────────────────────────────────────────────────────┘     │
│                                │                                     │
│  ┌─────────────────────────────┴─────────────────────────────┐     │
│  │  SQLite Database │ Event Hooks │ Token Tracking (tiktoken)│     │
│  └────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Claude Code Session
    │
    ├─► PreToolUse/PostToolUse Hooks
    │       │
    │       ▼
    ├─► send_event.py (Token counting + cost estimation)
    │       │
    │       ▼
    └─► Dashboard Server (http://localhost:4200)
            │
            ├─► SQLite Database (persist events)
            ├─► WebSocket Broadcast (live updates)
            └─► REST API (query data)
```

### Workflow: From Prompt to Parallel Execution

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER PROMPT                                      │
│   "Help me create a microcontroller-based environmental monitoring"     │
└─────────────────────────────────────┬───────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR (Tier 1 - Opus)                         │
│   • Analyzes prompt & gathers requirements                              │
│   • Identifies components & dependencies                                │
│   • Creates dependency graph                                            │
│   • Allocates budget per component                                      │
└─────────────────────────────────────┬───────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
        ┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
        │   WORKTREE 1      │ │   WORKTREE 2      │ │   WORKTREE 3      │
        │   hw-design       │ │   backend-api     │ │   dashboard       │
        │   (planner)       │ │   (implementer)   │ │   (implementer)   │
        │                   │ │                   │ │                   │
        │ SPEC → TEST →     │ │ SPEC → TEST →     │ │ SPEC → TEST →     │
        │ IMPL → VALIDATE   │ │ IMPL → VALIDATE   │ │ IMPL → VALIDATE   │
        └─────────┬─────────┘ └─────────┬─────────┘ └─────────┬─────────┘
                  │                     │                     │
        ┌─────────▼─────────┐ ┌─────────▼─────────┐           │
        │   WORKTREE 4      │ │   WORKTREE 5      │           │
        │   firmware        │ │   alerting        │           │
        │   (implementer)   │ │   (implementer)   │           │
        └─────────┬─────────┘ └─────────┬─────────┘           │
                  │                     │                     │
                  └──────────┬──────────┴─────────────────────┘
                             ▼
              ┌─────────────────────────────────────┐
              │         INTEGRATION                  │
              │   (orchestrator - main worktree)    │
              │   • Merge all branches              │
              │   • End-to-end testing              │
              │   • Final delivery                  │
              └─────────────────────────────────────┘
```

---

## Agent Registry (14 Agents)

### Tier 1 - Opus (Strategic/Quality) `$$$`

| Agent | Symbol | Role | Description |
|-------|--------|------|-------------|
| `orchestrator` | ◆ | Coordinator | Multi-agent workflow coordination |
| `synthesis` | ◆ | Combiner | Research output synthesizer |
| `critic` | ◆ | Challenger | Quality assurance, devil's advocate |
| `planner` | ◆ | Strategist | Read-only planning (PLAN MODE) |

### Tier 2 - Sonnet (Analysis/Research) `$$`

| Agent | Symbol | Role | Description |
|-------|--------|------|-------------|
| `researcher` | ● | Analyst | Documentation-based research |
| `perplexity-researcher` | ● | Search | Real-time web search with citations |
| `research-judge` | ● | Evaluator | Research quality scoring |
| `claude-md-auditor` | ● | Auditor | Documentation file auditing |
| `implementer` | ● | Builder | Execute approved plans (IMPLEMENT MODE) |

### Tier 3 - Haiku (Execution/Routine) `$`

| Agent | Symbol | Role | Description |
|-------|--------|------|-------------|
| `web-search-researcher` | ○ | Searcher | Broad web searches |
| `summarizer` | ○ | Compressor | Output compression/distillation |
| `test-writer` | ○ | Tester | Automated test generation |
| `installer` | ○ | Setup | Installation and configuration |
| `validator` | ○ | Validator | Four-layer validation (VALIDATE MODE) |

### Visual Architecture

```
┌──────────────────────────────────────────────────────────────┐
│            TIER 1 - OPUS (Strategic/Quality)                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ orchestrator│  │  synthesis  │  │   critic    │          │
│  │     ◆       │  │     ◆       │  │     ◆       │          │
│  │ Coordinator │  │  Combiner   │  │  Challenger │          │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          │
│         │      ┌─────────┴───┐            │                  │
│         │      │   planner   │            │                  │
│         │      │      ◆      │            │                  │
│         │      └─────────────┘            │                  │
└─────────┼────────────────────────────────┼──────────────────┘
          │                                │
┌─────────┼────────────────────────────────┼──────────────────┐
│         │    TIER 2 - SONNET (Analysis)  │                  │
│  ┌──────▼──────┐  ┌─────────────┐  ┌─────▼───────┐          │
│  │  researcher │  │  perplexity │  │research-judge│         │
│  │     ●       │  │     ●       │  │     ●       │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
│  ┌─────────────┐  ┌─────────────┐                           │
│  │ md-auditor  │  │ implementer │                           │
│  │     ●       │  │     ●       │                           │
│  └─────────────┘  └─────────────┘                           │
└─────────────────────────────────────────────────────────────┘
          │
┌─────────┼───────────────────────────────────────────────────┐
│         │    TIER 3 - HAIKU (Execution)                     │
│  ┌──────▼──────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ web-search  │  │  summarizer │  │ test-writer │          │
│  │     ○       │  │     ○       │  │     ○       │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
│  ┌─────────────┐  ┌─────────────┐                           │
│  │  installer  │  │  validator  │                           │
│  │     ○       │  │     ○       │                           │
│  └─────────────┘  └─────────────┘                           │
└─────────────────────────────────────────────────────────────┘
```

---

## Repository Structure

```
agent-dashboard/
├── agents/                         # Agent definitions (14 agents)
│   ├── orchestrator.md             # ◆ Tier 1 - Strategic coordinator
│   ├── synthesis.md                # ◆ Tier 1 - Research synthesizer
│   ├── critic.md                   # ◆ Tier 1 - Devil's advocate
│   ├── planner.md                  # ◆ Tier 1 - Read-only planner
│   ├── researcher.md               # ● Tier 2 - Documentation research
│   ├── perplexity-researcher.md    # ● Tier 2 - Real-time search
│   ├── research-judge.md           # ● Tier 2 - Quality evaluation
│   ├── claude-md-auditor.md        # ● Tier 2 - Doc auditing
│   ├── implementer.md              # ● Tier 2 - Code execution
│   ├── web-search-researcher.md    # ○ Tier 3 - Web searches
│   ├── summarizer.md               # ○ Tier 3 - Compression
│   ├── test-writer.md              # ○ Tier 3 - Test generation
│   ├── installer.md                # ○ Tier 3 - Setup tasks
│   └── validator.md                # ○ Tier 3 - Validation stack
│
├── src/                            # Core Python modules
│   ├── cli.py                      # Unified CLI interface
│   ├── web_server.py               # Web dashboard + REST API
│   └── workflow_engine.py          # Multi-agent orchestration
│
├── dashboard/
│   └── agent_monitor.py            # Terminal TUI dashboard (Rich)
│
├── hooks/
│   └── send_event.py               # Event capture + token tracking
│
├── tests/                          # Test suite (61 tests)
│   ├── test_workflow_engine.py     # Workflow engine tests (39)
│   ├── test_send_event.py          # Event hook tests (22)
│   └── __init__.py
│
├── docs/                           # Documentation
│   ├── IMPLEMENTATION.md           # Complete deployment guide
│   └── WORKFLOW_FRAMEWORK.md       # Design patterns & governance
│
├── scripts/
│   └── install.sh                  # Automated installation
│
└── README.md                       # This file
```

---

## Dependencies

### Required

```
rich>=13.0.0        # Terminal UI rendering
aiohttp>=3.8.0      # Async web server + WebSocket
```

### Recommended

```
tiktoken>=0.5.0     # Accurate token counting (optional, falls back to estimation)
pytest>=7.0.0       # Testing framework (development)
pytest-asyncio      # Async test support (development)
```

### External Tools

| Tool | Purpose | Installation |
|------|---------|--------------|
| Claude Code CLI | Agent integration | [Install Guide](https://docs.anthropic.com/claude-code) |
| uv | Fast package manager | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| tmux | Background dashboard | `apt install tmux` or `brew install tmux` |

### Installation Commands

```bash
# Using pip
pip install rich aiohttp tiktoken

# Using uv (recommended)
uv pip install rich aiohttp tiktoken

# Development dependencies
pip install pytest pytest-asyncio
```

---

## ⚙️ Configuration

### Claude Code Hooks (`~/.claude/settings.json`)

> **Note:** The installer automatically creates and configures this file. This section is for reference only. If you skipped hook configuration during install, you can run `./scripts/install.sh` again.

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": ".*",
      "hooks": [{
        "type": "command",
        "command": "bash \"$HOME/.claude/dashboard/hooks/run_hook.sh\" --event-type PreToolUse --agent-name ${AGENT_NAME:-claude} --model ${AGENT_MODEL:-sonnet}"
      }]
    }],
    "PostToolUse": [{
      "matcher": ".*",
      "hooks": [{
        "type": "command",
        "command": "bash \"$HOME/.claude/dashboard/hooks/run_hook.sh\" --event-type PostToolUse --agent-name ${AGENT_NAME:-claude} --model ${AGENT_MODEL:-sonnet}"
      }]
    }],
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "bash \"$HOME/.claude/dashboard/hooks/run_hook.sh\" --event-type Stop --agent-name ${AGENT_NAME:-claude}"
      }]
    }]
  }
}
```

### Environment Variables

All environment variables are **optional** with sensible defaults.

| Variable | Default | When to Set |
|----------|---------|-------------|
| `AGENT_DASHBOARD_URL` | `http://127.0.0.1:4200/events` | Only if using non-default port |
| `AGENT_NAME` | `claude` | When running as a specific agent |
| `AGENT_MODEL` | `sonnet` | When running as a specific agent |
| `AGENT_PROJECT` | Auto-detected from git | Only if git detection fails |

**Example (only needed for agent sessions):**
```bash
export AGENT_NAME="orchestrator"
export AGENT_MODEL="opus"
claude
```

---

## Workflow Engine

### TDD Phases (Locked Gate Pattern)

```
SPEC → TEST_DESIGN → TEST_IMPL → IMPLEMENT → VALIDATE → REVIEW → DELIVER
  │         │            │            │           │         │        │
  ▼         ▼            ▼            ▼           ▼         ▼        ▼
Approval  Approval   LOCK TESTS   All Pass    TDD Check  Review   Done
                    (immutable)   Required    Required
```

| Phase | Agent | Model | Description | Checkpoint |
|-------|-------|-------|-------------|------------|
| SPEC | planner | Opus | Define WHAT the feature does (not how) | Approval required |
| TEST_DESIGN | test-writer | Sonnet | Design test cases from specification | Approval required |
| TEST_IMPL | test-writer | Haiku | Write tests (become IMMUTABLE) | **LOCK approval** |
| IMPLEMENT | implementer | Sonnet | Write code to pass locked tests | Auto (all tests pass) |
| VALIDATE | validator | Haiku | Run six-layer TDD validation | Auto (all pass) |
| REVIEW | critic | Opus | Critical review, verify spec compliance | Approval required |
| DELIVER | summarizer | Haiku | Generate summary, document limitations | None |

### TDD Rules (Enforced)

| Rule | Requirement | Enforced By |
|------|-------------|-------------|
| Tests define correctness | Code must pass ALL tests | validator |
| Tests are IMMUTABLE | After lock, cannot change | workflow engine |
| NO TODOs | Zero in production code | validator |
| NO mocks in production | Only in test files | validator |

### Cost Governance

#### Model Pricing (per million tokens)

| Model | Tier | Input | Output | Best For |
|-------|------|-------|--------|----------|
| Opus | 1 | $15.00 | $75.00 | Spec, review |
| Sonnet | 2 | $3.00 | $15.00 | Test design, implementation |
| Haiku | 3 | $0.25 | $1.25 | Test impl, validation |

#### Circuit Breaker Thresholds

| Threshold | Action |
|-----------|--------|
| 50% | First warning |
| 75% | Second warning |
| 90% | Final warning |
| 100% | Circuit breaks (manual reset required) |

### Six-Layer TDD Validation Stack

| Layer | Check | Requirement |
|-------|-------|-------------|
| 1. Static Analysis | Type checking, linting | Zero errors |
| 2. Test Suite | All tests execution | 100% passing |
| 3. TODO/FIXME Check | Production code scan | Zero found |
| 4. Mock Detection | Production code scan | Zero found |
| 5. Integration Sandbox | Isolated execution | Pass or skip |
| 6. Behavioral Diff | Human-readable changes | Complete |

### CLI Usage

```bash
# Create workflow from task
python3 src/workflow_engine.py from-task "Add user authentication"

# Check budget status
python3 src/workflow_engine.py budget

# Generate governance document
python3 src/workflow_engine.py governance <workflow_id> -o CLAUDE.md
```

---

## API Reference

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web dashboard |
| `/events` | POST | Receive events from hooks |
| `/api/events` | GET | Get recent events |
| `/api/sessions` | GET | Get active sessions |
| `/api/stats` | GET | Get statistics |
| `/health` | GET | Health check |
| `/ws` | WebSocket | Live updates |

### Workflow Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/workflow` | POST | Create workflow from task |
| `/api/workflow` | GET | List all workflows |
| `/api/workflow/{id}` | GET | Get workflow status |
| `/api/workflow/{id}/prompt` | GET | Get orchestrator prompt |
| `/api/workflow/{id}/governance` | GET | Get CLAUDE.md governance |
| `/api/budget` | GET | Get budget status |

### Example Requests

```bash
# Health check
curl http://localhost:4200/health

# Create a workflow
curl -X POST http://localhost:4200/api/workflow \
  -H "Content-Type: application/json" \
  -d '{"task": "Add user authentication", "budget": 2.0}'

# Get budget status
curl http://localhost:4200/api/budget

# Send test event
curl -X POST http://localhost:4200/events \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "orchestrator",
    "event_type": "TaskStart",
    "session_id": "test-123",
    "project": "test-project",
    "model": "opus",
    "payload": {"task": "Test task"}
  }'
```

---

## Dashboard Features

### Terminal TUI (`agent-dashboard`)

- Real-time event timeline
- Active session tracking
- Token usage and cost monitoring
- Agent tier visualization (◆●○)
- Color-coded agents

### Web Dashboard (`agent-dashboard --web`)

- WebSocket live updates
- Interactive session cards
- Event filtering by type/agent
- 24-hour statistics
- Agent registry with tier information

---

## Testing

### Running Tests

```bash
# Run all tests (61 total)
python3 -m pytest tests/ -v

# Run specific test file
python3 -m pytest tests/test_workflow_engine.py -v

# Run with coverage
python3 -m pytest tests/ --cov=src --cov=hooks --cov-report=html
```

### Test Coverage

| File | Tests | Coverage Areas |
|------|-------|----------------|
| `test_workflow_engine.py` | 39 | Circuit breaker, tasks, workflows, validation |
| `test_send_event.py` | 22 | Token estimation, cost calculation, session management |

### Verification Commands

```bash
# Verify imports
python3 -c "from src.workflow_engine import WorkflowEngine; print('OK')"

# Test event sending (cross-platform)
bash ~/.claude/dashboard/hooks/run_hook.sh --event-type PreToolUse --agent-name test

# Direct Python (development only)
python3 hooks/send_event.py --event-type PreToolUse --agent-name test

# Check API health
curl http://localhost:4200/health
```

---

## Best Practices

### Agent Selection

| Task Type | Recommended Agent | Tier |
|-----------|-------------------|------|
| Complex planning | `planner` | Opus |
| Research synthesis | `orchestrator` → `synthesis` | Opus |
| Quality review | `critic` | Opus |
| Code implementation | `implementer` | Sonnet |
| Documentation research | `researcher` | Sonnet |
| Real-time search | `perplexity-researcher` | Sonnet |
| Test generation | `test-writer` | Haiku |
| Validation | `validator` | Haiku |
| Quick summaries | `summarizer` | Haiku |

### Cost Optimization

1. **Start with Haiku** for routine tasks (validation, summarization)
2. **Use Sonnet** for implementation and research
3. **Reserve Opus** for strategic planning and critical review
4. **Monitor budget** via `/api/budget` endpoint

### Workflow Execution

1. **Always start with PLAN phase** - Read-only exploration first
2. **Write tests before implementation** - TDD pattern
3. **Validate after each change** - Four-layer stack
4. **Use checkpoints** - Human approval at critical points

### Monitoring

1. **Keep dashboard running** during development
2. **Review token usage** to optimize costs
3. **Check critic findings** before accepting changes
4. **Run auditor** regularly on documentation

---

## Troubleshooting

### Events Not Appearing

```bash
# 1. Check server is running
curl http://localhost:4200/health

# 2. Test event sending manually (cross-platform)
bash ~/.claude/dashboard/hooks/run_hook.sh \
  --event-type PreToolUse --agent-name test

# Or direct Python (development only)
# python3 ~/.claude/dashboard/hooks/send_event.py --event-type PreToolUse --agent-name test

# 3. Check hook permissions
chmod +x ~/.claude/dashboard/hooks/send_event.py
```

### Dashboard Won't Start

```bash
# 1. Check port availability
lsof -i :4200

# 2. Verify dependencies
pip3 install rich aiohttp tiktoken

# 3. Try alternative port
agent-dashboard --web --port 4201
```

### Token Counting Issues

```bash
# Tiktoken falls back to character-based estimation if network restricted
python3 -c "
from hooks.send_event import estimate_tokens, _TIKTOKEN_AVAILABLE
print(f'Tiktoken available: {_TIKTOKEN_AVAILABLE}')
print(f'Test estimate: {estimate_tokens(\"Hello world\")} tokens')
"
```

For more troubleshooting, see [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md#troubleshooting).

---

## Documentation

| Document | Description |
|----------|-------------|
| [README.md](README.md) | Quick start and overview (this file) |
| [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md) | Complete deployment guide with project integration |
| [docs/WORKFLOW_FRAMEWORK.md](docs/WORKFLOW_FRAMEWORK.md) | Design patterns, governance, and validation architecture |

### Quick Links

- **Installation**: [Quick Start](#-quick-start) | [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md#installation)
- **Configuration**: [Configuration](#-configuration) | [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md#configuration)
- **Agent Setup**: [Agent Registry](#-agent-registry-14-agents) | [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md#agent-setup)
- **API Reference**: [API Reference](#-api-reference) | [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md#api-reference)
- **Workflow Engine**: [Workflow Engine](#-workflow-engine) | [docs/WORKFLOW_FRAMEWORK.md](docs/WORKFLOW_FRAMEWORK.md)
- **Testing**: [Testing](#-testing) | [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md#testing)
- **Troubleshooting**: [Troubleshooting](#-troubleshooting) | [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md#troubleshooting)

---

## 📖 Glossary

| Term | Definition |
|------|------------|
| **Agent** | A named Claude session with a specific role (e.g., orchestrator, researcher). Used for dashboard monitoring and identification—does not change Claude's behavior. |
| **Tier** | Model capability level: Tier 1 (Opus/strategic), Tier 2 (Sonnet/analysis), Tier 3 (Haiku/execution) |
| **Workflow** | A structured task breakdown using TDD phases, created via the Workflow Engine API |
| **Phase** | A stage in the TDD workflow: SPEC → TEST_DESIGN → TEST_IMPL → IMPLEMENT → VALIDATE → REVIEW → DELIVER |
| **Hook** | A Claude Code callback that sends events to the dashboard when tools are used |
| **Event** | A notification sent to the dashboard (PreToolUse, PostToolUse, UserPromptSubmit, Stop, SubagentStop) |

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Run tests (`python3 -m pytest tests/ -v`)
5. Submit a pull request

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Acknowledgments

- [Claude Code Hooks Multi-Agent Observability](https://github.com/disler/claude-code-hooks-multi-agent-observability) - Inspiration for hooks-based monitoring
- [Rich](https://github.com/Textualize/rich) - Beautiful terminal formatting
- [Anthropic](https://anthropic.com) - Claude models and documentation

---

Built for quality-focused AI workflows
