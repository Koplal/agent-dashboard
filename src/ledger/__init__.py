"""
Progress Ledger Module for Agent Dashboard.

Provides task tracking, loop detection, and progress monitoring
for multi-agent orchestration workflows.

Based on Microsoft Magentic-One patterns for robust orchestration.

Version: 2.6.0
"""

from .task_ledger import (
    TaskStatus,
    TaskPriority,
    ProgressEntry,
    TaskLedger,
)
from .operations import LedgerManager
from .runtime_tracker import RuntimeLedgerTracker, RuntimeMetrics

__all__ = [
    "TaskStatus",
    "TaskPriority",
    "ProgressEntry",
    "TaskLedger",
    "LedgerManager",
    "RuntimeLedgerTracker",
    "RuntimeMetrics",
]
