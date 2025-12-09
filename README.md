# Agent Dashboard v2.5

**Real-time monitoring and orchestration for Claude Code multi-agent workflows.**

A comprehensive multi-agent workflow framework with tiered model architecture (Opus/Sonnet/Haiku), cost governance, and four-layer validation. Built for production-grade AI workflows with quality-focused model selection.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.9+-green.svg)
![Claude](https://img.shields.io/badge/Claude-Code-purple.svg)

---

## Table of Contents

- [Features](#-features)
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
| **Multi-Agent Orchestration** | 14 specialized agents across 3 tiers (Opus/Sonnet/Haiku) |
| **Real-time Monitoring** | Terminal TUI (Rich) and Web Dashboard with WebSocket updates |
| **Workflow Engine** | Six-phase execution with locked-gate pattern |
| **Cost Governance** | Circuit breaker pattern with budget enforcement |
| **Token Tracking** | Accurate counting via tiktoken (cl100k_base encoding) |
| **Four-Layer Validation** | Static analysis, tests, integration sandbox, behavioral diff |

### What's New in v2.5

- **Workflow Engine** - Multi-phase task execution (PLAN → TEST → IMPLEMENT → VALIDATE → REVIEW → DELIVER)
- **Cost Circuit Breaker** - Automatic budget enforcement with warning thresholds
- **3 New Agents** - planner, implementer, validator for structured workflows
- **61 Unit Tests** - Comprehensive test coverage across all components
- **Tiktoken Integration** - Accurate token counting (with character-based fallback)
- **Enhanced API** - Workflow management endpoints

---

## Quick Start

### Prerequisites

| Requirement | Version | Check Command |
|-------------|---------|---------------|
| Python | 3.9+ | `python3 --version` |
| pip or uv | Latest | `pip3 --version` or `uv --version` |
| Claude Code CLI | Latest | `claude --version` |

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/agent-dashboard.git
cd agent-dashboard

# Run the automated installer
./scripts/install.sh

# Or install manually
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

## Configuration

### Claude Code Hooks (`~/.claude/settings.json`)

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": ".*",
      "hooks": [{
        "type": "command",
        "command": "python3 ~/.claude/dashboard/hooks/send_event.py --event-type PreToolUse --agent-name ${AGENT_NAME:-claude} --model ${AGENT_MODEL:-sonnet}"
      }]
    }],
    "PostToolUse": [{
      "matcher": ".*",
      "hooks": [{
        "type": "command",
        "command": "python3 ~/.claude/dashboard/hooks/send_event.py --event-type PostToolUse --agent-name ${AGENT_NAME:-claude} --model ${AGENT_MODEL:-sonnet}"
      }]
    }],
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "python3 ~/.claude/dashboard/hooks/send_event.py --event-type Stop --agent-name ${AGENT_NAME:-claude}"
      }]
    }]
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

### Phases (Locked Gate Pattern)

```
PLAN → TEST → IMPLEMENT → VALIDATE → REVIEW → DELIVER
  │      │        │          │         │        │
  └──────┴────────┴──────────┴─────────┴────────┘
         Human-in-the-Loop Checkpoints
```

| Phase | Agent | Model | Description |
|-------|-------|-------|-------------|
| PLAN | planner | Opus | Read-only exploration, create implementation plan |
| TEST | test-writer | Haiku | Write test specifications (TDD pattern) |
| IMPLEMENT | implementer | Sonnet | Execute approved plan, write code |
| VALIDATE | validator | Haiku | Run four-layer validation stack |
| REVIEW | critic | Opus | Challenge implementation, find weaknesses |
| DELIVER | summarizer | Haiku | Generate behavioral diff summary |

### Cost Governance

#### Model Pricing (per million tokens)

| Model | Tier | Input | Output | Best For |
|-------|------|-------|--------|----------|
| Opus | 1 | $15.00 | $75.00 | Strategic planning, critical review |
| Sonnet | 2 | $3.00 | $15.00 | Implementation, research |
| Haiku | 3 | $0.25 | $1.25 | Validation, summarization, tests |

#### Circuit Breaker Thresholds

| Threshold | Action |
|-----------|--------|
| 50% | First warning |
| 75% | Second warning |
| 90% | Final warning |
| 100% | Circuit breaks (manual reset required) |

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

# Test event sending
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

# 2. Test event sending manually
python3 ~/.claude/dashboard/hooks/send_event.py \
  --event-type PreToolUse --agent-name test

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
