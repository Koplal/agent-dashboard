"""
Research Agent Output Schemas.

Pydantic models for validating research agent outputs including
source references, claims with provenance, and synthesis.

Version: 2.6.0
"""

from datetime import datetime, timezone
from typing import List, Optional, Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator, ConfigDict

from .base import BaseAgentOutput, ConfidenceLevel, VerificationStatus, utc_now


class SourceReference(BaseModel):
    """Validated source citation with provenance tracking.

    Attributes:
        url: Valid HTTP(S) URL of the source
        title: Title of the source document
        publication_date: When the source was published
        accessed_date: When the source was accessed
        author: Author or organization
        source_type: Classification of source reliability
    """
    model_config = ConfigDict(extra="forbid")

    url: HttpUrl = Field(description="Valid HTTP(S) URL of the source")
    title: str = Field(
        min_length=1,
        max_length=500,
        description="Title of the source document"
    )
    publication_date: Optional[datetime] = Field(
        default=None,
        description="When the source was published"
    )
    accessed_date: datetime = Field(
        default_factory=utc_now,
        description="When the source was accessed"
    )
    author: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Author or organization"
    )
    source_type: Literal["primary", "secondary", "tertiary"] = Field(
        default="secondary",
        description="Classification of source reliability"
    )

    @field_validator("publication_date")
    @classmethod
    def check_publication_date(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Ensure publication date is not in the future."""
        if v is not None:
            now = datetime.now(timezone.utc)
            # Make v timezone-aware if it isn't
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc)
            if v > now:
                raise ValueError("Publication date cannot be in the future")
        return v


class ResearchClaim(BaseModel):
    """Individual research finding with provenance.

    Attributes:
        claim_text: The claim being made
        sources: List of sources supporting the claim
        confidence: Confidence score (0.0 to 1.0)
        verification_status: How well the claim is verified
        recency_flag: Warning if sources are old
        contradictions: Any contradicting information found
    """
    model_config = ConfigDict(extra="forbid")

    claim_text: str = Field(
        min_length=10,
        max_length=2000,
        description="The claim being made"
    )
    sources: List[SourceReference] = Field(
        min_length=1,
        description="List of sources supporting the claim"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0 to 1.0)"
    )
    verification_status: VerificationStatus = Field(
        description="How well the claim is verified"
    )
    recency_flag: Optional[str] = Field(
        default=None,
        description="Warning if sources are old"
    )
    contradictions: List[str] = Field(
        default_factory=list,
        description="Any contradicting information found"
    )

    @model_validator(mode="after")
    def validate_verification_matches_sources(self) -> "ResearchClaim":
        """Ensure verification status is consistent with source count."""
        if len(self.sources) == 1 and self.verification_status == VerificationStatus.VERIFIED:
            raise ValueError(
                "Cannot mark as 'verified' with only a single source. "
                "Use 'single_source' status instead."
            )
        return self

    @model_validator(mode="after")
    def check_recency(self) -> "ResearchClaim":
        """Flag old sources automatically."""
        if self.sources:
            pub_dates = [
                s.publication_date for s in self.sources
                if s.publication_date is not None
            ]
            if pub_dates:
                oldest = min(pub_dates)
                # Ensure timezone-aware comparison
                now = datetime.now(timezone.utc)
                if oldest.tzinfo is None:
                    oldest = oldest.replace(tzinfo=timezone.utc)
                age_days = (now - oldest).days
                if age_days > 180:
                    self.recency_flag = f"oldest_source_{age_days}_days"
        return self


class ResearchOutput(BaseAgentOutput):
    """Complete research agent output schema.

    Attributes:
        query: The research question that was investigated
        claims: List of findings with sources
        synthesis: Integrated summary of findings
        gaps_identified: Areas where information was lacking
        methodology: How the research was conducted
        overall_confidence: Overall confidence in the findings
        recommendations: Suggested next steps or actions
        search_queries_used: Queries used during research
    """
    query: str = Field(
        min_length=5,
        description="The research question that was investigated"
    )
    claims: List[ResearchClaim] = Field(
        default_factory=list,
        description="List of findings with sources"
    )
    synthesis: str = Field(
        min_length=50,
        max_length=10000,
        description="Integrated summary of findings"
    )
    gaps_identified: List[str] = Field(
        default_factory=list,
        description="Areas where information was lacking"
    )
    methodology: str = Field(
        min_length=20,
        max_length=1000,
        description="How the research was conducted"
    )
    overall_confidence: ConfidenceLevel = Field(
        description="Overall confidence in the findings"
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="Suggested next steps or actions"
    )
    search_queries_used: List[str] = Field(
        default_factory=list,
        description="Queries used during research"
    )

    @model_validator(mode="after")
    def validate_confidence_consistency(self) -> "ResearchOutput":
        """Ensure overall confidence aligns with claim confidences."""
        if not self.claims:
            return self

        avg_confidence = sum(c.confidence for c in self.claims) / len(self.claims)

        expected_level = (
            ConfidenceLevel.HIGH if avg_confidence >= 0.7 else
            ConfidenceLevel.MEDIUM if avg_confidence >= 0.4 else
            ConfidenceLevel.LOW
        )

        # Allow one level of divergence
        level_order = [ConfidenceLevel.LOW, ConfidenceLevel.MEDIUM, ConfidenceLevel.HIGH]
        actual_idx = level_order.index(self.overall_confidence)
        expected_idx = level_order.index(expected_level)

        if abs(actual_idx - expected_idx) > 1:
            raise ValueError(
                f"Overall confidence '{self.overall_confidence.value}' diverges significantly "
                f"from claim average ({avg_confidence:.2f} suggests '{expected_level.value}')"
            )

        return self

    @model_validator(mode="after")
    def validate_gaps_if_low_confidence(self) -> "ResearchOutput":
        """Low confidence should identify gaps."""
        if self.overall_confidence == ConfidenceLevel.LOW and not self.gaps_identified:
            raise ValueError(
                "Low confidence output should identify at least one gap in the research"
            )
        return self
