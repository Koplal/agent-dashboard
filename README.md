# Agent Dashboard v2.5.1

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
- [Agent Registry](#-agent-registry-20-agents)
- [Panel Judge Workflow](#-panel-judge-workflow)
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
| **Multi-Agent Orchestration** | 22 specialized agents across 3 tiers (Opus/Sonnet/Haiku) |
| **Real-time Monitoring** | Terminal TUI (Rich) and Web Dashboard with WebSocket updates |
| **7-Phase Workflow** | SPEC → TEST_DESIGN → TEST_IMPL → IMPLEMENT → VALIDATE → REVIEW → DELIVER |
| **Cost Governance** | Circuit breaker pattern with budget enforcement |
| **Six-Layer Validation** | Static analysis, tests, TODO check, mock detection, integration, diff |

### What's New in v2.5.0 - Agent Optimization

All 22 agent definitions upgraded to v2.4.0 with comprehensive quality improvements based on systematic prompt engineering analysis.

#### Quality-First Enhancements
- **5-Judge Panel Minimum** - Panel evaluations now require minimum 5 judges (quality floor), expandable to 7 for high-stakes tasks
- **62+ New Constraints** - Standardized ALWAYS/NEVER format across all agents
- **Evidence-Citing Requirements** - All panel judges must cite specific evidence for every finding
- **Few-Shot Examples** - 18+ examples added to Tier 1 agents and all panel judges

#### Safety Mechanisms
- **Iteration Limits** - Orchestrator (5 rounds), Implementer (50 iterations), Critic (3 rounds), Web-search (10 queries)
- **Test File Protection** - Implementer detects and rejects test file modifications during implementation
- **Escalation Protocols** - Clear timeout handling, scope expansion checkpoints, and failure escalation paths
- **Research Caching** - Documented caching pattern to reduce redundant research (20-30% savings)

#### Workflow Improvements
- **Standardized Handoff Schemas** - All researcher agents output structured JSON for synthesis
- **Verification Gates** - Planner specs require panel review for high-complexity/security features
- **Unresolvable Conflict Handling** - Synthesis explicitly marks conflicts that cannot be reconciled

#### Panel Review
All changes approved by 5-judge panel: **4.4/5 mean score, 5 PASS votes**

### What's New in v2.4.x

#### Collapsible Project Grouping (v2.4.1)
- **Collapsible Project Groups** - Click project headers to expand/collapse agent lists
- **Expand All / Collapse All** - Controls at the top of Active Sessions panel
- **Enhanced Project Metrics** - Total tokens, cost, execution time, and time since last activity
- **Project Status Indicators** - Visual status (active/idle/inactive) with color-coded dots
- **Nested Scrolling** - Independent scrolling for projects container and agent lists
- **State Persistence** - Collapse/expand states preserved during real-time updates

#### Dynamic Viewport Height
- **100vh Dashboard** - Fills entire browser viewport on any screen size (1080p to 4K)
- **Flexbox Layout** - Panels grow proportionally to fill available space
- **Responsive Scaling** - Adapts seamlessly across display resolutions

#### UI Layout Improvements
- **Optimized Grid** - 3-column layout with wider right pane for agent names (1fr 0.9fr 380px)
- **Compact Statistics** - Panel sized to fit content only
- **Color-Coded Models** - Opus (purple), Sonnet (blue), Haiku (green) badges

#### Backend Enhancements
- **New API Endpoint** - `GET /api/sessions/grouped` returns sessions with project aggregates
- **Subagent Tracking** - Proper extraction and display of spawned subagent names
- **Session Timing** - Accurate duration tracking via start_time field

### What's New in v2.3

- **Improved Token Counting** - Fixed accuracy by extracting content from multiple payload fields
- **Project Grouping** - Dashboard sessions are now grouped by project for better organization
- **Responsive Dashboard** - Better scaling from mobile (320px) to 4K (3840px) screens
- **Dynamic Agent Sync** - Agents are now automatically discovered from `/agents/*.md` files
- **Formatted Agent Names** - Agent names display properly formatted (capitalized, no hyphens)
- **New API Endpoint** - `GET /api/agents` returns dynamically scanned agent registry

### What's New in v2.2

- **225 Unit Tests** - Comprehensive test coverage across 8 test modules
- **Cross-Platform Documentation** - Improved Windows/macOS/Linux compatibility guidance
- **Six-Layer Validation** - Unified validation terminology across all documentation
- **Enhanced Docstrings** - Version information added to all source modules
- **Standardized Agents** - Version and tier fields added to all agent definitions

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
git clone https://github.com/Koplal/agent-dashboard.git
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
│  │  │  Cost Circuit Breaker │ Six-Layer Validation Stack   │ │     │
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

## Agent Registry (22 Agents)

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

### Panel Judges (Tier 2 - Sonnet) `$$`

The Panel Judge system provides automated quality evaluation for non-testable work products. Judges are spawned in parallel by the panel-coordinator based on task risk scoring.

| Agent | Symbol | Role | Description |
|-------|--------|------|-------------|
| `panel-coordinator` | ● | Coordinator | Orchestrates panels with automatic size selection |
| `judge-technical` | ● | Tech Judge | Technical accuracy and feasibility |
| `judge-completeness` | ● | Coverage Judge | Completeness and gap analysis |
| `judge-practicality` | ● | Practicality Judge | Real-world usefulness and clarity |
| `judge-adversarial` | ● | Attack Judge | Stress-testing and vulnerability finding |
| `judge-user` | ● | User Judge | End-user perspective and experience |

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

## Panel Judge Workflow

The Panel Judge system automatically scales quality evaluation based on task risk. It evaluates **non-testable work products** (plans, designs, documentation, decisions) where unit tests cannot verify correctness.

### Risk Scoring

Tasks are scored on 4 factors to determine panel size:

| Factor | Low | Medium | High |
|--------|-----|--------|------|
| **Reversibility** | Reversible (0) | - | Irreversible (4) |
| **Blast Radius** | Internal (0) | Team (1), Org (2) | External (3) |
| **Domain** | Business/Software (1) | - | Hardware/Mixed (2) |
| **Impact** | Low (0) | Medium (1), High (2) | Critical (4) |

### Panel Size Selection

> **Quality-First Policy (v2.5.0):** Minimum panel size is now 5 judges. Panel cannot be reduced below 5 but can expand to 7 for high-stakes evaluations.

| Risk Score | Panel Size | Judges |
|------------|------------|--------|
| 0-7 (Standard) | 5 judges | technical, completeness, practicality, adversarial, user |
| 8+ (High Stakes) | 7 judges | + domain-expert, risk |

### Workflow Sequence

```
1. TRIGGER → Task requires quality evaluation (non-testable work product)
2. SCORE   → Calculate risk from metadata or infer from keywords
3. SELECT  → Determine panel size (3, 5, or 7 judges)
4. SPAWN   → Launch judges in PARALLEL (all receive identical input)
5. EVALUATE → Each judge scores independently (max 500 tokens each)
6. AGGREGATE → Collect verdicts, calculate consensus level
7. VERDICT → Apply majority voting rules
8. REPORT  → Generate audit trail with recommendations
```

### Verdict Rules

| Verdict | Condition |
|---------|-----------|
| **APPROVED** | Majority PASS, no FAIL votes |
| **CONDITIONAL** | Majority PASS/CONDITIONAL, max 1 FAIL |
| **REVISION REQUIRED** | Majority CONDITIONAL or 2+ FAILs |
| **REJECTED** | Majority FAIL |

### Override Policy

- Users **CAN** escalate panel size (request 7 judges)
- Users **CANNOT** downgrade below 5 judges (quality floor)
- All overrides are logged for audit
- Panel expansion is encouraged for complex or high-stakes evaluations

### Triggering a Panel Evaluation

Panel evaluations are triggered when:
- A task is flagged as non-testable (plans, designs, documentation)
- The orchestrator delegates quality review for critical decisions
- A user explicitly requests panel evaluation via the API

```bash
# Example: Create a panel evaluation via API
curl -X POST http://localhost:4200/api/panel \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "API redesign proposal",
    "description": "Breaking change to authentication endpoints",
    "metadata": {
      "reversible": false,
      "blast_radius": "external",
      "domain": "software",
      "impact": "high"
    }
  }'
```

---

## Repository Structure

```
agent-dashboard/
├── agents/                         # Agent definitions (20 agents)
│   ├── orchestrator.md             # ◆ Tier 1 - Strategic coordinator
│   ├── synthesis.md                # ◆ Tier 1 - Research synthesizer
│   ├── critic.md                   # ◆ Tier 1 - Devil's advocate
│   ├── planner.md                  # ◆ Tier 1 - Read-only planner
│   ├── researcher.md               # ● Tier 2 - Documentation research
│   ├── perplexity-researcher.md    # ● Tier 2 - Real-time search
│   ├── research-judge.md           # ● Tier 2 - Quality evaluation
│   ├── claude-md-auditor.md        # ● Tier 2 - Doc auditing
│   ├── implementer.md              # ● Tier 2 - Code execution
│   ├── panel-coordinator.md        # ● Tier 2 - Panel orchestration
│   ├── judge-technical.md          # ● Tier 2 - Technical accuracy
│   ├── judge-completeness.md       # ● Tier 2 - Coverage evaluation
│   ├── judge-practicality.md       # ● Tier 2 - Usefulness evaluation
│   ├── judge-adversarial.md        # ● Tier 2 - Stress testing
│   ├── judge-user.md               # ● Tier 2 - User perspective
│   ├── web-search-researcher.md    # ○ Tier 3 - Web searches
│   ├── summarizer.md               # ○ Tier 3 - Compression
│   ├── test-writer.md              # ○ Tier 3 - Test generation
│   ├── installer.md                # ○ Tier 3 - Setup tasks
│   └── validator.md                # ○ Tier 3 - Validation stack
│
├── src/                            # Core Python modules
│   ├── cli.py                      # Unified CLI interface
│   ├── web_server.py               # Web dashboard + REST API
│   ├── workflow_engine.py          # Multi-agent orchestration
│   ├── token_counter.py            # Token counting with tiered fallback
│   ├── validation.py               # Six-layer validation stack
│   ├── compression_gate.py         # Token budgeting for handoffs
│   ├── panel_selector.py           # Judge panel selection logic
│   └── synthesis_validator.py      # Synthesis output validation
│
├── dashboard/
│   └── agent_monitor.py            # Terminal TUI dashboard (Rich)
│
├── hooks/
│   └── send_event.py               # Event capture + token tracking
│
├── tests/                          # Test suite (9 test files)
│   ├── test_workflow_engine.py     # Workflow engine tests (39)
│   ├── test_compression_gate.py    # Compression gate tests (37)
│   ├── test_synthesis_validator.py # Synthesis validator tests (32)
│   ├── test_panel_selector.py      # Panel selection tests (31)
│   ├── test_validation.py          # Base validation tests (31)
│   ├── test_send_event.py          # Event hook tests (22)
│   ├── test_cross_platform.py      # Cross-platform tests (20)
│   ├── test_token_counter.py       # Token counting tests (24)
│   ├── test_integration.py         # Integration tests (13)
│   └── __init__.py
│
├── docs/                           # Documentation
│   ├── EXAMPLE_USAGE.md            # Complete usage guide with examples
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
aiohttp>=3.9.0      # Async web server + WebSocket
```

### Recommended

```
transformers>=4.35.0  # Claude tokenizer (recommended, ~95% accuracy)
tokenizers>=0.15.0    # Required by transformers
tiktoken>=0.5.0       # Fallback tokenizer (~70-85% accuracy)
pytest>=7.0.0         # Testing framework (development)
pytest-asyncio        # Async test support (development)
```

---

## Token Counting

Agent Dashboard uses accurate Claude tokenization for cost estimation and budget governance.

### Tokenizer Priority

The system uses a tiered fallback approach:

| Priority | Tokenizer | Accuracy | Install |
|----------|-----------|----------|---------|
| 1 | Xenova/claude-tokenizer | ~95%+ | `pip install transformers tokenizers` |
| 2 | Anthropic API | 100% | `pip install anthropic` + API key |
| 3 | tiktoken (fallback) | ~70-85% | `pip install tiktoken` |
| 4 | Character estimation | ~60-70% | Built-in |

### Check Tokenizer Status

```bash
agent-dashboard tokenizer
```

### Recommended Installation

For best accuracy without API calls:
```bash
pip install transformers tokenizers
```

### Usage in Code

```python
from src.token_counter import count_tokens, estimate_cost, get_tokenizer_info

# Count tokens
tokens = count_tokens("Hello, world!")

# Get cost estimate
cost = estimate_cost(input_tokens=1000, output_tokens=500, model="claude-sonnet-4-5")

# Check which tokenizer is active
info = get_tokenizer_info()
print(f"Using: {info.name} ({info.accuracy})")
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

> **Rate Limits:** The local dashboard server has no rate limits. All endpoints accept unlimited requests. For production deployments, consider adding rate limiting via a reverse proxy (nginx, Caddy) if exposing the API externally.

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web dashboard |
| `/events` | POST | Receive events from hooks |
| `/api/events` | GET | Get recent events |
| `/api/sessions` | GET | Get active sessions |
| `/api/stats` | GET | Get statistics |
| `/api/agents` | GET | Get registered agents (dynamically scanned) |
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

### Panel Judge Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/panel` | POST | Create panel evaluation for non-testable work |
| `/api/panel/{id}` | GET | Get panel evaluation status and results |

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

### Web Dashboard Layout

The web dashboard uses a responsive 3-column grid layout that fills the viewport:

```
+-----------------------------------------------------------------------------------+
|                              Agent Dashboard Header                                |
|  [Live] Uptime: 00:00:00  Port: 4200  [Restart] [Stop]                           |
+-----------------------------------------------------------------------------------+
|                          |                        |                               |
|   Active Sessions (1fr)  |  Event Timeline (0.9fr)|  Statistics + Agents (380px) |
|                          |                        |                               |
|  +--------------------+  |  +------------------+  |  +------------------------+  |
|  | [Expand] [Collapse]|  |  | 12:34:56 Tool... |  |  | Events: 1,234          |  |
|  +--------------------+  |  | 12:34:55 Read... |  |  | Sessions: 12           |  |
|  |                    |  |  | 12:34:54 Bash... |  |  | Tokens: 45.2K          |  |
|  | > project-alpha    |  |  | ...              |  |  | Cost: $0.1234          |  |
|  |   [3 agents] $0.05 |  |  +------------------+  |  | Active: 3              |  |
|  |   +- orchestrator  |  |                        |  +------------------------+  |
|  |   +- researcher    |  |                        |  |                        |  |
|  |   +- implementer   |  |                        |  | Registered Agents      |  |
|  |                    |  |                        |  | [Refresh]              |  |
|  | v project-beta     |  |                        |  | > orchestrator [opus]  |  |
|  |   (collapsed)      |  |                        |  | > researcher [sonnet]  |  |
|  |                    |  |                        |  | > summarizer [haiku]   |  |
|  +--------------------+  |                        |  +------------------------+  |
|                          |                        |                               |
+-----------------------------------------------------------------------------------+
```

**Grid Configuration:** `grid-template-columns: 1fr 0.9fr 380px`

### Terminal TUI (`agent-dashboard`)

- Real-time event timeline
- Active session tracking
- Token usage and cost monitoring
- Agent tier visualization (diamond/circle/outline)
- Color-coded agents

### Web Dashboard (`agent-dashboard --web`)

#### Core Features
- WebSocket live updates
- Interactive session cards
- Event filtering by type/agent
- 24-hour statistics

#### Project Organization (v2.4)
- **Collapsible Project Groups** - Click to expand/collapse agent lists per project
- **Project Aggregates** - Total tokens, cost, execution time per project
- **Expand/Collapse All** - Quick controls to manage all project groups
- **Project Status Indicators** - Visual activity status (active/idle/inactive)
- **Nested Scrolling** - Projects container and agent lists scroll independently

#### Display Features
- **Dynamic Viewport Height** - Dashboard fills 100vh, scales on any screen
- **Dynamic Agent Registry** - Agents scanned from `/agents/*.md` files
- **Responsive Design** - Scales from mobile (320px) to 4K (3840px)
- **Formatted Names** - Agent names properly capitalized and formatted
- **Color-Coded Model Badges** - Opus (purple), Sonnet (blue), Haiku (green)

#### Dashboard Controls
- **Restart Button** - Restart the dashboard server
- **Shutdown Button** - Stop the dashboard server

---

## Testing

### Running Tests

```bash
# Run all tests (249 total)
# Use 'python' on Windows, 'python3' on Linux/macOS
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_workflow_engine.py -v

# Run with coverage
python -m pytest tests/ --cov=src --cov=hooks --cov-report=html
```

> **Cross-Platform Note:** Use `python` on Windows (Git Bash/PowerShell), `python3` on Linux/macOS. Most modern Python installations alias both commands.

### Test Coverage

| File | Tests | Coverage Areas |
|------|-------|----------------|
| `test_workflow_engine.py` | 39 | Circuit breaker, tasks, workflows, TDD phases |
| `test_compression_gate.py` | 37 | Compression gating, token estimation, handoff validation |
| `test_synthesis_validator.py` | 32 | Synthesis validation, finding consolidation |
| `test_panel_selector.py` | 31 | Panel selection, judge scoring, consensus |
| `test_validation.py` | 31 | Base validation, handoff schema, validation actions |
| `test_token_counter.py` | 24 | Token counting, tokenizer fallback, cost estimation |
| `test_send_event.py` | 22 | Token estimation, cost calculation, event sending |
| `test_cross_platform.py` | 20 | Cross-platform compatibility, Python detection |
| `test_integration.py` | 13 | End-to-end integration, API endpoints |
| **Total** | **249** | |

### Verification Commands

```bash
# Verify imports (use 'python' on Windows, 'python3' on Linux/macOS)
python -c "from src.workflow_engine import WorkflowEngine; print('OK')"

# Test event sending (cross-platform)
bash ~/.claude/dashboard/hooks/run_hook.sh --event-type PreToolUse --agent-name test

# Direct Python (development only)
python hooks/send_event.py --event-type PreToolUse --agent-name test

# Check API health
curl http://localhost:4200/health
```

> **Windows Users:** If `python` is not recognized, ensure Python is in your PATH or use the full path (e.g., `py -m pytest tests/ -v`).

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
3. **Validate after each change** - Six-layer validation stack
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
| [docs/EXAMPLE_USAGE.md](docs/EXAMPLE_USAGE.md) | **Complete usage guide with examples and hook troubleshooting** |
| [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md) | Complete deployment guide with project integration |
| [docs/WORKFLOW_FRAMEWORK.md](docs/WORKFLOW_FRAMEWORK.md) | Design patterns, governance, and validation architecture |

### Quick Links

- **Getting Started**: [docs/EXAMPLE_USAGE.md](docs/EXAMPLE_USAGE.md) (recommended first read)
- **Installation**: [Quick Start](#-quick-start) | [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md#installation)
- **Configuration**: [Configuration](#-configuration) | [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md#configuration)
- **Agent Setup**: [Agent Registry](#-agent-registry-20-agents) | [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md#agent-setup)
- **API Reference**: [API Reference](#-api-reference) | [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md#api-reference)
- **Workflow Engine**: [Workflow Engine](#-workflow-engine) | [docs/WORKFLOW_FRAMEWORK.md](docs/WORKFLOW_FRAMEWORK.md)
- **Testing**: [Testing](#-testing) | [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md#testing)
- **Hook Issues**: [docs/EXAMPLE_USAGE.md#troubleshooting-hooks](docs/EXAMPLE_USAGE.md#troubleshooting-hooks)
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

## Research References

The agent prompts and workflow architecture are informed by systematic analysis of prompt engineering research.

### Academic Sources

| Technique | Paper | Application |
|-----------|-------|-------------|
| **Chain-of-Verification** | Dhuliawala et al. (2023), Meta AI | Researcher verification loops |
| **Tree of Thoughts** | Yao et al. (2023), Princeton/DeepMind | Parallel research delegation |
| **Self-Consistency** | Wang et al. (2022), Google | Panel judge consensus voting |
| **ReAct Prompting** | Yao et al. (2022), Princeton/Google | Agent tool use patterns |

### Internal Analysis Documents

| Document | Purpose |
|----------|---------|
| [Agent Optimization Report](AGENT_OPTIMIZATION_REPORT.md) | Systematic analysis of 22 agent prompts |
| [Orchestrator Prompt](Research_Prompts/AGENT_OPTIMIZATION_ORCHESTRATOR_PROMPT.md) | Prompt used to analyze agent architecture |
| [Critical Analysis Report](Research_Prompts/Prompt%20Engineering%20Reports/CRITICAL_ANALYSIS_COGNITIVE_ARCHITECTURES_REPORT.md) | Source verification of prompt engineering claims |

---

## Acknowledgments

- [Claude Code Hooks Multi-Agent Observability](https://github.com/disler/claude-code-hooks-multi-agent-observability) - Inspiration for hooks-based monitoring
- [Rich](https://github.com/Textualize/rich) - Beautiful terminal formatting
- [Anthropic](https://anthropic.com) - Claude models and documentation
- Academic researchers whose work informed the prompt engineering approach

---

Built for quality-focused AI workflows
