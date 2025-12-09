#!/usr/bin/env python3
"""
Agent Dashboard - Real-time monitoring for Claude Code multi-agent workflows.

Features:
- Real-time agent status tracking with model tiers (Opus/Sonnet/Haiku)
- Token usage and cost monitoring
- Event timeline with color-coded agents
- Session management across multiple projects
- Support for 11 agents including orchestration layer

Updated: Added Tier 1 Opus agents (orchestrator, synthesis, critic)
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import deque
import sqlite3
import threading

from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.style import Style
from rich.align import Align

# Configuration - matches claude-powerline.json colors
THEME = {
    "directory": "#7dcfff",
    "git": "#bb9af7",
    "git_dirty": "#f7768e",
    "git_clean": "#9ece6a",
    "model": "#ff9e64",
    "session": "#7aa2f7",
    "block": "#e0af68",
    "today": "#9ece6a",
    "context": "#73daca",
    "context_warning": "#e0af68",
    "context_critical": "#f7768e",
    "metrics": "#a9b1d6",
    "lines_added": "#9ece6a",
    "lines_removed": "#f7768e",
    # Model tier colors
    "opus": "#ff79c6",      # Pink/Magenta for Opus (premium)
    "sonnet": "#7aa2f7",    # Blue for Sonnet (standard)
    "haiku": "#73daca",     # Teal for Haiku (fast)
}

# Agent-specific colors for visual distinction
AGENT_COLORS = [
    "#ff79c6",  # Pink - Opus tier
    "#bd93f9",  # Purple - Opus tier
    "#ff9e64",  # Orange - Opus tier
    "#7aa2f7",  # Blue - Sonnet tier
    "#7dcfff",  # Cyan - Sonnet tier
    "#9ece6a",  # Green - Sonnet tier
    "#73daca",  # Teal - Haiku tier
    "#e0af68",  # Yellow - Haiku tier
    "#f7768e",  # Red - Haiku tier
    "#a9b1d6",  # Gray - Other
    "#c0caf5",  # Light - Other
]

EVENT_EMOJIS = {
    "PreToolUse": "🔧",
    "PostToolUse": "✅",
    "Notification": "🔔",
    "Stop": "🛑",
    "SubagentStop": "👥",
    "PreCompact": "📦",
    "UserPromptSubmit": "💬",
    "SessionStart": "🚀",
    "SessionEnd": "🏁",
    "TaskStart": "▶️",
    "TaskComplete": "✔️",
    "TaskError": "❌",
    "Research": "🔍",
    "Summary": "📋",
    "Synthesis": "🔗",
    "Critique": "⚔️",
    "Orchestrate": "🎯",
}

# Agent registry with model assignments
REGISTERED_AGENTS = [
    # Tier 1 - Opus (Strategic/Quality)
    {"name": "orchestrator", "model": "opus", "emoji": "🎯", "tier": 1, "description": "Strategic coordinator"},
    {"name": "synthesis", "model": "opus", "emoji": "🔗", "tier": 1, "description": "Research synthesizer"},
    {"name": "critic", "model": "opus", "emoji": "⚔️", "tier": 1, "description": "Devil's advocate"},
    {"name": "planner", "model": "opus", "emoji": "📐", "tier": 1, "description": "Strategic planner"},
    # Tier 2 - Sonnet (Analysis/Research)
    {"name": "researcher", "model": "sonnet", "emoji": "🔍", "tier": 2, "description": "Documentation research"},
    {"name": "perplexity-researcher", "model": "sonnet", "emoji": "⚡", "tier": 2, "description": "Real-time search"},
    {"name": "research-judge", "model": "sonnet", "emoji": "⚖️", "tier": 2, "description": "Quality evaluation"},
    {"name": "claude-md-auditor", "model": "sonnet", "emoji": "📝", "tier": 2, "description": "Doc auditing"},
    {"name": "implementer", "model": "sonnet", "emoji": "🔨", "tier": 2, "description": "Code implementation"},
    # Tier 3 - Haiku (Execution)
    {"name": "web-search-researcher", "model": "haiku", "emoji": "🌐", "tier": 3, "description": "Web searches"},
    {"name": "summarizer", "model": "haiku", "emoji": "📋", "tier": 3, "description": "Compression"},
    {"name": "test-writer", "model": "haiku", "emoji": "🧪", "tier": 3, "description": "Test generation"},
    {"name": "installer", "model": "haiku", "emoji": "📦", "tier": 3, "description": "Setup tasks"},
    {"name": "validator", "model": "haiku", "emoji": "✅", "tier": 3, "description": "Validation stack"},
]


@dataclass
class AgentEvent:
    """Represents a single agent event."""
    timestamp: datetime
    agent_name: str
    event_type: str
    session_id: str
    project: str
    payload: Dict[str, Any] = field(default_factory=dict)
    model: str = "sonnet"
    tokens_in: int = 0
    tokens_out: int = 0
    cost: float = 0.0


@dataclass
class AgentSession:
    """Tracks an active agent session."""
    session_id: str
    agent_name: str
    project: str
    model: str
    started_at: datetime
    last_activity: datetime
    status: str = "active"  # active, paused, completed, error
    total_tokens: int = 0
    total_cost: float = 0.0
    events: List[AgentEvent] = field(default_factory=list)
    color_idx: int = 0


class AgentDatabase:
    """SQLite database for persisting agent events."""
    
    def __init__(self, db_path: str = "~/.claude/agent_dashboard.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    agent_name TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    project TEXT NOT NULL,
                    model TEXT,
                    tokens_in INTEGER DEFAULT 0,
                    tokens_out INTEGER DEFAULT 0,
                    cost REAL DEFAULT 0.0,
                    payload TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_session 
                ON events(session_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_timestamp 
                ON events(timestamp DESC)
            """)
            conn.commit()
    
    def insert_event(self, event: AgentEvent):
        """Insert an event into the database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO events 
                (timestamp, agent_name, event_type, session_id, project, 
                 model, tokens_in, tokens_out, cost, payload)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.timestamp.isoformat(),
                event.agent_name,
                event.event_type,
                event.session_id,
                event.project,
                event.model,
                event.tokens_in,
                event.tokens_out,
                event.cost,
                json.dumps(event.payload)
            ))
            conn.commit()
    
    def get_recent_events(self, limit: int = 100) -> List[AgentEvent]:
        """Get recent events from the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT timestamp, agent_name, event_type, session_id, project,
                       model, tokens_in, tokens_out, cost, payload
                FROM events
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            
            events = []
            for row in cursor.fetchall():
                events.append(AgentEvent(
                    timestamp=datetime.fromisoformat(row[0]),
                    agent_name=row[1],
                    event_type=row[2],
                    session_id=row[3],
                    project=row[4],
                    model=row[5] or "sonnet",
                    tokens_in=row[6] or 0,
                    tokens_out=row[7] or 0,
                    cost=row[8] or 0.0,
                    payload=json.loads(row[9]) if row[9] else {}
                ))
            return list(reversed(events))
    
    def get_session_stats(self, hours: int = 24) -> Dict:
        """Get aggregate statistics for sessions."""
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_events,
                    COUNT(DISTINCT session_id) as total_sessions,
                    SUM(tokens_in + tokens_out) as total_tokens,
                    SUM(cost) as total_cost
                FROM events
                WHERE timestamp > ?
            """, (since,))
            row = cursor.fetchone()
            return {
                "total_events": row[0] or 0,
                "total_sessions": row[1] or 0,
                "total_tokens": row[2] or 0,
                "total_cost": row[3] or 0.0,
            }


class EventServer:
    """HTTP server for receiving events from hooks."""
    
    def __init__(self, dashboard: 'AgentDashboard', port: int = 4200):
        self.dashboard = dashboard
        self.port = port
        self._running = False
    
    async def start(self):
        """Start the event server."""
        from aiohttp import web
        
        app = web.Application()
        app.router.add_post('/events', self.handle_event)
        app.router.add_get('/health', self.handle_health)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '127.0.0.1', self.port)
        await site.start()
        self._running = True
    
    async def handle_event(self, request):
        """Handle incoming event from hooks."""
        from aiohttp import web
        try:
            data = await request.json()
            event = AgentEvent(
                timestamp=datetime.now(),
                agent_name=data.get('agent_name', 'unknown'),
                event_type=data.get('event_type', 'unknown'),
                session_id=data.get('session_id', 'default'),
                project=data.get('project', 'unknown'),
                model=data.get('model', 'sonnet'),
                tokens_in=data.get('tokens_in', 0),
                tokens_out=data.get('tokens_out', 0),
                cost=data.get('cost', 0.0),
                payload=data.get('payload', {})
            )
            self.dashboard.add_event(event)
            return web.json_response({"status": "ok"})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)
    
    async def handle_health(self, request):
        """Health check endpoint."""
        from aiohttp import web
        return web.json_response({"status": "healthy"})


class AgentDashboard:
    """Main dashboard class managing the TUI."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.console = Console()
        self.db = AgentDatabase()
        self.sessions: Dict[str, AgentSession] = {}
        self.events: deque = deque(maxlen=500)
        self.color_idx = 0
        self.start_time = datetime.now()
        self._lock = threading.Lock()
        
        # Load recent events from database
        for event in self.db.get_recent_events(100):
            self.events.append(event)
            self._update_session(event)
    
    def _get_next_color(self) -> int:
        """Get next agent color index."""
        idx = self.color_idx
        self.color_idx = (self.color_idx + 1) % len(AGENT_COLORS)
        return idx
    
    def _get_agent_info(self, agent_name: str) -> Dict:
        """Get registered agent info or default."""
        for agent in REGISTERED_AGENTS:
            if agent["name"] == agent_name:
                return agent
        return {"name": agent_name, "model": "sonnet", "emoji": "🤖", "tier": 2, "description": "Custom agent"}
    
    def _update_session(self, event: AgentEvent):
        """Update or create session from event."""
        with self._lock:
            if event.session_id not in self.sessions:
                self.sessions[event.session_id] = AgentSession(
                    session_id=event.session_id,
                    agent_name=event.agent_name,
                    project=event.project,
                    model=event.model,
                    started_at=event.timestamp,
                    last_activity=event.timestamp,
                    color_idx=self._get_next_color()
                )
            
            session = self.sessions[event.session_id]
            session.last_activity = event.timestamp
            session.total_tokens += event.tokens_in + event.tokens_out
            session.total_cost += event.cost
            session.events.append(event)
            
            # Update status based on event type
            if event.event_type in ("Stop", "SessionEnd"):
                session.status = "completed"
            elif event.event_type == "TaskError":
                session.status = "error"
            elif event.event_type == "SessionStart":
                session.status = "active"
    
    def add_event(self, event: AgentEvent):
        """Add a new event to the dashboard."""
        self.events.append(event)
        self._update_session(event)
        self.db.insert_event(event)
    
    def make_header(self) -> Panel:
        """Create the header panel."""
        title = Text()
        title.append("🤖 ", style="bold")
        title.append("Agent Dashboard", style=f"bold {THEME['session']}")
        title.append(" │ ", style="dim")
        title.append("Multi-Agent Workflow Monitor", style=THEME['metrics'])
        title.append(" │ ", style="dim")
        title.append("v2.0", style=THEME['opus'])
        
        uptime = datetime.now() - self.start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        status = Text()
        status.append(f"⏱ {hours:02d}:{minutes:02d}:{seconds:02d}", style=THEME['today'])
        status.append(" │ ", style="dim")
        status.append(f"📡 Port 4200", style=THEME['context'])
        status.append(" │ ", style="dim")
        status.append(datetime.now().strftime("%H:%M:%S"), style=THEME['metrics'])
        status.append(" │ ", style="dim")
        status.append("Tiers: ", style="dim")
        status.append("◆Opus ", style=THEME['opus'])
        status.append("●Sonnet ", style=THEME['sonnet'])
        status.append("○Haiku", style=THEME['haiku'])
        
        content = Group(
            Align.center(title),
            Align.center(status)
        )
        
        return Panel(content, style=f"bold {THEME['directory']}", height=4)
    
    def make_sessions_panel(self) -> Panel:
        """Create the active sessions panel."""
        table = Table(show_header=True, header_style="bold", box=None, expand=True)
        table.add_column("Agent", style=THEME['session'], width=18)
        table.add_column("Project", style=THEME['directory'], width=15)
        table.add_column("Model", width=8)
        table.add_column("Status", width=10)
        table.add_column("Tokens", justify="right", style=THEME['context'], width=10)
        table.add_column("Cost", justify="right", style=THEME['today'], width=10)
        table.add_column("Activity", style=THEME['metrics'], width=10)
        
        # Sort sessions by last activity (most recent first)
        sorted_sessions = sorted(
            self.sessions.values(),
            key=lambda s: s.last_activity,
            reverse=True
        )[:10]  # Show top 10
        
        for session in sorted_sessions:
            status_style = {
                "active": THEME['git_clean'],
                "completed": THEME['session'],
                "error": THEME['git_dirty'],
                "paused": THEME['block'],
            }.get(session.status, THEME['metrics'])
            
            status_emoji = {
                "active": "🟢",
                "completed": "⚪",
                "error": "🔴",
                "paused": "🟡",
            }.get(session.status, "⚫")
            
            time_ago = datetime.now() - session.last_activity
            if time_ago.total_seconds() < 60:
                time_str = f"{int(time_ago.total_seconds())}s ago"
            elif time_ago.total_seconds() < 3600:
                time_str = f"{int(time_ago.total_seconds() / 60)}m ago"
            else:
                time_str = f"{int(time_ago.total_seconds() / 3600)}h ago"
            
            # Get agent info for color and model display
            agent_info = self._get_agent_info(session.agent_name)
            model_style = THEME.get(session.model, THEME['metrics'])
            model_symbol = {"opus": "◆", "sonnet": "●", "haiku": "○"}.get(session.model, "?")
            
            color = AGENT_COLORS[session.color_idx]
            agent_text = Text(f"{agent_info['emoji']} {session.agent_name[:14]}", style=color)
            
            table.add_row(
                agent_text,
                session.project[:15],
                Text(f"{model_symbol} {session.model}", style=model_style),
                Text(f"{status_emoji} {session.status}", style=status_style),
                f"{session.total_tokens:,}",
                f"${session.total_cost:.4f}",
                time_str,
            )
        
        if not sorted_sessions:
            table.add_row(
                Text("No active sessions", style="dim italic"),
                "", "", "", "", "", ""
            )
        
        return Panel(
            table,
            title="[bold]📊 Active Sessions[/bold]",
            border_style=THEME['session'],
        )
    
    def make_events_panel(self) -> Panel:
        """Create the event timeline panel."""
        table = Table(show_header=True, header_style="bold", box=None, expand=True)
        table.add_column("Time", style=THEME['metrics'], width=10)
        table.add_column("", width=3)  # Emoji
        table.add_column("Agent", style=THEME['session'], width=14)
        table.add_column("Event", width=18)
        table.add_column("Details", style=THEME['context'], no_wrap=False)
        
        # Get last 15 events
        recent_events = list(self.events)[-15:]
        
        for event in reversed(recent_events):
            emoji = EVENT_EMOJIS.get(event.event_type, "📌")
            time_str = event.timestamp.strftime("%H:%M:%S")
            
            # Get agent color
            session = self.sessions.get(event.session_id)
            agent_color = AGENT_COLORS[session.color_idx] if session else THEME['metrics']
            
            # Format details based on event type
            details = ""
            if event.event_type == "PreToolUse":
                tool = event.payload.get("tool_name", "unknown")
                details = f"Tool: {tool}"
            elif event.event_type == "PostToolUse":
                tool = event.payload.get("tool_name", "unknown")
                success = "✓" if event.payload.get("success", True) else "✗"
                details = f"{tool} {success}"
            elif event.event_type == "UserPromptSubmit":
                prompt = event.payload.get("prompt", "")[:50]
                details = f'"{prompt}..."' if len(prompt) >= 50 else f'"{prompt}"'
            elif event.event_type in ("TaskStart", "TaskComplete"):
                details = event.payload.get("task_name", "")[:35]
            elif event.event_type == "Research":
                details = event.payload.get("query", "")[:35]
            elif event.event_type in ("Synthesis", "Critique", "Orchestrate"):
                details = event.payload.get("action", "")[:35]
            else:
                details = event.payload.get("message", "")[:35] if event.payload else ""
            
            # Color-code event type
            event_style = {
                "PreToolUse": THEME['block'],
                "PostToolUse": THEME['git_clean'],
                "TaskError": THEME['git_dirty'],
                "Stop": THEME['context_warning'],
                "SessionStart": THEME['today'],
                "SessionEnd": THEME['metrics'],
                "Synthesis": THEME['opus'],
                "Critique": THEME['opus'],
                "Orchestrate": THEME['opus'],
            }.get(event.event_type, THEME['session'])
            
            table.add_row(
                time_str,
                emoji,
                Text(event.agent_name[:12], style=agent_color),
                Text(event.event_type, style=event_style),
                details,
            )
        
        if not recent_events:
            table.add_row(
                Text("Waiting for events...", style="dim italic"),
                "", "", "", ""
            )
        
        return Panel(
            table,
            title="[bold]📜 Event Timeline[/bold]",
            border_style=THEME['context'],
        )
    
    def make_stats_panel(self) -> Panel:
        """Create the statistics panel."""
        stats = self.db.get_session_stats(24)
        
        content = Table(show_header=False, box=None, expand=True, padding=(0, 2))
        content.add_column("Label", style=THEME['metrics'])
        content.add_column("Value", justify="right")
        
        content.add_row(
            "📈 Events (24h)",
            Text(f"{stats['total_events']:,}", style=THEME['session'])
        )
        content.add_row(
            "🔗 Sessions",
            Text(f"{stats['total_sessions']:,}", style=THEME['context'])
        )
        content.add_row(
            "🎯 Tokens",
            Text(f"{stats['total_tokens']:,}", style=THEME['block'])
        )
        content.add_row(
            "💰 Cost",
            Text(f"${stats['total_cost']:.4f}", style=THEME['today'])
        )
        content.add_row(
            "⚡ Active",
            Text(
                f"{len([s for s in self.sessions.values() if s.status == 'active'])}",
                style=THEME['git_clean']
            )
        )
        
        return Panel(
            content,
            title="[bold]📊 Statistics[/bold]",
            border_style=THEME['model'],
        )
    
    def make_agents_legend(self) -> Panel:
        """Create legend showing registered agents by tier."""
        content = Table(show_header=False, box=None, expand=True)
        content.add_column("", width=3)
        content.add_column("Agent", width=18)
        content.add_column("Model", justify="right", width=8)
        
        # Group by tier
        current_tier = 0
        tier_names = {1: "─ Tier 1: Opus ─", 2: "─ Tier 2: Sonnet ─", 3: "─ Tier 3: Haiku ─"}
        
        for agent in REGISTERED_AGENTS:
            if agent["tier"] != current_tier:
                current_tier = agent["tier"]
                tier_style = {1: THEME['opus'], 2: THEME['sonnet'], 3: THEME['haiku']}[current_tier]
                content.add_row("", Text(tier_names[current_tier], style=f"dim {tier_style}"), "")
            
            model_style = THEME.get(agent["model"], THEME['metrics'])
            content.add_row(
                agent["emoji"],
                Text(agent["name"], style=model_style),
                Text(agent["model"], style=model_style)
            )
        
        return Panel(
            content,
            title="[bold]🤖 Agent Registry[/bold]",
            border_style=THEME['git'],
        )
    
    def make_layout(self) -> Layout:
        """Create the main layout."""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=4),
            Layout(name="main"),
            Layout(name="footer", size=3),
        )
        
        layout["main"].split_row(
            Layout(name="left", ratio=3),
            Layout(name="right", ratio=1),
        )
        
        layout["left"].split_column(
            Layout(name="sessions", ratio=2),
            Layout(name="events", ratio=3),
        )
        
        layout["right"].split_column(
            Layout(name="stats"),
            Layout(name="agents"),
        )
        
        # Populate layout
        layout["header"].update(self.make_header())
        layout["sessions"].update(self.make_sessions_panel())
        layout["events"].update(self.make_events_panel())
        layout["stats"].update(self.make_stats_panel())
        layout["agents"].update(self.make_agents_legend())
        
        # Footer with help
        help_text = Text()
        help_text.append(" q", style=f"bold {THEME['session']}")
        help_text.append(" Quit  ", style=THEME['metrics'])
        help_text.append("r", style=f"bold {THEME['session']}")
        help_text.append(" Refresh  ", style=THEME['metrics'])
        help_text.append("c", style=f"bold {THEME['session']}")
        help_text.append(" Clear  ", style=THEME['metrics'])
        help_text.append("?", style=f"bold {THEME['session']}")
        help_text.append(" Help", style=THEME['metrics'])
        
        layout["footer"].update(Panel(
            Align.center(help_text),
            style=f"dim {THEME['directory']}"
        ))
        
        return layout
    
    async def run(self):
        """Run the dashboard with live updates."""
        # Try to start event server
        try:
            server = EventServer(self)
            await server.start()
            self.console.print(f"[green]Event server started on port 4200[/green]")
        except ImportError:
            self.console.print(
                "[yellow]aiohttp not installed, running without event server[/yellow]"
            )
        except Exception as e:
            self.console.print(f"[yellow]Could not start server: {e}[/yellow]")
        
        with Live(
            self.make_layout(),
            console=self.console,
            refresh_per_second=2,
            screen=True
        ) as live:
            while True:
                live.update(self.make_layout())
                await asyncio.sleep(0.5)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Agent Dashboard - Multi-Agent Monitor v2.0")
    parser.add_argument("--port", type=int, default=4200, help="Event server port")
    parser.add_argument("--db", type=str, help="Database path")
    args = parser.parse_args()
    
    dashboard = AgentDashboard()
    
    try:
        asyncio.run(dashboard.run())
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped")


if __name__ == "__main__":
    main()
