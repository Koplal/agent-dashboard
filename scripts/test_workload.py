#!/usr/bin/env python3
"""
test_workload.py - Generate test workload for dashboard UI testing

Simulates multiple agents across different projects to test the
collapsible project grouping feature.

Usage:
    python scripts/test_workload.py
"""

import json
import time
import random
import urllib.request
import urllib.error
from datetime import datetime

DASHBOARD_URL = "http://127.0.0.1:4200/events"

# Test projects with their agents
PROJECTS = {
    "web-frontend": {
        "agents": ["researcher", "implementer", "test-writer", "critic"],
        "description": "React frontend application"
    },
    "api-backend": {
        "agents": ["planner", "implementer", "validator", "orchestrator"],
        "description": "Node.js API service"
    },
    "data-pipeline": {
        "agents": ["researcher", "synthesis", "implementer"],
        "description": "ETL data processing"
    },
    "mobile-app": {
        "agents": ["explorer", "implementer", "test-writer"],
        "description": "React Native mobile app"
    },
    "infrastructure": {
        "agents": ["planner", "installer", "validator"],
        "description": "Terraform/K8s infrastructure"
    }
}

# Tools that agents might use
TOOLS = ["Read", "Write", "Edit", "Bash", "Grep", "Glob", "WebSearch", "Task"]

# Models
MODELS = ["claude-sonnet-4-20250514", "claude-opus-4-5-20251101", "claude-haiku-3-5-20241022"]


def send_event(event_data):
    """Send an event to the dashboard."""
    try:
        data = json.dumps(event_data).encode('utf-8')
        req = urllib.request.Request(
            DASHBOARD_URL,
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"Error sending event: {e}")
        return False


def generate_session_id(project, agent):
    """Generate a unique session ID."""
    return f"{project}-{agent}-{int(time.time() * 1000)}"


def simulate_agent_activity(project, agent, session_id):
    """Simulate a series of agent activities."""
    model = random.choice(MODELS)

    # Session start
    event = {
        "event_type": "SessionStart",
        "agent_name": agent,
        "project": project,
        "session_id": session_id,
        "model": model,
        "timestamp": datetime.now().isoformat(),
        "payload": {
            "description": f"Starting {agent} session for {project}"
        }
    }
    send_event(event)
    print(f"  [+] Started {agent} in {project}")

    # Simulate 2-5 tool uses
    num_tools = random.randint(2, 5)
    for i in range(num_tools):
        time.sleep(random.uniform(0.1, 0.3))

        tool = random.choice(TOOLS)
        input_tokens = random.randint(100, 2000)
        output_tokens = random.randint(50, 1500)

        # PreToolUse event
        event = {
            "event_type": "PreToolUse",
            "agent_name": agent,
            "project": project,
            "session_id": session_id,
            "model": model,
            "timestamp": datetime.now().isoformat(),
            "payload": {
                "tool_name": tool,
                "tool_input": {"content": "x" * input_tokens}
            }
        }
        send_event(event)

        # PostToolUse event
        time.sleep(random.uniform(0.05, 0.15))
        event = {
            "event_type": "PostToolUse",
            "agent_name": agent,
            "project": project,
            "session_id": session_id,
            "model": model,
            "timestamp": datetime.now().isoformat(),
            "payload": {
                "tool_name": tool,
                "output": "y" * output_tokens
            }
        }
        send_event(event)
        print(f"      [{agent}] Used {tool} ({input_tokens}+{output_tokens} tokens)")


def run_test_workload():
    """Run the test workload simulation."""
    print("=" * 60)
    print("Agent Dashboard Test Workload Generator")
    print("=" * 60)
    print(f"Dashboard URL: {DASHBOARD_URL}")
    print(f"Projects: {len(PROJECTS)}")
    print(f"Total agents: {sum(len(p['agents']) for p in PROJECTS.values())}")
    print("=" * 60)
    print()

    # Start agents across all projects
    active_sessions = []

    for project, config in PROJECTS.items():
        print(f"\n[PROJECT] {project} - {config['description']}")

        # Start some agents for this project
        agents_to_start = random.sample(
            config["agents"],
            k=random.randint(2, len(config["agents"]))
        )

        for agent in agents_to_start:
            session_id = generate_session_id(project, agent)
            active_sessions.append({
                "project": project,
                "agent": agent,
                "session_id": session_id,
                "model": random.choice(MODELS)
            })
            simulate_agent_activity(project, agent, session_id)
            time.sleep(random.uniform(0.1, 0.3))

    print("\n" + "=" * 60)
    print(f"Test workload complete!")
    print(f"  - {len(PROJECTS)} projects")
    print(f"  - {len(active_sessions)} active agent sessions")
    print("=" * 60)
    print("\nCheck the dashboard at http://localhost:4200")
    print("You should see projects grouped with collapsible sections.")

    # Keep sessions active with periodic updates
    print("\nSending periodic updates for 20 seconds...")
    print("Press Ctrl+C to stop early.\n")

    try:
        end_time = time.time() + 20
        while time.time() < end_time:
            session = random.choice(active_sessions)
            tool = random.choice(TOOLS)

            event = {
                "event_type": "PostToolUse",
                "agent_name": session["agent"],
                "project": session["project"],
                "session_id": session["session_id"],
                "model": session["model"],
                "timestamp": datetime.now().isoformat(),
                "payload": {
                    "tool_name": tool,
                    "output": "z" * random.randint(100, 500)
                }
            }
            send_event(event)
            print(f"  [{session['project']}] {session['agent']} used {tool}")
            time.sleep(random.uniform(0.5, 1.5))

    except KeyboardInterrupt:
        print("\n\nStopped by user.")

    print("\nTest workload finished.")


if __name__ == "__main__":
    run_test_workload()
