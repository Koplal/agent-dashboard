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

Subagent Name Extraction:
    For Task tool usage and SubagentStop events, the subagent name is automatically
    extracted from the payload and used instead of the parent agent name. This ensures
    proper tracking of spawned subagents in the dashboard.

Version: 2.5.2
"""

import argparse
import json
import os
import sys
import re
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


def extract_subagent_name(payload, event_type, fallback_name):
    """Extract subagent name from payload for Task tool usage and SubagentStop events.
    
    Claude Code passes subagent information in the payload when:
    1. Using the Task tool to spawn a subagent (tool_name == "Task")
    2. SubagentStop events contain info about which subagent stopped
    
    Returns:
        Tuple of (agent_name, subagent_model) - model may be None
    """
    subagent_name = None
    subagent_model = None
    
    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {})
    
    # Handle Task tool - extract the agent being spawned
    if tool_name == "Task":
        if isinstance(tool_input, dict):
            # Check for explicit agent field
            for field in ["subagent_type", "agent", "agent_name", "name", "subagent"]:
                if field in tool_input and tool_input[field]:
                    subagent_name = str(tool_input[field]).strip()
                    break
            
            # Check for model/tier specification
            for field in ["model", "tier", "agent_model"]:
                if field in tool_input and tool_input[field]:
                    subagent_model = str(tool_input[field]).strip().lower()
                    break
            
            # If no explicit agent field, try to extract from description/prompt
            if not subagent_name:
                for field in ["description", "prompt", "task", "content"]:
                    if field in tool_input and tool_input[field]:
                        text = str(tool_input[field])
                        patterns = [
                            r'^Task\(([a-zA-Z_-]+)\)',
                            r'^\[([a-zA-Z_-]+)\]',
                            r'^([a-zA-Z_-]+):\s',
                            r'^@([a-zA-Z_-]+)\s',
                        ]
                        for pattern in patterns:
                            match = re.match(pattern, text, re.IGNORECASE)
                            if match:
                                subagent_name = match.group(1).lower()
                                break
                        if subagent_name:
                            break
    
    # Handle SubagentStop events
    elif event_type == "SubagentStop":
        for field in ["subagent_name", "agent_name", "subagent", "agent", "name"]:
            if field in payload and payload[field]:
                subagent_name = str(payload[field]).strip()
                break
        
        for field in ["subagent_model", "model", "tier"]:
            if field in payload and payload[field]:
                subagent_model = str(payload[field]).strip().lower()
                break
        
        tool_response = payload.get("tool_response", {})
        if isinstance(tool_response, dict) and not subagent_name:
            for field in ["agent_name", "subagent", "agent"]:
                if field in tool_response and tool_response[field]:
                    subagent_name = str(tool_response[field]).strip()
                    break
    
    # Normalize and validate
    if subagent_name:
        subagent_name = subagent_name.strip().lower()
        subagent_name = re.sub(r'^(agent[_-]?|subagent[_-]?)', '', subagent_name)
        if subagent_name and re.match(r'^[a-z][a-z0-9_-]*$', subagent_name):
            return subagent_name, subagent_model
    
    return fallback_name, subagent_model



def extract_token_content(payload: Dict[str, Any]) -> Tuple[str, str]:
    """Extract input and output content from event payload for accurate token counting.

    Extracts from Claude Code hook payload structure:
    - Input: tool_input fields (command, content, query, etc.)
    - Output: tool_response.stdout, tool_response.file.content, etc.
    """
    input_parts = []
    output_parts = []

    # Extract from tool_input (the input to the tool)
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

    # Extract from tool_response (the output from the tool)
    # Claude Code hooks use tool_response with stdout/stderr or file content
    tool_response = payload.get("tool_response", {})
    if isinstance(tool_response, dict):
        # Bash tool output - stdout field
        if "stdout" in tool_response and tool_response["stdout"]:
            output_parts.append(str(tool_response["stdout"]))
        # Read tool output - file.content field
        if "file" in tool_response and isinstance(tool_response["file"], dict):
            file_content = tool_response["file"].get("content", "")
            if file_content:
                output_parts.append(str(file_content))
        # Generic content field
        if "content" in tool_response and tool_response["content"] and not output_parts:
            output_parts.append(str(tool_response["content"]))

    # Fallback to top-level output fields
    if not output_parts:
        output_fields = ["output", "result", "response", "content", "data"]
        for field in output_fields:
            if field in payload and payload[field] and not isinstance(payload[field], dict):
                output_parts.append(str(payload[field]))
                break

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
    
    # Extract subagent name from payload for Task tool and SubagentStop events
    effective_agent_name, subagent_model = extract_subagent_name(payload, event_type, agent_name)
    effective_model = subagent_model if subagent_model else model
    
    # Extract and estimate tokens using improved extraction (fixes accuracy issue)
    input_content, output_content = extract_token_content(payload)
    tokens_in = estimate_tokens(input_content)
    tokens_out = estimate_tokens(output_content)
    
    event = {
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "agent_name": effective_agent_name,
        "session_id": get_session_id(),
        "project": get_project_name(),
        "model": effective_model,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost": estimate_cost(tokens_in, tokens_out, effective_model),
        "payload": {
            **payload,
            "git_branch": git_info["branch"],
            "git_dirty": git_info["dirty"],
            "parent_agent": agent_name if effective_agent_name != agent_name else None,
        }
    }
    
    # Remove None values from payload
    event["payload"] = {k: v for k, v in event["payload"].items() if v is not None}
    
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
    elif tool_name == "Task":
        if isinstance(tool_input, dict):
            desc = tool_input.get("description", tool_input.get("prompt", ""))[:80]
            return f"Spawned subagent: {desc}"
    
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
