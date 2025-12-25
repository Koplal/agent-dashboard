#!/usr/bin/env python3
"""
compression_gate.py - Token budget enforcement between agent tiers.

This module implements compression gating to ensure senior agents receive
appropriately compressed inputs from junior agents.

Architecture: Hybrid (Centralized Enforcement + Distributed Awareness)

Thresholds:
- Soft: 1.25x budget -> Auto-route to summarizer
- Hard: 2.0x budget -> Reject with specific feedback

Budget Matrix:
| Source -> Target | Budget |
|------------------|--------|
| Haiku -> Opus    | 300    |
| Haiku -> Sonnet  | 500    |
| Sonnet -> Opus   | 1000   |
| Sonnet -> Sonnet | 1500   |

Dependencies:
    - tiktoken: Accurate token counting (optional, falls back to estimation)
    - validation: Base validation classes

Version: 2.6.0
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum, auto

# Import centralized token counter
try:
    from src.token_counter import count_tokens as _count_tokens_central
    _CENTRAL_COUNTER_AVAILABLE = True
except ImportError:
    _CENTRAL_COUNTER_AVAILABLE = False
    _count_tokens_central = None

from validation import (
    ValidationAction,
    GateResult,
    AgentTier,
    HandoffSchema,
)

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS AND CONSTANTS
# ============================================================================

class GateAction(Enum):
    """Actions that can be taken by the compression gate."""
    PASS = auto()       # Within budget, proceed
    AUTO_ROUTE = auto() # Soft threshold exceeded, route to summarizer
    REJECT = auto()     # Hard threshold exceeded, reject with feedback


# Token budgets for agent tier pairs
# Format: (source_tier, target_tier) -> max_tokens
TIER_BUDGETS: Dict[Tuple[AgentTier, AgentTier], int] = {
    (AgentTier.HAIKU, AgentTier.OPUS): 300,
    (AgentTier.HAIKU, AgentTier.SONNET): 500,
    (AgentTier.SONNET, AgentTier.OPUS): 1000,
    (AgentTier.SONNET, AgentTier.SONNET): 1500,
    # Default fallbacks
    (AgentTier.OPUS, AgentTier.OPUS): 1500,
    (AgentTier.HAIKU, AgentTier.HAIKU): 1000,
}

# Default budget when tier pair not found
DEFAULT_BUDGET = 500


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class GateDecision:
    """
    Complete decision record from compression gate.

    Includes all information needed for audit logging and feedback.
    """
    action: GateAction
    tokens: int
    budget: int
    ratio: float
    source_tier: AgentTier
    target_tier: AgentTier
    task_id: Optional[str] = None
    agent_name: Optional[str] = None
    routed_to: Optional[str] = None
    feedback: Optional[str] = None
    original_content: Optional[str] = None
    compressed_content: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action.name,
            "tokens": self.tokens,
            "budget": self.budget,
            "ratio": round(self.ratio, 2),
            "source_tier": self.source_tier.value,
            "target_tier": self.target_tier.value,
            "task_id": self.task_id,
            "agent_name": self.agent_name,
            "routed_to": self.routed_to,
            "feedback": self.feedback,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class CompressionStats:
    """Statistics for compression gate operations."""
    total_validations: int = 0
    passed: int = 0
    auto_routed: int = 0
    rejected: int = 0
    total_tokens_processed: int = 0
    total_tokens_saved: int = 0
    average_compression_ratio: float = 0.0


# ============================================================================
# COMPRESSION GATE
# ============================================================================

class CompressionGate:
    """
    Enforces token budgets between agent tiers.

    The CompressionGate sits between agents and validates that outputs
    from lower-tier agents are appropriately compressed before being
    passed to higher-tier agents.

    Thresholds:
    - SOFT_THRESHOLD (1.25x): Auto-route to summarizer
    - HARD_THRESHOLD (2.0x): Reject with specific feedback

    Usage:
        gate = CompressionGate()
        result = gate.validate("output text", AgentTier.HAIKU, AgentTier.OPUS)
        if result.action == GateAction.PASS:
            # Proceed with handoff
        elif result.action == GateAction.AUTO_ROUTE:
            # Send to summarizer first
        else:
            # Reject and provide feedback
    """

    SOFT_THRESHOLD = 1.25  # 25% over budget -> auto-route
    HARD_THRESHOLD = 2.0   # 100% over budget -> reject

    def __init__(
        self,
        budgets: Optional[Dict[Tuple[AgentTier, AgentTier], int]] = None,
        summarizer_agent: str = "summarizer"
    ):
        """
        Initialize the compression gate.

        Args:
            budgets: Optional custom budget matrix
            summarizer_agent: Name of summarizer agent for auto-routing
        """
        self.budgets = budgets or TIER_BUDGETS.copy()
        self.summarizer_agent = summarizer_agent
        self.stats = CompressionStats()
        self.decision_log: List[GateDecision] = []
        self._max_log_size = 1000

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using centralized token counter.

        Delegates to src.token_counter for accurate counting with
        multi-tier fallback (Claude HF -> Anthropic API -> tiktoken -> char).

        Args:
            text: Text to count tokens for

        Returns:
            Token count
        """
        if not text:
            return 0

        if _CENTRAL_COUNTER_AVAILABLE and _count_tokens_central is not None:
            try:
                return _count_tokens_central(text)
            except Exception:
                pass

        # Emergency fallback: ~4 chars per token
        return len(text) // 4

    def get_budget(self, source_tier: AgentTier, target_tier: AgentTier) -> int:
        """
        Get token budget for a source-target tier pair.

        Args:
            source_tier: Tier of the producing agent
            target_tier: Tier of the receiving agent

        Returns:
            Maximum token budget for this pair
        """
        return self.budgets.get((source_tier, target_tier), DEFAULT_BUDGET)

    def create_feedback(self, tokens: int, budget: int, source_tier: AgentTier, target_tier: AgentTier) -> str:
        """
        Create specific feedback for rejected outputs.

        Args:
            tokens: Actual token count
            budget: Token budget
            source_tier: Producing agent tier
            target_tier: Receiving agent tier

        Returns:
            Feedback message with specific guidance
        """
        overage = tokens - budget
        ratio = tokens / budget

        feedback_lines = [
            f"## Compression Required",
            f"",
            f"**Current:** {tokens} tokens | **Budget:** {budget} tokens | **Ratio:** {ratio:.1f}x",
            f"**Overage:** {overage} tokens ({(ratio - 1) * 100:.0f}% over budget)",
            f"",
            f"### Requirements",
            f"- {source_tier.value.title()} -> {target_tier.value.title()} handoff budget: {budget} tokens",
            f"- Your output must be compressed by at least {ratio:.1f}x",
            f"",
            f"### Compression Guidelines",
            f"1. Focus on KEY FINDINGS only (max 5)",
            f"2. Use 1-2 sentence outcome summary",
            f"3. Remove redundant explanations",
            f"4. Keep only high-confidence items",
            f"5. Use bullet points, not paragraphs",
            f"",
            f"### Required Format",
            f"```",
            f"## Task Completion: [task_id]",
            f"**Outcome:** [1-2 sentences]",
            f"### Key Findings",
            f"1. [Finding] - Confidence: [H/M/L]",
            f"### Gaps",
            f"- [What couldn't be determined]",
            f"```",
        ]

        return "\n".join(feedback_lines)

    def validate(
        self,
        output: str,
        source_tier: AgentTier,
        target_tier: AgentTier,
        task_id: Optional[str] = None,
        agent_name: Optional[str] = None
    ) -> GateDecision:
        """
        Validate output against compression budget.

        Args:
            output: Text output from agent
            source_tier: Tier of the producing agent
            target_tier: Tier of the receiving agent
            task_id: Optional task identifier for logging
            agent_name: Optional agent name for logging

        Returns:
            GateDecision with action to take
        """
        budget = self.get_budget(source_tier, target_tier)
        tokens = self.count_tokens(output)
        ratio = tokens / budget if budget > 0 else float('inf')

        # Update stats
        self.stats.total_validations += 1
        self.stats.total_tokens_processed += tokens

        # Determine action based on thresholds
        if ratio <= 1.0:
            action = GateAction.PASS
            self.stats.passed += 1
            feedback = None
            routed_to = None
        elif ratio <= self.SOFT_THRESHOLD:
            # Within tolerance, still pass
            action = GateAction.PASS
            self.stats.passed += 1
            feedback = None
            routed_to = None
            logger.info(f"Gate: {tokens} tokens at {ratio:.2f}x budget (within tolerance)")
        elif ratio <= self.HARD_THRESHOLD:
            # Soft threshold exceeded, auto-route to summarizer
            action = GateAction.AUTO_ROUTE
            self.stats.auto_routed += 1
            routed_to = self.summarizer_agent
            feedback = f"Output ({tokens} tokens) exceeds budget ({budget} tokens). Auto-routing to {self.summarizer_agent}."
            logger.warning(f"Gate: Auto-routing to {self.summarizer_agent} ({tokens}/{budget} tokens)")
        else:
            # Hard threshold exceeded, reject
            action = GateAction.REJECT
            self.stats.rejected += 1
            routed_to = None
            feedback = self.create_feedback(tokens, budget, source_tier, target_tier)
            logger.error(f"Gate: Rejected output ({tokens}/{budget} tokens, {ratio:.1f}x budget)")

        # Create decision record
        decision = GateDecision(
            action=action,
            tokens=tokens,
            budget=budget,
            ratio=ratio,
            source_tier=source_tier,
            target_tier=target_tier,
            task_id=task_id,
            agent_name=agent_name,
            routed_to=routed_to,
            feedback=feedback,
        )

        # Log decision
        self._log_decision(decision)

        return decision

    def validate_handoff(
        self,
        handoff: HandoffSchema,
        target_tier: AgentTier
    ) -> GateDecision:
        """
        Validate a HandoffSchema against compression budget.

        Args:
            handoff: HandoffSchema to validate
            target_tier: Tier of the receiving agent

        Returns:
            GateDecision with action to take
        """
        source_tier = handoff.model_tier or AgentTier.SONNET
        output = handoff.to_markdown()

        return self.validate(
            output=output,
            source_tier=source_tier,
            target_tier=target_tier,
            task_id=handoff.task_id,
            agent_name=handoff.agent_name
        )

    def _log_decision(self, decision: GateDecision) -> None:
        """Log a gate decision, maintaining max log size."""
        self.decision_log.append(decision)
        if len(self.decision_log) > self._max_log_size:
            self.decision_log = self.decision_log[-self._max_log_size:]

    def get_stats(self) -> Dict[str, Any]:
        """Get compression gate statistics."""
        return {
            "total_validations": self.stats.total_validations,
            "passed": self.stats.passed,
            "auto_routed": self.stats.auto_routed,
            "rejected": self.stats.rejected,
            "pass_rate": f"{(self.stats.passed / self.stats.total_validations * 100):.1f}%" if self.stats.total_validations > 0 else "N/A",
            "total_tokens_processed": self.stats.total_tokens_processed,
        }

    def get_recent_decisions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent gate decisions."""
        return [d.to_dict() for d in self.decision_log[-limit:]]

    def reset_stats(self) -> None:
        """Reset statistics."""
        self.stats = CompressionStats()
        self.decision_log.clear()


# ============================================================================
# BUDGET AWARE WRAPPER
# ============================================================================

class BudgetAwareAgent:
    """
    Wrapper that adds budget awareness to agent outputs.

    This wrapper can be used to automatically check outputs against
    compression gate budgets before handoff.
    """

    def __init__(
        self,
        agent_name: str,
        tier: AgentTier,
        gate: Optional[CompressionGate] = None
    ):
        self.agent_name = agent_name
        self.tier = tier
        self.gate = gate or CompressionGate()

    def prepare_handoff(
        self,
        output: str,
        target_tier: AgentTier,
        task_id: Optional[str] = None
    ) -> Tuple[str, GateDecision]:
        """
        Prepare output for handoff, checking against gate.

        Args:
            output: Agent output text
            target_tier: Tier of receiving agent
            task_id: Optional task identifier

        Returns:
            Tuple of (output_or_feedback, GateDecision)
        """
        decision = self.gate.validate(
            output=output,
            source_tier=self.tier,
            target_tier=target_tier,
            task_id=task_id,
            agent_name=self.agent_name
        )

        if decision.action == GateAction.PASS:
            return output, decision
        elif decision.action == GateAction.AUTO_ROUTE:
            # Return original output with routing indicator
            return output, decision
        else:
            # Return feedback for rejection
            return decision.feedback or "Output too large", decision

    def get_budget_for_target(self, target_tier: AgentTier) -> int:
        """Get token budget for handoff to target tier."""
        return self.gate.get_budget(self.tier, target_tier)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_tier_from_model(model: str) -> AgentTier:
    """
    Get AgentTier from model name string.

    Args:
        model: Model name (e.g., "opus", "sonnet", "haiku")

    Returns:
        Corresponding AgentTier
    """
    model_lower = model.lower()
    if "opus" in model_lower:
        return AgentTier.OPUS
    elif "haiku" in model_lower:
        return AgentTier.HAIKU
    else:
        return AgentTier.SONNET


def estimate_compression_ratio(input_tokens: int, output_tokens: int) -> float:
    """
    Calculate compression ratio from input to output.

    Args:
        input_tokens: Original token count
        output_tokens: Compressed token count

    Returns:
        Compression ratio (input/output)
    """
    if output_tokens <= 0:
        return float('inf')
    return input_tokens / output_tokens


def format_budget_status(
    tokens: int,
    budget: int,
    source_tier: AgentTier,
    target_tier: AgentTier
) -> str:
    """
    Format budget status for display.

    Args:
        tokens: Current token count
        budget: Token budget
        source_tier: Source agent tier
        target_tier: Target agent tier

    Returns:
        Formatted status string
    """
    ratio = tokens / budget if budget > 0 else 0
    status = "OK" if ratio <= 1.0 else ("WARNING" if ratio <= 1.25 else "OVER")

    return (
        f"[{status}] {tokens}/{budget} tokens "
        f"({ratio:.0%}) - {source_tier.value} -> {target_tier.value}"
    )
