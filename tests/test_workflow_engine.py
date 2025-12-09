#!/usr/bin/env python3
"""
Unit tests for the Workflow Engine.

Tests cover:
- Cost Circuit Breaker
- Workflow Creation and Management
- Task Status Transitions
- Validation Layer Stack
- Governance Generation
"""

import sys
import os
import pytest
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from workflow_engine import (
    WorkflowEngine,
    Workflow,
    Task,
    CostCircuitBreaker,
    ValidationLayerStack,
    WorkflowPhase,
    TaskStatus,
    AgentTier,
    MODEL_PRICING,
    AGENT_REGISTRY,
)


# ============================================================================
# COST CIRCUIT BREAKER TESTS
# ============================================================================

class TestCostCircuitBreaker:
    """Tests for the CostCircuitBreaker class."""

    def test_initialization(self):
        """Test circuit breaker initializes with correct defaults."""
        cb = CostCircuitBreaker(budget_limit=1.0)
        assert cb.budget.limit == 1.0
        assert cb.budget.spent == 0.0
        assert cb.budget.remaining == 1.0
        assert cb.budget.circuit_broken is False

    def test_token_estimation_empty_string(self):
        """Test token estimation handles empty strings."""
        cb = CostCircuitBreaker(budget_limit=1.0)
        assert cb.estimate_tokens("") == 0
        assert cb.estimate_tokens(None) == 0

    def test_token_estimation_basic(self):
        """Test token estimation for basic text."""
        cb = CostCircuitBreaker(budget_limit=1.0)
        # Using fallback estimation (4 chars per token)
        text = "Hello world"  # 11 chars
        tokens = cb.estimate_tokens(text)
        assert tokens > 0
        # Should be approximately 11/4 = 2-3 tokens (or more with tiktoken)
        assert tokens >= 2

    def test_cost_estimation_sonnet(self):
        """Test cost estimation for Sonnet model."""
        cb = CostCircuitBreaker(budget_limit=1.0)
        # Sonnet: $3/M input, $15/M output
        cost = cb.estimate_cost(1_000_000, 0, "sonnet")
        assert cost == pytest.approx(3.0, rel=0.01)

        cost = cb.estimate_cost(0, 1_000_000, "sonnet")
        assert cost == pytest.approx(15.0, rel=0.01)

    def test_cost_estimation_opus(self):
        """Test cost estimation for Opus model."""
        cb = CostCircuitBreaker(budget_limit=1.0)
        # Opus: $15/M input, $75/M output
        cost = cb.estimate_cost(1_000_000, 0, "opus")
        assert cost == pytest.approx(15.0, rel=0.01)

    def test_cost_estimation_haiku(self):
        """Test cost estimation for Haiku model."""
        cb = CostCircuitBreaker(budget_limit=1.0)
        # Haiku: $0.25/M input, $1.25/M output
        cost = cb.estimate_cost(1_000_000, 0, "haiku")
        assert cost == pytest.approx(0.25, rel=0.01)

    def test_budget_check_within_limit(self):
        """Test budget check when within limit."""
        cb = CostCircuitBreaker(budget_limit=1.0)
        allowed, msg = cb.check_budget(0.5)
        assert allowed is True
        assert "OK" in msg or "WARNING" in msg

    def test_budget_check_exceeds_limit(self):
        """Test budget check when exceeding limit."""
        cb = CostCircuitBreaker(budget_limit=0.10)
        cb.record_usage(100000, 50000, "sonnet")  # Use up budget
        allowed, msg = cb.check_budget(0.50)
        assert allowed is False
        assert "EXCEEDED" in msg or "CIRCUIT" in msg

    def test_circuit_breaker_trips(self):
        """Test that circuit breaker trips on budget exhaustion."""
        cb = CostCircuitBreaker(budget_limit=0.01)
        cb.record_usage(100000, 50000, "sonnet")  # Exceed budget

        # Check should indicate circuit is broken
        allowed, msg = cb.check_budget(0.01)
        assert cb.budget.circuit_broken is True

    def test_record_usage(self):
        """Test recording token usage."""
        cb = CostCircuitBreaker(budget_limit=1.0)
        cost = cb.record_usage(1000, 500, "sonnet")

        assert cost > 0
        assert cb.budget.spent == cost
        assert cb.budget.tokens_in == 1000
        assert cb.budget.tokens_out == 500

    def test_reset(self):
        """Test circuit breaker reset."""
        cb = CostCircuitBreaker(budget_limit=1.0)
        cb.record_usage(10000, 5000, "sonnet")
        cb.budget.circuit_broken = True

        cb.reset(new_limit=2.0)

        assert cb.budget.limit == 2.0
        assert cb.budget.spent == 0.0
        assert cb.budget.circuit_broken is False

    def test_get_status(self):
        """Test getting budget status."""
        cb = CostCircuitBreaker(budget_limit=1.0)
        cb.record_usage(1000, 500, "sonnet")

        status = cb.get_status()

        assert "limit" in status
        assert "spent" in status
        assert "remaining" in status
        assert "utilization" in status
        assert "tokens_in" in status
        assert "tokens_out" in status
        assert "circuit_broken" in status


# ============================================================================
# TASK TESTS
# ============================================================================

class TestTask:
    """Tests for the Task dataclass."""

    def test_task_creation(self):
        """Test basic task creation."""
        task = Task(
            id="test-001",
            content="Test task",
            active_form="Testing task"
        )

        assert task.id == "test-001"
        assert task.content == "Test task"
        assert task.status == TaskStatus.PENDING
        assert task.phase == WorkflowPhase.PLAN

    def test_task_to_dict(self):
        """Test task serialization to dict."""
        task = Task(
            id="test-001",
            content="Test task",
            active_form="Testing task",
            assigned_agent="planner"
        )

        d = task.to_dict()

        assert d["id"] == "test-001"
        assert d["content"] == "Test task"
        assert d["activeForm"] == "Testing task"
        assert d["status"] == "pending"
        assert d["assigned_agent"] == "planner"

    def test_task_status_transitions(self):
        """Test task status transitions."""
        task = Task(
            id="test-001",
            content="Test task",
            active_form="Testing task"
        )

        assert task.status == TaskStatus.PENDING

        task.status = TaskStatus.IN_PROGRESS
        assert task.status == TaskStatus.IN_PROGRESS

        task.status = TaskStatus.COMPLETED
        assert task.status == TaskStatus.COMPLETED


# ============================================================================
# WORKFLOW TESTS
# ============================================================================

class TestWorkflow:
    """Tests for the Workflow class."""

    def test_workflow_creation(self):
        """Test basic workflow creation."""
        cb = CostCircuitBreaker(budget_limit=1.0)
        workflow = Workflow(
            name="Test Workflow",
            description="A test workflow",
            circuit_breaker=cb
        )

        assert workflow.name == "Test Workflow"
        assert workflow.description == "A test workflow"
        assert workflow.current_phase == WorkflowPhase.PLAN
        assert len(workflow.tasks) == 0

    def test_add_task(self):
        """Test adding tasks to workflow."""
        cb = CostCircuitBreaker(budget_limit=1.0)
        workflow = Workflow(
            name="Test Workflow",
            description="Test",
            circuit_breaker=cb
        )

        task = workflow.add_task(
            content="First task",
            active_form="Working on first task",
            phase=WorkflowPhase.PLAN,
            assigned_agent="planner"
        )

        assert len(workflow.tasks) == 1
        assert task.content == "First task"
        assert task.assigned_agent == "planner"
        assert task.id.startswith(workflow.id)

    def test_add_checkpoint(self):
        """Test adding checkpoints to workflow."""
        cb = CostCircuitBreaker(budget_limit=1.0)
        workflow = Workflow(
            name="Test Workflow",
            description="Test",
            circuit_breaker=cb
        )

        cp = workflow.add_checkpoint(
            name="Plan Review",
            phase=WorkflowPhase.PLAN,
            requires_approval=True
        )

        assert len(workflow.checkpoints) == 1
        assert cp.name == "Plan Review"
        assert cp.requires_approval is True

    def test_get_tasks_for_phase(self):
        """Test getting tasks by phase."""
        cb = CostCircuitBreaker(budget_limit=1.0)
        workflow = Workflow(
            name="Test Workflow",
            description="Test",
            circuit_breaker=cb
        )

        workflow.add_task("Plan task", "Planning", phase=WorkflowPhase.PLAN)
        workflow.add_task("Implement task", "Implementing", phase=WorkflowPhase.IMPLEMENT)
        workflow.add_task("Another plan task", "Planning more", phase=WorkflowPhase.PLAN)

        plan_tasks = workflow.get_tasks_for_phase(WorkflowPhase.PLAN)
        impl_tasks = workflow.get_tasks_for_phase(WorkflowPhase.IMPLEMENT)

        assert len(plan_tasks) == 2
        assert len(impl_tasks) == 1

    def test_get_next_task(self):
        """Test getting next task respects dependencies."""
        cb = CostCircuitBreaker(budget_limit=1.0)
        workflow = Workflow(
            name="Test Workflow",
            description="Test",
            circuit_breaker=cb
        )

        task1 = workflow.add_task("First", "First", priority=1)
        task2 = workflow.add_task("Second", "Second", priority=2, dependencies=[task1.id])

        # Should get task1 first (no dependencies)
        next_task = workflow.get_next_task()
        assert next_task.id == task1.id

        # Complete task1
        task1.status = TaskStatus.COMPLETED

        # Now should get task2
        next_task = workflow.get_next_task()
        assert next_task.id == task2.id

    def test_advance_phase(self):
        """Test phase advancement."""
        cb = CostCircuitBreaker(budget_limit=1.0)
        workflow = Workflow(
            name="Test Workflow",
            description="Test",
            circuit_breaker=cb
        )

        assert workflow.current_phase == WorkflowPhase.PLAN

        workflow.advance_phase()
        assert workflow.current_phase == WorkflowPhase.TEST

        workflow.advance_phase()
        assert workflow.current_phase == WorkflowPhase.IMPLEMENT

    def test_to_todo_list(self):
        """Test conversion to TodoWrite format."""
        cb = CostCircuitBreaker(budget_limit=1.0)
        workflow = Workflow(
            name="Test Workflow",
            description="Test",
            circuit_breaker=cb
        )

        workflow.add_task("Task 1", "Task 1")
        workflow.add_task("Task 2", "Task 2")

        todo_list = workflow.to_todo_list()

        assert len(todo_list) == 2
        assert all("content" in t for t in todo_list)
        assert all("status" in t for t in todo_list)

    def test_get_status(self):
        """Test getting workflow status."""
        cb = CostCircuitBreaker(budget_limit=1.0)
        workflow = Workflow(
            name="Test Workflow",
            description="Test",
            circuit_breaker=cb
        )

        workflow.add_task("Task 1", "Task 1")
        workflow.add_task("Task 2", "Task 2")
        workflow.tasks[0].status = TaskStatus.COMPLETED

        status = workflow.get_status()

        assert status["total_tasks"] == 2
        assert status["completed"] == 1
        assert status["pending"] == 1


# ============================================================================
# WORKFLOW ENGINE TESTS
# ============================================================================

class TestWorkflowEngine:
    """Tests for the WorkflowEngine class."""

    def test_engine_initialization(self):
        """Test engine initialization."""
        engine = WorkflowEngine(budget_limit=1.0)

        assert engine.circuit_breaker.budget.limit == 1.0
        assert len(engine.workflows) == 0

    def test_create_workflow(self):
        """Test creating a workflow through the engine."""
        engine = WorkflowEngine(budget_limit=1.0)
        workflow = engine.create_workflow(
            name="Test Workflow",
            description="Test description"
        )

        assert workflow.name == "Test Workflow"
        assert workflow.id in engine.workflows
        # Should have default checkpoints
        assert len(workflow.checkpoints) == 4

    def test_create_workflow_from_task(self):
        """Test creating workflow from task description."""
        engine = WorkflowEngine(budget_limit=1.0)
        workflow = engine.create_workflow_from_task(
            "Implement user authentication"
        )

        assert len(workflow.tasks) == 11

        # Check phase distribution
        plan_tasks = workflow.get_tasks_for_phase(WorkflowPhase.PLAN)
        assert len(plan_tasks) == 3

        test_tasks = workflow.get_tasks_for_phase(WorkflowPhase.TEST)
        assert len(test_tasks) == 2

    def test_get_agent_for_task(self):
        """Test agent assignment for tasks."""
        engine = WorkflowEngine(budget_limit=1.0)

        task = Task(
            id="test-001",
            content="Test",
            active_form="Testing",
            phase=WorkflowPhase.PLAN,
            assigned_agent="planner"
        )

        agent = engine.get_agent_for_task(task)

        assert agent["name"] == "planner"
        assert agent["model"] == "opus"

    def test_generate_claude_md_governance(self):
        """Test CLAUDE.md governance generation."""
        engine = WorkflowEngine(budget_limit=1.0)
        workflow = engine.create_workflow_from_task("Test task")

        governance = engine.generate_claude_md_governance(workflow)

        assert "# Workflow Governance" in governance
        assert "ALWAYS" in governance  # Positive framing
        assert "Budget" in governance
        assert workflow.name in governance

    def test_generate_orchestrator_prompt(self):
        """Test orchestrator prompt generation."""
        engine = WorkflowEngine(budget_limit=1.0)
        workflow = engine.create_workflow_from_task("Test task")

        prompt = engine.generate_orchestrator_prompt(workflow)

        assert "Orchestrator Workflow Execution" in prompt
        assert workflow.name in prompt
        assert "PLAN" in prompt


# ============================================================================
# VALIDATION LAYER STACK TESTS
# ============================================================================

class TestValidationLayerStack:
    """Tests for the ValidationLayerStack class."""

    def test_initialization(self):
        """Test validation stack initialization."""
        validator = ValidationLayerStack(project_root=".")

        assert validator.project_root == Path(".")
        assert len(validator.results) == 0

    def test_layer_4_behavioral_diff(self):
        """Test behavioral diff layer."""
        validator = ValidationLayerStack(project_root=".")

        result = validator.run_layer_4_behavioral_diff()

        assert result.layer == "behavioral_diff"
        assert result.passed is True  # Informational layer
        assert "changed_files" in result.details or "error" in result.details

    def test_get_summary(self):
        """Test validation summary."""
        validator = ValidationLayerStack(project_root=".")

        # Run at least one layer
        validator.run_layer_4_behavioral_diff()

        summary = validator.get_summary()

        assert "total_layers" in summary
        assert "passed" in summary
        assert "failed" in summary
        assert "results" in summary


# ============================================================================
# AGENT REGISTRY TESTS
# ============================================================================

class TestAgentRegistry:
    """Tests for the agent registry configuration."""

    def test_all_agents_have_tiers(self):
        """Test all agents have tier assignments."""
        for agent_name, config in AGENT_REGISTRY.items():
            assert "tier" in config, f"Agent {agent_name} missing tier"
            assert isinstance(config["tier"], AgentTier)

    def test_all_agents_have_roles(self):
        """Test all agents have role assignments."""
        for agent_name, config in AGENT_REGISTRY.items():
            assert "role" in config, f"Agent {agent_name} missing role"

    def test_model_pricing_complete(self):
        """Test all model tiers have pricing."""
        for tier in ["opus", "sonnet", "haiku"]:
            assert tier in MODEL_PRICING
            assert "input" in MODEL_PRICING[tier]
            assert "output" in MODEL_PRICING[tier]


# ============================================================================
# WORKFLOW PHASE TESTS
# ============================================================================

class TestWorkflowPhase:
    """Tests for workflow phase enum."""

    def test_phase_order(self):
        """Test phases are in correct order."""
        phases = list(WorkflowPhase)

        assert phases[0] == WorkflowPhase.PLAN
        assert phases[1] == WorkflowPhase.TEST
        assert phases[2] == WorkflowPhase.IMPLEMENT
        assert phases[3] == WorkflowPhase.VALIDATE
        assert phases[4] == WorkflowPhase.REVIEW
        assert phases[5] == WorkflowPhase.DELIVER

    def test_all_phases_exist(self):
        """Test all expected phases exist."""
        expected = ["PLAN", "TEST", "IMPLEMENT", "VALIDATE", "REVIEW", "DELIVER"]
        actual = [p.name for p in WorkflowPhase]

        assert actual == expected


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests for the workflow engine."""

    def test_full_workflow_lifecycle(self):
        """Test complete workflow lifecycle."""
        engine = WorkflowEngine(budget_limit=2.0)

        # Create workflow
        workflow = engine.create_workflow_from_task("Add login feature")

        # Get and complete tasks
        while task := workflow.get_next_task():
            task.status = TaskStatus.IN_PROGRESS
            task.tokens_used = 100
            task.cost = 0.001
            task.status = TaskStatus.COMPLETED

        # Check final status
        status = workflow.get_status()
        assert status["completed"] == 11
        assert status["pending"] == 0

    def test_budget_enforcement_in_workflow(self):
        """Test budget is enforced during workflow execution."""
        engine = WorkflowEngine(budget_limit=0.001)  # Very small budget

        # Record heavy usage
        engine.circuit_breaker.record_usage(100000, 50000, "opus")

        # Check budget is enforced
        allowed, msg = engine.circuit_breaker.check_budget(0.10)
        assert allowed is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
