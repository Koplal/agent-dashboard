#!/usr/bin/env python3
"""
validation.py - Base validation classes for agent handoffs and compression gating.

This module provides:
- HandoffSchema: Required fields for agent-to-agent communication
- ValidationResult: Results from validation operations
- ValidationAction: Actions to take based on validation
- Validator: Abstract base class for validators

These classes enforce the handoff format required between agent tiers
to ensure proper compression and context management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Optional, Dict, List, Any, Set
from abc import ABC, abstractmethod


# ============================================================================
# ENUMS
# ============================================================================

class ValidationAction(Enum):
    """Actions that can be taken based on validation results."""
    ACCEPT = auto()      # Input is valid, proceed
    REJECT = auto()      # Input invalid, return with feedback
    AUTO_ROUTE = auto()  # Route to summarizer for compression
    ESCALATE = auto()    # Escalate to senior agent


class Confidence(Enum):
    """Confidence levels for findings."""
    HIGH = "H"
    MEDIUM = "M"
    LOW = "L"


class AgentTier(Enum):
    """Model tier assignments for cost governance."""
    OPUS = "opus"       # Strategic, quality-critical tasks
    SONNET = "sonnet"   # Analysis, research tasks
    HAIKU = "haiku"     # Execution, routine tasks


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class Finding:
    """A single finding with confidence level."""
    finding: str
    confidence: Confidence
    source: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding": self.finding,
            "confidence": self.confidence.value if isinstance(self.confidence, Confidence) else self.confidence,
            "source": self.source
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Finding":
        conf = data.get("confidence", "M")
        if isinstance(conf, str):
            conf = Confidence(conf) if conf in ["H", "M", "L"] else Confidence.MEDIUM
        return cls(
            finding=data.get("finding", ""),
            confidence=conf,
            source=data.get("source")
        )


@dataclass
class HandoffSchema:
    """
    Required schema for agent-to-agent handoffs.

    This schema enforces the standard format for passing information
    between agents, ensuring proper compression and context management.

    Required fields:
    - task_id: Unique identifier for the task
    - outcome: 1-2 sentence summary of what was accomplished
    - key_findings: Array of 1-5 findings with confidence levels
    - confidence: Overall confidence level (H/M/L)

    Optional fields:
    - sources: List of sources consulted
    - gaps: What couldn't be determined
    - recommendations: Specific action recommendations
    - token_count: Number of tokens in this handoff
    - compression_ratio: Ratio of original to compressed content
    """
    task_id: str
    outcome: str
    key_findings: List[Finding]
    confidence: Confidence

    # Optional fields
    sources: Optional[List[str]] = None
    gaps: Optional[List[str]] = None
    recommendations: Optional[List[str]] = None
    token_count: Optional[int] = None
    compression_ratio: Optional[float] = None
    agent_name: Optional[str] = None
    model_tier: Optional[AgentTier] = None
    duration_seconds: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)

    # Required fields list for validation
    REQUIRED_FIELDS: List[str] = field(default_factory=lambda: ["task_id", "outcome", "key_findings", "confidence"], repr=False)

    def is_valid(self) -> bool:
        """Check if all required fields are present and valid."""
        if not self.task_id or not isinstance(self.task_id, str):
            return False
        if not self.outcome or not isinstance(self.outcome, str):
            return False
        if not self.key_findings or not isinstance(self.key_findings, list):
            return False
        if len(self.key_findings) < 1 or len(self.key_findings) > 5:
            return False
        if not self.confidence:
            return False
        return True

    def get_missing_fields(self) -> Set[str]:
        """Get set of missing required fields."""
        missing = set()
        if not self.task_id:
            missing.add("task_id")
        if not self.outcome:
            missing.add("outcome")
        if not self.key_findings:
            missing.add("key_findings")
        if not self.confidence:
            missing.add("confidence")
        return missing

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "outcome": self.outcome,
            "key_findings": [f.to_dict() if isinstance(f, Finding) else f for f in self.key_findings],
            "confidence": self.confidence.value if isinstance(self.confidence, Confidence) else self.confidence,
            "sources": self.sources,
            "gaps": self.gaps,
            "recommendations": self.recommendations,
            "token_count": self.token_count,
            "compression_ratio": self.compression_ratio,
            "agent_name": self.agent_name,
            "model_tier": self.model_tier.value if self.model_tier else None,
            "duration_seconds": self.duration_seconds,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HandoffSchema":
        """Create HandoffSchema from dictionary."""
        findings = []
        for f in data.get("key_findings", []):
            if isinstance(f, dict):
                findings.append(Finding.from_dict(f))
            elif isinstance(f, Finding):
                findings.append(f)

        conf = data.get("confidence", "M")
        if isinstance(conf, str):
            conf = Confidence(conf) if conf in ["H", "M", "L"] else Confidence.MEDIUM

        tier = data.get("model_tier")
        if isinstance(tier, str):
            tier = AgentTier(tier) if tier in ["opus", "sonnet", "haiku"] else None

        return cls(
            task_id=data.get("task_id", ""),
            outcome=data.get("outcome", ""),
            key_findings=findings,
            confidence=conf,
            sources=data.get("sources"),
            gaps=data.get("gaps"),
            recommendations=data.get("recommendations"),
            token_count=data.get("token_count"),
            compression_ratio=data.get("compression_ratio"),
            agent_name=data.get("agent_name"),
            model_tier=tier,
            duration_seconds=data.get("duration_seconds"),
        )

    def to_markdown(self) -> str:
        """Convert to standard markdown handoff format."""
        lines = [
            f"## Task Completion: {self.task_id}",
            "",
            f"**Agent:** {self.agent_name or 'unknown'} | **Model:** {self.model_tier.value if self.model_tier else 'unknown'} | **Duration:** {self.duration_seconds or 0:.1f}s",
            "",
            "### Outcome",
            self.outcome,
            "",
            f"### Key Findings (max 5)",
        ]

        for i, finding in enumerate(self.key_findings, 1):
            conf = finding.confidence.value if isinstance(finding.confidence, Confidence) else finding.confidence
            lines.append(f"{i}. {finding.finding} - Confidence: {conf}")

        if self.recommendations:
            lines.extend(["", "### Recommended Actions"])
            for i, rec in enumerate(self.recommendations, 1):
                lines.append(f"{i}. {rec}")

        if self.gaps:
            lines.extend(["", "### Gaps/Uncertainties"])
            for gap in self.gaps:
                lines.append(f"- {gap}")

        lines.extend([
            "",
            "---",
            f"**Tokens:** {self.token_count or 'N/A'} | **Compression:** {self.compression_ratio or 'N/A'}:1"
        ])

        return "\n".join(lines)


@dataclass
class ValidationResult:
    """Result from a validation operation."""
    valid: bool
    action: ValidationAction = ValidationAction.ACCEPT
    reason: Optional[str] = None
    missing: Optional[Set[str]] = None
    suggestion: Optional[str] = None
    loop_count: int = 1
    routed_to: Optional[str] = None
    escalate_to: Optional[str] = None
    feedback: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "action": self.action.name,
            "reason": self.reason,
            "missing": list(self.missing) if self.missing else None,
            "suggestion": self.suggestion,
            "loop_count": self.loop_count,
            "routed_to": self.routed_to,
            "escalate_to": self.escalate_to,
            "feedback": self.feedback,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class GateResult:
    """Result from compression gate validation."""
    action: ValidationAction
    tokens: int = 0
    budget: int = 0
    ratio: float = 0.0
    routed_to: Optional[str] = None
    feedback: Optional[str] = None
    original_size: int = 0
    compressed_size: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action.name,
            "tokens": self.tokens,
            "budget": self.budget,
            "ratio": self.ratio,
            "routed_to": self.routed_to,
            "feedback": self.feedback,
            "original_size": self.original_size,
            "compressed_size": self.compressed_size,
        }


# ============================================================================
# ABSTRACT BASE CLASSES
# ============================================================================

class Validator(ABC):
    """Abstract base class for validators."""

    @abstractmethod
    def validate(self, input_data: Any, **kwargs) -> ValidationResult:
        """
        Validate input data.

        Args:
            input_data: The data to validate
            **kwargs: Additional validation parameters

        Returns:
            ValidationResult with action to take
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get the name of this validator."""
        pass


# ============================================================================
# VALIDATION ERROR
# ============================================================================

class ValidationError(Exception):
    """Exception raised when validation fails."""

    def __init__(self, message: str, missing_fields: Optional[Set[str]] = None):
        super().__init__(message)
        self.missing_fields = missing_fields or set()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_handoff(
    task_id: str,
    outcome: str,
    findings: List[Dict[str, str]],
    confidence: str = "M",
    **kwargs
) -> HandoffSchema:
    """
    Helper function to create a HandoffSchema from simple inputs.

    Args:
        task_id: Unique task identifier
        outcome: 1-2 sentence summary
        findings: List of dicts with 'finding' and 'confidence' keys
        confidence: Overall confidence (H/M/L)
        **kwargs: Additional optional fields

    Returns:
        HandoffSchema instance
    """
    finding_objs = []
    for f in findings:
        conf = f.get("confidence", "M")
        if isinstance(conf, str):
            conf = Confidence(conf) if conf in ["H", "M", "L"] else Confidence.MEDIUM
        finding_objs.append(Finding(
            finding=f.get("finding", ""),
            confidence=conf,
            source=f.get("source")
        ))

    conf_enum = Confidence(confidence) if confidence in ["H", "M", "L"] else Confidence.MEDIUM

    return HandoffSchema(
        task_id=task_id,
        outcome=outcome,
        key_findings=finding_objs,
        confidence=conf_enum,
        **kwargs
    )


def validate_handoff_dict(data: Dict[str, Any]) -> ValidationResult:
    """
    Validate a dictionary against HandoffSchema requirements.

    Args:
        data: Dictionary to validate

    Returns:
        ValidationResult indicating if data is valid
    """
    required = {"task_id", "outcome", "key_findings", "confidence"}
    missing = set()

    for field in required:
        if field not in data or not data[field]:
            missing.add(field)

    # Validate key_findings structure
    if "key_findings" in data and data["key_findings"]:
        findings = data["key_findings"]
        if not isinstance(findings, list):
            missing.add("key_findings")
        elif len(findings) < 1 or len(findings) > 5:
            return ValidationResult(
                valid=False,
                action=ValidationAction.REJECT,
                reason="key_findings must have 1-5 items",
                missing=missing
            )

    if missing:
        return ValidationResult(
            valid=False,
            action=ValidationAction.REJECT,
            reason=f"Missing required fields: {', '.join(missing)}",
            missing=missing,
            suggestion=f"Please provide: {', '.join(missing)}"
        )

    return ValidationResult(valid=True, action=ValidationAction.ACCEPT)
