"""
Specification Language Module.

Provides a formal DSL for defining agent behavior constraints,
output validation, and runtime limits.

Version: 2.6.0

Example Usage:
    from src.specifications import (
        SpecificationCompiler,
        SpecificationEnforcedAgent,
        create_enforced_agent,
    )

    # Compile a specification
    compiler = SpecificationCompiler()
    spec = compiler.compile('''
        AGENT ResearchAgent:
            TIER: sonnet
            TOOLS: [WebSearch, Read, Write]

            OUTPUT MUST SATISFY:
                confidence IN RANGE [0.0, 1.0]
                sources IS NOT_EMPTY
                forall s in sources: s.url IS VALID_URL

            BEHAVIOR:
                PREFER primary sources OVER secondary sources
                NEVER make claims without citations
                ALWAYS include confidence scores

            LIMITS:
                max_tool_calls: 50
                timeout_seconds: 300
    ''')

    # Wrap an agent with specification enforcement
    enforced = SpecificationEnforcedAgent(my_agent, spec)
    result = await enforced.execute("Research AI safety")

    if all(r.valid for r in result.validation_results):
        print("Output valid:", result.output)
    else:
        print("Violations found")
"""

from .ast import (
    # Enums
    TierLevel,
    Comparator,
    TypeCheck,
    Quantifier,
    # Value types
    PathExpr,
    DateExpr,
    LiteralValue,
    # Constraint types
    Constraint,
    ComparisonConstraint,
    TypeConstraint,
    RangeConstraint,
    InListConstraint,
    NotConstraint,
    AndConstraint,
    OrConstraint,
    QuantifiedConstraint,
    ConditionalConstraint,
    # Condition types
    Condition,
    ComparisonCondition,
    TypeCondition,
    CountCondition,
    AnyCondition,
    AllCondition,
    AndCondition,
    OrCondition,
    NotCondition,
    # Behavior rules
    BehaviorRule,
    PreferRule,
    NeverRule,
    AlwaysRule,
    WhenRule,
    LimitDecl,
    # Top-level
    AgentSpecification,
)

from .parser import (
    SpecificationParser,
    ParseError,
)

from .validators import (
    ValidationResult,
    SpecificationViolation,
    ConstraintValidator,
    SpecificationValidator,
)

from .compiler import (
    CompiledSpecification,
    BehaviorPromptGenerator,
    SpecificationCompiler,
    SpecificationRegistry,
    get_default_registry,
    set_specs_directory,
)

from .agent import (
    AgentProtocol,
    ExecutionResult,
    LimitEnforcer,
    LimitExceededError,
    SpecificationEnforcedAgent,
    MockAgent,
    create_enforced_agent,
)

__all__ = [
    # Enums
    "TierLevel",
    "Comparator",
    "TypeCheck",
    "Quantifier",
    # Value types
    "PathExpr",
    "DateExpr",
    "LiteralValue",
    # Constraint types
    "Constraint",
    "ComparisonConstraint",
    "TypeConstraint",
    "RangeConstraint",
    "InListConstraint",
    "NotConstraint",
    "AndConstraint",
    "OrConstraint",
    "QuantifiedConstraint",
    "ConditionalConstraint",
    # Condition types
    "Condition",
    "ComparisonCondition",
    "TypeCondition",
    "CountCondition",
    "AnyCondition",
    "AllCondition",
    "AndCondition",
    "OrCondition",
    "NotCondition",
    # Behavior rules
    "BehaviorRule",
    "PreferRule",
    "NeverRule",
    "AlwaysRule",
    "WhenRule",
    "LimitDecl",
    # Top-level AST
    "AgentSpecification",
    # Parser
    "SpecificationParser",
    "ParseError",
    # Validators
    "ValidationResult",
    "SpecificationViolation",
    "ConstraintValidator",
    "SpecificationValidator",
    # Compiler
    "CompiledSpecification",
    "BehaviorPromptGenerator",
    "SpecificationCompiler",
    "SpecificationRegistry",
    "get_default_registry",
    "set_specs_directory",
    # Agent
    "AgentProtocol",
    "ExecutionResult",
    "LimitEnforcer",
    "LimitExceededError",
    "SpecificationEnforcedAgent",
    "MockAgent",
    "create_enforced_agent",
]

__version__ = "2.6.0"
