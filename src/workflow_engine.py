#!/usr/bin/env python3
"""
workflow_engine.py - Multi-Agent Workflow Orchestration Engine v2.1

Implements a Test-Driven Development (TDD) workflow for autonomous Claude Code:

CORE PHILOSOPHY:
  1. Design what you want the feature to do
  2. Flesh out requirements and specifications
  3. Design unit tests and integration tests that GUARANTEE functionality
  4. Write tests FIRST from the test spec
  5. Then write code - it MUST pass all tests, CANNOT change tests
  6. NO TODOs, NO mocks in production code

Design Patterns Implemented:
  1. Constitutional Constraints - Executable governance via positive framing
  2. Ephemeral Task Sandboxes - Context isolation per task
  3. Verified Incrementalism - Micro-generation with interleaved verification
  4. Subagent Orchestration - Multi-agent delegation patterns
  5. Defense-in-Depth Validation - Four-layer validation stack
  6. Test-Driven Development - Tests define correctness, code follows

Workflow Phases:
  SPEC → TEST_DESIGN → TEST_IMPL → IMPLEMENT → VALIDATE → REVIEW → DELIVER

Usage:
    from workflow_engine import WorkflowEngine, Task, WorkflowPhase

    engine = WorkflowEngine(budget_limit=1.0)
    workflow = engine.create_workflow("Build user authentication")
    workflow.execute()
"""

import json
import os
import sys
import hashlib
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable
import sqlite3
import threading

# Try to import tiktoken for token estimation
try:
    import tiktoken
    _encoding = tiktoken.get_encoding("cl100k_base")
    _TIKTOKEN_AVAILABLE = True
except (ImportError, Exception):
    # ImportError: tiktoken not installed
    # Other exceptions: network errors when downloading encoding files
    _encoding = None
    _TIKTOKEN_AVAILABLE = False


# ============================================================================
# ENUMS AND CONSTANTS
# ============================================================================

class WorkflowPhase(Enum):
    """
    Phases that enforce the TDD Locked Gate Pattern.

    The workflow follows strict TDD principles:
    1. SPEC: Define what the feature does (product spec)
    2. TEST_DESIGN: Design tests that guarantee requirements
    3. TEST_IMPL: Write tests FIRST (tests are immutable after this)
    4. IMPLEMENT: Write code to pass tests (cannot modify tests)
    5. VALIDATE: Run full validation stack
    6. REVIEW: Critical review and quality assessment
    7. DELIVER: Final synthesis and delivery
    """
    SPEC = auto()         # Feature specification and requirements
    TEST_DESIGN = auto()  # Design test cases and scenarios
    TEST_IMPL = auto()    # Write tests first (TDD - tests become immutable)
    IMPLEMENT = auto()    # Write code to pass tests (cannot change tests)
    VALIDATE = auto()     # Run validation layers
    REVIEW = auto()       # Critic and quality assessment
    DELIVER = auto()      # Final synthesis and delivery


class TaskStatus(Enum):
    """Task lifecycle states."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class AgentTier(Enum):
    """Model tier assignments for cost governance."""
    OPUS = "opus"       # Strategic, quality-critical tasks
    SONNET = "sonnet"   # Analysis, research tasks
    HAIKU = "haiku"     # Execution, routine tasks


# Model pricing (per million tokens)
MODEL_PRICING = {
    "opus": {"input": 15.0, "output": 75.0},
    "sonnet": {"input": 3.0, "output": 15.0},
    "haiku": {"input": 0.25, "output": 1.25},
}

# Agent registry with tier assignments
AGENT_REGISTRY = {
    # Tier 1 - Opus (Strategic/Quality)
    "orchestrator": {"tier": AgentTier.OPUS, "role": "coordinator"},
    "synthesis": {"tier": AgentTier.OPUS, "role": "synthesizer"},
    "critic": {"tier": AgentTier.OPUS, "role": "reviewer"},
    "planner": {"tier": AgentTier.OPUS, "role": "planner"},

    # Tier 2 - Sonnet (Analysis/Research)
    "researcher": {"tier": AgentTier.SONNET, "role": "researcher"},
    "perplexity-researcher": {"tier": AgentTier.SONNET, "role": "researcher"},
    "research-judge": {"tier": AgentTier.SONNET, "role": "reviewer"},
    "claude-md-auditor": {"tier": AgentTier.SONNET, "role": "auditor"},
    "implementer": {"tier": AgentTier.SONNET, "role": "implementer"},

    # Panel Judges - Sonnet (Quality Evaluation)
    "panel-coordinator": {"tier": AgentTier.SONNET, "role": "coordinator"},
    "judge-technical": {"tier": AgentTier.SONNET, "role": "reviewer"},
    "judge-completeness": {"tier": AgentTier.SONNET, "role": "reviewer"},
    "judge-practicality": {"tier": AgentTier.SONNET, "role": "reviewer"},
    "judge-adversarial": {"tier": AgentTier.SONNET, "role": "reviewer"},
    "judge-user": {"tier": AgentTier.SONNET, "role": "reviewer"},

    # Tier 3 - Haiku (Execution)
    "web-search-researcher": {"tier": AgentTier.HAIKU, "role": "researcher"},
    "summarizer": {"tier": AgentTier.HAIKU, "role": "synthesizer"},
    "test-writer": {"tier": AgentTier.HAIKU, "role": "tester"},
    "installer": {"tier": AgentTier.HAIKU, "role": "executor"},
    "validator": {"tier": AgentTier.HAIKU, "role": "validator"},
}


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class Task:
    """A single task in a workflow."""
    id: str
    content: str
    active_form: str
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent: Optional[str] = None
    phase: WorkflowPhase = WorkflowPhase.SPEC
    priority: int = 0
    dependencies: List[str] = field(default_factory=list)
    tokens_used: int = 0
    cost: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "content": self.content,
            "activeForm": self.active_form,
            "status": self.status.value,
            "assigned_agent": self.assigned_agent,
            "phase": self.phase.name,
            "priority": self.priority,
            "dependencies": self.dependencies,
            "tokens_used": self.tokens_used,
            "cost": self.cost,
        }


@dataclass
class ValidationResult:
    """Result from a validation layer."""
    layer: str
    passed: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class WorkflowCheckpoint:
    """Human-in-the-loop checkpoint."""
    name: str
    phase: WorkflowPhase
    requires_approval: bool = True
    auto_proceed_conditions: List[str] = field(default_factory=list)
    approved: Optional[bool] = None
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None


@dataclass
class BudgetState:
    """Tracks cost governance state."""
    limit: float
    spent: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    warnings_issued: int = 0
    circuit_broken: bool = False

    @property
    def remaining(self) -> float:
        return max(0, self.limit - self.spent)

    @property
    def utilization(self) -> float:
        return (self.spent / self.limit * 100) if self.limit > 0 else 0


# ============================================================================
# COST GOVERNANCE - CIRCUIT BREAKER
# ============================================================================

class CostCircuitBreaker:
    """
    Implements cost governance with budget enforcement.

    Design Shift 5: Defense-in-Depth Validation
    - Tracks token usage across all agents
    - Enforces budget limits with circuit breaker pattern
    - Provides warnings at threshold levels
    """

    WARNING_THRESHOLDS = [0.5, 0.75, 0.9]  # 50%, 75%, 90%

    def __init__(self, budget_limit: float = 1.0):
        self.budget = BudgetState(limit=budget_limit)
        self._lock = threading.Lock()
        self._callbacks: List[Callable] = []

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count using tiktoken."""
        if not text:
            return 0
        if _TIKTOKEN_AVAILABLE and _encoding is not None:
            try:
                return len(_encoding.encode(text))
            except Exception:
                pass
        return len(text) // 4

    def estimate_cost(self, tokens_in: int, tokens_out: int, model: str) -> float:
        """Calculate cost for token usage."""
        model_key = model.lower()
        for key in MODEL_PRICING:
            if key in model_key:
                prices = MODEL_PRICING[key]
                return (tokens_in * prices["input"] + tokens_out * prices["output"]) / 1_000_000
        # Default to sonnet
        return (tokens_in * 3.0 + tokens_out * 15.0) / 1_000_000

    def check_budget(self, estimated_cost: float) -> tuple[bool, str]:
        """
        Check if operation is within budget.

        Returns:
            (allowed, message) tuple
        """
        with self._lock:
            if self.budget.circuit_broken:
                return False, "CIRCUIT BROKEN: Budget exhausted. Manual reset required."

            projected = self.budget.spent + estimated_cost

            if projected > self.budget.limit:
                self.budget.circuit_broken = True
                return False, f"BUDGET EXCEEDED: ${projected:.4f} > ${self.budget.limit:.4f}"

            # Check warning thresholds
            utilization = projected / self.budget.limit
            for threshold in self.WARNING_THRESHOLDS:
                if utilization >= threshold and self.budget.warnings_issued < self.WARNING_THRESHOLDS.index(threshold) + 1:
                    self.budget.warnings_issued += 1
                    return True, f"WARNING: Budget at {utilization*100:.0f}% (${projected:.4f}/${self.budget.limit:.4f})"

            return True, "OK"

    def record_usage(self, tokens_in: int, tokens_out: int, model: str) -> float:
        """Record token usage and return cost."""
        cost = self.estimate_cost(tokens_in, tokens_out, model)
        with self._lock:
            self.budget.spent += cost
            self.budget.tokens_in += tokens_in
            self.budget.tokens_out += tokens_out
        return cost

    def reset(self, new_limit: Optional[float] = None):
        """Reset circuit breaker state."""
        with self._lock:
            self.budget = BudgetState(limit=new_limit or self.budget.limit)

    def get_status(self) -> Dict[str, Any]:
        """Get current budget status."""
        with self._lock:
            return {
                "limit": self.budget.limit,
                "spent": self.budget.spent,
                "remaining": self.budget.remaining,
                "utilization": f"{self.budget.utilization:.1f}%",
                "tokens_in": self.budget.tokens_in,
                "tokens_out": self.budget.tokens_out,
                "circuit_broken": self.budget.circuit_broken,
            }


# ============================================================================
# VALIDATION LAYER STACK
# ============================================================================

class ValidationLayerStack:
    """
    Four-Layer Validation Stack (Design Shift 5).

    Layer 1: Static Analysis (Pre-commit)
    Layer 2: Unit Test Suite
    Layer 3: Integration Test Sandbox
    Layer 4: Behavioral Diff Auditing
    """

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.results: List[ValidationResult] = []

    def run_layer_1_static_analysis(self) -> ValidationResult:
        """
        Layer 1: Static Analysis
        - TypeScript/ESLint checks
        - Import validation
        - Formatting verification
        """
        checks = []
        passed = True

        # TypeScript check
        if (self.project_root / "tsconfig.json").exists():
            try:
                result = subprocess.run(
                    ["npx", "tsc", "--noEmit"],
                    capture_output=True, text=True, timeout=60,
                    cwd=self.project_root
                )
                if result.returncode != 0:
                    passed = False
                    checks.append({"check": "typescript", "passed": False, "output": result.stderr[:500]})
                else:
                    checks.append({"check": "typescript", "passed": True})
            except Exception as e:
                checks.append({"check": "typescript", "passed": False, "error": str(e)})

        # Python type check (if applicable)
        if list(self.project_root.glob("**/*.py")):
            try:
                result = subprocess.run(
                    ["python3", "-m", "py_compile"] + [str(f) for f in self.project_root.glob("**/*.py")][:10],
                    capture_output=True, text=True, timeout=30,
                    cwd=self.project_root
                )
                if result.returncode != 0:
                    passed = False
                    checks.append({"check": "python_syntax", "passed": False, "output": result.stderr[:500]})
                else:
                    checks.append({"check": "python_syntax", "passed": True})
            except Exception as e:
                checks.append({"check": "python_syntax", "passed": False, "error": str(e)})

        result = ValidationResult(
            layer="static_analysis",
            passed=passed,
            message="Static analysis " + ("passed" if passed else "failed"),
            details={"checks": checks}
        )
        self.results.append(result)
        return result

    def run_layer_2_unit_tests(self, test_pattern: str = "test_*.py") -> ValidationResult:
        """
        Layer 2: Unit Test Suite
        - Run test suite
        - Check coverage thresholds
        """
        passed = True
        details = {}

        # Try pytest first
        try:
            result = subprocess.run(
                ["python3", "-m", "pytest", "-v", "--tb=short"],
                capture_output=True, text=True, timeout=120,
                cwd=self.project_root
            )
            details["framework"] = "pytest"
            details["output"] = result.stdout[-1000:] if result.stdout else ""
            details["errors"] = result.stderr[-500:] if result.stderr else ""
            passed = result.returncode == 0
        except FileNotFoundError:
            # Try npm test
            if (self.project_root / "package.json").exists():
                try:
                    result = subprocess.run(
                        ["npm", "test"],
                        capture_output=True, text=True, timeout=120,
                        cwd=self.project_root
                    )
                    details["framework"] = "npm"
                    details["output"] = result.stdout[-1000:] if result.stdout else ""
                    passed = result.returncode == 0
                except Exception as e:
                    details["error"] = str(e)
                    passed = False
        except Exception as e:
            details["error"] = str(e)
            passed = False

        result = ValidationResult(
            layer="unit_tests",
            passed=passed,
            message="Unit tests " + ("passed" if passed else "failed"),
            details=details
        )
        self.results.append(result)
        return result

    def run_layer_3_integration_sandbox(self, sandbox_cmd: Optional[str] = None) -> ValidationResult:
        """
        Layer 3: Integration Test Sandbox
        - Isolated execution environment
        - No network access (configurable)
        """
        passed = True
        details = {"sandbox": "local"}

        if sandbox_cmd:
            try:
                result = subprocess.run(
                    sandbox_cmd.split(),
                    capture_output=True, text=True, timeout=300,
                    cwd=self.project_root
                )
                details["output"] = result.stdout[-1000:] if result.stdout else ""
                passed = result.returncode == 0
            except Exception as e:
                details["error"] = str(e)
                passed = False
        else:
            details["message"] = "No integration sandbox configured"

        result = ValidationResult(
            layer="integration_sandbox",
            passed=passed,
            message="Integration sandbox " + ("passed" if passed else "failed"),
            details=details
        )
        self.results.append(result)
        return result

    def run_layer_4_behavioral_diff(self) -> ValidationResult:
        """
        Layer 4: Behavioral Diff Auditing
        - Summarize functional changes
        - Generate human-readable diff report
        """
        details = {}

        try:
            # Get git diff stats
            result = subprocess.run(
                ["git", "diff", "--stat", "HEAD~1"],
                capture_output=True, text=True, timeout=10,
                cwd=self.project_root
            )
            details["diff_stat"] = result.stdout if result.returncode == 0 else ""

            # Get changed files
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD~1"],
                capture_output=True, text=True, timeout=10,
                cwd=self.project_root
            )
            details["changed_files"] = result.stdout.strip().split("\n") if result.returncode == 0 else []

            # Count additions/deletions
            result = subprocess.run(
                ["git", "diff", "--shortstat", "HEAD~1"],
                capture_output=True, text=True, timeout=10,
                cwd=self.project_root
            )
            details["shortstat"] = result.stdout.strip() if result.returncode == 0 else ""

        except Exception as e:
            details["error"] = str(e)

        result = ValidationResult(
            layer="behavioral_diff",
            passed=True,  # This layer is informational
            message="Behavioral diff generated",
            details=details
        )
        self.results.append(result)
        return result

    def run_all_layers(self) -> List[ValidationResult]:
        """Run all validation layers sequentially."""
        results = []
        results.append(self.run_layer_1_static_analysis())
        results.append(self.run_layer_2_unit_tests())
        results.append(self.run_layer_3_integration_sandbox())
        results.append(self.run_layer_4_behavioral_diff())
        return results

    def get_summary(self) -> Dict[str, Any]:
        """Get validation summary."""
        return {
            "total_layers": len(self.results),
            "passed": sum(1 for r in self.results if r.passed),
            "failed": sum(1 for r in self.results if not r.passed),
            "results": [
                {"layer": r.layer, "passed": r.passed, "message": r.message}
                for r in self.results
            ]
        }


# ============================================================================
# WORKFLOW ENGINE
# ============================================================================

class Workflow:
    """
    Represents a complete TDD workflow with tasks, phases, and checkpoints.

    Implements:
    - TDD Locked Gate Pattern (spec -> test_design -> test_impl -> implement -> validate)
    - Test-First Development (tests are written before implementation)
    - Test Immutability (tests cannot be modified during implementation)
    - Checklist-Scratchpad Pattern
    - Human-in-the-Loop Checkpoints

    TDD Rules:
    - Tests define correctness - code must pass ALL tests
    - Tests are IMMUTABLE after TEST_IMPL phase
    - NO TODOs in production code
    - NO mocks in production code (only in tests)
    - Implementation auto-iterates until all tests pass
    """

    def __init__(
        self,
        name: str,
        description: str,
        circuit_breaker: CostCircuitBreaker,
        project_root: str = "."
    ):
        self.id = hashlib.md5(f"{name}{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        self.name = name
        self.description = description
        self.tasks: List[Task] = []
        self.checkpoints: List[WorkflowCheckpoint] = []
        self.current_phase = WorkflowPhase.SPEC
        self.circuit_breaker = circuit_breaker
        self.validation_stack = ValidationLayerStack(project_root)
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self._task_counter = 0

    def add_task(
        self,
        content: str,
        active_form: str,
        phase: WorkflowPhase = WorkflowPhase.SPEC,
        assigned_agent: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
        priority: int = 0
    ) -> Task:
        """Add a task to the workflow."""
        self._task_counter += 1
        task = Task(
            id=f"{self.id}-{self._task_counter:03d}",
            content=content,
            active_form=active_form,
            phase=phase,
            assigned_agent=assigned_agent,
            dependencies=dependencies or [],
            priority=priority
        )
        self.tasks.append(task)
        return task

    def add_checkpoint(
        self,
        name: str,
        phase: WorkflowPhase,
        requires_approval: bool = True,
        auto_proceed_conditions: Optional[List[str]] = None
    ) -> WorkflowCheckpoint:
        """Add a human-in-the-loop checkpoint."""
        checkpoint = WorkflowCheckpoint(
            name=name,
            phase=phase,
            requires_approval=requires_approval,
            auto_proceed_conditions=auto_proceed_conditions or []
        )
        self.checkpoints.append(checkpoint)
        return checkpoint

    def get_tasks_for_phase(self, phase: WorkflowPhase) -> List[Task]:
        """Get all tasks for a specific phase."""
        return [t for t in self.tasks if t.phase == phase]

    def get_pending_tasks(self) -> List[Task]:
        """Get all pending tasks in priority order."""
        return sorted(
            [t for t in self.tasks if t.status == TaskStatus.PENDING],
            key=lambda t: (-t.priority, t.created_at)
        )

    def get_next_task(self) -> Optional[Task]:
        """Get the next task to execute based on dependencies and priority."""
        pending = self.get_pending_tasks()
        for task in pending:
            # Check if all dependencies are completed
            deps_completed = all(
                any(t.id == dep_id and t.status == TaskStatus.COMPLETED for t in self.tasks)
                for dep_id in task.dependencies
            )
            if deps_completed:
                return task
        return None

    def advance_phase(self) -> WorkflowPhase:
        """Advance to the next workflow phase."""
        phase_order = list(WorkflowPhase)
        current_idx = phase_order.index(self.current_phase)
        if current_idx < len(phase_order) - 1:
            self.current_phase = phase_order[current_idx + 1]
        return self.current_phase

    def get_checkpoint_for_phase(self, phase: WorkflowPhase) -> Optional[WorkflowCheckpoint]:
        """Get checkpoint for a phase if one exists."""
        for cp in self.checkpoints:
            if cp.phase == phase:
                return cp
        return None

    def to_todo_list(self) -> List[Dict[str, Any]]:
        """Convert workflow tasks to TodoWrite format."""
        return [task.to_dict() for task in self.tasks]

    def get_status(self) -> Dict[str, Any]:
        """Get workflow status summary."""
        return {
            "id": self.id,
            "name": self.name,
            "current_phase": self.current_phase.name,
            "total_tasks": len(self.tasks),
            "pending": sum(1 for t in self.tasks if t.status == TaskStatus.PENDING),
            "in_progress": sum(1 for t in self.tasks if t.status == TaskStatus.IN_PROGRESS),
            "completed": sum(1 for t in self.tasks if t.status == TaskStatus.COMPLETED),
            "failed": sum(1 for t in self.tasks if t.status == TaskStatus.FAILED),
            "total_tokens": sum(t.tokens_used for t in self.tasks),
            "total_cost": sum(t.cost for t in self.tasks),
            "budget_status": self.circuit_breaker.get_status(),
        }


class WorkflowEngine:
    """
    Main workflow orchestration engine.

    Implements all five design shifts:
    1. Constitutional Constraints
    2. Ephemeral Task Sandboxes
    3. Verified Incrementalism
    4. Subagent Orchestration
    5. Defense-in-Depth Validation
    """

    def __init__(
        self,
        budget_limit: float = 1.0,
        project_root: str = ".",
        db_path: str = "~/.claude/workflow_engine.db"
    ):
        self.circuit_breaker = CostCircuitBreaker(budget_limit)
        self.project_root = Path(project_root)
        self.db_path = Path(db_path).expanduser()
        self.workflows: Dict[str, Workflow] = {}
        self._init_db()

    def _init_db(self):
        """Initialize workflow database."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workflows (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    status TEXT,
                    created_at TEXT,
                    completed_at TEXT,
                    total_cost REAL DEFAULT 0,
                    data TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workflow_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_id TEXT,
                    event_type TEXT,
                    phase TEXT,
                    task_id TEXT,
                    agent TEXT,
                    tokens_in INTEGER DEFAULT 0,
                    tokens_out INTEGER DEFAULT 0,
                    cost REAL DEFAULT 0,
                    timestamp TEXT,
                    data TEXT,
                    FOREIGN KEY (workflow_id) REFERENCES workflows(id)
                )
            """)
            conn.commit()

    def create_workflow(
        self,
        name: str,
        description: str = "",
        budget_override: Optional[float] = None
    ) -> Workflow:
        """
        Create a new TDD workflow with proper initialization.

        Implements TDD Locked Gate Pattern with checkpoints:
        1. SPEC approval - Human reviews feature specification
        2. TEST_DESIGN approval - Human reviews test design
        3. TEST_IMPL lock - Tests become IMMUTABLE after this
        4. IMPLEMENT - Auto-iterate until all tests pass
        5. VALIDATE - Auto-proceed if all validations pass
        6. REVIEW - Human reviews final implementation
        """
        if budget_override:
            self.circuit_breaker.reset(budget_override)

        workflow = Workflow(
            name=name,
            description=description,
            circuit_breaker=self.circuit_breaker,
            project_root=str(self.project_root)
        )

        # Add TDD-specific checkpoints (Locked Gate Pattern)
        workflow.add_checkpoint(
            "Specification Review",
            WorkflowPhase.SPEC,
            requires_approval=True
        )
        workflow.add_checkpoint(
            "Test Design Review",
            WorkflowPhase.TEST_DESIGN,
            requires_approval=True  # Critical: approve test design before writing
        )
        workflow.add_checkpoint(
            "Test Implementation Lock",
            WorkflowPhase.TEST_IMPL,
            requires_approval=True  # CRITICAL: Tests become IMMUTABLE after approval
        )
        workflow.add_checkpoint(
            "Implementation Complete",
            WorkflowPhase.IMPLEMENT,
            requires_approval=False,
            auto_proceed_conditions=["all_tests_pass"]  # Auto-proceed when all tests pass
        )
        workflow.add_checkpoint(
            "Validation Review",
            WorkflowPhase.VALIDATE,
            requires_approval=False,
            auto_proceed_conditions=["all_validations_pass"]
        )
        workflow.add_checkpoint(
            "Final Review",
            WorkflowPhase.REVIEW,
            requires_approval=True
        )

        self.workflows[workflow.id] = workflow
        self._save_workflow(workflow)
        return workflow

    def create_workflow_from_task(self, task_description: str) -> Workflow:
        """
        Decompose a task description into a TDD workflow.

        Implements Test-Driven Development:
        1. SPEC: Design what you want the feature to do
        2. TEST_DESIGN: Design tests that guarantee requirements
        3. TEST_IMPL: Write tests FIRST (tests become IMMUTABLE)
        4. IMPLEMENT: Write code to pass tests (cannot change tests)
        5. VALIDATE: Run full validation stack
        6. REVIEW: Critical review
        7. DELIVER: Final synthesis

        TDD RULES:
        - Tests define correctness
        - Tests are IMMUTABLE after TEST_IMPL
        - NO TODOs in production code
        - NO mocks in production code
        - Auto-iterate until ALL tests pass
        """
        workflow = self.create_workflow(
            name=f"TDD Workflow: {task_description[:50]}",
            description=task_description
        )

        # =====================================================================
        # Phase 1: SPEC - Feature specification and requirements
        # =====================================================================
        workflow.add_task(
            "Analyze task requirements and define feature scope",
            "Analyzing requirements",
            phase=WorkflowPhase.SPEC,
            assigned_agent="planner",
            priority=100
        )
        workflow.add_task(
            "Explore codebase for existing patterns and conventions",
            "Exploring codebase",
            phase=WorkflowPhase.SPEC,
            assigned_agent="researcher",
            priority=99
        )
        workflow.add_task(
            "Create detailed product specification document",
            "Creating specification",
            phase=WorkflowPhase.SPEC,
            assigned_agent="planner",
            priority=98
        )
        workflow.add_task(
            "Define success criteria and acceptance requirements",
            "Defining success criteria",
            phase=WorkflowPhase.SPEC,
            assigned_agent="planner",
            priority=97
        )

        # =====================================================================
        # Phase 2: TEST_DESIGN - Design tests that guarantee requirements
        # =====================================================================
        workflow.add_task(
            "Design unit test cases from specification",
            "Designing unit tests",
            phase=WorkflowPhase.TEST_DESIGN,
            assigned_agent="test-writer",
            priority=90
        )
        workflow.add_task(
            "Design integration test cases for system boundaries",
            "Designing integration tests",
            phase=WorkflowPhase.TEST_DESIGN,
            assigned_agent="test-writer",
            priority=89
        )
        workflow.add_task(
            "Design edge case and error condition tests",
            "Designing edge case tests",
            phase=WorkflowPhase.TEST_DESIGN,
            assigned_agent="test-writer",
            priority=88
        )
        workflow.add_task(
            "Review test design for completeness and correctness",
            "Reviewing test design",
            phase=WorkflowPhase.TEST_DESIGN,
            assigned_agent="critic",
            priority=87
        )

        # =====================================================================
        # Phase 3: TEST_IMPL - Write tests FIRST (tests become IMMUTABLE)
        # =====================================================================
        workflow.add_task(
            "Implement unit tests from test design spec",
            "Implementing unit tests",
            phase=WorkflowPhase.TEST_IMPL,
            assigned_agent="test-writer",
            priority=80
        )
        workflow.add_task(
            "Implement integration tests from test design spec",
            "Implementing integration tests",
            phase=WorkflowPhase.TEST_IMPL,
            assigned_agent="test-writer",
            priority=79
        )
        workflow.add_task(
            "Verify all tests fail (code not yet written)",
            "Verifying tests fail",
            phase=WorkflowPhase.TEST_IMPL,
            assigned_agent="validator",
            priority=78
        )
        workflow.add_task(
            "LOCK TESTS: Mark tests as immutable for implementation phase",
            "Locking tests",
            phase=WorkflowPhase.TEST_IMPL,
            assigned_agent="validator",
            priority=77
        )

        # =====================================================================
        # Phase 4: IMPLEMENT - Write code to pass tests (CANNOT change tests)
        # =====================================================================
        workflow.add_task(
            "Implement minimum code to pass first test",
            "Implementing code",
            phase=WorkflowPhase.IMPLEMENT,
            assigned_agent="implementer",
            priority=70
        )
        workflow.add_task(
            "Iterate implementation until ALL tests pass",
            "Iterating until tests pass",
            phase=WorkflowPhase.IMPLEMENT,
            assigned_agent="implementer",
            priority=69
        )
        workflow.add_task(
            "Verify NO TODOs in production code",
            "Checking for TODOs",
            phase=WorkflowPhase.IMPLEMENT,
            assigned_agent="validator",
            priority=68
        )
        workflow.add_task(
            "Verify NO mocks in production code",
            "Checking for mocks",
            phase=WorkflowPhase.IMPLEMENT,
            assigned_agent="validator",
            priority=67
        )

        # =====================================================================
        # Phase 5: VALIDATE - Run full validation stack
        # =====================================================================
        workflow.add_task(
            "Run static analysis (type check, lint)",
            "Running static analysis",
            phase=WorkflowPhase.VALIDATE,
            assigned_agent="validator",
            priority=60
        )
        workflow.add_task(
            "Run complete test suite (must be 100% passing)",
            "Running test suite",
            phase=WorkflowPhase.VALIDATE,
            assigned_agent="validator",
            priority=59
        )
        workflow.add_task(
            "Run integration tests in sandbox",
            "Running integration tests",
            phase=WorkflowPhase.VALIDATE,
            assigned_agent="validator",
            priority=58
        )
        workflow.add_task(
            "Generate behavioral diff report",
            "Generating diff report",
            phase=WorkflowPhase.VALIDATE,
            assigned_agent="validator",
            priority=57
        )

        # =====================================================================
        # Phase 6: REVIEW - Critical review and quality assessment
        # =====================================================================
        workflow.add_task(
            "Critical review of implementation quality",
            "Reviewing implementation",
            phase=WorkflowPhase.REVIEW,
            assigned_agent="critic",
            priority=50
        )
        workflow.add_task(
            "Verify implementation matches specification",
            "Verifying spec compliance",
            phase=WorkflowPhase.REVIEW,
            assigned_agent="critic",
            priority=49
        )
        workflow.add_task(
            "Synthesize findings and recommendations",
            "Synthesizing findings",
            phase=WorkflowPhase.REVIEW,
            assigned_agent="synthesis",
            priority=48
        )

        # =====================================================================
        # Phase 7: DELIVER - Final synthesis and delivery
        # =====================================================================
        workflow.add_task(
            "Generate final implementation summary",
            "Generating summary",
            phase=WorkflowPhase.DELIVER,
            assigned_agent="summarizer",
            priority=40
        )
        workflow.add_task(
            "Document any follow-up tasks or known limitations",
            "Documenting follow-ups",
            phase=WorkflowPhase.DELIVER,
            assigned_agent="summarizer",
            priority=39
        )

        return workflow

    def _save_workflow(self, workflow: Workflow):
        """Persist workflow to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO workflows
                (id, name, description, status, created_at, completed_at, total_cost, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                workflow.id,
                workflow.name,
                workflow.description,
                workflow.current_phase.name,
                workflow.created_at.isoformat(),
                workflow.completed_at.isoformat() if workflow.completed_at else None,
                sum(t.cost for t in workflow.tasks),
                json.dumps(workflow.to_todo_list())
            ))
            conn.commit()

    def record_event(
        self,
        workflow_id: str,
        event_type: str,
        phase: str,
        task_id: Optional[str] = None,
        agent: Optional[str] = None,
        tokens_in: int = 0,
        tokens_out: int = 0,
        data: Optional[Dict] = None
    ):
        """Record a workflow event."""
        cost = self.circuit_breaker.record_usage(
            tokens_in, tokens_out,
            AGENT_REGISTRY.get(agent, {}).get("tier", AgentTier.SONNET).value if agent else "sonnet"
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO workflow_events
                (workflow_id, event_type, phase, task_id, agent, tokens_in, tokens_out, cost, timestamp, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                workflow_id,
                event_type,
                phase,
                task_id,
                agent,
                tokens_in,
                tokens_out,
                cost,
                datetime.now().isoformat(),
                json.dumps(data) if data else None
            ))
            conn.commit()

    def get_agent_for_task(self, task: Task) -> Dict[str, Any]:
        """
        Get the appropriate agent for a task.

        Implements Subagent Orchestration pattern for TDD workflow:
        - Match task type to agent role
        - Select appropriate tier for cost efficiency
        """
        if task.assigned_agent and task.assigned_agent in AGENT_REGISTRY:
            agent_info = AGENT_REGISTRY[task.assigned_agent]
            return {
                "name": task.assigned_agent,
                "model": agent_info["tier"].value,
                "role": agent_info["role"]
            }

        # Default mapping based on TDD phase
        phase_defaults = {
            WorkflowPhase.SPEC: ("planner", AgentTier.OPUS),
            WorkflowPhase.TEST_DESIGN: ("test-writer", AgentTier.SONNET),  # Upgraded for design
            WorkflowPhase.TEST_IMPL: ("test-writer", AgentTier.HAIKU),
            WorkflowPhase.IMPLEMENT: ("implementer", AgentTier.SONNET),
            WorkflowPhase.VALIDATE: ("validator", AgentTier.HAIKU),
            WorkflowPhase.REVIEW: ("critic", AgentTier.OPUS),
            WorkflowPhase.DELIVER: ("summarizer", AgentTier.HAIKU),
        }

        agent_name, tier = phase_defaults.get(task.phase, ("researcher", AgentTier.SONNET))
        return {
            "name": agent_name,
            "model": tier.value,
            "role": AGENT_REGISTRY.get(agent_name, {}).get("role", "general")
        }

    def generate_claude_md_governance(self, workflow: Workflow) -> str:
        """
        Generate CLAUDE.md governance content for TDD workflow.

        Implements Constitutional Constraints with TDD philosophy.
        """
        return f"""# TDD Workflow Governance: {workflow.name}

## Current Phase: {workflow.current_phase.name}

## TDD PHILOSOPHY - CORE RULES

These rules are NON-NEGOTIABLE:

1. **Tests define correctness** - Code must pass ALL tests
2. **Tests are IMMUTABLE** - After TEST_IMPL phase, tests CANNOT be modified
3. **NO TODOs** - Production code must have zero TODO comments
4. **NO mocks in production** - Mocks are only allowed in test files
5. **Auto-iterate** - Implementation continues until ALL tests pass

## TDD Workflow Phases

```
SPEC → TEST_DESIGN → TEST_IMPL → IMPLEMENT → VALIDATE → REVIEW → DELIVER
                          ↓
                    TESTS LOCKED
                    (immutable)
```

## Phase-Specific Constraints

### SPEC Phase (Current: {'✓' if workflow.current_phase == WorkflowPhase.SPEC else '○'})
ALWAYS define what the feature does before how
ALWAYS create a detailed product specification
ALWAYS define success criteria and acceptance requirements
ALWAYS get approval before proceeding to test design

### TEST_DESIGN Phase (Current: {'✓' if workflow.current_phase == WorkflowPhase.TEST_DESIGN else '○'})
ALWAYS design tests that guarantee requirements from spec
ALWAYS include unit tests, integration tests, and edge cases
ALWAYS design tests BEFORE thinking about implementation
ALWAYS get approval before writing tests

### TEST_IMPL Phase (Current: {'✓' if workflow.current_phase == WorkflowPhase.TEST_IMPL else '○'})
ALWAYS write tests exactly as designed
ALWAYS verify tests FAIL before implementation (no code yet)
ALWAYS get approval to LOCK tests before implementation
⚠️ AFTER APPROVAL: Tests become IMMUTABLE

### IMPLEMENT Phase (Current: {'✓' if workflow.current_phase == WorkflowPhase.IMPLEMENT else '○'})
ALWAYS write minimum code to pass tests
ALWAYS iterate until ALL tests pass
NEVER modify tests - they are LOCKED
NEVER add TODO comments
NEVER add mocks to production code
ALWAYS match existing code patterns

### VALIDATE Phase (Current: {'✓' if workflow.current_phase == WorkflowPhase.VALIDATE else '○'})
ALWAYS run full test suite (must be 100% passing)
ALWAYS run static analysis checks
ALWAYS verify NO TODOs in production code
ALWAYS verify NO mocks in production code
ALWAYS generate behavioral diff report

### REVIEW Phase (Current: {'✓' if workflow.current_phase == WorkflowPhase.REVIEW else '○'})
ALWAYS verify implementation matches specification
ALWAYS check for missed requirements
ALWAYS synthesize findings and recommendations

### DELIVER Phase (Current: {'✓' if workflow.current_phase == WorkflowPhase.DELIVER else '○'})
ALWAYS generate final summary
ALWAYS document any known limitations

## Budget Constraints

Current Budget: ${workflow.circuit_breaker.budget.limit:.2f}
Spent: ${workflow.circuit_breaker.budget.spent:.4f}
Remaining: ${workflow.circuit_breaker.budget.remaining:.4f}

ALWAYS check budget before spawning subagents
ALWAYS prefer Haiku for routine tasks to conserve budget
ALWAYS use Sonnet for test design (critical thinking required)
ALWAYS escalate to Opus only for strategic decisions

## Checkpoint Protocol

{chr(10).join(f"- {cp.name} ({cp.phase.name}): {'⚠️ REQUIRES APPROVAL' if cp.requires_approval else 'Auto-proceed if: ' + ', '.join(cp.auto_proceed_conditions)}" for cp in workflow.checkpoints)}

## Task List by Phase

{chr(10).join(f"### {phase.name}" + chr(10) + chr(10).join(f"- [{t.status.value}] {t.content} → {t.assigned_agent or 'unassigned'}" for t in workflow.tasks if t.phase == phase) for phase in WorkflowPhase)}
"""

    def generate_orchestrator_prompt(self, workflow: Workflow) -> str:
        """Generate a prompt for the orchestrator to execute the TDD workflow."""
        return f"""# TDD Orchestrator Workflow Execution

You are executing TDD workflow: **{workflow.name}**

## TDD PHILOSOPHY - CRITICAL RULES

**These rules are NON-NEGOTIABLE:**

1. **Tests define correctness** - Code must pass ALL tests
2. **Tests are IMMUTABLE** - After TEST_IMPL, tests CANNOT be changed
3. **NO TODOs** - Production code must have zero TODO comments
4. **NO mocks in production** - Mocks only in test files
5. **Auto-iterate** - Keep implementing until ALL tests pass

## Workflow Status
{json.dumps(workflow.get_status(), indent=2)}

## Current Phase: {workflow.current_phase.name}

## TDD Workflow Phases
```
SPEC → TEST_DESIGN → TEST_IMPL → IMPLEMENT → VALIDATE → REVIEW → DELIVER
                          ↓
                    TESTS LOCKED
```

## Tasks for This Phase
{json.dumps([t.to_dict() for t in workflow.get_tasks_for_phase(workflow.current_phase)], indent=2)}

## Execution Instructions

1. **Check Budget First**
   Current budget status: {json.dumps(workflow.circuit_breaker.get_status(), indent=2)}

2. **Phase-Specific Execution**

   **SPEC Phase:**
   - Create detailed feature specification
   - Define what the feature does (not how)
   - Define success criteria
   - Get approval before TEST_DESIGN

   **TEST_DESIGN Phase:**
   - Design unit tests from specification
   - Design integration tests
   - Design edge case tests
   - Get approval before TEST_IMPL

   **TEST_IMPL Phase:**
   - Write tests exactly as designed
   - Verify all tests FAIL (no implementation yet)
   - Get approval to LOCK TESTS
   - ⚠️ AFTER APPROVAL: Tests are IMMUTABLE

   **IMPLEMENT Phase:**
   - Write minimum code to pass first test
   - Iterate until ALL tests pass
   - CANNOT modify tests
   - NO TODOs allowed
   - NO mocks in production code

   **VALIDATE Phase:**
   - Run full test suite (100% must pass)
   - Run static analysis
   - Check for TODOs (must be zero)
   - Check for mocks in production (must be zero)

3. **Checkpoint Protocol**
   At phase completion, check for approval requirements:
   {json.dumps([{"name": cp.name, "requires_approval": cp.requires_approval} for cp in workflow.checkpoints if cp.phase == workflow.current_phase], indent=2)}

4. **Phase Transition**
   After completing all tasks in current phase:
   - Run validation if applicable
   - Request approval if checkpoint requires it
   - Advance to next phase

## Agent Delegation Guide

| Phase | Agent | Model | Role |
|-------|-------|-------|------|
| SPEC | planner | opus | Feature specification |
| TEST_DESIGN | test-writer | sonnet | Test case design |
| TEST_IMPL | test-writer | haiku | Test implementation |
| IMPLEMENT | implementer | sonnet | Code implementation |
| VALIDATE | validator | haiku | Validation checks |
| REVIEW | critic | opus | Quality review |
| DELIVER | summarizer | haiku | Final summary |

## Output Format

After executing each task:
```
TASK COMPLETED: [task_id]
Agent: [agent_name]
Tokens: [in]/[out]
Cost: $[amount]
Result: [summary]
```

At phase completion:
```
PHASE COMPLETED: [phase_name]
Tasks: [completed]/[total]
Phase Cost: $[amount]
Next Phase: [phase_name]
Checkpoint: [approval_status]
Tests Status: [passing/failing count] (if applicable)
```

## CRITICAL REMINDERS

- In TEST_IMPL: Verify tests fail BEFORE approving lock
- In IMPLEMENT: NEVER modify tests, iterate until ALL pass
- In VALIDATE: Check for TODOs and mocks (must be zero)
"""


# ============================================================================
# GOVERNANCE TEMPLATES
# ============================================================================

def generate_hook_configuration() -> Dict[str, Any]:
    """
    Generate Claude Code hook configuration for workflow integration.

    These hooks enforce governance by:
    - Running validation on file changes
    - Tracking token usage
    - Enforcing budget limits
    """
    return {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Edit|Write",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "python3 ~/.claude/dashboard/hooks/send_event.py --event-type PreToolUse --agent-name ${AGENT_NAME:-claude}"
                        }
                    ]
                }
            ],
            "PostToolUse": [
                {
                    "matcher": "Edit|Write",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "python3 ~/.claude/dashboard/hooks/send_event.py --event-type PostToolUse --agent-name ${AGENT_NAME:-claude}"
                        },
                        {
                            "type": "command",
                            "command": "if [[ \"$CLAUDE_FILE_PATHS\" =~ \\.(py)$ ]]; then python3 -m py_compile \"$CLAUDE_FILE_PATHS\" 2>&1 || echo 'Syntax error detected'; fi"
                        },
                        {
                            "type": "command",
                            "command": "if [[ \"$CLAUDE_FILE_PATHS\" =~ \\.(ts|tsx)$ ]]; then npx tsc --noEmit --skipLibCheck \"$CLAUDE_FILE_PATHS\" 2>&1 || echo 'TypeScript error detected'; fi"
                        }
                    ]
                }
            ],
            "Stop": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": "python3 ~/.claude/dashboard/hooks/send_event.py --event-type Stop --agent-name ${AGENT_NAME:-claude}"
                        }
                    ]
                }
            ]
        }
    }


# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    """Command-line interface for workflow engine."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Workflow Engine - Multi-Agent Orchestration"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Create workflow
    create_parser = subparsers.add_parser("create", help="Create a new workflow")
    create_parser.add_argument("name", help="Workflow name")
    create_parser.add_argument("--description", "-d", default="", help="Description")
    create_parser.add_argument("--budget", "-b", type=float, default=1.0, help="Budget limit")

    # Create from task
    task_parser = subparsers.add_parser("from-task", help="Create workflow from task description")
    task_parser.add_argument("task", help="Task description")
    task_parser.add_argument("--budget", "-b", type=float, default=1.0, help="Budget limit")

    # Status
    status_parser = subparsers.add_parser("status", help="Show workflow status")
    status_parser.add_argument("workflow_id", help="Workflow ID")

    # Generate governance
    gov_parser = subparsers.add_parser("governance", help="Generate governance files")
    gov_parser.add_argument("workflow_id", help="Workflow ID")
    gov_parser.add_argument("--output", "-o", default="CLAUDE.md", help="Output file")

    # Budget status
    subparsers.add_parser("budget", help="Show budget status")

    args = parser.parse_args()

    engine = WorkflowEngine()

    if args.command == "create":
        workflow = engine.create_workflow(args.name, args.description, args.budget)
        print(f"Created workflow: {workflow.id}")
        print(f"Name: {workflow.name}")
        print(f"Budget: ${args.budget:.2f}")

    elif args.command == "from-task":
        workflow = engine.create_workflow_from_task(args.task)
        print(f"Created workflow: {workflow.id}")
        print(f"Tasks created: {len(workflow.tasks)}")
        print("\nTask breakdown:")
        for task in workflow.tasks:
            print(f"  [{task.phase.name}] {task.content}")

    elif args.command == "status":
        if args.workflow_id in engine.workflows:
            workflow = engine.workflows[args.workflow_id]
            print(json.dumps(workflow.get_status(), indent=2))
        else:
            print(f"Workflow not found: {args.workflow_id}")

    elif args.command == "governance":
        if args.workflow_id in engine.workflows:
            workflow = engine.workflows[args.workflow_id]
            content = engine.generate_claude_md_governance(workflow)
            Path(args.output).write_text(content)
            print(f"Governance written to {args.output}")
        else:
            print(f"Workflow not found: {args.workflow_id}")

    elif args.command == "budget":
        print(json.dumps(engine.circuit_breaker.get_status(), indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
