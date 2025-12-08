# 🤖 Agent Dashboard v2.0

**Real-time monitoring for Claude Code multi-agent workflows with tiered model architecture.**

A comprehensive monitoring system for tracking agent activities across Opus, Sonnet, and Haiku tiers. Built for research-heavy workflows with quality-focused model selection.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.9+-green.svg)
![Claude](https://img.shields.io/badge/Claude-Code-purple.svg)

## 🎯 What's New in v2.0

- **Tiered Agent Architecture**: Opus for strategic decisions, Sonnet for analysis, Haiku for execution
- **3 New Orchestration Agents**: orchestrator, synthesis, and critic (all Opus-powered)
- **11 Total Agents**: Complete multi-agent research framework
- **Model Visualization**: Color-coded tiers in dashboard (◆Opus ●Sonnet ○Haiku)
- **Quality-First Design**: Optimized for research accuracy over cost

## 📊 Agent Architecture

```
┌──────────────────────────────────────────────────────────────┐
│            TIER 1 - OPUS (Strategic/Quality)                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ orchestrator│  │  synthesis  │  │   critic    │          │
│  │     🎯      │  │     🔗      │  │     ⚔️      │          │
│  │ Coordinator │  │  Combiner   │  │  Challenger │          │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          │
└─────────┼────────────────┼────────────────┼─────────────────┘
          │                │                │
┌─────────┼────────────────┼────────────────┼─────────────────┐
│         │    TIER 2 - SONNET (Analysis)   │                 │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐          │
│  │  researcher │  │  perplexity │  │research-judge│          │
│  │     🔍      │  │     ⚡      │  │     ⚖️      │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
│  ┌─────────────┐                                            │
│  │ md-auditor  │                                            │
│  │     📝      │                                            │
│  └─────────────┘                                            │
└─────────────────────────────────────────────────────────────┘
          │
┌─────────┼───────────────────────────────────────────────────┐
│         │    TIER 3 - HAIKU (Execution)                     │
│  ┌──────▼──────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ web-search  │  │  summarizer │  │ test-writer │          │
│  │     🌐      │  │     📋      │  │     🧪      │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
│  ┌─────────────┐                                            │
│  │  installer  │                                            │
│  │     📦      │                                            │
│  └─────────────┘                                            │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Claude Code CLI installed

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/agent-dashboard.git
cd agent-dashboard

# Run the installer
./scripts/install.sh

# Or install manually
pip install rich aiohttp
```

### Launch the Dashboard

```bash
# Terminal TUI dashboard
agent-dashboard

# Web dashboard (recommended)
agent-dashboard --web
# Open http://localhost:4200
```

## 📁 Repository Structure

```
agent-dashboard/
├── agents/                    # Agent definitions (place in ~/.claude/agents/)
│   ├── orchestrator.md        # 🎯 Tier 1 - Strategic coordinator (Opus)
│   ├── synthesis.md           # 🔗 Tier 1 - Research synthesizer (Opus)
│   ├── critic.md              # ⚔️ Tier 1 - Devil's advocate (Opus)
│   ├── researcher.md          # 🔍 Tier 2 - Documentation research (Sonnet)
│   ├── perplexity-researcher.md # ⚡ Tier 2 - Real-time search (Sonnet)
│   ├── research-judge.md      # ⚖️ Tier 2 - Quality evaluation (Sonnet)
│   ├── claude-md-auditor.md   # 📝 Tier 2 - Doc auditing (Sonnet)
│   ├── web-search-researcher.md # 🌐 Tier 3 - Web searches (Haiku)
│   ├── summarizer.md          # 📋 Tier 3 - Compression (Haiku)
│   ├── test-writer.md         # 🧪 Tier 3 - Test generation (Haiku)
│   └── installer.md           # 📦 Tier 3 - Setup tasks (Haiku)
├── dashboard/
│   └── agent_monitor.py       # Terminal TUI dashboard
├── src/
│   ├── web_server.py          # Web dashboard server
│   └── cli.py                 # Unified CLI
├── hooks/
│   └── send_event.py          # Event capture hook
├── config/
│   └── settings.json.template # Claude Code hooks configuration
├── scripts/
│   └── install.sh             # Installation script
├── docs/
│   ├── IMPLEMENTATION.md      # Detailed implementation guide
│   ├── AGENTS.md              # Agent documentation
│   └── ARCHITECTURE.md        # System architecture
└── README.md
```

## 🔧 Implementation Guide

### Step 1: Install the Dashboard

```bash
# Run the automated installer
./scripts/install.sh

# This will:
# 1. Copy agents to ~/.claude/agents/
# 2. Set up dashboard in ~/.claude/dashboard/
# 3. Configure hooks in ~/.claude/settings.json
# 4. Install Python dependencies
```

### Step 2: Register Agents with Claude Code

Copy agent files to Claude Code's agent directory:

```bash
cp agents/*.md ~/.claude/agents/
```

Verify agents are registered:

```bash
claude /agents
# Should list all 11 agents
```

### Step 3: Configure Hooks

Add to your `~/.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": ".*",
      "hooks": [{
        "type": "command",
        "command": "uv run ~/.claude/dashboard/hooks/send_event.py --event-type PreToolUse --agent-name ${AGENT_NAME:-claude} --model ${AGENT_MODEL:-sonnet}"
      }]
    }],
    "PostToolUse": [{
      "matcher": ".*",
      "hooks": [{
        "type": "command",
        "command": "uv run ~/.claude/dashboard/hooks/send_event.py --event-type PostToolUse --agent-name ${AGENT_NAME:-claude} --model ${AGENT_MODEL:-sonnet}"
      }]
    }],
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "uv run ~/.claude/dashboard/hooks/send_event.py --event-type Stop --agent-name ${AGENT_NAME:-claude}"
      }]
    }]
  }
}
```

### Step 4: Start the Dashboard

```bash
# Start the web dashboard
agent-dashboard --web

# In another terminal, use Claude Code with an agent
export AGENT_NAME=orchestrator
export AGENT_MODEL=opus
claude
```

### Step 5: Using the Orchestrator

The orchestrator is your entry point for complex research:

```
# In Claude Code
@orchestrator Research the best approaches for implementing RAG in production
```

The orchestrator will:
1. Analyze your query
2. Create a research strategy
3. Delegate to specialized agents (researcher, web-search, perplexity)
4. Send results to synthesis agent
5. Run critic for quality check
6. Deliver final output

## 📊 Model Tier Strategy

| Tier | Model | Cost | Use Case | Agents |
|------|-------|------|----------|--------|
| 1 | Opus | $$$ | Strategic decisions, synthesis, quality | orchestrator, synthesis, critic |
| 2 | Sonnet | $$ | Analysis, research, evaluation | researcher, perplexity, judge, auditor |
| 3 | Haiku | $ | Execution, high-volume tasks | web-search, summarizer, test-writer, installer |

### Cost Optimization Pattern

```
Research Query
    │
    ▼
Orchestrator (Opus) ─── Plans strategy, 1 call
    │
    ├─► researcher (Sonnet) ─── Primary research
    ├─► web-search (Haiku) ─── Parallel searches (cheap)
    └─► perplexity (Sonnet) ─── Current data
            │
            ▼
    Synthesis (Opus) ─── Combine findings, 1 call
            │
            ▼
    Critic (Opus) ─── Quality check, 1 call
            │
            ▼
    Final Output

Total Opus calls: 3 (strategic points only)
```

## 🎮 Dashboard Features

### Terminal TUI

- Real-time event timeline
- Active session tracking
- Token usage and cost monitoring
- Agent tier visualization
- Color-coded agents

### Web Dashboard (localhost:4200)

- WebSocket live updates
- Interactive session cards
- Event filtering
- 24-hour statistics
- Agent registry with tiers

## 🔄 Workflow Examples

### Research Workflow

```bash
# Set environment for orchestrator
export AGENT_NAME=orchestrator
export AGENT_MODEL=opus

# Start Claude Code
claude

# In Claude Code:
"Research the current state of vector databases for production RAG systems.
Compare at least 3 options with benchmarks."
```

The orchestrator will coordinate:
1. `researcher` → Official documentation
2. `web-search-researcher` → Recent benchmarks
3. `perplexity-researcher` → Latest news
4. `synthesis` → Combine all findings
5. `critic` → Challenge recommendations
6. `research-judge` → Score quality

### Code Review Workflow

```bash
export AGENT_NAME=critic
export AGENT_MODEL=opus

claude

# In Claude Code:
"Review this PR and find potential issues: [paste diff]"
```

### Documentation Audit

```bash
export AGENT_NAME=claude-md-auditor
export AGENT_MODEL=sonnet

claude

# In Claude Code:
"Audit the CLAUDE.md file against the actual codebase"
```

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web dashboard |
| `/events` | POST | Receive events from hooks |
| `/api/events` | GET | Recent events |
| `/api/sessions` | GET | Active sessions |
| `/api/stats` | GET | Statistics |
| `/health` | GET | Health check |
| `/ws` | WebSocket | Live updates |

## 🧪 Testing

```bash
# Send a test event
agent-dashboard test

# Or manually:
curl -X POST http://localhost:4200/events \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "orchestrator",
    "event_type": "TaskStart",
    "session_id": "test-123",
    "project": "test-project",
    "model": "opus",
    "payload": {"task": "Research query analysis"}
  }'
```

## 📈 Monitoring Best Practices

1. **Start with the orchestrator** for complex queries
2. **Use the web dashboard** for better visualization
3. **Monitor token usage** to optimize costs
4. **Check critic findings** before accepting research
5. **Run auditor regularly** on documentation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- [Claude Code Hooks Multi-Agent Observability](https://github.com/disler/claude-code-hooks-multi-agent-observability) - Inspiration for hooks-based monitoring
- [Rich](https://github.com/Textualize/rich) - Beautiful terminal formatting
- [Anthropic](https://anthropic.com) - Claude models and documentation

---

Built with ❤️ for quality-focused AI workflows
