"""
Rule Extractor.

Extracts generalizable rules from successful agent executions using LLM.

Version: 2.6.0
"""

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Protocol, runtime_checkable

from .models import (
    ExtractedRule,
    ExecutionOutcome,
    RuleCategory,
    RuleStatus,
)

logger = logging.getLogger(__name__)


@runtime_checkable
class LLMClient(Protocol):
    """Protocol for LLM clients."""

    def messages_create(
        self,
        model: str,
        max_tokens: int,
        messages: List[Dict[str, str]],
    ) -> Any:
        """Create a message completion."""
        ...


@dataclass
class ExtractionConfig:
    """Configuration for rule extraction."""
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 2000
    min_quality_score: float = 0.7
    max_rules_per_extraction: int = 5
    require_reasoning: bool = True


class RuleExtractor:
    """
    Extracts generalizable rules from successful executions.

    Uses an LLM to analyze successful task executions and extract
    reusable patterns as formal rules.

    Example:
        extractor = RuleExtractor(client)
        outcome = ExecutionOutcome(
            task="Research AI safety",
            approach="Used multiple sources and cross-verified",
            success=True,
            quality_score=0.9,
            execution_time=45.0,
        )
        rules = await extractor.extract_rules(
            task=outcome.task,
            approach=outcome.approach,
            outcome=outcome
        )
    """

    EXTRACTION_PROMPT = '''Analyze this successful task execution and extract generalizable rules.

TASK: {task}

APPROACH TAKEN: {approach}

OUTCOME:
- Success: {success}
- Quality Score: {quality_score}
- Execution Time: {execution_time}s
- Feedback: {feedback}

Extract rules that would help with similar future tasks.
For each rule, provide:

1. CONDITION: When should this rule apply? Be specific about task characteristics.
2. RECOMMENDATION: What approach should be taken?
3. REASONING: Why does this work?
4. CATEGORY: One of: research, code, analysis, synthesis, validation, general

Only extract rules that are:
- Generalizable (not just for this specific task)
- Actionable (can be applied by an agent)
- Non-obvious (add value beyond basic instructions)

Format as JSON array:
[
    {{
        "condition": "When [specific conditions]...",
        "recommendation": "Do [specific action]...",
        "reasoning": "Because [explanation]...",
        "category": "research"
    }}
]

If no generalizable rules can be extracted, return an empty array: []'''

    def __init__(
        self,
        client: Optional[LLMClient] = None,
        config: Optional[ExtractionConfig] = None,
        extraction_fn: Optional[Callable[[str], str]] = None,
    ):
        """
        Initialize the rule extractor.

        Args:
            client: LLM client (Anthropic-compatible)
            config: Extraction configuration
            extraction_fn: Optional custom extraction function for testing
        """
        self.client = client
        self.config = config or ExtractionConfig()
        self._extraction_fn = extraction_fn

    async def extract_rules(
        self,
        task: str,
        approach: str,
        outcome: ExecutionOutcome,
    ) -> List[ExtractedRule]:
        """
        Extract rules from a successful execution.

        Args:
            task: The task description
            approach: The approach that was taken
            outcome: The execution outcome

        Returns:
            List of extracted rules
        """
        # Only learn from good outcomes
        if not outcome.is_learnable:
            logger.debug(f"Outcome not learnable: success={outcome.success}, quality={outcome.quality_score}")
            return []

        # Build extraction prompt
        prompt = self.EXTRACTION_PROMPT.format(
            task=task,
            approach=approach,
            success=outcome.success,
            quality_score=outcome.quality_score,
            execution_time=outcome.execution_time,
            feedback=outcome.feedback or "None",
        )

        # Get LLM response
        try:
            if self._extraction_fn:
                response_text = self._extraction_fn(prompt)
            elif self.client:
                response = self.client.messages_create(
                    model=self.config.model,
                    max_tokens=self.config.max_tokens,
                    messages=[{"role": "user", "content": prompt}],
                )
                response_text = response.content[0].text
            else:
                logger.warning("No LLM client or extraction function configured")
                return []
        except Exception as e:
            logger.error(f"Error during rule extraction: {e}")
            return []

        # Parse rules from response
        rules = self._parse_rules(response_text, task, outcome.agent_id)

        # Limit number of rules
        return rules[:self.config.max_rules_per_extraction]

    def _parse_rules(
        self,
        response_text: str,
        source_task: str,
        source_agent: str = "",
    ) -> List[ExtractedRule]:
        """Parse rules from LLM response."""
        rules = []

        # Try to extract JSON from response
        json_str = self._extract_json(response_text)
        if not json_str:
            logger.warning("No JSON found in extraction response")
            return []

        try:
            parsed = json.loads(json_str)
            if not isinstance(parsed, list):
                parsed = [parsed]
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON: {e}")
            return []

        for item in parsed:
            if not isinstance(item, dict):
                continue

            condition = item.get("condition", "").strip()
            recommendation = item.get("recommendation", "").strip()
            reasoning = item.get("reasoning", "").strip()
            category_str = item.get("category", "general").lower()

            # Validate required fields
            if not condition or not recommendation:
                continue

            if self.config.require_reasoning and not reasoning:
                continue

            # Parse category
            try:
                category = RuleCategory(category_str)
            except ValueError:
                category = RuleCategory.GENERAL

            # Create rule
            rule = ExtractedRule(
                id=ExtractedRule.generate_id(condition, recommendation),
                condition=condition,
                recommendation=recommendation,
                reasoning=reasoning,
                confidence=0.7,  # Initial confidence
                source_task=source_task,
                source_agent=source_agent,
                category=category,
                status=RuleStatus.ACTIVE,
            )
            rules.append(rule)

        return rules

    def _extract_json(self, text: str) -> Optional[str]:
        """Extract JSON array from text."""
        # Try to find JSON array in text
        # First, look for code blocks
        code_block_match = re.search(r'```(?:json)?\s*([\[\{].*?[\]\}])\s*```', text, re.DOTALL)
        if code_block_match:
            return code_block_match.group(1)

        # Look for bare JSON array
        array_match = re.search(r'\[[\s\S]*?\]', text)
        if array_match:
            return array_match.group(0)

        # Look for bare JSON object
        obj_match = re.search(r'\{[\s\S]*?\}', text)
        if obj_match:
            return obj_match.group(0)

        return None

    def extract_rules_sync(
        self,
        task: str,
        approach: str,
        outcome: ExecutionOutcome,
    ) -> List[ExtractedRule]:
        """
        Synchronous version of extract_rules.

        For use when async is not available.
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.extract_rules(task, approach, outcome))


class MockRuleExtractor:
    """Mock extractor for testing."""

    def __init__(self, rules: Optional[List[ExtractedRule]] = None):
        """Initialize with optional predefined rules."""
        self.rules = rules or []
        self.extract_calls: List[Dict[str, Any]] = []

    async def extract_rules(
        self,
        task: str,
        approach: str,
        outcome: ExecutionOutcome,
    ) -> List[ExtractedRule]:
        """Return predefined rules."""
        self.extract_calls.append({
            "task": task,
            "approach": approach,
            "outcome": outcome,
        })
        return self.rules.copy()

    def set_rules(self, rules: List[ExtractedRule]) -> None:
        """Set rules to return on next extraction."""
        self.rules = rules
