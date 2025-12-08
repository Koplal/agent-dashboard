# 📘 Implementation Guide

This guide walks you through deploying the Agent Dashboard on any project using the multi-agent framework.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation Methods](#installation-methods)
3. [Configuration](#configuration)
4. [Agent Setup](#agent-setup)
5. [Dashboard Deployment](#dashboard-deployment)
6. [Project Integration](#project-integration)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required

- **Python 3.9+** - Check with `python3 --version`
- **Claude Code CLI** - Install from [anthropic.com/claude-code](https://anthropic.com/claude-code)
- **API Access** - Claude API key with access to Opus, Sonnet, and Haiku

### Recommended

- **uv** - Fast Python package manager
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- **tmux** - For running dashboard alongside Claude Code
  ```bash
  brew install tmux  # macOS
  apt install tmux   # Ubuntu
  ```

---

## Installation Methods

### Method 1: Automated Installation (Recommended)

```bash
# Clone the repository
git clone https://github.com/your-username/agent-dashboard.git
cd agent-dashboard

# Run installer
./scripts/install.sh
```

The installer will:
1. Create `~/.claude/dashboard/` directory
2. Copy dashboard files
3. Register agents in `~/.claude/agents/`
4. Configure hooks in `~/.claude/settings.json`
5. Install Python dependencies
6. Add `agent-dashboard` command to PATH

### Method 2: Manual Installation

```bash
# Create directories
mkdir -p ~/.claude/dashboard/hooks
mkdir -p ~/.claude/agents

# Copy dashboard files
cp dashboard/agent_monitor.py ~/.claude/dashboard/
cp src/web_server.py ~/.claude/dashboard/
cp src/cli.py ~/.claude/dashboard/
cp hooks/send_event.py ~/.claude/dashboard/hooks/

# Copy agent definitions
cp agents/*.md ~/.claude/agents/

# Install dependencies
pip install rich aiohttp

# Create launcher script
cat > ~/.local/bin/agent-dashboard << 'EOF'
#!/usr/bin/env bash
python3 ~/.claude/dashboard/cli.py "$@"
EOF
chmod +x ~/.local/bin/agent-dashboard
```

### Method 3: Per-Project Installation

For project-specific dashboards:

```bash
cd your-project

# Create .claude directory in project
mkdir -p .claude/hooks

# Copy hook file
cp /path/to/agent-dashboard/hooks/send_event.py .claude/hooks/

# Create project-specific settings.json
cat > .claude/settings.json << 'EOF'
{
  "hooks": {
    "PreToolUse": [{
      "matcher": ".*",
      "hooks": [{
        "type": "command",
        "command": "python3 .claude/hooks/send_event.py --event-type PreToolUse --agent-name ${AGENT_NAME:-claude}"
      }]
    }]
  }
}
EOF
```

---

## Configuration

### Global Settings (~/.claude/settings.json)

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "uv run ~/.claude/dashboard/hooks/send_event.py --event-type PreToolUse --agent-name ${AGENT_NAME:-claude} --model ${AGENT_MODEL:-sonnet}"
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
            "command": "uv run ~/.claude/dashboard/hooks/send_event.py --event-type PostToolUse --agent-name ${AGENT_NAME:-claude} --model ${AGENT_MODEL:-sonnet}"
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run ~/.claude/dashboard/hooks/send_event.py --event-type UserPromptSubmit --agent-name ${AGENT_NAME:-claude}"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run ~/.claude/dashboard/hooks/send_event.py --event-type Stop --agent-name ${AGENT_NAME:-claude}"
          }
        ]
      }
    ],
    "SubagentStop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run ~/.claude/dashboard/hooks/send_event.py --event-type SubagentStop --agent-name ${AGENT_NAME:-claude}"
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

# Dashboard server URL (default: localhost:4200)
export AGENT_DASHBOARD_URL="http://127.0.0.1:4200/events"

# Default agent (override per-session)
export AGENT_NAME="claude"
export AGENT_MODEL="sonnet"

# Project identification (auto-detected from git if not set)
export AGENT_PROJECT="my-project"
```

### Dashboard Configuration

Create `~/.claude/dashboard/config.json`:

```json
{
  "server": {
    "port": 4200,
    "host": "127.0.0.1"
  },
  "database": {
    "path": "~/.claude/agent_dashboard.db",
    "max_events": 10000
  },
  "display": {
    "max_events_shown": 100,
    "refresh_rate": 2
  },
  "theme": "tokyo-night"
}
```

---

## Agent Setup

### Registering Agents

Copy all agent files to the Claude Code agents directory:

```bash
cp agents/*.md ~/.claude/agents/
```

Verify registration:

```bash
# List available agents
ls ~/.claude/agents/

# In Claude Code, check agents
claude /agents
```

### Using Agents

**Method 1: Environment Variables**

```bash
export AGENT_NAME=orchestrator
export AGENT_MODEL=opus
claude
```

**Method 2: Per-Command**

```bash
AGENT_NAME=researcher AGENT_MODEL=sonnet claude "Research topic X"
```

**Method 3: In Claude Code**

```
@orchestrator Plan a research strategy for [topic]
```

### Agent Tier Reference

| Agent | Model | Environment Setup |
|-------|-------|-------------------|
| orchestrator | opus | `AGENT_NAME=orchestrator AGENT_MODEL=opus` |
| synthesis | opus | `AGENT_NAME=synthesis AGENT_MODEL=opus` |
| critic | opus | `AGENT_NAME=critic AGENT_MODEL=opus` |
| researcher | sonnet | `AGENT_NAME=researcher AGENT_MODEL=sonnet` |
| perplexity-researcher | sonnet | `AGENT_NAME=perplexity-researcher AGENT_MODEL=sonnet` |
| research-judge | sonnet | `AGENT_NAME=research-judge AGENT_MODEL=sonnet` |
| claude-md-auditor | sonnet | `AGENT_NAME=claude-md-auditor AGENT_MODEL=sonnet` |
| web-search-researcher | haiku | `AGENT_NAME=web-search-researcher AGENT_MODEL=haiku` |
| summarizer | haiku | `AGENT_NAME=summarizer AGENT_MODEL=haiku` |
| test-writer | haiku | `AGENT_NAME=test-writer AGENT_MODEL=haiku` |
| installer | haiku | `AGENT_NAME=installer AGENT_MODEL=haiku` |

---

## Dashboard Deployment

### Running the Dashboard

**Terminal TUI:**

```bash
agent-dashboard
```

**Web Dashboard:**

```bash
agent-dashboard --web
# Open http://localhost:4200
```

**Background Mode (recommended):**

```bash
# Using tmux
tmux new-session -d -s dashboard 'agent-dashboard --web'

# View dashboard
tmux attach -t dashboard

# Or in a separate terminal tab
agent-dashboard --web &
```

### Startup Script

Create `~/.local/bin/start-agents`:

```bash
#!/usr/bin/env bash
# Start agent dashboard and workspace

# Start dashboard in background
tmux new-session -d -s dashboard 'agent-dashboard --web' 2>/dev/null || true

# Open dashboard in browser (macOS)
sleep 2
open http://localhost:4200 2>/dev/null || xdg-open http://localhost:4200

# Print status
echo "🤖 Agent Dashboard running at http://localhost:4200"
echo "📡 Event endpoint: http://localhost:4200/events"
echo ""
echo "To use an agent:"
echo "  export AGENT_NAME=orchestrator AGENT_MODEL=opus"
echo "  claude"
```

---

## Project Integration

### Adding Dashboard to a New Project

1. **Create project hook directory:**

```bash
cd your-project
mkdir -p .claude/hooks
```

2. **Copy the event sender:**

```bash
cp ~/.claude/dashboard/hooks/send_event.py .claude/hooks/
```

3. **Create project settings:**

```bash
cat > .claude/settings.json << 'EOF'
{
  "hooks": {
    "PreToolUse": [{
      "matcher": ".*",
      "hooks": [{
        "type": "command",
        "command": "python3 .claude/hooks/send_event.py --event-type PreToolUse --agent-name ${AGENT_NAME:-claude}"
      }]
    }],
    "PostToolUse": [{
      "matcher": ".*",
      "hooks": [{
        "type": "command",
        "command": "python3 .claude/hooks/send_event.py --event-type PostToolUse --agent-name ${AGENT_NAME:-claude}"
      }]
    }],
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "python3 .claude/hooks/send_event.py --event-type Stop --agent-name ${AGENT_NAME:-claude}"
      }]
    }]
  }
}
EOF
```

4. **Add to .gitignore:**

```bash
echo ".claude/agent_dashboard.db" >> .gitignore
```

### Multi-Project Monitoring

All projects send events to the same dashboard. Each project is identified by:

1. Git remote URL (auto-detected)
2. Git repo name (fallback)
3. Directory name (final fallback)
4. `AGENT_PROJECT` environment variable (override)

View all projects in the dashboard filtered by project name.

---

## Troubleshooting

### Events Not Appearing

1. **Check server is running:**
   ```bash
   curl http://localhost:4200/health
   # Should return: {"status": "healthy"}
   ```

2. **Test event sending:**
   ```bash
   agent-dashboard test
   ```

3. **Check hook permissions:**
   ```bash
   chmod +x ~/.claude/dashboard/hooks/send_event.py
   ```

4. **Verify Python can find the script:**
   ```bash
   python3 ~/.claude/dashboard/hooks/send_event.py --help
   ```

### Dashboard Won't Start

1. **Check port availability:**
   ```bash
   lsof -i :4200
   # Kill if something else is using it
   ```

2. **Check dependencies:**
   ```bash
   pip install rich aiohttp
   ```

3. **Check Python version:**
   ```bash
   python3 --version
   # Must be 3.9+
   ```

### Agent Not Recognized

1. **Verify agent files exist:**
   ```bash
   ls ~/.claude/agents/
   ```

2. **Check file extension:**
   ```bash
   # Must be .md
   file ~/.claude/agents/orchestrator.md
   ```

3. **Verify YAML frontmatter:**
   ```bash
   head -10 ~/.claude/agents/orchestrator.md
   # Should start with ---
   ```

### High Token Usage

1. **Check model assignments** - Ensure Haiku is used for execution tasks
2. **Monitor in dashboard** - Watch for runaway loops
3. **Set token limits** - Use Claude Code's built-in limits

### Database Issues

```bash
# Reset the database
rm ~/.claude/agent_dashboard.db

# Restart dashboard
agent-dashboard --web
```

---

## Advanced Topics

### Custom Event Types

Add custom events in `send_event.py`:

```python
# Add to EVENT_TYPES list
"CustomResearch", "CustomAnalysis"
```

### Webhook Integration

Forward events to external systems:

```python
# In send_event.py, add after sending to dashboard:
requests.post("https://your-webhook.com/events", json=event)
```

### Metrics Export

Export metrics for Grafana/Prometheus:

```bash
curl http://localhost:4200/api/stats | jq
```

---

## Next Steps

1. **Start the dashboard:** `agent-dashboard --web`
2. **Use the orchestrator:** `AGENT_NAME=orchestrator claude`
3. **Monitor your workflow:** Watch events in the dashboard
4. **Iterate:** Adjust agent assignments based on quality/cost

For questions or issues, open a GitHub issue.
