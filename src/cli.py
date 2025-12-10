#!/usr/bin/env python3
"""
Agent Dashboard CLI - Unified command-line interface for the monitoring system.

Usage:
    agent-dashboard              # Terminal TUI (default)
    agent-dashboard --web        # Web dashboard
    agent-dashboard doctor       # Diagnose installation issues
    agent-dashboard status       # Show system status
    agent-dashboard test         # Send test event
    agent-dashboard logs         # View event logs
"""

import argparse
import asyncio
import json
import os
import sys
import socket
import urllib.request
from pathlib import Path
from datetime import datetime


def get_dashboard_dir() -> Path:
    """Get the dashboard installation directory."""
    return Path.home() / ".claude" / "dashboard"


def run_terminal_dashboard(args):
    """Launch the terminal TUI dashboard."""
    dashboard_file = get_dashboard_dir() / "agent_monitor.py"

    if not dashboard_file.exists():
        print(f"Error: Dashboard not found at {dashboard_file}")
        print("Run the installer first: ./scripts/install.sh")
        sys.exit(1)

    # Try to import and run directly
    try:
        sys.path.insert(0, str(get_dashboard_dir()))
        from agent_monitor import main
        main()
    except ImportError as e:
        # Fall back to subprocess
        import subprocess
        subprocess.run([
            sys.executable, str(dashboard_file),
            "--port", str(args.port)
        ])


def run_web_dashboard(args):
    """Launch the web dashboard server."""
    dashboard_file = get_dashboard_dir() / "web_server.py"

    if not dashboard_file.exists():
        print(f"Error: Web server not found at {dashboard_file}")
        print("Run the installer first: ./scripts/install.sh")
        sys.exit(1)

    try:
        sys.path.insert(0, str(get_dashboard_dir()))
        from web_server import main
        main()
    except ImportError:
        import subprocess
        subprocess.run([
            sys.executable, str(dashboard_file),
            "--port", str(args.port)
        ])


def send_test_event(args):
    """Send a test event to verify the system is working."""
    url = f"http://127.0.0.1:{args.port}/events"

    event = {
        "timestamp": datetime.now().isoformat(),
        "event_type": args.event_type,
        "agent_name": args.agent_name,
        "session_id": args.session_id,
        "project": args.project,
        "model": args.model,
        "tokens_in": 100,
        "tokens_out": 500,
        "cost": 0.0015,
        "payload": {
            "tool_name": "Bash",
            "tool_input": {"command": "echo 'Hello from test event!'"},
            "message": "This is a test event from agent-dashboard test"
        }
    }

    try:
        data = json.dumps(event).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                print(f"Test event sent successfully!")
                print(f"   Event type: {args.event_type}")
                print(f"   Agent: {args.agent_name}")
                print(f"   Project: {args.project}")
            else:
                print(f"Server returned status {response.status}")

    except urllib.error.URLError as e:
        print(f"Could not connect to dashboard server at {url}")
        print(f"   Error: {e}")
        print(f"\n   Make sure the server is running:")
        print(f"   agent-dashboard --web --port {args.port}")
        return 1
    except Exception as e:
        print(f"Error sending event: {e}")
        return 1

    return 0


def show_status(args):
    """Show the status of the dashboard system."""
    print("Agent Dashboard Status")
    print("=" * 50)

    # Check installation
    dashboard_dir = get_dashboard_dir()
    print(f"\nInstallation Directory: {dashboard_dir}")

    files_to_check = [
        ("agent_monitor.py", "Terminal Dashboard"),
        ("web_server.py", "Web Dashboard"),
        ("cli.py", "CLI Interface"),
        ("workflow_engine.py", "Workflow Engine"),
        ("hooks/send_event.py", "Event Hook"),
    ]

    print("\nComponents:")
    for filename, description in files_to_check:
        filepath = dashboard_dir / filename
        status = "[OK]" if filepath.exists() else "[MISSING]"
        print(f"   {status} {description}")

    # Check agents
    agents_dir = Path.home() / ".claude" / "agents"
    if agents_dir.exists():
        agent_count = len(list(agents_dir.glob("*.md")))
        print(f"\nAgents: {agent_count} installed")
    else:
        print("\nAgents: Directory not found")

    # Check server
    print(f"\nServer Status (port {args.port}):")
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{args.port}/health")
        with urllib.request.urlopen(req, timeout=2) as response:
            if response.status == 200:
                print(f"   [RUNNING] Server is healthy")
            else:
                print(f"   [WARNING] Server returned status {response.status}")
    except Exception:
        print(f"   [STOPPED] Server is not running")
        print(f"   Start with: agent-dashboard --web")

    # Check settings.json
    settings_file = Path.home() / ".claude" / "settings.json"
    print(f"\nClaude Code Settings: {settings_file}")
    if settings_file.exists():
        try:
            settings = json.loads(settings_file.read_text())
            hooks = settings.get("hooks", {})
            hook_count = len(hooks)
            print(f"   [OK] Found with {hook_count} hook types configured")

            # Check if dashboard hooks are present
            has_dashboard = any(
                "send_event.py" in str(h) or "run_hook.sh" in str(h)
                for hook_list in hooks.values()
                for matcher in hook_list
                for h in matcher.get("hooks", [])
            )
            if has_dashboard:
                print(f"   [OK] Dashboard hooks are configured")
            else:
                print(f"   [WARNING] Dashboard hooks not found")
        except Exception as e:
            print(f"   [WARNING] Could not parse settings: {e}")
    else:
        print(f"   [MISSING] Not found")

    # Check database
    db_file = Path.home() / ".claude" / "agent_dashboard.db"
    if db_file.exists():
        size = db_file.stat().st_size
        size_str = f"{size / 1024:.1f} KB" if size > 1024 else f"{size} bytes"
        print(f"\nDatabase: {size_str}")
    else:
        print(f"\nDatabase: Not created yet")

    return 0


def run_doctor(args):
    """
    Diagnose common installation and configuration issues.

    Checks:
        - Python version and availability
        - Required dependencies (rich, aiohttp, tiktoken)
        - Installation directories and files
        - Agent definitions
        - Dashboard connectivity
    """
    issues = 0
    warnings = 0

    print("Agent Dashboard Doctor")
    print("=" * 50)

    # Check Python version
    print("\n[1/6] Python")
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info >= (3, 9):
        print(f"  [OK] Python {py_version}")
    else:
        print(f"  [FAIL] Python {py_version} (requires 3.9+)")
        issues += 1

    # Check dependencies
    print("\n[2/6] Dependencies")
    deps = [
        ('rich', 'Terminal UI'),
        ('aiohttp', 'Web server'),
    ]
    for module, desc in deps:
        try:
            mod = __import__(module)
            version = getattr(mod, '__version__', 'installed')
            print(f"  [OK] {module} {version} ({desc})")
        except ImportError:
            print(f"  [FAIL] {module} not installed ({desc})")
            print(f"         Fix: pip install {module}")
            issues += 1

    # tiktoken is optional
    try:
        import tiktoken
        version = getattr(tiktoken, '__version__', 'installed')
        print(f"  [OK] tiktoken {version} (token counting)")
    except ImportError:
        print(f"  [WARN] tiktoken not installed (optional)")
        warnings += 1

    # Check installation
    print("\n[3/6] Installation")
    dashboard_dir = Path.home() / ".claude" / "dashboard"
    agents_dir = Path.home() / ".claude" / "agents"

    required_files = [
        (dashboard_dir / "agent_monitor.py", "Terminal dashboard"),
        (dashboard_dir / "web_server.py", "Web dashboard"),
        (dashboard_dir / "cli.py", "CLI interface"),
        (dashboard_dir / "hooks" / "send_event.py", "Event hook"),
    ]

    for filepath, desc in required_files:
        if filepath.exists():
            print(f"  [OK] {filepath.name} ({desc})")
        else:
            print(f"  [FAIL] {filepath.name} missing ({desc})")
            issues += 1

    # Check agents
    print("\n[4/6] Agents")
    if agents_dir.exists():
        agent_files = list(agents_dir.glob("*.md"))
        if len(agent_files) >= 14:
            print(f"  [OK] {len(agent_files)} agents installed")
        else:
            print(f"  [WARN] {len(agent_files)}/14 agents installed")
            warnings += 1
    else:
        print(f"  [FAIL] Agents directory not found")
        issues += 1

    # Check PATH
    print("\n[5/6] PATH")
    import shutil
    if shutil.which("agent-dashboard"):
        print("  [OK] agent-dashboard in PATH")
    else:
        bin_file = Path.home() / ".local" / "bin" / "agent-dashboard"
        if bin_file.exists():
            print("  [WARN] agent-dashboard not in PATH")
            print("         Add to ~/.bashrc: export PATH=\"$HOME/.local/bin:$PATH\"")
            warnings += 1
        else:
            print("  [FAIL] agent-dashboard not installed")
            issues += 1

    # Check dashboard connectivity
    print("\n[6/6] Server")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('127.0.0.1', args.port))
        sock.close()
        if result == 0:
            print(f"  [OK] Dashboard running on port {args.port}")
        else:
            print(f"  [INFO] Dashboard not running")
            print(f"         Start: agent-dashboard --web")
    except Exception as e:
        print(f"  [WARN] Could not check port: {e}")
        warnings += 1

    # Summary
    print("\n" + "=" * 50)
    if issues == 0 and warnings == 0:
        print("All checks passed!")
    elif issues == 0:
        print(f"{warnings} warning(s), but installation is functional")
    else:
        print(f"{issues} issue(s) and {warnings} warning(s) found")
        print("\nTo fix, run: ./scripts/install.sh")

    return issues


def show_logs(args):
    """
    Display recent log entries.

    Args:
        args.lines: Number of lines to show (default: 50)
        args.follow: Follow log file in real-time
    """
    import subprocess

    log_file = Path.home() / ".claude" / "logs" / "agent_events.log"

    if not log_file.exists():
        # Try the database as an alternative
        db_file = Path.home() / ".claude" / "agent_dashboard.db"
        if db_file.exists():
            print("No log file found. Showing recent events from database...")
            print("")
            show_recent_events_from_db(db_file, args.lines)
        else:
            print("No log file or database found.")
            print("Start the dashboard to generate logs: agent-dashboard --web")
        return 0

    if args.follow:
        # Follow mode (like tail -f)
        print(f"Following {log_file} (Ctrl+C to exit)...")
        try:
            subprocess.run(["tail", "-f", str(log_file)])
        except KeyboardInterrupt:
            pass
        except FileNotFoundError:
            # tail not available (Windows)
            print("Follow mode requires 'tail' command.")
            print("Showing last entries instead...")
            show_log_entries(log_file, args.lines)
    else:
        show_log_entries(log_file, args.lines)

    return 0


def show_log_entries(log_file: Path, lines: int):
    """Show last N lines from log file."""
    try:
        with open(log_file) as f:
            all_lines = f.readlines()
            for line in all_lines[-lines:]:
                print(line, end='')
    except Exception as e:
        print(f"Error reading log file: {e}")


def show_recent_events_from_db(db_file: Path, limit: int):
    """Show recent events from SQLite database."""
    import sqlite3

    try:
        with sqlite3.connect(db_file) as conn:
            cursor = conn.execute("""
                SELECT timestamp, agent_name, event_type, project
                FROM events
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))

            rows = cursor.fetchall()
            if not rows:
                print("No events in database yet.")
                return

            print(f"{'Timestamp':<25} {'Agent':<20} {'Event':<15} {'Project':<20}")
            print("-" * 80)
            for row in reversed(rows):
                timestamp = row[0][:19] if row[0] else ""
                agent = (row[1] or "")[:18]
                event = (row[2] or "")[:13]
                project = (row[3] or "")[:18]
                print(f"{timestamp:<25} {agent:<20} {event:<15} {project:<20}")
    except Exception as e:
        print(f"Error reading database: {e}")


def show_config(args):
    """Show current configuration."""
    print("Agent Dashboard Configuration")
    print("=" * 50)

    # Installation paths
    print("\nInstallation Paths:")
    print(f"  Dashboard: {Path.home() / '.claude' / 'dashboard'}")
    print(f"  Agents:    {Path.home() / '.claude' / 'agents'}")
    print(f"  Database:  {Path.home() / '.claude' / 'agent_dashboard.db'}")
    print(f"  Logs:      {Path.home() / '.claude' / 'logs'}")
    print(f"  CLI:       {Path.home() / '.local' / 'bin' / 'agent-dashboard'}")

    # Settings
    settings_file = Path.home() / ".claude" / "settings.json"
    if settings_file.exists():
        print(f"\nSettings ({settings_file}):")
        try:
            settings = json.loads(settings_file.read_text())
            print(json.dumps(settings, indent=2))
        except Exception as e:
            print(f"  Error reading settings: {e}")
    else:
        print(f"\nSettings: Not configured")

    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Agent Dashboard - Multi-Agent Monitoring for Claude Code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  agent-dashboard              Launch terminal TUI dashboard
  agent-dashboard --web        Launch web dashboard
  agent-dashboard doctor       Check installation
  agent-dashboard status       Check system status
  agent-dashboard test         Send a test event
  agent-dashboard logs         View recent events
        """
    )

    parser.add_argument(
        "--web", "-w",
        action="store_true",
        help="Launch web dashboard instead of terminal TUI"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=4200,
        help="Server port (default: 4200)"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Status command
    status_parser = subparsers.add_parser("status", help="Show system status")
    status_parser.set_defaults(func=show_status)

    # Test command
    test_parser = subparsers.add_parser("test", help="Send a test event")
    test_parser.add_argument("--event-type", default="PreToolUse", help="Event type")
    test_parser.add_argument("--agent-name", default="test-agent", help="Agent name")
    test_parser.add_argument("--session-id", default="test-session", help="Session ID")
    test_parser.add_argument("--project", default="test-project", help="Project name")
    test_parser.add_argument("--model", default="sonnet", help="Model name")
    test_parser.set_defaults(func=send_test_event)

    # Doctor command
    doctor_parser = subparsers.add_parser("doctor", help="Diagnose installation issues")
    doctor_parser.set_defaults(func=run_doctor)

    # Logs command
    logs_parser = subparsers.add_parser("logs", help="View event logs")
    logs_parser.add_argument("-n", "--lines", type=int, default=50, help="Number of lines to show")
    logs_parser.add_argument("-f", "--follow", action="store_true", help="Follow log output")
    logs_parser.set_defaults(func=show_logs)

    # Config command
    config_parser = subparsers.add_parser("config", help="Show configuration")
    config_parser.set_defaults(func=show_config)

    args = parser.parse_args()

    # Handle commands
    if hasattr(args, "func"):
        sys.exit(args.func(args))
    elif args.web:
        run_web_dashboard(args)
    else:
        run_terminal_dashboard(args)


if __name__ == "__main__":
    main()
