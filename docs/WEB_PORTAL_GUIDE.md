# Agent Dashboard Web Portal Guide

> **Version:** 2.7.0
> **Last Updated:** 2025-01-01
> **Purpose:** Complete guide to using the Agent Dashboard web interface

This guide covers all features of the web dashboard, including real-time monitoring, session management, and project organization.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Dashboard Overview](#dashboard-overview)
- [Understanding the UI Panels](#understanding-the-ui-panels)
- [Real-Time Monitoring](#real-time-monitoring)
- [Session Management](#session-management)
- [Project Grouping](#project-grouping)
- [Statistics and Cost Tracking](#statistics-and-cost-tracking)
- [API Reference](#api-reference)
- [Keyboard Shortcuts](#keyboard-shortcuts)

---

## Quick Start

### Starting the Dashboard

```bash
# Start web dashboard (default port 4200)
agent-dashboard --web

# Custom port
agent-dashboard --web --port 8080

# Expected output:
# Starting Agent Dashboard v2.7.0 (Web Mode)
# ===========================================
#
#   URL: http://localhost:4200
#
#   Press Ctrl+C to stop
```

### Accessing the Dashboard

1. Open your browser to `http://localhost:4200`
2. The dashboard loads with an empty event stream
3. Start Claude Code sessions to see events appear in real-time

### Verifying Connection

```bash
# Check server health
curl http://localhost:4200/health
# Expected: {"status": "ok"}

# Send a test event
agent-dashboard test
# Check browser - event should appear
```

---

## Dashboard Overview

The web dashboard uses a Tokyo Night color scheme and consists of five main panels:

```
+------------------+------------------+------------------+
|                  |                  |                  |
|   SESSION        |     EVENT        |    AGENT         |
|   CARDS          |    TIMELINE      |   REGISTRY       |
|                  |                  |                  |
+------------------+------------------+------------------+
|                  |                                     |
|   PROJECT        |        STATISTICS                   |
|   GROUPS         |                                     |
|                  |                                     |
+------------------+-------------------------------------+
```

### Color Coding

| Element | Color | Meaning |
|---------|-------|---------|
| Opus agents | Purple | Tier 1 - Complex reasoning |
| Sonnet agents | Blue | Tier 2 - Balanced tasks |
| Haiku agents | Cyan | Tier 3 - Quick tasks |
| Active session | Green border | Currently running |
| Completed session | Gray border | Session ended |
| Error events | Red text | Tool failure |
| Success events | Green text | Tool success |

---

## Understanding the UI Panels

### 1. Session Cards Panel (Left)

Displays all active and recent sessions with key metrics:

**Card Information:**
- Session ID (truncated)
- Agent name and model tier
- Project name
- Token counts (in/out)
- Estimated cost
- Last activity timestamp

**Actions:**
- Click card to filter events to that session
- Double-click to copy session ID
- Hover for full session details

### 2. Event Timeline Panel (Center)

Real-time stream of all tool uses across all sessions:

**Event Entry Format:**
```
[HH:MM:SS] agent_name (model) | EventType | tool_name
           Project: project_name | Session: abc123...
           Details: tool-specific information
```

**Event Types:**
| Type | Description |
|------|-------------|
| PreToolUse | Before tool execution begins |
| PostToolUse | After tool completes |
| Stop | Session/conversation ended |
| UserPromptSubmit | User message received |

### 3. Agent Registry Panel (Right)

Lists all 22 agent definitions with their tiers:

**Information Shown:**
- Agent name
- Model tier (opus/sonnet/haiku)
- Brief description
- Click to view full agent definition

### 4. Project Groups Panel (Bottom Left)

Organizes sessions by project with aggregated statistics.

### 5. Statistics Panel (Bottom Right)

24-hour usage summary with token counts and cost estimates.

---

## Real-Time Monitoring

### WebSocket Connection

The dashboard maintains a persistent WebSocket connection for real-time updates at `ws://localhost:4200/ws`.

### Connection Status Indicator

Located in the top-right corner:
- Green dot: Connected
- Yellow dot: Reconnecting
- Red dot: Disconnected

---

## Session Management

### Session Lifecycle

1. **Created**: When Claude Code starts with AGENT_NAME set
2. **Active**: Receiving events, green border
3. **Idle**: No events for 5+ minutes, yellow border
4. **Completed**: Stop event received, gray border

---

## Project Grouping

### How Projects Are Determined

Projects are assigned via the `AGENT_PROJECT` environment variable or auto-detected from:

1. Git repository root name
2. Current working directory name
3. "default" if neither available

### Setting Project Name

```bash
# Explicit project name
export AGENT_PROJECT="my-research-project"
claude

# Or inline
AGENT_PROJECT=my-project AGENT_NAME=researcher claude
```

---

## Statistics and Cost Tracking

### Cost Calculation

Costs are estimated based on token counts and model tiers:

| Model | Input (per 1K tokens) | Output (per 1K tokens) |
|-------|----------------------|------------------------|
| Opus | $0.015 | $0.075 |
| Sonnet | $0.003 | $0.015 |
| Haiku | $0.00025 | $0.00125 |

---

## API Reference

### Events API

```bash
# Get recent events (default: last 100)
GET /api/events

# Get events with filters
GET /api/events?limit=50&session_id=abc123

# Get events for a project
GET /api/events?project=my-project
```

### Sessions API

```bash
# Get all sessions
GET /api/sessions

# Get active sessions only
GET /api/sessions?active=true
```

### Statistics API

```bash
# Get overall statistics
GET /api/stats
```

### Health API

```bash
# Simple health check
GET /health
# Returns: {"status": "ok"}
```

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Space` | Pause/resume event stream |
| `Escape` | Clear filters |
| `f` | Focus search box |
| `j` / `k` | Navigate events (down/up) |
| `r` | Refresh dashboard |
| `?` | Show help |

---

## Related Documentation

- [Memory Architecture](MEMORY_ARCHITECTURE.md) - Database and persistence details
- [Example Usage Guide](EXAMPLE_USAGE.md) - Complete workflow examples
- [Multi-Project Guide](Agent%20dashboard%20multi%20project%20guide.md) - Project isolation

---

*Built for quality-focused AI workflows with comprehensive real-time monitoring.*
