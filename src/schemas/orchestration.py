"""
Orchestration Agent Output Schemas.

Pydantic models for validating orchestrator decisions including
agent selection, delegation, and workflow management.

Version: 2.6.0
"""

from datetime import datetime
from typing import List, Optional, Literal, Dict, Any

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

from .base import BaseAgentOutput, ConfidenceLevel, utc_now


class AgentSelection(BaseModel):
    """Selection of an agent for a task.

    Attributes:
        agent_type: Type of agent to use
        model_tier: Model tier (opus, sonnet, haiku)
        rationale: Why this agent was selected
        estimated_tokens: Expected token usage
        priority: Task priority for this agent
    """
    model_config = ConfigDict(extra="forbid")

    agent_type: str = Field(
        min_length=1,
        description="Type of agent to use (e.g., researcher, critic)"
    )
    model_tier: Literal["opus", "sonnet", "haiku"] = Field(
        description="Model tier to use"
    )
    rationale: str = Field(
        min_length=10,
        max_length=500,
        description="Why this agent was selected"
    )
    estimated_tokens: Optional[int] = Field(
        default=None,
        ge=0,
        description="Expected token usage"
    )
    priority: Literal["critical", "high", "medium", "low"] = Field(
        default="medium",
        description="Task priority for this agent"
    )


class DelegationDecision(BaseModel):
    """Decision to delegate work to agents.

    Attributes:
        task_description: What the delegated task should accomplish
        selected_agents: Agents selected for this task
        parallel: Whether agents should run in parallel
        dependencies: Other tasks that must complete first
        timeout_seconds: Maximum time allowed
        retry_budget: Number of retries allowed
    """
    model_config = ConfigDict(extra="forbid")

    task_description: str = Field(
        min_length=10,
        max_length=2000,
        description="What the delegated task should accomplish"
    )
    selected_agents: List[AgentSelection] = Field(
        min_length=1,
        max_length=5,
        description="Agents selected for this task"
    )
    parallel: bool = Field(
        default=False,
        description="Whether agents should run in parallel"
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="Other tasks that must complete first"
    )
    timeout_seconds: int = Field(
        default=300,
        ge=10,
        le=3600,
        description="Maximum time allowed"
    )
    retry_budget: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Number of retries allowed"
    )

    @model_validator(mode="after")
    def validate_parallel_agent_count(self) -> "DelegationDecision":
        """Limit parallel agents to prevent resource exhaustion."""
        if self.parallel and len(self.selected_agents) > 5:
            raise ValueError("Cannot run more than 5 agents in parallel")
        return self


class ResearchCacheEntry(BaseModel):
    """Cached research result for reuse.

    Attributes:
        query_hash: Hash of the original query
        findings_summary: Summary of cached findings
        cached_at: When the cache entry was created
        ttl_minutes: Time-to-live in minutes
        confidence: Confidence level of cached findings
    """
    model_config = ConfigDict(extra="forbid")

    query_hash: str = Field(min_length=1)
    findings_summary: str = Field(min_length=10)
    cached_at: datetime = Field(default_factory=utc_now)
    ttl_minutes: int = Field(default=30, ge=1, le=1440)
    confidence: ConfidenceLevel


class OrchestrationOutput(BaseAgentOutput):
    """Complete orchestrator output schema.

    Attributes:
        original_query: The user's original request
        query_analysis: Analysis of what was asked
        complexity_assessment: How complex the task is
        delegation_decisions: What work to delegate
        direct_response: Response if no delegation needed
        research_cache_hits: Cached results that were reused
        current_round: Current delegation round
        max_rounds: Maximum allowed rounds
        status: Current orchestration status
        human_review_required: Whether human approval is needed
        scope_expansion_detected: Whether scope has grown
    """
    original_query: str = Field(
        min_length=1,
        description="The user's original request"
    )
    query_analysis: str = Field(
        min_length=20,
        max_length=2000,
        description="Analysis of what was asked"
    )
    complexity_assessment: Literal["simple", "moderate", "complex", "very_complex"] = Field(
        description="How complex the task is"
    )
    delegation_decisions: List[DelegationDecision] = Field(
        default_factory=list,
        description="What work to delegate"
    )
    direct_response: Optional[str] = Field(
        default=None,
        description="Response if no delegation needed"
    )
    research_cache_hits: List[ResearchCacheEntry] = Field(
        default_factory=list,
        description="Cached results that were reused"
    )
    current_round: int = Field(
        default=1,
        ge=1,
        le=5,
        description="Current delegation round"
    )
    max_rounds: int = Field(
        default=5,
        ge=1,
        le=5,
        description="Maximum allowed rounds"
    )
    status: Literal["planning", "delegating", "synthesizing", "complete", "escalating"] = Field(
        description="Current orchestration status"
    )
    human_review_required: bool = Field(
        default=False,
        description="Whether human approval is needed"
    )
    scope_expansion_detected: bool = Field(
        default=False,
        description="Whether scope has grown beyond original request"
    )

    @model_validator(mode="after")
    def validate_round_limits(self) -> "OrchestrationOutput":
        """Ensure current round doesn't exceed max."""
        if self.current_round > self.max_rounds:
            raise ValueError(
                f"current_round ({self.current_round}) cannot exceed "
                f"max_rounds ({self.max_rounds})"
            )
        return self

    @model_validator(mode="after")
    def validate_delegation_or_direct(self) -> "OrchestrationOutput":
        """Must have either delegation decisions or direct response."""
        if not self.delegation_decisions and not self.direct_response:
            if self.status not in ("planning", "escalating"):
                raise ValueError(
                    "Must provide either delegation_decisions or direct_response "
                    "unless status is 'planning' or 'escalating'"
                )
        return self

    @model_validator(mode="after")
    def validate_escalation_requires_review(self) -> "OrchestrationOutput":
        """Escalation status requires human review flag."""
        if self.status == "escalating" and not self.human_review_required:
            self.human_review_required = True
        return self
