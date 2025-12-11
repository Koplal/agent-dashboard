#!/usr/bin/env python3
"""
Unit tests for validation.py - Base validation classes.

Tests cover:
- HandoffSchema validation
- ValidationResult creation
- Finding creation
- Helper functions
"""

import sys
import os
import pytest
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from validation import (
    HandoffSchema,
    ValidationResult,
    ValidationAction,
    ValidationError,
    Finding,
    Confidence,
    AgentTier,
    GateResult,
    create_handoff,
    validate_handoff_dict,
)


# ============================================================================
# FINDING TESTS
# ============================================================================

class TestFinding:
    """Tests for the Finding dataclass."""

    def test_finding_creation(self):
        """Test basic finding creation."""
        finding = Finding(
            finding="Test finding",
            confidence=Confidence.HIGH,
            source="test_source"
        )
        assert finding.finding == "Test finding"
        assert finding.confidence == Confidence.HIGH
        assert finding.source == "test_source"

    def test_finding_to_dict(self):
        """Test finding serialization."""
        finding = Finding(
            finding="Test finding",
            confidence=Confidence.MEDIUM
        )
        d = finding.to_dict()
        assert d["finding"] == "Test finding"
        assert d["confidence"] == "M"
        assert d["source"] is None

    def test_finding_from_dict(self):
        """Test finding deserialization."""
        data = {
            "finding": "Test finding",
            "confidence": "H",
            "source": "test"
        }
        finding = Finding.from_dict(data)
        assert finding.finding == "Test finding"
        assert finding.confidence == Confidence.HIGH
        assert finding.source == "test"


# ============================================================================
# HANDOFF SCHEMA TESTS
# ============================================================================

class TestHandoffSchema:
    """Tests for the HandoffSchema dataclass."""

    def test_handoff_schema_required_fields(self):
        """Test HandoffSchema validates required fields."""
        schema = HandoffSchema(
            task_id="123",
            outcome="Task completed successfully",
            key_findings=[Finding("X discovered", Confidence.HIGH)],
            confidence=Confidence.MEDIUM
        )
        assert schema.is_valid()
        assert schema.task_id == "123"
        assert schema.outcome == "Task completed successfully"
        assert len(schema.key_findings) == 1
        assert schema.confidence == Confidence.MEDIUM

    def test_handoff_schema_missing_task_id(self):
        """Test validation fails with missing task_id."""
        schema = HandoffSchema(
            task_id="",
            outcome="Done",
            key_findings=[Finding("X", Confidence.HIGH)],
            confidence=Confidence.MEDIUM
        )
        assert not schema.is_valid()
        assert "task_id" in schema.get_missing_fields()

    def test_handoff_schema_missing_outcome(self):
        """Test validation fails with missing outcome."""
        schema = HandoffSchema(
            task_id="123",
            outcome="",
            key_findings=[Finding("X", Confidence.HIGH)],
            confidence=Confidence.MEDIUM
        )
        assert not schema.is_valid()
        assert "outcome" in schema.get_missing_fields()

    def test_handoff_schema_missing_findings(self):
        """Test validation fails with empty key_findings."""
        schema = HandoffSchema(
            task_id="123",
            outcome="Done",
            key_findings=[],
            confidence=Confidence.MEDIUM
        )
        assert not schema.is_valid()

    def test_handoff_schema_too_many_findings(self):
        """Test validation fails with more than 5 findings."""
        findings = [Finding(f"Finding {i}", Confidence.HIGH) for i in range(6)]
        schema = HandoffSchema(
            task_id="123",
            outcome="Done",
            key_findings=findings,
            confidence=Confidence.MEDIUM
        )
        assert not schema.is_valid()

    def test_handoff_schema_to_dict(self):
        """Test HandoffSchema serialization."""
        schema = HandoffSchema(
            task_id="123",
            outcome="Done",
            key_findings=[Finding("X", Confidence.HIGH)],
            confidence=Confidence.MEDIUM,
            agent_name="researcher",
            model_tier=AgentTier.HAIKU
        )
        d = schema.to_dict()
        assert d["task_id"] == "123"
        assert d["outcome"] == "Done"
        assert len(d["key_findings"]) == 1
        assert d["confidence"] == "M"
        assert d["agent_name"] == "researcher"
        assert d["model_tier"] == "haiku"

    def test_handoff_schema_from_dict(self):
        """Test HandoffSchema deserialization."""
        data = {
            "task_id": "123",
            "outcome": "Done",
            "key_findings": [{"finding": "X", "confidence": "H"}],
            "confidence": "M",
            "agent_name": "researcher",
            "model_tier": "haiku"
        }
        schema = HandoffSchema.from_dict(data)
        assert schema.task_id == "123"
        assert schema.outcome == "Done"
        assert len(schema.key_findings) == 1
        assert schema.confidence == Confidence.MEDIUM
        assert schema.agent_name == "researcher"
        assert schema.model_tier == AgentTier.HAIKU

    def test_handoff_schema_to_markdown(self):
        """Test HandoffSchema markdown export."""
        schema = HandoffSchema(
            task_id="123",
            outcome="Task completed successfully",
            key_findings=[
                Finding("Found important info", Confidence.HIGH),
                Finding("Secondary finding", Confidence.MEDIUM)
            ],
            confidence=Confidence.MEDIUM,
            agent_name="researcher",
            model_tier=AgentTier.HAIKU,
            duration_seconds=5.5,
            recommendations=["Do X", "Consider Y"],
            gaps=["Unknown Z"]
        )
        md = schema.to_markdown()
        assert "Task Completion: 123" in md
        assert "researcher" in md
        assert "haiku" in md
        assert "Found important info" in md
        assert "Do X" in md
        assert "Unknown Z" in md

    def test_handoff_schema_optional_fields(self):
        """Test HandoffSchema with optional fields."""
        schema = HandoffSchema(
            task_id="123",
            outcome="Done",
            key_findings=[Finding("X", Confidence.HIGH)],
            confidence=Confidence.HIGH,
            sources=["source1", "source2"],
            gaps=["gap1"],
            recommendations=["rec1"],
            token_count=500,
            compression_ratio=10.5
        )
        assert schema.is_valid()
        assert schema.sources == ["source1", "source2"]
        assert schema.gaps == ["gap1"]
        assert schema.recommendations == ["rec1"]
        assert schema.token_count == 500
        assert schema.compression_ratio == 10.5


# ============================================================================
# VALIDATION RESULT TESTS
# ============================================================================

class TestValidationResult:
    """Tests for the ValidationResult dataclass."""

    def test_validation_result_creation(self):
        """Test basic ValidationResult creation."""
        result = ValidationResult(valid=True)
        assert result.valid is True
        assert result.action == ValidationAction.ACCEPT

    def test_validation_result_rejection(self):
        """Test rejection result."""
        result = ValidationResult(
            valid=False,
            action=ValidationAction.REJECT,
            reason="Missing required fields",
            missing={"task_id", "outcome"}
        )
        assert result.valid is False
        assert result.action == ValidationAction.REJECT
        assert "task_id" in result.missing

    def test_validation_result_auto_route(self):
        """Test auto-route result."""
        result = ValidationResult(
            valid=True,
            action=ValidationAction.AUTO_ROUTE,
            routed_to="summarizer"
        )
        assert result.action == ValidationAction.AUTO_ROUTE
        assert result.routed_to == "summarizer"

    def test_validation_result_escalation(self):
        """Test escalation result."""
        result = ValidationResult(
            valid=False,
            action=ValidationAction.ESCALATE,
            escalate_to="orchestrator",
            loop_count=5
        )
        assert result.action == ValidationAction.ESCALATE
        assert result.escalate_to == "orchestrator"
        assert result.loop_count == 5

    def test_validation_result_to_dict(self):
        """Test ValidationResult serialization."""
        result = ValidationResult(
            valid=False,
            action=ValidationAction.REJECT,
            missing={"task_id"}
        )
        d = result.to_dict()
        assert d["valid"] is False
        assert d["action"] == "REJECT"
        assert "task_id" in d["missing"]


# ============================================================================
# GATE RESULT TESTS
# ============================================================================

class TestGateResult:
    """Tests for the GateResult dataclass."""

    def test_gate_result_pass(self):
        """Test passing gate result."""
        result = GateResult(
            action=ValidationAction.ACCEPT,
            tokens=250,
            budget=300,
            ratio=0.83
        )
        assert result.action == ValidationAction.ACCEPT
        assert result.tokens == 250
        assert result.budget == 300

    def test_gate_result_auto_route(self):
        """Test auto-route gate result."""
        result = GateResult(
            action=ValidationAction.AUTO_ROUTE,
            tokens=450,
            budget=300,
            ratio=1.5,
            routed_to="summarizer"
        )
        assert result.action == ValidationAction.AUTO_ROUTE
        assert result.routed_to == "summarizer"

    def test_gate_result_reject(self):
        """Test rejection gate result."""
        result = GateResult(
            action=ValidationAction.REJECT,
            tokens=700,
            budget=300,
            ratio=2.33,
            feedback="Output exceeds 2x budget. Please compress to <300 tokens."
        )
        assert result.action == ValidationAction.REJECT
        assert result.feedback is not None

    def test_gate_result_to_dict(self):
        """Test GateResult serialization."""
        result = GateResult(
            action=ValidationAction.ACCEPT,
            tokens=200,
            budget=300,
            ratio=0.67
        )
        d = result.to_dict()
        assert d["action"] == "ACCEPT"
        assert d["tokens"] == 200
        assert d["budget"] == 300


# ============================================================================
# HELPER FUNCTION TESTS
# ============================================================================

class TestHelperFunctions:
    """Tests for helper functions."""

    def test_create_handoff(self):
        """Test create_handoff helper function."""
        handoff = create_handoff(
            task_id="123",
            outcome="Task done",
            findings=[
                {"finding": "Found X", "confidence": "H"},
                {"finding": "Found Y", "confidence": "M"}
            ],
            confidence="H",
            agent_name="researcher"
        )
        assert handoff.task_id == "123"
        assert handoff.outcome == "Task done"
        assert len(handoff.key_findings) == 2
        assert handoff.confidence == Confidence.HIGH
        assert handoff.agent_name == "researcher"

    def test_validate_handoff_dict_valid(self):
        """Test validating a valid handoff dict."""
        data = {
            "task_id": "123",
            "outcome": "Done",
            "key_findings": [{"finding": "X", "confidence": "H"}],
            "confidence": "M"
        }
        result = validate_handoff_dict(data)
        assert result.valid is True
        assert result.action == ValidationAction.ACCEPT

    def test_validate_handoff_dict_missing_fields(self):
        """Test validating dict with missing fields."""
        data = {
            "task_id": "123"
        }
        result = validate_handoff_dict(data)
        assert result.valid is False
        assert result.action == ValidationAction.REJECT
        assert "outcome" in result.missing
        assert "key_findings" in result.missing

    def test_validate_handoff_dict_invalid_findings(self):
        """Test validating dict with invalid findings."""
        data = {
            "task_id": "123",
            "outcome": "Done",
            "key_findings": "not a list",
            "confidence": "M"
        }
        result = validate_handoff_dict(data)
        assert result.valid is False

    def test_validate_handoff_dict_too_many_findings(self):
        """Test validating dict with too many findings."""
        data = {
            "task_id": "123",
            "outcome": "Done",
            "key_findings": [{"finding": f"F{i}", "confidence": "M"} for i in range(6)],
            "confidence": "M"
        }
        result = validate_handoff_dict(data)
        assert result.valid is False
        assert "1-5 items" in result.reason


# ============================================================================
# ENUM TESTS
# ============================================================================

class TestEnums:
    """Tests for enum classes."""

    def test_validation_action_values(self):
        """Test ValidationAction enum values exist."""
        assert ValidationAction.ACCEPT
        assert ValidationAction.REJECT
        assert ValidationAction.AUTO_ROUTE
        assert ValidationAction.ESCALATE

    def test_confidence_values(self):
        """Test Confidence enum values."""
        assert Confidence.HIGH.value == "H"
        assert Confidence.MEDIUM.value == "M"
        assert Confidence.LOW.value == "L"

    def test_agent_tier_values(self):
        """Test AgentTier enum values."""
        assert AgentTier.OPUS.value == "opus"
        assert AgentTier.SONNET.value == "sonnet"
        assert AgentTier.HAIKU.value == "haiku"


# ============================================================================
# VALIDATION ERROR TESTS
# ============================================================================

class TestValidationError:
    """Tests for ValidationError exception."""

    def test_validation_error_message(self):
        """Test ValidationError with message."""
        error = ValidationError("Test error")
        assert str(error) == "Test error"
        assert error.missing_fields == set()

    def test_validation_error_with_fields(self):
        """Test ValidationError with missing fields."""
        error = ValidationError("Missing fields", {"task_id", "outcome"})
        assert "task_id" in error.missing_fields
        assert "outcome" in error.missing_fields


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
