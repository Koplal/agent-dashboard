"""
Ledger Operations and Management.

Provides the LedgerManager class for centralized task tracking,
persistence, and loop detection.

Version: 2.6.0
"""

import json
import os
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

from .task_ledger import (
    TaskLedger,
    TaskStatus,
    TaskPriority,
    ProgressEntry,
)

logger = logging.getLogger(__name__)


class LedgerManager:
    """Central management for implementation progress.

    Provides:
    - Task creation and retrieval
    - Progress tracking with loop detection
    - JSON persistence for durability
    - Phase-based status summaries
    - Priority-based task scheduling

    Based on Microsoft Magentic-One Task Ledger pattern.
    """

    LEDGER_FILENAME = "task_ledger.json"

    def __init__(self, storage_path: str = "./ledger_data"):
        """Initialize the ledger manager.

        Args:
            storage_path: Directory for persistent storage
        """
        self.storage_path = Path(storage_path)
        self.tasks: Dict[str, TaskLedger] = {}
        self._ensure_storage_exists()
        self._load_existing()

    def _ensure_storage_exists(self) -> None:
        """Create storage directory if it doesn't exist."""
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def _get_ledger_path(self) -> Path:
        """Get path to the ledger file."""
        return self.storage_path / self.LEDGER_FILENAME

    def _load_existing(self) -> None:
        """Load existing tasks from persistent storage."""
        ledger_path = self._get_ledger_path()
        if ledger_path.exists():
            try:
                with open(ledger_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for task_data in data.get("tasks", []):
                    task = TaskLedger.from_dict(task_data)
                    self.tasks[task.task_id] = task
                logger.info(f"Loaded {len(self.tasks)} tasks from {ledger_path}")
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Failed to load ledger: {e}")
                self.tasks = {}

    def _save(self) -> None:
        """Persist tasks to storage."""
        ledger_path = self._get_ledger_path()
        data = {
            "version": "1.0.0",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "tasks": [task.to_dict() for task in self.tasks.values()],
        }
        try:
            with open(ledger_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved {len(self.tasks)} tasks to {ledger_path}")
        except IOError as e:
            logger.error(f"Failed to save ledger: {e}")

    def create_task(
        self,
        task_id: str,
        title: str,
        objective: str,
        phase: str = "immediate",
        category: str = "general",
        priority: TaskPriority = TaskPriority.MEDIUM,
        estimated_effort: str = "unknown",
        dependencies: Optional[List[str]] = None,
        acceptance_criteria: Optional[List[str]] = None,
    ) -> TaskLedger:
        """Create a new task in the ledger.

        Args:
            task_id: Unique identifier for the task
            title: Short descriptive title
            objective: Full description of what needs to be done
            phase: Implementation phase (immediate, medium_term, long_term)
            category: Task category
            priority: Task priority level
            estimated_effort: Effort estimate
            dependencies: Task IDs that must complete first
            acceptance_criteria: Conditions for completion

        Returns:
            The created TaskLedger instance
        """
        if task_id in self.tasks:
            raise ValueError(f"Task {task_id} already exists")

        now = datetime.now(timezone.utc)
        task = TaskLedger(
            task_id=task_id,
            phase=phase,
            category=category,
            title=title,
            objective=objective,
            status=TaskStatus.NOT_STARTED,
            priority=priority,
            created_at=now,
            updated_at=now,
            estimated_effort=estimated_effort,
            dependencies=dependencies or [],
            acceptance_criteria=acceptance_criteria or [],
        )
        self.tasks[task_id] = task
        self._save()
        logger.info(f"Created task {task_id}: {title}")
        return task

    def get_task(self, task_id: str) -> Optional[TaskLedger]:
        """Get a task by ID."""
        return self.tasks.get(task_id)

    def update_status(self, task_id: str, status: TaskStatus) -> None:
        """Update task status.

        Args:
            task_id: Task to update
            status: New status
        """
        task = self.tasks.get(task_id)
        if task:
            task.status = status
            task.updated_at = datetime.now(timezone.utc)
            self._save()
            logger.info(f"Updated {task_id} status to {status.value}")

    def add_progress(self, task_id: str, entry: ProgressEntry) -> None:
        """Record progress on a task with loop detection.

        Args:
            task_id: Task to update
            entry: Progress entry to add

        Raises:
            KeyError: If task doesn't exist
        """
        task = self.tasks.get(task_id)
        if not task:
            raise KeyError(f"Task {task_id} not found")

        task.add_progress(entry)

        # Detect repetitive patterns
        if self._detect_loop(task):
            task.status = TaskStatus.BLOCKED
            task.notes += f"\n[{entry.timestamp.isoformat()}] Loop detected - requires new approach"
            logger.warning(f"Loop detected in task {task_id}")

        self._save()

    def _detect_loop(self, task: TaskLedger) -> bool:
        """Identify if task is repeating without progress.

        Detects loops by checking if recent action-outcome pairs
        are repetitive (less than 50% unique).

        Args:
            task: Task to check

        Returns:
            True if loop detected
        """
        if len(task.progress_history) < 4:
            return False

        recent = task.progress_history[-4:]
        action_outcomes = [(e.action_taken, e.outcome) for e in recent]
        unique_pairs = set(action_outcomes)

        return len(unique_pairs) < len(action_outcomes) * 0.5

    def get_phase_summary(self, phase: str) -> Dict[str, Any]:
        """Generate status report for a phase.

        Args:
            phase: Phase to summarize (immediate, medium_term, long_term)

        Returns:
            Dictionary with task counts by status
        """
        phase_tasks = [t for t in self.tasks.values() if t.phase == phase]
        return {
            "phase": phase,
            "total": len(phase_tasks),
            "completed": sum(1 for t in phase_tasks if t.status == TaskStatus.COMPLETED),
            "in_progress": sum(1 for t in phase_tasks if t.status == TaskStatus.IN_PROGRESS),
            "blocked": sum(1 for t in phase_tasks if t.status == TaskStatus.BLOCKED),
            "pending_review": sum(1 for t in phase_tasks if t.status == TaskStatus.PENDING_REVIEW),
            "not_started": sum(1 for t in phase_tasks if t.status == TaskStatus.NOT_STARTED),
            "deferred": sum(1 for t in phase_tasks if t.status == TaskStatus.DEFERRED),
        }

    def get_all_summaries(self) -> Dict[str, Dict[str, Any]]:
        """Get summaries for all phases."""
        return {
            phase: self.get_phase_summary(phase)
            for phase in ["immediate", "medium_term", "long_term"]
        }

    def get_next_actionable(self) -> Optional[TaskLedger]:
        """Return highest priority task ready for work.

        A task is actionable if:
        - Status is NOT_STARTED or IN_PROGRESS
        - All dependencies are COMPLETED

        Returns:
            Highest priority actionable task, or None
        """
        candidates = [
            t for t in self.tasks.values()
            if t.status in [TaskStatus.NOT_STARTED, TaskStatus.IN_PROGRESS]
            and self._dependencies_satisfied(t)
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda t: (t.priority.value, t.created_at))

    def _dependencies_satisfied(self, task: TaskLedger) -> bool:
        """Check if all task dependencies are completed."""
        for dep_id in task.dependencies:
            dep_task = self.tasks.get(dep_id)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                return False
        return True

    def get_blocked_tasks(self) -> List[TaskLedger]:
        """Get all blocked tasks."""
        return [t for t in self.tasks.values() if t.status == TaskStatus.BLOCKED]

    def get_tasks_by_category(self, category: str) -> List[TaskLedger]:
        """Get all tasks in a category."""
        return [t for t in self.tasks.values() if t.category == category]

    def add_artifact(self, task_id: str, artifact: str) -> None:
        """Add an artifact to a task.

        Args:
            task_id: Task to update
            artifact: File path or artifact identifier
        """
        task = self.tasks.get(task_id)
        if task:
            task.artifacts.append(artifact)
            task.updated_at = datetime.now(timezone.utc)
            self._save()

    def complete_task(self, task_id: str, final_notes: str = "") -> None:
        """Mark a task as completed.

        Args:
            task_id: Task to complete
            final_notes: Optional completion notes
        """
        task = self.tasks.get(task_id)
        if task:
            task.status = TaskStatus.COMPLETED
            task.updated_at = datetime.now(timezone.utc)
            if final_notes:
                task.notes += f"\n[COMPLETED] {final_notes}"
            self._save()
            logger.info(f"Completed task {task_id}")

    def export_report(self) -> Dict[str, Any]:
        """Export full ledger report.

        Returns:
            Complete ledger state as dictionary
        """
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summaries": self.get_all_summaries(),
            "tasks": [task.to_dict() for task in self.tasks.values()],
            "blocked_tasks": [t.task_id for t in self.get_blocked_tasks()],
            "next_actionable": (
                self.get_next_actionable().task_id
                if self.get_next_actionable()
                else None
            ),
        }
