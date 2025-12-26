"""
Unit tests for Entity-Aware Provenance (AUDIT-001).

Tests cover:
- EntityRole enum values and behavior
- EntityProvenance frozen dataclass
- EntityProvenanceTracker recording and querying
- Integration with AuditTrailManager
- Edge cases and error handling

Target: 48 tests
Version: 2.6.0
"""

import pytest
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional
import uuid

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from knowledge.graph import Entity, EntityType
from audit import (
    AuditEntry,
    AuditTrailManager,
    DecisionType,
    MemoryStorageBackend,
)
from audit.provenance import (
    EntityRole,
    EntityProvenance,
    EntityProvenanceTracker,
)


def utc_now() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


# ============================================================================
# EntityRole Enum Tests (4 tests)
# ============================================================================

class TestEntityRole:
    """Tests for EntityRole enum."""

    def test_all_roles_exist(self):
        """ER-01: Verify EntityRole has INPUT, OUTPUT, CONTEXT, SUBJECT."""
        roles = [
            EntityRole.INPUT,
            EntityRole.OUTPUT,
            EntityRole.CONTEXT,
            EntityRole.SUBJECT,
        ]
        assert len(roles) == 4

    def test_role_values(self):
        """ER-02: Verify role string values."""
        assert EntityRole.INPUT.value == "input"
        assert EntityRole.OUTPUT.value == "output"
        assert EntityRole.CONTEXT.value == "context"
        assert EntityRole.SUBJECT.value == "subject"

    def test_role_is_string_enum(self):
        """ER-03: Verify EntityRole inherits from str."""
        assert isinstance(EntityRole.INPUT, str)
        assert isinstance(EntityRole.OUTPUT, str)
        assert EntityRole.INPUT == "input"

    def test_role_hashable(self):
        """ER-04: Roles can be used in sets/dicts."""
        role_set = {EntityRole.INPUT, EntityRole.OUTPUT}
        assert len(role_set) == 2
        assert EntityRole.INPUT in role_set

        role_dict = {EntityRole.INPUT: "value"}
        assert role_dict[EntityRole.INPUT] == "value"


# ============================================================================
# EntityProvenance Dataclass Tests (12 tests)
# ============================================================================

class TestEntityProvenance:
    """Tests for EntityProvenance frozen dataclass."""

    def test_create_basic(self):
        """EP-01: Create EntityProvenance with required fields."""
        prov = EntityProvenance(
            entity_name="TestEntity",
            entity_type=EntityType.CONCEPT,
            role=EntityRole.INPUT,
            entry_id="entry-123",
        )
        assert prov.entity_name == "TestEntity"
        assert prov.entity_type == EntityType.CONCEPT
        assert prov.role == EntityRole.INPUT
        assert prov.entry_id == "entry-123"

    def test_create_with_all_fields(self):
        """EP-02: Create with all optional fields."""
        now = utc_now()
        prov = EntityProvenance(
            entity_name="TestEntity",
            entity_type=EntityType.FUNCTION,
            role=EntityRole.OUTPUT,
            entry_id="entry-456",
            provenance_id="prov-789",
            recorded_at=now,
            valid_from=now - timedelta(days=1),
            valid_to=now + timedelta(days=1),
            source_location="module.py:42",
            metadata={"key": "value"},
        )
        assert prov.provenance_id == "prov-789"
        assert prov.recorded_at == now
        assert prov.valid_from == now - timedelta(days=1)
        assert prov.valid_to == now + timedelta(days=1)
        assert prov.source_location == "module.py:42"
        assert prov.metadata == {"key": "value"}

    def test_auto_provenance_id(self):
        """EP-03: UUID auto-generated if not provided."""
        prov = EntityProvenance(
            entity_name="TestEntity",
            entity_type=EntityType.CONCEPT,
            role=EntityRole.INPUT,
            entry_id="entry-123",
        )
        assert prov.provenance_id is not None
        # Verify it's a valid UUID format
        uuid.UUID(prov.provenance_id)

    def test_recorded_at_default(self):
        """EP-04: recorded_at defaults to UTC now."""
        before = utc_now()
        prov = EntityProvenance(
            entity_name="TestEntity",
            entity_type=EntityType.CONCEPT,
            role=EntityRole.INPUT,
            entry_id="entry-123",
        )
        after = utc_now()

        assert prov.recorded_at is not None
        assert prov.recorded_at.tzinfo is not None
        assert before <= prov.recorded_at <= after

    def test_frozen_immutability(self):
        """EP-05: Cannot modify after creation."""
        prov = EntityProvenance(
            entity_name="TestEntity",
            entity_type=EntityType.CONCEPT,
            role=EntityRole.INPUT,
            entry_id="entry-123",
        )
        with pytest.raises(FrozenInstanceError):
            prov.entity_name = "Modified"

    def test_to_dict_basic(self):
        """EP-06: Serialize to dictionary."""
        prov = EntityProvenance(
            entity_name="TestEntity",
            entity_type=EntityType.CLASS,
            role=EntityRole.CONTEXT,
            entry_id="entry-123",
        )
        d = prov.to_dict()

        assert d["entity_name"] == "TestEntity"
        assert d["entity_type"] == "class"
        assert d["role"] == "context"
        assert d["entry_id"] == "entry-123"
        assert "provenance_id" in d
        assert "recorded_at" in d

    def test_to_dict_with_temporal(self):
        """EP-07: Serialize with valid_from/valid_to."""
        now = utc_now()
        prov = EntityProvenance(
            entity_name="TestEntity",
            entity_type=EntityType.CONCEPT,
            role=EntityRole.INPUT,
            entry_id="entry-123",
            valid_from=now - timedelta(days=1),
            valid_to=now + timedelta(days=1),
        )
        d = prov.to_dict()

        assert d["valid_from"] is not None
        # Should be ISO format string
        assert isinstance(d["valid_from"], str)
        assert "T" in d["valid_from"]  # ISO format indicator

    def test_from_dict_roundtrip(self):
        """EP-08: Create from dict and back."""
        now = utc_now()
        original = EntityProvenance(
            entity_name="TestEntity",
            entity_type=EntityType.FILE,
            role=EntityRole.SUBJECT,
            entry_id="entry-123",
            valid_from=now - timedelta(hours=1),
            valid_to=now + timedelta(hours=1),
            source_location="test.py:10",
            metadata={"version": "1.0"},
        )
        d = original.to_dict()
        restored = EntityProvenance.from_dict(d)

        assert restored.entity_name == original.entity_name
        assert restored.entity_type == original.entity_type
        assert restored.role == original.role
        assert restored.entry_id == original.entry_id
        assert restored.provenance_id == original.provenance_id
        assert restored.source_location == original.source_location
        assert restored.metadata == original.metadata

    def test_from_entity_basic(self):
        """EP-09: Factory from Entity with role/entry_id."""
        entity = Entity(
            name="MyFunction",
            entity_type=EntityType.FUNCTION,
            metadata={"params": ["a", "b"]},
        )
        prov = EntityProvenance.from_entity(
            entity=entity,
            role=EntityRole.INPUT,
            entry_id="entry-abc",
        )

        assert prov.entity_name == "MyFunction"
        assert prov.entity_type == EntityType.FUNCTION
        assert prov.role == EntityRole.INPUT
        assert prov.entry_id == "entry-abc"
        assert prov.metadata == {"params": ["a", "b"]}

    def test_from_entity_with_temporal(self):
        """EP-10: Factory preserves temporal fields."""
        now = utc_now()
        entity = Entity(
            name="TemporalEntity",
            entity_type=EntityType.CLASS,
            valid_from=now - timedelta(days=7),
            valid_to=now + timedelta(days=7),
        )
        prov = EntityProvenance.from_entity(
            entity=entity,
            role=EntityRole.CONTEXT,
            entry_id="entry-temporal",
        )

        assert prov.valid_from == entity.valid_from
        assert prov.valid_to == entity.valid_to

    def test_from_entity_with_source_location(self):
        """EP-11: Factory preserves source_location."""
        entity = Entity(
            name="CodeEntity",
            entity_type=EntityType.FUNCTION,
            source_location="src/utils.py:42",
        )
        prov = EntityProvenance.from_entity(
            entity=entity,
            role=EntityRole.SUBJECT,
            entry_id="entry-code",
        )

        assert prov.source_location == "src/utils.py:42"

    def test_provenance_id_uniqueness(self):
        """EP-12: Multiple instances have unique IDs."""
        provs = [
            EntityProvenance(
                entity_name="Entity",
                entity_type=EntityType.CONCEPT,
                role=EntityRole.INPUT,
                entry_id="entry-123",
            )
            for _ in range(10)
        ]
        ids = {p.provenance_id for p in provs}
        assert len(ids) == 10


# ============================================================================
# EntityProvenanceTracker Tests - Recording (5 tests)
# ============================================================================

class TestEntityProvenanceTrackerRecording:
    """Tests for EntityProvenanceTracker recording functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tracker = EntityProvenanceTracker()

    def test_record_entity_basic(self):
        """ET-01: Record entity with role and entry_id."""
        entity = Entity(name="TestEntity", entity_type=EntityType.CONCEPT)
        prov = self.tracker.record(
            entity=entity,
            role=EntityRole.INPUT,
            entry_id="entry-123",
        )

        assert isinstance(prov, EntityProvenance)
        assert prov.entity_name == "TestEntity"
        assert prov.role == EntityRole.INPUT
        assert prov.entry_id == "entry-123"

    def test_record_multiple_entities(self):
        """ET-02: Record several entities."""
        entities = [
            Entity(name=f"Entity{i}", entity_type=EntityType.CONCEPT)
            for i in range(5)
        ]
        for i, entity in enumerate(entities):
            self.tracker.record(
                entity=entity,
                role=EntityRole.INPUT,
                entry_id=f"entry-{i}",
            )

        # Verify all stored
        for i in range(5):
            results = self.tracker.get_entities_by_entry(f"entry-{i}")
            assert len(results) == 1
            assert results[0].entity_name == f"Entity{i}"

    def test_record_same_entity_different_roles(self):
        """ET-03: Same entity as INPUT and OUTPUT."""
        entity = Entity(name="SharedEntity", entity_type=EntityType.FUNCTION)

        self.tracker.record(
            entity=entity,
            role=EntityRole.INPUT,
            entry_id="entry-in",
        )
        self.tracker.record(
            entity=entity,
            role=EntityRole.OUTPUT,
            entry_id="entry-out",
        )

        input_results = self.tracker.get_entities_by_entry("entry-in")
        output_results = self.tracker.get_entities_by_entry("entry-out")

        assert len(input_results) == 1
        assert input_results[0].role == EntityRole.INPUT
        assert len(output_results) == 1
        assert output_results[0].role == EntityRole.OUTPUT

    def test_record_entity_creates_snapshot(self):
        """ET-04: Temporal state captured at record time."""
        now = utc_now()
        entity = Entity(
            name="TemporalEntity",
            entity_type=EntityType.CLASS,
            valid_from=now - timedelta(days=1),
            valid_to=now + timedelta(days=1),
        )

        prov = self.tracker.record(
            entity=entity,
            role=EntityRole.CONTEXT,
            entry_id="entry-temporal",
        )

        # Modify original entity (simulating external change)
        entity.valid_to = now + timedelta(days=100)

        # Provenance should retain original value
        assert prov.valid_to == now + timedelta(days=1)

    def test_record_with_metadata(self):
        """ET-05: Record with optional metadata."""
        entity = Entity(name="MetaEntity", entity_type=EntityType.CONCEPT)
        prov = self.tracker.record(
            entity=entity,
            role=EntityRole.INPUT,
            entry_id="entry-meta",
            metadata={"custom": "data", "count": 42},
        )

        assert prov.metadata.get("custom") == "data"
        assert prov.metadata.get("count") == 42


# ============================================================================
# EntityProvenanceTracker Tests - Query (6 tests)
# ============================================================================

class TestEntityProvenanceTrackerQuery:
    """Tests for EntityProvenanceTracker query functionality."""

    def setup_method(self):
        """Set up test fixtures with sample data."""
        self.tracker = EntityProvenanceTracker()

        # Create diverse test data
        entities = [
            Entity("Alpha", EntityType.FUNCTION),
            Entity("Beta", EntityType.CLASS),
            Entity("Gamma", EntityType.FUNCTION),
            Entity("Delta", EntityType.CONCEPT),
        ]

        # Entry 1: Alpha (INPUT), Beta (CONTEXT)
        self.tracker.record(entities[0], EntityRole.INPUT, "entry-1")
        self.tracker.record(entities[1], EntityRole.CONTEXT, "entry-1")

        # Entry 2: Beta (INPUT), Gamma (OUTPUT)
        self.tracker.record(entities[1], EntityRole.INPUT, "entry-2")
        self.tracker.record(entities[2], EntityRole.OUTPUT, "entry-2")

        # Entry 3: Delta (SUBJECT)
        self.tracker.record(entities[3], EntityRole.SUBJECT, "entry-3")

    def test_get_entities_by_entry(self):
        """EQ-01: Find all entities for an entry_id."""
        results = self.tracker.get_entities_by_entry("entry-1")
        assert len(results) == 2
        names = {r.entity_name for r in results}
        assert names == {"Alpha", "Beta"}

    def test_get_entities_by_role(self):
        """EQ-02: Filter by EntityRole."""
        results = self.tracker.get_entities_by_role(EntityRole.INPUT)
        assert len(results) == 2
        names = {r.entity_name for r in results}
        assert names == {"Alpha", "Beta"}

    def test_get_entities_by_name(self):
        """EQ-03: Find all entries using entity name."""
        results = self.tracker.get_entities_by_name("Beta")
        assert len(results) == 2

        entry_ids = {r.entry_id for r in results}
        assert entry_ids == {"entry-1", "entry-2"}

    def test_get_entities_by_type(self):
        """EQ-04: Filter by EntityType."""
        results = self.tracker.get_entities_by_type(EntityType.FUNCTION)
        assert len(results) == 2
        names = {r.entity_name for r in results}
        assert names == {"Alpha", "Gamma"}

    def test_get_entities_combined_filter(self):
        """EQ-05: Multiple filter criteria with AND logic."""
        results = self.tracker.get_entities(
            entity_type=EntityType.CLASS,
            role=EntityRole.CONTEXT,
        )
        assert len(results) == 1
        assert results[0].entity_name == "Beta"
        assert results[0].entry_id == "entry-1"

    def test_get_entities_empty_result(self):
        """EQ-06: Query with no matches."""
        results = self.tracker.get_entities_by_entry("nonexistent-entry")
        assert results == []

        results = self.tracker.get_entities_by_name("NonexistentEntity")
        assert results == []


# ============================================================================
# EntityProvenanceTracker Tests - Timeline (4 tests)
# ============================================================================

class TestEntityProvenanceTrackerTimeline:
    """Tests for EntityProvenanceTracker timeline functionality."""

    def setup_method(self):
        """Set up test fixtures with temporal data."""
        self.tracker = EntityProvenanceTracker()
        self.base_time = utc_now()

    def test_get_entity_timeline(self):
        """TL-01: Get all appearances of entity over time."""
        entity = Entity("TrackMe", EntityType.CONCEPT)

        # Record at different "times" (simulated via different entries)
        for i in range(3):
            self.tracker.record(entity, EntityRole.INPUT, f"entry-{i}")

        timeline = self.tracker.get_entity_timeline("TrackMe")
        assert len(timeline) == 3
        # Should be chronologically ordered
        for i in range(len(timeline) - 1):
            assert timeline[i].recorded_at <= timeline[i + 1].recorded_at

    def test_timeline_with_date_range(self):
        """TL-02: Filter timeline by date range."""
        entity = Entity("RangeEntity", EntityType.FUNCTION)

        # Create entries
        for i in range(5):
            self.tracker.record(entity, EntityRole.INPUT, f"entry-{i}")

        all_records = self.tracker.get_entity_timeline("RangeEntity")
        assert len(all_records) >= 5

        # Filter by range (should get some subset)
        start = self.base_time - timedelta(minutes=1)
        end = self.base_time + timedelta(minutes=1)
        filtered = self.tracker.get_entity_timeline(
            "RangeEntity",
            start_date=start,
            end_date=end,
        )
        # All records should be in range (created just now)
        assert len(filtered) == 5

    def test_timeline_shows_role_changes(self):
        """TL-03: Entity appears as INPUT then OUTPUT."""
        entity = Entity("Transformer", EntityType.CONCEPT)

        self.tracker.record(entity, EntityRole.INPUT, "entry-transform-in")
        self.tracker.record(entity, EntityRole.OUTPUT, "entry-transform-out")

        timeline = self.tracker.get_entity_timeline("Transformer")
        roles = [t.role for t in timeline]

        assert EntityRole.INPUT in roles
        assert EntityRole.OUTPUT in roles

    def test_timeline_tracks_validity_changes(self):
        """TL-04: Temporal validity changes tracked."""
        now = utc_now()

        # First record: valid for 1 day
        entity_v1 = Entity(
            "Evolving",
            EntityType.CLASS,
            valid_from=now,
            valid_to=now + timedelta(days=1),
        )
        self.tracker.record(entity_v1, EntityRole.SUBJECT, "entry-v1")

        # Second record: validity extended
        entity_v2 = Entity(
            "Evolving",
            EntityType.CLASS,
            valid_from=now,
            valid_to=now + timedelta(days=30),
        )
        self.tracker.record(entity_v2, EntityRole.SUBJECT, "entry-v2")

        timeline = self.tracker.get_entity_timeline("Evolving")
        assert len(timeline) == 2

        # Check that different valid_to values are captured
        valid_to_values = [t.valid_to for t in timeline]
        assert now + timedelta(days=1) in valid_to_values
        assert now + timedelta(days=30) in valid_to_values


# ============================================================================
# EntityProvenanceTracker Tests - Trace (3 tests)
# ============================================================================

class TestEntityProvenanceTrackerTrace:
    """Tests for EntityProvenanceTracker trace functionality."""

    def setup_method(self):
        """Set up test fixtures with audit chain."""
        self.storage = MemoryStorageBackend()
        self.manager = AuditTrailManager(self.storage)
        self.tracker = EntityProvenanceTracker(manager=self.manager)

    def test_trace_entity_to_source(self):
        """TR-01: Trace entity back through decision chain."""
        # Create chain: entry1 -> entry2 -> entry3
        entry1 = self.manager.record(
            decision_type=DecisionType.TASK_ROUTING,
            agent_id="orchestrator",
            inputs={"task": "research"},
            outputs={"selected": "researcher"},
        )
        entity = Entity("TracedEntity", EntityType.CONCEPT)
        self.tracker.record(entity, EntityRole.INPUT, entry1.entry_id)

        entry2 = self.manager.record(
            decision_type=DecisionType.TOOL_INVOCATION,
            agent_id="researcher",
            inputs={"entity": "TracedEntity"},
            outputs={"result": "data"},
            parent_id=entry1.entry_id,
        )
        self.tracker.record(entity, EntityRole.CONTEXT, entry2.entry_id)

        entry3 = self.manager.record(
            decision_type=DecisionType.OUTPUT_GENERATION,
            agent_id="researcher",
            inputs={"context": "TracedEntity"},
            outputs={"output": "final"},
            parent_id=entry2.entry_id,
        )
        self.tracker.record(entity, EntityRole.OUTPUT, entry3.entry_id)

        # Trace back from entry3
        trace = self.tracker.trace_entity_to_source("TracedEntity", entry3.entry_id)

        # Should find path back to entry1
        assert len(trace) >= 2
        entry_ids = [t.entry_id for t in trace]
        assert entry3.entry_id in entry_ids

    def test_trace_with_max_depth(self):
        """TR-02: Limit trace depth."""
        entity = Entity("DeepEntity", EntityType.FUNCTION)

        # Create deep chain
        parent_id = None
        for i in range(5):
            entry = self.manager.record(
                decision_type=DecisionType.TASK_ROUTING,
                agent_id=f"agent-{i}",
                inputs={"step": i},
                outputs={"done": True},
                parent_id=parent_id,
            )
            self.tracker.record(entity, EntityRole.CONTEXT, entry.entry_id)
            parent_id = entry.entry_id

        # Trace with limited depth
        trace = self.tracker.trace_entity_to_source(
            "DeepEntity",
            parent_id,  # Last entry
            max_depth=2,
        )

        assert len(trace) <= 3  # At most max_depth + 1

    def test_trace_circular_reference(self):
        """TR-03: Handle circular references gracefully."""
        entity = Entity("CircularEntity", EntityType.CONCEPT)

        # Create entries that reference each other (simulated)
        entry1 = self.manager.record(
            decision_type=DecisionType.TASK_ROUTING,
            agent_id="agent-a",
            inputs={},
            outputs={},
        )
        self.tracker.record(entity, EntityRole.INPUT, entry1.entry_id)

        entry2 = self.manager.record(
            decision_type=DecisionType.TASK_ROUTING,
            agent_id="agent-b",
            inputs={},
            outputs={},
            parent_id=entry1.entry_id,
        )
        self.tracker.record(entity, EntityRole.OUTPUT, entry2.entry_id)

        # This should not infinite loop
        trace = self.tracker.trace_entity_to_source(
            "CircularEntity",
            entry2.entry_id,
            max_depth=10,
        )

        # Should complete without error
        assert isinstance(trace, list)


# ============================================================================
# Integration Tests with AuditTrailManager (8 tests)
# ============================================================================

class TestEntityProvenanceIntegration:
    """Integration tests with AuditTrailManager."""

    def setup_method(self):
        """Set up test fixtures."""
        self.storage = MemoryStorageBackend()
        self.manager = AuditTrailManager(self.storage)
        self.tracker = EntityProvenanceTracker(manager=self.manager)

    def test_manager_with_provenance_tracker(self):
        """IN-01: Create tracker attached to manager."""
        assert self.tracker.manager is self.manager

        # Record should work
        entry = self.manager.record(
            decision_type=DecisionType.TASK_ROUTING,
            agent_id="test",
            inputs={},
            outputs={},
        )
        entity = Entity("TestEntity", EntityType.CONCEPT)
        prov = self.tracker.record(entity, EntityRole.INPUT, entry.entry_id)

        assert prov.entry_id == entry.entry_id

    def test_record_decision_with_entities(self):
        """IN-02: Record decision with entity provenance."""
        entry = self.manager.record(
            decision_type=DecisionType.AGENT_SELECTION,
            agent_id="orchestrator",
            inputs={"task": "analyze code"},
            outputs={"selected": "code_analyzer"},
        )

        # Record entities involved
        input_entity = Entity("CodeFile", EntityType.FILE)
        output_entity = Entity("AnalysisResult", EntityType.CONCEPT)

        self.tracker.record(input_entity, EntityRole.INPUT, entry.entry_id)
        self.tracker.record(output_entity, EntityRole.OUTPUT, entry.entry_id)

        # Verify linkage
        results = self.tracker.get_entities_by_entry(entry.entry_id)
        assert len(results) == 2

    def test_entity_input_output_flow(self):
        """IN-03: Entity as INPUT becomes OUTPUT."""
        # Entry 1: Entity is INPUT
        entry1 = self.manager.record(
            decision_type=DecisionType.TASK_ROUTING,
            agent_id="router",
            inputs={"entity": "DataModel"},
            outputs={"route": "processor"},
        )
        entity = Entity("DataModel", EntityType.CLASS)
        self.tracker.record(entity, EntityRole.INPUT, entry1.entry_id)

        # Entry 2: Same entity is OUTPUT (after processing)
        entry2 = self.manager.record(
            decision_type=DecisionType.OUTPUT_GENERATION,
            agent_id="processor",
            inputs={"input": "DataModel"},
            outputs={"result": "ProcessedDataModel"},
            parent_id=entry1.entry_id,
        )
        self.tracker.record(entity, EntityRole.OUTPUT, entry2.entry_id)

        # Verify provenance chain
        timeline = self.tracker.get_entity_timeline("DataModel")
        assert len(timeline) == 2

        roles = [t.role for t in timeline]
        assert EntityRole.INPUT in roles
        assert EntityRole.OUTPUT in roles

    def test_tool_invocation_entities(self):
        """IN-04: Tool call records entity context."""
        entry = self.manager.record_tool_invocation(
            agent_id="code_analyzer",
            tool_name="read_file",
            tool_input={"path": "src/main.py"},
            tool_output={"content": "..."},
        )

        # Record the file entity
        file_entity = Entity(
            "main.py",
            EntityType.FILE,
            source_location="src/main.py",
        )
        self.tracker.record(file_entity, EntityRole.SUBJECT, entry.entry_id)

        results = self.tracker.get_entities_by_entry(entry.entry_id)
        assert len(results) == 1
        assert results[0].source_location == "src/main.py"

    def test_verification_entity_tracking(self):
        """IN-05: Verified content tracks entities."""
        entry = self.manager.record_verification(
            verifier_id="validator",
            content_hash="abc123",
            verdict="approved",
            score=0.95,
            reasoning="Valid code structure",
        )

        # Track what was verified
        verified_entity = Entity("UserAuth", EntityType.MODULE)
        self.tracker.record(verified_entity, EntityRole.SUBJECT, entry.entry_id)

        results = self.tracker.get_entities_by_role(EntityRole.SUBJECT)
        assert any(r.entity_name == "UserAuth" for r in results)

    def test_provenance_in_compliance_report(self):
        """IN-06: Entity stats available for compliance."""
        # Record several decisions with entities
        for i in range(5):
            entry = self.manager.record(
                decision_type=DecisionType.TASK_ROUTING,
                agent_id=f"agent-{i}",
                inputs={},
                outputs={},
            )
            entity = Entity(f"Entity{i}", EntityType.CONCEPT)
            self.tracker.record(entity, EntityRole.INPUT, entry.entry_id)

        stats = self.tracker.get_statistics()
        assert stats["total_provenance_records"] == 5
        assert stats["unique_entities"] >= 1

    def test_entity_integrity_verification(self):
        """IN-07: Verify entity provenance chain."""
        entry = self.manager.record(
            decision_type=DecisionType.TASK_ROUTING,
            agent_id="test",
            inputs={},
            outputs={},
        )
        entity = Entity("IntegrityTest", EntityType.FUNCTION)
        self.tracker.record(entity, EntityRole.INPUT, entry.entry_id)

        # Verify chain
        report = self.manager.verify_integrity()
        assert report.verified

        # Provenance should also be verifiable
        prov_valid = self.tracker.verify_integrity()
        assert prov_valid

    def test_full_workflow_with_entities(self):
        """IN-08: Complete workflow with entity tracking."""
        # Step 1: Task routing with input entity
        task_entry = self.manager.record(
            decision_type=DecisionType.TASK_ROUTING,
            agent_id="orchestrator",
            inputs={"query": "analyze function"},
            outputs={"route": "code_analyzer"},
        )
        query_entity = Entity("analyze_function_query", EntityType.CONCEPT)
        self.tracker.record(query_entity, EntityRole.INPUT, task_entry.entry_id)

        # Step 2: Tool invocation
        tool_entry = self.manager.record_tool_invocation(
            agent_id="code_analyzer",
            tool_name="find_function",
            tool_input={"name": "calculate"},
            tool_output={"location": "math.py:10"},
            parent_id=task_entry.entry_id,
        )
        func_entity = Entity(
            "calculate",
            EntityType.FUNCTION,
            source_location="math.py:10",
        )
        self.tracker.record(func_entity, EntityRole.SUBJECT, tool_entry.entry_id)

        # Step 3: Output generation
        output_entry = self.manager.record(
            decision_type=DecisionType.OUTPUT_GENERATION,
            agent_id="code_analyzer",
            inputs={"function": "calculate"},
            outputs={"analysis": "Pure function with 2 params"},
            parent_id=tool_entry.entry_id,
        )
        self.tracker.record(func_entity, EntityRole.OUTPUT, output_entry.entry_id)

        # Step 4: Verification
        verify_entry = self.manager.record_verification(
            verifier_id="validator",
            content_hash="xyz789",
            verdict="approved",
            score=0.98,
            reasoning="Analysis is accurate",
            parent_id=output_entry.entry_id,
        )
        self.tracker.record(func_entity, EntityRole.SUBJECT, verify_entry.entry_id)

        # Verify complete workflow
        func_timeline = self.tracker.get_entity_timeline("calculate")
        assert len(func_timeline) == 3

        # Verify audit integrity
        report = self.manager.verify_integrity()
        assert report.verified
        assert report.entries_checked == 4


# ============================================================================
# Edge Cases and Error Handling (6 tests)
# ============================================================================

class TestEntityProvenanceEdgeCases:
    """Tests for edge cases and error handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tracker = EntityProvenanceTracker()

    def test_empty_entity_name(self):
        """EC-01: Record entity with empty name raises ValueError."""
        entity = Entity("", EntityType.CONCEPT)
        with pytest.raises(ValueError, match="entity.*name"):
            self.tracker.record(entity, EntityRole.INPUT, "entry-123")

    def test_empty_entry_id(self):
        """EC-01b: Record with empty entry_id raises ValueError."""
        entity = Entity("ValidEntity", EntityType.CONCEPT)
        with pytest.raises(ValueError, match="entry_id"):
            self.tracker.record(entity, EntityRole.INPUT, "")
        with pytest.raises(ValueError, match="entry_id"):
            self.tracker.record(entity, EntityRole.INPUT, "   ")

    def test_invalid_entry_id(self):
        """EC-02: Query with non-existent entry_id returns empty list."""
        results = self.tracker.get_entities_by_entry("nonexistent-entry-id")
        assert results == []

    def test_none_entity(self):
        """EC-03: Pass None to record raises TypeError."""
        with pytest.raises(TypeError):
            self.tracker.record(None, EntityRole.INPUT, "entry-123")

    def test_timezone_handling(self):
        """EC-04: Mix of aware/naive datetimes handled consistently."""
        # Entity with naive datetime
        naive_dt = datetime(2024, 1, 1, 12, 0, 0)
        entity = Entity(
            "NaiveEntity",
            EntityType.CONCEPT,
            valid_from=naive_dt,
        )
        prov = self.tracker.record(entity, EntityRole.INPUT, "entry-tz")

        # Should be stored consistently (as UTC)
        assert prov.valid_from is not None
        # Either has tzinfo or is normalized
        if prov.valid_from.tzinfo is not None:
            assert prov.valid_from.tzinfo == timezone.utc

    def test_large_metadata(self):
        """EC-05: Record with very large metadata handled gracefully."""
        entity = Entity("BigMetaEntity", EntityType.CONCEPT)
        large_metadata = {
            f"key_{i}": f"value_{i}" * 100
            for i in range(100)
        }

        # Should not raise
        prov = self.tracker.record(
            entity=entity,
            role=EntityRole.INPUT,
            entry_id="entry-big",
            metadata=large_metadata,
        )

        assert len(prov.metadata) == 100

    def test_special_characters_in_name(self):
        """EC-06: Entity names with unicode/special chars stored correctly."""
        special_names = [
            "Entity with spaces",
            "Entity\twith\ttabs",
            "Entity/with/slashes",
            "Entity<with>brackets",
            "Unicode: \u00e9\u00e8\u00ea",
            "Emoji: \U0001F600",
            "Japanese: \u65e5\u672c\u8a9e",
        ]

        for name in special_names:
            entity = Entity(name, EntityType.CONCEPT)
            prov = self.tracker.record(
                entity=entity,
                role=EntityRole.INPUT,
                entry_id=f"entry-{hash(name)}",
            )
            assert prov.entity_name == name

            # Roundtrip through dict
            d = prov.to_dict()
            restored = EntityProvenance.from_dict(d)
            assert restored.entity_name == name


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
