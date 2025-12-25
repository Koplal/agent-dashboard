"""
Central Output Validation Service.

Provides validation of agent outputs against Pydantic schemas
with retry prompt generation and error tracking.

Version: 2.6.0
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Type, TypeVar, Optional, Dict, Any, List, Union, Tuple

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


@dataclass
class ValidationErrorInfo:
    """Structured information about a validation error.

    Attributes:
        agent_id: Agent that produced the invalid output
        task_id: Task the output was for
        error_type: Category of error
        field_path: Path to the invalid field
        message: Error message
        input_value: The invalid value (may be truncated)
        timestamp: When the error occurred
    """
    agent_id: str
    task_id: str
    error_type: str
    field_path: str
    message: str
    input_value: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "error_type": self.error_type,
            "field_path": self.field_path,
            "message": self.message,
            "input_value": self.input_value,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ValidationResult:
    """Result of a validation operation.

    Attributes:
        success: Whether validation succeeded
        validated_output: The validated model (if success)
        errors: List of validation errors (if failure)
        raw_error: The original exception (if any)
    """
    success: bool
    validated_output: Optional[BaseModel] = None
    errors: List[ValidationErrorInfo] = field(default_factory=list)
    raw_error: Optional[Exception] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "validated_output": (
                self.validated_output.model_dump()
                if self.validated_output else None
            ),
            "errors": [e.to_dict() for e in self.errors],
            "error_count": len(self.errors),
        }


class OutputValidator:
    """Central validation service for agent outputs.

    Provides:
    - Schema validation with detailed error reporting
    - Retry prompt generation for failed validations
    - Error history tracking for quality analysis
    - Configurable strict/lenient modes

    Example:
        validator = OutputValidator()
        result = validator.validate(
            raw_output='{"query": "test", ...}',
            schema=ResearchOutput,
            agent_id="researcher-1",
            task_id="task-123"
        )
        if result.success:
            output = result.validated_output
        else:
            retry_prompt = validator.generate_retry_prompt(
                result.errors, original_prompt
            )
    """

    def __init__(
        self,
        strict_mode: bool = True,
        max_error_history: int = 1000,
        retry_budget: int = 3,
    ):
        """Initialize the validator.

        Args:
            strict_mode: If True, reject any unexpected fields
            max_error_history: Maximum errors to keep in history
            retry_budget: Default retry attempts for validation failures
        """
        self.strict_mode = strict_mode
        self.max_error_history = max_error_history
        self.retry_budget = retry_budget
        self.error_history: List[ValidationErrorInfo] = []
        self.validation_count = 0
        self.success_count = 0

    def validate(
        self,
        raw_output: Union[str, Dict[str, Any]],
        schema: Type[T],
        agent_id: str,
        task_id: str,
        inject_metadata: bool = True,
    ) -> ValidationResult:
        """Validate agent output against schema.

        Args:
            raw_output: JSON string or dictionary to validate
            schema: Pydantic model class to validate against
            agent_id: Identifier of the agent that produced output
            task_id: Identifier of the task
            inject_metadata: If True, inject agent_id/task_id if missing

        Returns:
            ValidationResult with success status and validated output or errors
        """
        self.validation_count += 1

        try:
            # Parse JSON if string
            if isinstance(raw_output, str):
                try:
                    data = json.loads(raw_output)
                except json.JSONDecodeError as e:
                    error = ValidationErrorInfo(
                        agent_id=agent_id,
                        task_id=task_id,
                        error_type="json_parse_error",
                        field_path="<root>",
                        message=str(e),
                        input_value=raw_output[:200] if len(raw_output) > 200 else raw_output,
                    )
                    self._record_error(error)
                    return ValidationResult(
                        success=False,
                        errors=[error],
                        raw_error=e,
                    )
            else:
                data = raw_output.copy() if isinstance(raw_output, dict) else raw_output

            # Inject metadata if requested
            if inject_metadata and isinstance(data, dict):
                data.setdefault("agent_id", agent_id)
                data.setdefault("task_id", task_id)
                # Set default execution time and token count if not present
                data.setdefault("execution_time_ms", 0)
                data.setdefault("token_count", 0)

            # Validate against schema
            validated = schema.model_validate(data)
            self.success_count += 1

            return ValidationResult(
                success=True,
                validated_output=validated,
            )

        except ValidationError as e:
            errors = self._parse_validation_errors(e, agent_id, task_id)
            for error in errors:
                self._record_error(error)

            return ValidationResult(
                success=False,
                errors=errors,
                raw_error=e,
            )

        except Exception as e:
            error = ValidationErrorInfo(
                agent_id=agent_id,
                task_id=task_id,
                error_type="unexpected_error",
                field_path="<unknown>",
                message=str(e),
            )
            self._record_error(error)

            return ValidationResult(
                success=False,
                errors=[error],
                raw_error=e,
            )

    def _parse_validation_errors(
        self,
        error: ValidationError,
        agent_id: str,
        task_id: str,
    ) -> List[ValidationErrorInfo]:
        """Parse Pydantic ValidationError into structured errors."""
        errors = []
        for err in error.errors():
            field_path = " -> ".join(str(x) for x in err["loc"])
            input_val = err.get("input")
            if input_val is not None:
                input_str = str(input_val)[:100]
            else:
                input_str = None

            errors.append(ValidationErrorInfo(
                agent_id=agent_id,
                task_id=task_id,
                error_type=err["type"],
                field_path=field_path,
                message=err["msg"],
                input_value=input_str,
            ))
        return errors

    def _record_error(self, error: ValidationErrorInfo) -> None:
        """Record error in history, maintaining max size."""
        self.error_history.append(error)
        if len(self.error_history) > self.max_error_history:
            self.error_history = self.error_history[-self.max_error_history:]

    def generate_retry_prompt(
        self,
        errors: List[ValidationErrorInfo],
        original_prompt: str,
        max_errors_shown: int = 10,
    ) -> str:
        """Generate a corrective prompt with specific field errors.

        Args:
            errors: List of validation errors
            original_prompt: The original prompt that produced invalid output
            max_errors_shown: Maximum number of errors to include

        Returns:
            A prompt that explains the errors and requests correction
        """
        error_descriptions = []
        for err in errors[:max_errors_shown]:
            desc = f"  - {err.field_path}: {err.message}"
            if err.input_value:
                desc += f" (got: {err.input_value})"
            error_descriptions.append(desc)

        if len(errors) > max_errors_shown:
            error_descriptions.append(
                f"  ... and {len(errors) - max_errors_shown} more errors"
            )

        return f"""Your previous response had validation errors. Please correct and resubmit.

VALIDATION ERRORS:
{chr(10).join(error_descriptions)}

ORIGINAL REQUEST:
{original_prompt}

Please provide a corrected response that addresses all validation errors.
Ensure all required fields are present and have valid values."""

    def get_stats(self) -> Dict[str, Any]:
        """Get validation statistics.

        Returns:
            Dictionary with validation metrics
        """
        return {
            "total_validations": self.validation_count,
            "successful_validations": self.success_count,
            "failed_validations": self.validation_count - self.success_count,
            "success_rate": (
                self.success_count / self.validation_count
                if self.validation_count > 0 else 0.0
            ),
            "errors_in_history": len(self.error_history),
            "recent_error_types": self._get_recent_error_types(),
        }

    def _get_recent_error_types(self, limit: int = 10) -> Dict[str, int]:
        """Get counts of recent error types."""
        type_counts: Dict[str, int] = {}
        for error in self.error_history[-100:]:
            type_counts[error.error_type] = type_counts.get(error.error_type, 0) + 1
        return dict(sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:limit])

    def get_errors_for_agent(self, agent_id: str) -> List[ValidationErrorInfo]:
        """Get all errors for a specific agent."""
        return [e for e in self.error_history if e.agent_id == agent_id]

    def get_errors_for_task(self, task_id: str) -> List[ValidationErrorInfo]:
        """Get all errors for a specific task."""
        return [e for e in self.error_history if e.task_id == task_id]

    def clear_history(self) -> None:
        """Clear error history and reset counters."""
        self.error_history.clear()
        self.validation_count = 0
        self.success_count = 0


# Convenience functions for simple usage

_default_validator: Optional[OutputValidator] = None


def get_default_validator() -> OutputValidator:
    """Get or create the default validator instance."""
    global _default_validator
    if _default_validator is None:
        _default_validator = OutputValidator()
    return _default_validator


def validate_output(
    raw_output: Union[str, Dict[str, Any]],
    schema: Type[T],
    agent_id: str,
    task_id: str,
) -> ValidationResult:
    """Validate output using the default validator.

    Args:
        raw_output: JSON string or dictionary to validate
        schema: Pydantic model class to validate against
        agent_id: Identifier of the agent
        task_id: Identifier of the task

    Returns:
        ValidationResult with success status and validated output or errors
    """
    return get_default_validator().validate(raw_output, schema, agent_id, task_id)


def generate_retry_prompt(
    errors: List[ValidationErrorInfo],
    original_prompt: str,
) -> str:
    """Generate retry prompt using the default validator.

    Args:
        errors: List of validation errors
        original_prompt: The original prompt

    Returns:
        Corrective prompt string
    """
    return get_default_validator().generate_retry_prompt(errors, original_prompt)
