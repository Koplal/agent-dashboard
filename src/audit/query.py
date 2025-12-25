"""
Audit Trail Query Interface.

Provides flexible querying capabilities for audit trail investigation,
debugging, and analysis.

Version: 2.6.0
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Callable
from enum import Enum

from .trail import AuditEntry, DecisionType, VerificationStatus
from .storage import StorageBackend


def utc_now() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


class SortOrder(str, Enum):
    """Sort order for query results."""
    ASC = "asc"
    DESC = "desc"


class SortField(str, Enum):
    """Fields available for sorting."""
    TIMESTAMP = "timestamp"
    AGENT = "agent_id"
    TYPE = "decision_type"
    CONFIDENCE = "confidence_score"


@dataclass
class QueryFilter:
    """
    Filter criteria for audit queries.

    Attributes:
        decision_types: Filter by decision types
        agent_ids: Filter by agent IDs
        session_ids: Filter by session IDs
        verification_statuses: Filter by verification status
        min_confidence: Minimum confidence score
        max_confidence: Maximum confidence score
        start_date: Start of date range
        end_date: End of date range
        has_parent: Filter for entries with/without parent
        search_text: Text to search in summaries
        custom_filter: Custom filter function
    """
    decision_types: Optional[List[DecisionType]] = None
    agent_ids: Optional[List[str]] = None
    session_ids: Optional[List[str]] = None
    verification_statuses: Optional[List[VerificationStatus]] = None
    min_confidence: Optional[float] = None
    max_confidence: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    has_parent: Optional[bool] = None
    search_text: Optional[str] = None
    custom_filter: Optional[Callable[[AuditEntry], bool]] = None

    def matches(self, entry: AuditEntry) -> bool:
        """Check if an entry matches all filter criteria."""
        # Decision type filter
        if self.decision_types and entry.decision_type not in self.decision_types:
            return False

        # Agent filter
        if self.agent_ids and entry.agent_id not in self.agent_ids:
            return False

        # Session filter
        if self.session_ids and entry.session_id not in self.session_ids:
            return False

        # Verification status filter
        if self.verification_statuses:
            if entry.verification_status not in self.verification_statuses:
                return False

        # Confidence range
        if self.min_confidence is not None:
            if entry.confidence_score < self.min_confidence:
                return False
        if self.max_confidence is not None:
            if entry.confidence_score > self.max_confidence:
                return False

        # Date range
        if self.start_date and entry.timestamp < self.start_date:
            return False
        if self.end_date and entry.timestamp > self.end_date:
            return False

        # Parent filter
        if self.has_parent is not None:
            has_parent = entry.parent_entry_id is not None
            if has_parent != self.has_parent:
                return False

        # Text search
        if self.search_text:
            search_lower = self.search_text.lower()
            searchable = (
                entry.input_summary.lower() +
                entry.output_summary.lower() +
                entry.reasoning_summary.lower() +
                entry.selected_action.lower()
            )
            if search_lower not in searchable:
                return False

        # Custom filter
        if self.custom_filter and not self.custom_filter(entry):
            return False

        return True


@dataclass
class QueryResult:
    """
    Result of an audit query.

    Attributes:
        entries: Matching entries
        total_count: Total matches (before pagination)
        page: Current page number
        page_size: Entries per page
        has_more: Whether more pages exist
        query_time_ms: Query execution time
    """
    entries: List[AuditEntry] = field(default_factory=list)
    total_count: int = 0
    page: int = 1
    page_size: int = 50
    has_more: bool = False
    query_time_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "entries": [e.to_dict() for e in self.entries],
            "total_count": self.total_count,
            "page": self.page,
            "page_size": self.page_size,
            "has_more": self.has_more,
            "query_time_ms": self.query_time_ms,
        }


class AuditQueryEngine:
    """
    Query engine for audit trail investigation.

    Provides flexible querying with filtering, sorting, and pagination
    for investigating audit trail data.

    Example:
        engine = AuditQueryEngine(storage)

        # Find all verification failures
        results = engine.query(
            filter=QueryFilter(
                verification_statuses=[VerificationStatus.FAILED],
                start_date=datetime.now() - timedelta(days=7)
            ),
            sort_by=SortField.TIMESTAMP,
            order=SortOrder.DESC
        )

        for entry in results.entries:
            print(f"{entry.timestamp}: {entry.agent_id} - {entry.selected_action}")
    """

    def __init__(self, storage: StorageBackend):
        """
        Initialize the query engine.

        Args:
            storage: Storage backend to query
        """
        self.storage = storage

    def query(
        self,
        filter: Optional[QueryFilter] = None,
        sort_by: SortField = SortField.TIMESTAMP,
        order: SortOrder = SortOrder.DESC,
        page: int = 1,
        page_size: int = 50,
    ) -> QueryResult:
        """
        Execute a query against the audit trail.

        Args:
            filter: Filter criteria
            sort_by: Field to sort by
            order: Sort order
            page: Page number (1-indexed)
            page_size: Entries per page

        Returns:
            QueryResult with matching entries
        """
        import time
        start_time = time.time()

        filter = filter or QueryFilter()

        # Get base entries (optimize with date range if available)
        if filter.start_date and filter.end_date:
            all_entries = self.storage.get_entries_in_range(
                filter.start_date,
                filter.end_date,
            )
        else:
            all_entries = self.storage.get_all_entries()

        # Apply filters
        matching = [e for e in all_entries if filter.matches(e)]

        # Sort
        matching = self._sort_entries(matching, sort_by, order)

        # Paginate
        total_count = len(matching)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_entries = matching[start_idx:end_idx]

        elapsed_ms = int((time.time() - start_time) * 1000)

        return QueryResult(
            entries=page_entries,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_more=end_idx < total_count,
            query_time_ms=elapsed_ms,
        )

    def _sort_entries(
        self,
        entries: List[AuditEntry],
        sort_by: SortField,
        order: SortOrder,
    ) -> List[AuditEntry]:
        """Sort entries by specified field and order."""
        reverse = order == SortOrder.DESC

        if sort_by == SortField.TIMESTAMP:
            key = lambda e: e.timestamp
        elif sort_by == SortField.AGENT:
            key = lambda e: e.agent_id
        elif sort_by == SortField.TYPE:
            key = lambda e: e.decision_type.value
        elif sort_by == SortField.CONFIDENCE:
            key = lambda e: e.confidence_score
        else:
            key = lambda e: e.timestamp

        return sorted(entries, key=key, reverse=reverse)

    def find_by_id(self, entry_id: str) -> Optional[AuditEntry]:
        """Find a specific entry by ID."""
        return self.storage.get(entry_id)

    def find_children(self, parent_id: str) -> List[AuditEntry]:
        """Find all child entries of a given parent."""
        parent = self.storage.get(parent_id)
        if not parent:
            return []

        children = []
        for child_id in parent.child_entry_ids:
            child = self.storage.get(child_id)
            if child:
                children.append(child)

        return children

    def find_ancestors(self, entry_id: str) -> List[AuditEntry]:
        """Find all ancestor entries (parent chain)."""
        ancestors = []
        current = self.storage.get(entry_id)

        while current and current.parent_entry_id:
            parent = self.storage.get(current.parent_entry_id)
            if parent:
                ancestors.append(parent)
                current = parent
            else:
                break

        return ancestors

    def find_decision_tree(self, root_id: str) -> Dict[str, Any]:
        """
        Build a complete decision tree from a root entry.

        Returns tree structure with entry data and children.
        """
        root = self.storage.get(root_id)
        if not root:
            return {}

        return self._build_tree_node(root)

    def _build_tree_node(self, entry: AuditEntry) -> Dict[str, Any]:
        """Recursively build tree node."""
        children = []
        for child_id in entry.child_entry_ids:
            child = self.storage.get(child_id)
            if child:
                children.append(self._build_tree_node(child))

        return {
            "entry_id": entry.entry_id,
            "timestamp": entry.timestamp.isoformat(),
            "decision_type": entry.decision_type.value,
            "agent_id": entry.agent_id,
            "action": entry.selected_action,
            "confidence": entry.confidence_score,
            "children": children,
        }

    def get_timeline(
        self,
        session_id: str,
        include_details: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Get a timeline of events for a session.

        Args:
            session_id: Session to get timeline for
            include_details: Whether to include full entry details

        Returns:
            List of timeline events
        """
        entries = self.storage.get_entries_by_session(session_id)
        entries = sorted(entries, key=lambda e: e.timestamp)

        timeline = []
        for entry in entries:
            event = {
                "timestamp": entry.timestamp.isoformat(),
                "type": entry.decision_type.value,
                "agent": entry.agent_id,
                "action": entry.selected_action,
            }

            if include_details:
                event["entry_id"] = entry.entry_id
                event["confidence"] = entry.confidence_score
                event["verification"] = entry.verification_status.value
                event["input_summary"] = entry.input_summary
                event["output_summary"] = entry.output_summary

            timeline.append(event)

        return timeline

    def get_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get aggregate statistics for the audit trail.

        Args:
            start_date: Optional start of period
            end_date: Optional end of period

        Returns:
            Statistics dictionary
        """
        if start_date and end_date:
            entries = self.storage.get_entries_in_range(start_date, end_date)
        else:
            entries = self.storage.get_all_entries()

        if not entries:
            return {
                "total_entries": 0,
                "by_type": {},
                "by_agent": {},
                "by_verification": {},
                "confidence_avg": 0.0,
                "period": None,
            }

        by_type: Dict[str, int] = {}
        by_agent: Dict[str, int] = {}
        by_verification: Dict[str, int] = {}
        confidence_sum = 0.0
        confidence_count = 0

        for entry in entries:
            by_type[entry.decision_type.value] = by_type.get(entry.decision_type.value, 0) + 1

            if entry.agent_id:
                by_agent[entry.agent_id] = by_agent.get(entry.agent_id, 0) + 1

            by_verification[entry.verification_status.value] = (
                by_verification.get(entry.verification_status.value, 0) + 1
            )

            if entry.confidence_score > 0:
                confidence_sum += entry.confidence_score
                confidence_count += 1

        entries_sorted = sorted(entries, key=lambda e: e.timestamp)

        return {
            "total_entries": len(entries),
            "by_type": by_type,
            "by_agent": by_agent,
            "by_verification": by_verification,
            "confidence_avg": confidence_sum / confidence_count if confidence_count > 0 else 0.0,
            "period": {
                "start": entries_sorted[0].timestamp.isoformat(),
                "end": entries_sorted[-1].timestamp.isoformat(),
            },
        }

    def find_anomalies(
        self,
        lookback_hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """
        Find potential anomalies in recent audit entries.

        Checks for:
        - Low confidence scores
        - High error rates
        - Unusual activity patterns
        - Verification failures

        Args:
            lookback_hours: Hours to look back

        Returns:
            List of anomaly reports
        """
        end_date = utc_now()
        start_date = end_date - timedelta(hours=lookback_hours)

        entries = self.storage.get_entries_in_range(start_date, end_date)
        anomalies = []

        # Check for low confidence decisions
        low_confidence = [e for e in entries if 0 < e.confidence_score < 0.5]
        if low_confidence:
            anomalies.append({
                "type": "low_confidence",
                "count": len(low_confidence),
                "description": f"{len(low_confidence)} decisions with confidence < 0.5",
                "severity": "warning",
                "sample_ids": [e.entry_id for e in low_confidence[:5]],
            })

        # Check for verification failures
        failures = [e for e in entries if e.verification_status == VerificationStatus.FAILED]
        if failures:
            anomalies.append({
                "type": "verification_failure",
                "count": len(failures),
                "description": f"{len(failures)} verification failures",
                "severity": "high",
                "sample_ids": [e.entry_id for e in failures[:5]],
            })

        # Check for error handling entries (may indicate problems)
        errors = [e for e in entries if e.decision_type == DecisionType.ERROR_HANDLING]
        if len(errors) > len(entries) * 0.1:  # More than 10% errors
            anomalies.append({
                "type": "high_error_rate",
                "count": len(errors),
                "description": f"High error handling rate: {len(errors)}/{len(entries)}",
                "severity": "high",
                "sample_ids": [e.entry_id for e in errors[:5]],
            })

        return anomalies
