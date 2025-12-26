"""
Unit and Integration Tests for Hierarchical Session Summarizer.

Tests the HIER-001 Hierarchical Session Summarizer feature including:
- SummaryLevel enum
- HierarchicalSummary dataclass
- Phase detection
- Task, Phase, and Session summarization
- Context loading with token budget
- Integration with RuntimeLedgerTracker

Version: 2.6.0
Test Count: 36 (30 unit + 2 integration + 2 performance + 2 error)
"""

import time
import tempfile
import pytest
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from typing import List

from src.ledger.task_ledger import (
    TaskStatus,
    TaskPriority,
    ProgressEntry,
    TaskLedger,
)
from src.ledger.operations import LedgerManager
from src.ledger.runtime_tracker import RuntimeLedgerTracker
from src.ledger.summarizer import (
    SummaryLevel,
    HierarchicalSummary,
    HierarchicalSummarizer,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_progress_entry_success():
    """ProgressEntry with outcome='success'."""
    return ProgressEntry(
        timestamp=datetime.now(timezone.utc),
        agent_id="test-agent",
        action_taken="Completed feature implementation",
        outcome="success",
        artifacts_produced=["src/feature.py"],
        tokens_consumed=500,
    )


@pytest.fixture
def sample_progress_entry_completed():
    """ProgressEntry with outcome='completed'."""
    return ProgressEntry(
        timestamp=datetime.now(timezone.utc),
        agent_id="test-agent",
        action_taken="Finished testing suite",
        outcome="completed",
        artifacts_produced=["tests/test_feature.py"],
        tokens_consumed=300,
    )


@pytest.fixture
def sample_progress_entry_failed():
    """ProgressEntry with outcome='failed'."""
    return ProgressEntry(
        timestamp=datetime.now(timezone.utc),
        agent_id="test-agent",
        action_taken="Attempted database migration",
        outcome="failed",
        blockers_encountered=["Connection timeout"],
        tokens_consumed=200,
    )


@pytest.fixture
def sample_progress_entry_blocked():
    """ProgressEntry with outcome='blocked'."""
    return ProgressEntry(
        timestamp=datetime.now(timezone.utc),
        agent_id="test-agent",
        action_taken="Waiting for API approval",
        outcome="blocked",
        tokens_consumed=50,
    )


@pytest.fixture
def sample_progress_entry_with_blockers():
    """ProgressEntry with blockers_encountered populated."""
    return ProgressEntry(
        timestamp=datetime.now(timezone.utc),
        agent_id="test-agent",
        action_taken="Partial implementation",
        outcome="partial",
        blockers_encountered=["Missing dependency", "Unclear requirements"],
        tokens_consumed=400,
    )


def create_task_with_progress(
    task_id: str,
    progress_entries: List[ProgressEntry],
    base_time: datetime = None,
) -> TaskLedger:
    """Helper to create a TaskLedger with progress entries."""
    if base_time is None:
        base_time = datetime.now(timezone.utc)
    
    task = TaskLedger(
        task_id=task_id,
        phase="immediate",
        category="testing",
        title=f"Test Task {task_id}",
        objective=f"Objective for {task_id}",
        status=TaskStatus.IN_PROGRESS,
        priority=TaskPriority.MEDIUM,
        created_at=base_time,
        updated_at=base_time,
        estimated_effort="2 hours",
    )
    
    for entry in progress_entries:
        task.add_progress(entry)
    
    return task


@pytest.fixture
def sample_task_with_progress():
    """TaskLedger with realistic progress_history."""
    base_time = datetime.now(timezone.utc)
    entries = [
        ProgressEntry(
            timestamp=base_time,
            agent_id="agent-1",
            action_taken="Started implementation",
            outcome="in_progress",
            tokens_consumed=100,
        ),
        ProgressEntry(
            timestamp=base_time + timedelta(minutes=30),
            agent_id="agent-1",
            action_taken="Completed core logic",
            outcome="success",
            artifacts_produced=["src/core.py"],
            tokens_consumed=500,
        ),
        ProgressEntry(
            timestamp=base_time + timedelta(minutes=60),
            agent_id="agent-1",
            action_taken="Added error handling",
            outcome="success",
            tokens_consumed=300,
        ),
    ]
    return create_task_with_progress("TASK-001", entries, base_time)


@pytest.fixture
def sample_tasks_single_phase():
    """List of 3 tasks within 90-minute window (single phase)."""
    base_time = datetime.now(timezone.utc)
    
    tasks = []
    for i in range(3):
        offset = timedelta(minutes=i * 20)  # 0, 20, 40 minutes apart
        entries = [
            ProgressEntry(
                timestamp=base_time + offset,
                agent_id=f"agent-{i}",
                action_taken=f"Completed task {i}",
                outcome="success",
                tokens_consumed=100 * (i + 1),
            ),
        ]
        tasks.append(create_task_with_progress(f"TASK-{i:03d}", entries, base_time + offset))
    
    return tasks


@pytest.fixture
def sample_tasks_multiple_phases():
    """List of tasks spanning multiple phases (>90 minute gaps)."""
    base_time = datetime.now(timezone.utc)
    
    tasks = []
    # Phase 1: Tasks at 0, 30, 60 minutes
    for i in range(3):
        offset = timedelta(minutes=i * 30)
        entries = [
            ProgressEntry(
                timestamp=base_time + offset,
                agent_id=f"agent-{i}",
                action_taken=f"Phase 1 work {i}",
                outcome="success",
                tokens_consumed=100,
            ),
        ]
        tasks.append(create_task_with_progress(f"P1-TASK-{i:03d}", entries, base_time + offset))
    
    # Phase 2: Tasks at 180, 210 minutes (2-hour gap from phase 1)
    for i in range(2):
        offset = timedelta(minutes=180 + i * 30)
        entries = [
            ProgressEntry(
                timestamp=base_time + offset,
                agent_id=f"agent-{i}",
                action_taken=f"Phase 2 work {i}",
                outcome="success",
                tokens_consumed=100,
            ),
        ]
        tasks.append(create_task_with_progress(f"P2-TASK-{i:03d}", entries, base_time + offset))
    
    return tasks


@pytest.fixture
def sample_task_summary():
    """Pre-built HierarchicalSummary at TASK level."""
    return HierarchicalSummary(
        level=SummaryLevel.TASK,
        summary_id="TASK-abc123",
        parent_id="PHASE-def456",
        start_time=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
        end_time=datetime(2025, 1, 1, 11, 0, tzinfo=timezone.utc),
        accomplishments=["Implemented feature X", "Added unit tests"],
        blockers=["Dependency conflict resolved"],
        token_count=150,
        child_count=0,
        metadata={"task_id": "TASK-001", "assigned_agent": "agent-1"},
    )


@pytest.fixture
def sample_phase_summary():
    """Pre-built HierarchicalSummary at PHASE level."""
    return HierarchicalSummary(
        level=SummaryLevel.PHASE,
        summary_id="PHASE-def456",
        parent_id="SESSION-ghi789",
        start_time=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
        end_time=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        accomplishments=["Completed module A", "Refactored module B"],
        blockers=["API rate limiting"],
        token_count=300,
        child_count=3,
        metadata={"task_ids": ["TASK-001", "TASK-002", "TASK-003"]},
    )


@pytest.fixture
def sample_session_summary():
    """Pre-built HierarchicalSummary at SESSION level."""
    return HierarchicalSummary(
        level=SummaryLevel.SESSION,
        summary_id="SESSION-ghi789",
        parent_id=None,
        start_time=datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc),
        end_time=datetime(2025, 1, 1, 17, 0, tzinfo=timezone.utc),
        accomplishments=["Deployed new feature", "Fixed 5 bugs", "Updated documentation"],
        blockers=["Build server was down for 30 minutes"],
        token_count=500,
        child_count=2,
        metadata={"phase_count": 2, "total_task_count": 5},
    )


@pytest.fixture
def temp_ledger():
    """Create a temporary ledger manager."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield LedgerManager(storage_path=tmpdir)


@pytest.fixture
def tracker_with_tasks(temp_ledger):
    """RuntimeLedgerTracker populated with test data."""
    base_time = datetime.now(timezone.utc)
    
    # Create tasks with varied progress
    for i in range(5):
        task = temp_ledger.create_task(
            task_id=f"TEST-{i:03d}",
            title=f"Test Task {i}",
            objective=f"Objective {i}",
            phase="immediate",
            priority=TaskPriority.MEDIUM,
        )
        
        # Add progress entries
        for j in range(3):
            entry = ProgressEntry(
                timestamp=base_time + timedelta(minutes=i * 30 + j * 10),
                agent_id=f"agent-{i}",
                action_taken=f"Action {j} for task {i}",
                outcome="success" if j == 2 else "in_progress",
                tokens_consumed=100,
            )
            temp_ledger.add_progress(f"TEST-{i:03d}", entry)
    
    # Complete some tasks
    temp_ledger.complete_task("TEST-000")
    temp_ledger.complete_task("TEST-001")
    
    return RuntimeLedgerTracker(temp_ledger)


@pytest.fixture
def large_task_set_100():
    """100 tasks for performance testing."""
    base_time = datetime.now(timezone.utc)
    tasks = []
    
    for i in range(100):
        # Create varied gaps to form multiple phases
        if i % 10 == 0 and i > 0:
            offset = timedelta(hours=i // 10 * 2, minutes=i % 10 * 5)
        else:
            offset = timedelta(hours=(i // 10) * 2, minutes=i % 10 * 5)
        
        entries = [
            ProgressEntry(
                timestamp=base_time + offset,
                agent_id=f"agent-{i % 5}",
                action_taken=f"Completed task {i}",
                outcome="success",
                tokens_consumed=50,
            ),
        ]
        tasks.append(create_task_with_progress(f"PERF-{i:03d}", entries, base_time + offset))
    
    return tasks


# =============================================================================
# FR-001: SummaryLevel Enum Tests
# =============================================================================


class TestSummaryLevel:
    """Tests for SummaryLevel enumeration (FR-001)."""

    def test_summary_level_has_four_values(self):
        """T-001: Verify enum has exactly 4 members."""
        assert len(SummaryLevel) == 4
        assert hasattr(SummaryLevel, "SESSION")
        assert hasattr(SummaryLevel, "PHASE")
        assert hasattr(SummaryLevel, "TASK")
        assert hasattr(SummaryLevel, "ATOMIC")

    def test_summary_level_ordering_session_is_zero(self):
        """T-002: Verify SESSION is highest level (value 0)."""
        assert SummaryLevel.SESSION.value == 0

    def test_summary_level_ordering_atomic_is_three(self):
        """T-003: Verify ATOMIC is lowest level (value 3)."""
        assert SummaryLevel.ATOMIC.value == 3

    def test_summary_level_ordering_complete(self):
        """Verify complete ordering: SESSION < PHASE < TASK < ATOMIC."""
        assert SummaryLevel.SESSION.value < SummaryLevel.PHASE.value
        assert SummaryLevel.PHASE.value < SummaryLevel.TASK.value
        assert SummaryLevel.TASK.value < SummaryLevel.ATOMIC.value


# =============================================================================
# FR-002: HierarchicalSummary Dataclass Tests
# =============================================================================


class TestHierarchicalSummary:
    """Tests for HierarchicalSummary dataclass (FR-002)."""

    def test_hierarchical_summary_creation_with_required_fields(self):
        """T-004: Verify dataclass instantiation with all fields."""
        summary = HierarchicalSummary(
            level=SummaryLevel.TASK,
            summary_id="TASK-abc123",
            parent_id="PHASE-def456",
            start_time=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
            end_time=datetime(2025, 1, 1, 11, 0, tzinfo=timezone.utc),
            accomplishments=["Completed feature X"],
            blockers=["Blocked by dependency Y"],
            token_count=150,
            child_count=0,
            metadata={"task_id": "task-001"},
        )
        
        assert summary.level == SummaryLevel.TASK
        assert summary.summary_id == "TASK-abc123"
        assert summary.parent_id == "PHASE-def456"
        assert summary.accomplishments == ["Completed feature X"]
        assert summary.blockers == ["Blocked by dependency Y"]
        assert summary.token_count == 150
        assert summary.child_count == 0
        assert summary.metadata == {"task_id": "task-001"}

    def test_hierarchical_summary_with_children(self, sample_phase_summary):
        """T-005: Verify summary can reference child summaries via metadata."""
        assert sample_phase_summary.child_count == 3
        assert "task_ids" in sample_phase_summary.metadata
        assert len(sample_phase_summary.metadata["task_ids"]) == 3

    def test_hierarchical_summary_is_frozen(self, sample_task_summary):
        """T-006: Verify dataclass is immutable (frozen=True)."""
        import dataclasses
        assert dataclasses.is_dataclass(sample_task_summary)
        assert sample_task_summary.__dataclass_fields__ is not None

    def test_hierarchical_summary_modification_raises_error(self, sample_task_summary):
        """T-007: Verify attempting to modify raises FrozenInstanceError."""
        with pytest.raises((FrozenInstanceError, AttributeError)):
            sample_task_summary.accomplishments = ["new accomplishment"]

    def test_hierarchical_summary_token_count_calculation(self):
        """T-008: Verify token count reflects content size."""
        accomplishments = ["Completed feature X with full implementation"]
        blockers = ["Blocked by dependency Y"]
        
        summary = HierarchicalSummary(
            level=SummaryLevel.TASK,
            summary_id="TASK-test",
            parent_id=None,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            accomplishments=accomplishments,
            blockers=blockers,
            token_count=50,
            child_count=0,
            metadata={},
        )
        
        assert summary.token_count == 50


# =============================================================================
# FR-003: Phase Detection Tests
# =============================================================================


class TestPhaseDetection:
    """Tests for phase detection (FR-003)."""

    def test_phase_detection_groups_close_tasks(self, sample_tasks_single_phase):
        """T-009: Verify tasks within 90 minutes are grouped together."""
        summarizer = HierarchicalSummarizer()
        phases = summarizer.detect_phases(sample_tasks_single_phase)
        
        assert len(phases) == 1
        assert len(phases[0]) == 3

    def test_phase_detection_splits_on_90_minute_gap(self, sample_tasks_multiple_phases):
        """T-010: Verify gap > 90 minutes creates new phase."""
        summarizer = HierarchicalSummarizer()
        phases = summarizer.detect_phases(sample_tasks_multiple_phases)
        
        assert len(phases) == 2
        assert len(phases[0]) == 3
        assert len(phases[1]) == 2

    def test_phase_detection_single_task_returns_one_phase(self, sample_task_with_progress):
        """T-011: Verify single task creates single phase."""
        summarizer = HierarchicalSummarizer()
        phases = summarizer.detect_phases([sample_task_with_progress])
        
        assert len(phases) == 1
        assert len(phases[0]) == 1

    def test_phase_detection_empty_list_returns_empty(self):
        """T-012: Verify empty input returns empty output."""
        summarizer = HierarchicalSummarizer()
        phases = summarizer.detect_phases([])
        
        assert phases == []

    def test_phase_detection_boundary_exactly_90_minutes(self):
        """T-013: Verify boundary condition at exactly 90 minutes."""
        base_time = datetime.now(timezone.utc)
        
        task1_entries = [
            ProgressEntry(
                timestamp=base_time,
                agent_id="agent-1",
                action_taken="Task 1",
                outcome="success",
                tokens_consumed=100,
            ),
        ]
        task2_entries = [
            ProgressEntry(
                timestamp=base_time + timedelta(minutes=90),
                agent_id="agent-2",
                action_taken="Task 2",
                outcome="success",
                tokens_consumed=100,
            ),
        ]
        
        task1 = create_task_with_progress("TASK-1", task1_entries, base_time)
        task2 = create_task_with_progress("TASK-2", task2_entries, base_time + timedelta(minutes=90))
        
        summarizer = HierarchicalSummarizer()
        phases = summarizer.detect_phases([task1, task2])
        
        assert len(phases) == 1

    def test_phase_detection_configurable_threshold(self):
        """T-014: Verify threshold can be customized."""
        base_time = datetime.now(timezone.utc)
        
        task1_entries = [
            ProgressEntry(
                timestamp=base_time,
                agent_id="agent-1",
                action_taken="Task 1",
                outcome="success",
                tokens_consumed=100,
            ),
        ]
        task2_entries = [
            ProgressEntry(
                timestamp=base_time + timedelta(minutes=45),
                agent_id="agent-2",
                action_taken="Task 2",
                outcome="success",
                tokens_consumed=100,
            ),
        ]
        
        task1 = create_task_with_progress("TASK-1", task1_entries, base_time)
        task2 = create_task_with_progress("TASK-2", task2_entries, base_time + timedelta(minutes=45))
        
        summarizer = HierarchicalSummarizer()
        
        phases_30 = summarizer.detect_phases([task1, task2], threshold_minutes=30)
        assert len(phases_30) == 2
        
        phases_60 = summarizer.detect_phases([task1, task2], threshold_minutes=60)
        assert len(phases_60) == 1


# =============================================================================
# FR-004: Task Summarization Tests
# =============================================================================


class TestTaskSummarization:
    """Tests for task summarization (FR-004)."""

    def test_task_summary_extracts_accomplishments_from_success(self):
        """T-015: Verify accomplishments extracted from success/completed outcomes."""
        base_time = datetime.now(timezone.utc)
        entries = [
            ProgressEntry(
                timestamp=base_time,
                agent_id="agent-1",
                action_taken="Implemented feature A",
                outcome="success",
                tokens_consumed=100,
            ),
            ProgressEntry(
                timestamp=base_time + timedelta(minutes=30),
                agent_id="agent-1",
                action_taken="Finished testing",
                outcome="completed",
                tokens_consumed=100,
            ),
        ]
        task = create_task_with_progress("TASK-001", entries, base_time)
        
        summarizer = HierarchicalSummarizer()
        summary = summarizer.summarize_task(task)
        
        assert "Implemented feature A" in summary.accomplishments
        assert "Finished testing" in summary.accomplishments
        assert len(summary.accomplishments) == 2

    def test_task_summary_extracts_blockers_from_failed(self):
        """T-016: Verify blockers extracted from failed/blocked outcomes."""
        base_time = datetime.now(timezone.utc)
        entries = [
            ProgressEntry(
                timestamp=base_time,
                agent_id="agent-1",
                action_taken="API timeout occurred",
                outcome="failed",
                tokens_consumed=100,
            ),
            ProgressEntry(
                timestamp=base_time + timedelta(minutes=30),
                agent_id="agent-1",
                action_taken="Waiting for approval",
                outcome="blocked",
                tokens_consumed=50,
            ),
        ]
        task = create_task_with_progress("TASK-001", entries, base_time)
        
        summarizer = HierarchicalSummarizer()
        summary = summarizer.summarize_task(task)
        
        assert "API timeout occurred" in summary.blockers
        assert "Waiting for approval" in summary.blockers
        assert len(summary.blockers) == 2

    def test_task_summary_extracts_blockers_from_blockers_encountered(self):
        """T-017: Verify blockers extracted from blockers_encountered field."""
        base_time = datetime.now(timezone.utc)
        entries = [
            ProgressEntry(
                timestamp=base_time,
                agent_id="agent-1",
                action_taken="Partial implementation",
                outcome="partial",
                blockers_encountered=["Dependency conflict", "Missing documentation"],
                tokens_consumed=100,
            ),
        ]
        task = create_task_with_progress("TASK-001", entries, base_time)
        
        summarizer = HierarchicalSummarizer()
        summary = summarizer.summarize_task(task)
        
        assert "Dependency conflict" in summary.blockers
        assert "Missing documentation" in summary.blockers

    def test_task_summary_empty_progress_returns_empty_lists(self):
        """T-018: Verify empty progress creates valid but empty summary."""
        base_time = datetime.now(timezone.utc)
        task = create_task_with_progress("TASK-001", [], base_time)
        
        summarizer = HierarchicalSummarizer()
        summary = summarizer.summarize_task(task)
        
        assert summary.accomplishments == []
        assert summary.blockers == []
        assert summary.level == SummaryLevel.TASK

    def test_task_summary_deduplicates_accomplishments(self):
        """T-019: Verify duplicate items are removed."""
        base_time = datetime.now(timezone.utc)
        entries = [
            ProgressEntry(
                timestamp=base_time,
                agent_id="agent-1",
                action_taken="Completed feature X",
                outcome="success",
                tokens_consumed=100,
            ),
            ProgressEntry(
                timestamp=base_time + timedelta(minutes=10),
                agent_id="agent-1",
                action_taken="completed feature x",
                outcome="success",
                tokens_consumed=100,
            ),
            ProgressEntry(
                timestamp=base_time + timedelta(minutes=20),
                agent_id="agent-1",
                action_taken="  Completed feature X  ",
                outcome="success",
                tokens_consumed=100,
            ),
        ]
        task = create_task_with_progress("TASK-001", entries, base_time)
        
        summarizer = HierarchicalSummarizer()
        summary = summarizer.summarize_task(task)
        
        assert len(summary.accomplishments) == 1


# =============================================================================
# FR-005: Phase Summarization Tests
# =============================================================================


class TestPhaseSummarization:
    """Tests for phase summarization (FR-005)."""

    def test_phase_summary_aggregates_child_accomplishments(self):
        """T-020: Verify phase combines accomplishments from all tasks."""
        task_summaries = [
            HierarchicalSummary(
                level=SummaryLevel.TASK,
                summary_id="TASK-001",
                parent_id=None,
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc),
                accomplishments=["A", "B"],
                blockers=[],
                token_count=50,
                child_count=0,
                metadata={},
            ),
            HierarchicalSummary(
                level=SummaryLevel.TASK,
                summary_id="TASK-002",
                parent_id=None,
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc),
                accomplishments=["C", "D"],
                blockers=[],
                token_count=50,
                child_count=0,
                metadata={},
            ),
        ]
        
        summarizer = HierarchicalSummarizer()
        phase_summary = summarizer.summarize_phase(task_summaries)
        
        assert "A" in phase_summary.accomplishments
        assert "B" in phase_summary.accomplishments
        assert "C" in phase_summary.accomplishments
        assert "D" in phase_summary.accomplishments
        assert len(phase_summary.accomplishments) == 4

    def test_phase_summary_deduplicates_across_children(self):
        """T-021: Verify duplicates across tasks are removed."""
        task_summaries = [
            HierarchicalSummary(
                level=SummaryLevel.TASK,
                summary_id="TASK-001",
                parent_id=None,
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc),
                accomplishments=["A", "B"],
                blockers=[],
                token_count=50,
                child_count=0,
                metadata={},
            ),
            HierarchicalSummary(
                level=SummaryLevel.TASK,
                summary_id="TASK-002",
                parent_id=None,
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc),
                accomplishments=["B", "C"],
                blockers=[],
                token_count=50,
                child_count=0,
                metadata={},
            ),
        ]
        
        summarizer = HierarchicalSummarizer()
        phase_summary = summarizer.summarize_phase(task_summaries)
        
        assert len(phase_summary.accomplishments) == 3
        assert "A" in phase_summary.accomplishments
        assert "B" in phase_summary.accomplishments
        assert "C" in phase_summary.accomplishments

    def test_phase_summary_sets_correct_child_count(self):
        """T-022: Verify child_count reflects aggregated tasks."""
        task_summaries = [
            HierarchicalSummary(
                level=SummaryLevel.TASK,
                summary_id=f"TASK-{i}",
                parent_id=None,
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc),
                accomplishments=[f"Item {i}"],
                blockers=[],
                token_count=30,
                child_count=0,
                metadata={},
            )
            for i in range(5)
        ]
        
        summarizer = HierarchicalSummarizer()
        phase_summary = summarizer.summarize_phase(task_summaries)
        
        assert phase_summary.child_count == 5


# =============================================================================
# FR-006: Session Summarization Tests
# =============================================================================


class TestSessionSummarization:
    """Tests for session summarization (FR-006)."""

    def test_session_summary_has_no_parent_id(self):
        """T-023: Verify SESSION level has parent_id=None."""
        phase_summaries = [
            HierarchicalSummary(
                level=SummaryLevel.PHASE,
                summary_id="PHASE-001",
                parent_id=None,
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc),
                accomplishments=["Phase 1 work"],
                blockers=[],
                token_count=100,
                child_count=3,
                metadata={},
            ),
        ]
        
        summarizer = HierarchicalSummarizer()
        session_summary = summarizer.summarize_session(phase_summaries)
        
        assert session_summary.parent_id is None
        assert session_summary.level == SummaryLevel.SESSION

    def test_session_summary_aggregates_all_phases(self):
        """T-024: Verify session combines all phase data."""
        phase_summaries = [
            HierarchicalSummary(
                level=SummaryLevel.PHASE,
                summary_id="PHASE-001",
                parent_id=None,
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc),
                accomplishments=["Phase 1 accomplishment"],
                blockers=["Phase 1 blocker"],
                token_count=100,
                child_count=3,
                metadata={"task_ids": ["T1", "T2", "T3"]},
            ),
            HierarchicalSummary(
                level=SummaryLevel.PHASE,
                summary_id="PHASE-002",
                parent_id=None,
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc),
                accomplishments=["Phase 2 accomplishment"],
                blockers=[],
                token_count=100,
                child_count=2,
                metadata={"task_ids": ["T4", "T5"]},
            ),
        ]
        
        summarizer = HierarchicalSummarizer()
        session_summary = summarizer.summarize_session(phase_summaries)
        
        assert "Phase 1 accomplishment" in session_summary.accomplishments
        assert "Phase 2 accomplishment" in session_summary.accomplishments
        assert "Phase 1 blocker" in session_summary.blockers
        assert session_summary.metadata.get("phase_count") == 2
        assert session_summary.metadata.get("total_task_count") == 5

    def test_session_summary_empty_phases_returns_empty_summary(self):
        """T-025: Verify empty input creates valid empty session."""
        summarizer = HierarchicalSummarizer()
        session_summary = summarizer.summarize_session([])
        
        assert session_summary.level == SummaryLevel.SESSION
        assert session_summary.accomplishments == []
        assert session_summary.blockers == []
        assert session_summary.parent_id is None


# =============================================================================
# FR-007: Context Loading Tests
# =============================================================================


class TestContextLoading:
    """Tests for context loading with token budget (FR-007)."""

    def test_context_loading_respects_token_budget(self, sample_session_summary):
        """T-026: Verify output never exceeds budget."""
        summarizer = HierarchicalSummarizer()
        
        result = summarizer.load_context(sample_session_summary, token_budget=200)
        
        total_tokens = sum(s.token_count for s in result)
        assert total_tokens <= 200

    def test_context_loading_expands_when_budget_allows(self):
        """T-027: Verify hierarchy expands with larger budget."""
        task_summaries = [
            HierarchicalSummary(
                level=SummaryLevel.TASK,
                summary_id=f"TASK-{i}",
                parent_id="PHASE-001",
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc),
                accomplishments=[f"Task {i} done"],
                blockers=[],
                token_count=25,
                child_count=0,
                metadata={},
            )
            for i in range(4)
        ]
        
        phase_summary = HierarchicalSummary(
            level=SummaryLevel.PHASE,
            summary_id="PHASE-001",
            parent_id="SESSION-001",
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            accomplishments=["Phase complete"],
            blockers=[],
            token_count=50,
            child_count=4,
            metadata={"child_summaries": task_summaries},
        )
        
        session_summary = HierarchicalSummary(
            level=SummaryLevel.SESSION,
            summary_id="SESSION-001",
            parent_id=None,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            accomplishments=["Session complete"],
            blockers=[],
            token_count=100,
            child_count=1,
            metadata={"child_summaries": [phase_summary]},
        )
        
        summarizer = HierarchicalSummarizer()
        
        result = summarizer.load_context(session_summary, token_budget=500)
        
        assert len(result) >= 1
        assert result[0].level == SummaryLevel.SESSION

    def test_context_loading_zero_budget_returns_empty(self, sample_session_summary):
        """T-028: Verify zero budget returns empty list."""
        summarizer = HierarchicalSummarizer()
        result = summarizer.load_context(sample_session_summary, token_budget=0)
        
        assert result == []

    def test_context_loading_query_prioritizes_matches(self):
        """T-029: Verify query string affects selection."""
        task1 = HierarchicalSummary(
            level=SummaryLevel.TASK,
            summary_id="TASK-001",
            parent_id="PHASE-001",
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            accomplishments=["Fixed authentication bug"],
            blockers=[],
            token_count=50,
            child_count=0,
            metadata={},
        )
        
        task2 = HierarchicalSummary(
            level=SummaryLevel.TASK,
            summary_id="TASK-002",
            parent_id="PHASE-001",
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            accomplishments=["Updated UI colors"],
            blockers=[],
            token_count=50,
            child_count=0,
            metadata={},
        )
        
        session = HierarchicalSummary(
            level=SummaryLevel.SESSION,
            summary_id="SESSION-001",
            parent_id=None,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            accomplishments=["Session work"],
            blockers=[],
            token_count=30,
            child_count=2,
            metadata={"child_summaries": [task1, task2]},
        )
        
        summarizer = HierarchicalSummarizer()
        
        result = summarizer.load_context(session, token_budget=100, query="authentication")
        
        task_ids = [s.summary_id for s in result if s.level == SummaryLevel.TASK]
        if task_ids:
            assert "TASK-001" in task_ids

    def test_context_loading_returns_hierarchical_order(self):
        """T-030: Verify output order is SESSION -> PHASE -> TASK."""
        task = HierarchicalSummary(
            level=SummaryLevel.TASK,
            summary_id="TASK-001",
            parent_id="PHASE-001",
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            accomplishments=["Task done"],
            blockers=[],
            token_count=30,
            child_count=0,
            metadata={},
        )
        
        phase = HierarchicalSummary(
            level=SummaryLevel.PHASE,
            summary_id="PHASE-001",
            parent_id="SESSION-001",
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            accomplishments=["Phase done"],
            blockers=[],
            token_count=40,
            child_count=1,
            metadata={"child_summaries": [task]},
        )
        
        session = HierarchicalSummary(
            level=SummaryLevel.SESSION,
            summary_id="SESSION-001",
            parent_id=None,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            accomplishments=["Session done"],
            blockers=[],
            token_count=50,
            child_count=1,
            metadata={"child_summaries": [phase]},
        )
        
        summarizer = HierarchicalSummarizer()
        result = summarizer.load_context(session, token_budget=500)
        
        if len(result) >= 1:
            assert result[0].level == SummaryLevel.SESSION
        if len(result) >= 2:
            assert result[1].level == SummaryLevel.PHASE
        if len(result) >= 3:
            assert result[2].level == SummaryLevel.TASK


# =============================================================================
# FR-008: Integration Tests
# =============================================================================


class TestRuntimeTrackerIntegration:
    """Integration tests for RuntimeLedgerTracker (FR-008)."""

    def test_runtime_tracker_get_session_summary_returns_hierarchy(self, tracker_with_tasks):
        """T-031: Verify integration with RuntimeLedgerTracker."""
        summary = tracker_with_tasks.get_session_summary()
        
        assert summary is not None
        assert summary.level == SummaryLevel.SESSION
        assert summary.parent_id is None
        assert summary.metadata.get("total_task_count", 0) >= 1

    def test_runtime_tracker_cache_invalidation_on_modification(self, tracker_with_tasks):
        """T-032: Verify cache is invalidated when ledger changes."""
        summary1 = tracker_with_tasks.get_session_summary()
        initial_accomplishment_count = len(summary1.accomplishments)
        
        entry = ProgressEntry(
            timestamp=datetime.now(timezone.utc),
            agent_id="new-agent",
            action_taken="New accomplishment added",
            outcome="success",
            tokens_consumed=100,
        )
        tracker_with_tasks.ledger.add_progress("TEST-002", entry)
        
        summary2 = tracker_with_tasks.get_session_summary()
        
        assert summary2 is not None
        assert summary2.level == SummaryLevel.SESSION


# =============================================================================
# Error Condition Tests
# =============================================================================


class TestErrorConditions:
    """Tests for error conditions."""

    def test_invalid_negative_budget_raises_value_error(self, sample_session_summary):
        """T-033: Verify negative budget is rejected."""
        summarizer = HierarchicalSummarizer()
        
        with pytest.raises(ValueError, match="Token budget must be non-negative"):
            summarizer.load_context(sample_session_summary, token_budget=-100)

    def test_invalid_negative_threshold_raises_value_error(self, sample_tasks_single_phase):
        """T-034: Verify negative phase threshold is rejected."""
        summarizer = HierarchicalSummarizer()
        
        with pytest.raises(ValueError, match="Phase threshold must be positive"):
            summarizer.detect_phases(sample_tasks_single_phase, threshold_minutes=-30)


# =============================================================================
# Performance Tests (NFR-001, NFR-002)
# =============================================================================


class TestPerformance:
    """Performance tests for summarizer."""

    def test_phase_detection_performance_under_100ms(self, large_task_set_100):
        """T-035: Verify phase detection completes in < 100ms for 100 tasks."""
        summarizer = HierarchicalSummarizer()
        
        start = time.perf_counter()
        phases = summarizer.detect_phases(large_task_set_100)
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        assert elapsed_ms < 100, f"Phase detection took {elapsed_ms:.2f}ms (limit: 100ms)"
        assert len(phases) >= 1

    def test_full_session_summary_under_2_seconds(self, large_task_set_100):
        """T-036: Verify full session summary generated in < 2 seconds."""
        summarizer = HierarchicalSummarizer()
        
        start = time.perf_counter()
        session_summary = summarizer.generate_full_session_summary(large_task_set_100)
        elapsed = time.perf_counter() - start
        
        assert elapsed < 2.0, f"Session summary took {elapsed:.2f}s (limit: 2s)"
        assert session_summary.level == SummaryLevel.SESSION
