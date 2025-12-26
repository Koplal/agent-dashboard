"""
Runtime Ledger Tracker.

Provides real-time monitoring, metrics calculation, and
dashboard data generation for the ledger system.

Version: 2.6.0
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List, Callable, Awaitable

from .task_ledger import TaskStatus, TaskLedger
from .operations import LedgerManager
from .summarizer import HierarchicalSummary, HierarchicalSummarizer

logger = logging.getLogger(__name__)


@dataclass
class RuntimeMetrics:
    """Real-time execution metrics.

    Attributes:
        active_tasks: Number of currently in-progress tasks
        completed_tasks_last_hour: Tasks completed in the last hour
        blocked_tasks: Number of blocked tasks
        average_completion_time: Average time to complete tasks
        loop_detections: Number of loop detections
        human_escalations: Number of human escalations
        total_tokens_consumed: Total API tokens used
    """
    active_tasks: int
    completed_tasks_last_hour: int
    blocked_tasks: int
    average_completion_time: timedelta
    loop_detections: int
    human_escalations: int
    total_tokens_consumed: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "active_tasks": self.active_tasks,
            "completed_tasks_last_hour": self.completed_tasks_last_hour,
            "blocked_tasks": self.blocked_tasks,
            "average_completion_time_seconds": self.average_completion_time.total_seconds(),
            "loop_detections": self.loop_detections,
            "human_escalations": self.human_escalations,
            "total_tokens_consumed": self.total_tokens_consumed,
        }


class RuntimeLedgerTracker:
    """Real-time tracking and monitoring of ledger state.

    Provides:
    - Background monitoring for stale/blocked tasks
    - Real-time metrics calculation
    - Dashboard data generation
    - Callback hooks for issue detection
    """

    def __init__(
        self,
        ledger: LedgerManager,
        stale_threshold: timedelta = timedelta(minutes=30),
        on_stale_detected: Optional[Callable[[TaskLedger], Awaitable[None]]] = None,
        on_loop_detected: Optional[Callable[[TaskLedger], Awaitable[None]]] = None,
        on_blocked_detected: Optional[Callable[[TaskLedger], Awaitable[None]]] = None,
    ):
        """Initialize the runtime tracker.

        Args:
            ledger: LedgerManager instance to monitor
            stale_threshold: Time after which an in-progress task is stale
            on_stale_detected: Async callback when stale task detected
            on_loop_detected: Async callback when loop detected
            on_blocked_detected: Async callback when task becomes blocked
        """
        self.ledger = ledger
        self.stale_threshold = stale_threshold
        self.on_stale_detected = on_stale_detected
        self.on_loop_detected = on_loop_detected
        self.on_blocked_detected = on_blocked_detected
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None

    async def start_monitoring(self, check_interval: int = 60) -> None:
        """Begin background monitoring for issues.

        Args:
            check_interval: Seconds between checks
        """
        self._monitoring = True
        logger.info(f"Starting ledger monitoring (interval: {check_interval}s)")

        while self._monitoring:
            await self._check_for_issues()
            await asyncio.sleep(check_interval)

    def start_monitoring_background(self, check_interval: int = 60) -> asyncio.Task:
        """Start monitoring as a background task.

        Args:
            check_interval: Seconds between checks

        Returns:
            The asyncio Task running the monitor
        """
        self._monitor_task = asyncio.create_task(
            self.start_monitoring(check_interval)
        )
        return self._monitor_task

    def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        self._monitoring = False
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
        logger.info("Stopped ledger monitoring")

    async def _check_for_issues(self) -> None:
        """Check for stale tasks and other issues."""
        now = datetime.now(timezone.utc)

        for task_id, task in self.ledger.tasks.items():
            # Check for stale in-progress tasks
            if task.status == TaskStatus.IN_PROGRESS:
                if now - task.updated_at > self.stale_threshold:
                    logger.warning(f"Stale task detected: {task_id}")
                    if self.on_stale_detected:
                        await self.on_stale_detected(task)

            # Check for blocked tasks with loop detection
            if task.status == TaskStatus.BLOCKED:
                if "Loop detected" in task.notes:
                    if self.on_loop_detected:
                        await self.on_loop_detected(task)
                elif self.on_blocked_detected:
                    await self.on_blocked_detected(task)

    def get_metrics(self) -> RuntimeMetrics:
        """Calculate current runtime metrics.

        Returns:
            RuntimeMetrics with current state
        """
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)

        tasks = list(self.ledger.tasks.values())

        # Count by status
        active = [t for t in tasks if t.status == TaskStatus.IN_PROGRESS]
        completed_recent = [
            t for t in tasks
            if t.status == TaskStatus.COMPLETED and t.updated_at > one_hour_ago
        ]
        blocked = [t for t in tasks if t.status == TaskStatus.BLOCKED]

        # Calculate average completion time
        completed_with_time = [
            t for t in tasks
            if t.status == TaskStatus.COMPLETED
            and t.created_at
            and t.updated_at
            and t.progress_history  # Has actual progress
        ]
        if completed_with_time:
            avg_seconds = sum(
                (t.updated_at - t.created_at).total_seconds()
                for t in completed_with_time
            ) / len(completed_with_time)
            avg_completion = timedelta(seconds=avg_seconds)
        else:
            avg_completion = timedelta(0)

        # Count loop detections
        loop_detections = sum(
            1 for t in tasks if "Loop detected" in t.notes
        )

        # Count human escalations
        escalations = sum(
            1 for t in tasks
            if any(
                "escalate" in e.action_taken.lower()
                or "human" in e.action_taken.lower()
                for e in t.progress_history
            )
        )

        # Total tokens consumed
        total_tokens = sum(t.get_total_tokens() for t in tasks)

        return RuntimeMetrics(
            active_tasks=len(active),
            completed_tasks_last_hour=len(completed_recent),
            blocked_tasks=len(blocked),
            average_completion_time=avg_completion,
            loop_detections=loop_detections,
            human_escalations=escalations,
            total_tokens_consumed=total_tokens,
        )

    def generate_dashboard_data(self) -> Dict[str, Any]:
        """Generate data for dashboard display.

        Returns:
            Dictionary with metrics, phase summaries, and recent activity
        """
        metrics = self.get_metrics()

        # Get phase summaries
        by_phase = self.ledger.get_all_summaries()

        # Get recent activity (last 20 progress entries)
        all_entries: List[tuple] = []
        for task in self.ledger.tasks.values():
            for entry in task.progress_history:
                all_entries.append((task.task_id, task.title, entry))

        all_entries.sort(key=lambda x: x[2].timestamp, reverse=True)
        recent_activity = [
            {
                "task_id": tid,
                "task_title": title,
                "timestamp": entry.timestamp.isoformat(),
                "agent": entry.agent_id,
                "action": entry.action_taken,
                "outcome": entry.outcome,
            }
            for tid, title, entry in all_entries[:20]
        ]

        # Get blocked tasks detail
        blocked_detail = [
            {
                "task_id": t.task_id,
                "title": t.title,
                "blocked_since": t.updated_at.isoformat(),
                "notes": t.notes[-200:] if t.notes else "",
            }
            for t in self.ledger.get_blocked_tasks()
        ]

        # Get next actionable
        next_task = self.ledger.get_next_actionable()

        return {
            "metrics": metrics.to_dict(),
            "by_phase": by_phase,
            "recent_activity": recent_activity,
            "blocked_tasks": blocked_detail,
            "next_actionable": {
                "task_id": next_task.task_id,
                "title": next_task.title,
                "priority": next_task.priority.name,
            } if next_task else None,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_task_timeline(self, task_id: str) -> List[Dict[str, Any]]:
        """Get timeline of a specific task.

        Args:
            task_id: Task to get timeline for

        Returns:
            List of timeline events
        """
        task = self.ledger.get_task(task_id)
        if not task:
            return []

        timeline = [
            {
                "type": "created",
                "timestamp": task.created_at.isoformat(),
                "details": f"Task created: {task.title}",
            }
        ]

        for entry in task.progress_history:
            timeline.append({
                "type": "progress",
                "timestamp": entry.timestamp.isoformat(),
                "agent": entry.agent_id,
                "action": entry.action_taken,
                "outcome": entry.outcome,
                "artifacts": entry.artifacts_produced,
                "blockers": entry.blockers_encountered,
            })

        if task.status == TaskStatus.COMPLETED:
            timeline.append({
                "type": "completed",
                "timestamp": task.updated_at.isoformat(),
                "details": "Task completed",
            })

        return timeline

    def get_health_status(self) -> Dict[str, Any]:
        """Get overall system health status.

        Returns:
            Health status with warnings and recommendations
        """
        metrics = self.get_metrics()
        warnings = []
        recommendations = []

        # Check for concerning metrics
        if metrics.blocked_tasks > 0:
            warnings.append(f"{metrics.blocked_tasks} task(s) are blocked")
            recommendations.append("Review blocked tasks for loop patterns or dependencies")

        if metrics.loop_detections > 0:
            warnings.append(f"{metrics.loop_detections} loop detection(s) occurred")
            recommendations.append("Consider alternative approaches for looping tasks")

        # Check for stale tasks
        stale_count = sum(
            1 for t in self.ledger.tasks.values()
            if t.status == TaskStatus.IN_PROGRESS
            and datetime.now(timezone.utc) - t.updated_at > self.stale_threshold
        )
        if stale_count > 0:
            warnings.append(f"{stale_count} task(s) appear stale (no recent progress)")
            recommendations.append("Check stale tasks for issues or reassign")

        # Determine health level
        if metrics.blocked_tasks > 2 or metrics.loop_detections > 2:
            health = "degraded"
        elif warnings:
            health = "warning"
        else:
            health = "healthy"

        return {
            "status": health,
            "warnings": warnings,
            "recommendations": recommendations,
            "metrics_summary": {
                "active": metrics.active_tasks,
                "blocked": metrics.blocked_tasks,
                "completed_last_hour": metrics.completed_tasks_last_hour,
            },
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_session_summary(self) -> HierarchicalSummary:
        """Get hierarchical session summary.

        Generates a SESSION-level summary of all tasks in the ledger,
        including phase detection, accomplishment/blocker extraction,
        and hierarchical aggregation.

        Returns:
            HierarchicalSummary at SESSION level with nested phases and tasks
        """
        # Get all tasks from ledger
        tasks = list(self.ledger.tasks.values())
        
        # Use summarizer to generate full session summary
        summarizer = HierarchicalSummarizer()
        return summarizer.generate_full_session_summary(tasks)
