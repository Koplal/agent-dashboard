#!/usr/bin/env python3
"""
run_hook.py - Cross-Platform Hook Wrapper

This Python wrapper provides an alternative to run_hook.sh for environments
where bash is not available or reliable (e.g., Windows without Git Bash).

Usage:
    python run_hook.py --event-type PreToolUse --agent-name researcher

The wrapper resolves shell variable syntax (${VAR:-default}) since Windows
doesn't expand these, then forwards arguments to send_event.py.

Version: 2.6.0
"""

import os
import re
import sys
import subprocess


def resolve_shell_variable(value: str) -> str:
    """Resolve shell variable syntax ${VAR:-default} to actual values.

    Examples:
        ${AGENT_NAME:-claude} -> os.environ.get('AGENT_NAME', 'claude')
        ${AGENT_MODEL:-sonnet} -> os.environ.get('AGENT_MODEL', 'sonnet')
    """
    # Match ${VAR:-default} pattern
    pattern = r'\$\{([^:}]+):-([^}]+)\}'

    def replacer(match):
        var_name = match.group(1)
        default_value = match.group(2)
        return os.environ.get(var_name, default_value)

    # Also handle ${VAR} without default
    simple_pattern = r'\$\{([^}]+)\}'

    result = re.sub(pattern, replacer, value)
    result = re.sub(simple_pattern, lambda m: os.environ.get(m.group(1), ''), result)

    return result


def main():
    """Execute send_event.py with resolved arguments."""
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    send_event_path = os.path.join(script_dir, "send_event.py")

    # Verify send_event.py exists
    if not os.path.exists(send_event_path):
        sys.exit(0)  # Silently exit - don't break Claude Code

    # Resolve shell variables in arguments
    resolved_args = [resolve_shell_variable(arg) for arg in sys.argv[1:]]

    # Forward resolved arguments to send_event.py
    try:
        result = subprocess.run(
            [sys.executable, send_event_path] + resolved_args,
            stdin=sys.stdin,
            capture_output=True,  # Don't pollute Claude Code terminal
            timeout=10
        )
    except Exception:
        pass  # Silently ignore all errors

    # Always exit successfully - hooks should never break Claude Code
    sys.exit(0)


if __name__ == "__main__":
    main()
