# Agent Dashboard v2.1 Implementation Guide

Complete guide for deploying the Agent Dashboard multi-agent workflow framework on any project.

## Terminal Requirements

This guide assumes you are using a **Bash-compatible terminal**:

| Terminal | Platform | Supported |
|----------|----------|-----------|
| Bash | Linux, macOS, WSL | Yes |
| Zsh | macOS (default), Linux | Yes |
| Git Bash | Windows | Yes |
| WSL2 | Windows | Yes |
| PowerShell | Windows | No (use WSL2 or Git Bash) |
| CMD.exe | Windows | No (use WSL2 or Git Bash) |

**VS Code Users:** Open the integrated terminal (`Ctrl+\`` or `Cmd+\``) and select Bash/Zsh from the terminal dropdown.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Workflow Engine](#workflow-engine)
6. [Agent Setup](#agent-setup)
7. [API Reference](#api-reference)
8. [Testing](#testing)
9. [Project Integration Guide](#project-integration-guide)
10. [Troubleshooting](#troubleshooting)

---

## Overview

The Agent Dashboard is a multi-agent workflow orchestration system for Claude Code that provides:

- **Real-time Monitoring** - Track agent activities, token usage, and costs
- **Workflow Orchestration** - Multi-phase task execution with governance
- **Cost Governance** - Budget enforcement with circuit breaker pattern
- **Accurate Token Tracking** - Tiktoken-based token counting (cl100k_base encoding)
- **Four-Layer Validation** - Automated quality assurance pipeline
- **14 Specialized Agents** - Tiered by model (Opus/Sonnet/Haiku) for cost optimization

### Architecture

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

---

## Prerequisites

### Required

| Requirement | Version | Check Command |
|-------------|---------|---------------|
| Python | 3.9+ | `python3 --version` |
| pip/uv | Latest | `pip3 --version` or `uv --version` |
| Claude Code CLI | Latest | `claude --version` |

### Recommended

| Tool | Purpose | Install |
|------|---------|---------|
| uv | Fast package manager | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| tmux | Background dashboard | `apt install tmux` or `brew install tmux` |
| tiktoken | Accurate token counting | `pip install tiktoken` |

### Python Dependencies

```
rich>=13.0.0      # Terminal UI
aiohttp>=3.8.0    # Web server
tiktoken>=0.5.0   # Token counting (optional, falls back to estimation)
pytest>=7.0.0     # Testing (development)
```

---

## Installation

### Method 1: Automated Installation (Recommended)

```bash
# Clone the repository
git clone https://github.com/Koplal/agent-dashboard.git
cd agent-dashboard

# Run installer
./scripts/install.sh
```

The installer will:
1. Create `~/.claude/dashboard/` with all components
2. Install 14 agent definitions to `~/.claude/agents/`
3. Configure Claude Code hooks in `~/.claude/settings.json`
4. Install Python dependencies (rich, aiohttp, tiktoken)
5. Add `agent-dashboard` command to PATH

### Method 2: Manual Installation

```bash
# Create directories
mkdir -p ~/.claude/dashboard/hooks
mkdir -p ~/.claude/agents

# Copy dashboard files
cp dashboard/agent_monitor.py ~/.claude/dashboard/
cp src/web_server.py ~/.claude/dashboard/
cp src/workflow_engine.py ~/.claude/dashboard/
cp src/cli.py ~/.claude/dashboard/
cp hooks/send_event.py ~/.claude/dashboard/hooks/

# Copy agent definitions
cp agents/*.md ~/.claude/agents/

# Install dependencies
pip3 install rich aiohttp tiktoken

# Create launcher
cat > ~/.local/bin/agent-dashboard << 'EOF'
#!/usr/bin/env bash
python3 ~/.claude/dashboard/cli.py "$@"
EOF
chmod +x ~/.local/bin/agent-dashboard
```

### Method 3: Development Installation

```bash
cd agent-dashboard

# Install in development mode
pip3 install -e .

# Run tests to verify
python3 -m pytest tests/ -v
```

---

## Configuration

### Claude Code Hooks (~/.claude/settings.json)

> **Note:** The installer automatically creates and configures this file. This section is for reference only.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "bash \"$HOME/.claude/dashboard/hooks/run_hook.sh\" --event-type PreToolUse --agent-name ${AGENT_NAME:-claude} --model ${AGENT_MODEL:-sonnet}"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "bash \"$HOME/.claude/dashboard/hooks/run_hook.sh\" --event-type PostToolUse --agent-name ${AGENT_NAME:-claude} --model ${AGENT_MODEL:-sonnet}"
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash \"$HOME/.claude/dashboard/hooks/run_hook.sh\" --event-type UserPromptSubmit --agent-name ${AGENT_NAME:-claude}"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash \"$HOME/.claude/dashboard/hooks/run_hook.sh\" --event-type Stop --agent-name ${AGENT_NAME:-claude}"
          }
        ]
      }
    ],
    "SubagentStop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash \"$HOME/.claude/dashboard/hooks/run_hook.sh\" --event-type SubagentStop --agent-name ${AGENT_NAME:-claude}"
          }
        ]
      }
    ]
  }
}
```

### Environment Variables

```bash
# Add to ~/.bashrc or ~/.zshrc

# Dashboard server URL
export AGENT_DASHBOARD_URL="http://127.0.0.1:4200/events"

# Default agent configuration
export AGENT_NAME="claude"
export AGENT_MODEL="sonnet"

# Project identification (auto-detected from git if not set)
export AGENT_PROJECT="my-project"
```

---

## Workflow Engine

The Workflow Engine implements the "Locked Gate Pattern" for autonomous Claude Code workflows.

### Workflow Phases

```
PLAN → TEST → IMPLEMENT → VALIDATE → REVIEW → DELIVER
  │      │        │          │         │        │
  └──────┴────────┴──────────┴─────────┴────────┘
         Human-in-the-Loop Checkpoints
```

| Phase | Agent | Model | Description |
|-------|-------|-------|-------------|
| PLAN | planner | Opus | Read-only exploration, create implementation plan |
| TEST | test-writer | Haiku | Write test specifications (TDG pattern) |
| IMPLEMENT | implementer | Sonnet | Execute approved plan, write code |
| VALIDATE | validator | Haiku | Run four-layer validation stack |
| REVIEW | critic | Opus | Challenge implementation, find weaknesses |
| DELIVER | summarizer | Haiku | Generate behavioral diff summary |

### Cost Governance

The Circuit Breaker enforces budget limits:

```python
from workflow_engine import CostCircuitBreaker

cb = CostCircuitBreaker(budget_limit=1.0)  # $1.00 budget

# Check before operations
allowed, msg = cb.check_budget(estimated_cost=0.10)
if not allowed:
    print(f"Budget exceeded: {msg}")

# Record usage
cost = cb.record_usage(tokens_in=1000, tokens_out=500, model="sonnet")
```

**Warning Thresholds:**
- 50% budget: First warning
- 75% budget: Second warning
- 90% budget: Final warning
- 100% budget: Circuit breaks (manual reset required)

### Token Pricing (per million tokens)

| Model | Input | Output | Best For |
|-------|-------|--------|----------|
| Opus | $15.00 | $75.00 | Strategic planning, critical review |
| Sonnet | $3.00 | $15.00 | Implementation, research |
| Haiku | $0.25 | $1.25 | Validation, summarization, tests |

### Four-Layer Validation Stack

| Layer | Description | Tools |
|-------|-------------|-------|
| 1. Static Analysis | Type checking, linting | tsc, mypy, eslint |
| 2. Unit Tests | Test suite execution | pytest, jest |
| 3. Integration Sandbox | Isolated execution | Docker, fixtures |
| 4. Behavioral Diff | Human-readable changes | git diff analysis |

### CLI Usage

```bash
# Create workflow from task
python3 workflow_engine.py from-task "Add user authentication"

# Check budget status
python3 workflow_engine.py budget

# Generate governance document
python3 workflow_engine.py governance <workflow_id> -o CLAUDE.md
```

---

## Agent Setup

### Complete Agent Registry (14 Agents)

#### Tier 1 - Opus (Strategic/Quality)

| Agent | Description | Environment |
|-------|-------------|-------------|
| orchestrator | Strategic coordinator for workflows | `AGENT_NAME=orchestrator AGENT_MODEL=opus` |
| synthesis | Combines research into insights | `AGENT_NAME=synthesis AGENT_MODEL=opus` |
| critic | Challenges conclusions, finds weaknesses | `AGENT_NAME=critic AGENT_MODEL=opus` |
| planner | PLAN MODE - Read-only exploration | `AGENT_NAME=planner AGENT_MODEL=opus` |

#### Tier 2 - Sonnet (Analysis/Implementation)

| Agent | Description | Environment |
|-------|-------------|-------------|
| researcher | Documentation research | `AGENT_NAME=researcher AGENT_MODEL=sonnet` |
| perplexity-researcher | Real-time search with citations | `AGENT_NAME=perplexity-researcher AGENT_MODEL=sonnet` |
| research-judge | Quality evaluation | `AGENT_NAME=research-judge AGENT_MODEL=sonnet` |
| claude-md-auditor | Documentation auditing | `AGENT_NAME=claude-md-auditor AGENT_MODEL=sonnet` |
| implementer | IMPLEMENT MODE - Execute plans | `AGENT_NAME=implementer AGENT_MODEL=sonnet` |

#### Tier 3 - Haiku (Execution/Validation)

| Agent | Description | Environment |
|-------|-------------|-------------|
| web-search-researcher | Broad web searches | `AGENT_NAME=web-search-researcher AGENT_MODEL=haiku` |
| summarizer | Compression and distillation | `AGENT_NAME=summarizer AGENT_MODEL=haiku` |
| test-writer | Test generation | `AGENT_NAME=test-writer AGENT_MODEL=haiku` |
| installer | Setup and configuration | `AGENT_NAME=installer AGENT_MODEL=haiku` |
| validator | VALIDATE MODE - Run validation stack | `AGENT_NAME=validator AGENT_MODEL=haiku` |

---

## Running Claude as an Agent

> **What this does:** Labels your Claude session with an agent name so the dashboard can track which agent is active. This is for **monitoring and identification only** — it doesn't change Claude's behavior.

**Method 1: Environment Variables**
```bash
export AGENT_NAME=orchestrator
export AGENT_MODEL=opus
claude
```

**Method 2: Per-Command**
```bash
AGENT_NAME=planner AGENT_MODEL=opus claude "Analyze the authentication system"
```

**Method 3: Inline with Command**
```bash
AGENT_NAME=orchestrator claude "Plan a research strategy for implementing caching"
```

> **Note:** To use agent-specific system prompts, see the agent definitions in `~/.claude/agents/`.

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
| `/ws` | WS | WebSocket for live updates |

### Workflow Engine Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/workflow` | POST | Create workflow from task |
| `/api/workflow` | GET | List all workflows |
| `/api/workflow/{id}` | GET | Get workflow status |
| `/api/workflow/{id}/prompt` | GET | Get orchestrator prompt |
| `/api/workflow/{id}/governance` | GET | Get CLAUDE.md governance |
| `/api/budget` | GET | Get budget status |

### Example: Create Workflow

```bash
curl -X POST http://localhost:4200/api/workflow \
  -H "Content-Type: application/json" \
  -d '{"task": "Add user authentication with JWT", "budget": 2.0}'
```

**Response:**
```json
{
  "workflow_id": "abc123def456",
  "name": "Workflow: Add user authentication with JWT",
  "tasks": [...],
  "status": {
    "current_phase": "PLAN",
    "total_tasks": 11,
    "pending": 11,
    "completed": 0
  }
}
```

### Example: Get Budget Status

```bash
curl http://localhost:4200/api/budget
```

**Response:**
```json
{
  "limit": 2.0,
  "spent": 0.045,
  "remaining": 1.955,
  "utilization": "2.3%",
  "tokens_in": 5000,
  "tokens_out": 2000,
  "circuit_broken": false
}
```

---

## Testing

### Running the Test Suite

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run specific test file
python3 -m pytest tests/test_workflow_engine.py -v

# Run with coverage
python3 -m pytest tests/ --cov=src --cov-report=html
```

### Test Coverage (61 tests)

**test_workflow_engine.py (39 tests):**
- `TestCostCircuitBreaker` - Budget limits, token estimation, circuit breaking
- `TestTask` - Creation, serialization, status transitions
- `TestWorkflow` - Task management, phases, checkpoints, dependencies
- `TestWorkflowEngine` - Workflow creation, governance generation
- `TestValidationLayerStack` - Validation layers, summaries
- `TestIntegration` - Full lifecycle, budget enforcement

**test_send_event.py (22 tests):**
- `TestTokenEstimation` - Empty, basic, code, unicode text
- `TestCostEstimation` - All model tiers, unknown models
- `TestSummaryGeneration` - Tool summaries
- `TestProjectName` - Auto-detection
- `TestSessionId` - Generation and env vars

### Verifying Installation

```bash
# Test event sending
agent-dashboard test

# Check health
curl http://localhost:4200/health

# Verify workflow engine
python3 -c "from src.workflow_engine import WorkflowEngine; print('OK')"
```

---

## Project Integration Guide

### For New Git Repositories

#### Step 1: Initialize Project

```bash
mkdir my-new-project
cd my-new-project
git init
```

#### Step 2: Create Claude Configuration

```bash
mkdir -p .claude/hooks

# Copy event sender
cp ~/.claude/dashboard/hooks/send_event.py .claude/hooks/
```

#### Step 3: Create Project Settings

```bash
cat > .claude/settings.json << 'EOF'
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
EOF
```

#### Step 4: Create CLAUDE.md Governance

```bash
cat > CLAUDE.md << 'EOF'
# Project Governance

## Positive Action Constraints

ALWAYS explore the codebase before proposing changes
ALWAYS create a detailed plan before implementation
ALWAYS wait for plan approval before proceeding
ALWAYS run tests after each implementation change
ALWAYS match existing code patterns and conventions

## Workflow Phases

1. PLAN - Read-only exploration (planner agent)
2. TEST - Write tests first (test-writer agent)
3. IMPLEMENT - Execute approved plan (implementer agent)
4. VALIDATE - Run validation stack (validator agent)

## Budget Guidelines

- Use Haiku for routine tasks (validation, summarization)
- Use Sonnet for implementation and research
- Use Opus only for strategic planning and critical review
EOF
```

#### Step 5: Update .gitignore

```bash
cat >> .gitignore << 'EOF'

# Agent Dashboard
.claude/agent_dashboard.db
.claude/*.log
EOF
```

#### Step 6: Start Working

```bash
# Start dashboard (in separate terminal)
agent-dashboard --web

# Start Claude with orchestrator
AGENT_NAME=orchestrator AGENT_MODEL=opus claude
```

### For Existing Git Repositories

#### Step 1: Add Claude Configuration (Non-Destructive)

```bash
cd existing-project

# Create .claude directory if it doesn't exist
mkdir -p .claude/hooks

# Backup existing settings if present
[ -f .claude/settings.json ] && cp .claude/settings.json .claude/settings.json.backup

# Copy event sender
cp ~/.claude/dashboard/hooks/send_event.py .claude/hooks/
```

#### Step 2: Merge or Create Settings

**If .claude/settings.json doesn't exist:**
```bash
cat > .claude/settings.json << 'EOF'
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
EOF
```

**If .claude/settings.json exists, manually add hooks:**

Edit `.claude/settings.json` and add the hooks entries to your existing configuration.

#### Step 3: Add CLAUDE.md (If Not Present)

```bash
# Only if CLAUDE.md doesn't exist
[ ! -f CLAUDE.md ] && cat > CLAUDE.md << 'EOF'
# Project Governance

## Positive Action Constraints

ALWAYS explore the codebase before proposing changes
ALWAYS create a detailed plan before implementation
ALWAYS run existing tests before making changes
ALWAYS match existing code patterns and conventions
ALWAYS document significant changes

## Code Standards

Follow existing project conventions for:
- Naming (check existing files for patterns)
- File organization (follow existing structure)
- Error handling (match existing patterns)
- Testing (use existing test framework)
EOF
```

#### Step 4: Update .gitignore

```bash
# Add agent dashboard entries if not present
grep -q "agent_dashboard.db" .gitignore 2>/dev/null || cat >> .gitignore << 'EOF'

# Agent Dashboard
.claude/agent_dashboard.db
.claude/*.log
EOF
```

#### Step 5: Verify Integration

```bash
# Start dashboard
agent-dashboard --web &

# Test event sending (cross-platform)
bash ~/.claude/dashboard/hooks/run_hook.sh --event-type PreToolUse --agent-name test

# Check dashboard received event
curl http://localhost:4200/api/events | head -20
```

### Multi-Project Monitoring

All projects automatically send events to the same dashboard. Projects are identified by:

1. **Git remote URL** (auto-detected, preferred)
2. **Git repo name** (fallback)
3. **Directory name** (final fallback)
4. **AGENT_PROJECT env var** (override)

View all projects in the dashboard, filtered by project name in the sessions panel.

---

## Troubleshooting

### Events Not Appearing

```bash
# 1. Check server is running
curl http://localhost:4200/health
# Expected: {"status": "healthy"}

# 2. Test event sending (cross-platform)
bash ~/.claude/dashboard/hooks/run_hook.sh \
  --event-type PreToolUse --agent-name test --payload '{"test": true}'

# 3. Check hook permissions
chmod +x ~/.claude/dashboard/hooks/send_event.py

# 4. Verify hook execution
bash ~/.claude/dashboard/hooks/run_hook.sh --help
```

### Dashboard Won't Start

```bash
# 1. Check port availability
lsof -i :4200
# Kill process if needed: kill -9 <PID>

# 2. Verify dependencies
pip3 install rich aiohttp tiktoken

# 3. Check Python version
python3 --version  # Must be 3.9+

# 4. Try alternative port
agent-dashboard --web --port 4201
```

### Tiktoken Network Errors

If tiktoken can't download encoding files (restricted network):

```bash
# The system falls back to character-based estimation (len/4)
# This is less accurate but functional

# To verify fallback is working:
python3 -c "
from hooks.send_event import estimate_tokens, _TIKTOKEN_AVAILABLE
print(f'Tiktoken available: {_TIKTOKEN_AVAILABLE}')
print(f'Estimate for \"Hello world\": {estimate_tokens(\"Hello world\")} tokens')
"
```

### Workflow Engine Issues

```bash
# Reset workflow database
rm ~/.claude/workflow_engine.db

# Check budget status
python3 src/workflow_engine.py budget

# Reset circuit breaker (in Python)
python3 -c "
from src.workflow_engine import WorkflowEngine
engine = WorkflowEngine()
engine.circuit_breaker.reset(new_limit=5.0)
print('Circuit breaker reset')
"
```

### Test Failures

```bash
# Run tests with verbose output
python3 -m pytest tests/ -v --tb=long

# Run specific test
python3 -m pytest tests/test_workflow_engine.py::TestCostCircuitBreaker -v

# Check for import errors
python3 -c "from src.workflow_engine import *; print('OK')"
python3 -c "from hooks.send_event import *; print('OK')"
```

### Database Issues

```bash
# View database contents
sqlite3 ~/.claude/agent_dashboard.db "SELECT COUNT(*) FROM events"

# Reset database
rm ~/.claude/agent_dashboard.db
agent-dashboard --web  # Recreates on startup
```

---

## Quick Start Summary

```bash
# 1. Install
git clone https://github.com/your-org/agent-dashboard.git
cd agent-dashboard && ./scripts/install.sh

# 2. Start dashboard
agent-dashboard --web

# 3. Use orchestrator in any project
cd your-project
AGENT_NAME=orchestrator AGENT_MODEL=opus claude

# 4. Create a workflow programmatically
curl -X POST http://localhost:4200/api/workflow \
  -H "Content-Type: application/json" \
  -d '{"task": "Add feature X", "budget": 1.0}'

# 5. Monitor in browser
open http://localhost:4200
```

For additional support, open a GitHub issue or refer to `docs/WORKFLOW_FRAMEWORK.md`.
