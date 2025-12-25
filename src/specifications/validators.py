"""
Specification Validators.

Provides runtime validation of constraints against agent outputs.

Version: 2.6.0
"""

import re
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from urllib.parse import urlparse

from .ast import (
    AgentSpecification,
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
    Condition,
    ComparisonCondition,
    TypeCondition,
    CountCondition,
    PathExpr,
    Comparator,
    TypeCheck,
    Quantifier,
    LiteralValue,
    DateExpr,
)

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """
    Result of validating a constraint.

    Attributes:
        valid: Whether validation passed
        constraint: The constraint that was checked
        path: Path that was validated
        errors: List of error messages
        value: The actual value that was checked
    """
    valid: bool
    constraint: Optional[str] = None
    path: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    value: Any = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "valid": self.valid,
            "constraint": self.constraint,
            "path": self.path,
            "errors": self.errors,
            "value": str(self.value) if self.value is not None else None,
        }


@dataclass
class SpecificationViolation(Exception):
    """Exception raised when a specification is violated."""
    spec_name: str
    violations: List[ValidationResult]

    def __str__(self) -> str:
        errors = []
        for v in self.violations:
            if v.errors:
                errors.extend(v.errors)
        return f"Specification '{self.spec_name}' violated: {'; '.join(errors)}"


class ConstraintValidator:
    """
    Validates constraints against data.

    Supports all constraint types from the specification language.
    """

    def __init__(self):
        """Initialize the validator."""
        self.type_validators: Dict[TypeCheck, Callable[[Any], bool]] = {
            TypeCheck.VALID_URL: self._is_valid_url,
            TypeCheck.VALID_EMAIL: self._is_valid_email,
            TypeCheck.VALID_DATE: self._is_valid_date,
            TypeCheck.STRING: lambda x: isinstance(x, str),
            TypeCheck.NUMBER: lambda x: isinstance(x, (int, float)),
            TypeCheck.BOOLEAN: lambda x: isinstance(x, bool),
            TypeCheck.LIST: lambda x: isinstance(x, list),
            TypeCheck.OBJECT: lambda x: isinstance(x, dict),
            TypeCheck.NOT_EMPTY: self._is_not_empty,
        }

    def validate(
        self,
        constraint: Constraint,
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        """
        Validate a constraint against data.

        Args:
            constraint: The constraint to validate
            data: Data to validate against
            context: Additional context (variables, etc.)

        Returns:
            ValidationResult indicating success or failure
        """
        context = context or {}

        if isinstance(constraint, ComparisonConstraint):
            return self._validate_comparison(constraint, data, context)
        elif isinstance(constraint, TypeConstraint):
            return self._validate_type(constraint, data, context)
        elif isinstance(constraint, RangeConstraint):
            return self._validate_range(constraint, data, context)
        elif isinstance(constraint, InListConstraint):
            return self._validate_in_list(constraint, data, context)
        elif isinstance(constraint, NotConstraint):
            return self._validate_not(constraint, data, context)
        elif isinstance(constraint, AndConstraint):
            return self._validate_and(constraint, data, context)
        elif isinstance(constraint, OrConstraint):
            return self._validate_or(constraint, data, context)
        elif isinstance(constraint, QuantifiedConstraint):
            return self._validate_quantified(constraint, data, context)
        elif isinstance(constraint, ConditionalConstraint):
            return self._validate_conditional(constraint, data, context)
        else:
            return ValidationResult(
                valid=False,
                errors=[f"Unknown constraint type: {type(constraint).__name__}"]
            )

    def validate_all(
        self,
        constraints: List[Constraint],
        data: Dict[str, Any],
    ) -> List[ValidationResult]:
        """Validate all constraints against data."""
        return [self.validate(c, data) for c in constraints]

    def _validate_comparison(
        self,
        constraint: ComparisonConstraint,
        data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> ValidationResult:
        """Validate comparison constraint."""
        actual = self._resolve_path(constraint.path, data, context)
        expected = self._resolve_value(constraint.value, data, context)

        if actual is None:
            return ValidationResult(
                valid=False,
                constraint="comparison",
                path=str(constraint.path),
                errors=[f"Path '{constraint.path}' not found in data"],
            )

        try:
            result = self._compare(actual, constraint.comparator, expected)
            if result:
                return ValidationResult(valid=True, path=str(constraint.path), value=actual)
            else:
                return ValidationResult(
                    valid=False,
                    constraint="comparison",
                    path=str(constraint.path),
                    errors=[f"Expected {constraint.path} {constraint.comparator.value} {expected}, got {actual}"],
                    value=actual,
                )
        except Exception as e:
            return ValidationResult(
                valid=False,
                constraint="comparison",
                path=str(constraint.path),
                errors=[f"Comparison failed: {str(e)}"],
            )

    def _validate_type(
        self,
        constraint: TypeConstraint,
        data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> ValidationResult:
        """Validate type constraint."""
        actual = self._resolve_path(constraint.path, data, context)

        if actual is None and constraint.type_check != TypeCheck.NOT_EMPTY:
            return ValidationResult(
                valid=False,
                constraint="type",
                path=str(constraint.path),
                errors=[f"Path '{constraint.path}' not found"],
            )

        validator = self.type_validators.get(constraint.type_check)
        if validator and validator(actual):
            return ValidationResult(valid=True, path=str(constraint.path), value=actual)
        else:
            return ValidationResult(
                valid=False,
                constraint="type",
                path=str(constraint.path),
                errors=[f"Expected {constraint.path} IS {constraint.type_check.value}, got type {type(actual).__name__}"],
                value=actual,
            )

    def _validate_range(
        self,
        constraint: RangeConstraint,
        data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> ValidationResult:
        """Validate range constraint."""
        actual = self._resolve_path(constraint.path, data, context)

        if actual is None:
            return ValidationResult(
                valid=False,
                constraint="range",
                path=str(constraint.path),
                errors=[f"Path '{constraint.path}' not found"],
            )

        try:
            num_val = float(actual)
            if constraint.min_value <= num_val <= constraint.max_value:
                return ValidationResult(valid=True, path=str(constraint.path), value=actual)
            else:
                return ValidationResult(
                    valid=False,
                    constraint="range",
                    path=str(constraint.path),
                    errors=[f"Expected {constraint.path} in [{constraint.min_value}, {constraint.max_value}], got {num_val}"],
                    value=actual,
                )
        except (TypeError, ValueError) as e:
            return ValidationResult(
                valid=False,
                constraint="range",
                path=str(constraint.path),
                errors=[f"Cannot convert to number: {e}"],
                value=actual,
            )

    def _validate_in_list(
        self,
        constraint: InListConstraint,
        data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> ValidationResult:
        """Validate in-list constraint."""
        actual = self._resolve_path(constraint.path, data, context)

        if actual is None:
            return ValidationResult(
                valid=False,
                constraint="in_list",
                path=str(constraint.path),
                errors=[f"Path '{constraint.path}' not found"],
            )

        allowed = [v.value for v in constraint.values]
        if actual in allowed:
            return ValidationResult(valid=True, path=str(constraint.path), value=actual)
        else:
            return ValidationResult(
                valid=False,
                constraint="in_list",
                path=str(constraint.path),
                errors=[f"Expected {constraint.path} in {allowed}, got {actual}"],
                value=actual,
            )

    def _validate_not(
        self,
        constraint: NotConstraint,
        data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> ValidationResult:
        """Validate NOT constraint."""
        inner_result = self.validate(constraint.inner, data, context)
        if not inner_result.valid:
            return ValidationResult(valid=True)
        else:
            return ValidationResult(
                valid=False,
                constraint="not",
                errors=["NOT constraint failed - inner constraint was satisfied"],
            )

    def _validate_and(
        self,
        constraint: AndConstraint,
        data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> ValidationResult:
        """Validate AND constraint."""
        left_result = self.validate(constraint.left, data, context)
        right_result = self.validate(constraint.right, data, context)

        if left_result.valid and right_result.valid:
            return ValidationResult(valid=True)
        else:
            errors = left_result.errors + right_result.errors
            return ValidationResult(
                valid=False,
                constraint="and",
                errors=errors or ["AND constraint failed"],
            )

    def _validate_or(
        self,
        constraint: OrConstraint,
        data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> ValidationResult:
        """Validate OR constraint."""
        left_result = self.validate(constraint.left, data, context)
        if left_result.valid:
            return ValidationResult(valid=True)

        right_result = self.validate(constraint.right, data, context)
        if right_result.valid:
            return ValidationResult(valid=True)

        return ValidationResult(
            valid=False,
            constraint="or",
            errors=left_result.errors + right_result.errors,
        )

    def _validate_quantified(
        self,
        constraint: QuantifiedConstraint,
        data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> ValidationResult:
        """Validate quantified constraint (forall/exists)."""
        collection = self._resolve_path(constraint.path, data, context)

        if not isinstance(collection, (list, tuple)):
            if collection is None:
                collection = []
            else:
                collection = [collection]

        if constraint.quantifier == Quantifier.FORALL:
            # All items must satisfy the constraint
            for i, item in enumerate(collection):
                item_context = {**context, constraint.variable: item}
                result = self.validate(constraint.inner, data, item_context)
                if not result.valid:
                    result.errors.insert(0, f"forall failed at index {i}")
                    return result
            return ValidationResult(valid=True)

        elif constraint.quantifier == Quantifier.EXISTS:
            # At least one item must satisfy the constraint
            for item in collection:
                item_context = {**context, constraint.variable: item}
                result = self.validate(constraint.inner, data, item_context)
                if result.valid:
                    return ValidationResult(valid=True)
            return ValidationResult(
                valid=False,
                constraint="exists",
                path=str(constraint.path),
                errors=[f"No item in {constraint.path} satisfies the constraint"],
            )

        return ValidationResult(valid=True)

    def _validate_conditional(
        self,
        constraint: ConditionalConstraint,
        data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> ValidationResult:
        """Validate conditional constraint."""
        condition_met = self._evaluate_condition(constraint.condition, data, context)

        if not condition_met:
            # Condition not met, constraint doesn't apply
            return ValidationResult(valid=True)

        # Condition met, check consequence
        return self.validate(constraint.consequence, data, context)

    def _evaluate_condition(
        self,
        condition: Condition,
        data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> bool:
        """Evaluate a condition."""
        if isinstance(condition, ComparisonCondition):
            actual = self._resolve_path(condition.path, data, context)
            expected = self._resolve_value(condition.value, data, context)
            return self._compare(actual, condition.comparator, expected)

        elif isinstance(condition, TypeCondition):
            actual = self._resolve_path(condition.path, data, context)
            validator = self.type_validators.get(condition.type_check)
            return validator(actual) if validator else False

        elif isinstance(condition, CountCondition):
            collection = self._resolve_path(condition.path, data, context)
            count = len(collection) if isinstance(collection, (list, tuple)) else 0
            return self._compare(count, condition.comparator, condition.value)

        return False

    def _resolve_path(
        self,
        path: PathExpr,
        data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        """Resolve a path expression to a value."""
        # Check context first (for quantifier variables)
        if path.parts[0] in context:
            if len(path.parts) == 1:
                return context[path.parts[0]]
            # Continue resolving from context value
            value = context[path.parts[0]]
            for part in path.parts[1:]:
                if isinstance(value, dict):
                    value = value.get(part)
                elif hasattr(value, part):
                    value = getattr(value, part)
                else:
                    return None
            return value

        # Resolve from data
        return path.evaluate(data)

    def _resolve_value(
        self,
        value: Any,
        data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        """Resolve a value (literal or path)."""
        if isinstance(value, PathExpr):
            return self._resolve_path(value, data, context)
        elif isinstance(value, LiteralValue):
            if isinstance(value.value, DateExpr):
                return value.value.evaluate()
            return value.value
        elif isinstance(value, DateExpr):
            return value.evaluate()
        return value

    def _compare(self, left: Any, op: Comparator, right: Any) -> bool:
        """Perform comparison operation."""
        if left is None or right is None:
            if op == Comparator.EQ:
                return left == right
            elif op == Comparator.NE:
                return left != right
            return False

        try:
            if op == Comparator.EQ:
                return left == right
            elif op == Comparator.NE:
                return left != right
            elif op == Comparator.LT:
                return left < right
            elif op == Comparator.GT:
                return left > right
            elif op == Comparator.LE:
                return left <= right
            elif op == Comparator.GE:
                return left >= right
        except TypeError:
            return False

        return False

    # Type validation helpers
    def _is_valid_url(self, value: Any) -> bool:
        """Check if value is a valid URL."""
        if not isinstance(value, str):
            return False
        try:
            result = urlparse(value)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    def _is_valid_email(self, value: Any) -> bool:
        """Check if value is a valid email."""
        if not isinstance(value, str):
            return False
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, value))

    def _is_valid_date(self, value: Any) -> bool:
        """Check if value is a valid date."""
        if isinstance(value, datetime):
            return True
        if isinstance(value, str):
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
                return True
            except ValueError:
                pass
            # Try common formats
            for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"]:
                try:
                    datetime.strptime(value, fmt)
                    return True
                except ValueError:
                    continue
        return False

    def _is_not_empty(self, value: Any) -> bool:
        """Check if value is not empty."""
        if value is None:
            return False
        if isinstance(value, str):
            return len(value.strip()) > 0
        if isinstance(value, (list, dict)):
            return len(value) > 0
        return True


class SpecificationValidator:
    """
    Validates agent output against a complete specification.
    """

    def __init__(self, spec: AgentSpecification):
        """
        Initialize with a specification.

        Args:
            spec: The agent specification to validate against
        """
        self.spec = spec
        self.constraint_validator = ConstraintValidator()

    def validate(self, output: Dict[str, Any]) -> List[ValidationResult]:
        """
        Validate output against specification.

        Args:
            output: Agent output to validate

        Returns:
            List of validation results

        Raises:
            SpecificationViolation: If any constraint is violated
        """
        results = []

        for constraint in self.spec.output_constraints:
            result = self.constraint_validator.validate(constraint, output)
            results.append(result)

        # Check for violations
        violations = [r for r in results if not r.valid]
        if violations:
            raise SpecificationViolation(
                spec_name=self.spec.agent_name,
                violations=violations,
            )

        return results

    def validate_soft(self, output: Dict[str, Any]) -> List[ValidationResult]:
        """
        Validate without raising exceptions.

        Returns all results, including failures.
        """
        results = []
        for constraint in self.spec.output_constraints:
            result = self.constraint_validator.validate(constraint, output)
            results.append(result)
        return results
