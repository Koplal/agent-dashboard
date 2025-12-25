"""
Base Schema Classes for Agent Output Validation.

Provides foundational types and base models used across all agent schemas.

Version: 2.6.0
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


def utc_now() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class ConfidenceLevel(str, Enum):
    """Confidence levels for claims and outputs."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class VerificationStatus(str, Enum):
    """Verification status for claims."""
    VERIFIED = "verified"           # Multiple independent sources confirm
    SINGLE_SOURCE = "single_source" # Only one source available
    UNVERIFIED = "unverified"       # No sources found
    CONTRADICTED = "contradicted"   # Sources disagree


class Severity(str, Enum):
    """Severity levels for issues."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class BaseAgentOutput(BaseModel):
    """Base schema for all agent outputs.

    All agent output schemas should inherit from this base class
    to ensure consistent metadata across the system.

    Attributes:
        agent_id: Identifier of the agent that produced this output
        timestamp: When the output was generated (UTC)
        task_id: Identifier of the task this output responds to
        execution_time_ms: Time taken to generate this output
        token_count: Number of tokens consumed
        model_used: Optional model identifier used for generation
    """
    model_config = ConfigDict(
        extra="forbid",  # Reject unexpected fields
        str_strip_whitespace=True,
    )

    agent_id: str = Field(
        min_length=1,
        description="Identifier of the agent that produced this output"
    )
    timestamp: datetime = Field(
        default_factory=utc_now,
        description="When the output was generated (UTC)"
    )
    task_id: str = Field(
        min_length=1,
        description="Identifier of the task this output responds to"
    )
    execution_time_ms: int = Field(
        ge=0,
        description="Time taken to generate this output in milliseconds"
    )
    token_count: int = Field(
        ge=0,
        description="Number of tokens consumed"
    )
    model_used: Optional[str] = Field(
        default=None,
        description="Model identifier used for generation"
    )


class ErrorDetail(BaseModel):
    """Structured error information."""
    model_config = ConfigDict(extra="forbid")

    error_type: str = Field(min_length=1)
    message: str = Field(min_length=1)
    field_path: Optional[str] = None
    suggestion: Optional[str] = None


class ValidationResult(BaseModel):
    """Result of a validation operation."""
    model_config = ConfigDict(extra="forbid")

    valid: bool
    errors: list[ErrorDetail] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    validated_at: datetime = Field(default_factory=utc_now)
