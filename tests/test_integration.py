#!/usr/bin/env python3
"""
Integration tests for Agent Dashboard.

These tests verify end-to-end functionality including the web server,
event handling, and API endpoints.
"""

import asyncio
import json
import socket
import time
import pytest
from pathlib import Path
from datetime import datetime


def find_free_port():
    """Find a free port for testing."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


def safe_unlink(path: Path, retries: int = 3, delay: float = 0.2):
    """Safely delete a file with retries for Windows file locking issues."""
    for i in range(retries):
        try:
            path.unlink(missing_ok=True)
            return
        except PermissionError:
            if i < retries - 1:
                time.sleep(delay)
            # On final attempt, just ignore - file will be cleaned up later
            pass


class TestWebServerBasics:
    """Basic web server tests."""

    def test_web_server_module_imports(self):
        """Web server module should import without errors."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
        from web_server import WebDashboard
        assert WebDashboard is not None

    def test_web_dashboard_initialization(self):
        """WebDashboard should initialize correctly."""
        import sys
        import tempfile
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
        from web_server import WebDashboard

        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        try:
            port = find_free_port()
            dashboard = WebDashboard(db_path=db_path, port=port)
            assert dashboard.port == port
            assert dashboard.sessions == {}
            assert dashboard.events == []
        finally:
            safe_unlink(Path(db_path))


class TestWebServerAsync:
    """Async web server tests."""

    @pytest.fixture
    def free_port(self):
        """Find a free port for testing."""
        return find_free_port()

    @pytest.mark.asyncio
    async def test_health_endpoint(self, free_port):
        """Health endpoint should return 200."""
        import sys
        import tempfile
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

        from web_server import WebDashboard
        import aiohttp
        from aiohttp import web

        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        try:
            dashboard = WebDashboard(db_path=db_path, port=free_port)
            app = dashboard.create_app()

            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, 'localhost', free_port)
            await site.start()

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"http://localhost:{free_port}/health") as resp:
                        assert resp.status == 200
                        data = await resp.json()
                        assert data["status"] == "healthy"
            finally:
                await runner.cleanup()
        finally:
            safe_unlink(Path(db_path))

    @pytest.mark.asyncio
    async def test_event_submission(self, free_port):
        """Events should be accepted and stored."""
        import sys
        import tempfile
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

        from web_server import WebDashboard
        import aiohttp
        from aiohttp import web

        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        try:
            dashboard = WebDashboard(db_path=db_path, port=free_port)
            app = dashboard.create_app()

            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, 'localhost', free_port)
            await site.start()

            try:
                async with aiohttp.ClientSession() as session:
                    # Submit event
                    event = {
                        "event_type": "Test",
                        "agent_name": "test-agent",
                        "session_id": "test-session",
                        "project": "test-project",
                        "model": "sonnet",
                        "payload": {"test": True}
                    }
                    async with session.post(
                        f"http://localhost:{free_port}/events",
                        json=event
                    ) as resp:
                        assert resp.status == 200

                    # Verify event was stored
                    async with session.get(
                        f"http://localhost:{free_port}/api/events"
                    ) as resp:
                        assert resp.status == 200
                        data = await resp.json()
                        assert "events" in data
                        assert len(data["events"]) > 0
            finally:
                await runner.cleanup()
        finally:
            safe_unlink(Path(db_path))

    @pytest.mark.asyncio
    async def test_sessions_endpoint(self, free_port):
        """Sessions endpoint should return session data."""
        import sys
        import tempfile
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

        from web_server import WebDashboard
        import aiohttp
        from aiohttp import web

        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        try:
            dashboard = WebDashboard(db_path=db_path, port=free_port)
            app = dashboard.create_app()

            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, 'localhost', free_port)
            await site.start()

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"http://localhost:{free_port}/api/sessions") as resp:
                        assert resp.status == 200
                        data = await resp.json()
                        assert "sessions" in data
            finally:
                await runner.cleanup()
        finally:
            safe_unlink(Path(db_path))

    @pytest.mark.asyncio
    async def test_stats_endpoint(self, free_port):
        """Stats endpoint should return statistics."""
        import sys
        import tempfile
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

        from web_server import WebDashboard
        import aiohttp
        from aiohttp import web

        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        try:
            dashboard = WebDashboard(db_path=db_path, port=free_port)
            app = dashboard.create_app()

            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, 'localhost', free_port)
            await site.start()

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"http://localhost:{free_port}/api/stats") as resp:
                        assert resp.status == 200
                        data = await resp.json()
                        assert "total_events" in data
                        assert "total_sessions" in data
                        assert "total_tokens" in data
                        assert "total_cost" in data
            finally:
                await runner.cleanup()
        finally:
            safe_unlink(Path(db_path))


class TestCLI:
    """CLI integration tests."""

    def test_cli_module_imports(self):
        """CLI module should import without errors."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
        from cli import main, run_doctor, show_status
        assert main is not None
        assert run_doctor is not None
        assert show_status is not None

    def test_cli_help(self):
        """CLI should display help without errors."""
        import subprocess
        result = subprocess.run(
            ["python", str(Path(__file__).parent.parent / "src" / "cli.py"), "--help"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "Agent Dashboard" in result.stdout


class TestHooks:
    """Hook integration tests."""

    def test_send_event_module_imports(self):
        """send_event module should import without errors."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))
        from send_event import send_event, estimate_tokens, estimate_cost
        assert send_event is not None
        assert estimate_tokens is not None
        assert estimate_cost is not None

    def test_token_estimation(self):
        """Token estimation should work."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))
        from send_event import estimate_tokens

        # Test basic estimation
        result = estimate_tokens("Hello, world!")
        assert result > 0
        assert isinstance(result, int)

    def test_cost_estimation(self):
        """Cost estimation should work for all models."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))
        from send_event import estimate_cost

        for model in ["haiku", "sonnet", "opus"]:
            cost = estimate_cost(1000, 500, model)
            assert cost > 0
            assert isinstance(cost, float)


class TestWorkflowEngine:
    """Workflow engine integration tests."""

    def test_workflow_engine_imports(self):
        """Workflow engine should import without errors."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
        from workflow_engine import WorkflowEngine, WorkflowPhase, TaskStatus
        assert WorkflowEngine is not None
        assert WorkflowPhase is not None
        assert TaskStatus is not None

    def test_workflow_creation(self):
        """Workflow creation should work."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
        from workflow_engine import WorkflowEngine

        engine = WorkflowEngine(budget_limit=10.0)
        workflow = engine.create_workflow_from_task("Test task")

        assert workflow is not None
        assert workflow.id in engine.workflows
        assert len(workflow.tasks) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
