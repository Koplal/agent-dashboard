#!/usr/bin/env python3
"""
send_event.py - Universal event sender for Agent Dashboard

This script sends events to the Agent Dashboard server from Claude Code hooks.
It captures agent activities, tool usage, and session information.

Usage:
    uv run send_event.py --event-type PreToolUse --agent-name researcher

Environment:
    AGENT_DASHBOARD_URL: Dashboard server URL (default: http://127.0.0.1:4200)
    AGENT_PROJECT: Project identifier (auto-detected from git or cwd)

Dependencies:
    - tiktoken: Accurate token counting (optional, falls back to estimation)

Token Counting:
    For accurate token counting, this module extracts content from multiple
    payload fields including tool_input, output, content, and response data.

Version: 2.3.0
"""

import argparse
import json
import os
import sys
import subprocess
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import urllib.request
import urllib.error

# Token counting - standalone implementation for hook usage
# This avoids import path issues when running from ~/.claude/dashboard/hooks/
_TIKTOKEN_AVAILABLE = False
_encoding = None

try:
    import tiktoken
    _encoding = tiktoken.get_encoding("cl100k_base")
    _TIKTOKEN_AVAILABLE = True
except (ImportError, Exception):
    pass  # Silently fall back to character estimation


def count_tokens(text: str, **kwargs) -> int:
    """Count tokens using tiktoken or character estimation fallback."""
    if not text:
        return 0
    if _TIKTOKEN_AVAILABLE and _encoding:
        try:
            return len(_encoding.encode(text))
        except Exception:
            pass
    # Character estimation fallback (~4 chars per token)
    return len(text) // 4


def get_tokenizer_info():
    """Get tokenizer info for diagnostics."""
    return type('TokenizerInfo', (), {
        'name': 'tiktoken' if _TIKTOKEN_AVAILABLE else 'character',
        'accuracy': '~70-85%' if _TIKTOKEN_AVAILABLE else '~60-70%'
    })()

# Configuration
DEFAULT_URL = "http://127.0.0.1:4200/events"
TIMEOUT_SECONDS = 5


def get_project_name() -> str:
    """Auto-detect project name from git or directory."""
    # Try environment variable first
    if env_project := os.environ.get("AGENT_PROJECT"):
        return env_project
    
    # Try git remote
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            url = result.stdout.strip()
            # Extract repo name from URL
            name = url.rstrip("/").split("/")[-1]
            if name.endswith(".git"):
                name = name[:-4]
            return name
    except Exception:
        pass
    
    # Try git repo root name
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            return Path(result.stdout.strip()).name
    except Exception:
        pass
    
    # Fallback to current directory name
    return Path.cwd().name


def get_session_id() -> str:
    """Get or generate a session ID."""
    # Check environment for session ID
    if session_id := os.environ.get("CLAUDE_SESSION_ID"):
        return session_id

    # Safely get home directory (handles missing HOME env var)
    try:
        home_dir = Path.home()
    except RuntimeError:
        # Fallback for environments where HOME is not set
        home_dir = Path(os.environ.get("USERPROFILE", os.environ.get("HOME", ".")))

    # Try to read from Claude Code's session file
    session_file = home_dir / ".claude" / "session"
    if session_file.exists():
        try:
            return session_file.read_text().strip()[:36]
        except Exception:
            pass

    # Generate a deterministic session ID based on terminal
    terminal_info = f"{os.environ.get('TERM_SESSION_ID', '')}{os.environ.get('TMUX', '')}{os.getppid()}"
    return hashlib.md5(terminal_info.encode()).hexdigest()[:16]


def get_git_info() -> Dict[str, str]:
    """Get current git branch and status."""
    info = {"branch": "unknown", "dirty": False}
    
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            info["branch"] = result.stdout.strip() or "HEAD"
    except Exception:
        pass
    
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=2
        )
        info["dirty"] = bool(result.stdout.strip())
    except Exception:
        pass
    
    return info


def read_stdin_payload() -> Dict[str, Any]:
    """Read JSON payload from stdin (Claude Code hook format)."""
    if sys.stdin.isatty():
        return {}
    
    try:
        input_data = sys.stdin.read()
        if input_data:
            return json.loads(input_data)
    except json.JSONDecodeError:
        pass
    except Exception:
        pass
    
    return {}




def extract_token_content(payload: Dict[str, Any]) -> Tuple[str, str]:
    """Extract input and output content from event payload for accurate token counting.
    
    This fixes the token counting accuracy issue by checking multiple payload fields,
    not just tool_input.command.
    """
    input_parts = []
    output_parts = []
    
    tool_input = payload.get("tool_input", {})
    if isinstance(tool_input, dict):
        input_fields = ["command", "content", "file_path", "query", "prompt", "pattern", 
                       "code", "message", "text", "description", "new_source", "old_string", "new_string"]
        for field in input_fields:
            if field in tool_input and tool_input[field]:
                input_parts.append(str(tool_input[field]))
        if not input_parts and tool_input:
            input_parts.append(json.dumps(tool_input))
    elif tool_input:
        input_parts.append(str(tool_input))
    
    output_fields = ["output", "result", "response", "content", "data"]
    for field in output_fields:
        if field in payload and payload[field]:
            output_parts.append(str(payload[field]))
            break
    
    if "response" in payload and isinstance(payload["response"], dict):
        resp = payload["response"]
        if "content" in resp and resp["content"] and not output_parts:
            output_parts.append(str(resp["content"]))
    
    return "\n".join(input_parts), "\n".join(output_parts)

def estimate_tokens(text: str) -> int:
    """
    Estimate token count for text.

    Uses centralized token_counter module if available,
    otherwise falls back to local implementation.
    """
    return count_tokens(text)


def estimate_cost(tokens_in: int, tokens_out: int, model: str) -> float:
    """Estimate cost based on model pricing."""
    pricing = {
        "haiku": {"input": 0.25 / 1_000_000, "output": 1.25 / 1_000_000},
        "sonnet": {"input": 3.0 / 1_000_000, "output": 15.0 / 1_000_000},
        "opus": {"input": 15.0 / 1_000_000, "output": 75.0 / 1_000_000},
    }
    
    model_key = model.lower()
    for key in pricing:
        if key in model_key:
            prices = pricing[key]
            return tokens_in * prices["input"] + tokens_out * prices["output"]
    
    # Default to sonnet pricing
    return tokens_in * 3.0 / 1_000_000 + tokens_out * 15.0 / 1_000_000


def send_event(
    event_type: str,
    agent_name: str,
    payload: Dict[str, Any],
    model: str = "sonnet",
    summarize: bool = False,
    dashboard_url: Optional[str] = None,
) -> bool:
    """Send an event to the Agent Dashboard server."""
    
    url = dashboard_url or os.environ.get("AGENT_DASHBOARD_URL", DEFAULT_URL)
    
    # Build event data
    git_info = get_git_info()
    
    # Extract and estimate tokens using improved extraction (fixes accuracy issue)
    input_content, output_content = extract_token_content(payload)
    tokens_in = estimate_tokens(input_content)
    tokens_out = estimate_tokens(output_content)
    
    event = {
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "agent_name": agent_name,
        "session_id": get_session_id(),
        "project": get_project_name(),
        "model": model,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost": estimate_cost(tokens_in, tokens_out, model),
        "payload": {
            **payload,
            "git_branch": git_info["branch"],
            "git_dirty": git_info["dirty"],
        }
    }
    
    # Optional: Add AI summary
    if summarize and event_type in ("PostToolUse", "Stop", "SubagentStop"):
        try:
            summary = generate_summary(payload)
            if summary:
                event["payload"]["summary"] = summary
        except Exception:
            pass  # Silently skip if summarization fails
    
    try:
        data = json.dumps(event).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
            return response.status == 200

    except urllib.error.URLError:
        # Server not running - silently ignore (don't pollute Claude Code terminal)
        pass
    except Exception:
        # Silently ignore all errors to avoid polluting Claude Code terminal
        # Hook failures should never interrupt the user's workflow
        pass

    return False


def generate_summary(payload: Dict[str, Any]) -> Optional[str]:
    """Generate a brief AI summary of the event (optional)."""
    # This would call Claude API for summarization
    # For now, extract key info without API call
    
    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {})
    
    if tool_name == "Bash":
        cmd = tool_input.get("command", "")
        return f"Executed: {cmd[:100]}"
    elif tool_name == "Read":
        path = tool_input.get("file_path", "")
        return f"Read file: {path}"
    elif tool_name == "Write":
        path = tool_input.get("file_path", "")
        return f"Wrote file: {path}"
    elif tool_name == "WebSearch":
        query = tool_input.get("query", "")
        return f"Searched: {query[:50]}"
    
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Send events to Agent Dashboard"
    )
    parser.add_argument(
        "--event-type",
        required=True,
        choices=[
            "PreToolUse", "PostToolUse", "Notification", "Stop", 
            "SubagentStop", "PreCompact", "UserPromptSubmit",
            "SessionStart", "SessionEnd", "TaskStart", "TaskComplete",
            "TaskError", "Research", "Summary"
        ],
        help="Type of event"
    )
    parser.add_argument(
        "--agent-name",
        default="claude",
        help="Name of the agent (e.g., researcher, summarizer)"
    )
    parser.add_argument(
        "--model",
        default="sonnet",
        choices=["haiku", "sonnet", "opus"],
        help="Model being used"
    )
    parser.add_argument(
        "--summarize",
        action="store_true",
        help="Add AI-generated summary to event"
    )
    parser.add_argument(
        "--url",
        help="Dashboard server URL"
    )
    parser.add_argument(
        "--payload",
        help="JSON payload (alternative to stdin)"
    )
    
    args = parser.parse_args()
    
    # Get payload from stdin or argument
    if args.payload:
        try:
            payload = json.loads(args.payload)
        except json.JSONDecodeError:
            payload = {"raw": args.payload}
    else:
        payload = read_stdin_payload()
    
    send_event(
        event_type=args.event_type,
        agent_name=args.agent_name,
        payload=payload,
        model=args.model,
        summarize=args.summarize,
        dashboard_url=args.url,
    )

    # Always exit successfully - hook failures should never break Claude Code
    sys.exit(0)


if __name__ == "__main__":
    main()
