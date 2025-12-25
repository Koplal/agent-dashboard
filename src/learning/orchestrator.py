"""
Learning Orchestrator.

Orchestrates agent execution with neurosymbolic learning.

Version: 2.6.0
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Protocol, runtime_checkable

from .extractor import RuleExtractor, ExtractionConfig
from .models import (
    ExecutionOutcome,
    ExtractedRule,
    LearningStats,
    RuleMatch,
)
from .store import RuleStore

logger = logging.getLogger(__name__)


@runtime_checkable
class ExecutableAgent(Protocol):
    """Protocol for agents that can be executed."""

    async def execute(self, task: str) -> Dict[str, Any]:
        """Execute a task."""
        ...


@dataclass
class LearningConfig:
    """Configuration for the learning orchestrator."""
    # Rule application
    max_rules_to_apply: int = 3
    min_rule_effectiveness: float = 0.5

    # Learning triggers
    learn_from_high_quality: bool = True
    min_quality_for_learning: float = 0.8
    learn_from_feedback: bool = True

    # Pruning
    auto_prune: bool = True
    prune_interval_hours: int = 24
    min_applications_for_pruning: int = 10
    min_effectiveness_threshold: float = 0.4

    # Persistence
    auto_save: bool = True


@dataclass
class ExecutionContext:
    """Context for a single execution."""
    task: str
    agent_id: str
    rules_applied: List[RuleMatch] = field(default_factory=list)
    start_time: float = 0.0
    augmented_task: str = ""


class LearningOrchestrator:
    """
    Orchestrator with neurosymbolic learning.

    Wraps agent execution to:
    1. Apply learned rules to enhance task context
    2. Track execution outcomes
    3. Extract new rules from successful executions
    4. Update rule effectiveness based on outcomes

    Example:
        orchestrator = LearningOrchestrator(
            agents={"researcher": researcher_agent},
            rule_store=RuleStore(),
            rule_extractor=RuleExtractor(client),
        )

        result = await orchestrator.execute_with_learning(
            task="Research AI safety",
            agent_id="researcher"
        )
    """

    RULE_CONTEXT_TEMPLATE = """
LEARNED PATTERNS (from past successful executions):
{rules}

Apply these patterns where relevant to improve your approach.

"""

    def __init__(
        self,
        agents: Dict[str, ExecutableAgent],
        rule_store: RuleStore,
        rule_extractor: Optional[RuleExtractor] = None,
        config: Optional[LearningConfig] = None,
    ):
        """
        Initialize the learning orchestrator.

        Args:
            agents: Dictionary of agent_id -> agent
            rule_store: Rule storage
            rule_extractor: Rule extraction component
            config: Learning configuration
        """
        self.agents = agents
        self.rules = rule_store
        self.extractor = rule_extractor
        self.config = config or LearningConfig()

        # Execution tracking
        self.execution_count = 0
        self.successful_executions = 0
        self.rules_extracted_count = 0
        self.last_prune_time: Optional[datetime] = None

        # Callbacks
        self._on_execution_complete: List[Callable[[ExecutionOutcome], None]] = []
        self._on_rules_extracted: List[Callable[[List[ExtractedRule]], None]] = []

    async def execute_with_learning(
        self,
        task: str,
        agent_id: str,
        feedback: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute task with rule application and learning.

        Args:
            task: The task to execute
            agent_id: ID of the agent to use
            feedback: Optional feedback for the task

        Returns:
            Execution result with learning metadata
        """
        if agent_id not in self.agents:
            raise ValueError(f"Unknown agent: {agent_id}")

        self.execution_count += 1

        # Create execution context
        context = ExecutionContext(
            task=task,
            agent_id=agent_id,
            start_time=time.time(),
        )

        # Retrieve and apply rules
        applicable_rules = self._get_applicable_rules(task)
        context.rules_applied = applicable_rules

        # Build augmented task
        context.augmented_task = self._build_augmented_task(task, applicable_rules)

        # Execute agent
        agent = self.agents[agent_id]
        try:
            result = await agent.execute(context.augmented_task)
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            result = {
                "success": False,
                "error": str(e),
                "output": None,
            }

        execution_time = time.time() - context.start_time

        # Create outcome
        outcome = self._create_outcome(context, result, execution_time, feedback)

        # Update rule effectiveness
        await self._update_rule_effectiveness(context.rules_applied, outcome)

        # Extract new rules if applicable
        if outcome.is_high_quality and self.config.learn_from_high_quality:
            await self._extract_and_store_rules(task, result, outcome)

        # Run callbacks
        for callback in self._on_execution_complete:
            try:
                callback(outcome)
            except Exception as e:
                logger.warning(f"Execution callback failed: {e}")

        # Auto-prune if needed
        if self.config.auto_prune:
            await self._maybe_prune()

        # Add learning metadata to result
        result["_learning"] = {
            "rules_applied": [m.rule.id for m in applicable_rules],
            "execution_time": execution_time,
            "outcome_quality": outcome.quality_score,
        }

        if outcome.success:
            self.successful_executions += 1

        return result

    def _get_applicable_rules(self, task: str) -> List[RuleMatch]:
        """Get rules applicable to the task."""
        matches = self.rules.search(task, limit=self.config.max_rules_to_apply * 2)

        # Filter by effectiveness threshold
        filtered = [
            m for m in matches
            if m.rule.effectiveness >= self.config.min_rule_effectiveness
        ]

        return filtered[:self.config.max_rules_to_apply]

    def _build_augmented_task(
        self,
        task: str,
        rules: List[RuleMatch],
    ) -> str:
        """Build task with rule context."""
        if not rules:
            return task

        rule_lines = []
        for match in rules:
            rule = match.rule
            rule_lines.append(
                f"- When {rule.condition}: {rule.recommendation} "
                f"(effectiveness: {rule.effectiveness:.0%})"
            )

        rule_context = self.RULE_CONTEXT_TEMPLATE.format(
            rules="\n".join(rule_lines)
        )

        return f"{rule_context}TASK:\n{task}"

    def _create_outcome(
        self,
        context: ExecutionContext,
        result: Dict[str, Any],
        execution_time: float,
        feedback: Optional[str],
    ) -> ExecutionOutcome:
        """Create execution outcome from result."""
        return ExecutionOutcome(
            task=context.task,
            approach=result.get("approach", result.get("methodology", "unknown")),
            success=result.get("success", True),
            quality_score=result.get("quality_score", result.get("confidence", 0.5)),
            execution_time=execution_time,
            artifacts=result.get("artifacts", []),
            feedback=feedback,
            agent_id=context.agent_id,
            rules_applied=[m.rule.id for m in context.rules_applied],
            timestamp=datetime.now(),
        )

    async def _update_rule_effectiveness(
        self,
        rules: List[RuleMatch],
        outcome: ExecutionOutcome,
    ) -> None:
        """Update effectiveness of applied rules."""
        for match in rules:
            self.rules.update_effectiveness(match.rule.id, outcome.success)

    async def _extract_and_store_rules(
        self,
        task: str,
        result: Dict[str, Any],
        outcome: ExecutionOutcome,
    ) -> None:
        """Extract and store new rules from successful execution."""
        if not self.extractor:
            return

        try:
            new_rules = await self.extractor.extract_rules(
                task=task,
                approach=outcome.approach,
                outcome=outcome,
            )

            for rule in new_rules:
                self.rules.add(rule)
                self.rules_extracted_count += 1
                logger.info(f"Extracted and stored new rule: {rule.id}")

            # Run callbacks
            if new_rules:
                for callback in self._on_rules_extracted:
                    try:
                        callback(new_rules)
                    except Exception as e:
                        logger.warning(f"Rules extracted callback failed: {e}")

        except Exception as e:
            logger.error(f"Rule extraction failed: {e}")

    async def _maybe_prune(self) -> None:
        """Prune rules if needed."""
        if self.last_prune_time:
            hours_since_prune = (datetime.now() - self.last_prune_time).total_seconds() / 3600
            if hours_since_prune < self.config.prune_interval_hours:
                return

        # Run pruning
        pruned = self.rules.prune_ineffective(
            min_applications=self.config.min_applications_for_pruning,
            min_effectiveness=self.config.min_effectiveness_threshold,
        )

        if pruned:
            logger.info(f"Pruned {len(pruned)} ineffective rules")

        self.last_prune_time = datetime.now()

    def on_execution_complete(self, callback: Callable[[ExecutionOutcome], None]) -> None:
        """Register callback for execution completion."""
        self._on_execution_complete.append(callback)

    def on_rules_extracted(self, callback: Callable[[List[ExtractedRule]], None]) -> None:
        """Register callback for rule extraction."""
        self._on_rules_extracted.append(callback)

    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics."""
        rule_stats = self.rules.get_stats()
        return {
            "execution_count": self.execution_count,
            "successful_executions": self.successful_executions,
            "success_rate": (
                self.successful_executions / self.execution_count
                if self.execution_count > 0 else 0
            ),
            "rules_extracted": self.rules_extracted_count,
            "rule_stats": rule_stats.to_dict(),
            "agent_count": len(self.agents),
            "last_prune": self.last_prune_time.isoformat() if self.last_prune_time else None,
        }

    def get_learning_report(self) -> Dict[str, Any]:
        """Generate a learning report."""
        stats = self.rules.get_stats()
        top_rules = self.rules.get_top_rules(5)

        return {
            "summary": {
                "total_rules": stats.total_rules,
                "active_rules": stats.active_rules,
                "average_effectiveness": f"{stats.average_effectiveness:.1%}",
                "total_applications": stats.total_applications,
            },
            "top_rules": [
                {
                    "condition": r.condition,
                    "recommendation": r.recommendation,
                    "effectiveness": f"{r.effectiveness:.1%}",
                    "applications": r.total_applications,
                }
                for r in top_rules
            ],
            "by_category": stats.rules_by_category,
            "recent_activity": {
                "extractions_this_week": stats.recent_extractions,
                "executions": self.execution_count,
            },
        }

    def register_agent(self, agent_id: str, agent: ExecutableAgent) -> None:
        """Register an agent."""
        self.agents[agent_id] = agent

    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent."""
        if agent_id in self.agents:
            del self.agents[agent_id]
            return True
        return False


class MockLearningOrchestrator:
    """Mock orchestrator for testing."""

    def __init__(self):
        """Initialize mock orchestrator."""
        self.executions: List[Dict[str, Any]] = []
        self.results: Dict[str, Dict[str, Any]] = {}

    def set_result(self, task: str, result: Dict[str, Any]) -> None:
        """Set result for a task."""
        self.results[task] = result

    async def execute_with_learning(
        self,
        task: str,
        agent_id: str,
        feedback: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Mock execution."""
        self.executions.append({
            "task": task,
            "agent_id": agent_id,
            "feedback": feedback,
        })

        return self.results.get(task, {
            "success": True,
            "output": "Mock result",
            "quality_score": 0.9,
        })
