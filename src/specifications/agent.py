"""
Specification Enforced Agent.

Provides agent wrapper that enforces formal specifications.

Version: 2.6.0
"""

import asyncio
import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Protocol, runtime_checkable

from .ast import AgentSpecification
from .compiler import CompiledSpecification, SpecificationCompiler
from .validators import SpecificationViolation, ValidationResult

logger = logging.getLogger(__name__)


@runtime_checkable
class AgentProtocol(Protocol):
    """Protocol for agents that can be wrapped."""

    async def execute(self, task: str) -> Dict[str, Any]:
        """Execute a task."""
        ...


@dataclass
class ExecutionResult:
    """
    Result of executing a specification-enforced agent.

    Attributes:
        output: The agent output
        validation_results: Results of constraint validation
        execution_time_ms: Execution time in milliseconds
        limits_enforced: Limits that were enforced
        spec_name: Name of the specification used
    """
    output: Dict[str, Any]
    validation_results: List[ValidationResult] = field(default_factory=list)
    execution_time_ms: int = 0
    limits_enforced: Dict[str, int] = field(default_factory=dict)
    spec_name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "output": self.output,
            "validation_results": [r.to_dict() for r in self.validation_results],
            "execution_time_ms": self.execution_time_ms,
            "limits_enforced": self.limits_enforced,
            "spec_name": self.spec_name,
            "valid": all(r.valid for r in self.validation_results),
        }


class LimitEnforcer:
    """
    Enforces runtime limits during agent execution.

    Tracks resource usage and enforces limits.
    """

    def __init__(self, limits: Dict[str, int]):
        """
        Initialize with limits.

        Args:
            limits: Dictionary of limit_name -> max_value
        """
        self.limits = limits
        self.counters: Dict[str, int] = {k: 0 for k in limits}
        self.start_time: Optional[float] = None

    def check_limit(self, name: str, increment: int = 1) -> bool:
        """
        Check and increment a limit counter.

        Args:
            name: Name of the limit
            increment: Amount to increment

        Returns:
            True if within limit, False if exceeded

        Raises:
            LimitExceededError: If limit is exceeded
        """
        if name not in self.limits:
            return True

        self.counters[name] += increment
        if self.counters[name] > self.limits[name]:
            raise LimitExceededError(name, self.limits[name], self.counters[name])

        return True

    def check_timeout(self) -> bool:
        """
        Check if timeout has been exceeded.

        Returns:
            True if within timeout

        Raises:
            LimitExceededError: If timeout exceeded
        """
        if "timeout_seconds" not in self.limits:
            return True

        if self.start_time is None:
            self.start_time = time.time()
            return True

        elapsed = time.time() - self.start_time
        if elapsed > self.limits["timeout_seconds"]:
            raise LimitExceededError(
                "timeout_seconds",
                self.limits["timeout_seconds"],
                int(elapsed)
            )

        return True

    def get_usage(self) -> Dict[str, Dict[str, int]]:
        """Get current usage for all limits."""
        return {
            name: {"current": self.counters.get(name, 0), "limit": limit}
            for name, limit in self.limits.items()
        }

    def reset(self) -> None:
        """Reset all counters."""
        self.counters = {k: 0 for k in self.limits}
        self.start_time = None


class LimitExceededError(Exception):
    """Error raised when a limit is exceeded."""

    def __init__(self, limit_name: str, limit_value: int, actual_value: int):
        self.limit_name = limit_name
        self.limit_value = limit_value
        self.actual_value = actual_value
        super().__init__(
            f"Limit '{limit_name}' exceeded: {actual_value} > {limit_value}"
        )


class SpecificationEnforcedAgent:
    """
    Agent wrapper that enforces formal specifications.

    Wraps any agent to:
    1. Add behavioral guidelines to prompts
    2. Enforce runtime limits
    3. Validate output against constraints
    4. Track execution metrics

    Example:
        from src.specifications import SpecificationCompiler, SpecificationEnforcedAgent

        compiler = SpecificationCompiler()
        spec = compiler.compile(spec_text)

        enforced = SpecificationEnforcedAgent(base_agent, spec)
        result = await enforced.execute("Research AI safety")

        if result.valid:
            print(result.output)
        else:
            print("Violations:", result.validation_results)
    """

    def __init__(
        self,
        agent: Any,
        spec: CompiledSpecification,
        strict: bool = True,
    ):
        """
        Initialize the enforced agent.

        Args:
            agent: The base agent to wrap
            spec: Compiled specification to enforce
            strict: If True, raise on violations; if False, return with errors
        """
        self.agent = agent
        self.spec = spec
        self.strict = strict
        self.limit_enforcer = LimitEnforcer(spec.limits)

        # Execution tracking
        self.execution_count = 0
        self.violation_count = 0

    async def execute(self, task: str) -> ExecutionResult:
        """
        Execute task with specification enforcement.

        Args:
            task: The task to execute

        Returns:
            ExecutionResult with output and validation info

        Raises:
            SpecificationViolation: If strict mode and constraints violated
            LimitExceededError: If runtime limits exceeded
        """
        start_time = time.time()
        self.execution_count += 1
        self.limit_enforcer.reset()

        # Build augmented prompt with behavior guidelines
        augmented_prompt = self._build_prompt(task)

        # Execute with limit enforcement
        try:
            with self._enforce_limits():
                output = await self._execute_agent(augmented_prompt)
        except LimitExceededError as e:
            logger.warning(f"Limit exceeded during execution: {e}")
            raise

        elapsed_ms = int((time.time() - start_time) * 1000)

        # Validate output
        try:
            validation_results = self.spec.validator.validate(output)
        except SpecificationViolation as e:
            self.violation_count += 1
            if self.strict:
                raise
            # In non-strict mode, return with violation info
            validation_results = e.violations

        return ExecutionResult(
            output=output,
            validation_results=validation_results,
            execution_time_ms=elapsed_ms,
            limits_enforced=self.spec.limits,
            spec_name=self.spec.agent_name,
        )

    def _build_prompt(self, task: str) -> str:
        """Build prompt with behavior guidelines."""
        parts = []

        # Add behavior guidelines
        if self.spec.behavior_prompt:
            parts.append(self.spec.behavior_prompt)

        # Add tool restrictions if any
        if self.spec.tools:
            parts.append(f"## Available Tools")
            parts.append(f"You may only use these tools: {', '.join(self.spec.tools)}")
            parts.append("")

        # Add the task
        parts.append("## Task")
        parts.append(task)

        return "\n".join(parts)

    @contextmanager
    def _enforce_limits(self):
        """Context manager for limit enforcement."""
        self.limit_enforcer.reset()
        try:
            yield self.limit_enforcer
        finally:
            pass

    async def _execute_agent(self, prompt: str) -> Dict[str, Any]:
        """Execute the wrapped agent."""
        # Check timeout before execution
        self.limit_enforcer.check_timeout()

        # Try different agent interfaces
        if hasattr(self.agent, 'execute'):
            result = await self.agent.execute(prompt)
        elif hasattr(self.agent, 'run'):
            result = await self.agent.run(prompt)
        elif hasattr(self.agent, '__call__'):
            result = await self.agent(prompt)
        else:
            raise TypeError(f"Agent does not have execute/run method: {type(self.agent)}")

        # Ensure result is a dict
        if not isinstance(result, dict):
            result = {"output": result}

        return result

    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        return {
            "spec_name": self.spec.agent_name,
            "execution_count": self.execution_count,
            "violation_count": self.violation_count,
            "violation_rate": (
                self.violation_count / self.execution_count
                if self.execution_count > 0 else 0
            ),
            "limits": self.spec.limits,
        }


class MockAgent:
    """Mock agent for testing."""

    def __init__(self, response: Optional[Dict[str, Any]] = None):
        """Initialize with optional response."""
        self.response = response or {"output": "Mock response", "confidence": 0.9}
        self.calls: List[str] = []

    async def execute(self, task: str) -> Dict[str, Any]:
        """Execute mock task."""
        self.calls.append(task)
        return self.response.copy()


def create_enforced_agent(
    agent: Any,
    spec_text: str,
    strict: bool = True,
) -> SpecificationEnforcedAgent:
    """
    Convenience function to create an enforced agent.

    Args:
        agent: The base agent
        spec_text: Specification text
        strict: Whether to raise on violations

    Returns:
        SpecificationEnforcedAgent
    """
    compiler = SpecificationCompiler()
    spec = compiler.compile(spec_text)
    return SpecificationEnforcedAgent(agent, spec, strict=strict)
