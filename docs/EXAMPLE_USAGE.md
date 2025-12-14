# Agent Dashboard - Example Usage Guide

> **Version:** 2.2.1
> **Last Updated:** 2025-12-11
> **Purpose:** Complete walkthrough for using Agent Dashboard with Claude Code

This guide demonstrates how to use Agent Dashboard from installation through a complete multi-agent workflow, using plain language prompts and command-line instructions.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Hook Configuration](#hook-configuration)
- [Complete Workflow Example](#complete-workflow-example)
- [Multi-Agent Parallel Execution](#multi-agent-parallel-execution)
- [Monitoring Your Workflow](#monitoring-your-workflow)
- [Troubleshooting Hooks](#troubleshooting-hooks)
- [Advanced Usage](#advanced-usage)

---

## Prerequisites

Before starting, ensure you have:

| Requirement | Check Command | Expected Output |
|-------------|---------------|-----------------|
| Python 3.9+ | `python3 --version` | `Python 3.9.x` or higher |
| Git | `git --version` | `git version 2.x.x` |
| Claude Code CLI | `claude --version` | Version info displayed |
| Bash shell | `echo $SHELL` | `/bin/bash` or `/bin/zsh` |

**Windows Users:** Use Git Bash or WSL2. PowerShell and CMD are not supported.

---

## Quick Start

### Step 1: Install Agent Dashboard

```bash
# Clone the repository
git clone https://github.com/Koplal/agent-dashboard.git
cd agent-dashboard

# Run the automated installer
./scripts/install.sh
```

The installer will:
- Install Python dependencies (rich, aiohttp)
- Copy agent definitions to `~/.claude/agents/`
- Configure Claude Code hooks in `~/.claude/settings.json`
- Create the `agent-dashboard` command

### Step 2: Start the Dashboard

Open a terminal and start the dashboard server:

```bash
# Start web dashboard (recommended)
agent-dashboard --web

# Or start terminal TUI dashboard
agent-dashboard
```

**Expected Output:**
```
Agent Dashboard v2.2.1
Server running at http://localhost:4200
Press Ctrl+C to stop
```

### Step 3: Verify Installation

Open a new terminal and test the connection:

```bash
# Test server health
curl http://localhost:4200/health

# Expected output: {"status": "ok"}

# Test sending an event manually
curl -X POST http://localhost:4200/events \
  -H "Content-Type: application/json" \
  -d '{"event_type": "Test", "agent_name": "test", "session_id": "manual-test", "project": "test"}'

# Expected output: {"status": "received"}
```

### Step 4: Start Using Claude Code

Now start a Claude Code session. Events will automatically appear in the dashboard:

```bash
# Start Claude Code
claude

# Or with agent identification
AGENT_NAME=researcher AGENT_MODEL=sonnet claude
```

> **Important:** The `AGENT_NAME` and `AGENT_MODEL` environment variables are **metadata for the dashboard only**. They do not change which Claude model is actually used - that's controlled by your Claude Code configuration or API settings. These variables help the dashboard track and categorize your agent sessions by role and intended model tier.

---

## Hook Configuration

### Understanding Claude Code Hooks

Agent Dashboard uses Claude Code hooks to capture events. Hooks are configured in `~/.claude/settings.json`.

### Default Hook Configuration

The installer creates this configuration automatically. See [README.md Configuration](../README.md#-configuration) for the complete hook reference including all event types.

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

### Hook Event Types

| Event | When Triggered | Use Case |
|-------|----------------|----------|
| `PreToolUse` | Before any tool is executed | Track what tools are being used |
| `PostToolUse` | After any tool completes | Track results and token usage |
| `Stop` | When Claude session ends | Track session completion |
| `UserPromptSubmit` | When user sends a message | Track conversation flow |

### Manual Hook Configuration

If hooks weren't configured during installation:

```bash
# Edit Claude Code settings
nano ~/.claude/settings.json

# Or use the diagnostic tool
agent-dashboard doctor
```

---

## Complete Workflow Example

This example demonstrates a real-world use case: creating a REST API with Python.

### The Prompt

Start Claude Code and give it a comprehensive task:

```bash
# Start the dashboard first (in a separate terminal)
agent-dashboard --web

# Then start Claude Code
cd ~/projects/my-api
AGENT_NAME=orchestrator AGENT_MODEL=opus claude
```

**Plain Language Prompt:**

```
I want to create a simple REST API for a todo list application.

Requirements:
- Python with FastAPI
- SQLite database for persistence
- CRUD operations: create, read, update, delete todos
- Each todo has: id, title, description, completed status, created_at
- Include proper error handling
- Add input validation with Pydantic
- Write tests using pytest

Please follow TDD approach:
1. First, design the API specification
2. Then write failing tests
3. Then implement the code to pass the tests
4. Finally, validate everything works

Budget: Keep it simple, this is a learning project.
```

### What Happens Next

The dashboard will show Claude's progress in real-time:

```
┌─────────────────────────────────────────────────────────────────┐
│ Agent Dashboard v2.2.1                    http://localhost:4200 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  SESSION: abc123         PROJECT: my-api         AGENT: opus   │
│                                                                 │
│  Events:                                                        │
│  14:23:01 [orchestrator] PreToolUse: Read README.md            │
│  14:23:05 [orchestrator] PostToolUse: Read complete (234 tok)  │
│  14:23:08 [orchestrator] PreToolUse: Glob **/*.py              │
│  14:23:10 [orchestrator] PostToolUse: Found 0 files            │
│  14:23:15 [orchestrator] PreToolUse: Write main.py             │
│  ...                                                            │
│                                                                 │
│  Tokens: 12,450 in / 8,320 out    Est. Cost: $0.34             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Expected Claude Response

Claude will typically:

1. **Clarify requirements** - Ask about authentication, pagination, etc.
2. **Create project structure** - Set up directories and files
3. **Write specifications** - Document the API design
4. **Write tests first** - Create pytest test files
5. **Implement code** - Write the FastAPI application
6. **Validate** - Run tests and fix any issues

### Interacting During the Workflow

You can guide Claude with follow-up prompts:

```
# If Claude asks for clarification
"No authentication needed, keep it simple. Pagination would be nice but not required."

# To check progress
"Show me the current test coverage"

# To adjust direction
"Actually, let's add a priority field to todos as well"

# To request validation
"Run the tests and show me the results"
```

---

## Multi-Agent Parallel Execution

For larger projects, use multiple Claude sessions with different agent roles.

### Setting Up Parallel Worktrees

```bash
# Create the main project
mkdir ~/projects/env-monitor
cd ~/projects/env-monitor
git init

# Create worktrees for parallel work
git worktree add ../env-monitor-backend feature/backend
git worktree add ../env-monitor-frontend feature/frontend
git worktree add ../env-monitor-firmware feature/firmware
```

### Starting Parallel Agent Sessions

Open multiple terminal windows:

**Terminal 1 - Backend API (Sonnet):**
```bash
cd ~/projects/env-monitor-backend
AGENT_NAME=implementer AGENT_MODEL=sonnet claude "
Create a Python FastAPI backend for an environmental monitoring system.
- MQTT subscriber for sensor data
- SQLite database
- REST API for querying data
- Follow TDD approach
"
```

**Terminal 2 - Frontend Dashboard (Sonnet):**
```bash
cd ~/projects/env-monitor-frontend
AGENT_NAME=implementer AGENT_MODEL=sonnet claude "
Create a simple web dashboard for environmental monitoring.
- HTML/CSS/JavaScript (no frameworks)
- Chart.js for data visualization
- Auto-refresh every 30 seconds
- Responsive design
"
```

**Terminal 3 - Firmware (Sonnet):**
```bash
cd ~/projects/env-monitor-firmware
AGENT_NAME=implementer AGENT_MODEL=sonnet claude "
Create ESP32 firmware for environmental monitoring.
- Read DHT22 temperature/humidity sensor
- Read SCD40 CO2 sensor
- Publish to MQTT broker
- WiFi configuration via portal
"
```

**Terminal 4 - Dashboard Monitoring:**
```bash
agent-dashboard --web
# Open http://localhost:4200 in browser
```

### Viewing Parallel Progress

The web dashboard shows all active sessions:

```
┌─────────────────────────────────────────────────────────────────┐
│                    ACTIVE SESSIONS (3)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ env-monitor-be  │  │ env-monitor-fe  │  │ env-monitor-fw  │ │
│  │ implementer     │  │ implementer     │  │ implementer     │ │
│  │ sonnet          │  │ sonnet          │  │ sonnet          │ │
│  │ ████████░░ 80%  │  │ ██████░░░░ 60%  │  │ █████░░░░░ 45%  │ │
│  │ $0.42           │  │ $0.31           │  │ $0.28           │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│                                                                 │
│  Total Cost: $1.01    Total Tokens: 45,230 in / 28,450 out     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Merging Parallel Work

After all sessions complete:

```bash
cd ~/projects/env-monitor

# Merge all feature branches
git merge feature/backend
git merge feature/frontend
git merge feature/firmware

# Clean up worktrees
git worktree remove ../env-monitor-backend
git worktree remove ../env-monitor-frontend
git worktree remove ../env-monitor-firmware

# Run integration
AGENT_NAME=orchestrator AGENT_MODEL=opus claude "
Integrate all components:
- Verify backend receives firmware data
- Verify frontend displays data correctly
- Create deployment documentation
- Run end-to-end tests
"
```

---

## Monitoring Your Workflow

### Web Dashboard Features

Access the web dashboard at `http://localhost:4200`:

| Feature | Description |
|---------|-------------|
| **Event Timeline** | Real-time stream of all tool uses |
| **Session Cards** | Active sessions with cost tracking |
| **Agent Registry** | All 20 agents with tier information |
| **Statistics** | 24-hour usage summary |
| **WebSocket Updates** | Live updates without refresh |

### REST API Queries

```bash
# Get recent events
curl http://localhost:4200/api/events

# Get active sessions
curl http://localhost:4200/api/sessions

# Get statistics
curl http://localhost:4200/api/stats

# Get budget status (if using workflow engine)
curl http://localhost:4200/api/budget
```

### Terminal Dashboard

For terminal-only environments:

```bash
# Start terminal TUI
agent-dashboard

# Navigation:
# - Arrow keys to scroll
# - 'q' to quit
# - 'r' to refresh
```

---

## Troubleshooting Hooks

### Common Hook Issues

#### Issue 1: Events Not Appearing in Dashboard

**Symptoms:** Claude Code runs but nothing shows in dashboard.

**Diagnosis:**
```bash
# Check if dashboard is running
curl http://localhost:4200/health

# Test hook manually
bash ~/.claude/dashboard/hooks/run_hook.sh --event-type PreToolUse --agent-name test

# Check for Python
python --version
python3 --version
```

**Solutions:**

1. **Dashboard not running:**
   ```bash
   agent-dashboard --web
   ```

2. **Python not found:**
   ```bash
   # The hook silently exits if Python isn't found
   # Ensure Python 3.9+ is in PATH
   which python3
   ```

3. **Hooks not configured:**
   ```bash
   # Check settings.json
   cat ~/.claude/settings.json | grep hooks

   # Re-run installer
   ./scripts/install.sh
   ```

#### Issue 2: Hook Command Errors

**Symptoms:** Claude Code shows errors about hooks failing.

**Diagnosis:**
```bash
# Test the hook script directly
bash -x ~/.claude/dashboard/hooks/run_hook.sh --event-type PreToolUse --agent-name test
```

**Common causes:**

1. **Path with spaces:** Ensure paths are quoted in settings.json
   ```json
   "command": "bash \"$HOME/.claude/dashboard/hooks/run_hook.sh\" ..."
   ```

2. **Missing dependencies:**
   ```bash
   pip install rich aiohttp
   ```

3. **Import errors in send_event.py:**
   ```bash
   # Test Python script directly
   python3 ~/.claude/dashboard/hooks/send_event.py --event-type Test --agent-name test
   ```

#### Issue 3: Token Counting Not Working

**Symptoms:** Token counts show 0 or inaccurate numbers.

**Solutions:**
```bash
# Install recommended tokenizer
pip install transformers tokenizers

# Or fallback tokenizer
pip install tiktoken

# Check tokenizer status
agent-dashboard tokenizer
```

#### Issue 4: Environment Variables Not Set

**Symptoms:** Agent shows as "claude" instead of specific agent name.

**Solutions:**
```bash
# Set before starting Claude
export AGENT_NAME=researcher
export AGENT_MODEL=sonnet
claude

# Or inline
AGENT_NAME=researcher AGENT_MODEL=sonnet claude
```

### Hook Debugging

Enable verbose logging:

```bash
# Edit run_hook.sh to add debugging
# Add after line 12:
# set -x  # Enable debug output

# Or test send_event.py directly with verbose output
python3 ~/.claude/dashboard/hooks/send_event.py \
  --event-type PreToolUse \
  --agent-name test \
  --payload '{"tool_name": "Test"}'
```

### Verifying Hook Installation

```bash
# Run diagnostic
agent-dashboard doctor

# Expected output:
# ✓ Python 3.11 found
# ✓ Dashboard server reachable
# ✓ Hooks configured in settings.json
# ✓ Hook script executable
# ✓ Token counter available (transformers)
```

---

## Advanced Usage

### Using the Workflow Engine API

Create a structured TDD workflow:

```bash
curl -X POST http://localhost:4200/api/workflow \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Build a user authentication system with JWT",
    "budget": 2.0,
    "settings": {
      "tdd_phases": true,
      "parallel_execution": true
    }
  }'
```

### Custom Agent Sessions

Define agent roles for specific tasks:

```bash
# Research agent (read-only exploration)
AGENT_NAME=researcher AGENT_MODEL=sonnet claude "Research the codebase and explain the architecture"

# Implementer agent (code writing)
AGENT_NAME=implementer AGENT_MODEL=sonnet claude "Implement the feature according to the specification"

# Validator agent (testing and validation)
AGENT_NAME=validator AGENT_MODEL=haiku claude "Run all tests and validate the implementation"

# Critic agent (code review)
AGENT_NAME=critic AGENT_MODEL=opus claude "Review the implementation for security issues and code quality"
```

### Automated Workflows with Scripts

Create a workflow script:

```bash
#!/bin/bash
# workflow.sh - Automated multi-agent workflow

PROJECT_DIR=~/projects/my-project
cd "$PROJECT_DIR"

# Start dashboard in background
agent-dashboard --web &
DASHBOARD_PID=$!
sleep 2

# Phase 1: Planning
echo "=== Phase 1: Planning ==="
AGENT_NAME=planner AGENT_MODEL=opus claude "
Read the requirements.md file and create a detailed implementation plan.
Output to docs/implementation-plan.md
"

# Phase 2: Test Design
echo "=== Phase 2: Test Design ==="
AGENT_NAME=test-writer AGENT_MODEL=haiku claude "
Based on docs/implementation-plan.md, design test cases.
Output to tests/test_design.md
"

# Phase 3: Implementation
echo "=== Phase 3: Implementation ==="
AGENT_NAME=implementer AGENT_MODEL=sonnet claude "
Implement the feature to pass all tests.
Follow the plan in docs/implementation-plan.md
"

# Phase 4: Validation
echo "=== Phase 4: Validation ==="
AGENT_NAME=validator AGENT_MODEL=haiku claude "
Run all tests and validate the implementation.
Report any issues found.
"

# Cleanup
kill $DASHBOARD_PID
echo "=== Workflow Complete ==="
```

### Panel Judge Evaluation

For non-testable work products, use the panel judge system:

```bash
# Request a panel evaluation
curl -X POST http://localhost:4200/api/panel \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Architecture Decision Record",
    "description": "Evaluate the proposed microservices architecture",
    "content": "... ADR content ...",
    "metadata": {
      "reversible": false,
      "blast_radius": "org",
      "domain": "software",
      "impact": "high"
    }
  }'
```

---

## Quick Reference

### Common Commands

| Command | Description |
|---------|-------------|
| `agent-dashboard --web` | Start web dashboard |
| `agent-dashboard` | Start terminal dashboard |
| `agent-dashboard doctor` | Run diagnostics |
| `agent-dashboard tokenizer` | Check tokenizer status |
| `curl localhost:4200/health` | Test server health |

### Agent Tiers

| Tier | Model | Cost | Use For |
|------|-------|------|---------|
| 1 | Opus | $$$ | Planning, review, complex reasoning |
| 2 | Sonnet | $$ | Implementation, research, analysis |
| 3 | Haiku | $ | Validation, summarization, routine tasks |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_NAME` | `claude` | Agent identifier for dashboard |
| `AGENT_MODEL` | `sonnet` | Model tier (opus/sonnet/haiku) |
| `AGENT_DASHBOARD_URL` | `http://127.0.0.1:4200/events` | Dashboard server URL |
| `AGENT_PROJECT` | Auto-detected | Project name for grouping |

---

## Getting Help

- **Documentation:** See [README.md](../README.md) and [IMPLEMENTATION.md](IMPLEMENTATION.md)
- **Troubleshooting:** See [TROUBLESHOOTING.md](../TROUBLESHOOTING.md)
- **Issues:** Report at https://github.com/Koplal/agent-dashboard/issues

---

*Built for quality-focused AI workflows*
