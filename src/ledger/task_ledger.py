"""
Task Ledger Data Classes.

Defines the core data structures for progress tracking:
- TaskStatus: Lifecycle states for tasks
- TaskPriority: Priority levels for scheduling
- ProgressEntry: Individual progress updates
- TaskLedger: Complete task tracking record

Version: 2.6.0
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class TaskStatus(Enum):
    """Lifecycle states for tasks."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    PENDING_REVIEW = "pending_review"
    COMPLETED = "completed"
    DEFERRED = "deferred"


class TaskPriority(Enum):
    """Priority levels for task scheduling."""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass
class ProgressEntry:
    """Individual progress update within a task.

    Attributes:
        timestamp: When the progress was recorded
        agent_id: Identifier of the agent/human making progress
        action_taken: Description of what was done
        outcome: Result of the action (success, failed, partial, etc.)
        artifacts_produced: List of files/outputs created
        blockers_encountered: Issues that impeded progress
        next_steps: Planned follow-up actions
        tokens_consumed: API tokens used (for cost tracking)
    """
    timestamp: datetime
    agent_id: str
    action_taken: str
    outcome: str
    artifacts_produced: List[str] = field(default_factory=list)
    blockers_encountered: List[str] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)
    tokens_consumed: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "agent_id": self.agent_id,
            "action_taken": self.action_taken,
            "outcome": self.outcome,
            "artifacts_produced": self.artifacts_produced,
            "blockers_encountered": self.blockers_encountered,
            "next_steps": self.next_steps,
            "tokens_consumed": self.tokens_consumed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProgressEntry":
        """Create from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            agent_id=data["agent_id"],
            action_taken=data["action_taken"],
            outcome=data["outcome"],
            artifacts_produced=data.get("artifacts_produced", []),
            blockers_encountered=data.get("blockers_encountered", []),
            next_steps=data.get("next_steps", []),
            tokens_consumed=data.get("tokens_consumed", 0),
        )


@dataclass
class TaskLedger:
    """Complete task tracking record.

    Implements the Task Ledger pattern from Microsoft Magentic-One
    for robust multi-agent orchestration with progress visibility.

    Attributes:
        task_id: Unique identifier (e.g., NESY-001)
        phase: Implementation phase (immediate, medium_term, long_term)
        category: Task category (validation, knowledge, verification, etc.)
        title: Short descriptive title
        objective: Full description of what needs to be accomplished
        status: Current lifecycle state
        priority: Scheduling priority
        created_at: When the task was created
        updated_at: Last modification time
        estimated_effort: Effort estimate (hours or story points)
        assigned_agent: Agent/human currently working on task
        dependencies: List of task_ids that must complete first
        acceptance_criteria: Conditions for task completion
        progress_history: Chronological list of progress updates
        subtasks: Nested subtasks for decomposition
        artifacts: Files/outputs produced by this task
        notes: Free-form notes and observations
    """
    task_id: str
    phase: str
    category: str
    title: str
    objective: str
    status: TaskStatus
    priority: TaskPriority
    created_at: datetime
    updated_at: datetime
    estimated_effort: str
    assigned_agent: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    progress_history: List[ProgressEntry] = field(default_factory=list)
    subtasks: List["TaskLedger"] = field(default_factory=list)
    artifacts: List[str] = field(default_factory=list)
    notes: str = ""

    def add_progress(self, entry: ProgressEntry) -> None:
        """Add a progress entry and update timestamp."""
        self.progress_history.append(entry)
        self.updated_at = entry.timestamp

    def get_latest_progress(self) -> Optional[ProgressEntry]:
        """Get the most recent progress entry."""
        if self.progress_history:
            return self.progress_history[-1]
        return None

    def get_total_tokens(self) -> int:
        """Calculate total tokens consumed across all progress."""
        return sum(e.tokens_consumed for e in self.progress_history)

    def get_duration(self) -> Optional[float]:
        """Get elapsed time in hours since task started."""
        if self.status == TaskStatus.NOT_STARTED:
            return None
        first_progress = next(
            (e for e in self.progress_history if e.outcome != "not_started"),
            None
        )
        if first_progress:
            delta = datetime.utcnow() - first_progress.timestamp
            return delta.total_seconds() / 3600
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "phase": self.phase,
            "category": self.category,
            "title": self.title,
            "objective": self.objective,
            "status": self.status.value,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "estimated_effort": self.estimated_effort,
            "assigned_agent": self.assigned_agent,
            "dependencies": self.dependencies,
            "acceptance_criteria": self.acceptance_criteria,
            "progress_history": [e.to_dict() for e in self.progress_history],
            "subtasks": [s.to_dict() for s in self.subtasks],
            "artifacts": self.artifacts,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskLedger":
        """Create from dictionary."""
        return cls(
            task_id=data["task_id"],
            phase=data["phase"],
            category=data["category"],
            title=data["title"],
            objective=data["objective"],
            status=TaskStatus(data["status"]),
            priority=TaskPriority(data["priority"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            estimated_effort=data["estimated_effort"],
            assigned_agent=data.get("assigned_agent"),
            dependencies=data.get("dependencies", []),
            acceptance_criteria=data.get("acceptance_criteria", []),
            progress_history=[
                ProgressEntry.from_dict(e) for e in data.get("progress_history", [])
            ],
            subtasks=[
                TaskLedger.from_dict(s) for s in data.get("subtasks", [])
            ],
            artifacts=data.get("artifacts", []),
            notes=data.get("notes", ""),
        )

    def __repr__(self) -> str:
        return f"TaskLedger({self.task_id}: {self.title} [{self.status.value}])"
