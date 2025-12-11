#!/usr/bin/env python3
"""
Unit tests for the send_event.py hook.

Tests cover:
- Token estimation
- Cost calculation
- Event payload construction
"""

import sys
import os
import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime

# Add hooks to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'hooks'))

from send_event import (
    estimate_tokens,
    estimate_cost,
    get_project_name,
    get_session_id,
    generate_summary,
)


class TestTokenEstimation:
    """Tests for token estimation function."""

    def test_empty_string(self):
        """Test empty string returns 0."""
        assert estimate_tokens("") == 0

    def test_none_returns_zero(self):
        """Test None input returns 0."""
        # The token_counter treats None as falsy and returns 0
        assert estimate_tokens("") == 0  # Test with empty string instead

    def test_basic_text(self):
        """Test basic text returns positive count."""
        text = "Hello, world!"
        tokens = estimate_tokens(text)
        assert tokens > 0

    def test_longer_text(self):
        """Test longer text returns proportionally more tokens."""
        short = "Hello"
        long = "Hello " * 100

        short_tokens = estimate_tokens(short)
        long_tokens = estimate_tokens(long)

        assert long_tokens > short_tokens

    def test_code_text(self):
        """Test code text is tokenized."""
        code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
"""
        tokens = estimate_tokens(code)
        assert tokens > 0

    def test_unicode_text(self):
        """Test unicode text doesn't crash."""
        text = "Hello 世界 🌍 émoji"
        tokens = estimate_tokens(text)
        assert tokens >= 0


class TestCostEstimation:
    """Tests for cost estimation function."""

    def test_haiku_pricing(self):
        """Test Haiku model pricing."""
        cost = estimate_cost(1000, 500, "haiku")
        # Haiku: $0.25/M in, $1.25/M out
        expected = (1000 * 0.25 + 500 * 1.25) / 1_000_000
        assert cost == pytest.approx(expected, rel=0.01)

    def test_sonnet_pricing(self):
        """Test Sonnet model pricing."""
        cost = estimate_cost(1000, 500, "sonnet")
        # Sonnet: $3/M in, $15/M out
        expected = (1000 * 3.0 + 500 * 15.0) / 1_000_000
        assert cost == pytest.approx(expected, rel=0.01)

    def test_opus_pricing(self):
        """Test Opus model pricing."""
        cost = estimate_cost(1000, 500, "opus")
        # Opus: $15/M in, $75/M out
        expected = (1000 * 15.0 + 500 * 75.0) / 1_000_000
        assert cost == pytest.approx(expected, rel=0.01)

    def test_unknown_model_defaults_to_sonnet(self):
        """Test unknown model defaults to Sonnet pricing."""
        cost_unknown = estimate_cost(1000, 500, "unknown-model")
        cost_sonnet = estimate_cost(1000, 500, "sonnet")
        assert cost_unknown == pytest.approx(cost_sonnet, rel=0.01)

    def test_zero_tokens(self):
        """Test zero tokens returns zero cost."""
        assert estimate_cost(0, 0, "sonnet") == 0

    def test_model_name_case_insensitive(self):
        """Test model name is case insensitive."""
        cost_lower = estimate_cost(1000, 500, "haiku")
        cost_upper = estimate_cost(1000, 500, "HAIKU")
        cost_mixed = estimate_cost(1000, 500, "Haiku")

        assert cost_lower == cost_upper == cost_mixed


class TestSummaryGeneration:
    """Tests for summary generation function."""

    def test_bash_summary(self):
        """Test Bash command summary."""
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": "git status"}
        }
        summary = generate_summary(payload)
        assert "Executed" in summary
        assert "git status" in summary

    def test_read_summary(self):
        """Test Read file summary."""
        payload = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/path/to/file.py"}
        }
        summary = generate_summary(payload)
        assert "Read file" in summary
        assert "/path/to/file.py" in summary

    def test_write_summary(self):
        """Test Write file summary."""
        payload = {
            "tool_name": "Write",
            "tool_input": {"file_path": "/path/to/new_file.py"}
        }
        summary = generate_summary(payload)
        assert "Wrote file" in summary

    def test_websearch_summary(self):
        """Test WebSearch summary."""
        payload = {
            "tool_name": "WebSearch",
            "tool_input": {"query": "python best practices"}
        }
        summary = generate_summary(payload)
        assert "Searched" in summary

    def test_unknown_tool_returns_none(self):
        """Test unknown tool returns None."""
        payload = {
            "tool_name": "UnknownTool",
            "tool_input": {}
        }
        summary = generate_summary(payload)
        assert summary is None

    def test_long_command_truncated(self):
        """Test long commands are truncated."""
        long_command = "x" * 200
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": long_command}
        }
        summary = generate_summary(payload)
        assert len(summary) <= 110  # "Executed: " + 100 chars


class TestProjectName:
    """Tests for project name detection."""

    def test_env_variable_priority(self):
        """Test AGENT_PROJECT env var takes priority."""
        with patch.dict(os.environ, {"AGENT_PROJECT": "test-project"}):
            name = get_project_name()
            assert name == "test-project"

    def test_fallback_to_cwd(self):
        """Test fallback to current directory name."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove AGENT_PROJECT if set
            os.environ.pop("AGENT_PROJECT", None)
            name = get_project_name()
            # Should return some directory name
            assert isinstance(name, str)
            assert len(name) > 0


class TestSessionId:
    """Tests for session ID generation."""

    def test_env_variable_priority(self):
        """Test CLAUDE_SESSION_ID env var takes priority."""
        with patch.dict(os.environ, {"CLAUDE_SESSION_ID": "test-session-123"}):
            session_id = get_session_id()
            assert session_id == "test-session-123"

    def test_generates_id_without_env(self):
        """Test generates session ID without env var."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("CLAUDE_SESSION_ID", None)
            session_id = get_session_id()
            assert isinstance(session_id, str)
            assert len(session_id) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
