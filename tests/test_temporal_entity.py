"""
Tests for KG-001/002: Temporal Entity Extensions.

Tests EntityType code entity additions and Entity temporal validity fields.
These tests are LOCKED after approval - implementation must pass all tests.

Version: 2.6.0
"""

import os
import tempfile
import pytest
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from src.knowledge.graph import EntityType, Entity, KGClaim
from src.knowledge.storage import SQLiteGraphBackend


# =============================================================================
# Test Category 1: EntityType Extensions (KG-001)
# =============================================================================

class TestEntityTypeExtensions:
    """Tests for new code-related EntityType values."""

    def test_entity_type_file_exists(self):
        """T1.1: EntityType.FILE has value 'file'."""
        assert EntityType.FILE.value == "file"

    def test_entity_type_function_exists(self):
        """T1.2: EntityType.FUNCTION has value 'function'."""
        assert EntityType.FUNCTION.value == "function"

    def test_entity_type_class_exists(self):
        """T1.3: EntityType.CLASS has value 'class'."""
        assert EntityType.CLASS.value == "class"

    def test_entity_type_module_exists(self):
        """T1.4: EntityType.MODULE has value 'module'."""
        assert EntityType.MODULE.value == "module"

    def test_entity_type_variable_exists(self):
        """T1.5: EntityType.VARIABLE has value 'variable'."""
        assert EntityType.VARIABLE.value == "variable"

    def test_entity_type_dependency_exists(self):
        """T1.6: EntityType.DEPENDENCY has value 'dependency'."""
        assert EntityType.DEPENDENCY.value == "dependency"

    def test_existing_entity_types_preserved(self):
        """T1.7: Original EntityType values still exist and are unchanged."""
        assert EntityType.PERSON.value == "person"
        assert EntityType.ORGANIZATION.value == "organization"
        assert EntityType.LOCATION.value == "location"
        assert EntityType.DATE.value == "date"
        assert EntityType.CONCEPT.value == "concept"
        assert EntityType.TECHNOLOGY.value == "technology"
        assert EntityType.PRODUCT.value == "product"
        assert EntityType.EVENT.value == "event"
        assert EntityType.METRIC.value == "metric"
        assert EntityType.OTHER.value == "other"

    def test_entity_type_is_str_enum(self):
        """T1.8: EntityType inherits from str for JSON serialization."""
        assert isinstance(EntityType.FILE, str)
        assert isinstance(EntityType.FUNCTION, str)
        assert isinstance(EntityType.CLASS, str)
        # Can be used directly as string
        assert EntityType.FILE == "file"
        assert EntityType.MODULE == "module"


# =============================================================================
# Test Category 2: Entity Temporal Fields (KG-002)
# =============================================================================

class TestEntityTemporalFields:
    """Tests for Entity temporal validity fields."""

    def test_entity_valid_from_optional_default_none(self):
        """T2.1: valid_from defaults to None."""
        entity = Entity(name="test_func", entity_type=EntityType.FUNCTION)
        assert entity.valid_from is None

    def test_entity_valid_to_optional_default_none(self):
        """T2.2: valid_to defaults to None."""
        entity = Entity(name="test_func", entity_type=EntityType.FUNCTION)
        assert entity.valid_to is None

    def test_entity_source_location_optional_default_none(self):
        """T2.3: source_location defaults to None."""
        entity = Entity(name="test_func", entity_type=EntityType.FUNCTION)
        assert entity.source_location is None

    def test_entity_with_temporal_bounds(self):
        """T2.4: Entity accepts valid_from/valid_to datetimes."""
        now = datetime.now(timezone.utc)
        later = now + timedelta(days=30)

        entity = Entity(
            name="MyClass",
            entity_type=EntityType.CLASS,
            valid_from=now,
            valid_to=later,
        )

        assert entity.valid_from == now
        assert entity.valid_to == later

    def test_entity_with_source_location(self):
        """T2.5: Entity accepts source_location string."""
        entity = Entity(
            name="process_data",
            entity_type=EntityType.FUNCTION,
            source_location="src/utils/helpers.py:42",
        )

        assert entity.source_location == "src/utils/helpers.py:42"

    def test_entity_backward_compatible(self):
        """T2.6: Existing Entity usage without new fields works."""
        # Old-style entity creation should still work
        entity = Entity(
            name="Python",
            entity_type=EntityType.TECHNOLOGY,
            metadata={"version": "3.11"},
        )

        assert entity.name == "Python"
        assert entity.entity_type == EntityType.TECHNOLOGY
        assert entity.metadata == {"version": "3.11"}
        # New fields default to None
        assert entity.valid_from is None
        assert entity.valid_to is None
        assert entity.source_location is None


# =============================================================================
# Test Category 3: Entity.is_valid() Method
# =============================================================================

class TestEntityIsValid:
    """Tests for Entity.is_valid() temporal validation method."""

    def test_is_valid_no_bounds_returns_true(self):
        """T3.1: Entity with no temporal bounds is always valid."""
        entity = Entity(name="eternal_concept", entity_type=EntityType.CONCEPT)
        assert entity.is_valid() is True

    def test_is_valid_within_bounds_returns_true(self):
        """T3.2: Entity within [valid_from, valid_to] is valid."""
        now = datetime.now(timezone.utc)
        entity = Entity(
            name="active_module",
            entity_type=EntityType.MODULE,
            valid_from=now - timedelta(days=10),
            valid_to=now + timedelta(days=10),
        )

        assert entity.is_valid(as_of=now) is True

    def test_is_valid_before_valid_from_returns_false(self):
        """T3.3: Query before valid_from returns False."""
        now = datetime.now(timezone.utc)
        entity = Entity(
            name="future_feature",
            entity_type=EntityType.FUNCTION,
            valid_from=now + timedelta(days=5),
            valid_to=now + timedelta(days=30),
        )

        assert entity.is_valid(as_of=now) is False

    def test_is_valid_after_valid_to_returns_false(self):
        """T3.4: Query after valid_to returns False."""
        now = datetime.now(timezone.utc)
        entity = Entity(
            name="deprecated_class",
            entity_type=EntityType.CLASS,
            valid_from=now - timedelta(days=30),
            valid_to=now - timedelta(days=5),
        )

        assert entity.is_valid(as_of=now) is False

    def test_is_valid_only_valid_from_set(self):
        """T3.5: valid_from set, valid_to=None, respects lower bound only."""
        now = datetime.now(timezone.utc)
        entity = Entity(
            name="introduced_function",
            entity_type=EntityType.FUNCTION,
            valid_from=now - timedelta(days=5),
            valid_to=None,
        )

        # After valid_from: valid
        assert entity.is_valid(as_of=now) is True
        # Before valid_from: invalid
        assert entity.is_valid(as_of=now - timedelta(days=10)) is False

    def test_is_valid_only_valid_to_set(self):
        """T3.6: valid_to set, valid_from=None, respects upper bound only."""
        now = datetime.now(timezone.utc)
        entity = Entity(
            name="sunset_variable",
            entity_type=EntityType.VARIABLE,
            valid_from=None,
            valid_to=now + timedelta(days=5),
        )

        # Before valid_to: valid
        assert entity.is_valid(as_of=now) is True
        # After valid_to: invalid
        assert entity.is_valid(as_of=now + timedelta(days=10)) is False

    def test_is_valid_default_uses_current_time(self):
        """T3.7: as_of=None uses current UTC time."""
        now = datetime.now(timezone.utc)
        entity = Entity(
            name="current_entity",
            entity_type=EntityType.MODULE,
            valid_from=now - timedelta(days=1),
            valid_to=now + timedelta(days=1),
        )

        # Default should use current time (within bounds)
        assert entity.is_valid() is True

    def test_is_valid_explicit_as_of_datetime(self):
        """T3.8: Explicit as_of datetime is respected."""
        now = datetime.now(timezone.utc)
        past = now - timedelta(days=100)
        future = now + timedelta(days=100)

        entity = Entity(
            name="bounded_entity",
            entity_type=EntityType.FILE,
            valid_from=now - timedelta(days=50),
            valid_to=now + timedelta(days=50),
        )

        assert entity.is_valid(as_of=past) is False
        assert entity.is_valid(as_of=now) is True
        assert entity.is_valid(as_of=future) is False

    def test_is_valid_at_exact_boundary_valid_from(self):
        """T3.9: Query at exact valid_from is valid (inclusive)."""
        boundary = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        entity = Entity(
            name="boundary_test",
            entity_type=EntityType.DEPENDENCY,
            valid_from=boundary,
            valid_to=boundary + timedelta(days=30),
        )

        assert entity.is_valid(as_of=boundary) is True

    def test_is_valid_at_exact_boundary_valid_to(self):
        """T3.10: Query at exact valid_to is valid (inclusive)."""
        boundary = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        entity = Entity(
            name="boundary_test",
            entity_type=EntityType.DEPENDENCY,
            valid_from=boundary - timedelta(days=30),
            valid_to=boundary,
        )

        assert entity.is_valid(as_of=boundary) is True


# =============================================================================
# Test Category 4: Entity Serialization (to_dict/from_dict)
# =============================================================================

class TestEntitySerialization:
    """Tests for Entity to_dict/from_dict with temporal fields."""

    def test_to_dict_includes_valid_from(self):
        """T4.1: to_dict outputs valid_from as ISO string."""
        dt = datetime(2024, 6, 15, 12, 30, 0, tzinfo=timezone.utc)
        entity = Entity(
            name="test",
            entity_type=EntityType.FUNCTION,
            valid_from=dt,
        )

        data = entity.to_dict()
        assert data["valid_from"] == "2024-06-15T12:30:00+00:00"

    def test_to_dict_includes_valid_to(self):
        """T4.2: to_dict outputs valid_to as ISO string."""
        dt = datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        entity = Entity(
            name="test",
            entity_type=EntityType.CLASS,
            valid_to=dt,
        )

        data = entity.to_dict()
        assert data["valid_to"] == "2024-12-31T23:59:59+00:00"

    def test_to_dict_includes_source_location(self):
        """T4.3: to_dict outputs source_location."""
        entity = Entity(
            name="MyClass",
            entity_type=EntityType.CLASS,
            source_location="src/models/user.py:15",
        )

        data = entity.to_dict()
        assert data["source_location"] == "src/models/user.py:15"

    def test_to_dict_none_fields_serialized_as_null(self):
        """T4.4: None values serialize as null (None in Python dict)."""
        entity = Entity(name="basic", entity_type=EntityType.OTHER)

        data = entity.to_dict()
        assert data["valid_from"] is None
        assert data["valid_to"] is None
        assert data["source_location"] is None

    def test_from_dict_parses_valid_from(self):
        """T4.5: from_dict parses valid_from ISO string."""
        data = {
            "name": "test_func",
            "type": "function",
            "valid_from": "2024-06-15T12:30:00+00:00",
        }

        entity = Entity.from_dict(data)
        expected = datetime(2024, 6, 15, 12, 30, 0, tzinfo=timezone.utc)
        assert entity.valid_from == expected

    def test_from_dict_parses_valid_to(self):
        """T4.6: from_dict parses valid_to ISO string."""
        data = {
            "name": "old_class",
            "type": "class",
            "valid_to": "2024-12-31T23:59:59+00:00",
        }

        entity = Entity.from_dict(data)
        expected = datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        assert entity.valid_to == expected

    def test_from_dict_parses_source_location(self):
        """T4.7: from_dict parses source_location."""
        data = {
            "name": "helper",
            "type": "function",
            "source_location": "lib/utils.py:100",
        }

        entity = Entity.from_dict(data)
        assert entity.source_location == "lib/utils.py:100"

    def test_from_dict_missing_temporal_fields_default_none(self):
        """T4.8: Missing temporal fields default to None."""
        data = {
            "name": "legacy_entity",
            "type": "concept",
        }

        entity = Entity.from_dict(data)
        assert entity.valid_from is None
        assert entity.valid_to is None
        assert entity.source_location is None

    def test_roundtrip_serialization(self):
        """T4.9: to_dict -> from_dict preserves all fields."""
        now = datetime.now(timezone.utc)
        original = Entity(
            name="RoundtripClass",
            entity_type=EntityType.CLASS,
            valid_from=now - timedelta(days=10),
            valid_to=now + timedelta(days=90),
            source_location="src/core/engine.py:256",
            metadata={"author": "test", "lines": 150},
        )

        data = original.to_dict()
        restored = Entity.from_dict(data)

        assert restored.name == original.name
        assert restored.entity_type == original.entity_type
        assert restored.valid_from == original.valid_from
        assert restored.valid_to == original.valid_to
        assert restored.source_location == original.source_location
        assert restored.metadata == original.metadata

    def test_from_dict_backward_compatible(self):
        """T4.10: Old dict format (no temporal fields) still works."""
        # This is the old format without temporal fields
        old_format = {
            "name": "Python",
            "type": "technology",
            "metadata": {"version": "3.11"},
        }

        entity = Entity.from_dict(old_format)
        assert entity.name == "Python"
        assert entity.entity_type == EntityType.TECHNOLOGY
        assert entity.metadata == {"version": "3.11"}
        # New fields default to None
        assert entity.valid_from is None
        assert entity.valid_to is None
        assert entity.source_location is None


# =============================================================================
# Test Category 5: Integration with KGClaim
# =============================================================================

class TestTimezoneHandling:
    """Tests for timezone-aware and naive datetime handling."""

    def test_is_valid_with_naive_as_of(self):
        """T-TZ1: Timezone-naive as_of treated as UTC."""
        # Create entity with timezone-aware bounds
        entity = Entity(
            name="tz_test",
            entity_type=EntityType.FUNCTION,
            valid_from=datetime(2024, 6, 1, 0, 0, 0, tzinfo=timezone.utc),
            valid_to=datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
        )

        # Pass timezone-naive datetime (should be treated as UTC)
        naive_dt = datetime(2024, 6, 15, 12, 0, 0)  # No tzinfo
        assert entity.is_valid(as_of=naive_dt) is True

        # Before range - should be False
        naive_before = datetime(2024, 5, 1, 0, 0, 0)
        assert entity.is_valid(as_of=naive_before) is False

    def test_is_valid_with_naive_bounds(self):
        """T-TZ2: Timezone-naive bounds treated as UTC."""
        # Create entity with timezone-naive bounds
        entity = Entity(
            name="naive_bounds",
            entity_type=EntityType.CLASS,
            valid_from=datetime(2024, 6, 1, 0, 0, 0),  # Naive
            valid_to=datetime(2024, 12, 31, 23, 59, 59),  # Naive
        )

        # Pass timezone-aware datetime
        aware_dt = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        assert entity.is_valid(as_of=aware_dt) is True

    def test_is_valid_mixed_timezones_no_error(self):
        """T-TZ3: Mixed naive/aware datetimes don't raise TypeError."""
        entity = Entity(
            name="mixed_tz",
            entity_type=EntityType.MODULE,
            valid_from=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            valid_to=datetime(2024, 12, 31, 23, 59, 59),  # Naive
        )

        # This should not raise TypeError
        naive_dt = datetime(2024, 6, 15, 12, 0, 0)
        result = entity.is_valid(as_of=naive_dt)
        assert isinstance(result, bool)


class TestKGClaimIntegration:
    """Tests for Entity temporal extensions within KGClaim."""

    def test_kgclaim_with_temporal_entities(self):
        """T5.1: KGClaim can contain entities with temporal bounds."""
        now = datetime.now(timezone.utc)

        entities = [
            Entity(
                name="UserService",
                entity_type=EntityType.CLASS,
                valid_from=now - timedelta(days=30),
                valid_to=now + timedelta(days=365),
                source_location="src/services/user.py:10",
            ),
            Entity(
                name="authenticate",
                entity_type=EntityType.FUNCTION,
                valid_from=now - timedelta(days=30),
                source_location="src/services/user.py:45",
            ),
        ]

        claim = KGClaim(
            text="UserService provides authentication via authenticate()",
            confidence=0.9,
            source_url="https://docs.example.com/api",
            entities=entities,
        )

        assert len(claim.entities) == 2
        assert claim.entities[0].valid_from is not None
        assert claim.entities[0].source_location == "src/services/user.py:10"
        assert claim.entities[1].entity_type == EntityType.FUNCTION

    def test_kgclaim_serialization_preserves_temporal(self):
        """T5.2: KGClaim to_dict/from_dict preserves entity temporal data."""
        now = datetime.now(timezone.utc)

        entity = Entity(
            name="DataProcessor",
            entity_type=EntityType.MODULE,
            valid_from=now - timedelta(days=60),
            valid_to=now + timedelta(days=300),
            source_location="src/processing/__init__.py:1",
        )

        original_claim = KGClaim(
            text="DataProcessor handles all ETL operations",
            confidence=0.85,
            source_url="https://docs.example.com/etl",
            entities=[entity],
        )

        # Serialize and deserialize
        data = original_claim.to_dict()
        restored_claim = KGClaim.from_dict(data)

        # Verify entity temporal data preserved
        restored_entity = restored_claim.entities[0]
        assert restored_entity.name == "DataProcessor"
        assert restored_entity.entity_type == EntityType.MODULE
        assert restored_entity.valid_from == entity.valid_from
        assert restored_entity.valid_to == entity.valid_to
        assert restored_entity.source_location == "src/processing/__init__.py:1"

    def test_code_entity_types_in_kgclaim(self):
        """T5.3: KGClaim entities can use new code EntityTypes."""
        entities = [
            Entity(name="config.py", entity_type=EntityType.FILE),
            Entity(name="process_data", entity_type=EntityType.FUNCTION),
            Entity(name="DataModel", entity_type=EntityType.CLASS),
            Entity(name="utils", entity_type=EntityType.MODULE),
            Entity(name="MAX_RETRIES", entity_type=EntityType.VARIABLE),
            Entity(name="requests", entity_type=EntityType.DEPENDENCY),
        ]

        claim = KGClaim(
            text="Code analysis extracted multiple entity types",
            confidence=0.95,
            source_url="file://src/analyzer.py",
            entities=entities,
        )

        # Verify all new types work
        types_found = {e.entity_type for e in claim.entities}
        assert EntityType.FILE in types_found
        assert EntityType.FUNCTION in types_found
        assert EntityType.CLASS in types_found
        assert EntityType.MODULE in types_found
        assert EntityType.VARIABLE in types_found
        assert EntityType.DEPENDENCY in types_found

        # Verify serialization works
        data = claim.to_dict()
        entity_types_in_dict = [e["type"] for e in data["entities"]]
        assert "file" in entity_types_in_dict
        assert "function" in entity_types_in_dict
        assert "class" in entity_types_in_dict
        assert "module" in entity_types_in_dict
        assert "variable" in entity_types_in_dict
        assert "dependency" in entity_types_in_dict


# =============================================================================
# Test Category 6: SQLite Persistence (Critic-identified gap)
# =============================================================================

class TestSQLitePersistence:
    """Tests for SQLite backend temporal field persistence."""

    @pytest.fixture
    def sqlite_backend(self):
        """Create a temporary SQLite backend for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        backend = SQLiteGraphBackend(db_path)
        yield backend
        backend.close()

        # Cleanup
        try:
            os.unlink(db_path)
        except OSError:
            pass

    def test_sqlite_temporal_entity_roundtrip(self, sqlite_backend):
        """T6.1: Temporal fields survive SQLite store/retrieve cycle."""
        now = datetime.now(timezone.utc)

        entity = Entity(
            name="PersistentClass",
            entity_type=EntityType.CLASS,
            valid_from=now - timedelta(days=30),
            valid_to=now + timedelta(days=365),
            source_location="src/models/persistent.py:25",
            metadata={"author": "test"},
        )

        claim = KGClaim(
            text="PersistentClass handles data persistence",
            confidence=0.9,
            source_url="https://docs.example.com/persistence",
            entities=[entity],
        )

        # Store and retrieve
        sqlite_backend.store_claim(claim)
        retrieved = sqlite_backend.get_claim(claim.claim_id)

        assert retrieved is not None
        assert len(retrieved.entities) == 1

        retrieved_entity = retrieved.entities[0]
        assert retrieved_entity.name == "PersistentClass"
        assert retrieved_entity.entity_type == EntityType.CLASS
        assert retrieved_entity.valid_from == entity.valid_from
        assert retrieved_entity.valid_to == entity.valid_to
        assert retrieved_entity.source_location == "src/models/persistent.py:25"

    def test_sqlite_code_entity_types(self, sqlite_backend):
        """T6.2: New code EntityTypes persist in SQLite."""
        entities = [
            Entity(name="main.py", entity_type=EntityType.FILE),
            Entity(name="process", entity_type=EntityType.FUNCTION),
            Entity(name="Handler", entity_type=EntityType.CLASS),
            Entity(name="core", entity_type=EntityType.MODULE),
            Entity(name="CONFIG", entity_type=EntityType.VARIABLE),
            Entity(name="numpy", entity_type=EntityType.DEPENDENCY),
        ]

        claim = KGClaim(
            text="Code entities test",
            confidence=0.95,
            source_url="file://test.py",
            entities=entities,
        )

        sqlite_backend.store_claim(claim)
        retrieved = sqlite_backend.get_claim(claim.claim_id)

        assert retrieved is not None
        types = {e.entity_type for e in retrieved.entities}
        assert EntityType.FILE in types
        assert EntityType.FUNCTION in types
        assert EntityType.CLASS in types
        assert EntityType.MODULE in types
        assert EntityType.VARIABLE in types
        assert EntityType.DEPENDENCY in types

    def test_sqlite_null_temporal_fields(self, sqlite_backend):
        """T6.3: Null temporal fields handled correctly in SQLite."""
        entity = Entity(
            name="NoTemporalBounds",
            entity_type=EntityType.CONCEPT,
            # valid_from, valid_to, source_location all None
        )

        claim = KGClaim(
            text="Entity without temporal bounds",
            confidence=0.8,
            source_url="https://example.com",
            entities=[entity],
        )

        sqlite_backend.store_claim(claim)
        retrieved = sqlite_backend.get_claim(claim.claim_id)

        assert retrieved is not None
        assert len(retrieved.entities) == 1

        retrieved_entity = retrieved.entities[0]
        assert retrieved_entity.valid_from is None
        assert retrieved_entity.valid_to is None
        assert retrieved_entity.source_location is None
