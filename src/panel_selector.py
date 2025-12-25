#!/usr/bin/env python3
"""
panel_selector.py - Automatic panel size selection for quality evaluation.

This module implements automatic panel sizing based on task characteristics,
ensuring appropriate scrutiny for high-stakes decisions.

Scoring Heuristic:
| Factor | Values | Score |
|--------|--------|-------|
| Reversibility | reversible=0, irreversible=4 | 0-4 |
| Blast Radius | internal=0, team=1, org=2, external=3 | 0-3 |
| Domain | business=1, software=1, hardware=2, mixed=2 | 1-2 |
| Impact | low=0, medium=1, high=2, critical=4 | 0-4 |

Score to Panel:
| Score | Panel Size |
|-------|------------|
| 0-3   | 3 judges   |
| 4-7   | 5 judges   |
| 8+    | 7 judges   |

Override Rules: User can escalate only (not downgrade)

Dependencies:
    - sqlite3: Audit database persistence (optional)

Version: 2.6.0
"""

import json
import logging
import sqlite3
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS
# ============================================================================

class Reversibility(Enum):
    """Reversibility of an action."""
    REVERSIBLE = "reversible"
    IRREVERSIBLE = "irreversible"


class BlastRadius(Enum):
    """Scope of impact."""
    INTERNAL = "internal"   # Affects only local system
    TEAM = "team"           # Affects team members
    ORG = "org"             # Affects organization
    EXTERNAL = "external"   # Affects external users/systems


class Domain(Enum):
    """Domain type."""
    BUSINESS = "business"
    SOFTWARE = "software"
    HARDWARE = "hardware"
    MIXED = "mixed"


class Impact(Enum):
    """Impact level."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ============================================================================
# SCORING CONSTANTS
# ============================================================================

REVERSIBILITY_SCORES = {
    Reversibility.REVERSIBLE: 0,
    Reversibility.IRREVERSIBLE: 4,
}

BLAST_RADIUS_SCORES = {
    BlastRadius.INTERNAL: 0,
    BlastRadius.TEAM: 1,
    BlastRadius.ORG: 2,
    BlastRadius.EXTERNAL: 3,
}

DOMAIN_SCORES = {
    Domain.BUSINESS: 1,
    Domain.SOFTWARE: 1,
    Domain.HARDWARE: 2,
    Domain.MIXED: 2,
}

IMPACT_SCORES = {
    Impact.LOW: 0,
    Impact.MEDIUM: 1,
    Impact.HIGH: 2,
    Impact.CRITICAL: 4,
}

# Score thresholds for panel sizes
PANEL_THRESHOLDS = [
    (8, 7),   # Score >= 8 -> 7 judges
    (4, 5),   # Score >= 4 -> 5 judges
    (0, 3),   # Score >= 0 -> 3 judges
]


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class TaskMetadata:
    """
    Metadata about a task for panel size calculation.

    Attributes:
        reversible: Whether the action can be undone
        blast_radius: Scope of impact
        domain: Domain type
        estimated_impact: Impact level
        user_override: Optional user-specified panel size (escalation only)
        explicit: Whether metadata was explicitly provided vs inferred
    """
    reversible: bool = True
    blast_radius: str = "internal"
    domain: str = "software"
    estimated_impact: str = "medium"
    user_override: Optional[int] = None
    explicit: bool = False
    keywords: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reversible": self.reversible,
            "blast_radius": self.blast_radius,
            "domain": self.domain,
            "estimated_impact": self.estimated_impact,
            "user_override": self.user_override,
            "explicit": self.explicit,
            "keywords": self.keywords,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskMetadata":
        return cls(
            reversible=data.get("reversible", True),
            blast_radius=data.get("blast_radius", "internal"),
            domain=data.get("domain", "software"),
            estimated_impact=data.get("estimated_impact", "medium"),
            user_override=data.get("user_override"),
            explicit=data.get("explicit", False),
            keywords=data.get("keywords", []),
        )


@dataclass
class ScoreBreakdown:
    """Detailed score breakdown for audit purposes."""
    reversibility: int = 0
    blast_radius: int = 0
    domain: int = 0
    impact: int = 0
    total: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reversibility": self.reversibility,
            "blast_radius": self.blast_radius,
            "domain": self.domain,
            "impact": self.impact,
            "total": self.total,
        }


@dataclass
class PanelSelection:
    """
    Complete panel selection result.

    Includes panel size, score breakdown, and audit information.
    """
    task_id: str
    description: str
    panel_size: int
    calculated_size: int
    score: int
    score_breakdown: ScoreBreakdown
    metadata: TaskMetadata
    override_applied: bool = False
    override_attempted: bool = False
    override_blocked: bool = False
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "description": self.description,
            "panel_size": self.panel_size,
            "calculated_size": self.calculated_size,
            "score": self.score,
            "score_breakdown": self.score_breakdown.to_dict(),
            "metadata": self.metadata.to_dict(),
            "override_applied": self.override_applied,
            "override_attempted": self.override_attempted,
            "override_blocked": self.override_blocked,
            "timestamp": self.timestamp.isoformat(),
        }


# ============================================================================
# PANEL SIZE SELECTOR
# ============================================================================

class PanelSizeSelector:
    """
    Automatically selects appropriate panel size based on task characteristics.

    The selector uses a scoring heuristic based on:
    - Reversibility: Can the action be undone?
    - Blast Radius: How many people/systems are affected?
    - Domain: What type of work is this?
    - Impact: How significant is the potential impact?

    Override Rules:
    - Users can ONLY escalate (request larger panel)
    - Users CANNOT downgrade (request smaller panel than calculated)
    - All overrides are logged for audit

    Usage:
        selector = PanelSizeSelector()
        metadata = TaskMetadata(reversible=False, blast_radius="external")
        selection = selector.select("task-1", "Deploy to production", metadata)
        print(f"Panel size: {selection.panel_size}")
    """

    def __init__(
        self,
        thresholds: Optional[List[Tuple[int, int]]] = None,
        db_path: Optional[str] = None
    ):
        """
        Initialize the panel size selector.

        Args:
            thresholds: Optional custom thresholds [(score, panel_size), ...]
            db_path: Optional path to SQLite audit database
        """
        self.thresholds = thresholds or PANEL_THRESHOLDS.copy()
        self.db_path = Path(db_path).expanduser() if db_path else None
        self.selection_log: List[PanelSelection] = []

        if self.db_path:
            self._init_db()

    def _init_db(self) -> None:
        """Initialize audit database."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS panel_selections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    description TEXT,
                    panel_size INTEGER NOT NULL,
                    calculated_size INTEGER NOT NULL,
                    score INTEGER NOT NULL,
                    score_breakdown TEXT,
                    metadata TEXT,
                    override_applied INTEGER DEFAULT 0,
                    override_attempted INTEGER DEFAULT 0,
                    override_blocked INTEGER DEFAULT 0,
                    timestamp TEXT NOT NULL
                )
            """)
            conn.commit()

    def calculate_score(self, metadata: TaskMetadata) -> Tuple[int, ScoreBreakdown]:
        """
        Calculate risk score from task metadata.

        Args:
            metadata: Task metadata

        Returns:
            Tuple of (total_score, breakdown)
        """
        breakdown = ScoreBreakdown()

        # Reversibility score
        breakdown.reversibility = 0 if metadata.reversible else 4

        # Blast radius score
        blast_map = {"internal": 0, "team": 1, "org": 2, "external": 3}
        breakdown.blast_radius = blast_map.get(metadata.blast_radius, 1)

        # Domain score
        domain_map = {"business": 1, "software": 1, "hardware": 2, "mixed": 2}
        breakdown.domain = domain_map.get(metadata.domain, 1)

        # Impact score
        impact_map = {"low": 0, "medium": 1, "high": 2, "critical": 4}
        breakdown.impact = impact_map.get(metadata.estimated_impact, 1)

        # Calculate total
        breakdown.total = (
            breakdown.reversibility +
            breakdown.blast_radius +
            breakdown.domain +
            breakdown.impact
        )

        return breakdown.total, breakdown

    def score_to_panel_size(self, score: int) -> int:
        """
        Convert score to panel size using thresholds.

        Args:
            score: Risk score

        Returns:
            Panel size (3, 5, or 7)
        """
        for threshold, size in sorted(self.thresholds, reverse=True):
            if score >= threshold:
                return size
        return 3  # Default to smallest panel

    def apply_override(
        self,
        calculated: int,
        requested: Optional[int]
    ) -> Tuple[int, bool, bool]:
        """
        Apply user override with escalation-only rule.

        Args:
            calculated: Calculated panel size
            requested: User-requested panel size

        Returns:
            Tuple of (final_size, override_applied, override_blocked)
        """
        if requested is None:
            return calculated, False, False

        if requested > calculated:
            # Escalation allowed
            logger.info(f"Override applied: {calculated} -> {requested}")
            return requested, True, False
        elif requested < calculated:
            # Downgrade blocked
            logger.warning(f"Override blocked: {calculated} cannot be reduced to {requested}")
            return calculated, False, True
        else:
            return calculated, False, False

    def select(
        self,
        task_id: str,
        description: str,
        metadata: TaskMetadata
    ) -> PanelSelection:
        """
        Select panel size for a task.

        Args:
            task_id: Task identifier
            description: Task description
            metadata: Task metadata

        Returns:
            PanelSelection with panel size and audit info
        """
        # Calculate score
        score, breakdown = self.calculate_score(metadata)

        # Determine panel size
        calculated_size = self.score_to_panel_size(score)

        # Apply any override
        final_size, override_applied, override_blocked = self.apply_override(
            calculated_size,
            metadata.user_override
        )

        # Create selection record
        selection = PanelSelection(
            task_id=task_id,
            description=description,
            panel_size=final_size,
            calculated_size=calculated_size,
            score=score,
            score_breakdown=breakdown,
            metadata=metadata,
            override_applied=override_applied,
            override_attempted=metadata.user_override is not None,
            override_blocked=override_blocked,
        )

        # Log selection
        self._log_selection(selection)

        return selection

    def _log_selection(self, selection: PanelSelection) -> None:
        """Log selection to memory and optionally database."""
        self.selection_log.append(selection)

        if self.db_path:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO panel_selections
                        (task_id, description, panel_size, calculated_size, score,
                         score_breakdown, metadata, override_applied, override_attempted,
                         override_blocked, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        selection.task_id,
                        selection.description,
                        selection.panel_size,
                        selection.calculated_size,
                        selection.score,
                        json.dumps(selection.score_breakdown.to_dict()),
                        json.dumps(selection.metadata.to_dict()),
                        int(selection.override_applied),
                        int(selection.override_attempted),
                        int(selection.override_blocked),
                        selection.timestamp.isoformat(),
                    ))
                    conn.commit()
            except Exception as e:
                logger.error(f"Failed to log selection to database: {e}")

    def get_selection_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent selection history."""
        return [s.to_dict() for s in self.selection_log[-limit:]]


# ============================================================================
# METADATA INFERRER
# ============================================================================

class MetadataInferrer:
    """
    Infers task metadata from description using keyword analysis.

    This provides reasonable defaults when explicit metadata is not available.
    """

    # Keyword mappings for inference
    IRREVERSIBLE_KEYWORDS = [
        "delete", "remove", "drop", "destroy", "terminate", "kill",
        "deploy", "publish", "release", "production", "prod",
        "migrate", "migration", "permanent", "irreversible",
    ]

    EXTERNAL_KEYWORDS = [
        "customer", "user", "public", "external", "api",
        "production", "prod", "live", "publish", "release",
    ]

    ORG_KEYWORDS = [
        "company", "organization", "org-wide", "enterprise",
        "global", "all-teams", "infrastructure",
    ]

    TEAM_KEYWORDS = [
        "team", "shared", "service", "internal-api", "database",
    ]

    CRITICAL_KEYWORDS = [
        "security", "critical", "urgent", "emergency", "breach",
        "vulnerability", "pii", "payment", "financial", "compliance",
    ]

    HIGH_IMPACT_KEYWORDS = [
        "production", "deploy", "release", "major", "breaking",
        "migration", "database", "infrastructure",
    ]

    HARDWARE_KEYWORDS = [
        "hardware", "physical", "device", "firmware", "embedded",
        "network", "server", "rack", "datacenter",
    ]

    def infer(self, description: str) -> TaskMetadata:
        """
        Infer metadata from task description.

        Args:
            description: Task description text

        Returns:
            TaskMetadata with inferred values
        """
        desc_lower = description.lower()
        keywords_found = []

        # Infer reversibility
        reversible = True
        for kw in self.IRREVERSIBLE_KEYWORDS:
            if kw in desc_lower:
                reversible = False
                keywords_found.append(kw)
                break

        # Infer blast radius
        blast_radius = "internal"
        for kw in self.EXTERNAL_KEYWORDS:
            if kw in desc_lower:
                blast_radius = "external"
                keywords_found.append(kw)
                break
        if blast_radius == "internal":
            for kw in self.ORG_KEYWORDS:
                if kw in desc_lower:
                    blast_radius = "org"
                    keywords_found.append(kw)
                    break
        if blast_radius == "internal":
            for kw in self.TEAM_KEYWORDS:
                if kw in desc_lower:
                    blast_radius = "team"
                    keywords_found.append(kw)
                    break

        # Infer impact
        impact = "medium"
        for kw in self.CRITICAL_KEYWORDS:
            if kw in desc_lower:
                impact = "critical"
                keywords_found.append(kw)
                break
        if impact == "medium":
            for kw in self.HIGH_IMPACT_KEYWORDS:
                if kw in desc_lower:
                    impact = "high"
                    keywords_found.append(kw)
                    break

        # Infer domain
        domain = "software"
        for kw in self.HARDWARE_KEYWORDS:
            if kw in desc_lower:
                domain = "hardware"
                keywords_found.append(kw)
                break

        return TaskMetadata(
            reversible=reversible,
            blast_radius=blast_radius,
            domain=domain,
            estimated_impact=impact,
            explicit=False,
            keywords=keywords_found,
        )


# ============================================================================
# PANEL JUDGES
# ============================================================================

# Judge types for different panel sizes
PANEL_3_JUDGES = ["judge-technical", "judge-completeness", "judge-practicality"]
PANEL_5_JUDGES = PANEL_3_JUDGES + ["judge-adversarial", "judge-user"]
PANEL_7_JUDGES = PANEL_5_JUDGES + ["judge-domain-expert", "judge-risk"]


def get_judges_for_panel(panel_size: int) -> List[str]:
    """
    Get list of judges for a given panel size.

    Args:
        panel_size: Panel size (3, 5, or 7)

    Returns:
        List of judge agent names
    """
    if panel_size >= 7:
        return PANEL_7_JUDGES.copy()
    elif panel_size >= 5:
        return PANEL_5_JUDGES.copy()
    else:
        return PANEL_3_JUDGES.copy()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def quick_select_panel(
    description: str,
    user_override: Optional[int] = None
) -> PanelSelection:
    """
    Quick panel selection with automatic inference.

    Args:
        description: Task description
        user_override: Optional user override

    Returns:
        PanelSelection result
    """
    inferrer = MetadataInferrer()
    metadata = inferrer.infer(description)
    metadata.user_override = user_override

    selector = PanelSizeSelector()
    task_id = f"quick-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    return selector.select(task_id, description, metadata)


def format_panel_selection(selection: PanelSelection) -> str:
    """
    Format panel selection for display.

    Args:
        selection: PanelSelection to format

    Returns:
        Formatted string
    """
    lines = [
        f"## Panel Selection: {selection.task_id}",
        "",
        f"**Task:** {selection.description}",
        f"**Panel Size:** {selection.panel_size} judges",
        f"**Risk Score:** {selection.score}",
        "",
        "### Score Breakdown",
        f"- Reversibility: {selection.score_breakdown.reversibility}",
        f"- Blast Radius: {selection.score_breakdown.blast_radius}",
        f"- Domain: {selection.score_breakdown.domain}",
        f"- Impact: {selection.score_breakdown.impact}",
        f"- **Total:** {selection.score_breakdown.total}",
    ]

    if selection.override_applied:
        lines.extend([
            "",
            f"**Note:** User override applied (escalated from {selection.calculated_size})"
        ])
    elif selection.override_blocked:
        lines.extend([
            "",
            f"**Note:** User override blocked (cannot downgrade from {selection.calculated_size})"
        ])

    judges = get_judges_for_panel(selection.panel_size)
    lines.extend([
        "",
        "### Panel Judges",
        *[f"- {j}" for j in judges]
    ])

    return "\n".join(lines)


# ============================================================================
# INTEGRATION WITH HETEROGENEOUS JUDGES
# ============================================================================

def create_judge_panel_from_selection(
    selection: PanelSelection,
    api_client: Optional[Any] = None,
) -> "JudgePanel":
    """
    Create a JudgePanel from a PanelSelection.

    Bridges the panel size selection with the heterogeneous
    judge configuration system.

    Args:
        selection: PanelSelection with determined panel size
        api_client: Optional API client for LLM calls

    Returns:
        Configured JudgePanel instance
    """
    from .judges import JudgePanel, get_default_panel_configs

    configs = get_default_panel_configs(selection.panel_size)

    return JudgePanel(
        configs=configs,
        api_client=api_client,
        consensus_threshold=0.7 if selection.score < 8 else 0.8,
    )


async def evaluate_with_panel(
    content: str,
    description: str,
    context: Optional[Dict[str, Any]] = None,
    content_type: str = "research",
    api_client: Optional[Any] = None,
    user_override: Optional[int] = None,
) -> Tuple[PanelSelection, "AggregatedVerdict"]:
    """
    Complete evaluation workflow: select panel size and run evaluation.

    Args:
        content: Content to evaluate
        description: Task description for panel sizing
        context: Additional context for judges
        content_type: Type of content being evaluated
        api_client: Optional API client for LLM calls
        user_override: Optional user-specified panel size

    Returns:
        Tuple of (PanelSelection, AggregatedVerdict)

    Example:
        selection, verdict = await evaluate_with_panel(
            content="Research findings...",
            description="Critical security analysis",
            content_type="research"
        )
        print(f"Panel: {selection.panel_size} judges")
        print(f"Result: {'PASS' if verdict.passed else 'FAIL'}")
    """
    from .judges import JudgePanel, AggregatedVerdict

    # Select panel size based on task
    selection = quick_select_panel(description, user_override)

    # Create and run panel
    panel = create_judge_panel_from_selection(selection, api_client)

    context = context or {}
    context["original_request"] = description
    context["panel_size"] = selection.panel_size
    context["risk_score"] = selection.score

    verdict = await panel.evaluate(
        content=content,
        context=context,
        content_type=content_type,
        task_id=selection.task_id,
    )

    return selection, verdict


async def evaluate_with_symbolic_verification(
    content: str,
    description: str,
    claims: Optional[List[str]] = None,
    context: Optional[Dict[str, Any]] = None,
    content_type: str = "research",
    api_client: Optional[Any] = None,
) -> Tuple[PanelSelection, "AggregatedVerdict", "VerificationReport"]:
    """
    Complete evaluation with both judge panel and symbolic verification.

    Runs symbolic verification on applicable claims, then uses
    judge panel for quality assessment.

    Args:
        content: Content to evaluate
        description: Task description for panel sizing
        claims: Pre-extracted claims (optional)
        context: Additional context
        content_type: Type of content
        api_client: Optional API client

    Returns:
        Tuple of (PanelSelection, AggregatedVerdict, VerificationReport)

    Example:
        selection, verdict, verification = await evaluate_with_symbolic_verification(
            content="Budget: $50,000. Spent: $42,000. Remaining: $8,000.",
            description="Financial report review"
        )
        if verification.has_refuted:
            print("Arithmetic errors found!")
        if verdict.passed:
            print("Quality approved by panel")
    """
    from .judges import JudgePanel, AggregatedVerdict
    from .verification import HybridVerifier, VerificationReport

    # Run symbolic verification first
    hybrid_verifier = HybridVerifier()
    verification_report = await hybrid_verifier.verify_content(
        content=content,
        context=context or {},
        claims=claims,
    )

    # Select panel size based on task
    selection = quick_select_panel(description)

    # Enhance context with verification results
    enhanced_context = context.copy() if context else {}
    enhanced_context["original_request"] = description
    enhanced_context["symbolic_verification"] = {
        "verified_count": len(verification_report.verified_claims),
        "refuted_count": len(verification_report.refuted_claims),
        "uncertain_count": len(verification_report.uncertain_claims),
    }

    # If symbolic verification found refuted claims, note it
    if verification_report.has_refuted:
        enhanced_context["pre_verification_issues"] = [
            c.output.explanation if hasattr(c.output, 'explanation') else str(c.output)
            for c in verification_report.refuted_claims
        ]

    # Create and run panel
    panel = create_judge_panel_from_selection(selection, api_client)

    verdict = await panel.evaluate(
        content=content,
        context=enhanced_context,
        content_type=content_type,
        task_id=selection.task_id,
    )

    return selection, verdict, verification_report
