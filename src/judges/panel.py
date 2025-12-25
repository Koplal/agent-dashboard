"""
Judge Panel Implementation.

Provides the JudgePanel class for coordinating heterogeneous
judge evaluations with verdict aggregation and human escalation.

Version: 2.6.0
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Callable, Tuple
from enum import Enum

from .configurations import JudgeConfig, JudgePersona, get_default_panel_configs

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


# =============================================================================
# DATA CLASSES
# =============================================================================

class EscalationReason(Enum):
    """Reasons for human escalation."""
    LOW_CONSENSUS = "low_consensus"
    LOW_CONFIDENCE = "low_confidence"
    CRITICAL_ISSUES = "critical_issues"
    CONFLICTING_VERDICTS = "conflicting_verdicts"
    SCORE_VARIANCE = "score_variance"


@dataclass
class ParsedVerdict:
    """
    Parsed verdict from a single judge response.

    Attributes:
        persona: Judge persona type
        passed: Whether the content passed evaluation
        score: Numeric score (0.0-1.0)
        confidence: Confidence level (0.0-1.0)
        issues_found: List of issues with severity
        strengths_noted: Positive aspects noted
        detailed_feedback: Full evaluation text
        dimension_scores: Optional per-dimension scores
        raw_response: Original response text
    """
    persona: JudgePersona
    passed: bool
    score: float
    confidence: float
    issues_found: List[Dict[str, str]] = field(default_factory=list)
    strengths_noted: List[str] = field(default_factory=list)
    detailed_feedback: str = ""
    dimension_scores: Dict[str, float] = field(default_factory=dict)
    raw_response: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "persona": self.persona.value,
            "passed": self.passed,
            "score": self.score,
            "confidence": self.confidence,
            "issues_found": self.issues_found,
            "strengths_noted": self.strengths_noted,
            "detailed_feedback": self.detailed_feedback[:500] + "..." if len(self.detailed_feedback) > 500 else self.detailed_feedback,
            "dimension_scores": self.dimension_scores,
        }


@dataclass
class AggregatedVerdict:
    """
    Aggregated verdict from all judges.

    Attributes:
        passed: Whether the panel approved the content
        consensus_level: Level of agreement (0.0-1.0)
        aggregated_score: Weighted average score
        individual_verdicts: Each judge's verdict
        critical_issues: Issues found by multiple judges
        requires_human_review: Whether human should review
        escalation_reasons: Why human review is needed
        recommendation: Final recommendation text
        dissenting_opinions: Summary of disagreements
        evaluation_duration_ms: Total evaluation time
    """
    passed: bool
    consensus_level: float
    aggregated_score: float
    individual_verdicts: List[ParsedVerdict]
    critical_issues: List[str] = field(default_factory=list)
    requires_human_review: bool = False
    escalation_reasons: List[EscalationReason] = field(default_factory=list)
    recommendation: str = ""
    dissenting_opinions: List[str] = field(default_factory=list)
    evaluation_duration_ms: int = 0
    timestamp: datetime = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "passed": self.passed,
            "consensus_level": self.consensus_level,
            "aggregated_score": self.aggregated_score,
            "individual_verdicts": [v.to_dict() for v in self.individual_verdicts],
            "critical_issues": self.critical_issues,
            "requires_human_review": self.requires_human_review,
            "escalation_reasons": [r.value for r in self.escalation_reasons],
            "recommendation": self.recommendation,
            "dissenting_opinions": self.dissenting_opinions,
            "evaluation_duration_ms": self.evaluation_duration_ms,
            "timestamp": self.timestamp.isoformat(),
        }


# =============================================================================
# VERDICT PARSER
# =============================================================================

class VerdictParser:
    """
    Parses judge responses into structured verdicts.

    Handles various response formats and extracts:
    - Pass/Fail status
    - Numeric scores
    - Issues and strengths
    - Confidence levels
    """

    # Regex patterns for parsing
    OVERALL_PATTERN = re.compile(
        r"(?:OVERALL\s*ASSESSMENT|VERDICT)[:\s]*([A-Z]+)",
        re.IGNORECASE
    )
    SCORE_PATTERN = re.compile(
        r"(?:SCORE|RATING)[:\s]*(\d+(?:\.\d+)?)\s*(?:/\s*100|%)?",
        re.IGNORECASE
    )
    CONFIDENCE_PATTERN = re.compile(
        r"(?:CONFIDENCE)[:\s]*(\d+(?:\.\d+)?)\s*%?",
        re.IGNORECASE
    )
    ISSUE_PATTERN = re.compile(
        r"[-•*]\s*(?:\[?(CRITICAL|MAJOR|MINOR|SUGGESTION)\]?[:\s]*)?(.*?)(?=[-•*]|\n\n|$)",
        re.IGNORECASE | re.DOTALL
    )
    STRENGTH_PATTERN = re.compile(
        r"[-•*]\s*(.*?)(?=[-•*]|\n\n|$)",
        re.IGNORECASE | re.DOTALL
    )

    def parse(self, response: str, persona: JudgePersona) -> ParsedVerdict:
        """
        Parse a judge response into a structured verdict.

        Args:
            response: Raw response text from judge
            persona: Judge persona type

        Returns:
            ParsedVerdict with extracted information
        """
        # Extract pass/fail
        passed = self._extract_passed(response)

        # Extract score (0-100 -> 0.0-1.0)
        score = self._extract_score(response)

        # Extract confidence
        confidence = self._extract_confidence(response)

        # Extract issues
        issues = self._extract_issues(response)

        # Extract strengths
        strengths = self._extract_strengths(response)

        # Extract detailed feedback
        feedback = self._extract_feedback(response)

        return ParsedVerdict(
            persona=persona,
            passed=passed,
            score=score,
            confidence=confidence,
            issues_found=issues,
            strengths_noted=strengths,
            detailed_feedback=feedback,
            raw_response=response,
        )

    def _extract_passed(self, response: str) -> bool:
        """Extract pass/fail status."""
        match = self.OVERALL_PATTERN.search(response)
        if match:
            status = match.group(1).upper()
            if status in ("PASS", "PASSED", "APPROVE", "APPROVED"):
                return True
            if status in ("FAIL", "FAILED", "REJECT", "REJECTED"):
                return False

        # Fallback: look for keywords
        upper = response.upper()
        if "VERDICT: PASS" in upper or "**PASS**" in upper:
            return True
        if "VERDICT: FAIL" in upper or "**FAIL**" in upper:
            return False

        # Default to score-based decision
        score = self._extract_score(response)
        return score >= 0.6

    def _extract_score(self, response: str) -> float:
        """Extract numeric score (normalized to 0.0-1.0)."""
        # Check for X/5 rubric scores FIRST (before general SCORE pattern)
        rubric_match = re.search(r"(\d+(?:\.\d+)?)\s*/\s*5", response)
        if rubric_match:
            return float(rubric_match.group(1)) / 5.0

        # Check for general SCORE pattern
        match = self.SCORE_PATTERN.search(response)
        if match:
            score = float(match.group(1))
            # Normalize to 0.0-1.0
            if score > 1.0:
                score = score / 100.0
            return min(1.0, max(0.0, score))

        # Default
        return 0.5

    def _extract_confidence(self, response: str) -> float:
        """Extract confidence level (normalized to 0.0-1.0)."""
        match = self.CONFIDENCE_PATTERN.search(response)
        if match:
            confidence = float(match.group(1))
            if confidence > 1.0:
                confidence = confidence / 100.0
            return min(1.0, max(0.0, confidence))

        # Default to moderate confidence
        return 0.7

    def _extract_issues(self, response: str) -> List[Dict[str, str]]:
        """Extract issues with severity."""
        issues = []

        # Find issues section
        issues_section = ""
        for marker in ["ISSUES FOUND:", "ISSUES:", "PROBLEMS:", "CONCERNS:"]:
            idx = response.upper().find(marker)
            if idx != -1:
                # Get text until next section
                end_idx = len(response)
                for end_marker in ["STRENGTHS", "DETAILED FEEDBACK", "VERDICT", "RECOMMENDATION"]:
                    next_idx = response.upper().find(end_marker, idx + len(marker))
                    if next_idx != -1:
                        end_idx = min(end_idx, next_idx)
                issues_section = response[idx + len(marker):end_idx]
                break

        if issues_section:
            for match in self.ISSUE_PATTERN.finditer(issues_section):
                severity = match.group(1) or "minor"
                text = match.group(2).strip()
                if text and len(text) > 5:
                    issues.append({
                        "severity": severity.lower(),
                        "issue": text[:200],
                    })

        return issues[:10]  # Limit to 10 issues

    def _extract_strengths(self, response: str) -> List[str]:
        """Extract strengths noted."""
        strengths = []

        # Find strengths section
        for marker in ["STRENGTHS:", "POSITIVE:", "GOOD:"]:
            idx = response.upper().find(marker)
            if idx != -1:
                end_idx = len(response)
                for end_marker in ["ISSUES", "DETAILED FEEDBACK", "VERDICT", "RECOMMENDATION"]:
                    next_idx = response.upper().find(end_marker, idx + len(marker))
                    if next_idx != -1:
                        end_idx = min(end_idx, next_idx)
                section = response[idx + len(marker):end_idx]

                for match in self.STRENGTH_PATTERN.finditer(section):
                    text = match.group(1).strip()
                    if text and len(text) > 5:
                        strengths.append(text[:200])
                break

        return strengths[:5]  # Limit to 5 strengths

    def _extract_feedback(self, response: str) -> str:
        """Extract detailed feedback section."""
        for marker in ["DETAILED FEEDBACK:", "FEEDBACK:", "ANALYSIS:"]:
            idx = response.upper().find(marker)
            if idx != -1:
                # Get rest of response or until next major section
                feedback = response[idx + len(marker):].strip()
                # Truncate at next section marker if present
                for end_marker in ["###", "##", "---"]:
                    end_idx = feedback.find(end_marker)
                    if end_idx > 100:
                        feedback = feedback[:end_idx].strip()
                        break
                return feedback[:2000]

        # Fallback: return last paragraph
        paragraphs = response.split("\n\n")
        if paragraphs:
            return paragraphs[-1].strip()[:1000]

        return ""


# =============================================================================
# ESCALATION HANDLER
# =============================================================================

@dataclass
class EscalationRequest:
    """Request for human escalation."""
    task_id: str
    content_summary: str
    verdict: "AggregatedVerdict"
    reasons: List[EscalationReason]
    priority: str  # "critical", "high", "normal"
    requested_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "content_summary": self.content_summary[:500],
            "verdict": self.verdict.to_dict(),
            "reasons": [r.value for r in self.reasons],
            "priority": self.priority,
            "requested_at": self.requested_at.isoformat(),
        }


class EscalationHandler:
    """
    Handles human escalation workflow.

    Determines when human review is needed and manages
    escalation requests.
    """

    def __init__(
        self,
        consensus_threshold: float = 0.6,
        confidence_threshold: float = 0.5,
        score_variance_threshold: float = 0.3,
        on_escalation: Optional[Callable[[EscalationRequest], None]] = None,
    ):
        """
        Initialize the escalation handler.

        Args:
            consensus_threshold: Minimum consensus to avoid escalation
            confidence_threshold: Minimum confidence to avoid escalation
            score_variance_threshold: Maximum score variance allowed
            on_escalation: Callback for escalation events
        """
        self.consensus_threshold = consensus_threshold
        self.confidence_threshold = confidence_threshold
        self.score_variance_threshold = score_variance_threshold
        self.on_escalation = on_escalation
        self.escalation_history: List[EscalationRequest] = []

    def check_escalation_needed(
        self,
        verdict: AggregatedVerdict,
    ) -> Tuple[bool, List[EscalationReason]]:
        """
        Check if human escalation is needed.

        Args:
            verdict: Aggregated verdict to check

        Returns:
            Tuple of (needs_escalation, reasons)
        """
        reasons = []

        # Check consensus level
        if verdict.consensus_level < self.consensus_threshold:
            reasons.append(EscalationReason.LOW_CONSENSUS)

        # Check confidence levels
        low_confidence = [
            v for v in verdict.individual_verdicts
            if v.confidence < self.confidence_threshold
        ]
        if low_confidence:
            reasons.append(EscalationReason.LOW_CONFIDENCE)

        # Check for critical issues
        critical_issues = []
        for v in verdict.individual_verdicts:
            for issue in v.issues_found:
                if issue.get("severity") == "critical":
                    critical_issues.append(issue.get("issue", ""))
        if critical_issues:
            reasons.append(EscalationReason.CRITICAL_ISSUES)

        # Check for conflicting verdicts
        pass_count = sum(1 for v in verdict.individual_verdicts if v.passed)
        fail_count = len(verdict.individual_verdicts) - pass_count
        if pass_count > 0 and fail_count > 0:
            # Some passed, some failed
            if min(pass_count, fail_count) / len(verdict.individual_verdicts) > 0.3:
                reasons.append(EscalationReason.CONFLICTING_VERDICTS)

        # Check score variance
        if verdict.individual_verdicts:
            scores = [v.score for v in verdict.individual_verdicts]
            variance = max(scores) - min(scores)
            if variance > self.score_variance_threshold:
                reasons.append(EscalationReason.SCORE_VARIANCE)

        return len(reasons) > 0, reasons

    def create_escalation(
        self,
        task_id: str,
        content_summary: str,
        verdict: AggregatedVerdict,
        reasons: List[EscalationReason],
    ) -> EscalationRequest:
        """
        Create an escalation request.

        Args:
            task_id: Task identifier
            content_summary: Summary of content being evaluated
            verdict: Aggregated verdict
            reasons: Escalation reasons

        Returns:
            EscalationRequest
        """
        # Determine priority
        if EscalationReason.CRITICAL_ISSUES in reasons:
            priority = "critical"
        elif EscalationReason.LOW_CONSENSUS in reasons:
            priority = "high"
        else:
            priority = "normal"

        request = EscalationRequest(
            task_id=task_id,
            content_summary=content_summary,
            verdict=verdict,
            reasons=reasons,
            priority=priority,
        )

        self.escalation_history.append(request)

        # Trigger callback if set
        if self.on_escalation:
            try:
                self.on_escalation(request)
            except Exception as e:
                logger.error(f"Escalation callback failed: {e}")

        return request


# =============================================================================
# JUDGE PANEL
# =============================================================================

class JudgePanel:
    """
    Panel of heterogeneous judges for robust evaluation.

    Coordinates multiple judges with different configurations,
    aggregates their verdicts, and handles escalation.

    Example:
        panel = JudgePanel(panel_size=5)
        verdict = await panel.evaluate(
            content="...",
            context={"original_request": "..."},
            content_type="research"
        )
        if verdict.passed:
            print("Content approved")
        if verdict.requires_human_review:
            print("Human review needed:", verdict.escalation_reasons)
    """

    def __init__(
        self,
        configs: Optional[List[JudgeConfig]] = None,
        panel_size: int = 3,
        consensus_threshold: float = 0.7,
        require_unanimous_pass: bool = False,
        api_client: Optional[Any] = None,
    ):
        """
        Initialize the judge panel.

        Args:
            configs: List of judge configurations (or use default for panel_size)
            panel_size: Number of judges if using defaults (3, 5, or 7)
            consensus_threshold: Minimum consensus for pass (0.0-1.0)
            require_unanimous_pass: Require all judges to pass
            api_client: API client for LLM calls (optional, for testing)
        """
        self.configs = configs or get_default_panel_configs(panel_size)
        self.consensus_threshold = consensus_threshold
        self.require_unanimous_pass = require_unanimous_pass
        self.api_client = api_client

        self.parser = VerdictParser()
        self.escalation_handler = EscalationHandler()

        # Statistics
        self.evaluations_run = 0
        self.total_passes = 0
        self.total_escalations = 0

    async def evaluate(
        self,
        content: str,
        context: Dict[str, Any],
        content_type: str,
        task_id: Optional[str] = None,
    ) -> AggregatedVerdict:
        """
        Run all judges and aggregate verdicts.

        Args:
            content: Content to evaluate
            context: Additional context (original request, etc.)
            content_type: Type of content (research, code, documentation)
            task_id: Optional task identifier

        Returns:
            AggregatedVerdict with combined results
        """
        start_time = datetime.now(timezone.utc)
        task_id = task_id or f"eval-{start_time.strftime('%Y%m%d%H%M%S')}"

        # Run all judges (in parallel if async)
        verdicts = await self._run_all_judges(content, context, content_type)

        # Aggregate results
        aggregated = self._aggregate_verdicts(verdicts)

        # Calculate duration
        duration = datetime.now(timezone.utc) - start_time
        aggregated.evaluation_duration_ms = int(duration.total_seconds() * 1000)

        # Check for escalation
        needs_escalation, reasons = self.escalation_handler.check_escalation_needed(
            aggregated
        )
        if needs_escalation:
            aggregated.requires_human_review = True
            aggregated.escalation_reasons = reasons
            self.escalation_handler.create_escalation(
                task_id=task_id,
                content_summary=content[:500],
                verdict=aggregated,
                reasons=reasons,
            )
            self.total_escalations += 1

        # Update stats
        self.evaluations_run += 1
        if aggregated.passed:
            self.total_passes += 1

        return aggregated

    async def _run_all_judges(
        self,
        content: str,
        context: Dict[str, Any],
        content_type: str,
    ) -> List[ParsedVerdict]:
        """Run all judges and collect verdicts."""
        if self.api_client:
            # Real API calls (parallel)
            tasks = [
                self._run_single_judge(config, content, context, content_type)
                for config in self.configs
            ]
            return await asyncio.gather(*tasks)
        else:
            # Mock mode for testing
            return [
                self._mock_judge_response(config)
                for config in self.configs
            ]

    async def _run_single_judge(
        self,
        config: JudgeConfig,
        content: str,
        context: Dict[str, Any],
        content_type: str,
    ) -> ParsedVerdict:
        """Execute single judge evaluation."""
        evaluation_prompt = self._build_evaluation_prompt(
            config, content, context, content_type
        )

        try:
            response = await self._call_api(config, evaluation_prompt)
            return self.parser.parse(response, config.persona)
        except Exception as e:
            logger.error(f"Judge {config.persona.value} failed: {e}")
            # Return failed verdict
            return ParsedVerdict(
                persona=config.persona,
                passed=False,
                score=0.0,
                confidence=0.0,
                detailed_feedback=f"Judge execution failed: {e}",
            )

    async def _call_api(
        self,
        config: JudgeConfig,
        prompt: str,
    ) -> str:
        """Make API call to LLM."""
        if not self.api_client:
            raise ValueError("No API client configured")

        # Anthropic-style API call
        response = await asyncio.to_thread(
            self.api_client.messages.create,
            model=config.model,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
            system=config.system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text

    def _build_evaluation_prompt(
        self,
        config: JudgeConfig,
        content: str,
        context: Dict[str, Any],
        content_type: str,
    ) -> str:
        """Build the evaluation prompt for a judge."""
        context_str = "\n".join(
            f"- {k}: {v}" for k, v in context.items()
            if isinstance(v, str) and len(str(v)) < 500
        )

        return f"""Evaluate the following {content_type} output.

CONTEXT:
{context_str}

CONTENT TO EVALUATE:
{content}

Provide your evaluation focusing on: {', '.join(config.evaluation_focus)}

Structure your response according to your evaluation format.
Be specific and cite evidence from the content."""

    def _mock_judge_response(self, config: JudgeConfig) -> ParsedVerdict:
        """Generate mock verdict for testing."""
        import random

        passed = random.random() > 0.3
        score = random.uniform(0.5, 1.0) if passed else random.uniform(0.2, 0.6)

        return ParsedVerdict(
            persona=config.persona,
            passed=passed,
            score=score,
            confidence=random.uniform(0.6, 0.95),
            issues_found=[
                {"severity": "minor", "issue": "Mock issue for testing"}
            ] if not passed else [],
            strengths_noted=["Mock strength"] if passed else [],
            detailed_feedback=f"Mock evaluation from {config.persona.value} judge",
        )

    def _aggregate_verdicts(
        self,
        verdicts: List[ParsedVerdict],
    ) -> AggregatedVerdict:
        """Combine individual verdicts into panel decision."""
        if not verdicts:
            return AggregatedVerdict(
                passed=False,
                consensus_level=0.0,
                aggregated_score=0.0,
                individual_verdicts=[],
                recommendation="No verdicts received",
            )

        # Calculate consensus
        pass_count = sum(1 for v in verdicts if v.passed)
        consensus_level = pass_count / len(verdicts)

        # Calculate weighted score
        total_weight = sum(
            self._get_weight_for_persona(v.persona) for v in verdicts
        )
        weighted_score = sum(
            v.score * self._get_weight_for_persona(v.persona)
            for v in verdicts
        ) / total_weight if total_weight > 0 else 0.0

        # Find critical issues (mentioned by multiple judges)
        issue_counts: Dict[str, int] = {}
        for v in verdicts:
            for issue in v.issues_found:
                issue_text = issue.get("issue", "").lower().strip()[:100]
                if issue_text:
                    issue_counts[issue_text] = issue_counts.get(issue_text, 0) + 1

        critical_issues = [
            issue for issue, count in issue_counts.items()
            if count >= len(verdicts) / 2
        ]

        # Determine pass/fail
        if self.require_unanimous_pass:
            passed = all(v.passed for v in verdicts)
        else:
            passed = consensus_level >= self.consensus_threshold

        # Record dissenting opinions
        majority_passed = passed
        dissenting = [
            f"{v.persona.value}: {'passed' if v.passed else 'failed'} (score: {v.score:.2f})"
            for v in verdicts
            if v.passed != majority_passed
        ]

        # Generate recommendation
        recommendation = self._generate_recommendation(
            verdicts, passed, critical_issues
        )

        return AggregatedVerdict(
            passed=passed,
            consensus_level=consensus_level,
            aggregated_score=weighted_score,
            individual_verdicts=verdicts,
            critical_issues=critical_issues,
            recommendation=recommendation,
            dissenting_opinions=dissenting,
        )

    def _get_weight_for_persona(self, persona: JudgePersona) -> float:
        """Get weight for a persona from configs."""
        for config in self.configs:
            if config.persona == persona:
                return config.weight
        return 1.0

    def _generate_recommendation(
        self,
        verdicts: List[ParsedVerdict],
        passed: bool,
        critical_issues: List[str],
    ) -> str:
        """Generate actionable recommendation from verdicts."""
        if passed and not critical_issues:
            return "Content approved. Minor improvements may be suggested in individual feedback."

        if passed and critical_issues:
            return f"Content conditionally approved. Address these issues: {'; '.join(critical_issues[:3])}"

        # Failed
        top_issues = []
        for v in verdicts:
            if not v.passed:
                for issue in v.issues_found[:2]:
                    issue_text = issue.get("issue", "")
                    if issue_text and issue_text not in top_issues:
                        top_issues.append(issue_text)

        if top_issues:
            return f"Revision required. Priority issues: {'; '.join(top_issues[:5])}"

        return "Revision required. See individual judge feedback for details."

    def get_stats(self) -> Dict[str, Any]:
        """Get panel statistics."""
        return {
            "evaluations_run": self.evaluations_run,
            "total_passes": self.total_passes,
            "total_escalations": self.total_escalations,
            "pass_rate": (
                self.total_passes / self.evaluations_run
                if self.evaluations_run > 0 else 0.0
            ),
            "escalation_rate": (
                self.total_escalations / self.evaluations_run
                if self.evaluations_run > 0 else 0.0
            ),
            "panel_size": len(self.configs),
            "consensus_threshold": self.consensus_threshold,
        }
