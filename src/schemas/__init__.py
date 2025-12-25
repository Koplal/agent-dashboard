"""
Pydantic Schemas for Agent Output Validation.

Provides structured validation for all agent outputs using Pydantic models
with field-level constraints and cross-field validation.

Version: 2.6.0
"""

from .base import (
    ConfidenceLevel,
    VerificationStatus,
    BaseAgentOutput,
)
from .research import (
    SourceReference,
    ResearchClaim,
    ResearchOutput,
)
from .code_analysis import (
    CodeLocation,
    CodeIssue,
    CodeAnalysisOutput,
)
from .orchestration import (
    AgentSelection,
    DelegationDecision,
    OrchestrationOutput,
)
from .judge import (
    EvaluationScore,
    JudgeVerdict,
    PanelVerdict,
)

__all__ = [
    # Base
    "ConfidenceLevel",
    "VerificationStatus",
    "BaseAgentOutput",
    # Research
    "SourceReference",
    "ResearchClaim",
    "ResearchOutput",
    # Code Analysis
    "CodeLocation",
    "CodeIssue",
    "CodeAnalysisOutput",
    # Orchestration
    "AgentSelection",
    "DelegationDecision",
    "OrchestrationOutput",
    # Judge
    "EvaluationScore",
    "JudgeVerdict",
    "PanelVerdict",
]
