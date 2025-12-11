#!/usr/bin/env python3
"""
Unit tests for synthesis_validator.py - Synthesis input validation.

Tests cover:
- Required field validation
- Loop counter logic
- Progress threshold behavior
- Escalation handling
- Quality metrics
"""

import sys
import os
import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from synthesis_validator import (
    SynthesisInputValidator,
    SynthesisValidationState,
    QualityMetrics,
    EscalationHandler,
    REQUIRED_FIELDS,
    MAX_LOOPS,
    PROGRESS_THRESHOLD,
    validate_synthesis_input,
    create_valid_synthesis_input,
)
from validation import ValidationAction, HandoffSchema, Finding, Confidence


# ============================================================================
# SYNTHESIS INPUT VALIDATOR TESTS
# ============================================================================

class TestSynthesisInputValidator:
    """Tests for the SynthesisInputValidator class."""

    def test_initialization(self):
        """Test validator initialization."""
        validator = SynthesisInputValidator()
        assert validator.required_fields == set(REQUIRED_FIELDS)
        assert validator.max_loops == MAX_LOOPS
        assert validator.progress_threshold == PROGRESS_THRESHOLD

    def test_get_name(self):
        """Test validator name."""
        validator = SynthesisInputValidator()
        assert validator.get_name() == "SynthesisInputValidator"

    def test_valid_input_passes(self):
        """Test that valid input passes validation."""
        validator = SynthesisInputValidator()
        valid_input = {
            "task_id": "123",
            "outcome": "Task completed successfully",
            "key_findings": [{"finding": "X discovered", "confidence": "H"}],
            "confidence": "M"
        }
        result = validator.validate(valid_input)
        assert result.valid is True
        assert result.action == ValidationAction.ACCEPT

    def test_missing_task_id_fails(self):
        """Test that missing task_id fails."""
        validator = SynthesisInputValidator()
        invalid_input = {
            "outcome": "Done",
            "key_findings": [{"finding": "X", "confidence": "H"}],
            "confidence": "M"
        }
        result = validator.validate(invalid_input)
        assert result.valid is False
        assert result.action == ValidationAction.REJECT
        assert "task_id" in result.missing

    def test_missing_outcome_fails(self):
        """Test that missing outcome fails."""
        validator = SynthesisInputValidator()
        invalid_input = {
            "task_id": "123",
            "key_findings": [{"finding": "X", "confidence": "H"}],
            "confidence": "M"
        }
        result = validator.validate(invalid_input)
        assert result.valid is False
        assert "outcome" in result.missing

    def test_missing_key_findings_fails(self):
        """Test that missing key_findings fails."""
        validator = SynthesisInputValidator()
        invalid_input = {
            "task_id": "123",
            "outcome": "Done",
            "confidence": "M"
        }
        result = validator.validate(invalid_input)
        assert result.valid is False
        assert "key_findings" in result.missing

    def test_empty_key_findings_fails(self):
        """Test that empty key_findings fails."""
        validator = SynthesisInputValidator()
        invalid_input = {
            "task_id": "123",
            "outcome": "Done",
            "key_findings": [],
            "confidence": "M"
        }
        result = validator.validate(invalid_input)
        assert result.valid is False
        assert "key_findings" in result.missing

    def test_missing_confidence_fails(self):
        """Test that missing confidence fails."""
        validator = SynthesisInputValidator()
        invalid_input = {
            "task_id": "123",
            "outcome": "Done",
            "key_findings": [{"finding": "X", "confidence": "H"}]
        }
        result = validator.validate(invalid_input)
        assert result.valid is False
        assert "confidence" in result.missing

    def test_progress_resets_counter(self):
        """Test that progress resets loop counter."""
        validator = SynthesisInputValidator()
        state = SynthesisValidationState()

        # First attempt: missing 4 fields
        input1 = {}
        result1 = validator.validate(input1, state=state)
        assert result1.loop_count == 1

        # Second attempt: still missing 4 fields (no progress)
        result2 = validator.validate(input1, state=state)
        assert result2.loop_count == 2

        # Third attempt: address 2 fields (50% progress)
        input3 = {
            "task_id": "123",
            "outcome": "Done"
        }
        result3 = validator.validate(input3, state=state)
        # Counter should reset due to progress
        assert result3.loop_count == 1

    def test_no_progress_increments_counter(self):
        """Test that no progress increments loop counter."""
        validator = SynthesisInputValidator()
        state = SynthesisValidationState()

        incomplete_input = {"task_id": "123"}

        for i in range(4):
            result = validator.validate(incomplete_input, state=state)
            assert result.loop_count == i + 1

    def test_escalation_after_max_loops(self):
        """Test escalation after maximum loops without progress."""
        validator = SynthesisInputValidator()
        state = SynthesisValidationState()

        incomplete_input = {"task_id": "123"}

        # Run until escalation
        for i in range(MAX_LOOPS - 1):
            result = validator.validate(incomplete_input, state=state)
            assert result.action == ValidationAction.REJECT

        # Next attempt should escalate
        result = validator.validate(incomplete_input, state=state)
        assert result.action == ValidationAction.ESCALATE
        assert result.escalate_to == "orchestrator"
        assert state.escalated is True

    def test_escalation_includes_suggestion(self):
        """Test that escalation includes helpful suggestion."""
        validator = SynthesisInputValidator()
        state = SynthesisValidationState()
        state.loop_count = MAX_LOOPS - 1

        incomplete_input = {"task_id": "123", "outcome": "Partial"}
        result = validator.validate(incomplete_input, state=state)

        assert result.action == ValidationAction.ESCALATE
        assert result.suggestion is not None
        assert "Options" in result.suggestion

    def test_feedback_contains_format(self):
        """Test that rejection feedback contains required format."""
        validator = SynthesisInputValidator()
        invalid_input = {"task_id": "123"}
        result = validator.validate(invalid_input)

        assert result.feedback is not None
        assert "Required Format" in result.feedback
        assert "task_id" in result.feedback

    def test_validate_handoff_schema(self):
        """Test validation of HandoffSchema objects."""
        validator = SynthesisInputValidator()
        handoff = HandoffSchema(
            task_id="123",
            outcome="Done",
            key_findings=[Finding("X", Confidence.HIGH)],
            confidence=Confidence.MEDIUM
        )
        result = validator.validate(handoff)
        assert result.valid is True

    def test_invalid_input_type(self):
        """Test validation of invalid input type."""
        validator = SynthesisInputValidator()
        result = validator.validate("not a dict")
        assert result.valid is False
        assert "dictionary" in result.reason.lower()

    def test_custom_configuration(self):
        """Test validator with custom configuration."""
        custom_fields = {"field1", "field2"}
        validator = SynthesisInputValidator(
            required_fields=custom_fields,
            max_loops=3,
            progress_threshold=0.75,
            escalation_target="custom-handler"
        )
        assert validator.required_fields == custom_fields
        assert validator.max_loops == 3
        assert validator.progress_threshold == 0.75
        assert validator.escalation_target == "custom-handler"


# ============================================================================
# VALIDATION STATE TESTS
# ============================================================================

class TestSynthesisValidationState:
    """Tests for the SynthesisValidationState dataclass."""

    def test_state_initialization(self):
        """Test state initialization."""
        state = SynthesisValidationState()
        assert state.loop_count == 0
        assert len(state.previous_missing) == 0
        assert state.escalated is False

    def test_state_to_dict(self):
        """Test state serialization."""
        state = SynthesisValidationState()
        state.loop_count = 3
        state.previous_missing = {"task_id", "outcome"}
        state.escalated = True

        d = state.to_dict()
        assert d["loop_count"] == 3
        assert set(d["previous_missing"]) == {"task_id", "outcome"}
        assert d["escalated"] is True


# ============================================================================
# QUALITY METRICS TESTS
# ============================================================================

class TestQualityMetrics:
    """Tests for the QualityMetrics dataclass."""

    def test_quality_assessment_high(self):
        """Test high quality assessment."""
        validator = SynthesisInputValidator()
        high_quality = {
            "task_id": "123",
            "outcome": "Comprehensive analysis completed",
            "key_findings": [
                {"finding": "A", "confidence": "H"},
                {"finding": "B", "confidence": "H"},
                {"finding": "C", "confidence": "M"}
            ],
            "confidence": "H",
            "sources": ["source1", "source2"],
            "gaps": ["minor gap"]
        }
        metrics = validator.assess_quality(high_quality)
        assert metrics.completeness == 1.0
        assert metrics.finding_count == 3
        assert metrics.estimated_quality == "high"

    def test_quality_assessment_medium(self):
        """Test medium quality assessment."""
        validator = SynthesisInputValidator()
        medium_quality = {
            "task_id": "123",
            "outcome": "Done",
            "key_findings": [{"finding": "A", "confidence": "M"}],
            "confidence": "M"
        }
        metrics = validator.assess_quality(medium_quality)
        assert metrics.completeness == 1.0
        assert metrics.finding_count == 1
        assert metrics.estimated_quality == "medium"

    def test_quality_assessment_low(self):
        """Test low quality assessment."""
        validator = SynthesisInputValidator()
        low_quality = {
            "task_id": "123"
        }
        metrics = validator.assess_quality(low_quality)
        assert metrics.completeness < 1.0
        assert metrics.estimated_quality == "low"

    def test_quality_metrics_to_dict(self):
        """Test quality metrics serialization."""
        metrics = QualityMetrics(
            completeness=0.75,
            finding_count=2,
            has_confidence=True,
            estimated_quality="medium"
        )
        d = metrics.to_dict()
        assert d["completeness"] == 0.75
        assert d["finding_count"] == 2
        assert d["estimated_quality"] == "medium"


# ============================================================================
# ESCALATION HANDLER TESTS
# ============================================================================

class TestEscalationHandler:
    """Tests for the EscalationHandler class."""

    def test_initialization(self):
        """Test handler initialization."""
        handler = EscalationHandler()
        assert handler.default_target == "orchestrator"
        assert len(handler.escalation_log) == 0

    def test_handle_escalation(self):
        """Test handling an escalation."""
        handler = EscalationHandler()
        validator = SynthesisInputValidator()

        # Create an escalation scenario
        state = SynthesisValidationState()
        state.loop_count = MAX_LOOPS - 1

        result = validator.validate({"task_id": "123"}, state=state)
        assert result.action == ValidationAction.ESCALATE

        context = handler.handle_escalation(
            result,
            original_input={"task_id": "123"},
            source_agent="researcher"
        )

        assert context["type"] == "synthesis_validation_escalation"
        assert context["target"] == "orchestrator"
        assert context["source_agent"] == "researcher"
        assert len(context["options"]) == 4

    def test_proceed_with_gaps(self):
        """Test proceeding with documented gaps."""
        handler = EscalationHandler()
        original = {"task_id": "123"}
        missing = {"outcome", "key_findings", "confidence"}

        modified = handler.proceed_with_gaps(original, missing)

        assert modified["task_id"] == "123"
        assert "[INCOMPLETE]" in modified["outcome"]
        assert len(modified["key_findings"]) > 0
        assert modified["confidence"] == "L"
        assert modified["_proceeded_with_gaps"] is True
        assert set(modified["_original_missing"]) == missing

    def test_proceed_with_gaps_adds_gap_documentation(self):
        """Test that gaps are documented when proceeding."""
        handler = EscalationHandler()
        original = {"task_id": "123", "outcome": "Done"}
        missing = {"key_findings", "confidence"}

        modified = handler.proceed_with_gaps(original, missing)

        assert "gaps" in modified
        assert any("key_findings" in gap for gap in modified["gaps"])

    def test_escalation_history(self):
        """Test escalation history tracking."""
        handler = EscalationHandler()
        validator = SynthesisInputValidator()

        # Create escalation
        state = SynthesisValidationState()
        state.loop_count = MAX_LOOPS - 1
        result = validator.validate({"task_id": "test"}, state=state)

        handler.handle_escalation(result, {"task_id": "test"})

        history = handler.get_escalation_history()
        assert len(history) == 1
        assert history[0]["type"] == "synthesis_validation_escalation"


# ============================================================================
# HELPER FUNCTION TESTS
# ============================================================================

class TestHelperFunctions:
    """Tests for helper functions."""

    def test_validate_synthesis_input_valid(self):
        """Test validate_synthesis_input with valid input."""
        valid = {
            "task_id": "123",
            "outcome": "Done",
            "key_findings": [{"finding": "X", "confidence": "H"}],
            "confidence": "M"
        }
        result = validate_synthesis_input(valid)
        assert result.valid is True

    def test_validate_synthesis_input_invalid(self):
        """Test validate_synthesis_input with invalid input."""
        invalid = {"task_id": "123"}
        result = validate_synthesis_input(invalid)
        assert result.valid is False

    def test_create_valid_synthesis_input(self):
        """Test create_valid_synthesis_input helper."""
        input_dict = create_valid_synthesis_input(
            task_id="123",
            outcome="Task done",
            findings=[{"finding": "X", "confidence": "H"}],
            confidence="M",
            sources=["source1"]
        )
        assert input_dict["task_id"] == "123"
        assert input_dict["outcome"] == "Task done"
        assert len(input_dict["key_findings"]) == 1
        assert input_dict["sources"] == ["source1"]

        # Verify it passes validation
        result = validate_synthesis_input(input_dict)
        assert result.valid is True


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests for synthesis validation."""

    def test_full_validation_workflow(self):
        """Test complete validation workflow with retries."""
        validator = SynthesisInputValidator()
        state = SynthesisValidationState()

        # Attempt 1: Empty input
        r1 = validator.validate({}, state=state)
        assert r1.valid is False
        assert r1.loop_count == 1

        # Attempt 2: Partial input (no progress)
        r2 = validator.validate({}, state=state)
        assert r2.loop_count == 2

        # Attempt 3: Some fields added (50% progress)
        r3 = validator.validate({
            "task_id": "123",
            "outcome": "Done"
        }, state=state)
        # Counter should reset due to progress
        assert r3.loop_count == 1

        # Attempt 4: Complete input
        r4 = validator.validate({
            "task_id": "123",
            "outcome": "Done",
            "key_findings": [{"finding": "X", "confidence": "H"}],
            "confidence": "M"
        }, state=state)
        assert r4.valid is True

    def test_escalation_workflow(self):
        """Test workflow leading to escalation."""
        validator = SynthesisInputValidator()
        handler = EscalationHandler()
        state = SynthesisValidationState()

        # Repeatedly fail with no progress
        incomplete = {"task_id": "123"}
        for _ in range(MAX_LOOPS):
            result = validator.validate(incomplete, state=state)

        # Should have escalated
        assert result.action == ValidationAction.ESCALATE

        # Handle escalation
        context = handler.handle_escalation(result, incomplete)
        assert context["target"] == "orchestrator"

        # Proceed with gaps
        modified = handler.proceed_with_gaps(incomplete, result.missing)
        assert modified["_proceeded_with_gaps"] is True

        # Modified input should now pass
        final_result = validator.validate(modified)
        assert final_result.valid is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
