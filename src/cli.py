#!/usr/bin/env python3
"""
Agent Dashboard CLI - Unified command-line interface for the monitoring system.

Usage:
    agent-dashboard              # Terminal TUI (default)
    agent-dashboard --web        # Web dashboard
    agent-dashboard server       # Run event server only
    agent-dashboard test         # Send test event
"""

import argparse
import asyncio
import json
import os
import sys
import urllib.request
from pathlib import Path


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
        "timestamp": "2024-01-01T12:00:00",
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
            "message": "This is a test event"
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
                print(f"✅ Test event sent successfully!")
                print(f"   Event type: {args.event_type}")
                print(f"   Agent: {args.agent_name}")
                print(f"   Project: {args.project}")
            else:
                print(f"❌ Server returned status {response.status}")
                
    except urllib.error.URLError as e:
        print(f"❌ Could not connect to dashboard server at {url}")
        print(f"   Error: {e}")
        print(f"\n   Make sure the server is running:")
        print(f"   agent-dashboard --web --port {args.port}")
    except Exception as e:
        print(f"❌ Error sending event: {e}")


def show_status(args):
    """Show the status of the dashboard system."""
    print("🤖 Agent Dashboard Status")
    print("=" * 40)
    
    # Check installation
    dashboard_dir = get_dashboard_dir()
    print(f"\n📁 Installation Directory: {dashboard_dir}")
    
    files_to_check = [
        ("agent_monitor.py", "Terminal Dashboard"),
        ("web_server.py", "Web Dashboard"),
        ("hooks/send_event.py", "Event Hook"),
        ("agent_dashboard.db", "Database"),
    ]
    
    print("\n📦 Components:")
    for filename, description in files_to_check:
        filepath = dashboard_dir / filename
        status = "✅" if filepath.exists() else "❌"
        print(f"   {status} {description}: {filepath}")
    
    # Check server
    print(f"\n📡 Server Status (port {args.port}):")
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{args.port}/health")
        with urllib.request.urlopen(req, timeout=2) as response:
            if response.status == 200:
                print(f"   ✅ Server is running")
            else:
                print(f"   ⚠️ Server returned status {response.status}")
    except Exception:
        print(f"   ❌ Server is not running")
    
    # Check settings.json
    settings_file = Path.home() / ".claude" / "settings.json"
    print(f"\n⚙️ Claude Code Settings: {settings_file}")
    if settings_file.exists():
        try:
            settings = json.loads(settings_file.read_text())
            hooks = settings.get("hooks", {})
            hook_count = len(hooks)
            print(f"   ✅ Found with {hook_count} hook types configured")
            
            # Check if dashboard hooks are present
            has_dashboard = any(
                "send_event.py" in str(h)
                for hook_list in hooks.values()
                for matcher in hook_list
                for h in matcher.get("hooks", [])
            )
            if has_dashboard:
                print(f"   ✅ Dashboard hooks are configured")
            else:
                print(f"   ⚠️ Dashboard hooks not found")
        except Exception as e:
            print(f"   ⚠️ Could not parse settings: {e}")
    else:
        print(f"   ❌ Not found")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Agent Dashboard - Multi-Agent Monitoring for Claude Code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  agent-dashboard              Launch terminal TUI dashboard
  agent-dashboard --web        Launch web dashboard
  agent-dashboard status       Check system status
  agent-dashboard test         Send a test event
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
    
    args = parser.parse_args()
    
    # Handle commands
    if hasattr(args, "func"):
        args.func(args)
    elif args.web:
        run_web_dashboard(args)
    else:
        run_terminal_dashboard(args)


if __name__ == "__main__":
    main()
