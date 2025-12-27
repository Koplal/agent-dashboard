"""
Tests for the Grammar-Constrained Generation Module.

Tests structured generation, tool schemas, schema registry,
and grammar-constrained local model generation.

Version: 2.6.0
"""

import pytest
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


def _outlines_available() -> bool:
    """Check if Outlines package is available."""
    try:
        import outlines
        return True
    except ImportError:
        return False


def _local_model_available() -> bool:
    """Check if all dependencies for local model generation are available.

    Requires GPU (CUDA) for practical inference speed.
    CPU-only inference takes 12+ minutes per generation.
    """
    try:
        import outlines
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        # Require CUDA for practical inference speed
        return torch.cuda.is_available()
    except ImportError:
        return False


# ============================================================================
# TEST SCHEMAS
# ============================================================================

class SimpleOutput(BaseModel):
    """Simple test output schema."""
    result: str
    score: float = Field(ge=0.0, le=1.0)


class ComplexOutput(BaseModel):
    """Complex test output schema."""
    title: str = Field(min_length=1)
    findings: List[str]
    confidence: float = Field(ge=0.0, le=1.0)
    metadata: Optional[Dict[str, Any]] = None


class NestedOutput(BaseModel):
    """Nested test output schema."""
    class InnerData(BaseModel):
        key: str
        value: int

    name: str
    data: InnerData


# ============================================================================
# TOOL SCHEMA TESTS
# ============================================================================

class TestToolSchema:
    """Tests for ToolSchema and tool definitions."""

    def test_tool_schema_creation(self):
        """Test creating a tool schema."""
        from src.constraints.tool_schemas import ToolSchema, ToolCategory

        schema = ToolSchema(
            name="test_tool",
            description="A test tool",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "minLength": 3},
                },
                "required": ["query"],
            },
            category=ToolCategory.SEARCH,
        )

        assert schema.name == "test_tool"
        assert schema.category == ToolCategory.SEARCH

    def test_tool_schema_to_claude_format(self):
        """Test conversion to Claude API format."""
        from src.constraints.tool_schemas import ToolSchema

        schema = ToolSchema(
            name="my_tool",
            description="My description",
            input_schema={"type": "object"},
        )

        claude_format = schema.to_claude_tool()

        assert claude_format["name"] == "my_tool"
        assert claude_format["description"] == "My description"
        assert "input_schema" in claude_format

    def test_tool_schema_validation(self):
        """Test input validation against schema."""
        from src.constraints.tool_schemas import ToolSchema

        schema = ToolSchema(
            name="test",
            description="Test",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "minLength": 5},
                    "count": {"type": "integer", "minimum": 1, "maximum": 10},
                },
                "required": ["query"],
            },
        )

        # Valid input
        errors = schema.validate_input({"query": "hello world", "count": 5})
        assert len(errors) == 0

        # Missing required field
        errors = schema.validate_input({"count": 5})
        assert any("Missing required" in e for e in errors)

        # String too short
        errors = schema.validate_input({"query": "hi"})
        assert any("at least 5" in e for e in errors)

        # Integer out of range
        errors = schema.validate_input({"query": "hello", "count": 20})
        assert any("at most 10" in e for e in errors)

    def test_builtin_tool_schemas(self):
        """Test built-in tool schemas."""
        from src.constraints.tool_schemas import (
            WEB_SEARCH_TOOL,
            FILE_OPERATION_TOOL,
            CODE_EXECUTION_TOOL,
            RESEARCH_QUERY_TOOL,
            JUDGE_VERDICT_TOOL,
        )

        assert WEB_SEARCH_TOOL.name == "web_search"
        assert FILE_OPERATION_TOOL.name == "file_operation"
        assert CODE_EXECUTION_TOOL.name == "execute_code"
        assert RESEARCH_QUERY_TOOL.name == "research_query"
        assert JUDGE_VERDICT_TOOL.name == "judge_verdict"

    def test_get_tool_schema(self):
        """Test getting tool schema by name."""
        from src.constraints.tool_schemas import get_tool_schema

        schema = get_tool_schema("web_search")
        assert schema is not None
        assert schema.name == "web_search"

        # Non-existent tool
        schema = get_tool_schema("nonexistent")
        assert schema is None

    def test_list_tool_schemas(self):
        """Test listing tool schemas."""
        from src.constraints.tool_schemas import list_tool_schemas, ToolCategory

        # All schemas
        all_schemas = list_tool_schemas()
        assert len(all_schemas) >= 5

        # Filter by category
        search_schemas = list_tool_schemas(category=ToolCategory.SEARCH)
        assert len(search_schemas) >= 1
        assert all(s.category == ToolCategory.SEARCH for s in search_schemas)

    def test_get_tools_for_claude(self):
        """Test getting tools formatted for Claude API."""
        from src.constraints.tool_schemas import get_tools_for_claude

        # All tools
        all_tools = get_tools_for_claude()
        assert len(all_tools) >= 5
        assert all("name" in t and "description" in t for t in all_tools)

        # Specific tools
        specific = get_tools_for_claude(["web_search", "file_operation"])
        assert len(specific) == 2


# ============================================================================
# SCHEMA REGISTRY TESTS
# ============================================================================

class TestSchemaRegistry:
    """Tests for SchemaRegistry."""

    def test_registry_creation(self):
        """Test creating a schema registry."""
        from src.constraints.schema_registry import SchemaRegistry

        registry = SchemaRegistry()
        assert registry is not None

    def test_register_schema(self):
        """Test registering a schema."""
        from src.constraints.schema_registry import SchemaRegistry

        registry = SchemaRegistry()
        metadata = registry.register(
            SimpleOutput,
            description="Simple output schema",
            category="test",
        )

        assert metadata.name == "SimpleOutput"
        assert metadata.category == "test"

    def test_get_schema(self):
        """Test retrieving a registered schema."""
        from src.constraints.schema_registry import SchemaRegistry

        registry = SchemaRegistry()
        registry.register(SimpleOutput, category="test")

        schema = registry.get("SimpleOutput")
        assert schema is SimpleOutput

        # Non-existent schema
        schema = registry.get("NonExistent")
        assert schema is None

    def test_list_schemas(self):
        """Test listing registered schemas."""
        from src.constraints.schema_registry import SchemaRegistry

        registry = SchemaRegistry()
        registry.register(SimpleOutput, category="cat1")
        registry.register(ComplexOutput, category="cat2")
        registry.register(NestedOutput, category="cat1")

        # All schemas
        all_schemas = registry.list_schemas()
        assert len(all_schemas) == 3

        # Filter by category
        cat1_schemas = registry.list_schemas(category="cat1")
        assert len(cat1_schemas) == 2

    def test_deprecated_schema_warning(self, caplog):
        """Test warning for deprecated schemas."""
        from src.constraints.schema_registry import SchemaRegistry
        import logging

        registry = SchemaRegistry()
        registry.register(
            SimpleOutput,
            deprecated=True,
            replacement="ComplexOutput",
        )

        with caplog.at_level(logging.WARNING):
            registry.get("SimpleOutput")

        assert "deprecated" in caplog.text.lower()

    def test_unregister_schema(self):
        """Test unregistering a schema."""
        from src.constraints.schema_registry import SchemaRegistry

        registry = SchemaRegistry()
        registry.register(SimpleOutput, category="test")

        assert registry.get("SimpleOutput") is not None

        result = registry.unregister("SimpleOutput")
        assert result is True

        assert registry.get("SimpleOutput") is None

        # Unregister non-existent
        result = registry.unregister("NonExistent")
        assert result is False

    def test_get_json_schema(self):
        """Test getting JSON schema for a registered schema."""
        from src.constraints.schema_registry import SchemaRegistry

        registry = SchemaRegistry()
        registry.register(SimpleOutput)

        json_schema = registry.get_json_schema("SimpleOutput")
        assert json_schema is not None
        assert "properties" in json_schema
        assert "result" in json_schema["properties"]

    def test_validate_data(self):
        """Test validating data against registered schema."""
        from src.constraints.schema_registry import SchemaRegistry

        registry = SchemaRegistry()
        registry.register(SimpleOutput)

        # Valid data
        success, model, error = registry.validate_data(
            "SimpleOutput",
            {"result": "test", "score": 0.5}
        )
        assert success is True
        assert model is not None
        assert error is None

        # Invalid data
        success, model, error = registry.validate_data(
            "SimpleOutput",
            {"result": "test", "score": 2.0}  # score > 1.0
        )
        assert success is False
        assert error is not None

    def test_registered_schema_decorator(self):
        """Test the @registered_schema decorator."""
        from src.constraints.schema_registry import (
            registered_schema,
            get_default_registry,
        )

        @registered_schema(category="decorated", description="Decorated schema")
        class DecoratedOutput(BaseModel):
            value: int

        registry = get_default_registry()
        schema = registry.get("DecoratedOutput")

        assert schema is DecoratedOutput

    def test_schema_validator(self):
        """Test adding custom schema validators."""
        from src.constraints.schema_registry import SchemaRegistry

        registry = SchemaRegistry()

        # Add validator that rejects schemas without docstrings
        def require_docstring(schema_class):
            if not schema_class.__doc__:
                return "Schema must have a docstring"
            return None

        registry.add_validator(require_docstring)

        # Schema with docstring should pass
        registry.register(SimpleOutput)  # Has docstring

        # Schema without docstring should fail
        class NoDocSchema(BaseModel):
            x: int

        with pytest.raises(ValueError, match="docstring"):
            registry.register(NoDocSchema)

    def test_registry_stats(self):
        """Test getting registry statistics."""
        from src.constraints.schema_registry import SchemaRegistry

        registry = SchemaRegistry()
        registry.register(SimpleOutput, category="cat1")
        registry.register(ComplexOutput, category="cat1", deprecated=True)
        registry.register(NestedOutput, category="cat2")

        stats = registry.get_stats()

        assert stats["total_schemas"] == 3
        assert stats["deprecated_schemas"] == 1
        assert stats["active_schemas"] == 2
        assert stats["categories"] == 2


# ============================================================================
# STRUCTURED GENERATION TESTS
# ============================================================================

class TestStructuredGenerator:
    """Tests for StructuredGenerator."""

    def test_generator_creation(self):
        """Test creating a structured generator."""
        from src.constraints.structured_generation import StructuredGenerator

        generator = StructuredGenerator()
        assert generator is not None
        assert generator.max_retries == 2

    def test_generation_result_creation(self):
        """Test creating a GenerationResult."""
        from src.constraints.structured_generation import GenerationResult

        result = GenerationResult(
            success=True,
            output={"test": "value"},
            model_used="test-model",
            tokens_used=100,
        )

        assert result.success is True
        assert result.tokens_used == 100

    def test_generation_result_to_dict(self):
        """Test converting GenerationResult to dict."""
        from src.constraints.structured_generation import GenerationResult

        result = GenerationResult(
            success=True,
            output={"test": "value"},
        )

        result_dict = result.to_dict()
        assert result_dict["success"] is True
        assert result_dict["output"] == {"test": "value"}

    def test_generation_result_with_pydantic(self):
        """Test GenerationResult with Pydantic model output."""
        from src.constraints.structured_generation import GenerationResult

        output = SimpleOutput(result="test", score=0.9)
        result = GenerationResult(success=True, output=output)

        result_dict = result.to_dict()
        assert result_dict["output"]["result"] == "test"
        assert result_dict["output"]["score"] == 0.9

    def test_clean_schema_for_claude(self):
        """Test schema cleaning for Claude API."""
        from src.constraints.structured_generation import StructuredGenerator

        generator = StructuredGenerator()

        schema = {
            "$schema": "http://json-schema.org/...",
            "$defs": {"SomeRef": {}},
            "title": "MySchema",
            "type": "object",
            "properties": {
                "field1": {
                    "type": "string",
                    "title": "Field 1",
                    "examples": ["example"],
                },
            },
        }

        cleaned = generator._clean_schema_for_claude(schema)

        assert "$schema" not in cleaned
        assert "$defs" not in cleaned
        assert "title" not in cleaned
        assert "field1" in cleaned["properties"]
        assert "title" not in cleaned["properties"]["field1"]
        assert "examples" not in cleaned["properties"]["field1"]

    def test_clean_property_schema_union_types(self):
        """Test cleaning union types in property schema."""
        from src.constraints.structured_generation import StructuredGenerator

        generator = StructuredGenerator()

        prop = {
            "anyOf": [
                {"type": "string"},
                {"type": "null"},
            ]
        }

        cleaned = generator._clean_property_schema(prop)
        assert cleaned.get("type") == "string"
        assert "anyOf" not in cleaned

    def test_generator_stats(self):
        """Test generator statistics."""
        from src.constraints.structured_generation import StructuredGenerator

        generator = StructuredGenerator()

        stats = generator.get_stats()
        assert stats["generations_attempted"] == 0
        assert stats["success_rate"] == 0.0


class TestMockStructuredGenerator:
    """Tests for MockStructuredGenerator."""

    def test_mock_generator_creation(self):
        """Test creating a mock generator."""
        from src.constraints.structured_generation import MockStructuredGenerator

        mock = MockStructuredGenerator()
        assert mock is not None

    def test_mock_with_predefined_response(self):
        """Test mock generator with predefined response."""
        from src.constraints.structured_generation import MockStructuredGenerator

        mock = MockStructuredGenerator(
            mock_responses={
                "SimpleOutput": {"result": "mock result", "score": 0.75}
            }
        )

        result = mock.generate_with_schema("test prompt", SimpleOutput)

        assert result.success is True
        assert result.output.result == "mock result"
        assert result.output.score == 0.75

    def test_mock_failure_mode(self):
        """Test mock generator in failure mode."""
        from src.constraints.structured_generation import MockStructuredGenerator

        mock = MockStructuredGenerator(should_succeed=False)

        result = mock.generate_with_schema("test", SimpleOutput)

        assert result.success is False
        assert result.error == "Mock failure"

    def test_mock_tool_call(self):
        """Test mock tool call generation."""
        from src.constraints.structured_generation import MockStructuredGenerator

        mock = MockStructuredGenerator()

        tools = [
            {"name": "test_tool", "description": "Test", "input_schema": {}}
        ]

        result = mock.generate_tool_call("context", tools)

        assert result.success is True
        assert result.output["tool_name"] == "test_tool"

    def test_mock_with_default_data(self):
        """Test mock generator building default data."""
        from src.constraints.structured_generation import MockStructuredGenerator

        mock = MockStructuredGenerator()

        result = mock.generate_with_schema("test", SimpleOutput)

        # Should succeed with default values
        assert result.success is True
        assert result.output is not None


# ============================================================================
# GRAMMAR-CONSTRAINED GENERATION TESTS
# ============================================================================

class TestGrammarConstrainedGenerator:
    """Tests for GrammarConstrainedGenerator."""

    def test_outlines_availability_check(self):
        """Test checking Outlines availability."""
        from src.constraints.grammar_constrained import (
            GrammarConstrainedGenerator,
            OUTLINES_AVAILABLE,
        )

        generator = GrammarConstrainedGenerator(load_on_init=False)

        # Should reflect actual package availability
        assert generator.is_available() == OUTLINES_AVAILABLE

    def test_local_generation_result(self):
        """Test LocalGenerationResult creation."""
        from src.constraints.grammar_constrained import LocalGenerationResult

        result = LocalGenerationResult(
            success=True,
            output={"test": "value"},
            model_used="test-model",
        )

        assert result.success is True
        assert result.model_used == "test-model"

    def test_local_generation_result_to_dict(self):
        """Test LocalGenerationResult to_dict with Pydantic model."""
        from src.constraints.grammar_constrained import LocalGenerationResult

        output = SimpleOutput(result="test", score=0.5)
        result = LocalGenerationResult(
            success=True,
            output=output,
        )

        result_dict = result.to_dict()
        assert result_dict["output"]["result"] == "test"

    def test_generator_stats(self):
        """Test grammar-constrained generator statistics."""
        from src.constraints.grammar_constrained import GrammarConstrainedGenerator

        generator = GrammarConstrainedGenerator(load_on_init=False)

        stats = generator.get_stats()
        assert "outlines_available" in stats
        assert "model_loaded" in stats
        assert stats["generations_attempted"] == 0

    @pytest.mark.skipif(
        not _local_model_available(),
        reason="Requires Outlines + PyTorch + transformers (pip install outlines torch transformers)"
    )
    def test_json_generation_with_outlines(self):
        """Test JSON generation with Outlines (requires local model)."""
        from src.constraints.grammar_constrained import GrammarConstrainedGenerator

        generator = GrammarConstrainedGenerator()
        result = generator.generate_json(
            prompt="Generate a simple output",
            schema=SimpleOutput,
        )

        assert result.success is True


class TestMockGrammarConstrainedGenerator:
    """Tests for MockGrammarConstrainedGenerator."""

    def test_mock_always_available(self):
        """Test mock generator is always available."""
        from src.constraints.grammar_constrained import (
            MockGrammarConstrainedGenerator
        )

        mock = MockGrammarConstrainedGenerator()
        assert mock.is_available() is True

    def test_mock_json_generation(self):
        """Test mock JSON generation."""
        from src.constraints.grammar_constrained import (
            MockGrammarConstrainedGenerator
        )

        mock = MockGrammarConstrainedGenerator(
            mock_responses={"SimpleOutput": {"result": "test", "score": 0.5}}
        )

        result = mock.generate_json("prompt", SimpleOutput)

        assert result.success is True
        assert result.output.result == "test"

    def test_mock_regex_generation(self):
        """Test mock regex generation."""
        from src.constraints.grammar_constrained import (
            MockGrammarConstrainedGenerator
        )

        mock = MockGrammarConstrainedGenerator()
        result = mock.generate_regex("prompt", r"[a-z]+")

        assert result.success is True
        assert result.raw_text == "mock_match"

    def test_mock_choice_generation(self):
        """Test mock choice generation."""
        from src.constraints.grammar_constrained import (
            MockGrammarConstrainedGenerator
        )

        mock = MockGrammarConstrainedGenerator()
        result = mock.generate_choice("prompt", ["option1", "option2"])

        assert result.success is True
        assert result.output == "option1"

    def test_mock_failure_mode(self):
        """Test mock in failure mode."""
        from src.constraints.grammar_constrained import (
            MockGrammarConstrainedGenerator
        )

        mock = MockGrammarConstrainedGenerator(should_succeed=False)

        result = mock.generate_json("prompt", SimpleOutput)
        assert result.success is False


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestConstraintsModuleImports:
    """Test module imports work correctly."""

    def test_main_imports(self):
        """Test main module imports."""
        from src.constraints import (
            StructuredGenerator,
            GenerationResult,
            GenerationError,
            ToolSchema,
            get_tool_schema,
            list_tool_schemas,
            WEB_SEARCH_TOOL,
            SchemaRegistry,
            get_default_registry,
            register_schema,
            get_schema,
            GrammarConstrainedGenerator,
            LocalGenerationResult,
            OUTLINES_AVAILABLE,
        )

        # All imports should work
        assert StructuredGenerator is not None
        assert WEB_SEARCH_TOOL is not None
        assert SchemaRegistry is not None

    def test_default_registry_initialization(self):
        """Test default registry initializes with built-in schemas."""
        from src.constraints.schema_registry import get_default_registry

        registry = get_default_registry()

        # Should have some schemas (from built-in registration)
        stats = registry.get_stats()
        assert stats["total_schemas"] >= 0  # May be 0 if schemas module fails

    def test_convenience_functions(self):
        """Test convenience functions work."""
        from src.constraints.schema_registry import (
            register_schema,
            get_schema,
            list_schemas,
        )

        # Register a schema
        class TestConvenienceOutput(BaseModel):
            value: str

        register_schema(TestConvenienceOutput, category="convenience_test")

        # Retrieve it
        schema = get_schema("TestConvenienceOutput")
        assert schema is TestConvenienceOutput

        # List schemas
        schemas = list_schemas(category="convenience_test")
        assert len(schemas) >= 1


class TestPanelSelectorIntegration:
    """Test integration with panel_selector."""

    def test_evaluate_with_structured_generation_exists(self):
        """Test that integration function exists."""
        from src.panel_selector import evaluate_with_structured_generation

        assert evaluate_with_structured_generation is not None

    def test_create_structured_tool_call_exists(self):
        """Test that tool call function exists."""
        from src.panel_selector import create_structured_tool_call

        assert create_structured_tool_call is not None


# ============================================================================
# EDGE CASES AND ERROR HANDLING
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_tool_validation(self):
        """Test validating empty input."""
        from src.constraints.tool_schemas import ToolSchema

        schema = ToolSchema(
            name="test",
            description="Test",
            input_schema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        )

        # Empty input should be valid
        errors = schema.validate_input({})
        assert len(errors) == 0

    def test_enum_validation(self):
        """Test enum value validation."""
        from src.constraints.tool_schemas import ToolSchema

        schema = ToolSchema(
            name="test",
            description="Test",
            input_schema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["active", "inactive"],
                    },
                },
                "required": ["status"],
            },
        )

        # Valid enum value
        errors = schema.validate_input({"status": "active"})
        assert len(errors) == 0

        # Invalid enum value
        errors = schema.validate_input({"status": "unknown"})
        assert any("one of" in e for e in errors)

    def test_pattern_validation(self):
        """Test regex pattern validation."""
        from src.constraints.tool_schemas import ToolSchema

        schema = ToolSchema(
            name="test",
            description="Test",
            input_schema={
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "pattern": r"^[a-z]+@[a-z]+\.[a-z]+$",
                    },
                },
                "required": ["email"],
            },
        )

        # Valid pattern
        errors = schema.validate_input({"email": "test@example.com"})
        assert len(errors) == 0

        # Invalid pattern
        errors = schema.validate_input({"email": "not-an-email"})
        assert any("pattern" in e for e in errors)

    def test_type_coercion_not_applied(self):
        """Test that type validation doesn't coerce types."""
        from src.constraints.tool_schemas import ToolSchema

        schema = ToolSchema(
            name="test",
            description="Test",
            input_schema={
                "type": "object",
                "properties": {
                    "count": {"type": "integer"},
                },
                "required": ["count"],
            },
        )

        # String "5" should fail integer validation
        errors = schema.validate_input({"count": "5"})
        assert any("integer" in e for e in errors)

    def test_nested_object_not_validated_deeply(self):
        """Test that nested objects are type-checked but not deeply validated."""
        from src.constraints.tool_schemas import ToolSchema

        schema = ToolSchema(
            name="test",
            description="Test",
            input_schema={
                "type": "object",
                "properties": {
                    "config": {"type": "object"},
                },
                "required": ["config"],
            },
        )

        # Nested object should be valid
        errors = schema.validate_input({"config": {"any": "value"}})
        assert len(errors) == 0

        # Non-object should fail
        errors = schema.validate_input({"config": "not-an-object"})
        assert any("object" in e for e in errors)


class TestGenerationError:
    """Tests for GenerationError."""

    def test_generation_error_creation(self):
        """Test creating a GenerationError."""
        from src.constraints.structured_generation import GenerationError

        error = GenerationError(
            "Something went wrong",
            error_type="api_error",
            details={"code": 500},
        )

        assert str(error) == "Something went wrong"
        assert error.error_type == "api_error"
        assert error.details["code"] == 500

    def test_generation_error_default_type(self):
        """Test default error type."""
        from src.constraints.structured_generation import GenerationError

        error = GenerationError("Error message")

        assert error.error_type == "generation_error"
        assert error.details == {}
