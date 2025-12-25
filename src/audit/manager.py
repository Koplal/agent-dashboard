"""
Audit Trail Manager.

Provides high-level interface for recording and managing audit entries
with chain integrity, verification, and compliance support.

Version: 2.6.0
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Callable

from .trail import (
    AuditEntry,
    DecisionType,
    VerificationStatus,
    hash_content,
    summarize_content,
)
from .storage import StorageBackend, MemoryStorageBackend

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


@dataclass
class IntegrityReport:
    """
    Result of integrity verification.

    Attributes:
        verified: Whether all entries passed verification
        entries_checked: Number of entries checked
        issues: List of integrity issues found
        checked_at: When verification was performed
    """
    verified: bool
    entries_checked: int
    issues: List[Dict[str, Any]] = field(default_factory=list)
    checked_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "verified": self.verified,
            "entries_checked": self.entries_checked,
            "issues": self.issues,
            "checked_at": self.checked_at.isoformat(),
        }


class AuditTrailManager:
    """
    Manages audit trail with integrity guarantees.

    Provides:
    - Recording of decision points with full context
    - Chain integrity verification
    - Query interface for investigation
    - Compliance report generation
    - Session and conversation tracking

    Example:
        from src.audit import AuditTrailManager, SQLiteStorageBackend

        storage = SQLiteStorageBackend("~/.claude/audit.db")
        manager = AuditTrailManager(storage)

        # Record a decision
        entry = manager.record(
            decision_type=DecisionType.AGENT_SELECTION,
            agent_id="orchestrator",
            inputs={"task": "research quantum computing"},
            outputs={"selected_agent": "researcher"},
            session_id="session-123",
            confidence=0.95
        )

        # Verify integrity
        report = manager.verify_integrity()
        if not report.verified:
            print("Integrity issues found:", report.issues)
    """

    def __init__(
        self,
        storage_backend: Optional[StorageBackend] = None,
        session_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ):
        """
        Initialize the audit trail manager.

        Args:
            storage_backend: Storage backend (defaults to in-memory)
            session_id: Default session ID for entries
            conversation_id: Default conversation ID for entries
        """
        self.storage = storage_backend or MemoryStorageBackend()
        self.session_id = session_id or str(uuid.uuid4())
        self.conversation_id = conversation_id or ""

        # Get current chain hash
        self.current_chain_hash = self.storage.get_latest_hash()

        # Statistics
        self.entries_recorded = 0
        self.verification_checks = 0

        # Hooks for custom processing
        self._pre_record_hooks: List[Callable[[AuditEntry], AuditEntry]] = []
        self._post_record_hooks: List[Callable[[AuditEntry], None]] = []

    def record(
        self,
        decision_type: DecisionType,
        agent_id: str,
        inputs: Any,
        outputs: Any,
        **kwargs,
    ) -> AuditEntry:
        """
        Record a decision with full context.

        Args:
            decision_type: Type of decision being made
            agent_id: ID of agent making the decision
            inputs: Input data (will be hashed)
            outputs: Output data (will be hashed)
            **kwargs: Additional fields:
                - session_id: Session identifier
                - conversation_id: Conversation identifier
                - model_name: Model used
                - model_version: Model version
                - input_tokens: Token count for inputs
                - output_tokens: Token count for outputs
                - reasoning: Reasoning summary
                - alternatives: Alternative options considered
                - action: Selected action
                - confidence: Confidence score (0.0-1.0)
                - rules: Business rules applied
                - sources: Context sources
                - documents: Source documents
                - parent_id: Parent entry ID
                - metadata: Additional metadata

        Returns:
            The created and stored AuditEntry
        """
        # Create entry
        entry = AuditEntry(
            session_id=kwargs.get("session_id", self.session_id),
            conversation_id=kwargs.get("conversation_id", self.conversation_id),
            decision_type=decision_type,
            agent_id=agent_id,
            model_name=kwargs.get("model_name", ""),
            model_version=kwargs.get("model_version", ""),
            input_hash=hash_content(inputs),
            input_summary=summarize_content(inputs, max_length=200),
            input_token_count=kwargs.get("input_tokens", 0),
            context_sources=kwargs.get("sources", []),
            reasoning_summary=kwargs.get("reasoning", ""),
            alternatives_considered=kwargs.get("alternatives", []),
            selected_action=kwargs.get("action", ""),
            confidence_score=kwargs.get("confidence", 0.0),
            rules_applied=kwargs.get("rules", []),
            output_hash=hash_content(outputs),
            output_summary=summarize_content(outputs, max_length=200),
            output_token_count=kwargs.get("output_tokens", 0),
            source_documents=kwargs.get("documents", []),
            parent_entry_id=kwargs.get("parent_id"),
            previous_entry_hash=self.current_chain_hash,
            metadata=kwargs.get("metadata", {}),
        )

        # Run pre-record hooks
        for hook in self._pre_record_hooks:
            entry = hook(entry)

        # Finalize entry (compute hash)
        entry.finalize()

        # Update chain hash
        self.current_chain_hash = entry.entry_hash

        # Store entry
        self.storage.store(entry)
        self.entries_recorded += 1

        # Update parent if specified
        parent_id = kwargs.get("parent_id")
        if parent_id:
            self._add_child_to_parent(parent_id, entry.entry_id)

        # Run post-record hooks
        for hook in self._post_record_hooks:
            hook(entry)

        logger.debug(f"Recorded audit entry: {entry.entry_id} ({decision_type.value})")

        return entry

    def _add_child_to_parent(self, parent_id: str, child_id: str) -> None:
        """Add child reference to parent entry."""
        parent = self.storage.get(parent_id)
        if parent:
            parent.add_child(child_id)
            # Note: This creates a new entry with updated child_entry_ids
            # In SQLite backend, this will update in place

    def record_tool_invocation(
        self,
        agent_id: str,
        tool_name: str,
        tool_input: Any,
        tool_output: Any,
        success: bool = True,
        **kwargs,
    ) -> AuditEntry:
        """
        Convenience method for recording tool invocations.

        Args:
            agent_id: Agent invoking the tool
            tool_name: Name of the tool
            tool_input: Tool input parameters
            tool_output: Tool output
            success: Whether invocation succeeded
            **kwargs: Additional fields

        Returns:
            The created AuditEntry
        """
        return self.record(
            decision_type=DecisionType.TOOL_INVOCATION,
            agent_id=agent_id,
            inputs={"tool": tool_name, "input": tool_input},
            outputs={"output": tool_output, "success": success},
            action=f"invoke_{tool_name}",
            **kwargs,
        )

    def record_agent_selection(
        self,
        orchestrator_id: str,
        task: str,
        selected_agent: str,
        candidates: List[str],
        confidence: float = 0.0,
        **kwargs,
    ) -> AuditEntry:
        """
        Convenience method for recording agent selection decisions.

        Args:
            orchestrator_id: Orchestrator making the selection
            task: Task to be performed
            selected_agent: Agent selected for the task
            candidates: Candidate agents considered
            confidence: Confidence in selection
            **kwargs: Additional fields

        Returns:
            The created AuditEntry
        """
        alternatives = [
            {"agent": agent, "reason": "candidate"}
            for agent in candidates
            if agent != selected_agent
        ]

        return self.record(
            decision_type=DecisionType.AGENT_SELECTION,
            agent_id=orchestrator_id,
            inputs={"task": task, "candidates": candidates},
            outputs={"selected_agent": selected_agent},
            action=f"select_{selected_agent}",
            alternatives=alternatives,
            confidence=confidence,
            **kwargs,
        )

    def record_verification(
        self,
        verifier_id: str,
        content_hash: str,
        verdict: str,
        score: float,
        reasoning: str,
        **kwargs,
    ) -> AuditEntry:
        """
        Convenience method for recording verification decisions.

        Args:
            verifier_id: Verifier agent ID
            content_hash: Hash of verified content
            verdict: Verification verdict
            score: Verification score
            reasoning: Reasoning for verdict
            **kwargs: Additional fields

        Returns:
            The created AuditEntry
        """
        return self.record(
            decision_type=DecisionType.VERIFICATION,
            agent_id=verifier_id,
            inputs={"content_hash": content_hash},
            outputs={"verdict": verdict, "score": score},
            action=f"verify_{verdict}",
            reasoning=reasoning,
            confidence=score,
            **kwargs,
        )

    def record_panel_selection(
        self,
        description: str,
        panel_size: int,
        risk_score: int,
        **kwargs,
    ) -> AuditEntry:
        """
        Convenience method for recording panel selection decisions.

        Args:
            description: Task description
            panel_size: Selected panel size
            risk_score: Calculated risk score
            **kwargs: Additional fields

        Returns:
            The created AuditEntry
        """
        return self.record(
            decision_type=DecisionType.PANEL_SELECTION,
            agent_id="panel_selector",
            inputs={"description": description},
            outputs={"panel_size": panel_size, "risk_score": risk_score},
            action=f"select_panel_{panel_size}",
            confidence=1.0,  # Deterministic selection
            **kwargs,
        )

    def verify_integrity(self) -> IntegrityReport:
        """
        Verify chain integrity of all audit entries.

        Checks:
        1. Each entry's stored hash matches computed hash
        2. Chain linkage is correct (previous_entry_hash matches)

        Returns:
            IntegrityReport with verification results
        """
        self.verification_checks += 1

        entries = self.storage.get_all_entries()
        issues = []

        for i, entry in enumerate(entries):
            # Verify self-hash
            if not entry.verify_hash():
                computed = entry.compute_hash()
                issues.append({
                    "entry_id": entry.entry_id,
                    "issue": "hash_mismatch",
                    "stored": entry.entry_hash,
                    "computed": computed,
                    "timestamp": entry.timestamp.isoformat(),
                })

            # Verify chain linkage
            if i > 0:
                expected_previous = entries[i - 1].entry_hash
                if entry.previous_entry_hash != expected_previous:
                    issues.append({
                        "entry_id": entry.entry_id,
                        "issue": "chain_break",
                        "expected_previous": expected_previous,
                        "stored_previous": entry.previous_entry_hash,
                        "timestamp": entry.timestamp.isoformat(),
                    })

        report = IntegrityReport(
            verified=len(issues) == 0,
            entries_checked=len(entries),
            issues=issues,
        )

        if not report.verified:
            logger.warning(
                f"Integrity verification failed: {len(issues)} issues found"
            )

        return report

    def get_entry(self, entry_id: str) -> Optional[AuditEntry]:
        """Get a specific audit entry by ID."""
        return self.storage.get(entry_id)

    def get_session_entries(self, session_id: Optional[str] = None) -> List[AuditEntry]:
        """Get all entries for a session."""
        session_id = session_id or self.session_id
        return self.storage.get_entries_by_session(session_id)

    def get_entries_by_type(
        self,
        decision_type: DecisionType,
    ) -> List[AuditEntry]:
        """Get entries of a specific decision type."""
        return self.storage.get_entries_by_type(decision_type)

    def get_entries_in_range(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> List[AuditEntry]:
        """Get entries within a date range."""
        return self.storage.get_entries_in_range(start_date, end_date)

    def update_verification(
        self,
        entry_id: str,
        status: VerificationStatus,
        verifier_id: str,
        score: Optional[float] = None,
    ) -> bool:
        """
        Update verification status of an entry.

        Args:
            entry_id: Entry to update
            status: New verification status
            verifier_id: ID of verifier
            score: Optional verification score

        Returns:
            True if update succeeded
        """
        entry = self.storage.get(entry_id)
        if entry:
            entry.set_verification(status, verifier_id, score)
            self.storage.store(entry)
            return True
        return False

    def add_pre_record_hook(
        self,
        hook: Callable[[AuditEntry], AuditEntry],
    ) -> None:
        """
        Add a hook to be called before recording an entry.

        Hook receives the entry and should return the (possibly modified) entry.
        """
        self._pre_record_hooks.append(hook)

    def add_post_record_hook(
        self,
        hook: Callable[[AuditEntry], None],
    ) -> None:
        """
        Add a hook to be called after recording an entry.

        Hook receives the finalized entry.
        """
        self._post_record_hooks.append(hook)

    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics."""
        return {
            "entries_recorded": self.entries_recorded,
            "total_entries": self.storage.count(),
            "verification_checks": self.verification_checks,
            "current_session": self.session_id,
            "chain_hash": self.current_chain_hash[:16] + "..." if self.current_chain_hash else "",
        }

    def new_session(self, session_id: Optional[str] = None) -> str:
        """
        Start a new session.

        Args:
            session_id: Optional session ID (generated if not provided)

        Returns:
            The new session ID
        """
        self.session_id = session_id or str(uuid.uuid4())
        return self.session_id


# Default manager instance
_default_manager: Optional[AuditTrailManager] = None


def get_default_manager() -> AuditTrailManager:
    """Get or create the default audit trail manager."""
    global _default_manager
    if _default_manager is None:
        _default_manager = AuditTrailManager()
    return _default_manager


def record_decision(
    decision_type: DecisionType,
    agent_id: str,
    inputs: Any,
    outputs: Any,
    **kwargs,
) -> AuditEntry:
    """
    Record a decision using the default manager.

    Convenience function for simple audit logging.
    """
    return get_default_manager().record(
        decision_type=decision_type,
        agent_id=agent_id,
        inputs=inputs,
        outputs=outputs,
        **kwargs,
    )
