"""
Tests for the Specification Language Module.

Tests parsing, validation, compilation, and agent enforcement.
"""

import asyncio
import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime, timedelta

from src.specifications import (
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
    ComparisonCondition,
    TypeCondition,
    CountCondition,
    # Behavior rules
    PreferRule,
    NeverRule,
    AlwaysRule,
    WhenRule,
    # Top-level AST
    AgentSpecification,
    # Parser
    SpecificationParser,
    ParseError,
    # Validators
    ValidationResult,
    SpecificationViolation,
    ConstraintValidator,
    SpecificationValidator,
    # Compiler
    CompiledSpecification,
    BehaviorPromptGenerator,
    SpecificationCompiler,
    SpecificationRegistry,
    get_default_registry,
    set_specs_directory,
    # Agent
    ExecutionResult,
    LimitEnforcer,
    LimitExceededError,
    SpecificationEnforcedAgent,
    MockAgent,
    create_enforced_agent,
)


# =============================================================================
# AST Tests
# =============================================================================

class TestPathExpr:
    """Tests for PathExpr."""

    def test_simple_path(self):
        """Test simple path evaluation."""
        path = PathExpr(["output"])
        data = {"output": "hello"}
        assert path.evaluate(data) == "hello"

    def test_nested_path(self):
        """Test nested path evaluation."""
        path = PathExpr(["output", "claims", "source"])
        data = {"output": {"claims": {"source": "wikipedia"}}}
        assert path.evaluate(data) == "wikipedia"

    def test_missing_path(self):
        """Test missing path returns None."""
        path = PathExpr(["output", "missing"])
        data = {"output": {}}
        assert path.evaluate(data) is None

    def test_list_index_path(self):
        """Test list index in path."""
        path = PathExpr(["items", "0", "name"])
        data = {"items": [{"name": "first"}, {"name": "second"}]}
        assert path.evaluate(data) == "first"

    def test_str_representation(self):
        """Test string representation."""
        path = PathExpr(["output", "claims", "source"])
        assert str(path) == "output.claims.source"


class TestDateExpr:
    """Tests for DateExpr."""

    def test_today(self):
        """Test TODAY evaluation."""
        expr = DateExpr(base="TODAY", offset_value=0)
        result = expr.evaluate()
        assert result.date() == datetime.now().date()

    def test_today_minus_days(self):
        """Test TODAY - N DAYS."""
        expr = DateExpr(base="TODAY", offset_value=-30, offset_unit="DAYS")
        result = expr.evaluate()
        expected = datetime.now() - timedelta(days=30)
        assert abs((result - expected).total_seconds()) < 1

    def test_today_plus_hours(self):
        """Test TODAY + N HOURS."""
        expr = DateExpr(base="TODAY", offset_value=24, offset_unit="HOURS")
        result = expr.evaluate()
        expected = datetime.now() + timedelta(hours=24)
        assert abs((result - expected).total_seconds()) < 1


class TestLiteralValue:
    """Tests for LiteralValue."""

    def test_string_literal(self):
        """Test string literal parsing."""
        lit = LiteralValue.from_parsed('"hello"')
        assert lit.value == "hello"
        assert lit.value_type == "string"

    def test_boolean_true(self):
        """Test TRUE literal."""
        lit = LiteralValue.from_parsed("TRUE")
        assert lit.value is True
        assert lit.value_type == "boolean"

    def test_boolean_false(self):
        """Test FALSE literal."""
        lit = LiteralValue.from_parsed("FALSE")
        assert lit.value is False
        assert lit.value_type == "boolean"

    def test_null_literal(self):
        """Test NULL literal."""
        lit = LiteralValue.from_parsed("NULL")
        assert lit.value is None
        assert lit.value_type == "null"

    def test_number_literal(self):
        """Test number literal."""
        lit = LiteralValue.from_parsed(42)
        assert lit.value == 42
        assert lit.value_type == "number"


# =============================================================================
# Parser Tests
# =============================================================================

class TestSpecificationParser:
    """Tests for SpecificationParser."""

    @pytest.fixture
    def parser(self):
        return SpecificationParser()

    def test_parse_minimal_spec(self, parser):
        """Test parsing minimal specification."""
        spec_text = """
        AGENT MinimalAgent:
            TIER: haiku
        """
        spec = parser.parse(spec_text)
        assert spec.agent_name == "MinimalAgent"
        assert spec.tier == TierLevel.HAIKU

    def test_parse_with_tools(self, parser):
        """Test parsing tools declaration."""
        spec_text = """
        AGENT ToolAgent:
            TIER: sonnet
            TOOLS: [WebSearch, Read, Write]
        """
        spec = parser.parse(spec_text)
        assert spec.tools == ["WebSearch", "Read", "Write"]

    def test_parse_output_constraints(self, parser):
        """Test parsing output constraints."""
        spec_text = """
        AGENT ConstraintAgent:
            TIER: sonnet

            OUTPUT MUST SATISFY:
                confidence IN RANGE [0.0, 1.0]
                status IN ["success", "error", "pending"]
                output IS NOT_EMPTY
        """
        spec = parser.parse(spec_text)
        assert len(spec.output_constraints) == 3

    def test_parse_comparison_constraint(self, parser):
        """Test parsing comparison constraints."""
        spec_text = """
        AGENT CompAgent:
            TIER: sonnet

            OUTPUT MUST SATISFY:
                count >= 5
                status == "ok"
        """
        spec = parser.parse(spec_text)
        assert len(spec.output_constraints) == 2

    def test_parse_quantified_constraint(self, parser):
        """Test parsing forall/exists constraints."""
        spec_text = """
        AGENT QuantAgent:
            TIER: sonnet

            OUTPUT MUST SATISFY:
                forall item in items: item.valid == TRUE
                exists source in sources: source.verified == TRUE
        """
        spec = parser.parse(spec_text)
        assert len(spec.output_constraints) == 2
        assert isinstance(spec.output_constraints[0], QuantifiedConstraint)
        assert spec.output_constraints[0].quantifier == Quantifier.FORALL

    def test_parse_conditional_constraint(self, parser):
        """Test parsing conditional constraints."""
        spec_text = """
        AGENT CondAgent:
            TIER: sonnet

            OUTPUT MUST SATISFY:
                if confidence >= 0.9: sources IS NOT_EMPTY
        """
        spec = parser.parse(spec_text)
        assert len(spec.output_constraints) == 1
        assert isinstance(spec.output_constraints[0], ConditionalConstraint)

    def test_parse_behavior_rules(self, parser):
        """Test parsing behavior section."""
        spec_text = """
        AGENT BehaviorAgent:
            TIER: sonnet

            BEHAVIOR:
                PREFER accuracy OVER speed
                NEVER make unsupported claims
                ALWAYS cite sources
        """
        spec = parser.parse(spec_text)
        assert len(spec.behavior_rules) == 3
        assert isinstance(spec.behavior_rules[0], PreferRule)
        assert isinstance(spec.behavior_rules[1], NeverRule)
        assert isinstance(spec.behavior_rules[2], AlwaysRule)

    def test_parse_limits(self, parser):
        """Test parsing limits section."""
        spec_text = """
        AGENT LimitAgent:
            TIER: sonnet

            LIMITS:
                max_tool_calls: 50
                timeout_seconds: 300
        """
        spec = parser.parse(spec_text)
        assert spec.limits == {"max_tool_calls": 50, "timeout_seconds": 300}

    def test_parse_complete_spec(self, parser):
        """Test parsing complete specification."""
        spec_text = """
        AGENT CompleteAgent:
            TIER: opus
            TOOLS: [WebSearch, Read]

            OUTPUT MUST SATISFY:
                confidence IN RANGE [0.0, 1.0]
                output IS NOT_EMPTY

            BEHAVIOR:
                ALWAYS be thorough
                NEVER skip validation

            LIMITS:
                max_tool_calls: 100
                timeout_seconds: 600
        """
        spec = parser.parse(spec_text)
        assert spec.agent_name == "CompleteAgent"
        assert spec.tier == TierLevel.OPUS
        assert len(spec.tools) == 2
        assert len(spec.output_constraints) == 2
        assert len(spec.behavior_rules) == 2
        assert len(spec.limits) == 2

    def test_parse_missing_agent(self, parser):
        """Test error on missing AGENT declaration."""
        spec_text = """
        TIER: sonnet
        """
        with pytest.raises(ParseError):
            parser.parse(spec_text)


# =============================================================================
# Validator Tests
# =============================================================================

class TestConstraintValidator:
    """Tests for ConstraintValidator."""

    @pytest.fixture
    def validator(self):
        return ConstraintValidator()

    def test_comparison_equal(self, validator):
        """Test equality comparison."""
        constraint = ComparisonConstraint(
            PathExpr(["status"]),
            Comparator.EQ,
            LiteralValue("success", "string")
        )
        result = validator.validate(constraint, {"status": "success"})
        assert result.valid

    def test_comparison_not_equal(self, validator):
        """Test inequality comparison."""
        constraint = ComparisonConstraint(
            PathExpr(["status"]),
            Comparator.NE,
            LiteralValue("error", "string")
        )
        result = validator.validate(constraint, {"status": "success"})
        assert result.valid

    def test_comparison_less_than(self, validator):
        """Test less than comparison."""
        constraint = ComparisonConstraint(
            PathExpr(["count"]),
            Comparator.LT,
            LiteralValue(10, "number")
        )
        result = validator.validate(constraint, {"count": 5})
        assert result.valid

    def test_comparison_greater_equal(self, validator):
        """Test greater than or equal comparison."""
        constraint = ComparisonConstraint(
            PathExpr(["score"]),
            Comparator.GE,
            LiteralValue(80, "number")
        )
        result = validator.validate(constraint, {"score": 85})
        assert result.valid

    def test_comparison_failure(self, validator):
        """Test failed comparison."""
        constraint = ComparisonConstraint(
            PathExpr(["status"]),
            Comparator.EQ,
            LiteralValue("success", "string")
        )
        result = validator.validate(constraint, {"status": "error"})
        assert not result.valid
        assert len(result.errors) > 0

    def test_type_string(self, validator):
        """Test string type check."""
        constraint = TypeConstraint(PathExpr(["name"]), TypeCheck.STRING)
        result = validator.validate(constraint, {"name": "hello"})
        assert result.valid

    def test_type_number(self, validator):
        """Test number type check."""
        constraint = TypeConstraint(PathExpr(["count"]), TypeCheck.NUMBER)
        result = validator.validate(constraint, {"count": 42})
        assert result.valid

    def test_type_boolean(self, validator):
        """Test boolean type check."""
        constraint = TypeConstraint(PathExpr(["active"]), TypeCheck.BOOLEAN)
        result = validator.validate(constraint, {"active": True})
        assert result.valid

    def test_type_list(self, validator):
        """Test list type check."""
        constraint = TypeConstraint(PathExpr(["items"]), TypeCheck.LIST)
        result = validator.validate(constraint, {"items": [1, 2, 3]})
        assert result.valid

    def test_type_object(self, validator):
        """Test object type check."""
        constraint = TypeConstraint(PathExpr(["data"]), TypeCheck.OBJECT)
        result = validator.validate(constraint, {"data": {"key": "value"}})
        assert result.valid

    def test_type_not_empty_string(self, validator):
        """Test not empty check on string."""
        constraint = TypeConstraint(PathExpr(["text"]), TypeCheck.NOT_EMPTY)
        result = validator.validate(constraint, {"text": "hello"})
        assert result.valid

    def test_type_not_empty_failure(self, validator):
        """Test not empty check failure."""
        constraint = TypeConstraint(PathExpr(["text"]), TypeCheck.NOT_EMPTY)
        result = validator.validate(constraint, {"text": ""})
        assert not result.valid

    def test_type_valid_url(self, validator):
        """Test valid URL check."""
        constraint = TypeConstraint(PathExpr(["url"]), TypeCheck.VALID_URL)
        result = validator.validate(constraint, {"url": "https://example.com"})
        assert result.valid

    def test_type_valid_url_failure(self, validator):
        """Test invalid URL check."""
        constraint = TypeConstraint(PathExpr(["url"]), TypeCheck.VALID_URL)
        result = validator.validate(constraint, {"url": "not-a-url"})
        assert not result.valid

    def test_type_valid_email(self, validator):
        """Test valid email check."""
        constraint = TypeConstraint(PathExpr(["email"]), TypeCheck.VALID_EMAIL)
        result = validator.validate(constraint, {"email": "test@example.com"})
        assert result.valid

    def test_type_valid_email_failure(self, validator):
        """Test invalid email check."""
        constraint = TypeConstraint(PathExpr(["email"]), TypeCheck.VALID_EMAIL)
        result = validator.validate(constraint, {"email": "not-an-email"})
        assert not result.valid

    def test_range_in_bounds(self, validator):
        """Test range constraint within bounds."""
        constraint = RangeConstraint(PathExpr(["confidence"]), 0.0, 1.0)
        result = validator.validate(constraint, {"confidence": 0.75})
        assert result.valid

    def test_range_at_min(self, validator):
        """Test range constraint at minimum."""
        constraint = RangeConstraint(PathExpr(["score"]), 0, 100)
        result = validator.validate(constraint, {"score": 0})
        assert result.valid

    def test_range_at_max(self, validator):
        """Test range constraint at maximum."""
        constraint = RangeConstraint(PathExpr(["score"]), 0, 100)
        result = validator.validate(constraint, {"score": 100})
        assert result.valid

    def test_range_out_of_bounds(self, validator):
        """Test range constraint out of bounds."""
        constraint = RangeConstraint(PathExpr(["confidence"]), 0.0, 1.0)
        result = validator.validate(constraint, {"confidence": 1.5})
        assert not result.valid

    def test_in_list_success(self, validator):
        """Test in-list constraint success."""
        constraint = InListConstraint(
            PathExpr(["status"]),
            [LiteralValue("pending", "string"), LiteralValue("complete", "string")]
        )
        result = validator.validate(constraint, {"status": "pending"})
        assert result.valid

    def test_in_list_failure(self, validator):
        """Test in-list constraint failure."""
        constraint = InListConstraint(
            PathExpr(["status"]),
            [LiteralValue("pending", "string"), LiteralValue("complete", "string")]
        )
        result = validator.validate(constraint, {"status": "unknown"})
        assert not result.valid

    def test_not_constraint(self, validator):
        """Test NOT constraint."""
        inner = ComparisonConstraint(
            PathExpr(["status"]),
            Comparator.EQ,
            LiteralValue("error", "string")
        )
        constraint = NotConstraint(inner)
        result = validator.validate(constraint, {"status": "success"})
        assert result.valid

    def test_and_constraint(self, validator):
        """Test AND constraint."""
        left = ComparisonConstraint(
            PathExpr(["a"]),
            Comparator.GT,
            LiteralValue(0, "number")
        )
        right = ComparisonConstraint(
            PathExpr(["b"]),
            Comparator.GT,
            LiteralValue(0, "number")
        )
        constraint = AndConstraint(left, right)
        result = validator.validate(constraint, {"a": 5, "b": 10})
        assert result.valid

    def test_and_constraint_failure(self, validator):
        """Test AND constraint failure."""
        left = ComparisonConstraint(
            PathExpr(["a"]),
            Comparator.GT,
            LiteralValue(0, "number")
        )
        right = ComparisonConstraint(
            PathExpr(["b"]),
            Comparator.GT,
            LiteralValue(0, "number")
        )
        constraint = AndConstraint(left, right)
        result = validator.validate(constraint, {"a": 5, "b": -1})
        assert not result.valid

    def test_or_constraint(self, validator):
        """Test OR constraint."""
        left = ComparisonConstraint(
            PathExpr(["a"]),
            Comparator.GT,
            LiteralValue(10, "number")
        )
        right = ComparisonConstraint(
            PathExpr(["b"]),
            Comparator.GT,
            LiteralValue(10, "number")
        )
        constraint = OrConstraint(left, right)
        result = validator.validate(constraint, {"a": 5, "b": 15})
        assert result.valid

    def test_forall_constraint(self, validator):
        """Test forall quantifier."""
        inner = ComparisonConstraint(
            PathExpr(["x"]),
            Comparator.GT,
            LiteralValue(0, "number")
        )
        constraint = QuantifiedConstraint(
            Quantifier.FORALL,
            "x",
            PathExpr(["items"]),
            inner
        )
        result = validator.validate(constraint, {"items": [1, 2, 3]})
        assert result.valid

    def test_forall_constraint_failure(self, validator):
        """Test forall quantifier failure."""
        inner = ComparisonConstraint(
            PathExpr(["x"]),
            Comparator.GT,
            LiteralValue(0, "number")
        )
        constraint = QuantifiedConstraint(
            Quantifier.FORALL,
            "x",
            PathExpr(["items"]),
            inner
        )
        result = validator.validate(constraint, {"items": [1, -2, 3]})
        assert not result.valid

    def test_exists_constraint(self, validator):
        """Test exists quantifier."""
        inner = ComparisonConstraint(
            PathExpr(["x"]),
            Comparator.GT,
            LiteralValue(5, "number")
        )
        constraint = QuantifiedConstraint(
            Quantifier.EXISTS,
            "x",
            PathExpr(["items"]),
            inner
        )
        result = validator.validate(constraint, {"items": [1, 2, 10]})
        assert result.valid

    def test_exists_constraint_failure(self, validator):
        """Test exists quantifier failure."""
        inner = ComparisonConstraint(
            PathExpr(["x"]),
            Comparator.GT,
            LiteralValue(100, "number")
        )
        constraint = QuantifiedConstraint(
            Quantifier.EXISTS,
            "x",
            PathExpr(["items"]),
            inner
        )
        result = validator.validate(constraint, {"items": [1, 2, 10]})
        assert not result.valid

    def test_conditional_constraint_applies(self, validator):
        """Test conditional constraint when condition applies."""
        condition = ComparisonCondition(
            PathExpr(["confidence"]),
            Comparator.GE,
            LiteralValue(0.9, "number")
        )
        consequence = TypeConstraint(PathExpr(["sources"]), TypeCheck.NOT_EMPTY)
        constraint = ConditionalConstraint(condition, consequence)
        result = validator.validate(constraint, {
            "confidence": 0.95,
            "sources": ["source1"]
        })
        assert result.valid

    def test_conditional_constraint_not_applies(self, validator):
        """Test conditional constraint when condition doesn't apply."""
        condition = ComparisonCondition(
            PathExpr(["confidence"]),
            Comparator.GE,
            LiteralValue(0.9, "number")
        )
        consequence = TypeConstraint(PathExpr(["sources"]), TypeCheck.NOT_EMPTY)
        constraint = ConditionalConstraint(condition, consequence)
        # Condition not met, so constraint passes even with empty sources
        result = validator.validate(constraint, {
            "confidence": 0.5,
            "sources": []
        })
        assert result.valid


class TestSpecificationValidator:
    """Tests for SpecificationValidator."""

    def test_validate_all_pass(self):
        """Test validation when all constraints pass."""
        spec = AgentSpecification(
            agent_name="TestAgent",
            output_constraints=[
                RangeConstraint(PathExpr(["confidence"]), 0.0, 1.0),
                TypeConstraint(PathExpr(["output"]), TypeCheck.NOT_EMPTY),
            ]
        )
        validator = SpecificationValidator(spec)
        results = validator.validate({"confidence": 0.8, "output": "result"})
        assert all(r.valid for r in results)

    def test_validate_raises_on_violation(self):
        """Test validation raises on violation."""
        spec = AgentSpecification(
            agent_name="TestAgent",
            output_constraints=[
                RangeConstraint(PathExpr(["confidence"]), 0.0, 1.0),
            ]
        )
        validator = SpecificationValidator(spec)
        with pytest.raises(SpecificationViolation) as exc_info:
            validator.validate({"confidence": 1.5})
        assert "TestAgent" in str(exc_info.value)

    def test_validate_soft_no_raise(self):
        """Test soft validation doesn't raise."""
        spec = AgentSpecification(
            agent_name="TestAgent",
            output_constraints=[
                RangeConstraint(PathExpr(["confidence"]), 0.0, 1.0),
            ]
        )
        validator = SpecificationValidator(spec)
        results = validator.validate_soft({"confidence": 1.5})
        assert not results[0].valid


# =============================================================================
# Compiler Tests
# =============================================================================

class TestBehaviorPromptGenerator:
    """Tests for BehaviorPromptGenerator."""

    @pytest.fixture
    def generator(self):
        return BehaviorPromptGenerator()

    def test_empty_rules(self, generator):
        """Test empty rules generates empty prompt."""
        result = generator.generate([])
        assert result == ""

    def test_prefer_rule(self, generator):
        """Test PREFER rule generation."""
        rules = [PreferRule("accuracy", "speed")]
        result = generator.generate(rules)
        assert "Prefer accuracy over speed" in result

    def test_never_rule(self, generator):
        """Test NEVER rule generation."""
        rules = [NeverRule("make unsupported claims")]
        result = generator.generate(rules)
        assert "Never make unsupported claims" in result

    def test_always_rule(self, generator):
        """Test ALWAYS rule generation."""
        rules = [AlwaysRule("cite sources")]
        result = generator.generate(rules)
        assert "Always cite sources" in result

    def test_when_rule(self, generator):
        """Test WHEN rule generation."""
        condition = ComparisonCondition(
            PathExpr(["confidence"]),
            Comparator.LT,
            LiteralValue(0.5, "number")
        )
        rules = [WhenRule(condition, "ask for clarification")]
        result = generator.generate(rules)
        assert "When" in result
        assert "ask for clarification" in result

    def test_multiple_rules(self, generator):
        """Test multiple rules generation."""
        rules = [
            PreferRule("facts", "opinions"),
            NeverRule("lie"),
            AlwaysRule("be helpful"),
        ]
        result = generator.generate(rules)
        assert "Behavioral Guidelines" in result
        assert "Prefer facts over opinions" in result
        assert "Never lie" in result
        assert "Always be helpful" in result


class TestSpecificationCompiler:
    """Tests for SpecificationCompiler."""

    @pytest.fixture
    def compiler(self):
        return SpecificationCompiler()

    def test_compile_basic(self, compiler):
        """Test basic compilation."""
        spec_text = """
        AGENT BasicAgent:
            TIER: sonnet
        """
        compiled = compiler.compile(spec_text)
        assert compiled.agent_name == "BasicAgent"
        assert compiled.tier == TierLevel.SONNET

    def test_compile_with_constraints(self, compiler):
        """Test compilation with constraints."""
        spec_text = """
        AGENT ConstraintAgent:
            TIER: sonnet

            OUTPUT MUST SATISFY:
                confidence IN RANGE [0.0, 1.0]
        """
        compiled = compiler.compile(spec_text)
        assert compiled.validator is not None
        assert len(compiled.raw_spec.output_constraints) == 1

    def test_compile_with_behavior(self, compiler):
        """Test compilation with behavior rules."""
        spec_text = """
        AGENT BehaviorAgent:
            TIER: sonnet

            BEHAVIOR:
                ALWAYS be helpful
                NEVER be harmful
        """
        compiled = compiler.compile(spec_text)
        assert "Behavioral Guidelines" in compiled.behavior_prompt
        assert "Always be helpful" in compiled.behavior_prompt

    def test_compile_with_limits(self, compiler):
        """Test compilation with limits."""
        spec_text = """
        AGENT LimitAgent:
            TIER: sonnet

            LIMITS:
                max_tool_calls: 50
        """
        compiled = compiler.compile(spec_text)
        assert compiled.limits == {"max_tool_calls": 50}

    def test_compile_file(self, compiler):
        """Test compiling from file."""
        # Create temp file and close it before using to avoid Windows file locking
        fd, temp_path = tempfile.mkstemp(suffix=".spec")
        try:
            with os.fdopen(fd, "w") as f:
                f.write("""
            AGENT FileAgent:
                TIER: haiku
            """)
            compiled = compiler.compile_file(temp_path)
            assert compiled.agent_name == "FileAgent"
        finally:
            try:
                os.unlink(temp_path)
            except PermissionError:
                pass  # Windows may still have file locked

    def test_compile_file_not_found(self, compiler):
        """Test error on file not found."""
        with pytest.raises(FileNotFoundError):
            compiler.compile_file("/nonexistent/path.spec")


class TestSpecificationRegistry:
    """Tests for SpecificationRegistry."""

    def test_register_and_load(self):
        """Test registering and loading spec."""
        registry = SpecificationRegistry()
        spec_text = """
        AGENT RegisteredAgent:
            TIER: sonnet
        """
        compiled = registry.register("test", spec_text)
        assert compiled.agent_name == "RegisteredAgent"

        loaded = registry.load("test")
        assert loaded is not None
        assert loaded.agent_name == "RegisteredAgent"

    def test_get_raises_on_missing(self):
        """Test get raises on missing spec."""
        registry = SpecificationRegistry()
        with pytest.raises(KeyError):
            registry.get("nonexistent")

    def test_list_specs(self):
        """Test listing specs."""
        registry = SpecificationRegistry()
        registry.register("spec1", "AGENT Agent1:\n    TIER: sonnet")
        registry.register("spec2", "AGENT Agent2:\n    TIER: haiku")
        specs = registry.list_specs()
        assert "spec1" in specs
        assert "spec2" in specs

    def test_clear_cache(self):
        """Test cache clearing."""
        registry = SpecificationRegistry()
        registry.register("test", "AGENT TestAgent:\n    TIER: sonnet")
        assert registry.load("test") is not None
        registry.clear_cache()
        assert registry.load("test") is None

    def test_load_from_directory(self):
        """Test loading from specs directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            spec_file = Path(tmpdir) / "myagent.spec"
            spec_file.write_text("AGENT MyAgent:\n    TIER: opus")

            registry = SpecificationRegistry(tmpdir)
            loaded = registry.load("myagent")
            assert loaded is not None
            assert loaded.agent_name == "MyAgent"


# =============================================================================
# Agent Tests
# =============================================================================

class TestLimitEnforcer:
    """Tests for LimitEnforcer."""

    def test_check_limit_within(self):
        """Test limit check within bounds."""
        enforcer = LimitEnforcer({"max_calls": 10})
        for _ in range(5):
            assert enforcer.check_limit("max_calls")

    def test_check_limit_exceeded(self):
        """Test limit exceeded raises error."""
        enforcer = LimitEnforcer({"max_calls": 3})
        enforcer.check_limit("max_calls")
        enforcer.check_limit("max_calls")
        enforcer.check_limit("max_calls")
        with pytest.raises(LimitExceededError) as exc_info:
            enforcer.check_limit("max_calls")
        assert exc_info.value.limit_name == "max_calls"
        assert exc_info.value.limit_value == 3

    def test_check_unknown_limit(self):
        """Test checking unknown limit passes."""
        enforcer = LimitEnforcer({"max_calls": 10})
        assert enforcer.check_limit("unknown_limit")

    def test_check_timeout(self):
        """Test timeout check."""
        enforcer = LimitEnforcer({"timeout_seconds": 60})
        assert enforcer.check_timeout()

    def test_get_usage(self):
        """Test getting usage stats."""
        enforcer = LimitEnforcer({"max_calls": 10})
        enforcer.check_limit("max_calls")
        enforcer.check_limit("max_calls")
        usage = enforcer.get_usage()
        assert usage["max_calls"]["current"] == 2
        assert usage["max_calls"]["limit"] == 10

    def test_reset(self):
        """Test reset counters."""
        enforcer = LimitEnforcer({"max_calls": 10})
        enforcer.check_limit("max_calls", 5)
        enforcer.reset()
        assert enforcer.counters["max_calls"] == 0


class TestMockAgent:
    """Tests for MockAgent."""

    @pytest.mark.asyncio
    async def test_execute(self):
        """Test mock agent execution."""
        agent = MockAgent({"output": "test result", "confidence": 0.9})
        result = await agent.execute("test task")
        assert result["output"] == "test result"
        assert result["confidence"] == 0.9
        assert "test task" in agent.calls

    @pytest.mark.asyncio
    async def test_default_response(self):
        """Test mock agent default response."""
        agent = MockAgent()
        result = await agent.execute("task")
        assert "output" in result
        assert "confidence" in result


class TestSpecificationEnforcedAgent:
    """Tests for SpecificationEnforcedAgent."""

    @pytest.fixture
    def mock_agent(self):
        return MockAgent({"confidence": 0.8, "output": "result"})

    @pytest.fixture
    def compiled_spec(self):
        compiler = SpecificationCompiler()
        return compiler.compile("""
        AGENT TestAgent:
            TIER: sonnet

            OUTPUT MUST SATISFY:
                confidence IN RANGE [0.0, 1.0]

            BEHAVIOR:
                ALWAYS be helpful

            LIMITS:
                max_tool_calls: 10
        """)

    @pytest.mark.asyncio
    async def test_execute_valid_output(self, mock_agent, compiled_spec):
        """Test execution with valid output."""
        enforced = SpecificationEnforcedAgent(mock_agent, compiled_spec)
        result = await enforced.execute("test task")
        assert all(r.valid for r in result.validation_results)
        assert result.output["confidence"] == 0.8

    @pytest.mark.asyncio
    async def test_execute_tracks_stats(self, mock_agent, compiled_spec):
        """Test execution tracking."""
        enforced = SpecificationEnforcedAgent(mock_agent, compiled_spec)
        await enforced.execute("task1")
        await enforced.execute("task2")
        stats = enforced.get_stats()
        assert stats["execution_count"] == 2
        assert stats["violation_count"] == 0

    @pytest.mark.asyncio
    async def test_execute_invalid_output_strict(self):
        """Test execution with invalid output in strict mode."""
        agent = MockAgent({"confidence": 1.5, "output": "result"})
        compiler = SpecificationCompiler()
        spec = compiler.compile("""
        AGENT TestAgent:
            TIER: sonnet

            OUTPUT MUST SATISFY:
                confidence IN RANGE [0.0, 1.0]
        """)
        enforced = SpecificationEnforcedAgent(agent, spec, strict=True)
        with pytest.raises(SpecificationViolation):
            await enforced.execute("test task")

    @pytest.mark.asyncio
    async def test_execute_invalid_output_nonstrict(self):
        """Test execution with invalid output in non-strict mode."""
        agent = MockAgent({"confidence": 1.5, "output": "result"})
        compiler = SpecificationCompiler()
        spec = compiler.compile("""
        AGENT TestAgent:
            TIER: sonnet

            OUTPUT MUST SATISFY:
                confidence IN RANGE [0.0, 1.0]
        """)
        enforced = SpecificationEnforcedAgent(agent, spec, strict=False)
        result = await enforced.execute("test task")
        assert not all(r.valid for r in result.validation_results)

    @pytest.mark.asyncio
    async def test_prompt_augmentation(self, mock_agent, compiled_spec):
        """Test prompt is augmented with behavior."""
        enforced = SpecificationEnforcedAgent(mock_agent, compiled_spec)
        await enforced.execute("original task")
        # Check that behavior was added to the prompt
        assert len(mock_agent.calls) == 1
        augmented_prompt = mock_agent.calls[0]
        assert "Behavioral Guidelines" in augmented_prompt
        assert "original task" in augmented_prompt


class TestExecutionResult:
    """Tests for ExecutionResult."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = ExecutionResult(
            output={"test": "output"},
            validation_results=[ValidationResult(valid=True)],
            execution_time_ms=100,
            limits_enforced={"max_calls": 10},
            spec_name="TestAgent",
        )
        d = result.to_dict()
        assert d["output"] == {"test": "output"}
        assert d["execution_time_ms"] == 100
        assert d["spec_name"] == "TestAgent"
        assert d["valid"] is True

    def test_valid_flag(self):
        """Test valid flag in to_dict."""
        result = ExecutionResult(
            output={},
            validation_results=[
                ValidationResult(valid=True),
                ValidationResult(valid=False, errors=["error"]),
            ],
        )
        d = result.to_dict()
        assert d["valid"] is False


class TestCreateEnforcedAgent:
    """Tests for create_enforced_agent helper."""

    @pytest.mark.asyncio
    async def test_create_and_execute(self):
        """Test creating and executing enforced agent."""
        agent = MockAgent({"confidence": 0.9, "output": "result"})
        spec_text = """
        AGENT QuickAgent:
            TIER: haiku

            OUTPUT MUST SATISFY:
                confidence IN RANGE [0.0, 1.0]
        """
        enforced = create_enforced_agent(agent, spec_text)
        result = await enforced.execute("test")
        assert all(r.valid for r in result.validation_results)


# =============================================================================
# Integration Tests
# =============================================================================

class TestSpecificationIntegration:
    """Integration tests for the full specification workflow."""

    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test complete specification workflow."""
        # Define a specification
        spec_text = """
        AGENT ResearchAgent:
            TIER: sonnet
            TOOLS: [WebSearch, Read]

            OUTPUT MUST SATISFY:
                confidence IN RANGE [0.0, 1.0]
                summary IS NOT_EMPTY
                forall source in sources: source IS STRING

            BEHAVIOR:
                PREFER primary sources OVER secondary sources
                NEVER make unsupported claims
                ALWAYS cite sources

            LIMITS:
                max_tool_calls: 50
                timeout_seconds: 300
        """

        # Compile
        compiler = SpecificationCompiler()
        compiled = compiler.compile(spec_text)

        assert compiled.agent_name == "ResearchAgent"
        assert compiled.tier == TierLevel.SONNET
        assert "WebSearch" in compiled.tools
        assert compiled.limits["max_tool_calls"] == 50

        # Create mock agent with valid output
        agent = MockAgent({
            "confidence": 0.85,
            "summary": "Research findings",
            "sources": ["source1", "source2"],
        })

        # Wrap with specification enforcement
        enforced = SpecificationEnforcedAgent(agent, compiled)

        # Execute
        result = await enforced.execute("Research AI safety")

        # Verify
        assert all(r.valid for r in result.validation_results)
        assert result.output["confidence"] == 0.85
        assert result.spec_name == "ResearchAgent"

    @pytest.mark.asyncio
    async def test_forall_validation(self):
        """Test forall constraint validation in integration."""
        spec_text = """
        AGENT URLAgent:
            TIER: sonnet

            OUTPUT MUST SATISFY:
                forall url in urls: url IS VALID_URL
        """

        compiler = SpecificationCompiler()
        compiled = compiler.compile(spec_text)

        # Valid URLs
        agent = MockAgent({"urls": ["https://example.com", "https://test.org"]})
        enforced = SpecificationEnforcedAgent(agent, compiled)
        result = await enforced.execute("test")
        assert all(r.valid for r in result.validation_results)

        # Invalid URLs
        agent2 = MockAgent({"urls": ["https://example.com", "not-a-url"]})
        enforced2 = SpecificationEnforcedAgent(agent2, compiled, strict=False)
        result2 = await enforced2.execute("test")
        assert not all(r.valid for r in result2.validation_results)

    @pytest.mark.asyncio
    async def test_conditional_validation(self):
        """Test conditional constraint validation in integration."""
        # Use numeric comparison which is more reliable in parsing
        spec_text = """
        AGENT CondAgent:
            TIER: sonnet

            OUTPUT MUST SATISFY:
                if confidence >= 0.9: source_count >= 3
        """

        compiler = SpecificationCompiler()
        compiled = compiler.compile(spec_text)

        # High confidence, enough sources - should pass
        agent1 = MockAgent({"confidence": 0.95, "source_count": 5})
        enforced1 = SpecificationEnforcedAgent(agent1, compiled)
        result1 = await enforced1.execute("test")
        assert all(r.valid for r in result1.validation_results)

        # Low confidence, not enough sources - should pass (condition not met)
        agent2 = MockAgent({"confidence": 0.5, "source_count": 1})
        enforced2 = SpecificationEnforcedAgent(agent2, compiled)
        result2 = await enforced2.execute("test")
        assert all(r.valid for r in result2.validation_results)

        # High confidence, not enough sources - should fail
        agent3 = MockAgent({"confidence": 0.95, "source_count": 1})
        enforced3 = SpecificationEnforcedAgent(agent3, compiled, strict=False)
        result3 = await enforced3.execute("test")
        assert not all(r.valid for r in result3.validation_results)


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_spec(self):
        """Test minimal empty spec."""
        parser = SpecificationParser()
        spec = parser.parse("AGENT Empty:\n    TIER: haiku")
        assert spec.agent_name == "Empty"
        assert spec.output_constraints == []
        assert spec.behavior_rules == []

    def test_nested_path_validation(self):
        """Test deeply nested path validation."""
        validator = ConstraintValidator()
        constraint = TypeConstraint(
            PathExpr(["level1", "level2", "level3", "value"]),
            TypeCheck.STRING
        )
        data = {"level1": {"level2": {"level3": {"value": "deep"}}}}
        result = validator.validate(constraint, data)
        assert result.valid

    def test_missing_nested_path(self):
        """Test missing nested path."""
        validator = ConstraintValidator()
        constraint = TypeConstraint(
            PathExpr(["level1", "missing", "value"]),
            TypeCheck.STRING
        )
        data = {"level1": {}}
        result = validator.validate(constraint, data)
        assert not result.valid

    @pytest.mark.asyncio
    async def test_agent_with_run_method(self):
        """Test wrapping agent with run method instead of execute."""
        class RunAgent:
            async def run(self, task: str):
                return {"output": "from run", "confidence": 0.9}

        compiler = SpecificationCompiler()
        spec = compiler.compile("""
        AGENT RunAgent:
            TIER: sonnet

            OUTPUT MUST SATISFY:
                confidence IN RANGE [0.0, 1.0]
        """)
        enforced = SpecificationEnforcedAgent(RunAgent(), spec)
        result = await enforced.execute("test")
        assert result.output["output"] == "from run"

    @pytest.mark.asyncio
    async def test_agent_with_call_method(self):
        """Test wrapping callable agent."""
        class CallableAgent:
            async def __call__(self, task: str):
                return {"output": "from call", "confidence": 0.7}

        compiler = SpecificationCompiler()
        spec = compiler.compile("""
        AGENT CallAgent:
            TIER: sonnet

            OUTPUT MUST SATISFY:
                confidence IN RANGE [0.0, 1.0]
        """)
        enforced = SpecificationEnforcedAgent(CallableAgent(), spec)
        result = await enforced.execute("test")
        assert result.output["output"] == "from call"

    @pytest.mark.asyncio
    async def test_agent_returns_non_dict(self):
        """Test agent that returns non-dict output."""
        class StringAgent:
            async def execute(self, task: str):
                return "string result"

        compiler = SpecificationCompiler()
        spec = compiler.compile("""
        AGENT StringAgent:
            TIER: sonnet
        """)
        enforced = SpecificationEnforcedAgent(StringAgent(), spec)
        result = await enforced.execute("test")
        assert result.output == {"output": "string result"}

    def test_specification_to_dict(self):
        """Test AgentSpecification to_dict."""
        spec = AgentSpecification(
            agent_name="TestAgent",
            tier=TierLevel.OPUS,
            tools=["Tool1", "Tool2"],
            limits={"max_calls": 10},
        )
        d = spec.to_dict()
        assert d["agent_name"] == "TestAgent"
        assert d["tier"] == "opus"
        assert d["tools"] == ["Tool1", "Tool2"]

    def test_compiled_spec_to_dict(self):
        """Test CompiledSpecification to_dict."""
        compiler = SpecificationCompiler()
        compiled = compiler.compile("""
        AGENT TestAgent:
            TIER: sonnet
            TOOLS: [Read, Write]

            OUTPUT MUST SATISFY:
                confidence IN RANGE [0.0, 1.0]

            BEHAVIOR:
                ALWAYS be helpful
        """)
        d = compiled.to_dict()
        assert d["agent_name"] == "TestAgent"
        assert d["tier"] == "sonnet"
        assert d["tools"] == ["Read", "Write"]
        assert d["constraint_count"] == 1
        assert d["behavior_rule_count"] == 1

    def test_validation_result_to_dict(self):
        """Test ValidationResult to_dict."""
        result = ValidationResult(
            valid=False,
            constraint="comparison",
            path="output.value",
            errors=["Expected 10, got 5"],
            value=5,
        )
        d = result.to_dict()
        assert d["valid"] is False
        assert d["constraint"] == "comparison"
        assert d["path"] == "output.value"
        assert len(d["errors"]) == 1
