"""
Unit tests for Pydantic Schemas and Validators.

Tests schema validation, field constraints, and cross-field validators.

Version: 2.6.0
"""

import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from src.schemas.base import (
    ConfidenceLevel,
    VerificationStatus,
    BaseAgentOutput,
    Severity,
)
from src.schemas.research import (
    SourceReference,
    ResearchClaim,
    ResearchOutput,
)
from src.schemas.code_analysis import (
    CodeLocation,
    CodeIssue,
    CodeAnalysisOutput,
    CodeMetrics,
)
from src.schemas.orchestration import (
    AgentSelection,
    DelegationDecision,
    OrchestrationOutput,
)
from src.schemas.judge import (
    EvaluationScore,
    JudgeVerdict,
    PanelVerdict,
    IssueFound,
)
from src.validators.output_validator import (
    OutputValidator,
    ValidationResult,
    ValidationErrorInfo,
    validate_output,
)


class TestConfidenceLevel:
    """Tests for ConfidenceLevel enum."""

    def test_all_levels_exist(self):
        """Test all confidence levels are defined."""
        assert ConfidenceLevel.HIGH.value == "high"
        assert ConfidenceLevel.MEDIUM.value == "medium"
        assert ConfidenceLevel.LOW.value == "low"


class TestVerificationStatus:
    """Tests for VerificationStatus enum."""

    def test_all_statuses_exist(self):
        """Test all verification statuses are defined."""
        assert VerificationStatus.VERIFIED.value == "verified"
        assert VerificationStatus.SINGLE_SOURCE.value == "single_source"
        assert VerificationStatus.UNVERIFIED.value == "unverified"
        assert VerificationStatus.CONTRADICTED.value == "contradicted"


class TestBaseAgentOutput:
    """Tests for BaseAgentOutput schema."""

    def test_valid_output(self):
        """Test valid base output creation."""
        output = BaseAgentOutput(
            agent_id="test-agent",
            task_id="task-123",
            execution_time_ms=100,
            token_count=50,
        )
        assert output.agent_id == "test-agent"
        assert output.task_id == "task-123"
        assert output.execution_time_ms == 100
        assert output.token_count == 50
        assert output.timestamp is not None

    def test_empty_agent_id_fails(self):
        """Test that empty agent_id is rejected."""
        with pytest.raises(ValidationError):
            BaseAgentOutput(
                agent_id="",
                task_id="task-123",
                execution_time_ms=100,
                token_count=50,
            )

    def test_negative_execution_time_fails(self):
        """Test that negative execution time is rejected."""
        with pytest.raises(ValidationError):
            BaseAgentOutput(
                agent_id="test",
                task_id="task-123",
                execution_time_ms=-1,
                token_count=50,
            )

    def test_extra_fields_rejected(self):
        """Test that extra fields are rejected in strict mode."""
        with pytest.raises(ValidationError):
            BaseAgentOutput(
                agent_id="test",
                task_id="task-123",
                execution_time_ms=100,
                token_count=50,
                extra_field="should fail",
            )


class TestSourceReference:
    """Tests for SourceReference schema."""

    def test_valid_source(self):
        """Test valid source reference creation."""
        source = SourceReference(
            url="https://example.com/article",
            title="Test Article",
        )
        assert str(source.url) == "https://example.com/article"
        assert source.title == "Test Article"
        assert source.source_type == "secondary"

    def test_invalid_url_fails(self):
        """Test that invalid URLs are rejected."""
        with pytest.raises(ValidationError):
            SourceReference(
                url="not-a-url",
                title="Test",
            )

    def test_future_publication_date_fails(self):
        """Test that future publication dates are rejected."""
        future = datetime.now(timezone.utc) + timedelta(days=30)
        with pytest.raises(ValidationError):
            SourceReference(
                url="https://example.com",
                title="Test",
                publication_date=future,
            )

    def test_empty_title_fails(self):
        """Test that empty titles are rejected."""
        with pytest.raises(ValidationError):
            SourceReference(
                url="https://example.com",
                title="",
            )


class TestResearchClaim:
    """Tests for ResearchClaim schema."""

    @pytest.fixture
    def valid_source(self):
        """Create a valid source for testing."""
        return SourceReference(
            url="https://example.com/source",
            title="Test Source",
        )

    def test_valid_claim(self, valid_source):
        """Test valid claim creation."""
        claim = ResearchClaim(
            claim_text="This is a valid research claim with sufficient length.",
            sources=[valid_source],
            confidence=0.8,
            verification_status=VerificationStatus.SINGLE_SOURCE,
        )
        assert claim.confidence == 0.8
        assert len(claim.sources) == 1

    def test_claim_too_short_fails(self, valid_source):
        """Test that short claims are rejected."""
        with pytest.raises(ValidationError):
            ResearchClaim(
                claim_text="Short",
                sources=[valid_source],
                confidence=0.8,
                verification_status=VerificationStatus.SINGLE_SOURCE,
            )

    def test_verified_with_single_source_fails(self, valid_source):
        """Test that verified status with single source fails."""
        with pytest.raises(ValidationError) as exc_info:
            ResearchClaim(
                claim_text="This is a claim that should not be verified.",
                sources=[valid_source],
                confidence=0.9,
                verification_status=VerificationStatus.VERIFIED,
            )
        assert "single source" in str(exc_info.value).lower()

    def test_confidence_out_of_range_fails(self, valid_source):
        """Test that confidence outside 0-1 is rejected."""
        with pytest.raises(ValidationError):
            ResearchClaim(
                claim_text="This is a valid claim text.",
                sources=[valid_source],
                confidence=1.5,
                verification_status=VerificationStatus.SINGLE_SOURCE,
            )

    def test_recency_flag_auto_set(self):
        """Test that old sources get recency flag."""
        old_date = datetime.now(timezone.utc) - timedelta(days=200)
        source = SourceReference(
            url="https://example.com",
            title="Old Source",
            publication_date=old_date,
        )
        claim = ResearchClaim(
            claim_text="This claim uses an old source that should be flagged.",
            sources=[source],
            confidence=0.5,
            verification_status=VerificationStatus.SINGLE_SOURCE,
        )
        assert claim.recency_flag is not None
        assert "200" in claim.recency_flag


class TestResearchOutput:
    """Tests for ResearchOutput schema."""

    @pytest.fixture
    def valid_claim(self):
        """Create a valid claim for testing."""
        source = SourceReference(
            url="https://example.com",
            title="Test Source",
        )
        return ResearchClaim(
            claim_text="This is a valid research claim for testing.",
            sources=[source],
            confidence=0.8,
            verification_status=VerificationStatus.SINGLE_SOURCE,
        )

    def test_valid_research_output(self, valid_claim):
        """Test valid research output creation."""
        output = ResearchOutput(
            agent_id="researcher",
            task_id="task-123",
            execution_time_ms=5000,
            token_count=1000,
            query="What is the best practice for X?",
            claims=[valid_claim],
            synthesis="This is a comprehensive synthesis of the research findings. "
                     "The evidence suggests that the approach is valid and well-supported.",
            methodology="Searched academic databases and official documentation.",
            overall_confidence=ConfidenceLevel.HIGH,
        )
        assert output.query == "What is the best practice for X?"
        assert len(output.claims) == 1

    def test_confidence_consistency_validation(self):
        """Test that overall confidence must match claim confidences."""
        source = SourceReference(url="https://example.com", title="Test")
        low_confidence_claim = ResearchClaim(
            claim_text="This claim has low confidence due to weak evidence.",
            sources=[source],
            confidence=0.2,
            verification_status=VerificationStatus.UNVERIFIED,
        )

        with pytest.raises(ValidationError) as exc_info:
            ResearchOutput(
                agent_id="researcher",
                task_id="task-123",
                execution_time_ms=1000,
                token_count=500,
                query="Test query for validation",
                claims=[low_confidence_claim],
                synthesis="This synthesis should fail because confidence is inconsistent. "
                         "The overall confidence is high but the claims are low.",
                methodology="Basic search methodology",
                overall_confidence=ConfidenceLevel.HIGH,
                gaps_identified=["Gap 1"],
            )
        assert "diverges" in str(exc_info.value).lower()

    def test_low_confidence_requires_gaps(self):
        """Test that low confidence output must identify gaps."""
        with pytest.raises(ValidationError) as exc_info:
            ResearchOutput(
                agent_id="researcher",
                task_id="task-123",
                execution_time_ms=1000,
                token_count=500,
                query="Test query for gaps validation",
                claims=[],
                synthesis="This synthesis has low confidence but doesn't identify gaps. "
                         "This should fail the validation check.",
                methodology="Limited search methodology",
                overall_confidence=ConfidenceLevel.LOW,
            )
        assert "gap" in str(exc_info.value).lower()


class TestCodeLocation:
    """Tests for CodeLocation schema."""

    def test_valid_location(self):
        """Test valid code location creation."""
        loc = CodeLocation(
            file_path="src/main.py",
            start_line=10,
            end_line=20,
        )
        assert loc.file_path == "src/main.py"
        assert loc.start_line == 10
        assert loc.end_line == 20

    def test_end_before_start_fails(self):
        """Test that end_line before start_line fails."""
        with pytest.raises(ValidationError) as exc_info:
            CodeLocation(
                file_path="src/main.py",
                start_line=20,
                end_line=10,
            )
        assert "start_line" in str(exc_info.value).lower()

    def test_line_zero_fails(self):
        """Test that line 0 is rejected (1-indexed)."""
        with pytest.raises(ValidationError):
            CodeLocation(
                file_path="src/main.py",
                start_line=0,
                end_line=10,
            )


class TestCodeIssue:
    """Tests for CodeIssue schema."""

    def test_valid_issue(self):
        """Test valid code issue creation."""
        issue = CodeIssue(
            issue_type="bug",
            severity="high",
            location=CodeLocation(
                file_path="src/main.py",
                start_line=10,
                end_line=15,
            ),
            description="This function may cause a null pointer exception.",
            confidence=0.9,
        )
        assert issue.issue_type == "bug"
        assert issue.severity == "high"


class TestCodeAnalysisOutput:
    """Tests for CodeAnalysisOutput schema."""

    def test_valid_analysis_output(self):
        """Test valid code analysis output."""
        output = CodeAnalysisOutput(
            agent_id="code-analyzer",
            task_id="task-123",
            execution_time_ms=3000,
            token_count=800,
            target_files=["src/main.py"],
            summary="No critical issues found. Code follows best practices overall.",
            analysis_depth="standard",
        )
        assert len(output.target_files) == 1
        assert output.analysis_depth == "standard"

    def test_deep_analysis_requires_metrics(self):
        """Test that deep analysis must include metrics."""
        with pytest.raises(ValidationError) as exc_info:
            CodeAnalysisOutput(
                agent_id="code-analyzer",
                task_id="task-123",
                execution_time_ms=5000,
                token_count=1500,
                target_files=["src/main.py"],
                summary="Deep analysis performed but no metrics provided.",
                analysis_depth="deep",
            )
        assert "metrics" in str(exc_info.value).lower()

    def test_issues_sorted_by_severity(self):
        """Test that issues are sorted by severity."""
        output = CodeAnalysisOutput(
            agent_id="code-analyzer",
            task_id="task-123",
            execution_time_ms=2000,
            token_count=600,
            target_files=["src/main.py"],
            issues_found=[
                CodeIssue(
                    issue_type="style",
                    severity="low",
                    location=CodeLocation(file_path="a.py", start_line=1, end_line=1),
                    description="Minor style issue here",
                    confidence=0.8,
                ),
                CodeIssue(
                    issue_type="bug",
                    severity="critical",
                    location=CodeLocation(file_path="b.py", start_line=1, end_line=1),
                    description="Critical bug found in this location",
                    confidence=0.95,
                ),
            ],
            summary="Found issues of varying severity.",
            analysis_depth="standard",
        )
        assert output.issues_found[0].severity == "critical"
        assert output.issues_found[1].severity == "low"


class TestJudgeVerdict:
    """Tests for JudgeVerdict schema."""

    def test_valid_verdict(self):
        """Test valid judge verdict creation."""
        verdict = JudgeVerdict(
            judge_type="rubric_based",
            passed=True,
            overall_score=0.85,
            detailed_feedback="The output meets all criteria and is well-structured. "
                            "Minor improvements could be made but overall quality is high.",
            confidence=0.9,
        )
        assert verdict.passed is True
        assert verdict.overall_score == 0.85

    def test_passed_with_low_score_fails(self):
        """Test that passed=True with low score fails."""
        with pytest.raises(ValidationError) as exc_info:
            JudgeVerdict(
                judge_type="adversarial",
                passed=True,
                overall_score=0.3,
                detailed_feedback="This verdict is inconsistent - marked as passed but score is low.",
                confidence=0.8,
            )
        assert "score" in str(exc_info.value).lower()

    def test_failed_with_high_score_fails(self):
        """Test that passed=False with high score fails."""
        with pytest.raises(ValidationError) as exc_info:
            JudgeVerdict(
                judge_type="technical",
                passed=False,
                overall_score=0.8,
                detailed_feedback="This verdict is inconsistent - marked as failed but score is high.",
                confidence=0.8,
            )
        assert "score" in str(exc_info.value).lower()

    def test_critical_issue_must_fail(self):
        """Test that critical issues must result in failure."""
        with pytest.raises(ValidationError) as exc_info:
            JudgeVerdict(
                judge_type="technical",
                passed=True,
                overall_score=0.7,
                issues_found=[
                    IssueFound(
                        issue="Critical security vulnerability",
                        severity="critical",
                    ),
                ],
                detailed_feedback="Despite critical issues, the overall quality was marked as passing.",
                confidence=0.9,
            )
        assert "critical" in str(exc_info.value).lower()


class TestPanelVerdict:
    """Tests for PanelVerdict schema."""

    @pytest.fixture
    def passing_verdict(self):
        """Create a passing verdict."""
        return JudgeVerdict(
            judge_type="rubric_based",
            passed=True,
            overall_score=0.8,
            detailed_feedback="The content meets all criteria and passes review successfully.",
            confidence=0.9,
        )

    @pytest.fixture
    def failing_verdict(self):
        """Create a failing verdict."""
        return JudgeVerdict(
            judge_type="adversarial",
            passed=False,
            overall_score=0.4,
            detailed_feedback="The content has significant issues that require attention.",
            confidence=0.85,
        )

    def test_valid_panel_verdict(self, passing_verdict):
        """Test valid panel verdict creation."""
        panel = PanelVerdict(
            passed=True,
            consensus_level=1.0,
            individual_verdicts=[passing_verdict],
            aggregated_score=0.8,
            recommendation="Approved - all judges agree.",
        )
        assert panel.passed is True
        assert panel.consensus_level == 1.0

    def test_consensus_calculation_validated(self, passing_verdict, failing_verdict):
        """Test that consensus level is validated."""
        with pytest.raises(ValidationError) as exc_info:
            PanelVerdict(
                passed=True,
                consensus_level=1.0,  # Wrong - should be 0.5
                individual_verdicts=[passing_verdict, failing_verdict],
                aggregated_score=0.6,
                recommendation="Inconsistent consensus level.",
            )
        assert "consensus" in str(exc_info.value).lower()


class TestOutputValidator:
    """Tests for OutputValidator service."""

    @pytest.fixture
    def validator(self):
        """Create a validator instance."""
        return OutputValidator()

    def test_validate_valid_output(self, validator):
        """Test validating valid output."""
        result = validator.validate(
            raw_output={
                "agent_id": "test",
                "task_id": "task-1",
                "execution_time_ms": 100,
                "token_count": 50,
            },
            schema=BaseAgentOutput,
            agent_id="test",
            task_id="task-1",
        )
        assert result.success is True
        assert result.validated_output is not None
        assert result.validated_output.agent_id == "test"

    def test_validate_json_string(self, validator):
        """Test validating JSON string input."""
        json_str = '{"agent_id": "test", "task_id": "task-1", "execution_time_ms": 100, "token_count": 50}'
        result = validator.validate(
            raw_output=json_str,
            schema=BaseAgentOutput,
            agent_id="test",
            task_id="task-1",
        )
        assert result.success is True

    def test_validate_invalid_json(self, validator):
        """Test handling of invalid JSON."""
        result = validator.validate(
            raw_output="not valid json {",
            schema=BaseAgentOutput,
            agent_id="test",
            task_id="task-1",
        )
        assert result.success is False
        assert len(result.errors) == 1
        assert result.errors[0].error_type == "json_parse_error"

    def test_validate_schema_error(self, validator):
        """Test handling of schema validation errors."""
        result = validator.validate(
            raw_output={"agent_id": "", "task_id": "task-1"},
            schema=BaseAgentOutput,
            agent_id="test",
            task_id="task-1",
        )
        assert result.success is False
        assert len(result.errors) > 0

    def test_metadata_injection(self, validator):
        """Test that metadata is injected when missing."""
        result = validator.validate(
            raw_output={},
            schema=BaseAgentOutput,
            agent_id="injected-agent",
            task_id="injected-task",
            inject_metadata=True,
        )
        assert result.success is True
        assert result.validated_output.agent_id == "injected-agent"
        assert result.validated_output.task_id == "injected-task"

    def test_generate_retry_prompt(self, validator):
        """Test retry prompt generation."""
        errors = [
            ValidationErrorInfo(
                agent_id="test",
                task_id="task-1",
                error_type="missing_field",
                field_path="synthesis",
                message="Field required",
            ),
        ]
        prompt = validator.generate_retry_prompt(errors, "Original prompt")
        assert "synthesis" in prompt
        assert "Field required" in prompt
        assert "Original prompt" in prompt

    def test_error_history_tracking(self, validator):
        """Test that errors are tracked in history."""
        validator.validate(
            raw_output={"invalid": "data"},
            schema=BaseAgentOutput,
            agent_id="test",
            task_id="task-1",
        )
        assert len(validator.error_history) > 0
        assert validator.validation_count == 1
        assert validator.success_count == 0

    def test_get_stats(self, validator):
        """Test statistics retrieval."""
        # Perform some validations
        validator.validate(
            raw_output={
                "agent_id": "test",
                "task_id": "task-1",
                "execution_time_ms": 100,
                "token_count": 50,
            },
            schema=BaseAgentOutput,
            agent_id="test",
            task_id="task-1",
        )
        validator.validate(
            raw_output={"invalid": "data"},
            schema=BaseAgentOutput,
            agent_id="test",
            task_id="task-2",
        )

        stats = validator.get_stats()
        assert stats["total_validations"] == 2
        assert stats["successful_validations"] == 1
        assert stats["failed_validations"] == 1
        assert stats["success_rate"] == 0.5


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_validate_output_function(self):
        """Test the validate_output convenience function."""
        result = validate_output(
            raw_output={
                "agent_id": "test",
                "task_id": "task-1",
                "execution_time_ms": 100,
                "token_count": 50,
            },
            schema=BaseAgentOutput,
            agent_id="test",
            task_id="task-1",
        )
        assert result.success is True
