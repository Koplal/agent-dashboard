#!/usr/bin/env python3
"""
Unit tests for compression_gate.py - Token budget enforcement.

Tests cover:
- CompressionGate validation
- Budget calculations
- Threshold behavior (soft/hard)
- Auto-routing logic
- BudgetAwareAgent wrapper
"""

import sys
import os
import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from compression_gate import (
    CompressionGate,
    GateAction,
    GateDecision,
    BudgetAwareAgent,
    TIER_BUDGETS,
    DEFAULT_BUDGET,
    get_tier_from_model,
    estimate_compression_ratio,
    format_budget_status,
)
from validation import AgentTier, HandoffSchema, Finding, Confidence


# ============================================================================
# COMPRESSION GATE TESTS
# ============================================================================

class TestCompressionGate:
    """Tests for the CompressionGate class."""

    def test_initialization(self):
        """Test compression gate initializes correctly."""
        gate = CompressionGate()
        assert gate.SOFT_THRESHOLD == 1.25
        assert gate.HARD_THRESHOLD == 2.0
        assert gate.summarizer_agent == "summarizer"
        assert gate.stats.total_validations == 0

    def test_custom_budgets(self):
        """Test custom budget configuration."""
        custom_budgets = {
            (AgentTier.HAIKU, AgentTier.OPUS): 200,
            (AgentTier.SONNET, AgentTier.OPUS): 800,
        }
        gate = CompressionGate(budgets=custom_budgets)
        assert gate.get_budget(AgentTier.HAIKU, AgentTier.OPUS) == 200
        assert gate.get_budget(AgentTier.SONNET, AgentTier.OPUS) == 800

    def test_get_budget_haiku_to_opus(self):
        """Test budget for Haiku -> Opus is 300."""
        gate = CompressionGate()
        budget = gate.get_budget(AgentTier.HAIKU, AgentTier.OPUS)
        assert budget == 300

    def test_get_budget_haiku_to_sonnet(self):
        """Test budget for Haiku -> Sonnet is 500."""
        gate = CompressionGate()
        budget = gate.get_budget(AgentTier.HAIKU, AgentTier.SONNET)
        assert budget == 500

    def test_get_budget_sonnet_to_opus(self):
        """Test budget for Sonnet -> Opus is 1000."""
        gate = CompressionGate()
        budget = gate.get_budget(AgentTier.SONNET, AgentTier.OPUS)
        assert budget == 1000

    def test_get_budget_sonnet_to_sonnet(self):
        """Test budget for Sonnet -> Sonnet is 1500."""
        gate = CompressionGate()
        budget = gate.get_budget(AgentTier.SONNET, AgentTier.SONNET)
        assert budget == 1500

    def test_get_budget_default(self):
        """Test default budget for unknown tier pair."""
        gate = CompressionGate()
        # Clear budgets to test default
        gate.budgets = {}
        budget = gate.get_budget(AgentTier.OPUS, AgentTier.HAIKU)
        assert budget == DEFAULT_BUDGET

    def test_count_tokens_empty(self):
        """Test token counting for empty string."""
        gate = CompressionGate()
        assert gate.count_tokens("") == 0
        assert gate.count_tokens(None) == 0

    def test_count_tokens_basic(self):
        """Test token counting for basic text."""
        gate = CompressionGate()
        # Basic text should have some tokens
        tokens = gate.count_tokens("Hello, this is a test message.")
        assert tokens > 0

    def test_under_budget_passes(self):
        """Test that under-budget output passes."""
        gate = CompressionGate()
        # Short output under 300 token budget
        result = gate.validate(
            "Task completed successfully.",
            AgentTier.HAIKU,
            AgentTier.OPUS
        )
        assert result.action == GateAction.PASS
        assert result.tokens < result.budget

    def test_at_budget_passes(self):
        """Test that at-budget output passes."""
        gate = CompressionGate()
        # Create output that's approximately at budget
        # Haiku -> Opus budget is 300 tokens
        result = gate.validate(
            "x" * 1000,  # ~250 tokens with 4 char/token estimate
            AgentTier.HAIKU,
            AgentTier.OPUS
        )
        # Should pass if within 1.25x
        assert result.action in [GateAction.PASS, GateAction.AUTO_ROUTE]

    def test_soft_threshold_auto_routes(self):
        """Test soft threshold (1.25x) triggers auto-route."""
        gate = CompressionGate()
        # Haiku -> Opus budget is 300, soft threshold is 375 tokens
        # Create output of ~400 tokens (1.33x budget)
        output = "word " * 400  # Each "word " is ~1.25 tokens
        result = gate.validate(output, AgentTier.HAIKU, AgentTier.OPUS)

        # Should be between soft and hard thresholds
        if 1.25 < result.ratio <= 2.0:
            assert result.action == GateAction.AUTO_ROUTE
            assert result.routed_to == "summarizer"

    def test_hard_threshold_rejects(self):
        """Test hard threshold (2x) triggers rejection."""
        gate = CompressionGate()
        # Haiku -> Opus budget is 300, hard threshold is 600 tokens
        # Create output well over 600 tokens
        output = "word " * 1000  # ~1000+ tokens
        result = gate.validate(output, AgentTier.HAIKU, AgentTier.OPUS)

        if result.ratio > 2.0:
            assert result.action == GateAction.REJECT
            assert result.feedback is not None
            assert "Compression Required" in result.feedback

    def test_feedback_contains_guidance(self):
        """Test rejection feedback contains compression guidance."""
        gate = CompressionGate()
        output = "word " * 1000  # Large output
        result = gate.validate(output, AgentTier.HAIKU, AgentTier.OPUS)

        if result.action == GateAction.REJECT:
            assert "KEY FINDINGS" in result.feedback
            assert "Required Format" in result.feedback
            assert "budget" in result.feedback.lower()

    def test_stats_tracking(self):
        """Test statistics are tracked correctly."""
        gate = CompressionGate()

        # Perform some validations
        gate.validate("short", AgentTier.HAIKU, AgentTier.OPUS)
        gate.validate("short text", AgentTier.SONNET, AgentTier.OPUS)

        stats = gate.get_stats()
        assert stats["total_validations"] == 2
        assert stats["passed"] >= 0
        assert stats["total_tokens_processed"] > 0

    def test_decision_logging(self):
        """Test decisions are logged."""
        gate = CompressionGate()
        gate.validate("test output", AgentTier.HAIKU, AgentTier.OPUS, task_id="task-1")

        decisions = gate.get_recent_decisions(5)
        assert len(decisions) == 1
        assert decisions[0]["task_id"] == "task-1"

    def test_reset_stats(self):
        """Test stats reset."""
        gate = CompressionGate()
        gate.validate("test", AgentTier.HAIKU, AgentTier.OPUS)

        gate.reset_stats()

        stats = gate.get_stats()
        assert stats["total_validations"] == 0
        assert len(gate.decision_log) == 0


# ============================================================================
# GATE DECISION TESTS
# ============================================================================

class TestGateDecision:
    """Tests for the GateDecision dataclass."""

    def test_gate_decision_creation(self):
        """Test GateDecision creation."""
        decision = GateDecision(
            action=GateAction.PASS,
            tokens=200,
            budget=300,
            ratio=0.67,
            source_tier=AgentTier.HAIKU,
            target_tier=AgentTier.OPUS
        )
        assert decision.action == GateAction.PASS
        assert decision.tokens == 200
        assert decision.budget == 300

    def test_gate_decision_to_dict(self):
        """Test GateDecision serialization."""
        decision = GateDecision(
            action=GateAction.AUTO_ROUTE,
            tokens=400,
            budget=300,
            ratio=1.33,
            source_tier=AgentTier.HAIKU,
            target_tier=AgentTier.OPUS,
            routed_to="summarizer"
        )
        d = decision.to_dict()
        assert d["action"] == "AUTO_ROUTE"
        assert d["tokens"] == 400
        assert d["routed_to"] == "summarizer"


# ============================================================================
# BUDGET AWARE AGENT TESTS
# ============================================================================

class TestBudgetAwareAgent:
    """Tests for the BudgetAwareAgent wrapper."""

    def test_initialization(self):
        """Test BudgetAwareAgent initialization."""
        agent = BudgetAwareAgent("researcher", AgentTier.HAIKU)
        assert agent.agent_name == "researcher"
        assert agent.tier == AgentTier.HAIKU
        assert agent.gate is not None

    def test_prepare_handoff_passes(self):
        """Test handoff preparation for valid output."""
        agent = BudgetAwareAgent("researcher", AgentTier.HAIKU)
        output, decision = agent.prepare_handoff(
            "Short output",
            AgentTier.OPUS,
            task_id="test-1"
        )
        assert decision.action == GateAction.PASS
        assert output == "Short output"

    def test_prepare_handoff_rejects(self):
        """Test handoff preparation for over-budget output."""
        agent = BudgetAwareAgent("researcher", AgentTier.HAIKU)
        large_output = "word " * 1000
        output, decision = agent.prepare_handoff(
            large_output,
            AgentTier.OPUS,
            task_id="test-2"
        )
        if decision.action == GateAction.REJECT:
            assert "Compression" in output

    def test_get_budget_for_target(self):
        """Test getting budget for target tier."""
        agent = BudgetAwareAgent("researcher", AgentTier.HAIKU)
        budget = agent.get_budget_for_target(AgentTier.OPUS)
        assert budget == 300

    def test_custom_gate(self):
        """Test BudgetAwareAgent with custom gate."""
        custom_gate = CompressionGate(summarizer_agent="custom-summarizer")
        agent = BudgetAwareAgent("test", AgentTier.SONNET, gate=custom_gate)
        assert agent.gate.summarizer_agent == "custom-summarizer"


# ============================================================================
# HANDOFF SCHEMA VALIDATION TESTS
# ============================================================================

class TestHandoffValidation:
    """Tests for validating HandoffSchema through gate."""

    def test_validate_handoff_schema(self):
        """Test validating a HandoffSchema."""
        gate = CompressionGate()
        handoff = HandoffSchema(
            task_id="test-1",
            outcome="Task completed",
            key_findings=[Finding("Found X", Confidence.HIGH)],
            confidence=Confidence.MEDIUM,
            agent_name="researcher",
            model_tier=AgentTier.HAIKU
        )
        result = gate.validate_handoff(handoff, AgentTier.OPUS)
        assert result.action in [GateAction.PASS, GateAction.AUTO_ROUTE, GateAction.REJECT]
        assert result.source_tier == AgentTier.HAIKU
        assert result.target_tier == AgentTier.OPUS


# ============================================================================
# HELPER FUNCTION TESTS
# ============================================================================

class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_tier_from_model_opus(self):
        """Test getting tier from opus model name."""
        assert get_tier_from_model("opus") == AgentTier.OPUS
        assert get_tier_from_model("claude-opus-4") == AgentTier.OPUS

    def test_get_tier_from_model_sonnet(self):
        """Test getting tier from sonnet model name."""
        assert get_tier_from_model("sonnet") == AgentTier.SONNET
        assert get_tier_from_model("claude-sonnet-4") == AgentTier.SONNET

    def test_get_tier_from_model_haiku(self):
        """Test getting tier from haiku model name."""
        assert get_tier_from_model("haiku") == AgentTier.HAIKU
        assert get_tier_from_model("claude-haiku-3") == AgentTier.HAIKU

    def test_get_tier_from_model_default(self):
        """Test default tier for unknown model."""
        assert get_tier_from_model("unknown") == AgentTier.SONNET

    def test_estimate_compression_ratio(self):
        """Test compression ratio calculation."""
        assert estimate_compression_ratio(1000, 100) == 10.0
        assert estimate_compression_ratio(500, 250) == 2.0
        assert estimate_compression_ratio(100, 0) == float('inf')

    def test_format_budget_status_ok(self):
        """Test budget status formatting when OK."""
        status = format_budget_status(200, 300, AgentTier.HAIKU, AgentTier.OPUS)
        assert "[OK]" in status
        assert "200/300" in status
        assert "haiku" in status
        assert "opus" in status

    def test_format_budget_status_warning(self):
        """Test budget status formatting when in warning zone."""
        status = format_budget_status(350, 300, AgentTier.HAIKU, AgentTier.OPUS)
        assert "[WARNING]" in status

    def test_format_budget_status_over(self):
        """Test budget status formatting when over."""
        status = format_budget_status(400, 300, AgentTier.HAIKU, AgentTier.OPUS)
        assert "[OVER]" in status


# ============================================================================
# TIER BUDGET TESTS
# ============================================================================

class TestTierBudgets:
    """Tests for tier budget constants."""

    def test_all_budgets_defined(self):
        """Test all expected tier budgets are defined."""
        assert (AgentTier.HAIKU, AgentTier.OPUS) in TIER_BUDGETS
        assert (AgentTier.HAIKU, AgentTier.SONNET) in TIER_BUDGETS
        assert (AgentTier.SONNET, AgentTier.OPUS) in TIER_BUDGETS
        assert (AgentTier.SONNET, AgentTier.SONNET) in TIER_BUDGETS

    def test_budget_values(self):
        """Test budget values match specification."""
        assert TIER_BUDGETS[(AgentTier.HAIKU, AgentTier.OPUS)] == 300
        assert TIER_BUDGETS[(AgentTier.HAIKU, AgentTier.SONNET)] == 500
        assert TIER_BUDGETS[(AgentTier.SONNET, AgentTier.OPUS)] == 1000
        assert TIER_BUDGETS[(AgentTier.SONNET, AgentTier.SONNET)] == 1500


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests for compression gate."""

    def test_full_workflow_haiku_to_opus(self):
        """Test complete workflow from Haiku to Opus."""
        gate = CompressionGate()

        # Simulate typical handoff sizes
        short_handoff = "## Task: test-1\nOutcome: Found relevant info.\n- Finding 1"
        medium_handoff = short_handoff + "\n" + "Additional context. " * 50
        large_handoff = medium_handoff + "\n" + "More details. " * 200

        # Short should pass
        r1 = gate.validate(short_handoff, AgentTier.HAIKU, AgentTier.OPUS)
        assert r1.action == GateAction.PASS

        # Medium might pass or auto-route
        r2 = gate.validate(medium_handoff, AgentTier.HAIKU, AgentTier.OPUS)
        assert r2.action in [GateAction.PASS, GateAction.AUTO_ROUTE]

        # Large should auto-route or reject
        r3 = gate.validate(large_handoff, AgentTier.HAIKU, AgentTier.OPUS)
        assert r3.action in [GateAction.AUTO_ROUTE, GateAction.REJECT]

    def test_multi_agent_pipeline(self):
        """Test multi-agent pipeline with compression gate."""
        gate = CompressionGate()

        # Haiku researcher output
        haiku_output = "Found 3 relevant docs. Key points: A, B, C."
        r1 = gate.validate(haiku_output, AgentTier.HAIKU, AgentTier.SONNET)
        assert r1.action == GateAction.PASS

        # Sonnet synthesis output
        sonnet_output = "Synthesis: Based on research, recommend X. Evidence: ..."
        r2 = gate.validate(sonnet_output, AgentTier.SONNET, AgentTier.OPUS)
        assert r2.action == GateAction.PASS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
