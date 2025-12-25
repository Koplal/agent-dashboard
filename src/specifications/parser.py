"""
Specification Parser.

Parses agent specification DSL into AST using Lark or fallback regex parser.

Version: 2.6.0
"""

import re
import logging
from typing import Dict, Any, List, Optional

from .ast import (
    AgentSpecification,
    TierLevel,
    Comparator,
    TypeCheck,
    Quantifier,
    PathExpr,
    LiteralValue,
    DateExpr,
    # Constraints
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
    # Conditions
    Condition,
    ComparisonCondition,
    TypeCondition,
    CountCondition,
    # Behavior
    BehaviorRule,
    PreferRule,
    NeverRule,
    AlwaysRule,
    WhenRule,
    LimitDecl,
)

logger = logging.getLogger(__name__)

# Try to import Lark
try:
    from lark import Lark, Transformer, v_args, Token
    LARK_AVAILABLE = True
except ImportError:
    LARK_AVAILABLE = False
    logger.warning("Lark not available, using fallback regex parser")


class ParseError(Exception):
    """Error during specification parsing."""
    pass


class SpecificationParser:
    """
    Parser for agent specification DSL.

    Uses Lark if available, otherwise falls back to regex-based parsing.
    """

    def __init__(self):
        """Initialize the parser."""
        self._lark_parser = None
        if LARK_AVAILABLE:
            try:
                from .grammar import SPECIFICATION_GRAMMAR
                self._lark_parser = Lark(
                    SPECIFICATION_GRAMMAR,
                    start='start',
                    parser='lalr',
                )
            except Exception as e:
                logger.warning(f"Failed to initialize Lark parser: {e}")

    def parse(self, spec_text: str) -> AgentSpecification:
        """
        Parse specification text into AST.

        Args:
            spec_text: The specification text

        Returns:
            Parsed AgentSpecification

        Raises:
            ParseError: If parsing fails
        """
        if self._lark_parser:
            try:
                return self._parse_with_lark(spec_text)
            except Exception as e:
                logger.warning(f"Lark parsing failed, using fallback: {e}")

        return self._parse_with_regex(spec_text)

    def _parse_with_lark(self, spec_text: str) -> AgentSpecification:
        """Parse using Lark parser."""
        tree = self._lark_parser.parse(spec_text)
        transformer = SpecificationTransformer()
        return transformer.transform(tree)

    def _parse_with_regex(self, spec_text: str) -> AgentSpecification:
        """Fallback regex-based parser."""
        spec = AgentSpecification(agent_name="", raw_text=spec_text)

        # Parse agent name
        agent_match = re.search(r"AGENT\s+(\w+)\s*:", spec_text)
        if agent_match:
            spec.agent_name = agent_match.group(1)
        else:
            raise ParseError("Missing AGENT declaration")

        # Parse tier
        tier_match = re.search(r"TIER:\s*(opus|sonnet|haiku)", spec_text, re.IGNORECASE)
        if tier_match:
            spec.tier = TierLevel(tier_match.group(1).lower())

        # Parse tools
        tools_match = re.search(r"TOOLS:\s*\[([\w\s,]+)\]", spec_text)
        if tools_match:
            tools_str = tools_match.group(1)
            spec.tools = [t.strip() for t in tools_str.split(",") if t.strip()]

        # Parse output constraints
        spec.output_constraints = self._parse_output_constraints(spec_text)

        # Parse behavior rules
        spec.behavior_rules = self._parse_behavior_rules(spec_text)

        # Parse limits
        spec.limits = self._parse_limits(spec_text)

        return spec

    def _parse_output_constraints(self, spec_text: str) -> List[Constraint]:
        """Parse OUTPUT MUST SATISFY section."""
        constraints = []

        # Find the output section
        output_match = re.search(
            r"OUTPUT\s+MUST\s+SATISFY:\s*(.*?)(?=BEHAVIOR:|LIMITS:|$)",
            spec_text,
            re.DOTALL | re.IGNORECASE
        )
        if not output_match:
            return constraints

        output_text = output_match.group(1).strip()
        lines = [line.strip() for line in output_text.split("\n") if line.strip()]

        for line in lines:
            constraint = self._parse_constraint_line(line)
            if constraint:
                constraints.append(constraint)

        return constraints

    def _parse_constraint_line(self, line: str) -> Optional[Constraint]:
        """Parse a single constraint line."""
        line = line.strip()
        if not line or line.startswith("#"):
            return None

        # forall/exists quantifier
        quant_match = re.match(
            r"(forall|exists)\s+(\w+)\s+in\s+([\w.]+)\s*:\s*(.+)",
            line,
            re.IGNORECASE
        )
        if quant_match:
            quantifier = Quantifier.FORALL if quant_match.group(1).lower() == "forall" else Quantifier.EXISTS
            variable = quant_match.group(2)
            path = PathExpr(quant_match.group(3).split("."))
            inner_text = quant_match.group(4)
            inner = self._parse_constraint_line(inner_text)
            if inner:
                return QuantifiedConstraint(quantifier, variable, path, inner)
            return None

        # if condition: constraint
        if_match = re.match(r"if\s+(.+)\s*:\s*(.+)", line, re.IGNORECASE)
        if if_match:
            condition = self._parse_condition(if_match.group(1))
            consequence = self._parse_constraint_line(if_match.group(2))
            if condition and consequence:
                return ConditionalConstraint(condition, consequence)
            return None

        # path IN RANGE [min, max]
        range_match = re.match(
            r"([\w.]+)\s+IN\s+RANGE\s*\[\s*([\d.-]+)\s*,\s*([\d.-]+)\s*\]",
            line,
            re.IGNORECASE
        )
        if range_match:
            path = PathExpr(range_match.group(1).split("."))
            min_val = float(range_match.group(2))
            max_val = float(range_match.group(3))
            return RangeConstraint(path, min_val, max_val)

        # path IN [values]
        in_list_match = re.match(
            r"([\w.]+)\s+IN\s*\[([^\]]+)\]",
            line,
            re.IGNORECASE
        )
        if in_list_match:
            path = PathExpr(in_list_match.group(1).split("."))
            values_str = in_list_match.group(2)
            values = [
                LiteralValue.from_parsed(v.strip().strip('"\''))
                for v in values_str.split(",")
            ]
            return InListConstraint(path, values)

        # path IS type_check
        type_match = re.match(
            r"([\w.]+)\s+IS\s+(\w+)",
            line,
            re.IGNORECASE
        )
        if type_match:
            path = PathExpr(type_match.group(1).split("."))
            type_str = type_match.group(2).upper()
            try:
                type_check = TypeCheck(type_str.lower())
            except ValueError:
                type_check = TypeCheck.NOT_EMPTY
            return TypeConstraint(path, type_check)

        # path comparator value
        comp_match = re.match(
            r"([\w.]+)\s*(==|!=|<=|>=|<|>)\s*(.+)",
            line
        )
        if comp_match:
            path = PathExpr(comp_match.group(1).split("."))
            comp_str = comp_match.group(2)
            comparator = {
                "==": Comparator.EQ,
                "!=": Comparator.NE,
                "<": Comparator.LT,
                ">": Comparator.GT,
                "<=": Comparator.LE,
                ">=": Comparator.GE,
            }[comp_str]
            value = LiteralValue.from_parsed(comp_match.group(3).strip())
            return ComparisonConstraint(path, comparator, value)

        return None

    def _parse_condition(self, text: str) -> Optional[Condition]:
        """Parse a condition expression."""
        text = text.strip()

        # count(path) comparator value
        count_match = re.match(
            r"count\s*\(\s*([\w.]+)\s*\)\s*(==|!=|<|>|<=|>=)\s*(\d+)",
            text,
            re.IGNORECASE
        )
        if count_match:
            path = PathExpr(count_match.group(1).split("."))
            comp_str = count_match.group(2)
            comparator = {
                "==": Comparator.EQ,
                "!=": Comparator.NE,
                "<": Comparator.LT,
                ">": Comparator.GT,
                "<=": Comparator.LE,
                ">=": Comparator.GE,
            }[comp_str]
            value = int(count_match.group(3))
            return CountCondition(path, comparator, value)

        # path IS type
        type_match = re.match(r"([\w.]+)\s+IS\s+(\w+)", text, re.IGNORECASE)
        if type_match:
            path = PathExpr(type_match.group(1).split("."))
            type_str = type_match.group(2).upper()
            try:
                type_check = TypeCheck(type_str.lower())
            except ValueError:
                type_check = TypeCheck.NOT_EMPTY
            return TypeCondition(path, type_check)

        # path comparator value
        comp_match = re.match(r"([\w.]+)\s*(==|!=|<=|>=|<|>)\s*(.+)", text)
        if comp_match:
            path = PathExpr(comp_match.group(1).split("."))
            comp_str = comp_match.group(2)
            comparator = {
                "==": Comparator.EQ,
                "!=": Comparator.NE,
                "<": Comparator.LT,
                ">": Comparator.GT,
                "<=": Comparator.LE,
                ">=": Comparator.GE,
            }[comp_str]
            value = LiteralValue.from_parsed(comp_match.group(3).strip())
            return ComparisonCondition(path, comparator, value)

        return None

    def _parse_behavior_rules(self, spec_text: str) -> List[BehaviorRule]:
        """Parse BEHAVIOR section."""
        rules = []

        behavior_match = re.search(
            r"BEHAVIOR:\s*(.*?)(?=LIMITS:|$)",
            spec_text,
            re.DOTALL | re.IGNORECASE
        )
        if not behavior_match:
            return rules

        behavior_text = behavior_match.group(1).strip()
        lines = [line.strip() for line in behavior_text.split("\n") if line.strip()]

        for line in lines:
            rule = self._parse_behavior_line(line)
            if rule:
                rules.append(rule)

        return rules

    def _parse_behavior_line(self, line: str) -> Optional[BehaviorRule]:
        """Parse a single behavior rule line."""
        line = line.strip()
        if not line or line.startswith("#"):
            return None

        # PREFER x OVER y
        prefer_match = re.match(
            r"PREFER\s+(.+?)\s+OVER\s+(.+)",
            line,
            re.IGNORECASE
        )
        if prefer_match:
            return PreferRule(
                preferred=prefer_match.group(1).strip(),
                over=prefer_match.group(2).strip()
            )

        # NEVER action
        never_match = re.match(r"NEVER\s+(.+)", line, re.IGNORECASE)
        if never_match:
            return NeverRule(action=never_match.group(1).strip())

        # ALWAYS action
        always_match = re.match(r"ALWAYS\s+(.+)", line, re.IGNORECASE)
        if always_match:
            return AlwaysRule(action=always_match.group(1).strip())

        # WHEN condition: action
        when_match = re.match(r"WHEN\s+(.+?)\s*:\s*(.+)", line, re.IGNORECASE)
        if when_match:
            condition = self._parse_condition(when_match.group(1))
            action = when_match.group(2).strip()
            if condition:
                return WhenRule(condition=condition, action=action)

        return None

    def _parse_limits(self, spec_text: str) -> Dict[str, int]:
        """Parse LIMITS section."""
        limits = {}

        limits_match = re.search(
            r"LIMITS:\s*(.*?)$",
            spec_text,
            re.DOTALL | re.IGNORECASE
        )
        if not limits_match:
            return limits

        limits_text = limits_match.group(1).strip()
        lines = [line.strip() for line in limits_text.split("\n") if line.strip()]

        for line in lines:
            if line.startswith("#"):
                continue
            limit_match = re.match(r"(\w+)\s*:\s*(\d+)", line)
            if limit_match:
                limits[limit_match.group(1)] = int(limit_match.group(2))

        return limits


if LARK_AVAILABLE:
    class SpecificationTransformer(Transformer):
        """Transforms Lark parse tree to AST."""

        def specification(self, items):
            name = str(items[0])
            body = items[1]
            return AgentSpecification(
                agent_name=name,
                tier=body.get("tier", TierLevel.SONNET),
                tools=body.get("tools", []),
                output_constraints=body.get("constraints", []),
                behavior_rules=body.get("behaviors", []),
                limits=body.get("limits", {}),
            )

        def agent_body(self, items):
            result = {}
            for item in items:
                if isinstance(item, dict):
                    result.update(item)
            return result

        def tier_decl(self, items):
            return {"tier": items[0]}

        def tier_name(self, items):
            return TierLevel(str(items[0]).lower())

        def tools_decl(self, items):
            return {"tools": items[0]}

        def tool_list(self, items):
            return [str(t) for t in items]

        def output_spec(self, items):
            return {"constraints": items[0]}

        def constraint_list(self, items):
            return list(items)

        def behavior_spec(self, items):
            return {"behaviors": items[0]}

        def behavior_list(self, items):
            return list(items)

        def limits_spec(self, items):
            return {"limits": items[0]}

        def limit_list(self, items):
            result = {}
            for item in items:
                result.update(item)
            return result

        def limit_decl(self, items):
            return {str(items[0]): int(items[1])}

        def path(self, items):
            return PathExpr([str(p) for p in items])

        def number(self, items):
            return float(items[0])

        def IDENTIFIER(self, token):
            return str(token)

        def STRING_VALUE(self, token):
            return str(token)[1:-1]  # Remove quotes
