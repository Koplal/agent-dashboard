"""
Specification Compiler.

Compiles parsed specifications into executable components.

Version: 2.6.0
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

from .ast import (
    AgentSpecification,
    TierLevel,
    BehaviorRule,
    PreferRule,
    NeverRule,
    AlwaysRule,
    WhenRule,
    Condition,
    ComparisonCondition,
    TypeCondition,
    CountCondition,
)
from .parser import SpecificationParser, ParseError
from .validators import ConstraintValidator, SpecificationValidator, ValidationResult

logger = logging.getLogger(__name__)


@dataclass
class CompiledSpecification:
    """
    Compiled agent specification ready for enforcement.

    Attributes:
        agent_name: Name of the agent
        tier: Agent tier level
        tools: Allowed tools
        validator: Output validator
        behavior_prompt: Prompt additions from behavior rules
        limits: Runtime limits
        raw_spec: Original specification
    """
    agent_name: str
    tier: TierLevel
    tools: List[str]
    validator: SpecificationValidator
    behavior_prompt: str
    limits: Dict[str, int]
    raw_spec: AgentSpecification

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_name": self.agent_name,
            "tier": self.tier.value,
            "tools": self.tools,
            "limits": self.limits,
            "behavior_prompt_length": len(self.behavior_prompt),
            "constraint_count": len(self.raw_spec.output_constraints),
            "behavior_rule_count": len(self.raw_spec.behavior_rules),
        }


class BehaviorPromptGenerator:
    """
    Generates prompt additions from behavior rules.

    Converts formal behavior specifications into natural language
    instructions for the LLM.
    """

    def generate(self, rules: List[BehaviorRule]) -> str:
        """
        Generate prompt text from behavior rules.

        Args:
            rules: List of behavior rules

        Returns:
            Formatted prompt text
        """
        if not rules:
            return ""

        lines = ["## Behavioral Guidelines", ""]

        for rule in rules:
            line = self._rule_to_prompt(rule)
            if line:
                lines.append(f"- {line}")

        lines.append("")
        return "\n".join(lines)

    def _rule_to_prompt(self, rule: BehaviorRule) -> str:
        """Convert a single rule to prompt text."""
        if isinstance(rule, PreferRule):
            return f"Prefer {rule.preferred} over {rule.over}"

        elif isinstance(rule, NeverRule):
            return f"Never {rule.action}"

        elif isinstance(rule, AlwaysRule):
            return f"Always {rule.action}"

        elif isinstance(rule, WhenRule):
            condition_text = self._condition_to_text(rule.condition)
            return f"When {condition_text}: {rule.action}"

        return ""

    def _condition_to_text(self, condition: Condition) -> str:
        """Convert condition to natural language."""
        if isinstance(condition, ComparisonCondition):
            op_text = {
                "==": "equals",
                "!=": "does not equal",
                "<": "is less than",
                ">": "is greater than",
                "<=": "is at most",
                ">=": "is at least",
            }.get(condition.comparator.value, condition.comparator.value)

            value = condition.value
            if hasattr(value, 'value'):
                value = value.value

            return f"{condition.path} {op_text} {value}"

        elif isinstance(condition, TypeCondition):
            return f"{condition.path} is {condition.type_check.value}"

        elif isinstance(condition, CountCondition):
            return f"count of {condition.path} {condition.comparator.value} {condition.value}"

        return "the condition is met"


class SpecificationCompiler:
    """
    Compiles specification DSL to executable components.

    Handles parsing, validation setup, and prompt generation.

    Example:
        compiler = SpecificationCompiler()
        compiled = compiler.compile(spec_text)

        # Use the compiled spec
        print(compiled.behavior_prompt)
        results = compiled.validator.validate(output)
    """

    def __init__(self):
        """Initialize the compiler."""
        self.parser = SpecificationParser()
        self.prompt_generator = BehaviorPromptGenerator()

    def compile(self, spec_text: str) -> CompiledSpecification:
        """
        Parse and compile a specification.

        Args:
            spec_text: The specification text

        Returns:
            CompiledSpecification ready for use

        Raises:
            ParseError: If parsing fails
            ValueError: If specification is invalid
        """
        # Parse specification
        spec = self.parser.parse(spec_text)

        # Generate behavior prompt
        behavior_prompt = self.prompt_generator.generate(spec.behavior_rules)

        # Create validator
        validator = SpecificationValidator(spec)

        return CompiledSpecification(
            agent_name=spec.agent_name,
            tier=spec.tier,
            tools=spec.tools,
            validator=validator,
            behavior_prompt=behavior_prompt,
            limits=spec.limits,
            raw_spec=spec,
        )

    def compile_file(self, file_path: str) -> CompiledSpecification:
        """
        Compile a specification from a file.

        Args:
            file_path: Path to the specification file

        Returns:
            CompiledSpecification
        """
        path = Path(file_path).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"Specification file not found: {path}")

        spec_text = path.read_text()
        return self.compile(spec_text)


class SpecificationRegistry:
    """
    Registry for compiled specifications.

    Manages loading and caching of agent specifications.
    """

    def __init__(self, specs_dir: Optional[str] = None):
        """
        Initialize the registry.

        Args:
            specs_dir: Directory containing specification files
        """
        self.specs_dir = Path(specs_dir).expanduser() if specs_dir else None
        self.compiler = SpecificationCompiler()
        self._cache: Dict[str, CompiledSpecification] = {}

    def register(self, name: str, spec_text: str) -> CompiledSpecification:
        """
        Register a specification from text.

        Args:
            name: Name for the specification
            spec_text: The specification text

        Returns:
            CompiledSpecification
        """
        compiled = self.compiler.compile(spec_text)
        self._cache[name] = compiled
        return compiled

    def load(self, name: str) -> Optional[CompiledSpecification]:
        """
        Load a specification by name.

        Args:
            name: Specification name

        Returns:
            CompiledSpecification if found, None otherwise
        """
        # Check cache first
        if name in self._cache:
            return self._cache[name]

        # Try to load from file
        if self.specs_dir:
            spec_file = self.specs_dir / f"{name}.spec"
            if spec_file.exists():
                compiled = self.compiler.compile_file(str(spec_file))
                self._cache[name] = compiled
                return compiled

        return None

    def get(self, name: str) -> CompiledSpecification:
        """
        Get a specification by name.

        Args:
            name: Specification name

        Returns:
            CompiledSpecification

        Raises:
            KeyError: If specification not found
        """
        spec = self.load(name)
        if spec is None:
            raise KeyError(f"Specification not found: {name}")
        return spec

    def list_specs(self) -> List[str]:
        """List all registered specification names."""
        names = set(self._cache.keys())

        if self.specs_dir and self.specs_dir.exists():
            for spec_file in self.specs_dir.glob("*.spec"):
                names.add(spec_file.stem)

        return sorted(names)

    def clear_cache(self) -> None:
        """Clear the specification cache."""
        self._cache.clear()


# Default registry instance
_default_registry: Optional[SpecificationRegistry] = None


def get_default_registry() -> SpecificationRegistry:
    """Get or create the default specification registry."""
    global _default_registry
    if _default_registry is None:
        _default_registry = SpecificationRegistry()
    return _default_registry


def set_specs_directory(path: str) -> None:
    """Set the directory for specification files."""
    global _default_registry
    _default_registry = SpecificationRegistry(path)
