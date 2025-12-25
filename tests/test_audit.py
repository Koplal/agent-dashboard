"""
Unit tests for Audit Trail Infrastructure (NESY-009).

Tests cover:
- AuditEntry creation and hash chaining
- Storage backends (Memory, File, SQLite)
- AuditTrailManager operations
- Query engine filtering and pagination
- Compliance report generation
"""

import json
import os
import pytest
import tempfile
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from audit import (
    # Trail
    AuditEntry,
    DecisionType,
    VerificationStatus,
    hash_content,
    summarize_content,
    # Storage
    StorageBackend,
    FileStorageBackend,
    SQLiteStorageBackend,
    MemoryStorageBackend,
    # Manager
    AuditTrailManager,
    IntegrityReport,
    get_default_manager,
    record_decision,
    # Query
    AuditQueryEngine,
    QueryFilter,
    QueryResult,
    SortField,
    SortOrder,
    # Compliance
    ComplianceReport,
    ComplianceReportGenerator,
)


# ============================================================================
# Trail Tests
# ============================================================================

class TestHashContent:
    """Tests for hash_content function."""

    def test_hash_string(self):
        """Test hashing a string."""
        result = hash_content("test string")
        assert isinstance(result, str)
        assert len(result) == 64  # SHA-256 hex

    def test_hash_dict(self):
        """Test hashing a dictionary."""
        result = hash_content({"key": "value", "num": 42})
        assert isinstance(result, str)
        assert len(result) == 64

    def test_hash_list(self):
        """Test hashing a list."""
        result = hash_content([1, 2, 3, "four"])
        assert isinstance(result, str)
        assert len(result) == 64

    def test_hash_deterministic(self):
        """Test that hashing is deterministic."""
        data = {"a": 1, "b": [2, 3]}
        assert hash_content(data) == hash_content(data)

    def test_hash_different_inputs(self):
        """Test that different inputs produce different hashes."""
        assert hash_content("a") != hash_content("b")

    def test_hash_none(self):
        """Test hashing None."""
        result = hash_content(None)
        assert isinstance(result, str)
        assert len(result) == 64


class TestSummarizeContent:
    """Tests for summarize_content function."""

    def test_summarize_string(self):
        """Test summarizing a string."""
        result = summarize_content("short text")
        assert result == "short text"

    def test_summarize_long_string(self):
        """Test summarizing a long string."""
        long_text = "x" * 200
        result = summarize_content(long_text, max_length=50)
        assert len(result) <= 53  # 50 + "..."
        assert result.endswith("...")

    def test_summarize_dict(self):
        """Test summarizing a dictionary."""
        result = summarize_content({"key": "value"})
        assert "key" in result

    def test_summarize_list(self):
        """Test summarizing a list."""
        result = summarize_content([1, 2, 3])
        assert "list of 3 items" in result

    def test_summarize_none(self):
        """Test summarizing None."""
        result = summarize_content(None)
        assert result == "<none>"


class TestDecisionType:
    """Tests for DecisionType enum."""

    def test_all_types_exist(self):
        """Test that all expected decision types exist."""
        types = [
            DecisionType.TASK_ROUTING,
            DecisionType.AGENT_SELECTION,
            DecisionType.TOOL_INVOCATION,
            DecisionType.OUTPUT_GENERATION,
            DecisionType.VERIFICATION,
            DecisionType.HUMAN_ESCALATION,
            DecisionType.RULE_APPLICATION,
            DecisionType.ERROR_HANDLING,
            DecisionType.PANEL_SELECTION,
            DecisionType.JUDGE_VERDICT,
            DecisionType.SYMBOLIC_VERIFICATION,
            DecisionType.SCHEMA_VALIDATION,
        ]
        assert len(types) == 12

    def test_type_values(self):
        """Test that types have string values."""
        assert DecisionType.TASK_ROUTING.value == "task_routing"
        assert DecisionType.PANEL_SELECTION.value == "panel_selection"


class TestVerificationStatus:
    """Tests for VerificationStatus enum."""

    def test_all_statuses_exist(self):
        """Test that all expected statuses exist."""
        statuses = [
            VerificationStatus.PENDING,
            VerificationStatus.VERIFIED,
            VerificationStatus.FAILED,
            VerificationStatus.SKIPPED,
        ]
        assert len(statuses) == 4


class TestAuditEntry:
    """Tests for AuditEntry dataclass."""

    def test_create_entry(self):
        """Test creating an audit entry."""
        entry = AuditEntry(
            session_id="session-123",
            decision_type=DecisionType.TASK_ROUTING,
            agent_id="orchestrator",
            input_hash="abc123",
            output_hash="def456",
        )
        assert entry.session_id == "session-123"
        assert entry.decision_type == DecisionType.TASK_ROUTING
        assert entry.agent_id == "orchestrator"
        assert entry.entry_id  # Auto-generated

    def test_entry_timestamp(self):
        """Test that entry has timestamp."""
        entry = AuditEntry(
            session_id="session-123",
            decision_type=DecisionType.TASK_ROUTING,
            agent_id="orchestrator",
            input_hash="abc123",
            output_hash="def456",
        )
        assert entry.timestamp is not None
        assert entry.timestamp.tzinfo == timezone.utc

    def test_compute_hash(self):
        """Test computing entry hash."""
        entry = AuditEntry(
            session_id="session-123",
            decision_type=DecisionType.TASK_ROUTING,
            agent_id="orchestrator",
            input_hash="abc123",
            output_hash="def456",
        )
        hash_value = entry.compute_hash()
        assert isinstance(hash_value, str)
        assert len(hash_value) == 64

    def test_finalize_entry(self):
        """Test finalizing entry."""
        entry = AuditEntry(
            session_id="session-123",
            decision_type=DecisionType.TASK_ROUTING,
            agent_id="orchestrator",
            input_hash="abc123",
            output_hash="def456",
        )
        entry.finalize()
        assert entry.entry_hash
        assert len(entry.entry_hash) == 64

    def test_verify_hash(self):
        """Test hash verification."""
        entry = AuditEntry(
            session_id="session-123",
            decision_type=DecisionType.TASK_ROUTING,
            agent_id="orchestrator",
            input_hash="abc123",
            output_hash="def456",
        )
        entry.finalize()
        assert entry.verify_hash()

    def test_tampered_entry_fails_verification(self):
        """Test that tampered entry fails verification."""
        entry = AuditEntry(
            session_id="session-123",
            decision_type=DecisionType.TASK_ROUTING,
            agent_id="orchestrator",
            input_hash="abc123",
            output_hash="def456",
        )
        entry.finalize()
        entry.input_hash = "modified"  # Tamper with entry
        assert not entry.verify_hash()

    def test_add_child(self):
        """Test adding child entry."""
        entry = AuditEntry(
            session_id="session-123",
            decision_type=DecisionType.TASK_ROUTING,
            agent_id="orchestrator",
            input_hash="abc123",
            output_hash="def456",
        )
        entry.add_child("child-1")
        entry.add_child("child-2")
        assert len(entry.child_entry_ids) == 2
        assert "child-1" in entry.child_entry_ids

    def test_set_verification(self):
        """Test setting verification status."""
        entry = AuditEntry(
            session_id="session-123",
            decision_type=DecisionType.TASK_ROUTING,
            agent_id="orchestrator",
            input_hash="abc123",
            output_hash="def456",
        )
        entry.set_verification(VerificationStatus.VERIFIED, "verifier-1", 0.95)
        assert entry.verification_status == VerificationStatus.VERIFIED
        assert "verifier-1" in entry.verifier_ids
        assert entry.verification_scores.get("verifier-1") == 0.95

    def test_to_dict(self):
        """Test converting entry to dictionary."""
        entry = AuditEntry(
            session_id="session-123",
            decision_type=DecisionType.TASK_ROUTING,
            agent_id="orchestrator",
            input_hash="abc123",
            output_hash="def456",
        )
        entry.finalize()
        d = entry.to_dict()
        assert d["session_id"] == "session-123"
        assert d["decision_type"] == "task_routing"
        assert d["agent_id"] == "orchestrator"

    def test_from_dict(self):
        """Test creating entry from dictionary."""
        entry = AuditEntry(
            session_id="session-123",
            decision_type=DecisionType.TASK_ROUTING,
            agent_id="orchestrator",
            input_hash="abc123",
            output_hash="def456",
        )
        entry.finalize()
        d = entry.to_dict()
        restored = AuditEntry.from_dict(d)
        assert restored.session_id == entry.session_id
        assert restored.decision_type == entry.decision_type
        assert restored.entry_hash == entry.entry_hash


# ============================================================================
# Storage Backend Tests
# ============================================================================

class TestMemoryStorageBackend:
    """Tests for MemoryStorageBackend."""

    def test_store_and_get(self):
        """Test storing and retrieving an entry."""
        storage = MemoryStorageBackend()
        entry = AuditEntry(
            session_id="session-123",
            decision_type=DecisionType.TASK_ROUTING,
            agent_id="orchestrator",
            input_hash="abc123",
            output_hash="def456",
        )
        entry.finalize()
        storage.store(entry)
        retrieved = storage.get(entry.entry_id)
        assert retrieved is not None
        assert retrieved.entry_id == entry.entry_id

    def test_get_nonexistent(self):
        """Test getting non-existent entry."""
        storage = MemoryStorageBackend()
        assert storage.get("nonexistent") is None

    def test_count(self):
        """Test counting entries."""
        storage = MemoryStorageBackend()
        assert storage.count() == 0
        for i in range(5):
            entry = AuditEntry(
                session_id=f"session-{i}",
                decision_type=DecisionType.TASK_ROUTING,
                agent_id="orchestrator",
                input_hash=f"hash-{i}",
                output_hash=f"out-{i}",
            )
            entry.finalize()
            storage.store(entry)
        assert storage.count() == 5

    def test_get_all_entries(self):
        """Test getting all entries."""
        storage = MemoryStorageBackend()
        for i in range(3):
            entry = AuditEntry(
                session_id=f"session-{i}",
                decision_type=DecisionType.TASK_ROUTING,
                agent_id="orchestrator",
                input_hash=f"hash-{i}",
                output_hash=f"out-{i}",
            )
            entry.finalize()
            storage.store(entry)
        entries = storage.get_all_entries()
        assert len(entries) == 3

    def test_get_entries_by_session(self):
        """Test getting entries by session."""
        storage = MemoryStorageBackend()
        for i in range(3):
            entry = AuditEntry(
                session_id="session-A" if i < 2 else "session-B",
                decision_type=DecisionType.TASK_ROUTING,
                agent_id="orchestrator",
                input_hash=f"hash-{i}",
                output_hash=f"out-{i}",
            )
            entry.finalize()
            storage.store(entry)
        session_a_entries = storage.get_entries_by_session("session-A")
        assert len(session_a_entries) == 2

    def test_get_entries_by_type(self):
        """Test getting entries by type."""
        storage = MemoryStorageBackend()
        entry1 = AuditEntry(
            session_id="session-1",
            decision_type=DecisionType.TASK_ROUTING,
            agent_id="orchestrator",
            input_hash="hash-1",
            output_hash="out-1",
        )
        entry1.finalize()
        storage.store(entry1)

        entry2 = AuditEntry(
            session_id="session-1",
            decision_type=DecisionType.VERIFICATION,
            agent_id="verifier",
            input_hash="hash-2",
            output_hash="out-2",
        )
        entry2.finalize()
        storage.store(entry2)

        routing_entries = storage.get_entries_by_type(DecisionType.TASK_ROUTING)
        assert len(routing_entries) == 1

    def test_get_entries_in_range(self):
        """Test getting entries in date range."""
        storage = MemoryStorageBackend()
        now = datetime.now(timezone.utc)

        entry1 = AuditEntry(
            session_id="session-1",
            decision_type=DecisionType.TASK_ROUTING,
            agent_id="orchestrator",
            input_hash="hash-1",
            output_hash="out-1",
        )
        entry1.timestamp = now - timedelta(hours=2)
        entry1.finalize()
        storage.store(entry1)

        entry2 = AuditEntry(
            session_id="session-1",
            decision_type=DecisionType.TASK_ROUTING,
            agent_id="orchestrator",
            input_hash="hash-2",
            output_hash="out-2",
        )
        entry2.timestamp = now
        entry2.finalize()
        storage.store(entry2)

        entries = storage.get_entries_in_range(
            now - timedelta(hours=1),
            now + timedelta(minutes=1)
        )
        assert len(entries) == 1

    def test_get_latest_hash(self):
        """Test getting latest hash."""
        storage = MemoryStorageBackend()
        assert storage.get_latest_hash() == ""

        entry = AuditEntry(
            session_id="session-1",
            decision_type=DecisionType.TASK_ROUTING,
            agent_id="orchestrator",
            input_hash="hash-1",
            output_hash="out-1",
        )
        entry.finalize()
        storage.store(entry)
        assert storage.get_latest_hash() == entry.entry_hash


class TestFileStorageBackend:
    """Tests for FileStorageBackend."""

    def test_store_and_get(self):
        """Test storing and retrieving an entry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = FileStorageBackend(tmpdir)
            entry = AuditEntry(
                session_id="session-123",
                decision_type=DecisionType.TASK_ROUTING,
                agent_id="orchestrator",
                input_hash="abc123",
                output_hash="def456",
            )
            entry.finalize()
            storage.store(entry)
            retrieved = storage.get(entry.entry_id)
            assert retrieved is not None
            assert retrieved.entry_id == entry.entry_id

    def test_persistence(self):
        """Test that data persists across instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage1 = FileStorageBackend(tmpdir)
            entry = AuditEntry(
                session_id="session-123",
                decision_type=DecisionType.TASK_ROUTING,
                agent_id="orchestrator",
                input_hash="abc123",
                output_hash="def456",
            )
            entry.finalize()
            storage1.store(entry)

            # Create new instance
            storage2 = FileStorageBackend(tmpdir)
            retrieved = storage2.get(entry.entry_id)
            assert retrieved is not None
            assert retrieved.entry_id == entry.entry_id

    def test_count(self):
        """Test counting entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = FileStorageBackend(tmpdir)
            for i in range(3):
                entry = AuditEntry(
                    session_id=f"session-{i}",
                    decision_type=DecisionType.TASK_ROUTING,
                    agent_id="orchestrator",
                    input_hash=f"hash-{i}",
                    output_hash=f"out-{i}",
                )
                entry.finalize()
                storage.store(entry)
            assert storage.count() == 3


class TestSQLiteStorageBackend:
    """Tests for SQLiteStorageBackend."""

    def test_store_and_get(self):
        """Test storing and retrieving an entry."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            storage = SQLiteStorageBackend(db_path)
            entry = AuditEntry(
                session_id="session-123",
                decision_type=DecisionType.TASK_ROUTING,
                agent_id="orchestrator",
                input_hash="abc123",
                output_hash="def456",
            )
            entry.finalize()
            storage.store(entry)
            retrieved = storage.get(entry.entry_id)
            assert retrieved is not None
            assert retrieved.entry_id == entry.entry_id
        finally:
            os.unlink(db_path)

    def test_persistence(self):
        """Test that data persists across instances."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            storage1 = SQLiteStorageBackend(db_path)
            entry = AuditEntry(
                session_id="session-123",
                decision_type=DecisionType.TASK_ROUTING,
                agent_id="orchestrator",
                input_hash="abc123",
                output_hash="def456",
            )
            entry.finalize()
            storage1.store(entry)

            # Create new instance
            storage2 = SQLiteStorageBackend(db_path)
            retrieved = storage2.get(entry.entry_id)
            assert retrieved is not None
            assert retrieved.entry_id == entry.entry_id
        finally:
            os.unlink(db_path)

    def test_get_entries_by_agent(self):
        """Test getting entries by agent."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            storage = SQLiteStorageBackend(db_path)
            entry1 = AuditEntry(
                session_id="session-1",
                decision_type=DecisionType.TASK_ROUTING,
                agent_id="agent-A",
                input_hash="hash-1",
                output_hash="out-1",
            )
            entry1.finalize()
            storage.store(entry1)

            entry2 = AuditEntry(
                session_id="session-1",
                decision_type=DecisionType.TASK_ROUTING,
                agent_id="agent-B",
                input_hash="hash-2",
                output_hash="out-2",
            )
            entry2.finalize()
            storage.store(entry2)

            agent_a_entries = storage.get_entries_by_agent("agent-A")
            assert len(agent_a_entries) == 1
            assert agent_a_entries[0].agent_id == "agent-A"
        finally:
            os.unlink(db_path)


# ============================================================================
# Manager Tests
# ============================================================================

class TestAuditTrailManager:
    """Tests for AuditTrailManager."""

    def test_create_manager(self):
        """Test creating a manager."""
        manager = AuditTrailManager()
        assert manager.storage is not None
        assert manager.session_id

    def test_record_decision(self):
        """Test recording a decision."""
        manager = AuditTrailManager()
        entry = manager.record(
            decision_type=DecisionType.TASK_ROUTING,
            agent_id="orchestrator",
            inputs={"task": "test"},
            outputs={"result": "success"},
        )
        assert entry is not None
        assert entry.decision_type == DecisionType.TASK_ROUTING
        assert entry.agent_id == "orchestrator"

    def test_record_with_options(self):
        """Test recording with additional options."""
        manager = AuditTrailManager()
        entry = manager.record(
            decision_type=DecisionType.AGENT_SELECTION,
            agent_id="orchestrator",
            inputs={"task": "research"},
            outputs={"agent": "researcher"},
            confidence=0.95,
            reasoning="Best fit for research tasks",
            action="select_researcher",
        )
        assert entry.confidence_score == 0.95
        assert entry.reasoning_summary == "Best fit for research tasks"
        assert entry.selected_action == "select_researcher"

    def test_record_tool_invocation(self):
        """Test recording tool invocation."""
        manager = AuditTrailManager()
        entry = manager.record_tool_invocation(
            agent_id="researcher",
            tool_name="web_search",
            tool_input={"query": "test"},
            tool_output={"results": []},
        )
        assert entry.decision_type == DecisionType.TOOL_INVOCATION
        assert "web_search" in entry.selected_action

    def test_record_agent_selection(self):
        """Test recording agent selection."""
        manager = AuditTrailManager()
        entry = manager.record_agent_selection(
            orchestrator_id="orchestrator",
            task="research quantum computing",
            selected_agent="researcher",
            candidates=["researcher", "summarizer", "validator"],
            confidence=0.9,
        )
        assert entry.decision_type == DecisionType.AGENT_SELECTION
        assert entry.confidence_score == 0.9

    def test_record_verification(self):
        """Test recording verification."""
        manager = AuditTrailManager()
        entry = manager.record_verification(
            verifier_id="validator",
            content_hash="abc123",
            verdict="approved",
            score=0.95,
            reasoning="Meets quality standards",
        )
        assert entry.decision_type == DecisionType.VERIFICATION
        assert entry.confidence_score == 0.95

    def test_record_panel_selection(self):
        """Test recording panel selection."""
        manager = AuditTrailManager()
        entry = manager.record_panel_selection(
            description="Evaluate research quality",
            panel_size=3,
            risk_score=45,
        )
        assert entry.decision_type == DecisionType.PANEL_SELECTION
        assert entry.agent_id == "panel_selector"

    def test_chain_integrity(self):
        """Test chain integrity is maintained."""
        manager = AuditTrailManager()
        entries = []
        for i in range(5):
            entry = manager.record(
                decision_type=DecisionType.TASK_ROUTING,
                agent_id=f"agent-{i}",
                inputs={"step": i},
                outputs={"done": True},
            )
            entries.append(entry)

        # Verify chain
        for i in range(1, len(entries)):
            assert entries[i].previous_entry_hash == entries[i-1].entry_hash

    def test_verify_integrity_success(self):
        """Test integrity verification succeeds for valid chain."""
        manager = AuditTrailManager()
        for i in range(3):
            manager.record(
                decision_type=DecisionType.TASK_ROUTING,
                agent_id=f"agent-{i}",
                inputs={"step": i},
                outputs={"done": True},
            )
        report = manager.verify_integrity()
        assert report.verified
        assert report.entries_checked == 3
        assert len(report.issues) == 0

    def test_get_entry(self):
        """Test getting a specific entry."""
        manager = AuditTrailManager()
        entry = manager.record(
            decision_type=DecisionType.TASK_ROUTING,
            agent_id="orchestrator",
            inputs={"task": "test"},
            outputs={"result": "success"},
        )
        retrieved = manager.get_entry(entry.entry_id)
        assert retrieved is not None
        assert retrieved.entry_id == entry.entry_id

    def test_get_session_entries(self):
        """Test getting entries for current session."""
        manager = AuditTrailManager()
        for i in range(3):
            manager.record(
                decision_type=DecisionType.TASK_ROUTING,
                agent_id=f"agent-{i}",
                inputs={"step": i},
                outputs={"done": True},
            )
        entries = manager.get_session_entries()
        assert len(entries) == 3

    def test_new_session(self):
        """Test starting a new session."""
        manager = AuditTrailManager()
        old_session = manager.session_id
        new_session = manager.new_session()
        assert new_session != old_session

    def test_hooks(self):
        """Test pre and post record hooks."""
        manager = AuditTrailManager()
        pre_called = []
        post_called = []

        def pre_hook(entry):
            pre_called.append(entry)
            entry.metadata["pre_processed"] = True
            return entry

        def post_hook(entry):
            post_called.append(entry)

        manager.add_pre_record_hook(pre_hook)
        manager.add_post_record_hook(post_hook)

        entry = manager.record(
            decision_type=DecisionType.TASK_ROUTING,
            agent_id="orchestrator",
            inputs={"task": "test"},
            outputs={"result": "success"},
        )

        assert len(pre_called) == 1
        assert len(post_called) == 1
        assert entry.metadata.get("pre_processed")

    def test_get_stats(self):
        """Test getting manager statistics."""
        manager = AuditTrailManager()
        for i in range(3):
            manager.record(
                decision_type=DecisionType.TASK_ROUTING,
                agent_id=f"agent-{i}",
                inputs={"step": i},
                outputs={"done": True},
            )
        stats = manager.get_stats()
        assert stats["entries_recorded"] == 3
        assert stats["total_entries"] == 3


class TestDefaultManager:
    """Tests for default manager functions."""

    def test_get_default_manager(self):
        """Test getting default manager."""
        manager = get_default_manager()
        assert manager is not None
        assert isinstance(manager, AuditTrailManager)

    def test_record_decision_function(self):
        """Test record_decision convenience function."""
        entry = record_decision(
            decision_type=DecisionType.TASK_ROUTING,
            agent_id="test-agent",
            inputs={"test": True},
            outputs={"done": True},
        )
        assert entry is not None
        assert entry.decision_type == DecisionType.TASK_ROUTING


# ============================================================================
# Query Engine Tests
# ============================================================================

class TestQueryFilter:
    """Tests for QueryFilter."""

    def test_empty_filter_matches_all(self):
        """Test that empty filter matches all entries."""
        filter = QueryFilter()
        entry = AuditEntry(
            session_id="session-1",
            decision_type=DecisionType.TASK_ROUTING,
            agent_id="orchestrator",
            input_hash="hash-1",
            output_hash="out-1",
        )
        assert filter.matches(entry)

    def test_filter_by_type(self):
        """Test filtering by decision type."""
        filter = QueryFilter(decision_types=[DecisionType.VERIFICATION])
        entry1 = AuditEntry(
            session_id="session-1",
            decision_type=DecisionType.TASK_ROUTING,
            agent_id="orchestrator",
            input_hash="hash-1",
            output_hash="out-1",
        )
        entry2 = AuditEntry(
            session_id="session-1",
            decision_type=DecisionType.VERIFICATION,
            agent_id="verifier",
            input_hash="hash-2",
            output_hash="out-2",
        )
        assert not filter.matches(entry1)
        assert filter.matches(entry2)

    def test_filter_by_agent(self):
        """Test filtering by agent ID."""
        filter = QueryFilter(agent_ids=["orchestrator"])
        entry1 = AuditEntry(
            session_id="session-1",
            decision_type=DecisionType.TASK_ROUTING,
            agent_id="orchestrator",
            input_hash="hash-1",
            output_hash="out-1",
        )
        entry2 = AuditEntry(
            session_id="session-1",
            decision_type=DecisionType.TASK_ROUTING,
            agent_id="other",
            input_hash="hash-2",
            output_hash="out-2",
        )
        assert filter.matches(entry1)
        assert not filter.matches(entry2)

    def test_filter_by_confidence(self):
        """Test filtering by confidence range."""
        filter = QueryFilter(min_confidence=0.8, max_confidence=1.0)
        entry1 = AuditEntry(
            session_id="session-1",
            decision_type=DecisionType.TASK_ROUTING,
            agent_id="orchestrator",
            input_hash="hash-1",
            output_hash="out-1",
            confidence_score=0.95,
        )
        entry2 = AuditEntry(
            session_id="session-1",
            decision_type=DecisionType.TASK_ROUTING,
            agent_id="orchestrator",
            input_hash="hash-2",
            output_hash="out-2",
            confidence_score=0.5,
        )
        assert filter.matches(entry1)
        assert not filter.matches(entry2)

    def test_filter_by_text_search(self):
        """Test filtering by text search."""
        filter = QueryFilter(search_text="quantum")
        entry1 = AuditEntry(
            session_id="session-1",
            decision_type=DecisionType.TASK_ROUTING,
            agent_id="orchestrator",
            input_hash="hash-1",
            output_hash="out-1",
            input_summary="research quantum computing",
        )
        entry2 = AuditEntry(
            session_id="session-1",
            decision_type=DecisionType.TASK_ROUTING,
            agent_id="orchestrator",
            input_hash="hash-2",
            output_hash="out-2",
            input_summary="research classical computing",
        )
        assert filter.matches(entry1)
        assert not filter.matches(entry2)

    def test_custom_filter(self):
        """Test custom filter function."""
        filter = QueryFilter(custom_filter=lambda e: e.agent_id.startswith("orch"))
        entry1 = AuditEntry(
            session_id="session-1",
            decision_type=DecisionType.TASK_ROUTING,
            agent_id="orchestrator",
            input_hash="hash-1",
            output_hash="out-1",
        )
        entry2 = AuditEntry(
            session_id="session-1",
            decision_type=DecisionType.TASK_ROUTING,
            agent_id="researcher",
            input_hash="hash-2",
            output_hash="out-2",
        )
        assert filter.matches(entry1)
        assert not filter.matches(entry2)


class TestAuditQueryEngine:
    """Tests for AuditQueryEngine."""

    def setup_method(self):
        """Set up test fixtures."""
        self.storage = MemoryStorageBackend()
        self.engine = AuditQueryEngine(self.storage)

        # Create test entries
        for i in range(10):
            entry = AuditEntry(
                session_id=f"session-{i % 3}",
                decision_type=DecisionType.TASK_ROUTING if i % 2 == 0 else DecisionType.VERIFICATION,
                agent_id=f"agent-{i % 4}",
                input_hash=f"hash-{i}",
                output_hash=f"out-{i}",
                confidence_score=i / 10,
            )
            entry.finalize()
            self.storage.store(entry)

    def test_query_all(self):
        """Test querying all entries."""
        result = self.engine.query()
        assert result.total_count == 10

    def test_query_with_filter(self):
        """Test querying with filter."""
        filter = QueryFilter(decision_types=[DecisionType.VERIFICATION])
        result = self.engine.query(filter=filter)
        assert result.total_count == 5  # Odd indices

    def test_query_pagination(self):
        """Test query pagination."""
        result = self.engine.query(page=1, page_size=3)
        assert len(result.entries) == 3
        assert result.page == 1
        assert result.has_more

        result2 = self.engine.query(page=4, page_size=3)
        assert len(result2.entries) == 1
        assert not result2.has_more

    def test_query_sorting(self):
        """Test query sorting."""
        result = self.engine.query(
            sort_by=SortField.CONFIDENCE,
            order=SortOrder.DESC,
        )
        scores = [e.confidence_score for e in result.entries]
        assert scores == sorted(scores, reverse=True)

    def test_find_by_id(self):
        """Test finding entry by ID."""
        entries = self.storage.get_all_entries()
        entry = self.engine.find_by_id(entries[0].entry_id)
        assert entry is not None
        assert entry.entry_id == entries[0].entry_id

    def test_get_statistics(self):
        """Test getting statistics."""
        stats = self.engine.get_statistics()
        assert stats["total_entries"] == 10
        assert "by_type" in stats
        assert "by_agent" in stats


class TestQueryResult:
    """Tests for QueryResult."""

    def test_to_dict(self):
        """Test converting result to dictionary."""
        result = QueryResult(
            entries=[],
            total_count=100,
            page=2,
            page_size=25,
            has_more=True,
            query_time_ms=15,
        )
        d = result.to_dict()
        assert d["total_count"] == 100
        assert d["page"] == 2
        assert d["page_size"] == 25
        assert d["has_more"]


# ============================================================================
# Compliance Report Tests
# ============================================================================

class TestComplianceReport:
    """Tests for ComplianceReport."""

    def test_create_report(self):
        """Test creating a report."""
        report = ComplianceReport(
            total_decisions=100,
            by_type={"task_routing": 50, "verification": 50},
            by_agent={"orchestrator": 60, "verifier": 40},
        )
        assert report.report_id
        assert report.total_decisions == 100

    def test_to_dict(self):
        """Test converting report to dictionary."""
        report = ComplianceReport(total_decisions=100)
        d = report.to_dict()
        assert "report_id" in d
        assert "summary" in d
        assert d["summary"]["total_decisions"] == 100

    def test_to_json(self):
        """Test converting report to JSON."""
        report = ComplianceReport(total_decisions=100)
        json_str = report.to_json()
        parsed = json.loads(json_str)
        assert parsed["summary"]["total_decisions"] == 100

    def test_to_markdown(self):
        """Test converting report to Markdown."""
        report = ComplianceReport(
            total_decisions=100,
            by_type={"task_routing": 50, "verification": 50},
            executive_summary="Test summary",
        )
        md = report.to_markdown()
        assert "# Compliance Report" in md
        assert "Test summary" in md
        assert "task_routing" in md


class TestComplianceReportGenerator:
    """Tests for ComplianceReportGenerator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.storage = MemoryStorageBackend()
        self.manager = AuditTrailManager(self.storage)

        # Create test entries
        now = datetime.now(timezone.utc)
        for i in range(10):
            entry = self.manager.record(
                decision_type=DecisionType.TASK_ROUTING if i % 2 == 0 else DecisionType.VERIFICATION,
                agent_id=f"agent-{i % 3}",
                inputs={"step": i},
                outputs={"done": True},
                confidence=i / 10,
            )

        self.generator = ComplianceReportGenerator(self.manager)

    def test_generate_report(self):
        """Test generating a report."""
        now = datetime.now(timezone.utc)
        report = self.generator.generate(
            start_date=now - timedelta(hours=1),
            end_date=now + timedelta(hours=1),
        )
        assert report.total_decisions == 10
        assert len(report.by_type) > 0
        assert len(report.by_agent) > 0

    def test_generate_report_with_integrity(self):
        """Test report includes integrity check."""
        now = datetime.now(timezone.utc)
        report = self.generator.generate(
            start_date=now - timedelta(hours=1),
            end_date=now + timedelta(hours=1),
            verify_integrity=True,
        )
        assert report.integrity is not None
        assert report.integrity.verified

    def test_generate_report_with_samples(self):
        """Test report includes sample entries."""
        now = datetime.now(timezone.utc)
        report = self.generator.generate(
            start_date=now - timedelta(hours=1),
            end_date=now + timedelta(hours=1),
            include_samples=True,
            sample_count=5,
        )
        assert len(report.sample_entries) == 5

    def test_generate_agent_report(self):
        """Test generating agent-specific report."""
        report = self.generator.generate_agent_report("agent-0")
        assert "agent_id" in report
        assert "total_decisions" in report

    def test_generate_session_report(self):
        """Test generating session-specific report."""
        report = self.generator.generate_session_report(self.manager.session_id)
        assert "session_id" in report
        assert "total_decisions" in report

    def test_export_for_soc2(self):
        """Test exporting report for SOC2."""
        now = datetime.now(timezone.utc)
        report = self.generator.generate(
            start_date=now - timedelta(hours=1),
            end_date=now + timedelta(hours=1),
        )
        soc2 = self.generator.export_for_regulatory(report, "SOC2")
        assert "soc2_controls" in soc2
        assert "CC6.1" in soc2["soc2_controls"]
        assert "CC7.2" in soc2["soc2_controls"]

    def test_export_for_hipaa(self):
        """Test exporting report for HIPAA."""
        now = datetime.now(timezone.utc)
        report = self.generator.generate(
            start_date=now - timedelta(hours=1),
            end_date=now + timedelta(hours=1),
        )
        hipaa = self.generator.export_for_regulatory(report, "HIPAA")
        assert "hipaa_safeguards" in hipaa
        assert "access_control" in hipaa["hipaa_safeguards"]
        assert "audit_controls" in hipaa["hipaa_safeguards"]


# ============================================================================
# Integration Tests
# ============================================================================

class TestAuditIntegration:
    """Integration tests for audit system."""

    def test_full_workflow(self):
        """Test complete audit workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create manager with file storage
            storage = FileStorageBackend(tmpdir)
            manager = AuditTrailManager(storage)

            # Record some decisions
            parent = manager.record_agent_selection(
                orchestrator_id="orchestrator",
                task="research quantum computing",
                selected_agent="researcher",
                candidates=["researcher", "summarizer"],
                confidence=0.9,
            )

            manager.record_tool_invocation(
                agent_id="researcher",
                tool_name="web_search",
                tool_input={"query": "quantum computing"},
                tool_output={"results": ["result1", "result2"]},
                parent_id=parent.entry_id,
            )

            manager.record_verification(
                verifier_id="validator",
                content_hash="abc123",
                verdict="approved",
                score=0.95,
                reasoning="High quality research",
                parent_id=parent.entry_id,
            )

            # Verify integrity
            report = manager.verify_integrity()
            assert report.verified
            assert report.entries_checked == 3

            # Query entries
            engine = AuditQueryEngine(storage)
            result = engine.query(
                filter=QueryFilter(decision_types=[DecisionType.VERIFICATION])
            )
            assert result.total_count == 1

            # Generate compliance report
            generator = ComplianceReportGenerator(manager)
            now = datetime.now(timezone.utc)
            compliance = generator.generate(
                start_date=now - timedelta(hours=1),
                end_date=now + timedelta(hours=1),
            )
            assert compliance.total_decisions == 3
            assert compliance.integrity.verified

    def test_tamper_detection(self):
        """Test that tampering is detected."""
        storage = MemoryStorageBackend()
        manager = AuditTrailManager(storage)

        # Record entries
        for i in range(3):
            manager.record(
                decision_type=DecisionType.TASK_ROUTING,
                agent_id=f"agent-{i}",
                inputs={"step": i},
                outputs={"done": True},
            )

        # Tamper with an entry
        entries = storage.get_all_entries()
        entries[1].input_hash = "tampered"

        # Verify should fail
        report = manager.verify_integrity()
        assert not report.verified
        assert len(report.issues) > 0
        assert any("hash_mismatch" in str(issue) for issue in report.issues)

    def test_chain_break_detection(self):
        """Test that chain breaks are detected."""
        storage = MemoryStorageBackend()
        manager = AuditTrailManager(storage)

        # Record entries
        for i in range(3):
            manager.record(
                decision_type=DecisionType.TASK_ROUTING,
                agent_id=f"agent-{i}",
                inputs={"step": i},
                outputs={"done": True},
            )

        # Break the chain
        entries = storage.get_all_entries()
        entries[2].previous_entry_hash = "broken"

        # Verify should fail
        report = manager.verify_integrity()
        assert not report.verified
        assert any("chain_break" in str(issue) for issue in report.issues)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
