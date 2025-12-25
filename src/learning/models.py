"""
Learning Data Models.

Provides data structures for extracted rules and execution outcomes.

Version: 2.6.0
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from enum import Enum


class RuleCategory(str, Enum):
    """Categories for extracted rules."""
    RESEARCH = "research"
    CODE = "code"
    ANALYSIS = "analysis"
    SYNTHESIS = "synthesis"
    VALIDATION = "validation"
    GENERAL = "general"


class RuleStatus(str, Enum):
    """Status of an extracted rule."""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    PRUNED = "pruned"
    PENDING_REVIEW = "pending_review"


@dataclass
class ExtractedRule:
    """
    Rule extracted from successful execution.

    Represents a generalizable pattern learned from successful agent executions.
    Rules have conditions (when to apply), recommendations (what to do), and
    reasoning (why it works).

    Attributes:
        id: Unique identifier for the rule
        condition: When to apply this rule
        recommendation: What action to take
        reasoning: Why this works
        confidence: Initial confidence score (0-1)
        success_count: Number of successful applications
        failure_count: Number of failed applications
        source_task: Original task that generated this rule
        source_agent: Agent that generated this rule
        category: Rule category
        status: Current rule status
        tags: Tags for categorization
        created_at: Creation timestamp
        last_used: Last usage timestamp
        metadata: Additional metadata
    """
    id: str
    condition: str
    recommendation: str
    reasoning: str
    confidence: float = 0.7
    success_count: int = 1
    failure_count: int = 0
    source_task: str = ""
    source_agent: str = ""
    category: RuleCategory = RuleCategory.GENERAL
    status: RuleStatus = RuleStatus.ACTIVE
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def effectiveness(self) -> float:
        """
        Calculate rule effectiveness using Bayesian estimation.

        Uses a beta distribution prior to estimate effectiveness,
        which provides better estimates with limited data.
        """
        # Beta distribution parameters (prior: alpha=2, beta=2 for slight optimism)
        alpha = 2 + self.success_count
        beta = 2 + self.failure_count
        # Expected value of beta distribution
        return alpha / (alpha + beta)

    @property
    def total_applications(self) -> int:
        """Total number of times this rule was applied."""
        return self.success_count + self.failure_count

    @property
    def is_reliable(self) -> bool:
        """Check if rule has enough data to be considered reliable."""
        return self.total_applications >= 5 and self.effectiveness >= 0.6

    @property
    def should_prune(self) -> bool:
        """Check if rule should be pruned due to poor performance."""
        if self.total_applications < 10:
            return False
        return self.effectiveness < 0.4

    def record_application(self, success: bool) -> None:
        """Record a rule application outcome."""
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
        self.last_used = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "condition": self.condition,
            "recommendation": self.recommendation,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "effectiveness": self.effectiveness,
            "source_task": self.source_task,
            "source_agent": self.source_agent,
            "category": self.category.value,
            "status": self.status.value,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "total_applications": self.total_applications,
            "is_reliable": self.is_reliable,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExtractedRule":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            condition=data["condition"],
            recommendation=data["recommendation"],
            reasoning=data["reasoning"],
            confidence=data.get("confidence", 0.7),
            success_count=data.get("success_count", 1),
            failure_count=data.get("failure_count", 0),
            source_task=data.get("source_task", ""),
            source_agent=data.get("source_agent", ""),
            category=RuleCategory(data.get("category", "general")),
            status=RuleStatus(data.get("status", "active")),
            tags=data.get("tags", []),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            last_used=datetime.fromisoformat(data["last_used"]) if data.get("last_used") else None,
            metadata=data.get("metadata", {}),
        )

    @staticmethod
    def generate_id(condition: str, recommendation: str) -> str:
        """Generate a unique ID based on rule content."""
        content = f"{condition}:{recommendation}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class ExecutionOutcome:
    """
    Outcome of an agent execution.

    Captures the results of an agent task execution for learning purposes.

    Attributes:
        task: The task that was executed
        approach: The approach taken
        success: Whether execution was successful
        quality_score: Quality score (0-1)
        execution_time: Execution time in seconds
        artifacts: List of artifacts produced
        feedback: Optional feedback from user or evaluator
        agent_id: ID of the agent that executed
        rules_applied: IDs of rules that were applied
        timestamp: When the execution occurred
        metadata: Additional metadata
    """
    task: str
    approach: str
    success: bool
    quality_score: float
    execution_time: float
    artifacts: List[str] = field(default_factory=list)
    feedback: Optional[str] = None
    agent_id: str = ""
    rules_applied: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_high_quality(self) -> bool:
        """Check if execution was high quality (good for learning)."""
        return self.success and self.quality_score >= 0.8

    @property
    def is_learnable(self) -> bool:
        """Check if execution is suitable for rule extraction."""
        return self.success and self.quality_score >= 0.7

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "task": self.task,
            "approach": self.approach,
            "success": self.success,
            "quality_score": self.quality_score,
            "execution_time": self.execution_time,
            "artifacts": self.artifacts,
            "feedback": self.feedback,
            "agent_id": self.agent_id,
            "rules_applied": self.rules_applied,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionOutcome":
        """Create from dictionary."""
        return cls(
            task=data["task"],
            approach=data["approach"],
            success=data["success"],
            quality_score=data["quality_score"],
            execution_time=data["execution_time"],
            artifacts=data.get("artifacts", []),
            feedback=data.get("feedback"),
            agent_id=data.get("agent_id", ""),
            rules_applied=data.get("rules_applied", []),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(),
            metadata=data.get("metadata", {}),
        )


@dataclass
class RuleMatch:
    """
    Match result from rule search.

    Attributes:
        rule: The matched rule
        score: Relevance score (0-1)
        match_reason: Why this rule matched
    """
    rule: ExtractedRule
    score: float
    match_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rule": self.rule.to_dict(),
            "score": self.score,
            "match_reason": self.match_reason,
        }


@dataclass
class LearningStats:
    """
    Statistics about the learning system.

    Attributes:
        total_rules: Total number of rules
        active_rules: Number of active rules
        pruned_rules: Number of pruned rules
        total_applications: Total rule applications
        average_effectiveness: Average effectiveness of active rules
        rules_by_category: Count of rules per category
        recent_extractions: Number of rules extracted recently
    """
    total_rules: int = 0
    active_rules: int = 0
    pruned_rules: int = 0
    total_applications: int = 0
    average_effectiveness: float = 0.0
    rules_by_category: Dict[str, int] = field(default_factory=dict)
    recent_extractions: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_rules": self.total_rules,
            "active_rules": self.active_rules,
            "pruned_rules": self.pruned_rules,
            "total_applications": self.total_applications,
            "average_effectiveness": self.average_effectiveness,
            "rules_by_category": self.rules_by_category,
            "recent_extractions": self.recent_extractions,
        }
