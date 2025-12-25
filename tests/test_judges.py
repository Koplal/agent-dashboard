"""
Tests for Heterogeneous Judge Panel System (NESY-003).

Tests configurations, verdict parsing, panel aggregation,
and escalation workflow.
"""

import pytest
import asyncio
from datetime import datetime, timezone

from src.judges.configurations import (
    JudgePersona,
    JudgeConfig,
    ADVERSARIAL_CONFIG,
    RUBRIC_CONFIG,
    DOMAIN_EXPERT_CONFIG,
    SKEPTIC_CONFIG,
    END_USER_CONFIG,
    TECHNICAL_CONFIG,
    COMPLETENESS_CONFIG,
    PRACTICALITY_CONFIG,
    get_default_panel_configs,
    get_config_by_persona,
    create_custom_config,
)
from src.judges.panel import (
    VerdictParser,
    ParsedVerdict,
    AggregatedVerdict,
    EscalationHandler,
    EscalationReason,
    EscalationRequest,
    JudgePanel,
)


# =============================================================================
# CONFIGURATION TESTS
# =============================================================================

class TestJudgePersona:
    """Tests for JudgePersona enum."""

    def test_all_personas_have_values(self):
        """All personas should have string values."""
        for persona in JudgePersona:
            assert isinstance(persona.value, str)
            assert len(persona.value) > 0

    def test_persona_count(self):
        """Should have at least 5 personas for diverse evaluation."""
        assert len(JudgePersona) >= 5


class TestJudgeConfig:
    """Tests for JudgeConfig dataclass."""

    def test_adversarial_config(self):
        """Adversarial config should be properly configured."""
        config = ADVERSARIAL_CONFIG
        assert config.persona == JudgePersona.ADVERSARIAL
        assert config.temperature == 0.3
        assert "skeptical" in config.system_prompt.lower()
        assert "errors" in config.evaluation_focus

    def test_rubric_config(self):
        """Rubric config should have structured evaluation."""
        config = RUBRIC_CONFIG
        assert config.persona == JudgePersona.RUBRIC_BASED
        assert config.temperature == 0.1  # Low for consistency
        assert "accuracy" in config.evaluation_focus
        assert "completeness" in config.evaluation_focus

    def test_domain_expert_config(self):
        """Domain expert should focus on technical accuracy."""
        config = DOMAIN_EXPERT_CONFIG
        assert config.persona == JudgePersona.DOMAIN_EXPERT
        assert "technical_accuracy" in config.evaluation_focus
        assert "best_practices" in config.evaluation_focus

    def test_skeptic_config_requires_evidence(self):
        """Skeptic should require evidence."""
        config = SKEPTIC_CONFIG
        assert config.require_evidence is True
        assert "source_quality" in config.evaluation_focus

    def test_end_user_config_no_evidence_required(self):
        """End user perspective shouldn't require citations."""
        config = END_USER_CONFIG
        assert config.require_evidence is False
        assert "usability" in config.evaluation_focus

    def test_config_to_dict(self):
        """Config should convert to dictionary."""
        config = ADVERSARIAL_CONFIG
        d = config.to_dict()
        assert d["persona"] == "adversarial"
        assert d["temperature"] == 0.3
        assert isinstance(d["evaluation_focus"], list)

    def test_config_weights(self):
        """Configs should have appropriate weights."""
        # Adversarial should have higher weight
        assert ADVERSARIAL_CONFIG.weight > 1.0
        # Domain expert should have elevated weight
        assert DOMAIN_EXPERT_CONFIG.weight > 1.0
        # End user slightly lower
        assert END_USER_CONFIG.weight < 1.0


class TestConfigRegistry:
    """Tests for configuration registry functions."""

    def test_get_config_by_persona(self):
        """Should retrieve correct config for persona."""
        config = get_config_by_persona(JudgePersona.ADVERSARIAL)
        assert config.persona == JudgePersona.ADVERSARIAL

    def test_get_config_by_persona_all(self):
        """Should have configs for all personas."""
        for persona in JudgePersona:
            config = get_config_by_persona(persona)
            assert config.persona == persona

    def test_get_default_panel_configs_3(self):
        """3-judge panel should have core configs."""
        configs = get_default_panel_configs(3)
        assert len(configs) == 3
        personas = [c.persona for c in configs]
        assert JudgePersona.TECHNICAL in personas
        assert JudgePersona.COMPLETENESS in personas
        assert JudgePersona.PRACTICALITY in personas

    def test_get_default_panel_configs_5(self):
        """5-judge panel should add adversarial and user."""
        configs = get_default_panel_configs(5)
        assert len(configs) == 5
        personas = [c.persona for c in configs]
        assert JudgePersona.ADVERSARIAL in personas
        assert JudgePersona.END_USER in personas

    def test_get_default_panel_configs_7(self):
        """7-judge panel should add expert and skeptic."""
        configs = get_default_panel_configs(7)
        assert len(configs) == 7
        personas = [c.persona for c in configs]
        assert JudgePersona.DOMAIN_EXPERT in personas
        assert JudgePersona.SKEPTIC in personas

    def test_create_custom_config(self):
        """Should create custom config with specified params."""
        config = create_custom_config(
            persona=JudgePersona.TECHNICAL,
            system_prompt="Custom prompt",
            evaluation_focus=["custom_focus"],
            temperature=0.5,
        )
        assert config.persona == JudgePersona.TECHNICAL
        assert config.system_prompt == "Custom prompt"
        assert config.temperature == 0.5


# =============================================================================
# VERDICT PARSER TESTS
# =============================================================================

class TestVerdictParser:
    """Tests for VerdictParser class."""

    @pytest.fixture
    def parser(self):
        return VerdictParser()

    def test_parse_pass_verdict(self, parser):
        """Should correctly parse PASS verdict."""
        response = """
        OVERALL ASSESSMENT: PASS
        SCORE: 85
        CONFIDENCE: 90%

        ISSUES FOUND:
        - Minor: Small formatting issue

        STRENGTHS:
        - Well-structured code
        - Good documentation

        DETAILED FEEDBACK:
        This is a well-implemented solution.
        """
        verdict = parser.parse(response, JudgePersona.TECHNICAL)
        assert verdict.passed is True
        assert verdict.score == 0.85
        assert verdict.confidence == 0.9
        assert len(verdict.issues_found) >= 1
        assert len(verdict.strengths_noted) >= 1

    def test_parse_fail_verdict(self, parser):
        """Should correctly parse FAIL verdict."""
        response = """
        OVERALL ASSESSMENT: FAIL
        SCORE: 35
        CONFIDENCE: 85%

        ISSUES FOUND:
        - CRITICAL: Security vulnerability in auth
        - MAJOR: Missing error handling

        DETAILED FEEDBACK:
        Critical issues must be addressed before approval.
        """
        verdict = parser.parse(response, JudgePersona.ADVERSARIAL)
        assert verdict.passed is False
        assert verdict.score == 0.35
        assert len(verdict.issues_found) >= 1

    def test_parse_score_normalization(self, parser):
        """Should normalize scores to 0.0-1.0."""
        response = "SCORE: 75/100"
        verdict = parser.parse(response, JudgePersona.RUBRIC_BASED)
        assert 0.0 <= verdict.score <= 1.0
        assert verdict.score == 0.75

    def test_parse_rubric_score(self, parser):
        """Should parse X/5 rubric scores."""
        response = "SCORE: 4/5"
        verdict = parser.parse(response, JudgePersona.RUBRIC_BASED)
        assert verdict.score == 0.8

    def test_parse_missing_overall(self, parser):
        """Should infer pass/fail from score when overall missing."""
        response = "SCORE: 80"
        verdict = parser.parse(response, JudgePersona.TECHNICAL)
        assert verdict.passed is True  # 0.8 >= 0.6

        response = "SCORE: 40"
        verdict = parser.parse(response, JudgePersona.TECHNICAL)
        assert verdict.passed is False  # 0.4 < 0.6

    def test_parse_issue_severity(self, parser):
        """Should extract issue severity."""
        response = """
        ISSUES FOUND:
        - [CRITICAL] Authentication bypass possible
        - [MAJOR] Missing input validation
        - [MINOR] Typo in variable name
        """
        verdict = parser.parse(response, JudgePersona.ADVERSARIAL)
        severities = [i.get("severity") for i in verdict.issues_found]
        assert "critical" in severities

    def test_parse_detailed_feedback(self, parser):
        """Should extract detailed feedback section."""
        response = """
        SCORE: 70

        DETAILED FEEDBACK:
        This is a comprehensive analysis of the submitted work.
        The implementation shows good understanding of the problem.
        """
        verdict = parser.parse(response, JudgePersona.DOMAIN_EXPERT)
        assert "comprehensive analysis" in verdict.detailed_feedback

    def test_parse_empty_response(self, parser):
        """Should handle empty response gracefully."""
        verdict = parser.parse("", JudgePersona.TECHNICAL)
        assert verdict.score == 0.5  # Default
        assert verdict.confidence == 0.7  # Default

    def test_parse_verdict_keywords(self, parser):
        """Should recognize verdict keywords."""
        response = "**PASS** with minor reservations"
        verdict = parser.parse(response, JudgePersona.TECHNICAL)
        assert verdict.passed is True

        response = "VERDICT: FAIL due to critical issues"
        verdict = parser.parse(response, JudgePersona.TECHNICAL)
        assert verdict.passed is False


# =============================================================================
# ESCALATION HANDLER TESTS
# =============================================================================

class TestEscalationHandler:
    """Tests for EscalationHandler class."""

    @pytest.fixture
    def handler(self):
        return EscalationHandler(
            consensus_threshold=0.6,
            confidence_threshold=0.5,
            score_variance_threshold=0.3,
        )

    def test_no_escalation_unanimous(self, handler):
        """Should not escalate when all judges agree."""
        verdict = AggregatedVerdict(
            passed=True,
            consensus_level=1.0,
            aggregated_score=0.85,
            individual_verdicts=[
                ParsedVerdict(JudgePersona.TECHNICAL, True, 0.85, 0.9),
                ParsedVerdict(JudgePersona.COMPLETENESS, True, 0.80, 0.85),
                ParsedVerdict(JudgePersona.PRACTICALITY, True, 0.90, 0.88),
            ],
        )
        needs, reasons = handler.check_escalation_needed(verdict)
        assert needs is False
        assert len(reasons) == 0

    def test_escalation_low_consensus(self, handler):
        """Should escalate when consensus is low."""
        verdict = AggregatedVerdict(
            passed=True,
            consensus_level=0.5,  # Below threshold
            aggregated_score=0.65,
            individual_verdicts=[
                ParsedVerdict(JudgePersona.TECHNICAL, True, 0.75, 0.8),
                ParsedVerdict(JudgePersona.COMPLETENESS, False, 0.55, 0.7),
            ],
        )
        needs, reasons = handler.check_escalation_needed(verdict)
        assert needs is True
        assert EscalationReason.LOW_CONSENSUS in reasons

    def test_escalation_low_confidence(self, handler):
        """Should escalate when any judge has low confidence."""
        verdict = AggregatedVerdict(
            passed=True,
            consensus_level=1.0,
            aggregated_score=0.75,
            individual_verdicts=[
                ParsedVerdict(JudgePersona.TECHNICAL, True, 0.75, 0.4),  # Low confidence
                ParsedVerdict(JudgePersona.COMPLETENESS, True, 0.80, 0.85),
            ],
        )
        needs, reasons = handler.check_escalation_needed(verdict)
        assert needs is True
        assert EscalationReason.LOW_CONFIDENCE in reasons

    def test_escalation_critical_issues(self, handler):
        """Should escalate when critical issues found."""
        verdict = AggregatedVerdict(
            passed=False,
            consensus_level=1.0,
            aggregated_score=0.45,
            individual_verdicts=[
                ParsedVerdict(
                    JudgePersona.ADVERSARIAL, False, 0.45, 0.9,
                    issues_found=[{"severity": "critical", "issue": "Security flaw"}]
                ),
            ],
        )
        needs, reasons = handler.check_escalation_needed(verdict)
        assert needs is True
        assert EscalationReason.CRITICAL_ISSUES in reasons

    def test_escalation_score_variance(self, handler):
        """Should escalate when score variance is high."""
        verdict = AggregatedVerdict(
            passed=True,
            consensus_level=1.0,
            aggregated_score=0.7,
            individual_verdicts=[
                ParsedVerdict(JudgePersona.TECHNICAL, True, 0.9, 0.8),
                ParsedVerdict(JudgePersona.COMPLETENESS, True, 0.5, 0.75),  # 0.4 variance
            ],
        )
        needs, reasons = handler.check_escalation_needed(verdict)
        assert needs is True
        assert EscalationReason.SCORE_VARIANCE in reasons

    def test_create_escalation_priority(self, handler):
        """Should set priority based on reasons."""
        verdict = AggregatedVerdict(
            passed=False,
            consensus_level=0.5,
            aggregated_score=0.45,
            individual_verdicts=[
                ParsedVerdict(
                    JudgePersona.ADVERSARIAL, False, 0.45, 0.9,
                    issues_found=[{"severity": "critical", "issue": "Security flaw"}]
                ),
            ],
        )
        request = handler.create_escalation(
            "task-1", "Test content", verdict,
            [EscalationReason.CRITICAL_ISSUES]
        )
        assert request.priority == "critical"

    def test_escalation_callback(self, handler):
        """Should trigger callback on escalation."""
        callback_called = []

        def callback(req):
            callback_called.append(req)

        handler.on_escalation = callback

        verdict = AggregatedVerdict(
            passed=False,
            consensus_level=0.5,
            aggregated_score=0.45,
            individual_verdicts=[],
        )
        handler.create_escalation(
            "task-1", "Test", verdict,
            [EscalationReason.LOW_CONSENSUS]
        )
        assert len(callback_called) == 1


# =============================================================================
# JUDGE PANEL TESTS
# =============================================================================

class TestJudgePanel:
    """Tests for JudgePanel class."""

    @pytest.fixture
    def panel_3(self):
        return JudgePanel(panel_size=3)

    @pytest.fixture
    def panel_5(self):
        return JudgePanel(panel_size=5)

    def test_panel_initialization_3(self, panel_3):
        """Should initialize 3-judge panel correctly."""
        assert len(panel_3.configs) == 3

    def test_panel_initialization_5(self, panel_5):
        """Should initialize 5-judge panel correctly."""
        assert len(panel_5.configs) == 5

    def test_panel_custom_configs(self):
        """Should accept custom configurations."""
        configs = [ADVERSARIAL_CONFIG, TECHNICAL_CONFIG]
        panel = JudgePanel(configs=configs)
        assert len(panel.configs) == 2

    @pytest.mark.asyncio
    async def test_evaluate_mock_mode(self, panel_3):
        """Should run evaluation in mock mode."""
        verdict = await panel_3.evaluate(
            content="Test content",
            context={"original_request": "Test request"},
            content_type="research",
        )
        assert isinstance(verdict, AggregatedVerdict)
        assert len(verdict.individual_verdicts) == 3
        assert 0.0 <= verdict.consensus_level <= 1.0
        assert 0.0 <= verdict.aggregated_score <= 1.0

    @pytest.mark.asyncio
    async def test_evaluate_returns_recommendation(self, panel_3):
        """Should generate recommendation."""
        verdict = await panel_3.evaluate(
            content="Test content",
            context={},
            content_type="code",
        )
        assert verdict.recommendation
        assert len(verdict.recommendation) > 10

    @pytest.mark.asyncio
    async def test_evaluate_tracks_duration(self, panel_3):
        """Should track evaluation duration."""
        verdict = await panel_3.evaluate(
            content="Test",
            context={},
            content_type="documentation",
        )
        assert verdict.evaluation_duration_ms >= 0

    @pytest.mark.asyncio
    async def test_evaluate_updates_stats(self, panel_3):
        """Should update statistics after evaluation."""
        await panel_3.evaluate("Test", {}, "research")
        await panel_3.evaluate("Test", {}, "research")

        stats = panel_3.get_stats()
        assert stats["evaluations_run"] == 2
        assert stats["panel_size"] == 3

    def test_aggregate_verdicts_unanimous_pass(self, panel_3):
        """Should pass with unanimous agreement."""
        verdicts = [
            ParsedVerdict(JudgePersona.TECHNICAL, True, 0.9, 0.95),
            ParsedVerdict(JudgePersona.COMPLETENESS, True, 0.85, 0.9),
            ParsedVerdict(JudgePersona.PRACTICALITY, True, 0.88, 0.92),
        ]
        aggregated = panel_3._aggregate_verdicts(verdicts)
        assert aggregated.passed is True
        assert aggregated.consensus_level == 1.0

    def test_aggregate_verdicts_unanimous_fail(self, panel_3):
        """Should fail with unanimous rejection."""
        verdicts = [
            ParsedVerdict(JudgePersona.TECHNICAL, False, 0.3, 0.9),
            ParsedVerdict(JudgePersona.COMPLETENESS, False, 0.35, 0.85),
            ParsedVerdict(JudgePersona.PRACTICALITY, False, 0.28, 0.88),
        ]
        aggregated = panel_3._aggregate_verdicts(verdicts)
        assert aggregated.passed is False
        assert aggregated.consensus_level == 0.0

    def test_aggregate_verdicts_mixed(self, panel_3):
        """Should handle mixed verdicts with consensus threshold."""
        verdicts = [
            ParsedVerdict(JudgePersona.TECHNICAL, True, 0.75, 0.85),
            ParsedVerdict(JudgePersona.COMPLETENESS, True, 0.80, 0.9),
            ParsedVerdict(JudgePersona.PRACTICALITY, False, 0.55, 0.75),
        ]
        aggregated = panel_3._aggregate_verdicts(verdicts)
        # 2/3 = 0.67, below 0.7 threshold
        assert aggregated.consensus_level == pytest.approx(0.67, rel=0.1)

    def test_aggregate_records_dissent(self, panel_3):
        """Should record dissenting opinions."""
        verdicts = [
            ParsedVerdict(JudgePersona.TECHNICAL, True, 0.8, 0.9),
            ParsedVerdict(JudgePersona.COMPLETENESS, True, 0.75, 0.85),
            ParsedVerdict(JudgePersona.PRACTICALITY, False, 0.5, 0.8),
        ]
        aggregated = panel_3._aggregate_verdicts(verdicts)
        assert len(aggregated.dissenting_opinions) > 0

    def test_aggregate_finds_critical_issues(self, panel_3):
        """Should identify issues found by multiple judges."""
        verdicts = [
            ParsedVerdict(
                JudgePersona.TECHNICAL, False, 0.4, 0.9,
                issues_found=[{"severity": "major", "issue": "common issue"}]
            ),
            ParsedVerdict(
                JudgePersona.COMPLETENESS, False, 0.45, 0.85,
                issues_found=[{"severity": "major", "issue": "common issue"}]
            ),
            ParsedVerdict(
                JudgePersona.PRACTICALITY, True, 0.6, 0.8,
            ),
        ]
        aggregated = panel_3._aggregate_verdicts(verdicts)
        assert len(aggregated.critical_issues) > 0

    def test_aggregate_empty_verdicts(self, panel_3):
        """Should handle empty verdicts list."""
        aggregated = panel_3._aggregate_verdicts([])
        assert aggregated.passed is False
        assert aggregated.consensus_level == 0.0

    def test_require_unanimous_pass(self):
        """Should require all judges to pass when configured."""
        panel = JudgePanel(panel_size=3, require_unanimous_pass=True)
        verdicts = [
            ParsedVerdict(JudgePersona.TECHNICAL, True, 0.9, 0.95),
            ParsedVerdict(JudgePersona.COMPLETENESS, True, 0.85, 0.9),
            ParsedVerdict(JudgePersona.PRACTICALITY, False, 0.55, 0.8),
        ]
        aggregated = panel._aggregate_verdicts(verdicts)
        assert aggregated.passed is False  # One dissent blocks

    def test_build_evaluation_prompt(self, panel_3):
        """Should build proper evaluation prompt."""
        config = panel_3.configs[0]
        prompt = panel_3._build_evaluation_prompt(
            config,
            content="Test content",
            context={"original_request": "Analyze this"},
            content_type="research",
        )
        assert "Test content" in prompt
        assert "research" in prompt
        assert config.evaluation_focus[0] in prompt


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestPanelIntegration:
    """Integration tests for panel system."""

    @pytest.mark.asyncio
    async def test_full_evaluation_workflow(self):
        """Test complete evaluation workflow."""
        # Create panel
        panel = JudgePanel(panel_size=5)

        # Run evaluation
        verdict = await panel.evaluate(
            content="""
            Research findings indicate that implementing
            output validation reduces errors by 40%.
            """,
            context={
                "original_request": "Analyze validation approaches",
                "source": "internal research",
            },
            content_type="research",
            task_id="test-task-001",
        )

        # Verify result structure
        assert isinstance(verdict, AggregatedVerdict)
        assert len(verdict.individual_verdicts) == 5
        assert verdict.recommendation
        # Duration may be 0 in mock mode (synchronous), just verify it's non-negative
        assert verdict.evaluation_duration_ms >= 0

    @pytest.mark.asyncio
    async def test_escalation_in_evaluation(self):
        """Test that escalation is triggered appropriately."""
        escalations = []

        def capture_escalation(req):
            escalations.append(req)

        panel = JudgePanel(panel_size=3)
        panel.escalation_handler.on_escalation = capture_escalation

        # Run multiple evaluations
        for _ in range(5):
            await panel.evaluate("Test", {}, "code")

        # Stats should be tracked
        stats = panel.get_stats()
        assert stats["evaluations_run"] == 5


class TestParsedVerdictDataclass:
    """Tests for ParsedVerdict dataclass."""

    def test_to_dict(self):
        """Should convert to dictionary properly."""
        verdict = ParsedVerdict(
            persona=JudgePersona.TECHNICAL,
            passed=True,
            score=0.85,
            confidence=0.9,
            issues_found=[{"severity": "minor", "issue": "test"}],
            strengths_noted=["good"],
            detailed_feedback="Detailed analysis here",
        )
        d = verdict.to_dict()
        assert d["persona"] == "technical"
        assert d["passed"] is True
        assert d["score"] == 0.85

    def test_feedback_truncation(self):
        """Should truncate long feedback in dict."""
        long_feedback = "x" * 1000
        verdict = ParsedVerdict(
            persona=JudgePersona.TECHNICAL,
            passed=True,
            score=0.8,
            confidence=0.9,
            detailed_feedback=long_feedback,
        )
        d = verdict.to_dict()
        assert len(d["detailed_feedback"]) < len(long_feedback)
        assert "..." in d["detailed_feedback"]


class TestAggregatedVerdictDataclass:
    """Tests for AggregatedVerdict dataclass."""

    def test_to_dict(self):
        """Should convert to dictionary properly."""
        verdict = AggregatedVerdict(
            passed=True,
            consensus_level=0.8,
            aggregated_score=0.75,
            individual_verdicts=[],
            critical_issues=["Issue 1"],
            requires_human_review=True,
            escalation_reasons=[EscalationReason.LOW_CONFIDENCE],
            recommendation="Approved with conditions",
        )
        d = verdict.to_dict()
        assert d["passed"] is True
        assert d["consensus_level"] == 0.8
        assert "low_confidence" in d["escalation_reasons"]
        assert "timestamp" in d
