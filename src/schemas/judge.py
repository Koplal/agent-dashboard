"""
Judge Agent Output Schemas.

Pydantic models for validating judge verdicts, panel evaluations,
and quality assessments.

Version: 2.6.0
"""

from typing import List, Optional, Literal, Dict, Any

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

from .base import BaseAgentOutput, ConfidenceLevel, utc_now


class EvaluationScore(BaseModel):
    """Score for a single evaluation dimension.

    Attributes:
        dimension: What is being evaluated
        score: Numeric score (1-5)
        weight: How important this dimension is (0.0-1.0)
        justification: Why this score was given
    """
    model_config = ConfigDict(extra="forbid")

    dimension: str = Field(
        min_length=1,
        max_length=50,
        description="What is being evaluated (e.g., accuracy, completeness)"
    )
    score: int = Field(
        ge=1,
        le=5,
        description="Numeric score (1-5)"
    )
    weight: float = Field(
        ge=0.0,
        le=1.0,
        description="How important this dimension is"
    )
    justification: str = Field(
        min_length=10,
        max_length=500,
        description="Why this score was given"
    )

    @property
    def weighted_score(self) -> float:
        """Calculate the weighted score."""
        return self.score * self.weight


class IssueFound(BaseModel):
    """Issue identified during evaluation.

    Attributes:
        issue: Description of the problem
        severity: How serious the issue is
        location: Where the issue was found (if applicable)
        suggested_fix: How to address the issue
    """
    model_config = ConfigDict(extra="forbid")

    issue: str = Field(
        min_length=5,
        max_length=500,
        description="Description of the problem"
    )
    severity: Literal["critical", "major", "minor", "suggestion"] = Field(
        description="How serious the issue is"
    )
    location: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Where the issue was found"
    )
    suggested_fix: Optional[str] = Field(
        default=None,
        max_length=500,
        description="How to address the issue"
    )


class JudgeVerdict(BaseModel):
    """Individual judge's evaluation.

    Attributes:
        judge_type: Type of judge (adversarial, rubric, domain_expert, etc.)
        passed: Whether the content passed evaluation
        overall_score: Aggregate score (0.0-1.0)
        dimension_scores: Scores for individual dimensions
        issues_found: Problems identified
        strengths_noted: Positive aspects found
        detailed_feedback: Full evaluation narrative
        confidence: How confident the judge is
    """
    model_config = ConfigDict(extra="forbid")

    judge_type: Literal[
        "adversarial",
        "rubric_based",
        "domain_expert",
        "end_user",
        "skeptic",
        "technical",
        "completeness",
        "practicality"
    ] = Field(description="Type of judge perspective")
    passed: bool = Field(description="Whether the content passed evaluation")
    overall_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Aggregate score (0.0-1.0)"
    )
    dimension_scores: List[EvaluationScore] = Field(
        default_factory=list,
        description="Scores for individual dimensions"
    )
    issues_found: List[IssueFound] = Field(
        default_factory=list,
        description="Problems identified"
    )
    strengths_noted: List[str] = Field(
        default_factory=list,
        description="Positive aspects found"
    )
    detailed_feedback: str = Field(
        min_length=50,
        max_length=3000,
        description="Full evaluation narrative"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="How confident the judge is"
    )

    @model_validator(mode="after")
    def validate_score_consistency(self) -> "JudgeVerdict":
        """Ensure pass/fail aligns with score."""
        if self.passed and self.overall_score < 0.5:
            raise ValueError(
                f"Marked as passed but score ({self.overall_score}) is below 0.5"
            )
        if not self.passed and self.overall_score >= 0.7:
            raise ValueError(
                f"Marked as failed but score ({self.overall_score}) is 0.7 or above"
            )
        return self

    @model_validator(mode="after")
    def validate_critical_issues_fail(self) -> "JudgeVerdict":
        """Critical issues should result in failure."""
        critical_issues = [i for i in self.issues_found if i.severity == "critical"]
        if critical_issues and self.passed:
            raise ValueError(
                "Cannot pass with critical issues present"
            )
        return self


class PanelVerdict(BaseModel):
    """Aggregated verdict from judge panel.

    Attributes:
        passed: Whether the panel approved the content
        consensus_level: Level of agreement (0.0-1.0)
        individual_verdicts: Each judge's verdict
        critical_issues: Issues found by multiple judges
        aggregated_score: Combined score from all judges
        requires_human_review: Whether human should review
        recommendation: Final recommendation
        dissenting_opinions: Judges who disagreed with majority
    """
    model_config = ConfigDict(extra="forbid")

    passed: bool = Field(description="Whether the panel approved the content")
    consensus_level: float = Field(
        ge=0.0,
        le=1.0,
        description="Level of agreement among judges"
    )
    individual_verdicts: List[JudgeVerdict] = Field(
        min_length=1,
        description="Each judge's verdict"
    )
    critical_issues: List[str] = Field(
        default_factory=list,
        description="Issues found by multiple judges"
    )
    aggregated_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Combined score from all judges"
    )
    requires_human_review: bool = Field(
        default=False,
        description="Whether human should review"
    )
    recommendation: str = Field(
        min_length=10,
        max_length=500,
        description="Final recommendation"
    )
    dissenting_opinions: List[str] = Field(
        default_factory=list,
        description="Summary of dissenting views"
    )

    @model_validator(mode="after")
    def validate_consensus_calculation(self) -> "PanelVerdict":
        """Verify consensus level matches individual verdicts."""
        if not self.individual_verdicts:
            return self

        pass_count = sum(1 for v in self.individual_verdicts if v.passed)
        calculated_consensus = pass_count / len(self.individual_verdicts)

        # Allow small floating point differences
        if abs(calculated_consensus - self.consensus_level) > 0.01:
            raise ValueError(
                f"consensus_level ({self.consensus_level}) doesn't match "
                f"calculated value ({calculated_consensus:.2f})"
            )
        return self

    @model_validator(mode="after")
    def validate_human_review_trigger(self) -> "PanelVerdict":
        """Flag for human review when judges disagree significantly."""
        if 0.3 < self.consensus_level < 0.7:
            self.requires_human_review = True
        if any(v.confidence < 0.5 for v in self.individual_verdicts):
            self.requires_human_review = True
        return self

    @model_validator(mode="after")
    def validate_dissent_recorded(self) -> "PanelVerdict":
        """Record dissenting opinions when consensus is not unanimous."""
        if self.consensus_level < 1.0 and not self.dissenting_opinions:
            # Auto-generate dissent summary
            minority_passed = self.passed
            dissenters = [
                v.judge_type for v in self.individual_verdicts
                if v.passed != minority_passed
            ]
            if dissenters:
                self.dissenting_opinions = [
                    f"{judge} disagreed with majority verdict"
                    for judge in dissenters[:3]
                ]
        return self


class JudgeOutput(BaseAgentOutput):
    """Complete judge agent output schema.

    Attributes:
        content_evaluated: What was being evaluated
        content_type: Type of content (research, code, documentation)
        evaluation_criteria: What criteria were used
        verdict: The judge's verdict
        evaluation_duration_ms: Time spent evaluating
    """
    content_evaluated: str = Field(
        min_length=1,
        max_length=50000,
        description="What was being evaluated (may be truncated)"
    )
    content_type: Literal["research", "code", "documentation", "synthesis", "other"] = Field(
        description="Type of content being evaluated"
    )
    evaluation_criteria: List[str] = Field(
        min_length=1,
        description="What criteria were used"
    )
    verdict: JudgeVerdict = Field(description="The judge's verdict")
    evaluation_duration_ms: int = Field(
        ge=0,
        description="Time spent evaluating"
    )
