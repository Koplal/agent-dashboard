#!/usr/bin/env python3
"""test_cli.py - CLI integration tests for Agent Dashboard.

Tests critical CLI paths:
- Status check when not installed
- Test event when server unavailable
- Recent events with empty/populated database

Version: 2.5.2
"""

import sys
import tempfile
import subprocess
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

class TestCLIModule:
    """Tests for CLI module imports and basic functionality."""

    def test_cli_module_imports(self):
        """CLI module should import without errors."""
        from cli import main, run_doctor, show_status, send_test_event
        assert main is not None
        assert run_doctor is not None
        assert show_status is not None
        assert send_test_event is not None

    def test_cli_help_output(self):
        """CLI help should display without errors."""
        cli_path = Path(__file__).parent.parent / "src" / "cli.py"
        result = subprocess.run(
            [sys.executable, str(cli_path), "--help"],
            capture_output=True, text=True
        )
        assert result.returncode == 0
        assert "Agent Dashboard" in result.stdout

class TestStatusCommand:
    """Tests for the status command."""

    def test_status_when_not_installed(self):
        """Status should handle missing installation gracefully."""
        from cli import show_status
        from argparse import Namespace
        args = Namespace(port=4200)
        # Should not raise, returns 0
        result = show_status(args)
        assert result == 0

    def test_status_shows_components(self, capsys):
        """Status should display component information."""
        from cli import show_status
        from argparse import Namespace
        args = Namespace(port=4200)
        show_status(args)
        captured = capsys.readouterr()
        assert "Agent Dashboard Status" in captured.out
        assert "Components" in captured.out

class TestTestEventCommand:
    """Tests for the test event command."""

    def test_event_when_server_unavailable(self, capsys):
        """Test event should handle unavailable server gracefully."""
        from cli import send_test_event
        from argparse import Namespace
        # Use a port unlikely to be in use
        args = Namespace(
            port=59999,
            event_type="PreToolUse",
            agent_name="test-agent",
            session_id="test-session",
            project="test-project",
            model="sonnet"
        )
        result = send_test_event(args)
        # Should return error code 1 when server unavailable
        assert result == 1
        captured = capsys.readouterr()
        assert "Could not connect" in captured.out

class TestLogsCommand:
    """Tests for the logs command."""

    def test_logs_with_empty_database(self, capsys, tmp_path):
        """Logs should handle empty database gracefully."""
        from cli import show_recent_events_from_db
        import sqlite3
        # Create empty database
        db_path = tmp_path / "test.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE events (
                    id INTEGER PRIMARY KEY,
                    timestamp TEXT,
                    agent_name TEXT,
                    event_type TEXT,
                    project TEXT
                )
            """)
        show_recent_events_from_db(db_path, 10)
        captured = capsys.readouterr()
        assert "No events" in captured.out

    def test_logs_with_populated_database(self, capsys, tmp_path):
        """Logs should display events from populated database."""
        from cli import show_recent_events_from_db
        import sqlite3
        from datetime import datetime
        # Create and populate database
        db_path = tmp_path / "test.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE events (
                    id INTEGER PRIMARY KEY,
                    timestamp TEXT,
                    agent_name TEXT,
                    event_type TEXT,
                    project TEXT
                )
            """)
            conn.execute(
                "INSERT INTO events (timestamp, agent_name, event_type, project) VALUES (?, ?, ?, ?)",
                (datetime.now().isoformat(), "test-agent", "PreToolUse", "test-project")
            )
        show_recent_events_from_db(db_path, 10)
        captured = capsys.readouterr()
        assert "test-agent" in captured.out
        assert "test-project" in captured.out

class TestDoctorCommand:
    """Tests for the doctor command."""

    def test_doctor_runs_without_error(self, capsys):
        """Doctor should complete without raising exceptions."""
        from cli import run_doctor
        from argparse import Namespace
        args = Namespace(port=4200)
        # Should run without error (may return non-zero for issues)
        result = run_doctor(args)
        assert isinstance(result, int)
        captured = capsys.readouterr()
        assert "Agent Dashboard Doctor" in captured.out

    def test_doctor_checks_python_version(self, capsys):
        """Doctor should check Python version."""
        from cli import run_doctor
        from argparse import Namespace
        args = Namespace(port=4200)
        run_doctor(args)
        captured = capsys.readouterr()
        assert "Python" in captured.out

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
