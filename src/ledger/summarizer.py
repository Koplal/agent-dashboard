"""
Hierarchical Session Summarizer.

Provides multi-level summarization of task progress with token-aware
context loading for LLM optimization.

Implements HIER-001 with:
- SummaryLevel enum (SESSION, PHASE, TASK, ATOMIC)
- HierarchicalSummary frozen dataclass
- HierarchicalSummarizer class for phase detection and summarization

Version: 2.6.0
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, Any, Optional, List
import uuid

from .task_ledger import TaskLedger


class SummaryLevel(Enum):
    """Hierarchy levels for summarization.
    
    Values represent depth: 0=highest (SESSION), 3=lowest (ATOMIC).
    """
    SESSION = 0
    PHASE = 1
    TASK = 2
    ATOMIC = 3


@dataclass(frozen=True)
class HierarchicalSummary:
    """Immutable summary at a specific hierarchy level.
    
    Attributes:
        level: Summary hierarchy level
        summary_id: Unique identifier for this summary
        parent_id: ID of parent summary (None for SESSION)
        start_time: Start of summarized time period
        end_time: End of summarized time period
        accomplishments: List of completed items
        blockers: List of encountered blockers
        token_count: Estimated token count for this summary
        child_count: Number of child summaries aggregated
        metadata: Additional context-specific data
    """
    level: SummaryLevel
    summary_id: str
    parent_id: Optional[str]
    start_time: datetime
    end_time: datetime
    accomplishments: List[str]
    blockers: List[str]
    token_count: int
    child_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class HierarchicalSummarizer:
    """Creates hierarchical summaries from task progress.
    
    Provides:
    - Phase detection based on time gaps
    - Task-level summarization from progress entries
    - Phase and session aggregation
    - Token-budget-aware context loading
    """
    
    def __init__(self):
        """Initialize the summarizer."""
        pass
    
    def detect_phases(
        self,
        tasks: List[TaskLedger],
        threshold_minutes: int = 90
    ) -> List[List[TaskLedger]]:
        """Group tasks into phases based on time proximity.
        
        Args:
            tasks: List of tasks to group
            threshold_minutes: Gap threshold for phase boundary (default 90)
            
        Returns:
            List of task groups (phases), each group is a list of tasks
            
        Raises:
            ValueError: If threshold_minutes is not positive
        """
        if threshold_minutes <= 0:
            raise ValueError("Phase threshold must be positive")
        
        if not tasks:
            return []
        
        # Sort tasks by their earliest timestamp
        def get_task_time(task: TaskLedger) -> datetime:
            if task.progress_history:
                return min(e.timestamp for e in task.progress_history)
            return task.created_at
        
        sorted_tasks = sorted(tasks, key=get_task_time)
        
        phases: List[List[TaskLedger]] = []
        current_phase: List[TaskLedger] = [sorted_tasks[0]]
        
        for i in range(1, len(sorted_tasks)):
            prev_task = sorted_tasks[i - 1]
            curr_task = sorted_tasks[i]
            
            prev_time = get_task_time(prev_task)
            curr_time = get_task_time(curr_task)
            
            gap = (curr_time - prev_time).total_seconds() / 60
            
            if gap > threshold_minutes:
                phases.append(current_phase)
                current_phase = [curr_task]
            else:
                current_phase.append(curr_task)
        
        phases.append(current_phase)
        return phases

    def summarize_task(self, task: TaskLedger) -> HierarchicalSummary:
        """Create a TASK-level summary from a TaskLedger.
        
        Args:
            task: TaskLedger to summarize
            
        Returns:
            HierarchicalSummary at TASK level
        """
        accomplishments: List[str] = []
        blockers: List[str] = []
        
        seen_accomplishments: set = set()
        seen_blockers: set = set()
        
        for entry in task.progress_history:
            # Extract accomplishments from success/completed outcomes
            if entry.outcome in ("success", "completed"):
                normalized = entry.action_taken.strip().lower()
                if normalized not in seen_accomplishments:
                    seen_accomplishments.add(normalized)
                    accomplishments.append(entry.action_taken.strip())
            
            # Extract blockers from failed/blocked outcomes
            if entry.outcome in ("failed", "blocked"):
                normalized = entry.action_taken.strip().lower()
                if normalized not in seen_blockers:
                    seen_blockers.add(normalized)
                    blockers.append(entry.action_taken.strip())
            
            # Also add blockers from blockers_encountered field
            for blocker in entry.blockers_encountered:
                normalized = blocker.strip().lower()
                if normalized not in seen_blockers:
                    seen_blockers.add(normalized)
                    blockers.append(blocker.strip())
        
        # Calculate time bounds
        if task.progress_history:
            start_time = min(e.timestamp for e in task.progress_history)
            end_time = max(e.timestamp for e in task.progress_history)
        else:
            start_time = task.created_at
            end_time = task.updated_at
        
        # Estimate token count based on content
        content_length = sum(len(a) for a in accomplishments) + sum(len(b) for b in blockers)
        token_count = max(1, content_length // 4)
        
        return HierarchicalSummary(
            level=SummaryLevel.TASK,
            summary_id=f"TASK-{task.task_id}",
            parent_id=None,
            start_time=start_time,
            end_time=end_time,
            accomplishments=accomplishments,
            blockers=blockers,
            token_count=token_count,
            child_count=0,
            metadata={"task_id": task.task_id, "assigned_agent": task.assigned_agent},
        )

    def summarize_phase(
        self,
        task_summaries: List[HierarchicalSummary]
    ) -> HierarchicalSummary:
        """Create a PHASE-level summary from task summaries.
        
        Args:
            task_summaries: List of TASK-level summaries to aggregate
            
        Returns:
            HierarchicalSummary at PHASE level
        """
        if not task_summaries:
            now = datetime.now(timezone.utc)
            return HierarchicalSummary(
                level=SummaryLevel.PHASE,
                summary_id=f"PHASE-{uuid.uuid4().hex[:8]}",
                parent_id=None,
                start_time=now,
                end_time=now,
                accomplishments=[],
                blockers=[],
                token_count=0,
                child_count=0,
                metadata={"task_ids": []},
            )
        
        # Deduplicate accomplishments across tasks
        accomplishments: List[str] = []
        seen_accomplishments: set = set()
        
        for summary in task_summaries:
            for acc in summary.accomplishments:
                normalized = acc.strip().lower()
                if normalized not in seen_accomplishments:
                    seen_accomplishments.add(normalized)
                    accomplishments.append(acc)
        
        # Deduplicate blockers across tasks
        blockers: List[str] = []
        seen_blockers: set = set()
        
        for summary in task_summaries:
            for blk in summary.blockers:
                normalized = blk.strip().lower()
                if normalized not in seen_blockers:
                    seen_blockers.add(normalized)
                    blockers.append(blk)
        
        # Calculate time bounds
        start_time = min(s.start_time for s in task_summaries)
        end_time = max(s.end_time for s in task_summaries)
        
        # Aggregate token count
        total_tokens = sum(s.token_count for s in task_summaries)
        
        # Extract task IDs from metadata
        task_ids = []
        for summary in task_summaries:
            if "task_id" in summary.metadata:
                task_ids.append(summary.metadata["task_id"])
            else:
                task_ids.append(summary.summary_id)
        
        return HierarchicalSummary(
            level=SummaryLevel.PHASE,
            summary_id=f"PHASE-{uuid.uuid4().hex[:8]}",
            parent_id=None,
            start_time=start_time,
            end_time=end_time,
            accomplishments=accomplishments,
            blockers=blockers,
            token_count=total_tokens,
            child_count=len(task_summaries),
            metadata={"task_ids": task_ids, "child_summaries": list(task_summaries)},
        )

    def summarize_session(
        self,
        phase_summaries: List[HierarchicalSummary]
    ) -> HierarchicalSummary:
        """Create a SESSION-level summary from phase summaries.
        
        Args:
            phase_summaries: List of PHASE-level summaries to aggregate
            
        Returns:
            HierarchicalSummary at SESSION level with parent_id=None
        """
        if not phase_summaries:
            now = datetime.now(timezone.utc)
            return HierarchicalSummary(
                level=SummaryLevel.SESSION,
                summary_id=f"SESSION-{uuid.uuid4().hex[:8]}",
                parent_id=None,
                start_time=now,
                end_time=now,
                accomplishments=[],
                blockers=[],
                token_count=0,
                child_count=0,
                metadata={"phase_count": 0, "total_task_count": 0},
            )
        
        # Deduplicate accomplishments across phases
        accomplishments: List[str] = []
        seen_accomplishments: set = set()
        
        for summary in phase_summaries:
            for acc in summary.accomplishments:
                normalized = acc.strip().lower()
                if normalized not in seen_accomplishments:
                    seen_accomplishments.add(normalized)
                    accomplishments.append(acc)
        
        # Deduplicate blockers across phases
        blockers: List[str] = []
        seen_blockers: set = set()
        
        for summary in phase_summaries:
            for blk in summary.blockers:
                normalized = blk.strip().lower()
                if normalized not in seen_blockers:
                    seen_blockers.add(normalized)
                    blockers.append(blk)
        
        # Calculate time bounds
        start_time = min(s.start_time for s in phase_summaries)
        end_time = max(s.end_time for s in phase_summaries)
        
        # Aggregate token count
        total_tokens = sum(s.token_count for s in phase_summaries)
        
        # Count total tasks across all phases
        total_task_count = sum(s.child_count for s in phase_summaries)
        
        return HierarchicalSummary(
            level=SummaryLevel.SESSION,
            summary_id=f"SESSION-{uuid.uuid4().hex[:8]}",
            parent_id=None,
            start_time=start_time,
            end_time=end_time,
            accomplishments=accomplishments,
            blockers=blockers,
            token_count=total_tokens,
            child_count=len(phase_summaries),
            metadata={
                "phase_count": len(phase_summaries),
                "total_task_count": total_task_count,
                "child_summaries": list(phase_summaries),
            },
        )

    def load_context(
        self,
        summary: HierarchicalSummary,
        token_budget: int,
        query: Optional[str] = None
    ) -> List[HierarchicalSummary]:
        """Load summaries within token budget, optionally prioritizing by query.

        Args:
            summary: Root summary to expand
            token_budget: Maximum tokens to include
            query: Optional query string to prioritize matching summaries

        Returns:
            List of summaries in hierarchical order (SESSION -> PHASE -> TASK)

        Raises:
            ValueError: If token_budget is negative

        Note:
            Token counts use a 4 chars/token heuristic approximation.
            For strict LLM token budgets, apply a 0.8 safety factor.
        """
        if token_budget < 0:
            raise ValueError("Token budget must be non-negative")
        
        if token_budget == 0:
            return []
        
        result: List[HierarchicalSummary] = []
        remaining_budget = token_budget
        
        # Always try to include the root summary first
        if summary.token_count <= remaining_budget:
            result.append(summary)
            remaining_budget -= summary.token_count
        else:
            return result
        
        # Get child summaries from metadata
        child_summaries = summary.metadata.get("child_summaries", [])
        
        if not child_summaries:
            return result
        
        # Score and sort children by query relevance if query provided
        if query:
            query_lower = query.lower()
            
            def relevance_score(s: HierarchicalSummary) -> int:
                score = 0
                for acc in s.accomplishments:
                    if query_lower in acc.lower():
                        score += 10
                for blk in s.blockers:
                    if query_lower in blk.lower():
                        score += 5
                return score
            
            child_summaries = sorted(
                child_summaries,
                key=relevance_score,
                reverse=True
            )
        
        # Add children within budget
        for child in child_summaries:
            if child.token_count <= remaining_budget:
                result.append(child)
                remaining_budget -= child.token_count
                
                # Recursively expand child if budget allows
                nested_children = child.metadata.get("child_summaries", [])
                for nested in nested_children:
                    if nested.token_count <= remaining_budget:
                        result.append(nested)
                        remaining_budget -= nested.token_count
        
        # Sort result by hierarchy level (SESSION first, then PHASE, then TASK)
        result.sort(key=lambda s: s.level.value)
        
        return result

    def generate_full_session_summary(
        self,
        tasks: List[TaskLedger]
    ) -> HierarchicalSummary:
        """Generate a complete hierarchical session summary.
        
        Args:
            tasks: All tasks to summarize
            
        Returns:
            SESSION-level HierarchicalSummary with nested phases and tasks
        """
        if not tasks:
            now = datetime.now(timezone.utc)
            return HierarchicalSummary(
                level=SummaryLevel.SESSION,
                summary_id=f"SESSION-{uuid.uuid4().hex[:8]}",
                parent_id=None,
                start_time=now,
                end_time=now,
                accomplishments=[],
                blockers=[],
                token_count=0,
                child_count=0,
                metadata={"phase_count": 0, "total_task_count": 0},
            )
        
        # Detect phases
        phases = self.detect_phases(tasks)
        
        # Summarize each phase
        phase_summaries: List[HierarchicalSummary] = []
        
        for phase_tasks in phases:
            # Summarize tasks in this phase
            task_summaries = [self.summarize_task(t) for t in phase_tasks]
            
            # Aggregate into phase summary
            phase_summary = self.summarize_phase(task_summaries)
            phase_summaries.append(phase_summary)
        
        # Create session summary
        return self.summarize_session(phase_summaries)
