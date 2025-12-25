"""
Audit Trail Entry and Types.

Provides comprehensive audit record structure for enterprise compliance,
with tamper-evident hash chaining for integrity verification.

Version: 2.6.0
"""

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional, List


def utc_now() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class DecisionType(str, Enum):
    """Types of decisions that require audit logging."""
    TASK_ROUTING = "task_routing"
    AGENT_SELECTION = "agent_selection"
    TOOL_INVOCATION = "tool_invocation"
    OUTPUT_GENERATION = "output_generation"
    VERIFICATION = "verification"
    HUMAN_ESCALATION = "human_escalation"
    RULE_APPLICATION = "rule_application"
    ERROR_HANDLING = "error_handling"
    PANEL_SELECTION = "panel_selection"
    JUDGE_VERDICT = "judge_verdict"
    SYMBOLIC_VERIFICATION = "symbolic_verification"
    SCHEMA_VALIDATION = "schema_validation"


class VerificationStatus(str, Enum):
    """Status of audit entry verification."""
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class AuditEntry:
    """
    Complete audit record for a decision point.

    Provides comprehensive logging for enterprise compliance requirements,
    with tamper-evident hash chaining for integrity verification.

    Attributes:
        # Identity
        entry_id: Unique identifier for this entry
        timestamp: When the decision was made (UTC)
        session_id: Session this decision belongs to
        conversation_id: Conversation context

        # Decision context
        decision_type: Type of decision being audited
        agent_id: Agent that made the decision
        model_name: Model used for generation
        model_version: Version of the model

        # Inputs (hashed for privacy)
        input_hash: SHA-256 hash of inputs
        input_summary: Human-readable summary
        input_token_count: Token count for inputs
        context_sources: Sources of context used

        # Decision process
        reasoning_summary: Summary of reasoning
        alternatives_considered: Other options considered
        selected_action: Action that was selected
        confidence_score: Confidence in the decision
        rules_applied: Business rules applied

        # Outputs
        output_hash: SHA-256 hash of outputs
        output_summary: Human-readable summary
        output_token_count: Token count for outputs

        # Verification
        verification_status: Current verification status
        verifier_ids: IDs of verifying agents
        verification_scores: Scores from verifiers

        # Provenance
        source_documents: Documents used as sources
        parent_entry_id: Parent entry in decision tree
        child_entry_ids: Child entries spawned

        # Chain integrity
        previous_entry_hash: Hash of previous entry
        entry_hash: Hash of this entry
    """
    # Identity
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=utc_now)
    session_id: str = ""
    conversation_id: str = ""

    # Decision context
    decision_type: DecisionType = DecisionType.OUTPUT_GENERATION
    agent_id: str = ""
    model_name: str = ""
    model_version: str = ""

    # Inputs (hashed for privacy, summarized for readability)
    input_hash: str = ""
    input_summary: str = ""
    input_token_count: int = 0
    context_sources: List[str] = field(default_factory=list)

    # Decision process
    reasoning_summary: str = ""
    alternatives_considered: List[Dict[str, Any]] = field(default_factory=list)
    selected_action: str = ""
    confidence_score: float = 0.0
    rules_applied: List[str] = field(default_factory=list)

    # Outputs
    output_hash: str = ""
    output_summary: str = ""
    output_token_count: int = 0

    # Verification
    verification_status: VerificationStatus = VerificationStatus.PENDING
    verifier_ids: List[str] = field(default_factory=list)
    verification_scores: Dict[str, float] = field(default_factory=dict)

    # Provenance
    source_documents: List[str] = field(default_factory=list)
    parent_entry_id: Optional[str] = None
    child_entry_ids: List[str] = field(default_factory=list)

    # Chain integrity
    previous_entry_hash: str = ""
    entry_hash: str = ""

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def compute_hash(self) -> str:
        """
        Compute tamper-evident hash of entry content.

        Uses SHA-256 hash of key fields to detect tampering.
        The hash includes the previous entry hash for chain integrity.
        """
        content = json.dumps({
            "entry_id": self.entry_id,
            "timestamp": self.timestamp.isoformat(),
            "decision_type": self.decision_type.value,
            "agent_id": self.agent_id,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "confidence_score": self.confidence_score,
            "verification_status": self.verification_status.value,
            "previous_entry_hash": self.previous_entry_hash,
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    def finalize(self) -> None:
        """Compute and set entry hash, making the entry immutable."""
        self.entry_hash = self.compute_hash()

    def verify_hash(self) -> bool:
        """Verify that the stored hash matches computed hash."""
        return self.entry_hash == self.compute_hash()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id,
            "conversation_id": self.conversation_id,
            "decision_type": self.decision_type.value,
            "agent_id": self.agent_id,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "input_hash": self.input_hash,
            "input_summary": self.input_summary,
            "input_token_count": self.input_token_count,
            "context_sources": self.context_sources,
            "reasoning_summary": self.reasoning_summary,
            "alternatives_considered": self.alternatives_considered,
            "selected_action": self.selected_action,
            "confidence_score": self.confidence_score,
            "rules_applied": self.rules_applied,
            "output_hash": self.output_hash,
            "output_summary": self.output_summary,
            "output_token_count": self.output_token_count,
            "verification_status": self.verification_status.value,
            "verifier_ids": self.verifier_ids,
            "verification_scores": self.verification_scores,
            "source_documents": self.source_documents,
            "parent_entry_id": self.parent_entry_id,
            "child_entry_ids": self.child_entry_ids,
            "previous_entry_hash": self.previous_entry_hash,
            "entry_hash": self.entry_hash,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEntry":
        """Create an AuditEntry from a dictionary."""
        # Parse timestamp
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            # Handle both aware and naive datetime strings
            if timestamp.endswith("Z"):
                timestamp = timestamp[:-1] + "+00:00"
            try:
                timestamp = datetime.fromisoformat(timestamp)
            except ValueError:
                timestamp = utc_now()
        elif timestamp is None:
            timestamp = utc_now()

        # Parse decision type
        decision_type_str = data.get("decision_type", "output_generation")
        try:
            decision_type = DecisionType(decision_type_str)
        except ValueError:
            decision_type = DecisionType.OUTPUT_GENERATION

        # Parse verification status
        verification_status_str = data.get("verification_status", "pending")
        try:
            verification_status = VerificationStatus(verification_status_str)
        except ValueError:
            verification_status = VerificationStatus.PENDING

        return cls(
            entry_id=data.get("entry_id", str(uuid.uuid4())),
            timestamp=timestamp,
            session_id=data.get("session_id", ""),
            conversation_id=data.get("conversation_id", ""),
            decision_type=decision_type,
            agent_id=data.get("agent_id", ""),
            model_name=data.get("model_name", ""),
            model_version=data.get("model_version", ""),
            input_hash=data.get("input_hash", ""),
            input_summary=data.get("input_summary", ""),
            input_token_count=data.get("input_token_count", 0),
            context_sources=data.get("context_sources", []),
            reasoning_summary=data.get("reasoning_summary", ""),
            alternatives_considered=data.get("alternatives_considered", []),
            selected_action=data.get("selected_action", ""),
            confidence_score=data.get("confidence_score", 0.0),
            rules_applied=data.get("rules_applied", []),
            output_hash=data.get("output_hash", ""),
            output_summary=data.get("output_summary", ""),
            output_token_count=data.get("output_token_count", 0),
            verification_status=verification_status,
            verifier_ids=data.get("verifier_ids", []),
            verification_scores=data.get("verification_scores", {}),
            source_documents=data.get("source_documents", []),
            parent_entry_id=data.get("parent_entry_id"),
            child_entry_ids=data.get("child_entry_ids", []),
            previous_entry_hash=data.get("previous_entry_hash", ""),
            entry_hash=data.get("entry_hash", ""),
            metadata=data.get("metadata", {}),
        )

    def add_child(self, child_entry_id: str) -> None:
        """Add a child entry ID to this entry."""
        if child_entry_id not in self.child_entry_ids:
            self.child_entry_ids.append(child_entry_id)

    def set_verification(
        self,
        status: VerificationStatus,
        verifier_id: str,
        score: Optional[float] = None,
    ) -> None:
        """Update verification status."""
        self.verification_status = status
        if verifier_id not in self.verifier_ids:
            self.verifier_ids.append(verifier_id)
        if score is not None:
            self.verification_scores[verifier_id] = score


def hash_content(content: Any) -> str:
    """
    Hash content for privacy-preserving storage.

    Creates SHA-256 hash of JSON-serialized content.
    """
    try:
        serialized = json.dumps(content, sort_keys=True, default=str)
    except (TypeError, ValueError):
        serialized = str(content)
    return hashlib.sha256(serialized.encode()).hexdigest()


def summarize_content(content: Any, max_length: int = 200) -> str:
    """
    Create human-readable summary of content.

    Truncates long content and shows structure for complex objects.
    """
    if content is None:
        return "<none>"
    elif isinstance(content, str):
        if len(content) > max_length:
            return content[:max_length] + "..."
        return content
    elif isinstance(content, dict):
        keys_str = str(list(content.keys()))
        if len(keys_str) > max_length:
            return keys_str[:max_length] + "..."
        return f"dict with keys: {keys_str}"
    elif isinstance(content, list):
        return f"list of {len(content)} items"
    else:
        type_name = type(content).__name__
        return f"<{type_name}>"
