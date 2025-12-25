"""
Heterogeneous Judge Panel System.

Provides diversified judge agent configurations to reduce correlated
evaluation failures through varying prompts, temperature settings,
and evaluation frameworks.

Version: 2.6.0
"""

from .configurations import (
    JudgePersona,
    JudgeConfig,
    ADVERSARIAL_CONFIG,
    RUBRIC_CONFIG,
    DOMAIN_EXPERT_CONFIG,
    SKEPTIC_CONFIG,
    END_USER_CONFIG,
    get_default_panel_configs,
    get_config_by_persona,
)
from .panel import (
    JudgePanel,
    VerdictParser,
    EscalationHandler,
)

__all__ = [
    # Configurations
    "JudgePersona",
    "JudgeConfig",
    "ADVERSARIAL_CONFIG",
    "RUBRIC_CONFIG",
    "DOMAIN_EXPERT_CONFIG",
    "SKEPTIC_CONFIG",
    "END_USER_CONFIG",
    "get_default_panel_configs",
    "get_config_by_persona",
    # Panel
    "JudgePanel",
    "VerdictParser",
    "EscalationHandler",
]
