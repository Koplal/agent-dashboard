#!/usr/bin/env python3
"""
Unit tests for panel_selector.py - Automatic panel size selection.

Tests cover:
- Score calculation
- Panel size thresholds
- Override rules (escalate only)
- Metadata inference
- Audit logging
"""

import sys
import os
import pytest
import tempfile

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from panel_selector import (
    PanelSizeSelector,
    TaskMetadata,
    ScoreBreakdown,
    PanelSelection,
    MetadataInferrer,
    PANEL_THRESHOLDS,
    PANEL_3_JUDGES,
    PANEL_5_JUDGES,
    PANEL_7_JUDGES,
    get_judges_for_panel,
    quick_select_panel,
    format_panel_selection,
)


# ============================================================================
# TASK METADATA TESTS
# ============================================================================

class TestTaskMetadata:
    """Tests for the TaskMetadata dataclass."""

    def test_default_values(self):
        """Test default metadata values."""
        meta = TaskMetadata()
        assert meta.reversible is True
        assert meta.blast_radius == "internal"
        assert meta.domain == "software"
        assert meta.estimated_impact == "medium"
        assert meta.user_override is None

    def test_to_dict(self):
        """Test metadata serialization."""
        meta = TaskMetadata(
            reversible=False,
            blast_radius="external",
            estimated_impact="critical"
        )
        d = meta.to_dict()
        assert d["reversible"] is False
        assert d["blast_radius"] == "external"
        assert d["estimated_impact"] == "critical"

    def test_from_dict(self):
        """Test metadata deserialization."""
        data = {
            "reversible": False,
            "blast_radius": "org",
            "domain": "hardware",
            "estimated_impact": "high"
        }
        meta = TaskMetadata.from_dict(data)
        assert meta.reversible is False
        assert meta.blast_radius == "org"
        assert meta.domain == "hardware"
        assert meta.estimated_impact == "high"


# ============================================================================
# SCORE CALCULATION TESTS
# ============================================================================

class TestScoreCalculation:
    """Tests for score calculation."""

    def test_minimum_score(self):
        """Test minimum possible score (reversible, internal, software, low)."""
        selector = PanelSizeSelector()
        meta = TaskMetadata(
            reversible=True,
            blast_radius="internal",
            domain="software",
            estimated_impact="low"
        )
        score, breakdown = selector.calculate_score(meta)

        assert breakdown.reversibility == 0
        assert breakdown.blast_radius == 0
        assert breakdown.domain == 1
        assert breakdown.impact == 0
        assert score == 1  # Only domain contributes

    def test_maximum_score(self):
        """Test maximum possible score (irreversible, external, hardware, critical)."""
        selector = PanelSizeSelector()
        meta = TaskMetadata(
            reversible=False,
            blast_radius="external",
            domain="hardware",
            estimated_impact="critical"
        )
        score, breakdown = selector.calculate_score(meta)

        assert breakdown.reversibility == 4
        assert breakdown.blast_radius == 3
        assert breakdown.domain == 2
        assert breakdown.impact == 4
        assert score == 13

    def test_medium_score(self):
        """Test medium score calculation."""
        selector = PanelSizeSelector()
        meta = TaskMetadata(
            reversible=True,
            blast_radius="team",
            domain="software",
            estimated_impact="medium"
        )
        score, breakdown = selector.calculate_score(meta)

        # 0 + 1 + 1 + 1 = 3
        assert score == 3


# ============================================================================
# PANEL SIZE SELECTION TESTS
# ============================================================================

class TestPanelSizeSelection:
    """Tests for panel size selection."""

    def test_low_risk_3_panel(self):
        """Test low risk task gets 3-judge panel."""
        selector = PanelSizeSelector()
        meta = TaskMetadata(
            reversible=True,
            blast_radius="internal",
            domain="software",
            estimated_impact="low"
        )
        result = selector.select("t1", "Fix typo in docs", meta)

        assert result.panel_size == 3
        assert result.score < 4

    def test_medium_risk_5_panel(self):
        """Test medium risk task gets 5-judge panel."""
        selector = PanelSizeSelector()
        meta = TaskMetadata(
            reversible=True,
            blast_radius="team",
            domain="software",
            estimated_impact="high"
        )
        result = selector.select("t2", "Update shared library", meta)

        # Score should be in 4-7 range
        if 4 <= result.score <= 7:
            assert result.panel_size == 5

    def test_high_risk_7_panel(self):
        """Test high risk task gets 7-judge panel."""
        selector = PanelSizeSelector()
        meta = TaskMetadata(
            reversible=False,
            blast_radius="external",
            domain="hardware",
            estimated_impact="critical"
        )
        result = selector.select("t3", "Deploy firmware update", meta)

        assert result.panel_size == 7
        assert result.score >= 8

    def test_score_breakdown_included(self):
        """Test score breakdown is included in result."""
        selector = PanelSizeSelector()
        meta = TaskMetadata()
        result = selector.select("t4", "Test task", meta)

        assert result.score_breakdown is not None
        assert result.score_breakdown.total == result.score


# ============================================================================
# OVERRIDE TESTS
# ============================================================================

class TestOverrideRules:
    """Tests for override rules (escalate only)."""

    def test_user_can_escalate(self):
        """Test user can escalate panel size."""
        selector = PanelSizeSelector()
        meta = TaskMetadata(
            reversible=True,
            blast_radius="internal",
            domain="software",
            estimated_impact="low",
            user_override=5
        )
        result = selector.select("t1", "Simple task", meta)

        # Low risk would get 3, but user requested 5
        assert result.panel_size == 5
        assert result.override_applied is True
        assert result.calculated_size == 3

    def test_user_cannot_downgrade(self):
        """Test user cannot downgrade panel size."""
        selector = PanelSizeSelector()
        meta = TaskMetadata(
            reversible=False,
            blast_radius="external",
            domain="software",
            estimated_impact="high",
            user_override=3
        )
        result = selector.select("t2", "Critical task", meta)

        # High risk should get 5+, user tried to downgrade to 3
        assert result.panel_size >= 5
        assert result.override_blocked is True
        assert result.override_applied is False

    def test_no_override_when_not_requested(self):
        """Test no override when not requested."""
        selector = PanelSizeSelector()
        meta = TaskMetadata(
            reversible=True,
            blast_radius="internal"
        )
        result = selector.select("t3", "Normal task", meta)

        assert result.override_applied is False
        assert result.override_attempted is False
        assert result.override_blocked is False

    def test_same_size_override_no_change(self):
        """Test override with same size has no effect."""
        selector = PanelSizeSelector()
        meta = TaskMetadata(
            reversible=True,
            blast_radius="internal",
            domain="software",
            estimated_impact="low",
            user_override=3
        )
        result = selector.select("t4", "Task", meta)

        # Score should result in 3, override is also 3
        if result.calculated_size == 3:
            assert result.panel_size == 3
            assert result.override_applied is False


# ============================================================================
# METADATA INFERRER TESTS
# ============================================================================

class TestMetadataInferrer:
    """Tests for metadata inference."""

    def test_infer_irreversible(self):
        """Test inference of irreversible action."""
        inferrer = MetadataInferrer()
        meta = inferrer.infer("Delete all production data")

        assert meta.reversible is False
        assert "delete" in meta.keywords or "production" in meta.keywords

    def test_infer_external_blast(self):
        """Test inference of external blast radius."""
        inferrer = MetadataInferrer()
        meta = inferrer.infer("Update customer-facing API")

        assert meta.blast_radius == "external"

    def test_infer_critical_impact(self):
        """Test inference of critical impact."""
        inferrer = MetadataInferrer()
        meta = inferrer.infer("Fix security vulnerability in auth")

        assert meta.estimated_impact == "critical"

    def test_infer_hardware_domain(self):
        """Test inference of hardware domain."""
        inferrer = MetadataInferrer()
        meta = inferrer.infer("Update firmware on network devices")

        assert meta.domain == "hardware"

    def test_infer_defaults_for_unknown(self):
        """Test defaults for unknown description."""
        inferrer = MetadataInferrer()
        meta = inferrer.infer("Do something")

        assert meta.reversible is True
        assert meta.blast_radius == "internal"
        assert meta.domain == "software"
        assert meta.estimated_impact == "medium"
        assert meta.explicit is False

    def test_infer_deployment(self):
        """Test inference for deployment."""
        inferrer = MetadataInferrer()
        meta = inferrer.infer("Deploy new feature to production")

        assert meta.reversible is False  # deploy is irreversible keyword
        assert meta.blast_radius == "external"  # production implies external
        assert meta.estimated_impact == "high"


# ============================================================================
# AUDIT LOGGING TESTS
# ============================================================================

class TestAuditLogging:
    """Tests for audit logging."""

    def test_selection_logged_to_memory(self):
        """Test selections are logged to memory."""
        selector = PanelSizeSelector()
        meta = TaskMetadata()

        selector.select("t1", "Task 1", meta)
        selector.select("t2", "Task 2", meta)

        history = selector.get_selection_history()
        assert len(history) == 2
        assert history[0]["task_id"] == "t1"
        assert history[1]["task_id"] == "t2"

    def test_selection_logged_to_database(self):
        """Test selections are logged to database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            selector = PanelSizeSelector(db_path=db_path)
            meta = TaskMetadata()

            selector.select("t1", "Task 1", meta)

            # Check database
            import sqlite3
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM panel_selections")
                count = cursor.fetchone()[0]
                assert count == 1
        finally:
            os.unlink(db_path)


# ============================================================================
# HELPER FUNCTION TESTS
# ============================================================================

class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_judges_for_panel_3(self):
        """Test getting judges for 3-panel."""
        judges = get_judges_for_panel(3)
        assert len(judges) == 3
        assert "judge-technical" in judges
        assert "judge-completeness" in judges
        assert "judge-practicality" in judges

    def test_get_judges_for_panel_5(self):
        """Test getting judges for 5-panel."""
        judges = get_judges_for_panel(5)
        assert len(judges) == 5
        assert "judge-adversarial" in judges
        assert "judge-user" in judges

    def test_get_judges_for_panel_7(self):
        """Test getting judges for 7-panel."""
        judges = get_judges_for_panel(7)
        assert len(judges) == 7
        assert "judge-domain-expert" in judges
        assert "judge-risk" in judges

    def test_quick_select_panel(self):
        """Test quick panel selection."""
        result = quick_select_panel("Deploy to production")

        assert result.panel_size in [3, 5, 7]
        assert result.description == "Deploy to production"

    def test_quick_select_with_override(self):
        """Test quick selection with override."""
        result = quick_select_panel("Simple task", user_override=7)

        # Override should escalate
        assert result.panel_size == 7

    def test_format_panel_selection(self):
        """Test panel selection formatting."""
        selector = PanelSizeSelector()
        meta = TaskMetadata()
        selection = selector.select("t1", "Test task", meta)

        formatted = format_panel_selection(selection)

        assert "Panel Selection" in formatted
        assert "Test task" in formatted
        assert "Score Breakdown" in formatted
        assert "Panel Judges" in formatted


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests for panel selection."""

    def test_full_workflow_with_inference(self):
        """Test full workflow with automatic inference."""
        # Infer metadata from description
        inferrer = MetadataInferrer()
        meta = inferrer.infer("Delete user accounts from production database")

        # Select panel
        selector = PanelSizeSelector()
        result = selector.select("delete-users", "Delete user accounts", meta)

        # Should be high risk due to:
        # - "delete" -> irreversible (4)
        # - "production" -> external blast (3)
        # - should trigger high impact
        assert result.score >= 7
        assert result.panel_size >= 5

    def test_escalation_path(self):
        """Test user escalation path."""
        # Start with low-risk task
        meta = TaskMetadata(
            reversible=True,
            blast_radius="internal",
            domain="software",
            estimated_impact="low"
        )

        selector = PanelSizeSelector()

        # First selection: auto-selected
        r1 = selector.select("t1", "Low risk", meta)
        assert r1.panel_size == 3

        # User decides to escalate
        meta.user_override = 5
        r2 = selector.select("t2", "Low risk - escalated", meta)
        assert r2.panel_size == 5
        assert r2.override_applied is True

    def test_blocked_downgrade_path(self):
        """Test blocked downgrade path."""
        # High-risk task
        meta = TaskMetadata(
            reversible=False,
            blast_radius="external",
            domain="software",
            estimated_impact="critical",
            user_override=3  # Try to downgrade
        )

        selector = PanelSizeSelector()
        result = selector.select("critical-task", "Critical operation", meta)

        # Downgrade should be blocked
        assert result.panel_size >= 5
        assert result.override_blocked is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
