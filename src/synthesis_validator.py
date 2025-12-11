#!/usr/bin/env python3
"""
synthesis_validator.py - Input validation for synthesis agents.

This module implements validation for inputs to synthesis agents,
ensuring they meet required schema before synthesis can proceed.

Key Features:
- Required field validation (task_id, outcome, key_findings, confidence)
- Loop counter logic with progress tracking
- Escalation to orchestrator after max loops
- Graceful degradation with documented gaps

Loop Counter Logic:
- Progress threshold: 50% of missing fields addressed -> reset counter
- Max loops: 5 consecutive rejections without progress -> escalate
- Escalation target: Orchestrator
- Senior action: Proceed with documented gaps
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List, Set
from enum import Enum, auto

from validation import (
    ValidationResult,
    ValidationAction,
    HandoffSchema,
    Validator,
    Confidence,
)

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# CONSTANTS
# ============================================================================

# Required fields for synthesis input
REQUIRED_FIELDS = frozenset(['task_id', 'outcome', 'key_findings', 'confidence'])

# Maximum consecutive loops without progress before escalation
MAX_LOOPS = 5

# Progress threshold for resetting loop counter (50%)
PROGRESS_THRESHOLD = 0.5

# Default escalation target
DEFAULT_ESCALATION_TARGET = "orchestrator"


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class SynthesisValidationState:
    """
    Tracks validation state across iterations.

    This state persists across multiple validation attempts,
    tracking progress and determining when to escalate.
    """
    loop_count: int = 0
    previous_missing: Set[str] = field(default_factory=set)
    total_attempts: int = 0
    escalated: bool = False
    escalation_reason: Optional[str] = None
    last_validation: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "loop_count": self.loop_count,
            "previous_missing": list(self.previous_missing),
            "total_attempts": self.total_attempts,
            "escalated": self.escalated,
            "escalation_reason": self.escalation_reason,
            "last_validation": self.last_validation.isoformat() if self.last_validation else None,
        }


@dataclass
class QualityMetrics:
    """Quality metrics for synthesis input."""
    completeness: float = 0.0  # 0-1 scale
    finding_count: int = 0
    has_confidence: bool = False
    has_sources: bool = False
    has_gaps: bool = False
    estimated_quality: str = "unknown"  # low/medium/high

    def to_dict(self) -> Dict[str, Any]:
        return {
            "completeness": round(self.completeness, 2),
            "finding_count": self.finding_count,
            "has_confidence": self.has_confidence,
            "has_sources": self.has_sources,
            "has_gaps": self.has_gaps,
            "estimated_quality": self.estimated_quality,
        }


# ============================================================================
# SYNTHESIS INPUT VALIDATOR
# ============================================================================

class SynthesisInputValidator(Validator):
    """
    Validates inputs to synthesis agents.

    This validator ensures that inputs to synthesis agents meet
    the required schema and tracks validation attempts to determine
    when to escalate for manual intervention.

    Usage:
        validator = SynthesisInputValidator()
        state = SynthesisValidationState()

        result = validator.validate(input_dict, state=state)
        if result.valid:
            # Proceed with synthesis
        elif result.action == ValidationAction.ESCALATE:
            # Route to orchestrator
        else:
            # Return feedback to source agent
    """

    def __init__(
        self,
        required_fields: Optional[Set[str]] = None,
        max_loops: int = MAX_LOOPS,
        progress_threshold: float = PROGRESS_THRESHOLD,
        escalation_target: str = DEFAULT_ESCALATION_TARGET
    ):
        self.required_fields = required_fields or set(REQUIRED_FIELDS)
        self.max_loops = max_loops
        self.progress_threshold = progress_threshold
        self.escalation_target = escalation_target

    def get_name(self) -> str:
        return "SynthesisInputValidator"

    def validate(
        self,
        input_data: Any,
        state: Optional[SynthesisValidationState] = None,
        **kwargs
    ) -> ValidationResult:
        """
        Validate input against synthesis requirements.

        Args:
            input_data: Dictionary or HandoffSchema to validate
            state: Optional validation state for tracking loops
            **kwargs: Additional validation parameters

        Returns:
            ValidationResult with action to take
        """
        if state is None:
            state = SynthesisValidationState()

        state.total_attempts += 1
        state.last_validation = datetime.now()

        # Convert to dict if HandoffSchema
        if isinstance(input_data, HandoffSchema):
            data = input_data.to_dict()
        elif isinstance(input_data, dict):
            data = input_data
        else:
            return ValidationResult(
                valid=False,
                action=ValidationAction.REJECT,
                reason="Input must be a dictionary or HandoffSchema",
                loop_count=state.loop_count
            )

        # Check for missing required fields
        missing = self.check_required_fields(data)

        # If no missing fields, input is valid
        if not missing:
            quality = self.assess_quality(data)
            return ValidationResult(
                valid=True,
                action=ValidationAction.ACCEPT,
                reason="All required fields present",
                loop_count=state.loop_count
            )

        # Check for progress from previous attempt
        progress = self.check_progress(missing, state.previous_missing)

        # Update loop counter based on progress
        if progress:
            state.loop_count = 1  # Reset on progress
            logger.info(f"Progress made: {len(state.previous_missing - missing)} fields addressed")
        else:
            state.loop_count += 1
            logger.warning(f"No progress: loop count now {state.loop_count}")

        # Update previous missing for next iteration
        state.previous_missing = missing

        # Check for escalation
        if state.loop_count >= self.max_loops:
            state.escalated = True
            state.escalation_reason = f"Max loops ({self.max_loops}) reached without progress"
            logger.error(f"Escalating to {self.escalation_target}: {state.escalation_reason}")

            return ValidationResult(
                valid=False,
                action=ValidationAction.ESCALATE,
                reason=state.escalation_reason,
                missing=missing,
                escalate_to=self.escalation_target,
                loop_count=state.loop_count,
                suggestion=self.create_escalation_suggestion(data, missing)
            )

        # Return rejection with feedback
        return ValidationResult(
            valid=False,
            action=ValidationAction.REJECT,
            reason=f"Missing required fields: {', '.join(sorted(missing))}",
            missing=missing,
            suggestion=self.create_suggestion(missing),
            loop_count=state.loop_count,
            feedback=self.create_feedback(missing, state.loop_count)
        )

    def check_required_fields(self, data: Dict[str, Any]) -> Set[str]:
        """
        Check which required fields are missing.

        Args:
            data: Input dictionary to check

        Returns:
            Set of missing field names
        """
        missing = set()

        for field in self.required_fields:
            if field not in data or not data[field]:
                missing.add(field)
            elif field == "key_findings":
                # Validate key_findings structure
                findings = data.get("key_findings", [])
                if not isinstance(findings, list) or len(findings) < 1:
                    missing.add("key_findings")

        return missing

    def check_progress(self, current_missing: Set[str], previous_missing: Set[str]) -> bool:
        """
        Check if progress was made from previous attempt.

        Progress is defined as addressing at least 50% of previously
        missing fields.

        Args:
            current_missing: Currently missing fields
            previous_missing: Previously missing fields

        Returns:
            True if sufficient progress was made
        """
        if not previous_missing:
            return False

        addressed = previous_missing - current_missing
        progress_ratio = len(addressed) / len(previous_missing)

        return progress_ratio >= self.progress_threshold

    def assess_quality(self, data: Dict[str, Any]) -> QualityMetrics:
        """
        Assess quality of synthesis input.

        Args:
            data: Input dictionary

        Returns:
            QualityMetrics with assessment
        """
        metrics = QualityMetrics()

        # Completeness based on required fields
        present = sum(1 for f in self.required_fields if f in data and data[f])
        metrics.completeness = present / len(self.required_fields)

        # Count findings
        findings = data.get("key_findings", [])
        metrics.finding_count = len(findings) if isinstance(findings, list) else 0

        # Check optional quality indicators
        metrics.has_confidence = bool(data.get("confidence"))
        metrics.has_sources = bool(data.get("sources"))
        metrics.has_gaps = bool(data.get("gaps"))

        # Estimate overall quality
        if metrics.completeness == 1.0 and metrics.finding_count >= 3:
            metrics.estimated_quality = "high"
        elif metrics.completeness >= 0.75 and metrics.finding_count >= 1:
            metrics.estimated_quality = "medium"
        else:
            metrics.estimated_quality = "low"

        return metrics

    def create_suggestion(self, missing: Set[str]) -> str:
        """
        Create suggestion for addressing missing fields.

        Args:
            missing: Set of missing field names

        Returns:
            Suggestion string
        """
        suggestions = []

        if "task_id" in missing:
            suggestions.append("- Add task_id: Unique identifier for the task")

        if "outcome" in missing:
            suggestions.append("- Add outcome: 1-2 sentence summary of what was accomplished")

        if "key_findings" in missing:
            suggestions.append("- Add key_findings: Array of 1-5 findings with confidence levels")
            suggestions.append("  Format: [{\"finding\": \"...\", \"confidence\": \"H/M/L\"}]")

        if "confidence" in missing:
            suggestions.append("- Add confidence: Overall confidence level (H/M/L)")

        return "\n".join(suggestions)

    def create_feedback(self, missing: Set[str], loop_count: int) -> str:
        """
        Create detailed feedback for rejection.

        Args:
            missing: Set of missing field names
            loop_count: Current loop count

        Returns:
            Feedback string
        """
        remaining_attempts = self.max_loops - loop_count

        lines = [
            "## Synthesis Input Validation Failed",
            "",
            f"**Attempt:** {loop_count}/{self.max_loops}",
            f"**Remaining:** {remaining_attempts} attempts before escalation",
            "",
            "### Missing Required Fields",
        ]

        for field in sorted(missing):
            lines.append(f"- [ ] {field}")

        lines.extend([
            "",
            "### Required Format",
            "```json",
            "{",
            '  "task_id": "unique-task-id",',
            '  "outcome": "1-2 sentence summary of accomplishment",',
            '  "key_findings": [',
            '    {"finding": "Key insight 1", "confidence": "H"},',
            '    {"finding": "Key insight 2", "confidence": "M"}',
            '  ],',
            '  "confidence": "M"',
            "}",
            "```",
            "",
            "### Guidance",
            self.create_suggestion(missing),
        ])

        if remaining_attempts <= 2:
            lines.extend([
                "",
                f"**WARNING:** Only {remaining_attempts} attempt(s) remaining.",
                f"After {self.max_loops} failed attempts, this will escalate to {self.escalation_target}."
            ])

        return "\n".join(lines)

    def create_escalation_suggestion(self, data: Dict[str, Any], missing: Set[str]) -> str:
        """
        Create suggestion for escalation scenario.

        Args:
            data: Original input data
            missing: Missing fields

        Returns:
            Escalation suggestion
        """
        lines = [
            "## Escalation: Synthesis Input Validation",
            "",
            "The source agent failed to provide complete input after multiple attempts.",
            "",
            "### Options",
            "1. **Proceed with gaps:** Continue synthesis with documented missing information",
            "2. **Manual fix:** Provide the missing fields directly",
            "3. **Reassign:** Route to a different agent for completion",
            "",
            "### Current Input State",
            f"- Task ID: {data.get('task_id', 'MISSING')}",
            f"- Outcome: {data.get('outcome', 'MISSING')[:100] + '...' if data.get('outcome') else 'MISSING'}",
            f"- Findings: {len(data.get('key_findings', []))} provided",
            f"- Confidence: {data.get('confidence', 'MISSING')}",
            "",
            f"### Missing Fields: {', '.join(sorted(missing))}",
        ]

        return "\n".join(lines)


# ============================================================================
# ESCALATION HANDLER
# ============================================================================

class EscalationHandler:
    """
    Handles escalation from synthesis validation failures.

    This handler routes escalations to the appropriate senior agent
    and provides context for decision-making.
    """

    def __init__(self, default_target: str = DEFAULT_ESCALATION_TARGET):
        self.default_target = default_target
        self.escalation_log: List[Dict[str, Any]] = []

    def handle_escalation(
        self,
        result: ValidationResult,
        original_input: Dict[str, Any],
        source_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle an escalation from validation failure.

        Args:
            result: ValidationResult with escalation action
            original_input: Original input that failed validation
            source_agent: Agent that produced the input

        Returns:
            Escalation context for senior agent
        """
        context = {
            "type": "synthesis_validation_escalation",
            "target": result.escalate_to or self.default_target,
            "source_agent": source_agent,
            "loop_count": result.loop_count,
            "missing_fields": list(result.missing) if result.missing else [],
            "reason": result.reason,
            "original_input": original_input,
            "options": [
                {
                    "action": "proceed_with_gaps",
                    "description": "Continue synthesis with documented missing information",
                    "risk": "Incomplete synthesis output"
                },
                {
                    "action": "manual_completion",
                    "description": "Provide missing fields directly",
                    "risk": "None if accurate"
                },
                {
                    "action": "reassign",
                    "description": "Route to different agent for completion",
                    "risk": "Additional latency"
                },
                {
                    "action": "abort",
                    "description": "Cancel synthesis for this input",
                    "risk": "Incomplete workflow"
                }
            ],
            "timestamp": datetime.now().isoformat()
        }

        # Log escalation
        self.escalation_log.append(context)

        return context

    def proceed_with_gaps(
        self,
        original_input: Dict[str, Any],
        missing_fields: Set[str]
    ) -> Dict[str, Any]:
        """
        Create a modified input that proceeds with documented gaps.

        Args:
            original_input: Original input data
            missing_fields: Fields that are missing

        Returns:
            Modified input with gap documentation
        """
        modified = original_input.copy()

        # Add gap documentation
        if "gaps" not in modified:
            modified["gaps"] = []

        for field in missing_fields:
            gap_doc = f"[VALIDATION GAP] Field '{field}' was not provided by source agent"
            if gap_doc not in modified["gaps"]:
                modified["gaps"].append(gap_doc)

        # Add defaults for missing required fields
        if "task_id" not in modified or not modified["task_id"]:
            modified["task_id"] = f"gap-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        if "outcome" not in modified or not modified["outcome"]:
            modified["outcome"] = "[INCOMPLETE] Outcome not provided by source agent"

        if "key_findings" not in modified or not modified["key_findings"]:
            modified["key_findings"] = [{"finding": "[INCOMPLETE] No findings provided", "confidence": "L"}]

        if "confidence" not in modified or not modified["confidence"]:
            modified["confidence"] = "L"

        modified["_proceeded_with_gaps"] = True
        modified["_original_missing"] = list(missing_fields)

        return modified

    def get_escalation_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent escalation history."""
        return self.escalation_log[-limit:]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def validate_synthesis_input(
    input_data: Dict[str, Any],
    state: Optional[SynthesisValidationState] = None
) -> ValidationResult:
    """
    Convenience function for validating synthesis input.

    Args:
        input_data: Input dictionary to validate
        state: Optional validation state

    Returns:
        ValidationResult
    """
    validator = SynthesisInputValidator()
    return validator.validate(input_data, state=state)


def create_valid_synthesis_input(
    task_id: str,
    outcome: str,
    findings: List[Dict[str, str]],
    confidence: str = "M",
    **kwargs
) -> Dict[str, Any]:
    """
    Create a valid synthesis input dictionary.

    Args:
        task_id: Task identifier
        outcome: Outcome summary
        findings: List of findings
        confidence: Overall confidence
        **kwargs: Additional fields

    Returns:
        Valid input dictionary
    """
    return {
        "task_id": task_id,
        "outcome": outcome,
        "key_findings": findings,
        "confidence": confidence,
        **kwargs
    }
