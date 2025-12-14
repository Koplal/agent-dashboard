#!/usr/bin/env python3
"""
run_hook.py - Cross-Platform Hook Wrapper

This Python wrapper provides an alternative to run_hook.sh for environments
where bash is not available or reliable (e.g., Windows without Git Bash).

Usage:
    python run_hook.py --event-type PreToolUse --agent-name researcher

The wrapper simply forwards all arguments to send_event.py.

Version: 2.2.1
"""

import os
import sys
import subprocess


def main():
    """Execute send_event.py with forwarded arguments."""
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    send_event_path = os.path.join(script_dir, "send_event.py")

    # Verify send_event.py exists
    if not os.path.exists(send_event_path):
        print(f"Error: send_event.py not found at {send_event_path}", file=sys.stderr)
        sys.exit(1)

    # Forward all arguments to send_event.py
    try:
        result = subprocess.run(
            [sys.executable, send_event_path] + sys.argv[1:],
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        sys.exit(result.returncode)
    except Exception as e:
        # Silently fail to avoid breaking Claude Code
        # Hook failures should not interrupt the main process
        print(f"Warning: Hook execution failed: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
