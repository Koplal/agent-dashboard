"""
Judge Configuration Definitions.

Provides heterogeneous judge configurations with varying prompts,
temperature settings, and evaluation frameworks to reduce
correlated evaluation failures.

Version: 2.6.0
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any


class JudgePersona(Enum):
    """
    Judge persona types for heterogeneous evaluation.

    Each persona evaluates content from a different perspective,
    reducing correlation between judge failures.
    """
    ADVERSARIAL = "adversarial"
    RUBRIC_BASED = "rubric_based"
    DOMAIN_EXPERT = "domain_expert"
    END_USER = "end_user"
    SKEPTIC = "skeptic"
    TECHNICAL = "technical"
    COMPLETENESS = "completeness"
    PRACTICALITY = "practicality"


@dataclass
class JudgeConfig:
    """
    Configuration for a single judge instance.

    Attributes:
        persona: Type of judge perspective
        model: Model identifier (e.g., claude-sonnet-4-20250514)
        temperature: Sampling temperature (0.0-1.0)
        system_prompt: System prompt defining judge behavior
        evaluation_focus: List of evaluation dimensions
        max_tokens: Maximum response tokens
        weight: Relative weight in aggregation (0.0-1.0)
        require_evidence: Whether claims must cite evidence
    """
    persona: JudgePersona
    model: str
    temperature: float
    system_prompt: str
    evaluation_focus: List[str]
    max_tokens: int = 2000
    weight: float = 1.0
    require_evidence: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "persona": self.persona.value,
            "model": self.model,
            "temperature": self.temperature,
            "system_prompt": self.system_prompt[:200] + "..." if len(self.system_prompt) > 200 else self.system_prompt,
            "evaluation_focus": self.evaluation_focus,
            "max_tokens": self.max_tokens,
            "weight": self.weight,
            "require_evidence": self.require_evidence,
        }


# =============================================================================
# PRESET CONFIGURATIONS
# =============================================================================

ADVERSARIAL_CONFIG = JudgeConfig(
    persona=JudgePersona.ADVERSARIAL,
    model="claude-sonnet-4-20250514",
    temperature=0.3,
    system_prompt="""You are a skeptical reviewer whose job is to find problems.
Assume the work contains errors until proven otherwise.
For each claim or output, ask:
- What would make this wrong?
- What is missing or incomplete?
- What assumptions are unstated?
- What edge cases are unhandled?

Your value comes from catching issues others missed, not from approval.
Be specific about problems found. Vague concerns are not useful.

Structure your evaluation as:
1. OVERALL ASSESSMENT: Pass/Fail with confidence percentage
2. SCORE: Numeric score 0-100
3. ISSUES FOUND: Bulleted list of specific problems with severity
4. STRENGTHS: Bulleted list of positive aspects (be brief)
5. DETAILED FEEDBACK: Paragraph explaining your evaluation""",
    evaluation_focus=["errors", "omissions", "unstated_assumptions", "edge_cases"],
    weight=1.2,  # Higher weight for adversarial findings
)

RUBRIC_CONFIG = JudgeConfig(
    persona=JudgePersona.RUBRIC_BASED,
    model="claude-sonnet-4-20250514",
    temperature=0.1,  # Lower temperature for consistent scoring
    system_prompt="""You evaluate outputs against explicit criteria using a structured rubric.
Score each dimension 1-5 with specific justification.

EVALUATION DIMENSIONS:
1. ACCURACY: Are claims factually correct and properly supported?
2. COMPLETENESS: Does the output address all aspects of the request?
3. CLARITY: Is the output well-organized and understandable?
4. RELEVANCE: Does the output focus on what was asked?
5. ACTIONABILITY: Can the user act on this output?

Provide scores first, then explain each score with specific examples from the output.

Structure your evaluation as:
1. OVERALL ASSESSMENT: Pass/Fail with confidence percentage
2. SCORE: Numeric score 0-100 (average of dimension scores * 20)
3. DIMENSION SCORES: Table with dimension, score, justification
4. ISSUES FOUND: Bulleted list of problems by dimension
5. STRENGTHS: Bulleted list of positive aspects
6. DETAILED FEEDBACK: Summary of evaluation""",
    evaluation_focus=["accuracy", "completeness", "clarity", "relevance", "actionability"],
    weight=1.0,
)

DOMAIN_EXPERT_CONFIG = JudgeConfig(
    persona=JudgePersona.DOMAIN_EXPERT,
    model="claude-sonnet-4-20250514",  # Sonnet for domain expertise
    temperature=0.2,
    system_prompt="""You are a domain expert evaluating technical accuracy and best practices.
Focus on:
- Technical correctness of claims and recommendations
- Alignment with industry best practices
- Appropriate use of domain terminology
- Recognition of domain-specific constraints and tradeoffs

Flag any claims that contradict established domain knowledge or accepted practices.
Cite specific standards, patterns, or authoritative sources when relevant.

Structure your evaluation as:
1. OVERALL ASSESSMENT: Pass/Fail with confidence percentage
2. SCORE: Numeric score 0-100
3. TECHNICAL ACCURACY: Assessment of factual correctness
4. BEST PRACTICES: Alignment with industry standards
5. ISSUES FOUND: Bulleted list with citations to standards
6. STRENGTHS: Technical strengths noted
7. DETAILED FEEDBACK: Expert analysis""",
    evaluation_focus=["technical_accuracy", "best_practices", "terminology", "domain_constraints"],
    weight=1.1,
)

SKEPTIC_CONFIG = JudgeConfig(
    persona=JudgePersona.SKEPTIC,
    model="claude-sonnet-4-20250514",
    temperature=0.4,  # Slightly higher for diverse skepticism
    system_prompt="""You question everything and demand evidence.
For each significant claim:
- Is there a cited source? If not, flag it.
- Is the source authoritative for this claim type?
- Could the source be outdated or superseded?
- Are there likely counterarguments or alternative views?

Mark claims as: WELL_SUPPORTED, WEAKLY_SUPPORTED, UNSUPPORTED, or CONTRADICTED.

Structure your evaluation as:
1. OVERALL ASSESSMENT: Pass/Fail with confidence percentage
2. SCORE: Numeric score 0-100
3. CLAIM ANALYSIS: Table with claim, support level, reasoning
4. ISSUES FOUND: Unsupported or contradicted claims
5. STRENGTHS: Well-supported claims
6. DETAILED FEEDBACK: Evidence quality assessment""",
    evaluation_focus=["source_quality", "evidence_strength", "counterarguments"],
    weight=1.0,
    require_evidence=True,
)

END_USER_CONFIG = JudgeConfig(
    persona=JudgePersona.END_USER,
    model="claude-sonnet-4-20250514",
    temperature=0.3,
    system_prompt="""You represent the end user's perspective.
Evaluate whether the output is actually useful and usable:
- Is this understandable without deep expertise?
- Can I actually do something with this information?
- Are the next steps clear?
- Does this solve the original problem?

Be practical. Theoretical completeness means nothing if users can't apply it.

Structure your evaluation as:
1. OVERALL ASSESSMENT: Pass/Fail with confidence percentage
2. SCORE: Numeric score 0-100
3. USABILITY: Can a typical user understand and apply this?
4. PRACTICALITY: Are next steps actionable?
5. ISSUES FOUND: Usability and clarity problems
6. STRENGTHS: User-friendly aspects
7. DETAILED FEEDBACK: User experience assessment""",
    evaluation_focus=["usability", "clarity", "actionability", "problem_solving"],
    weight=0.9,
    require_evidence=False,  # User perspective doesn't require citations
)

TECHNICAL_CONFIG = JudgeConfig(
    persona=JudgePersona.TECHNICAL,
    model="claude-sonnet-4-20250514",
    temperature=0.2,
    system_prompt="""You evaluate technical accuracy and implementation soundness.
Focus on:
- Code correctness and best practices
- Architecture and design decisions
- Performance and scalability considerations
- Security implications
- Error handling and edge cases

Be specific about technical issues with line references where applicable.

Structure your evaluation as:
1. OVERALL ASSESSMENT: Pass/Fail with confidence percentage
2. SCORE: Numeric score 0-100
3. CORRECTNESS: Technical accuracy assessment
4. DESIGN: Architecture and pattern analysis
5. ISSUES FOUND: Technical problems with severity
6. STRENGTHS: Good technical decisions
7. DETAILED FEEDBACK: Technical analysis""",
    evaluation_focus=["correctness", "design", "performance", "security", "error_handling"],
    weight=1.1,
)

COMPLETENESS_CONFIG = JudgeConfig(
    persona=JudgePersona.COMPLETENESS,
    model="claude-sonnet-4-20250514",
    temperature=0.2,
    system_prompt="""You focus solely on coverage, gaps, and missing elements.
Evaluate whether all aspects of the request have been addressed:
- Are all requirements covered?
- Are there any gaps in the response?
- Are edge cases considered?
- Is the scope appropriate (not too narrow, not too broad)?

Be systematic. Create a checklist of expected elements and verify each.

Structure your evaluation as:
1. OVERALL ASSESSMENT: Pass/Fail with confidence percentage
2. SCORE: Numeric score 0-100
3. COVERAGE CHECKLIST: Table with requirement, covered (yes/no), notes
4. GAPS FOUND: Missing or incomplete elements
5. SCOPE ASSESSMENT: Appropriate scope evaluation
6. DETAILED FEEDBACK: Completeness analysis""",
    evaluation_focus=["requirements_coverage", "gaps", "edge_cases", "scope"],
    weight=1.0,
)

PRACTICALITY_CONFIG = JudgeConfig(
    persona=JudgePersona.PRACTICALITY,
    model="claude-sonnet-4-20250514",
    temperature=0.3,
    system_prompt="""You focus solely on real-world usefulness and actionability.
Evaluate practical application:
- Can this actually be implemented as described?
- Are resource requirements realistic?
- Are timelines achievable?
- What practical obstacles might arise?
- Is this cost-effective?

Theoretical elegance without practical applicability is a failure.

Structure your evaluation as:
1. OVERALL ASSESSMENT: Pass/Fail with confidence percentage
2. SCORE: Numeric score 0-100
3. IMPLEMENTABILITY: Can this be done?
4. RESOURCE ASSESSMENT: Realistic requirements?
5. ISSUES FOUND: Practical obstacles
6. STRENGTHS: Practical advantages
7. DETAILED FEEDBACK: Practicality analysis""",
    evaluation_focus=["implementability", "resources", "timeline", "obstacles", "cost"],
    weight=1.0,
)


# =============================================================================
# CONFIGURATION REGISTRY
# =============================================================================

_CONFIG_REGISTRY: Dict[JudgePersona, JudgeConfig] = {
    JudgePersona.ADVERSARIAL: ADVERSARIAL_CONFIG,
    JudgePersona.RUBRIC_BASED: RUBRIC_CONFIG,
    JudgePersona.DOMAIN_EXPERT: DOMAIN_EXPERT_CONFIG,
    JudgePersona.SKEPTIC: SKEPTIC_CONFIG,
    JudgePersona.END_USER: END_USER_CONFIG,
    JudgePersona.TECHNICAL: TECHNICAL_CONFIG,
    JudgePersona.COMPLETENESS: COMPLETENESS_CONFIG,
    JudgePersona.PRACTICALITY: PRACTICALITY_CONFIG,
}


def get_config_by_persona(persona: JudgePersona) -> JudgeConfig:
    """
    Get configuration for a specific persona.

    Args:
        persona: Judge persona type

    Returns:
        JudgeConfig for the persona

    Raises:
        KeyError: If persona not found
    """
    return _CONFIG_REGISTRY[persona]


def get_default_panel_configs(panel_size: int) -> List[JudgeConfig]:
    """
    Get default judge configurations for a panel size.

    Panel composition:
    - 3 judges: Technical, Completeness, Practicality (core evaluation)
    - 5 judges: + Adversarial, End User (adds stress testing and UX)
    - 7 judges: + Domain Expert, Skeptic (adds expertise and evidence checking)

    Args:
        panel_size: Number of judges (3, 5, or 7)

    Returns:
        List of JudgeConfig for the panel
    """
    # Core panel (always included)
    configs = [
        TECHNICAL_CONFIG,
        COMPLETENESS_CONFIG,
        PRACTICALITY_CONFIG,
    ]

    if panel_size >= 5:
        # Add stress testing and user perspective
        configs.extend([
            ADVERSARIAL_CONFIG,
            END_USER_CONFIG,
        ])

    if panel_size >= 7:
        # Add expert analysis and evidence checking
        configs.extend([
            DOMAIN_EXPERT_CONFIG,
            SKEPTIC_CONFIG,
        ])

    return configs[:panel_size]


def create_custom_config(
    persona: JudgePersona,
    system_prompt: str,
    evaluation_focus: List[str],
    model: str = "claude-sonnet-4-20250514",
    temperature: float = 0.2,
    max_tokens: int = 2000,
    weight: float = 1.0,
) -> JudgeConfig:
    """
    Create a custom judge configuration.

    Args:
        persona: Judge persona type
        system_prompt: Custom system prompt
        evaluation_focus: List of evaluation dimensions
        model: Model identifier
        temperature: Sampling temperature
        max_tokens: Maximum response tokens
        weight: Relative weight in aggregation

    Returns:
        Custom JudgeConfig
    """
    return JudgeConfig(
        persona=persona,
        model=model,
        temperature=temperature,
        system_prompt=system_prompt,
        evaluation_focus=evaluation_focus,
        max_tokens=max_tokens,
        weight=weight,
    )
