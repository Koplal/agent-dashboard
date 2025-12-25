"""
Unit tests for the Progress Ledger module.

Tests task ledger data classes, operations, and runtime tracking.

Version: 2.6.0
"""

import json
import tempfile
import pytest
from datetime import datetime, timedelta
from pathlib import Path

from src.ledger.task_ledger import (
    TaskStatus,
    TaskPriority,
    ProgressEntry,
    TaskLedger,
)
from src.ledger.operations import LedgerManager
from src.ledger.runtime_tracker import RuntimeLedgerTracker, RuntimeMetrics


class TestProgressEntry:
    """Tests for ProgressEntry dataclass."""

    def test_create_progress_entry(self):
        """Test basic progress entry creation."""
        entry = ProgressEntry(
            timestamp=datetime.utcnow(),
            agent_id="test-agent",
            action_taken="Implemented feature X",
            outcome="success",
        )
        assert entry.agent_id == "test-agent"
        assert entry.outcome == "success"
        assert entry.artifacts_produced == []
        assert entry.tokens_consumed == 0

    def test_progress_entry_with_artifacts(self):
        """Test progress entry with artifacts and blockers."""
        entry = ProgressEntry(
            timestamp=datetime.utcnow(),
            agent_id="test-agent",
            action_taken="Wrote tests",
            outcome="partial",
            artifacts_produced=["tests/test_foo.py"],
            blockers_encountered=["Missing dependency"],
            next_steps=["Install dependency", "Retry tests"],
            tokens_consumed=1500,
        )
        assert len(entry.artifacts_produced) == 1
        assert len(entry.blockers_encountered) == 1
        assert entry.tokens_consumed == 1500

    def test_progress_entry_serialization(self):
        """Test to_dict and from_dict round-trip."""
        original = ProgressEntry(
            timestamp=datetime(2024, 12, 24, 12, 0, 0),
            agent_id="test-agent",
            action_taken="Test action",
            outcome="success",
            artifacts_produced=["file.py"],
            tokens_consumed=500,
        )
        data = original.to_dict()
        restored = ProgressEntry.from_dict(data)

        assert restored.agent_id == original.agent_id
        assert restored.action_taken == original.action_taken
        assert restored.tokens_consumed == original.tokens_consumed
        assert restored.artifacts_produced == original.artifacts_produced


class TestTaskLedger:
    """Tests for TaskLedger dataclass."""

    def test_create_task_ledger(self):
        """Test basic task ledger creation."""
        now = datetime.utcnow()
        task = TaskLedger(
            task_id="TEST-001",
            phase="immediate",
            category="testing",
            title="Test Task",
            objective="Test the task ledger",
            status=TaskStatus.NOT_STARTED,
            priority=TaskPriority.HIGH,
            created_at=now,
            updated_at=now,
            estimated_effort="2 hours",
        )
        assert task.task_id == "TEST-001"
        assert task.status == TaskStatus.NOT_STARTED
        assert task.priority == TaskPriority.HIGH

    def test_add_progress(self):
        """Test adding progress entries."""
        now = datetime.utcnow()
        task = TaskLedger(
            task_id="TEST-001",
            phase="immediate",
            category="testing",
            title="Test Task",
            objective="Test progress tracking",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.MEDIUM,
            created_at=now,
            updated_at=now,
            estimated_effort="1 hour",
        )

        entry = ProgressEntry(
            timestamp=datetime.utcnow(),
            agent_id="test-agent",
            action_taken="Started work",
            outcome="in_progress",
        )
        task.add_progress(entry)

        assert len(task.progress_history) == 1
        assert task.get_latest_progress() == entry

    def test_get_total_tokens(self):
        """Test token counting across progress entries."""
        now = datetime.utcnow()
        task = TaskLedger(
            task_id="TEST-001",
            phase="immediate",
            category="testing",
            title="Test Task",
            objective="Test token counting",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.MEDIUM,
            created_at=now,
            updated_at=now,
            estimated_effort="1 hour",
        )

        for i in range(3):
            entry = ProgressEntry(
                timestamp=datetime.utcnow(),
                agent_id="test-agent",
                action_taken=f"Action {i}",
                outcome="success",
                tokens_consumed=100 * (i + 1),
            )
            task.add_progress(entry)

        assert task.get_total_tokens() == 100 + 200 + 300

    def test_task_ledger_serialization(self):
        """Test to_dict and from_dict round-trip."""
        now = datetime.utcnow()
        original = TaskLedger(
            task_id="TEST-001",
            phase="immediate",
            category="testing",
            title="Test Task",
            objective="Test serialization",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            created_at=now,
            updated_at=now,
            estimated_effort="4 hours",
            dependencies=["TEST-000"],
            acceptance_criteria=["All tests pass"],
        )

        entry = ProgressEntry(
            timestamp=now,
            agent_id="test-agent",
            action_taken="Test action",
            outcome="success",
        )
        original.add_progress(entry)

        data = original.to_dict()
        restored = TaskLedger.from_dict(data)

        assert restored.task_id == original.task_id
        assert restored.status == original.status
        assert restored.priority == original.priority
        assert len(restored.progress_history) == 1
        assert restored.dependencies == ["TEST-000"]


class TestLedgerManager:
    """Tests for LedgerManager operations."""

    @pytest.fixture
    def temp_ledger(self):
        """Create a temporary ledger manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield LedgerManager(storage_path=tmpdir)

    def test_create_task(self, temp_ledger):
        """Test task creation."""
        task = temp_ledger.create_task(
            task_id="TEST-001",
            title="Test Task",
            objective="Test task creation",
            phase="immediate",
            priority=TaskPriority.HIGH,
        )
        assert task.task_id == "TEST-001"
        assert "TEST-001" in temp_ledger.tasks

    def test_create_duplicate_task_raises(self, temp_ledger):
        """Test that creating duplicate task raises error."""
        temp_ledger.create_task(
            task_id="TEST-001",
            title="Test Task",
            objective="First task",
        )
        with pytest.raises(ValueError, match="already exists"):
            temp_ledger.create_task(
                task_id="TEST-001",
                title="Duplicate",
                objective="Should fail",
            )

    def test_add_progress(self, temp_ledger):
        """Test adding progress to a task."""
        temp_ledger.create_task(
            task_id="TEST-001",
            title="Test Task",
            objective="Test progress",
        )

        entry = ProgressEntry(
            timestamp=datetime.utcnow(),
            agent_id="test-agent",
            action_taken="Made progress",
            outcome="success",
        )
        temp_ledger.add_progress("TEST-001", entry)

        task = temp_ledger.get_task("TEST-001")
        assert len(task.progress_history) == 1

    def test_add_progress_nonexistent_task(self, temp_ledger):
        """Test adding progress to nonexistent task raises error."""
        entry = ProgressEntry(
            timestamp=datetime.utcnow(),
            agent_id="test-agent",
            action_taken="Made progress",
            outcome="success",
        )
        with pytest.raises(KeyError):
            temp_ledger.add_progress("NONEXISTENT", entry)

    def test_loop_detection(self, temp_ledger):
        """Test that repetitive progress triggers loop detection."""
        temp_ledger.create_task(
            task_id="TEST-001",
            title="Test Task",
            objective="Test loop detection",
        )
        temp_ledger.update_status("TEST-001", TaskStatus.IN_PROGRESS)

        # Add 4 identical action-outcome pairs
        for _ in range(4):
            entry = ProgressEntry(
                timestamp=datetime.utcnow(),
                agent_id="test-agent",
                action_taken="Same action",
                outcome="Same outcome",
            )
            temp_ledger.add_progress("TEST-001", entry)

        task = temp_ledger.get_task("TEST-001")
        assert task.status == TaskStatus.BLOCKED
        assert "Loop detected" in task.notes

    def test_get_phase_summary(self, temp_ledger):
        """Test phase summary generation."""
        # Create tasks in different phases
        temp_ledger.create_task(
            task_id="IMMEDIATE-001",
            title="Task 1",
            objective="Test",
            phase="immediate",
        )
        temp_ledger.create_task(
            task_id="IMMEDIATE-002",
            title="Task 2",
            objective="Test",
            phase="immediate",
        )
        temp_ledger.update_status("IMMEDIATE-001", TaskStatus.IN_PROGRESS)

        summary = temp_ledger.get_phase_summary("immediate")
        assert summary["total"] == 2
        assert summary["in_progress"] == 1
        assert summary["not_started"] == 1

    def test_get_next_actionable(self, temp_ledger):
        """Test getting next actionable task."""
        # Create tasks with different priorities
        temp_ledger.create_task(
            task_id="LOW-001",
            title="Low Priority",
            objective="Test",
            priority=TaskPriority.LOW,
        )
        temp_ledger.create_task(
            task_id="HIGH-001",
            title="High Priority",
            objective="Test",
            priority=TaskPriority.HIGH,
        )

        next_task = temp_ledger.get_next_actionable()
        assert next_task.task_id == "HIGH-001"

    def test_get_next_actionable_with_dependencies(self, temp_ledger):
        """Test that tasks with unsatisfied dependencies are skipped."""
        temp_ledger.create_task(
            task_id="DEP-001",
            title="Dependency",
            objective="Must complete first",
            priority=TaskPriority.LOW,
        )
        temp_ledger.create_task(
            task_id="DEPENDENT-001",
            title="Dependent Task",
            objective="Depends on DEP-001",
            priority=TaskPriority.CRITICAL,
            dependencies=["DEP-001"],
        )

        # Dependent task has higher priority but can't be started
        next_task = temp_ledger.get_next_actionable()
        assert next_task.task_id == "DEP-001"

        # Complete dependency
        temp_ledger.complete_task("DEP-001")

        # Now dependent task is actionable
        next_task = temp_ledger.get_next_actionable()
        assert next_task.task_id == "DEPENDENT-001"

    def test_persistence(self):
        """Test that tasks persist across manager instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create and populate first manager
            manager1 = LedgerManager(storage_path=tmpdir)
            manager1.create_task(
                task_id="PERSIST-001",
                title="Persistent Task",
                objective="Test persistence",
            )
            entry = ProgressEntry(
                timestamp=datetime.utcnow(),
                agent_id="test-agent",
                action_taken="Made progress",
                outcome="success",
            )
            manager1.add_progress("PERSIST-001", entry)

            # Create new manager from same storage
            manager2 = LedgerManager(storage_path=tmpdir)

            assert "PERSIST-001" in manager2.tasks
            task = manager2.get_task("PERSIST-001")
            assert len(task.progress_history) == 1

    def test_complete_task(self, temp_ledger):
        """Test task completion."""
        temp_ledger.create_task(
            task_id="TEST-001",
            title="Test Task",
            objective="Test completion",
        )
        temp_ledger.complete_task("TEST-001", "Successfully completed")

        task = temp_ledger.get_task("TEST-001")
        assert task.status == TaskStatus.COMPLETED
        assert "Successfully completed" in task.notes


class TestRuntimeMetrics:
    """Tests for RuntimeMetrics dataclass."""

    def test_metrics_to_dict(self):
        """Test metrics serialization."""
        metrics = RuntimeMetrics(
            active_tasks=5,
            completed_tasks_last_hour=3,
            blocked_tasks=1,
            average_completion_time=timedelta(hours=2),
            loop_detections=2,
            human_escalations=1,
            total_tokens_consumed=15000,
        )
        data = metrics.to_dict()

        assert data["active_tasks"] == 5
        assert data["blocked_tasks"] == 1
        assert data["average_completion_time_seconds"] == 7200
        assert data["total_tokens_consumed"] == 15000


class TestRuntimeLedgerTracker:
    """Tests for RuntimeLedgerTracker."""

    @pytest.fixture
    def tracker_with_tasks(self):
        """Create a tracker with sample tasks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = LedgerManager(storage_path=tmpdir)

            # Create various tasks
            ledger.create_task(
                task_id="ACTIVE-001",
                title="Active Task",
                objective="Test",
                phase="immediate",
            )
            ledger.update_status("ACTIVE-001", TaskStatus.IN_PROGRESS)

            ledger.create_task(
                task_id="COMPLETED-001",
                title="Completed Task",
                objective="Test",
                phase="immediate",
            )
            ledger.complete_task("COMPLETED-001")

            ledger.create_task(
                task_id="BLOCKED-001",
                title="Blocked Task",
                objective="Test",
                phase="medium_term",
            )
            ledger.update_status("BLOCKED-001", TaskStatus.BLOCKED)

            tracker = RuntimeLedgerTracker(ledger)
            yield tracker

    def test_get_metrics(self, tracker_with_tasks):
        """Test metrics calculation."""
        metrics = tracker_with_tasks.get_metrics()

        assert metrics.active_tasks == 1
        assert metrics.blocked_tasks == 1
        assert isinstance(metrics.average_completion_time, timedelta)

    def test_generate_dashboard_data(self, tracker_with_tasks):
        """Test dashboard data generation."""
        data = tracker_with_tasks.generate_dashboard_data()

        assert "metrics" in data
        assert "by_phase" in data
        assert "recent_activity" in data
        assert "blocked_tasks" in data
        assert "generated_at" in data

        # Check phase summaries exist
        assert "immediate" in data["by_phase"]
        assert "medium_term" in data["by_phase"]

    def test_get_health_status(self, tracker_with_tasks):
        """Test health status generation."""
        health = tracker_with_tasks.get_health_status()

        assert "status" in health
        assert "warnings" in health
        assert "recommendations" in health
        assert health["status"] in ["healthy", "warning", "degraded"]

        # Should have warning about blocked task
        assert len(health["warnings"]) > 0

    def test_get_task_timeline(self, tracker_with_tasks):
        """Test task timeline generation."""
        # Add some progress
        entry = ProgressEntry(
            timestamp=datetime.utcnow(),
            agent_id="test-agent",
            action_taken="Made progress",
            outcome="success",
        )
        tracker_with_tasks.ledger.add_progress("ACTIVE-001", entry)

        timeline = tracker_with_tasks.get_task_timeline("ACTIVE-001")

        assert len(timeline) >= 2  # Created + progress
        assert timeline[0]["type"] == "created"

    def test_get_task_timeline_nonexistent(self, tracker_with_tasks):
        """Test timeline for nonexistent task returns empty."""
        timeline = tracker_with_tasks.get_task_timeline("NONEXISTENT")
        assert timeline == []


class TestTaskStatusEnum:
    """Tests for TaskStatus enum values."""

    def test_all_statuses_have_values(self):
        """Test all status values are strings."""
        for status in TaskStatus:
            assert isinstance(status.value, str)

    def test_status_values(self):
        """Test specific status values."""
        assert TaskStatus.NOT_STARTED.value == "not_started"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.BLOCKED.value == "blocked"


class TestTaskPriorityEnum:
    """Tests for TaskPriority enum values."""

    def test_priority_ordering(self):
        """Test that priority values are ordered correctly."""
        assert TaskPriority.CRITICAL.value < TaskPriority.HIGH.value
        assert TaskPriority.HIGH.value < TaskPriority.MEDIUM.value
        assert TaskPriority.MEDIUM.value < TaskPriority.LOW.value

    def test_priority_sorting(self):
        """Test that priorities sort correctly."""
        priorities = [
            TaskPriority.LOW,
            TaskPriority.CRITICAL,
            TaskPriority.MEDIUM,
            TaskPriority.HIGH,
        ]
        sorted_priorities = sorted(priorities, key=lambda p: p.value)
        assert sorted_priorities == [
            TaskPriority.CRITICAL,
            TaskPriority.HIGH,
            TaskPriority.MEDIUM,
            TaskPriority.LOW,
        ]
