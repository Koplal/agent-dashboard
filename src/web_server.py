#!/usr/bin/env python3
"""
web_server.py - Agent Dashboard Web Server

Provides both REST API and WebSocket endpoints for real-time agent monitoring.
Serves a beautiful web dashboard with live updates.

Usage:
    python web_server.py --port 4200

Endpoints:
    GET  /               - Web dashboard
    GET  /api/events     - Recent events
    GET  /api/sessions   - Active sessions
    GET  /api/stats      - Statistics
    POST /events         - Receive events from hooks
    WS   /ws             - WebSocket for live updates

Dependencies:
    - aiohttp: Async HTTP/WebSocket server
    - workflow_engine: Workflow orchestration (optional)

Version: 2.2.1
"""

import asyncio
import json
import os
import sqlite3
import socket
import subprocess
import sys
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import argparse

try:
    from aiohttp import web
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False
    print("Warning: aiohttp not installed. Run: pip install aiohttp")

# Import workflow engine for orchestration
try:
    from workflow_engine import WorkflowEngine, WorkflowPhase, TaskStatus
    HAS_WORKFLOW_ENGINE = True
except ImportError:
    HAS_WORKFLOW_ENGINE = False


# =============================================================================
# PORT CONFLICT HANDLING UTILITIES
# =============================================================================

def is_port_available(port: int, host: str = "0.0.0.0") -> bool:
    """Check if a port is available for binding.

    Args:
        port: The port number to check
        host: The host address to bind to

    Returns:
        True if port is available, False if in use
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, port))
            return True
    except OSError:
        return False


def find_available_port(start_port: int, max_attempts: int = 10) -> Optional[int]:
    """Find the next available port starting from start_port.

    Args:
        start_port: The port number to start searching from
        max_attempts: Maximum number of ports to try

    Returns:
        An available port number, or None if no port found
    """
    for offset in range(max_attempts):
        port = start_port + offset
        if is_port_available(port):
            return port
    return None


def get_process_using_port(port: int) -> Optional[Dict[str, Any]]:
    """Get information about the process using a specific port.

    Args:
        port: The port number to check

    Returns:
        Dict with 'pid', 'name' keys if found, None otherwise
    """
    try:
        if sys.platform == "win32":
            # Windows: use netstat to find PID
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True,
                timeout=10
            )

            for line in result.stdout.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    if parts:
                        pid = int(parts[-1])
                        # Get process name
                        proc_result = subprocess.run(
                            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        proc_name = "unknown"
                        if proc_result.stdout.strip():
                            # Parse CSV output: "name.exe","pid",...
                            match = re.match(r'"([^"]+)"', proc_result.stdout.strip())
                            if match:
                                proc_name = match.group(1)
                        return {"pid": pid, "name": proc_name}
        else:
            # Unix: use lsof
            result = subprocess.run(
                ["lsof", "-i", f":{port}", "-t"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.stdout.strip():
                pid = int(result.stdout.strip().split()[0])
                # Get process name
                proc_result = subprocess.run(
                    ["ps", "-p", str(pid), "-o", "comm="],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                proc_name = proc_result.stdout.strip() or "unknown"
                return {"pid": pid, "name": proc_name}
    except Exception as e:
        print(f"Warning: Could not identify process on port {port}: {e}")

    return None


def kill_process_on_port(port: int, force: bool = False) -> bool:
    """Kill the process using a specific port.

    Args:
        port: The port number
        force: If True, kill without confirmation

    Returns:
        True if process was killed, False otherwise
    """
    proc_info = get_process_using_port(port)
    if not proc_info:
        return True  # No process to kill

    pid = proc_info["pid"]
    name = proc_info["name"]

    if not force:
        print(f"\n[!] Port {port} is in use by {name} (PID: {pid})")
        try:
            response = input("    Kill this process? [y/N]: ").strip().lower()
            if response != 'y':
                print("    Aborted.")
                return False
        except (EOFError, KeyboardInterrupt):
            print("\n    Aborted.")
            return False

    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], check=True)
        else:
            os.kill(pid, 9)  # SIGKILL

        # Wait a moment for the port to be released
        import time
        time.sleep(0.5)

        if is_port_available(port):
            print(f"[+] Killed process {name} (PID: {pid})")
            return True
        else:
            print(f"[-] Failed to free port {port}")
            return False
    except Exception as e:
        print(f"[-] Error killing process: {e}")
        return False


def check_port_and_handle(port: int, force: bool = False, auto_port: bool = False) -> Tuple[int, bool]:
    """Check port availability and handle conflicts based on flags.

    Args:
        port: The desired port
        force: Kill existing process if True
        auto_port: Find alternative port if True

    Returns:
        Tuple of (port_to_use, success)
    """
    if is_port_available(port):
        return port, True

    proc_info = get_process_using_port(port)
    proc_desc = f"{proc_info['name']} (PID: {proc_info['pid']})" if proc_info else "unknown process"

    if force:
        print(f"[*] Port {port} in use by {proc_desc}, killing...")
        if kill_process_on_port(port, force=True):
            return port, True
        else:
            print(f"[-] Failed to free port {port}")
            return port, False

    if auto_port:
        print(f"[*] Port {port} in use by {proc_desc}, finding alternative...")
        alt_port = find_available_port(port + 1)
        if alt_port:
            print(f"[+] Using port {alt_port} instead")
            return alt_port, True
        else:
            print(f"[-] No available ports found in range {port+1}-{port+10}")
            return port, False

    # Neither flag set - show interactive prompt
    print(f"\n{'='*60}")
    print(f"Port {port} is already in use")
    print(f"{'='*60}")
    print(f"\n  Process: {proc_desc}")
    print(f"\n  Options:")
    print(f"    [1] Kill the existing process and use port {port}")
    print(f"    [2] Use a different port automatically")
    print(f"    [3] Cancel and exit")
    print()

    try:
        choice = input("  Select an option [1/2/3]: ").strip()

        if choice == "1":
            print(f"\n[*] Killing process {proc_desc}...")
            if kill_process_on_port(port, force=True):
                return port, True
            else:
                print(f"[-] Failed to free port {port}")
                return port, False

        elif choice == "2":
            print(f"\n[*] Finding alternative port...")
            alt_port = find_available_port(port + 1)
            if alt_port:
                print(f"[+] Using port {alt_port} instead")
                return alt_port, True
            else:
                print(f"[-] No available ports found in range {port+1}-{port+10}")
                return port, False

        else:
            print("\n[x] Cancelled.")
            return port, False

    except (EOFError, KeyboardInterrupt):
        print("\n\n[x] Cancelled.")
        return port, False


# Theme colors matching claude-powerline.json
THEME = {
    "directory": "#7dcfff",
    "git": "#bb9af7",
    "model": "#ff9e64",
    "session": "#7aa2f7",
    "block": "#e0af68",
    "today": "#9ece6a",
    "context": "#73daca",
    "metrics": "#a9b1d6",
    "error": "#f7768e",
    "success": "#9ece6a",
}


# HTML Template for the dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🤖 Agent Dashboard</title>
    <style>
        :root {
            --bg-primary: #1a1b26;
            --bg-secondary: #24283b;
            --bg-tertiary: #414868;
            --text-primary: #c0caf5;
            --text-secondary: #a9b1d6;
            --text-muted: #565f89;
            --accent-blue: #7aa2f7;
            --accent-cyan: #7dcfff;
            --accent-purple: #bb9af7;
            --accent-green: #9ece6a;
            --accent-orange: #ff9e64;
            --accent-red: #f7768e;
            --accent-yellow: #e0af68;
            --accent-teal: #73daca;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'JetBrains Mono', 'Fira Code', monospace;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
        }
        
        .container {
            max-width: 1800px;
            margin: 0 auto;
            padding: 1rem;
        }
        
        header {
            background: linear-gradient(135deg, var(--bg-secondary) 0%, var(--bg-tertiary) 100%);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            border: 1px solid var(--bg-tertiary);
        }
        
        header h1 {
            font-size: 1.8rem;
            color: var(--accent-cyan);
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .header-info {
            display: flex;
            gap: 2rem;
            margin-top: 0.5rem;
            color: var(--text-secondary);
            font-size: 0.9rem;
        }
        
        .header-info span {
            display: flex;
            align-items: center;
            gap: 0.3rem;
        }
        
        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr 300px;
            gap: 1rem;
            margin-bottom: 1rem;
        }
        
        .panel {
            background: var(--bg-secondary);
            border-radius: 12px;
            border: 1px solid var(--bg-tertiary);
            overflow: hidden;
        }
        
        .panel-header {
            padding: 1rem;
            background: var(--bg-tertiary);
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .panel-content {
            padding: 1rem;
            max-height: 400px;
            overflow-y: auto;
        }
        
        .session-card {
            background: var(--bg-primary);
            border-radius: 8px;
            padding: 0.8rem;
            margin-bottom: 0.5rem;
            border-left: 3px solid var(--accent-blue);
        }
        
        .session-card .name {
            font-weight: 600;
            color: var(--accent-cyan);
        }
        
        .session-card .meta {
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-top: 0.3rem;
        }
        
        .session-card .stats {
            display: flex;
            gap: 1rem;
            margin-top: 0.5rem;
            font-size: 0.85rem;
        }
        
        .event-row {
            display: grid;
            grid-template-columns: 80px 30px 100px 120px 1fr;
            gap: 0.5rem;
            padding: 0.5rem;
            border-radius: 6px;
            align-items: center;
            font-size: 0.85rem;
        }
        
        .event-row:hover {
            background: var(--bg-primary);
        }
        
        .event-row .time {
            color: var(--text-muted);
        }
        
        .event-row .agent {
            color: var(--accent-purple);
            font-weight: 500;
        }
        
        .event-row .type {
            color: var(--accent-orange);
        }
        
        .event-row .details {
            color: var(--text-secondary);
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        
        .stat-item {
            display: flex;
            justify-content: space-between;
            padding: 0.7rem 0;
            border-bottom: 1px solid var(--bg-tertiary);
        }
        
        .stat-item:last-child {
            border-bottom: none;
        }
        
        .stat-value {
            font-weight: 600;
            color: var(--accent-green);
        }
        
        .status-active { color: var(--accent-green); }
        .status-completed { color: var(--text-muted); }
        .status-error { color: var(--accent-red); }
        
        .live-indicator {
            display: flex;
            align-items: center;
            gap: 0.3rem;
        }
        
        .live-dot {
            width: 8px;
            height: 8px;
            background: var(--accent-green);
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .agent-legend {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }
        
        .agent-item {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem;
            background: var(--bg-primary);
            border-radius: 6px;
        }
        
        .agent-color {
            width: 12px;
            height: 12px;
            border-radius: 3px;
        }
        
        .agent-model {
            margin-left: auto;
            color: var(--accent-orange);
            font-size: 0.75rem;
        }
        
        @media (max-width: 1200px) {
            .grid {
                grid-template-columns: 1fr 1fr;
            }
        }
        
        @media (max-width: 768px) {
            .grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🤖 Agent Dashboard</h1>
            <div class="header-info">
                <span class="live-indicator">
                    <span class="live-dot"></span>
                    <span id="connection-status">Connecting...</span>
                </span>
                <span>⏱ <span id="uptime">00:00:00</span></span>
                <span>📡 Port {port}</span>
                <span>🕐 <span id="current-time"></span></span>
            </div>
        </header>
        
        <div class="grid">
            <div class="panel">
                <div class="panel-header">📊 Active Sessions</div>
                <div class="panel-content" id="sessions-panel">
                    <p style="color: var(--text-muted)">Waiting for sessions...</p>
                </div>
            </div>
            
            <div class="panel">
                <div class="panel-header">📜 Event Timeline</div>
                <div class="panel-content" id="events-panel">
                    <p style="color: var(--text-muted)">Waiting for events...</p>
                </div>
            </div>
            
            <div class="panel">
                <div class="panel-header">📈 Statistics (24h)</div>
                <div class="panel-content" id="stats-panel">
                    <div class="stat-item">
                        <span>📊 Events</span>
                        <span class="stat-value" id="stat-events">0</span>
                    </div>
                    <div class="stat-item">
                        <span>🔗 Sessions</span>
                        <span class="stat-value" id="stat-sessions">0</span>
                    </div>
                    <div class="stat-item">
                        <span>🎯 Tokens</span>
                        <span class="stat-value" id="stat-tokens">0</span>
                    </div>
                    <div class="stat-item">
                        <span>💰 Cost</span>
                        <span class="stat-value" id="stat-cost">$0.00</span>
                    </div>
                    <div class="stat-item">
                        <span>⚡ Active</span>
                        <span class="stat-value status-active" id="stat-active">0</span>
                    </div>
                </div>
                
                <div class="panel-header" style="margin-top: 1rem;">🤖 Registered Agents</div>
                <div class="panel-content">
                    <div class="agent-legend">
                        <div class="agent-item">
                            <span class="agent-color" style="background: #7dcfff"></span>
                            <span>🔍 researcher</span>
                            <span class="agent-model">haiku</span>
                        </div>
                        <div class="agent-item">
                            <span class="agent-color" style="background: #bb9af7"></span>
                            <span>🌐 web-search-researcher</span>
                            <span class="agent-model">sonnet</span>
                        </div>
                        <div class="agent-item">
                            <span class="agent-color" style="background: #ff9e64"></span>
                            <span>⚡ perplexity-researcher</span>
                            <span class="agent-model">sonnet</span>
                        </div>
                        <div class="agent-item">
                            <span class="agent-color" style="background: #9ece6a"></span>
                            <span>📋 summarizer</span>
                            <span class="agent-model">sonnet</span>
                        </div>
                        <div class="agent-item">
                            <span class="agent-color" style="background: #f7768e"></span>
                            <span>⚖️ research-judge</span>
                            <span class="agent-model">sonnet</span>
                        </div>
                        <div class="agent-item">
                            <span class="agent-color" style="background: #7aa2f7"></span>
                            <span>🧪 test-writer</span>
                            <span class="agent-model">sonnet</span>
                        </div>
                        <div class="agent-item">
                            <span class="agent-color" style="background: #e0af68"></span>
                            <span>📦 installer</span>
                            <span class="agent-model">sonnet</span>
                        </div>
                        <div class="agent-item">
                            <span class="agent-color" style="background: #73daca"></span>
                            <span>📝 claude-md-auditor</span>
                            <span class="agent-model">haiku</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const AGENT_COLORS = [
            '#7dcfff', '#bb9af7', '#ff9e64', '#9ece6a',
            '#f7768e', '#7aa2f7', '#e0af68', '#73daca'
        ];
        
        const EVENT_EMOJIS = {
            'PreToolUse': '🔧', 'PostToolUse': '✅', 'Notification': '🔔',
            'Stop': '🛑', 'SubagentStop': '👥', 'PreCompact': '📦',
            'UserPromptSubmit': '💬', 'SessionStart': '🚀', 'SessionEnd': '🏁',
            'TaskStart': '▶️', 'TaskComplete': '✔️', 'TaskError': '❌',
            'Research': '🔍', 'Summary': '📋'
        };
        
        let ws;
        let sessions = {};
        let events = [];
        let startTime = Date.now();
        
        function connect() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
            
            ws.onopen = () => {
                document.getElementById('connection-status').textContent = 'Live';
                console.log('WebSocket connected');
            };
            
            ws.onmessage = (e) => {
                const data = JSON.parse(e.data);
                handleMessage(data);
            };
            
            ws.onclose = () => {
                document.getElementById('connection-status').textContent = 'Reconnecting...';
                setTimeout(connect, 2000);
            };
        }
        
        function handleMessage(data) {
            if (data.type === 'event') {
                events.unshift(data.event);
                if (events.length > 100) events.pop();
                updateEventsPanel();
                updateSession(data.event);
            } else if (data.type === 'init') {
                events = data.events || [];
                sessions = data.sessions || {};
                updateEventsPanel();
                updateSessionsPanel();
            } else if (data.type === 'stats') {
                updateStats(data.stats);
            }
        }
        
        function updateSession(event) {
            const sid = event.session_id;
            if (!sessions[sid]) {
                sessions[sid] = {
                    session_id: sid,
                    agent_name: event.agent_name,
                    project: event.project,
                    model: event.model || 'sonnet',
                    status: 'active',
                    total_tokens: 0,
                    total_cost: 0,
                    last_activity: event.timestamp,
                    color_idx: Object.keys(sessions).length % AGENT_COLORS.length
                };
            }
            
            const session = sessions[sid];
            session.last_activity = event.timestamp;
            session.total_tokens += (event.tokens_in || 0) + (event.tokens_out || 0);
            session.total_cost += event.cost || 0;
            
            if (['Stop', 'SessionEnd'].includes(event.event_type)) {
                session.status = 'completed';
            } else if (event.event_type === 'TaskError') {
                session.status = 'error';
            }
            
            updateSessionsPanel();
        }
        
        function updateSessionsPanel() {
            const panel = document.getElementById('sessions-panel');
            const sorted = Object.values(sessions).sort((a, b) => 
                new Date(b.last_activity) - new Date(a.last_activity)
            ).slice(0, 10);
            
            if (sorted.length === 0) {
                panel.innerHTML = '<p style="color: var(--text-muted)">No active sessions</p>';
                return;
            }
            
            panel.innerHTML = sorted.map(s => {
                const color = AGENT_COLORS[s.color_idx];
                const statusClass = `status-${s.status}`;
                const timeAgo = getTimeAgo(s.last_activity);
                
                return `
                    <div class="session-card" style="border-left-color: ${color}">
                        <div class="name" style="color: ${color}">${s.agent_name}</div>
                        <div class="meta">${s.project} • ${s.model}</div>
                        <div class="stats">
                            <span class="${statusClass}">● ${s.status}</span>
                            <span>🎯 ${s.total_tokens.toLocaleString()}</span>
                            <span>💰 $${s.total_cost.toFixed(4)}</span>
                            <span>⏱ ${timeAgo}</span>
                        </div>
                    </div>
                `;
            }).join('');
        }
        
        function updateEventsPanel() {
            const panel = document.getElementById('events-panel');
            
            if (events.length === 0) {
                panel.innerHTML = '<p style="color: var(--text-muted)">Waiting for events...</p>';
                return;
            }
            
            panel.innerHTML = events.slice(0, 20).map(e => {
                const emoji = EVENT_EMOJIS[e.event_type] || '📌';
                const time = new Date(e.timestamp).toLocaleTimeString();
                const session = sessions[e.session_id];
                const color = session ? AGENT_COLORS[session.color_idx] : '#a9b1d6';
                
                let details = '';
                if (e.payload) {
                    if (e.payload.tool_name) {
                        details = `Tool: ${e.payload.tool_name}`;
                    } else if (e.payload.prompt) {
                        details = `"${e.payload.prompt.substring(0, 50)}..."`;
                    } else if (e.payload.summary) {
                        details = e.payload.summary;
                    }
                }
                
                return `
                    <div class="event-row">
                        <span class="time">${time}</span>
                        <span>${emoji}</span>
                        <span class="agent" style="color: ${color}">${e.agent_name}</span>
                        <span class="type">${e.event_type}</span>
                        <span class="details">${details}</span>
                    </div>
                `;
            }).join('');
        }
        
        function updateStats(stats) {
            document.getElementById('stat-events').textContent = stats.total_events?.toLocaleString() || '0';
            document.getElementById('stat-sessions').textContent = stats.total_sessions?.toLocaleString() || '0';
            document.getElementById('stat-tokens').textContent = stats.total_tokens?.toLocaleString() || '0';
            document.getElementById('stat-cost').textContent = `$${(stats.total_cost || 0).toFixed(4)}`;
            document.getElementById('stat-active').textContent = 
                Object.values(sessions).filter(s => s.status === 'active').length;
        }
        
        function getTimeAgo(timestamp) {
            const diff = (Date.now() - new Date(timestamp)) / 1000;
            if (diff < 60) return `${Math.floor(diff)}s ago`;
            if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
            return `${Math.floor(diff / 3600)}h ago`;
        }
        
        function updateClock() {
            const now = new Date();
            document.getElementById('current-time').textContent = now.toLocaleTimeString();
            
            const uptime = Math.floor((Date.now() - startTime) / 1000);
            const h = Math.floor(uptime / 3600);
            const m = Math.floor((uptime % 3600) / 60);
            const s = uptime % 60;
            document.getElementById('uptime').textContent = 
                `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
        }
        
        // Initialize
        connect();
        setInterval(updateClock, 1000);
        updateClock();
        
        // Fetch initial data
        fetch('/api/events').then(r => r.json()).then(data => {
            events = data.events || [];
            updateEventsPanel();
        });
        
        fetch('/api/stats').then(r => r.json()).then(updateStats);
    </script>
</body>
</html>
"""


class WebDashboard:
    """Web dashboard server with WebSocket support."""

    def __init__(self, db_path: str = "~/.claude/agent_dashboard.db", port: int = 4200):
        self.db_path = Path(db_path).expanduser()
        self.port = port
        self.ws_clients: Set[web.WebSocketResponse] = set()
        self.sessions: Dict[str, Any] = {}
        self.events: List[Dict] = []
        self._init_db()
        self._load_recent_data()

        # Initialize workflow engine if available
        if HAS_WORKFLOW_ENGINE:
            self.workflow_engine = WorkflowEngine(budget_limit=10.0)
        else:
            self.workflow_engine = None
    
    def _init_db(self):
        """Initialize database."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
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
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp DESC)")
            conn.commit()
    
    def _load_recent_data(self):
        """Load recent events from database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT timestamp, agent_name, event_type, session_id, project,
                       model, tokens_in, tokens_out, cost, payload
                FROM events ORDER BY timestamp DESC LIMIT 100
            """)
            
            for row in cursor.fetchall():
                event = {
                    "timestamp": row[0],
                    "agent_name": row[1],
                    "event_type": row[2],
                    "session_id": row[3],
                    "project": row[4],
                    "model": row[5] or "sonnet",
                    "tokens_in": row[6] or 0,
                    "tokens_out": row[7] or 0,
                    "cost": row[8] or 0.0,
                    "payload": json.loads(row[9]) if row[9] else {}
                }
                self.events.insert(0, event)
                self._update_session(event)
    
    def _update_session(self, event: Dict):
        """Update session from event."""
        sid = event["session_id"]
        if sid not in self.sessions:
            self.sessions[sid] = {
                "session_id": sid,
                "agent_name": event["agent_name"],
                "project": event["project"],
                "model": event["model"],
                "status": "active",
                "total_tokens": 0,
                "total_cost": 0.0,
                "last_activity": event["timestamp"],
                "color_idx": len(self.sessions) % 8
            }
        
        session = self.sessions[sid]
        session["last_activity"] = event["timestamp"]
        session["total_tokens"] += event.get("tokens_in", 0) + event.get("tokens_out", 0)
        session["total_cost"] += event.get("cost", 0.0)
        
        if event["event_type"] in ("Stop", "SessionEnd"):
            session["status"] = "completed"
        elif event["event_type"] == "TaskError":
            session["status"] = "error"
    
    def _get_stats(self) -> Dict:
        """Get aggregate statistics."""
        since = (datetime.now() - timedelta(hours=24)).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT COUNT(*), COUNT(DISTINCT session_id), 
                       SUM(tokens_in + tokens_out), SUM(cost)
                FROM events WHERE timestamp > ?
            """, (since,))
            row = cursor.fetchone()
            return {
                "total_events": row[0] or 0,
                "total_sessions": row[1] or 0,
                "total_tokens": row[2] or 0,
                "total_cost": row[3] or 0.0,
            }
    
    async def handle_index(self, request):
        """Serve the dashboard HTML."""
        html = DASHBOARD_HTML.replace("{port}", str(self.port))
        return web.Response(text=html, content_type="text/html")
    
    async def handle_events_post(self, request):
        """Receive events from hooks."""
        try:
            data = await request.json()
            event = {
                "timestamp": data.get("timestamp", datetime.now().isoformat()),
                "agent_name": data.get("agent_name", "unknown"),
                "event_type": data.get("event_type", "unknown"),
                "session_id": data.get("session_id", "default"),
                "project": data.get("project", "unknown"),
                "model": data.get("model", "sonnet"),
                "tokens_in": data.get("tokens_in", 0),
                "tokens_out": data.get("tokens_out", 0),
                "cost": data.get("cost", 0.0),
                "payload": data.get("payload", {})
            }
            
            # Store in database
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO events 
                    (timestamp, agent_name, event_type, session_id, project, 
                     model, tokens_in, tokens_out, cost, payload)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event["timestamp"], event["agent_name"], event["event_type"],
                    event["session_id"], event["project"], event["model"],
                    event["tokens_in"], event["tokens_out"], event["cost"],
                    json.dumps(event["payload"])
                ))
                conn.commit()
            
            # Update in-memory state
            self.events.insert(0, event)
            if len(self.events) > 500:
                self.events.pop()
            self._update_session(event)
            
            # Broadcast to WebSocket clients
            await self.broadcast({"type": "event", "event": event})
            
            return web.json_response({"status": "ok"})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)
    
    async def handle_events_get(self, request):
        """Get recent events."""
        limit = int(request.query.get("limit", 100))
        return web.json_response({"events": self.events[:limit]})
    
    async def handle_sessions(self, request):
        """Get active sessions."""
        return web.json_response({"sessions": self.sessions})
    
    async def handle_stats(self, request):
        """Get statistics."""
        return web.json_response(self._get_stats())
    
    async def handle_health(self, request):
        """Health check."""
        return web.json_response({"status": "healthy"})

    # =========================================================================
    # WORKFLOW ENGINE API ENDPOINTS
    # =========================================================================

    async def handle_workflow_create(self, request):
        """Create a new workflow from a task description."""
        if not self.workflow_engine:
            return web.json_response(
                {"error": "Workflow engine not available"},
                status=503
            )

        try:
            data = await request.json()
            task = data.get("task", "")
            budget = data.get("budget", 1.0)

            if not task:
                return web.json_response(
                    {"error": "Task description required"},
                    status=400
                )

            workflow = self.workflow_engine.create_workflow_from_task(task)
            self.workflow_engine.circuit_breaker.reset(budget)

            return web.json_response({
                "workflow_id": workflow.id,
                "name": workflow.name,
                "tasks": workflow.to_todo_list(),
                "status": workflow.get_status()
            })
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

    async def handle_workflow_status(self, request):
        """Get workflow status."""
        if not self.workflow_engine:
            return web.json_response(
                {"error": "Workflow engine not available"},
                status=503
            )

        workflow_id = request.match_info.get("workflow_id")
        if workflow_id and workflow_id in self.workflow_engine.workflows:
            workflow = self.workflow_engine.workflows[workflow_id]
            return web.json_response({
                "status": workflow.get_status(),
                "tasks": workflow.to_todo_list(),
                "governance": self.workflow_engine.generate_claude_md_governance(workflow)
            })

        # Return all workflows
        workflows = {
            wid: wf.get_status()
            for wid, wf in self.workflow_engine.workflows.items()
        }
        return web.json_response({"workflows": workflows})

    async def handle_workflow_prompt(self, request):
        """Generate orchestrator prompt for a workflow."""
        if not self.workflow_engine:
            return web.json_response(
                {"error": "Workflow engine not available"},
                status=503
            )

        workflow_id = request.match_info.get("workflow_id")
        if workflow_id not in self.workflow_engine.workflows:
            return web.json_response(
                {"error": f"Workflow not found: {workflow_id}"},
                status=404
            )

        workflow = self.workflow_engine.workflows[workflow_id]
        prompt = self.workflow_engine.generate_orchestrator_prompt(workflow)

        return web.json_response({
            "workflow_id": workflow_id,
            "prompt": prompt
        })

    async def handle_workflow_budget(self, request):
        """Get budget status."""
        if not self.workflow_engine:
            return web.json_response(
                {"error": "Workflow engine not available"},
                status=503
            )

        return web.json_response(
            self.workflow_engine.circuit_breaker.get_status()
        )

    async def handle_workflow_governance(self, request):
        """Get governance document for a workflow."""
        if not self.workflow_engine:
            return web.json_response(
                {"error": "Workflow engine not available"},
                status=503
            )

        workflow_id = request.match_info.get("workflow_id")
        if workflow_id not in self.workflow_engine.workflows:
            return web.json_response(
                {"error": f"Workflow not found: {workflow_id}"},
                status=404
            )

        workflow = self.workflow_engine.workflows[workflow_id]
        governance = self.workflow_engine.generate_claude_md_governance(workflow)

        return web.Response(text=governance, content_type="text/markdown")

    async def handle_websocket(self, request):
        """WebSocket handler for live updates."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.ws_clients.add(ws)
        
        # Send initial data
        await ws.send_json({
            "type": "init",
            "events": self.events[:50],
            "sessions": self.sessions,
            "stats": self._get_stats()
        })
        
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    # Handle client messages if needed
                    pass
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    break
        finally:
            self.ws_clients.discard(ws)
        
        return ws
    
    async def broadcast(self, data: Dict):
        """Broadcast message to all WebSocket clients."""
        if not self.ws_clients:
            return
        
        message = json.dumps(data)
        dead_clients = set()
        
        for client in self.ws_clients:
            try:
                await client.send_str(message)
            except Exception:
                dead_clients.add(client)
        
        self.ws_clients -= dead_clients
    
    async def stats_broadcaster(self):
        """Periodically broadcast stats updates."""
        while True:
            await asyncio.sleep(10)
            await self.broadcast({"type": "stats", "stats": self._get_stats()})
    
    def create_app(self) -> web.Application:
        """Create the web application."""
        app = web.Application()

        # Core routes
        app.router.add_get("/", self.handle_index)
        app.router.add_post("/events", self.handle_events_post)
        app.router.add_get("/api/events", self.handle_events_get)
        app.router.add_get("/api/sessions", self.handle_sessions)
        app.router.add_get("/api/stats", self.handle_stats)
        app.router.add_get("/health", self.handle_health)
        app.router.add_get("/ws", self.handle_websocket)

        # Workflow engine routes
        if self.workflow_engine:
            app.router.add_post("/api/workflow", self.handle_workflow_create)
            app.router.add_get("/api/workflow", self.handle_workflow_status)
            app.router.add_get("/api/workflow/{workflow_id}", self.handle_workflow_status)
            app.router.add_get("/api/workflow/{workflow_id}/prompt", self.handle_workflow_prompt)
            app.router.add_get("/api/workflow/{workflow_id}/governance", self.handle_workflow_governance)
            app.router.add_get("/api/budget", self.handle_workflow_budget)

        return app
    
    async def run(self):
        """Run the server."""
        app = self.create_app()
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(runner, "0.0.0.0", self.port)
        await site.start()
        
        print(f"[*] Agent Dashboard running at http://localhost:{self.port}")
        print(f"[>] Event endpoint: http://localhost:{self.port}/events")
        print(f"[~] WebSocket: ws://localhost:{self.port}/ws")
        if self.workflow_engine:
            print(f"[+] Workflow API: http://localhost:{self.port}/api/workflow")
            print(f"[$] Budget API: http://localhost:{self.port}/api/budget")
        
        # Start stats broadcaster
        asyncio.create_task(self.stats_broadcaster())
        
        # Keep running
        while True:
            await asyncio.sleep(3600)


def main():
    if not HAS_AIOHTTP:
        print("Error: aiohttp is required. Install with: pip install aiohttp")
        return

    parser = argparse.ArgumentParser(description="Agent Dashboard Web Server")
    parser.add_argument("--port", "-p", type=int, default=4200, help="Server port (default: 4200)")
    parser.add_argument("--db", type=str, help="Database path")
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Kill any existing process using the port"
    )
    parser.add_argument(
        "--auto-port", "-a",
        action="store_true",
        help="Automatically find an available port if the specified one is in use"
    )
    args = parser.parse_args()

    # Check port availability and handle conflicts
    port, success = check_port_and_handle(
        port=args.port,
        force=args.force,
        auto_port=args.auto_port
    )

    if not success:
        sys.exit(1)

    dashboard = WebDashboard(port=port)

    try:
        asyncio.run(dashboard.run())
    except KeyboardInterrupt:
        print("\n[x] Server stopped")


if __name__ == "__main__":
    main()
