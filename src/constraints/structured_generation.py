"""
Structured Generation with Schema Enforcement.

Provides structured output generation using Claude's tool_use feature
to enforce JSON Schema constraints on outputs.

Version: 2.6.0
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, Type, Optional, List, Union, TypeVar

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def utc_now() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


class GenerationError(Exception):
    """Error during structured generation."""

    def __init__(
        self,
        message: str,
        error_type: str = "generation_error",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.error_type = error_type
        self.details = details or {}


@dataclass
class GenerationResult:
    """
    Result of a structured generation operation.

    Attributes:
        success: Whether generation succeeded
        output: The generated and validated output
        raw_response: Raw response from the API
        tool_call_id: ID of the tool call (if applicable)
        model_used: Model that generated the output
        tokens_used: Token count for the request
        generation_time_ms: Time taken to generate
    """
    success: bool
    output: Optional[Union[BaseModel, Dict[str, Any]]] = None
    raw_response: Optional[Dict[str, Any]] = None
    tool_call_id: Optional[str] = None
    model_used: Optional[str] = None
    tokens_used: int = 0
    generation_time_ms: int = 0
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        output_data = None
        if self.output is not None:
            if isinstance(self.output, BaseModel):
                output_data = self.output.model_dump()
            else:
                output_data = self.output

        return {
            "success": self.success,
            "output": output_data,
            "tool_call_id": self.tool_call_id,
            "model_used": self.model_used,
            "tokens_used": self.tokens_used,
            "generation_time_ms": self.generation_time_ms,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
        }


class StructuredGenerator:
    """
    Generate structured outputs with schema enforcement.

    Uses Claude's tool_use feature to enforce output structure,
    eliminating parsing failures and reducing retry loops.

    Example:
        from anthropic import Anthropic
        from pydantic import BaseModel

        class ResearchOutput(BaseModel):
            query: str
            findings: list[str]
            confidence: float

        client = Anthropic()
        generator = StructuredGenerator(client)

        result = generator.generate_with_schema(
            prompt="Research Python async best practices",
            schema=ResearchOutput
        )
        if result.success:
            output: ResearchOutput = result.output
            print(output.findings)
    """

    # Default model for structured generation
    DEFAULT_MODEL = "claude-sonnet-4-20250514"
    FALLBACK_MODEL = "claude-haiku-3-5-20241022"

    def __init__(
        self,
        client: Optional[Any] = None,
        default_model: str = DEFAULT_MODEL,
        max_retries: int = 2,
        timeout_seconds: int = 60,
    ):
        """
        Initialize the structured generator.

        Args:
            client: Anthropic client instance (optional, for testing)
            default_model: Default model to use for generation
            max_retries: Maximum retry attempts on failure
            timeout_seconds: Timeout for API calls
        """
        self.client = client
        self.default_model = default_model
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds

        # Statistics
        self.generations_attempted = 0
        self.generations_succeeded = 0
        self.total_tokens = 0
        self.retries_used = 0

    def _get_client(self) -> Any:
        """Get or create the Anthropic client."""
        if self.client is None:
            try:
                from anthropic import Anthropic
                self.client = Anthropic()
            except ImportError:
                raise GenerationError(
                    "anthropic package not installed",
                    error_type="import_error",
                )
        return self.client

    def generate_with_schema(
        self,
        prompt: str,
        schema: Type[T],
        model: Optional[str] = None,
        max_tokens: int = 4096,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
    ) -> GenerationResult:
        """
        Generate output conforming to a Pydantic schema.

        Uses Claude's tool_use to enforce structure.

        Args:
            prompt: User prompt for generation
            schema: Pydantic model class defining output structure
            model: Model to use (defaults to default_model)
            max_tokens: Maximum tokens in response
            system_prompt: Optional system prompt
            temperature: Sampling temperature

        Returns:
            GenerationResult with validated output or error
        """
        import time
        start_time = time.time()

        self.generations_attempted += 1
        model = model or self.default_model

        # Convert Pydantic schema to JSON Schema
        json_schema = schema.model_json_schema()

        # Clean up schema for Claude (remove unsupported fields)
        json_schema = self._clean_schema_for_claude(json_schema)

        # Define as a tool that returns structured data
        tool_definition = {
            "name": "structured_output",
            "description": f"Return the analysis results as a {schema.__name__}",
            "input_schema": json_schema,
        }

        try:
            client = self._get_client()

            messages = [{"role": "user", "content": prompt}]

            # Build request parameters
            request_params = {
                "model": model,
                "max_tokens": max_tokens,
                "tools": [tool_definition],
                "tool_choice": {"type": "tool", "name": "structured_output"},
                "messages": messages,
            }

            if system_prompt:
                request_params["system"] = system_prompt
            if temperature > 0:
                request_params["temperature"] = temperature

            response = client.messages.create(**request_params)

            # Extract token usage
            tokens_used = 0
            if hasattr(response, "usage"):
                tokens_used = (
                    getattr(response.usage, "input_tokens", 0) +
                    getattr(response.usage, "output_tokens", 0)
                )
            self.total_tokens += tokens_used

            # Extract tool use result
            for block in response.content:
                if hasattr(block, "type") and block.type == "tool_use":
                    try:
                        validated = schema.model_validate(block.input)
                        self.generations_succeeded += 1

                        elapsed_ms = int((time.time() - start_time) * 1000)

                        return GenerationResult(
                            success=True,
                            output=validated,
                            raw_response={"content": str(response.content)},
                            tool_call_id=block.id,
                            model_used=model,
                            tokens_used=tokens_used,
                            generation_time_ms=elapsed_ms,
                        )
                    except ValidationError as e:
                        # Schema validation failed despite tool use
                        elapsed_ms = int((time.time() - start_time) * 1000)
                        return GenerationResult(
                            success=False,
                            raw_response={"input": block.input},
                            model_used=model,
                            tokens_used=tokens_used,
                            generation_time_ms=elapsed_ms,
                            error=f"Validation failed: {e}",
                        )

            # No tool use in response
            elapsed_ms = int((time.time() - start_time) * 1000)
            return GenerationResult(
                success=False,
                model_used=model,
                tokens_used=tokens_used,
                generation_time_ms=elapsed_ms,
                error="No structured output generated",
            )

        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Structured generation failed: {e}")
            return GenerationResult(
                success=False,
                model_used=model,
                generation_time_ms=elapsed_ms,
                error=str(e),
            )

    def generate_tool_call(
        self,
        context: str,
        available_tools: List[Dict[str, Any]],
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> GenerationResult:
        """
        Generate a valid tool call from available options.

        Guarantees output matches one of the defined tool schemas.

        Args:
            context: Context for tool selection
            available_tools: List of tool definitions
            model: Model to use
            system_prompt: Optional system prompt

        Returns:
            GenerationResult with tool call information
        """
        import time
        start_time = time.time()

        self.generations_attempted += 1
        model = model or self.FALLBACK_MODEL

        try:
            client = self._get_client()

            request_params = {
                "model": model,
                "max_tokens": 1024,
                "tools": available_tools,
                "messages": [{"role": "user", "content": context}],
            }

            if system_prompt:
                request_params["system"] = system_prompt

            response = client.messages.create(**request_params)

            tokens_used = 0
            if hasattr(response, "usage"):
                tokens_used = (
                    getattr(response.usage, "input_tokens", 0) +
                    getattr(response.usage, "output_tokens", 0)
                )
            self.total_tokens += tokens_used

            for block in response.content:
                if hasattr(block, "type") and block.type == "tool_use":
                    self.generations_succeeded += 1
                    elapsed_ms = int((time.time() - start_time) * 1000)

                    return GenerationResult(
                        success=True,
                        output={
                            "tool_name": block.name,
                            "tool_id": block.id,
                            "parameters": block.input,
                        },
                        tool_call_id=block.id,
                        model_used=model,
                        tokens_used=tokens_used,
                        generation_time_ms=elapsed_ms,
                    )

            elapsed_ms = int((time.time() - start_time) * 1000)
            return GenerationResult(
                success=False,
                model_used=model,
                tokens_used=tokens_used,
                generation_time_ms=elapsed_ms,
                error="No tool call generated",
            )

        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Tool call generation failed: {e}")
            return GenerationResult(
                success=False,
                model_used=model,
                generation_time_ms=elapsed_ms,
                error=str(e),
            )

    def generate_with_retry(
        self,
        prompt: str,
        schema: Type[T],
        model: Optional[str] = None,
        max_tokens: int = 4096,
        system_prompt: Optional[str] = None,
    ) -> GenerationResult:
        """
        Generate with automatic retry on failure.

        Args:
            prompt: User prompt
            schema: Pydantic schema
            model: Model to use
            max_tokens: Maximum tokens
            system_prompt: Optional system prompt

        Returns:
            GenerationResult from successful attempt or last failure
        """
        last_result = None

        for attempt in range(self.max_retries + 1):
            result = self.generate_with_schema(
                prompt=prompt,
                schema=schema,
                model=model,
                max_tokens=max_tokens,
                system_prompt=system_prompt,
            )

            if result.success:
                return result

            last_result = result
            self.retries_used += 1

            # Enhance prompt with error info for retry
            if attempt < self.max_retries:
                prompt = self._build_retry_prompt(prompt, result.error)

        return last_result or GenerationResult(
            success=False,
            error="All retry attempts exhausted",
        )

    def _build_retry_prompt(self, original_prompt: str, error: Optional[str]) -> str:
        """Build an enhanced prompt for retry."""
        return f"""Previous attempt failed with error: {error}

Please try again, ensuring your response strictly follows the required schema.

ORIGINAL REQUEST:
{original_prompt}"""

    def _clean_schema_for_claude(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean JSON schema for Claude API compatibility.

        Removes unsupported keywords and fixes common issues.
        """
        cleaned = schema.copy()

        # Remove unsupported top-level keys
        unsupported = ["$defs", "definitions", "$schema", "examples", "title"]
        for key in unsupported:
            cleaned.pop(key, None)

        # Recursively clean properties
        if "properties" in cleaned:
            cleaned["properties"] = {
                k: self._clean_property_schema(v)
                for k, v in cleaned["properties"].items()
            }

        return cleaned

    def _clean_property_schema(self, prop: Dict[str, Any]) -> Dict[str, Any]:
        """Clean a single property schema."""
        if not isinstance(prop, dict):
            return prop

        cleaned = prop.copy()

        # Remove unsupported keys
        unsupported = ["title", "examples", "default", "$ref"]
        for key in unsupported:
            cleaned.pop(key, None)

        # Handle anyOf/oneOf by taking first option
        for union_key in ["anyOf", "oneOf"]:
            if union_key in cleaned:
                options = cleaned.pop(union_key)
                if options and isinstance(options[0], dict):
                    # Filter out null type if present
                    non_null = [o for o in options if o.get("type") != "null"]
                    if non_null:
                        cleaned.update(non_null[0])
                    elif options:
                        cleaned.update(options[0])

        # Recursively clean nested objects
        if cleaned.get("type") == "object" and "properties" in cleaned:
            cleaned["properties"] = {
                k: self._clean_property_schema(v)
                for k, v in cleaned["properties"].items()
            }

        # Clean array items
        if cleaned.get("type") == "array" and "items" in cleaned:
            cleaned["items"] = self._clean_property_schema(cleaned["items"])

        return cleaned

    def get_stats(self) -> Dict[str, Any]:
        """Get generation statistics."""
        success_rate = (
            self.generations_succeeded / self.generations_attempted
            if self.generations_attempted > 0
            else 0.0
        )

        return {
            "generations_attempted": self.generations_attempted,
            "generations_succeeded": self.generations_succeeded,
            "success_rate": success_rate,
            "total_tokens": self.total_tokens,
            "retries_used": self.retries_used,
            "default_model": self.default_model,
        }


# Mock generator for testing without API
class MockStructuredGenerator(StructuredGenerator):
    """
    Mock generator for testing without API calls.

    Returns predefined responses or validates against schema
    and returns empty/default values.
    """

    def __init__(
        self,
        mock_responses: Optional[Dict[str, Any]] = None,
        should_succeed: bool = True,
    ):
        """
        Initialize mock generator.

        Args:
            mock_responses: Predefined responses keyed by schema name
            should_succeed: Whether generations should succeed
        """
        super().__init__(client=None)
        self.mock_responses = mock_responses or {}
        self.should_succeed = should_succeed

    def generate_with_schema(
        self,
        prompt: str,
        schema: Type[T],
        model: Optional[str] = None,
        max_tokens: int = 4096,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
    ) -> GenerationResult:
        """Generate mock response."""
        import time
        start_time = time.time()

        self.generations_attempted += 1

        if not self.should_succeed:
            return GenerationResult(
                success=False,
                model_used=model or "mock",
                error="Mock failure",
            )

        # Check for predefined response
        schema_name = schema.__name__
        if schema_name in self.mock_responses:
            try:
                validated = schema.model_validate(self.mock_responses[schema_name])
                self.generations_succeeded += 1
                elapsed_ms = int((time.time() - start_time) * 1000)

                return GenerationResult(
                    success=True,
                    output=validated,
                    model_used=model or "mock",
                    generation_time_ms=elapsed_ms,
                )
            except ValidationError as e:
                return GenerationResult(
                    success=False,
                    model_used=model or "mock",
                    error=str(e),
                )

        # Try to create default instance
        try:
            # Build default values for required fields
            json_schema = schema.model_json_schema()
            default_data = self._build_default_data(json_schema)
            validated = schema.model_validate(default_data)
            self.generations_succeeded += 1
            elapsed_ms = int((time.time() - start_time) * 1000)

            return GenerationResult(
                success=True,
                output=validated,
                model_used=model or "mock",
                generation_time_ms=elapsed_ms,
            )
        except Exception as e:
            return GenerationResult(
                success=False,
                model_used=model or "mock",
                error=f"Could not create default: {e}",
            )

    def _build_default_data(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Build default data from schema."""
        data = {}
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        for field_name, field_schema in properties.items():
            if field_name not in required:
                continue

            field_type = field_schema.get("type", "string")

            if field_type == "string":
                enum_vals = field_schema.get("enum")
                if enum_vals:
                    data[field_name] = enum_vals[0]
                else:
                    min_len = field_schema.get("minLength", 1)
                    data[field_name] = "x" * min_len
            elif field_type == "integer":
                minimum = field_schema.get("minimum", 0)
                data[field_name] = minimum
            elif field_type == "number":
                minimum = field_schema.get("minimum", 0.0)
                data[field_name] = float(minimum)
            elif field_type == "boolean":
                data[field_name] = False
            elif field_type == "array":
                data[field_name] = []
            elif field_type == "object":
                data[field_name] = {}

        return data

    def generate_tool_call(
        self,
        context: str,
        available_tools: List[Dict[str, Any]],
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> GenerationResult:
        """Generate mock tool call."""
        self.generations_attempted += 1

        if not self.should_succeed or not available_tools:
            return GenerationResult(
                success=False,
                model_used=model or "mock",
                error="Mock failure or no tools",
            )

        # Return first tool with minimal valid input
        tool = available_tools[0]
        self.generations_succeeded += 1

        return GenerationResult(
            success=True,
            output={
                "tool_name": tool["name"],
                "tool_id": "mock_tool_id",
                "parameters": {},
            },
            tool_call_id="mock_tool_id",
            model_used=model or "mock",
        )
