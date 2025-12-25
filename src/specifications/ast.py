"""
Specification AST Types.

Provides dataclasses for the abstract syntax tree of parsed specifications.

Version: 2.6.0
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, List, Optional, Union


class TierLevel(str, Enum):
    """Agent tier levels."""
    OPUS = "opus"
    SONNET = "sonnet"
    HAIKU = "haiku"


class Comparator(str, Enum):
    """Comparison operators."""
    EQ = "=="
    NE = "!="
    LT = "<"
    GT = ">"
    LE = "<="
    GE = ">="


class TypeCheck(str, Enum):
    """Type validation checks."""
    VALID_URL = "valid_url"
    VALID_EMAIL = "valid_email"
    VALID_DATE = "valid_date"
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    LIST = "list"
    OBJECT = "object"
    NOT_EMPTY = "not_empty"


class Quantifier(str, Enum):
    """Quantifiers for constraints."""
    FORALL = "forall"
    EXISTS = "exists"


# Value types
@dataclass
class PathExpr:
    """Path expression like 'output.claims.source.url'."""
    parts: List[str]

    def __str__(self) -> str:
        return ".".join(self.parts)

    def evaluate(self, data: Dict[str, Any]) -> Any:
        """Evaluate path against data dictionary."""
        result = data
        for part in self.parts:
            if isinstance(result, dict):
                result = result.get(part)
            elif isinstance(result, list) and part.isdigit():
                idx = int(part)
                result = result[idx] if idx < len(result) else None
            elif hasattr(result, part):
                result = getattr(result, part)
            else:
                return None
            if result is None:
                return None
        return result


@dataclass
class DateExpr:
    """Date expression like 'TODAY - 90 DAYS'."""
    base: str = "TODAY"
    offset_value: int = 0
    offset_unit: str = "DAYS"

    def evaluate(self) -> datetime:
        """Evaluate to actual datetime."""
        now = datetime.now()
        if self.offset_unit == "DAYS":
            delta = timedelta(days=self.offset_value)
        elif self.offset_unit == "HOURS":
            delta = timedelta(hours=self.offset_value)
        elif self.offset_unit == "MINUTES":
            delta = timedelta(minutes=self.offset_value)
        elif self.offset_unit == "SECONDS":
            delta = timedelta(seconds=self.offset_value)
        else:
            delta = timedelta()
        return now + delta


@dataclass
class LiteralValue:
    """Literal value (string, number, boolean, null)."""
    value: Any
    value_type: str = "unknown"

    @classmethod
    def from_parsed(cls, value: Any) -> "LiteralValue":
        """Create from parsed value."""
        if isinstance(value, str):
            # Remove quotes if present
            if (value.startswith('"') and value.endswith('"')) or \
               (value.startswith("'") and value.endswith("'")):
                return cls(value[1:-1], "string")
            if value == "TRUE":
                return cls(True, "boolean")
            if value == "FALSE":
                return cls(False, "boolean")
            if value == "NULL":
                return cls(None, "null")
            if value == "TODAY":
                return cls(DateExpr(), "date")
            # Try to parse as number
            try:
                if "." in value:
                    return cls(float(value), "number")
                else:
                    return cls(int(value), "number")
            except ValueError:
                pass
            return cls(value, "string")
        elif isinstance(value, (int, float)):
            return cls(value, "number")
        elif isinstance(value, DateExpr):
            return cls(value, "date")
        return cls(value, "unknown")


# Constraint types
@dataclass
class Constraint:
    """Base class for constraints."""
    pass


@dataclass
class ComparisonConstraint(Constraint):
    """Comparison constraint: path comparator value."""
    path: PathExpr
    comparator: Comparator
    value: Union[LiteralValue, PathExpr]


@dataclass
class TypeConstraint(Constraint):
    """Type check constraint: path IS type_check."""
    path: PathExpr
    type_check: TypeCheck


@dataclass
class RangeConstraint(Constraint):
    """Range constraint: path IN RANGE [min, max]."""
    path: PathExpr
    min_value: float
    max_value: float


@dataclass
class InListConstraint(Constraint):
    """List membership constraint: path IN [values]."""
    path: PathExpr
    values: List[LiteralValue]


@dataclass
class NotConstraint(Constraint):
    """Negation constraint: NOT constraint."""
    inner: Constraint


@dataclass
class AndConstraint(Constraint):
    """Conjunction constraint: constraint AND constraint."""
    left: Constraint
    right: Constraint


@dataclass
class OrConstraint(Constraint):
    """Disjunction constraint: constraint OR constraint."""
    left: Constraint
    right: Constraint


@dataclass
class QuantifiedConstraint(Constraint):
    """Quantified constraint: forall/exists x in path: constraint."""
    quantifier: Quantifier
    variable: str
    path: PathExpr
    inner: Constraint


@dataclass
class ConditionalConstraint(Constraint):
    """Conditional constraint: if condition: constraint."""
    condition: "Condition"
    consequence: Constraint


# Condition types
@dataclass
class Condition:
    """Base class for conditions."""
    pass


@dataclass
class ComparisonCondition(Condition):
    """Comparison condition: path comparator value."""
    path: PathExpr
    comparator: Comparator
    value: Union[LiteralValue, PathExpr]


@dataclass
class TypeCondition(Condition):
    """Type check condition: path IS type_check."""
    path: PathExpr
    type_check: TypeCheck


@dataclass
class CountCondition(Condition):
    """Count condition: count(path) comparator value."""
    path: PathExpr
    comparator: Comparator
    value: int


@dataclass
class AnyCondition(Condition):
    """Any predicate condition: any(predicate)."""
    predicate: Condition


@dataclass
class AllCondition(Condition):
    """All predicate condition: all(predicate)."""
    predicate: Condition


@dataclass
class AndCondition(Condition):
    """Conjunction condition."""
    left: Condition
    right: Condition


@dataclass
class OrCondition(Condition):
    """Disjunction condition."""
    left: Condition
    right: Condition


@dataclass
class NotCondition(Condition):
    """Negation condition."""
    inner: Condition


# Behavior rules
@dataclass
class BehaviorRule:
    """Base class for behavior rules."""
    pass


@dataclass
class PreferRule(BehaviorRule):
    """PREFER x OVER y rule."""
    preferred: str
    over: str


@dataclass
class NeverRule(BehaviorRule):
    """NEVER action rule."""
    action: str


@dataclass
class AlwaysRule(BehaviorRule):
    """ALWAYS action rule."""
    action: str


@dataclass
class WhenRule(BehaviorRule):
    """WHEN condition: action rule."""
    condition: Condition
    action: str


# Limit declaration
@dataclass
class LimitDecl:
    """Limit declaration: name: value."""
    name: str
    value: int


# Top-level specification
@dataclass
class AgentSpecification:
    """
    Complete agent specification.

    Attributes:
        agent_name: Name of the agent
        tier: Agent tier level
        tools: List of allowed tools
        output_constraints: Output validation constraints
        behavior_rules: Behavioral rules
        limits: Runtime limits
        raw_text: Original specification text
    """
    agent_name: str
    tier: TierLevel = TierLevel.SONNET
    tools: List[str] = field(default_factory=list)
    output_constraints: List[Constraint] = field(default_factory=list)
    behavior_rules: List[BehaviorRule] = field(default_factory=list)
    limits: Dict[str, int] = field(default_factory=dict)
    raw_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_name": self.agent_name,
            "tier": self.tier.value,
            "tools": self.tools,
            "output_constraints": len(self.output_constraints),
            "behavior_rules": len(self.behavior_rules),
            "limits": self.limits,
        }
