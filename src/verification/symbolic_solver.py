"""
Symbolic Verification using Z3 Theorem Prover.

Provides formal verification of claims with logical or mathematical
structure, including arithmetic validation, constraint satisfiability,
and logical implication checking.

Version: 2.6.0
"""

import logging
import operator
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional, List, Tuple, Union, Callable

logger = logging.getLogger(__name__)

# Z3 imports with graceful fallback
try:
    from z3 import (
        Solver, Int, Real, Bool,
        And, Or, Not, Implies, If,
        sat, unsat, unknown,
        ForAll, Exists, IntVal, RealVal, BoolVal,
        ArithRef, BoolRef,
    )
    Z3_AVAILABLE = True
except ImportError:
    Z3_AVAILABLE = False
    logger.warning("Z3 not available. Symbolic verification will be disabled.")


def utc_now() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


class VerificationResult(Enum):
    """Result of symbolic verification."""
    VERIFIED = "verified"
    REFUTED = "refuted"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"
    Z3_UNAVAILABLE = "z3_unavailable"


@dataclass
class SymbolicVerificationOutput:
    """
    Result of a symbolic verification operation.

    Attributes:
        result: Verification outcome
        explanation: Human-readable explanation
        counterexample: Values that disprove the claim (if refuted)
        proof_steps: Steps in the verification (if available)
        verification_time_ms: Time taken for verification
        claim_text: Original claim being verified
        method: Verification method used
    """
    result: VerificationResult
    explanation: str
    counterexample: Optional[Dict[str, Any]] = None
    proof_steps: Optional[List[str]] = None
    verification_time_ms: int = 0
    claim_text: str = ""
    method: str = "symbolic"
    timestamp: datetime = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "result": self.result.value,
            "explanation": self.explanation,
            "counterexample": self.counterexample,
            "proof_steps": self.proof_steps,
            "verification_time_ms": self.verification_time_ms,
            "claim_text": self.claim_text,
            "method": self.method,
            "timestamp": self.timestamp.isoformat(),
        }

    @property
    def is_verified(self) -> bool:
        """Check if verification succeeded."""
        return self.result == VerificationResult.VERIFIED

    @property
    def is_refuted(self) -> bool:
        """Check if claim was refuted."""
        return self.result == VerificationResult.REFUTED


class SafeExpressionParser:
    """
    Safe parser for arithmetic and constraint expressions.

    Converts string expressions to Z3 constraints without using
    dangerous eval() on untrusted input.
    """

    # Supported operators
    OPERATORS = {
        "+": operator.add,
        "-": operator.sub,
        "*": operator.mul,
        "/": operator.truediv,
        "//": operator.floordiv,
        "%": operator.mod,
        "**": operator.pow,
    }

    COMPARISONS = {
        "==": operator.eq,
        "!=": operator.ne,
        "<": operator.lt,
        "<=": operator.le,
        ">": operator.gt,
        ">=": operator.ge,
    }

    # Token patterns - non-capturing alternation for cleaner matching
    TOKEN_PATTERN = re.compile(
        r"""
        \d+\.?\d*|        # Numbers
        [a-zA-Z_]\w*|     # Identifiers
        ==|!=|<=|>=|<|>|  # Comparisons
        \+|-|\*\*|\*|//|/|%|  # Operators (order matters: ** before *)
        \(|\)|            # Parentheses
        ,                 # Comma
        """,
        re.VERBOSE
    )

    def __init__(self, variables: Dict[str, Any]):
        """
        Initialize parser with Z3 variables.

        Args:
            variables: Mapping of variable names to Z3 variables
        """
        self.variables = variables
        # Only set Z3 functions if Z3 is available
        if Z3_AVAILABLE:
            self.z3_funcs = {
                "And": And,
                "Or": Or,
                "Not": Not,
                "Implies": Implies,
                "If": If,
            }
        else:
            self.z3_funcs = {}

    def parse_arithmetic(self, expr: str, values: Dict[str, float]) -> float:
        """
        Safely evaluate an arithmetic expression.

        Args:
            expr: Arithmetic expression (e.g., "total - spent")
            values: Variable values

        Returns:
            Computed result

        Raises:
            ValueError: If expression is invalid
        """
        # Tokenize
        tokens = self._tokenize(expr)
        if not tokens:
            raise ValueError(f"Empty expression: {expr}")

        # Simple expression evaluator
        return self._eval_expression(tokens, values)

    def parse_constraint(self, constraint: str) -> Any:
        """
        Parse a constraint string to Z3 expression.

        Args:
            constraint: Constraint like "x > 5" or "And(x > 0, y < 10)"

        Returns:
            Z3 constraint expression

        Raises:
            ValueError: If constraint is invalid
        """
        if not Z3_AVAILABLE:
            raise ValueError("Z3 not available")

        # Handle Z3 function calls
        constraint = constraint.strip()

        # Check for Z3 functions
        for func_name, func in self.z3_funcs.items():
            if constraint.startswith(f"{func_name}("):
                return self._parse_function_call(constraint, func_name, func)

        # Parse comparison expression
        return self._parse_comparison(constraint)

    def _tokenize(self, expr: str) -> List[str]:
        """Tokenize expression string."""
        tokens = []
        for match in self.TOKEN_PATTERN.finditer(expr):
            token = match.group(0)
            if token.strip():
                tokens.append(token)
        return tokens

    def _eval_expression(
        self,
        tokens: List[str],
        values: Dict[str, float]
    ) -> float:
        """Evaluate tokenized expression."""
        # Convert tokens to values
        output = []
        operators = []

        precedence = {"+": 1, "-": 1, "*": 2, "/": 2, "//": 2, "%": 2, "**": 3}

        i = 0
        while i < len(tokens):
            token = tokens[i]

            if re.match(r"\d+\.?\d*", token):
                # Number
                output.append(float(token))
            elif token in values:
                # Variable
                output.append(values[token])
            elif token in self.OPERATORS:
                # Operator
                while (operators and operators[-1] != "(" and
                       operators[-1] in precedence and
                       precedence.get(operators[-1], 0) >= precedence.get(token, 0)):
                    self._apply_operator(output, operators.pop())
                operators.append(token)
            elif token == "(":
                operators.append(token)
            elif token == ")":
                while operators and operators[-1] != "(":
                    self._apply_operator(output, operators.pop())
                if operators:
                    operators.pop()  # Remove (
            else:
                raise ValueError(f"Unknown token: {token}")

            i += 1

        while operators:
            self._apply_operator(output, operators.pop())

        if len(output) != 1:
            raise ValueError("Invalid expression")

        return output[0]

    def _apply_operator(self, output: List[float], op: str) -> None:
        """Apply operator to output stack."""
        if len(output) < 2:
            raise ValueError(f"Not enough operands for {op}")
        b = output.pop()
        a = output.pop()
        output.append(self.OPERATORS[op](a, b))

    def _parse_comparison(self, constraint: str) -> Any:
        """Parse a simple comparison expression."""
        # Find comparison operator
        for comp_op in ["==", "!=", "<=", ">=", "<", ">"]:
            if comp_op in constraint:
                parts = constraint.split(comp_op, 1)
                if len(parts) == 2:
                    left = self._parse_term(parts[0].strip())
                    right = self._parse_term(parts[1].strip())
                    return self.COMPARISONS[comp_op](left, right)

        raise ValueError(f"No comparison operator found in: {constraint}")

    def _parse_term(self, term: str) -> Any:
        """Parse a single term (variable, number, or expression)."""
        term = term.strip()

        # Check if it's a variable
        if term in self.variables:
            return self.variables[term]

        # Check if it's a number
        try:
            if "." in term:
                return float(term)
            return int(term)
        except ValueError:
            pass

        # Try parsing as expression with variables
        return self._parse_arithmetic_expr(term)

    def _parse_arithmetic_expr(self, expr: str) -> Any:
        """Parse arithmetic expression with Z3 variables."""
        # Handle simple binary operations
        for op in ["+", "-", "*", "/"]:
            # Find operator not inside parentheses
            depth = 0
            for i, c in enumerate(expr):
                if c == "(":
                    depth += 1
                elif c == ")":
                    depth -= 1
                elif c == op and depth == 0 and i > 0:
                    left = self._parse_term(expr[:i])
                    right = self._parse_term(expr[i+1:])
                    if op == "+":
                        return left + right
                    elif op == "-":
                        return left - right
                    elif op == "*":
                        return left * right
                    elif op == "/":
                        return left / right

        # Check for parentheses
        if expr.startswith("(") and expr.endswith(")"):
            return self._parse_term(expr[1:-1])

        raise ValueError(f"Cannot parse term: {expr}")

    def _parse_function_call(
        self,
        constraint: str,
        func_name: str,
        func: Callable
    ) -> Any:
        """Parse Z3 function call like And(x > 0, y < 10)."""
        # Extract arguments
        inner = constraint[len(func_name) + 1:-1]  # Remove "Func(" and ")"
        args = self._split_args(inner)

        if func_name == "Not":
            if len(args) != 1:
                raise ValueError(f"Not requires exactly 1 argument")
            return func(self.parse_constraint(args[0]))

        # And, Or, Implies take multiple arguments
        parsed_args = [self.parse_constraint(arg) for arg in args]
        return func(*parsed_args)

    def _split_args(self, inner: str) -> List[str]:
        """Split function arguments respecting nested parentheses."""
        args = []
        current = ""
        depth = 0

        for c in inner:
            if c == "(":
                depth += 1
                current += c
            elif c == ")":
                depth -= 1
                current += c
            elif c == "," and depth == 0:
                args.append(current.strip())
                current = ""
            else:
                current += c

        if current.strip():
            args.append(current.strip())

        return args


class SymbolicVerifier:
    """
    Formal verification using Z3 theorem prover.

    Provides verification for:
    - Arithmetic claims (e.g., "total - spent = remaining")
    - Constraint satisfaction (e.g., "x > 0 and x < 100 is satisfiable")
    - Logical implication (e.g., "if x > 5 then x > 0")

    Example:
        verifier = SymbolicVerifier()
        result = verifier.verify_arithmetic(
            values={"total": 50000, "spent": 42000},
            claimed_result=8000,
            operation="total - spent"
        )
        if result.is_verified:
            print("Arithmetic correct!")
    """

    def __init__(self, timeout_ms: int = 5000):
        """
        Initialize the symbolic verifier.

        Args:
            timeout_ms: Maximum time for Z3 solver (default 5 seconds)
        """
        self.timeout_ms = timeout_ms
        self.verification_count = 0
        self.verified_count = 0
        self.refuted_count = 0

    def verify_arithmetic(
        self,
        values: Dict[str, float],
        claimed_result: float,
        operation: str,
        tolerance: float = 0.001
    ) -> SymbolicVerificationOutput:
        """
        Verify an arithmetic claim.

        Args:
            values: Named values (e.g., {"total": 50000, "spent": 42000})
            claimed_result: The claimed result
            operation: The operation expression (e.g., "total - spent")
            tolerance: Acceptable difference for floating point

        Returns:
            SymbolicVerificationOutput with verification result

        Example:
            # Verify: 50000 - 42000 = 10000 (incorrect, should be 8000)
            result = verifier.verify_arithmetic(
                values={"total": 50000, "spent": 42000},
                claimed_result=10000,
                operation="total - spent"
            )
            assert result.is_refuted
            assert result.counterexample["actual"] == 8000
        """
        start_time = time.time()
        self.verification_count += 1

        claim_text = f"{operation} = {claimed_result}"

        try:
            parser = SafeExpressionParser({})
            actual_result = parser.parse_arithmetic(operation, values)
        except Exception as e:
            return SymbolicVerificationOutput(
                result=VerificationResult.NOT_APPLICABLE,
                explanation=f"Could not evaluate operation: {e}",
                claim_text=claim_text,
                verification_time_ms=self._elapsed_ms(start_time),
            )

        # Check if claimed result matches
        if abs(actual_result - claimed_result) <= tolerance:
            self.verified_count += 1
            return SymbolicVerificationOutput(
                result=VerificationResult.VERIFIED,
                explanation=f"Arithmetic verified: {operation} = {actual_result}",
                claim_text=claim_text,
                verification_time_ms=self._elapsed_ms(start_time),
                proof_steps=[
                    f"Given values: {values}",
                    f"Computed: {operation} = {actual_result}",
                    f"Claimed: {claimed_result}",
                    f"Difference: {abs(actual_result - claimed_result)} <= {tolerance}",
                    "VERIFIED",
                ],
            )
        else:
            self.refuted_count += 1
            return SymbolicVerificationOutput(
                result=VerificationResult.REFUTED,
                explanation=f"Arithmetic error: {operation} = {actual_result}, not {claimed_result}",
                counterexample={
                    "expected": claimed_result,
                    "actual": actual_result,
                    "difference": abs(actual_result - claimed_result),
                },
                claim_text=claim_text,
                verification_time_ms=self._elapsed_ms(start_time),
                proof_steps=[
                    f"Given values: {values}",
                    f"Computed: {operation} = {actual_result}",
                    f"Claimed: {claimed_result}",
                    f"Difference: {abs(actual_result - claimed_result)} > {tolerance}",
                    "REFUTED",
                ],
            )

    def verify_constraints(
        self,
        constraints: List[str],
        variable_types: Dict[str, str],
        should_be_satisfiable: bool = True
    ) -> SymbolicVerificationOutput:
        """
        Verify that a set of constraints is satisfiable (or unsatisfiable).

        Args:
            constraints: List of constraint expressions
            variable_types: Mapping of variable names to types ("int", "real", "bool")
            should_be_satisfiable: Whether we expect constraints to be satisfiable

        Returns:
            SymbolicVerificationOutput with verification result

        Example:
            # Verify: x > 0 and x < 0 is unsatisfiable
            result = verifier.verify_constraints(
                constraints=["x > 0", "x < 0"],
                variable_types={"x": "real"},
                should_be_satisfiable=True  # Claim: these are satisfiable
            )
            assert result.is_refuted  # Actually unsatisfiable
        """
        start_time = time.time()
        self.verification_count += 1

        claim_text = f"Constraints {constraints} are {'satisfiable' if should_be_satisfiable else 'unsatisfiable'}"

        if not Z3_AVAILABLE:
            return SymbolicVerificationOutput(
                result=VerificationResult.Z3_UNAVAILABLE,
                explanation="Z3 theorem prover is not installed",
                claim_text=claim_text,
                verification_time_ms=self._elapsed_ms(start_time),
            )

        try:
            s = Solver()
            s.set("timeout", self.timeout_ms)

            # Create typed Z3 variables
            z3_vars = self._create_z3_variables(variable_types)
            parser = SafeExpressionParser(z3_vars)

            # Parse and add constraints
            proof_steps = ["Creating Z3 solver"]
            for constraint in constraints:
                try:
                    z3_constraint = parser.parse_constraint(constraint)
                    s.add(z3_constraint)
                    proof_steps.append(f"Added constraint: {constraint}")
                except Exception as e:
                    return SymbolicVerificationOutput(
                        result=VerificationResult.NOT_APPLICABLE,
                        explanation=f"Could not parse constraint '{constraint}': {e}",
                        claim_text=claim_text,
                        verification_time_ms=self._elapsed_ms(start_time),
                    )

            # Check satisfiability
            proof_steps.append("Checking satisfiability...")
            result = s.check()

            if result == sat:
                model = s.model()
                satisfying_assignment = {
                    str(d): str(model[d]) for d in model.decls()
                }
                proof_steps.append(f"Found satisfying assignment: {satisfying_assignment}")

                if should_be_satisfiable:
                    self.verified_count += 1
                    return SymbolicVerificationOutput(
                        result=VerificationResult.VERIFIED,
                        explanation="Constraints are satisfiable as claimed",
                        counterexample=satisfying_assignment,
                        claim_text=claim_text,
                        verification_time_ms=self._elapsed_ms(start_time),
                        proof_steps=proof_steps + ["VERIFIED"],
                    )
                else:
                    self.refuted_count += 1
                    return SymbolicVerificationOutput(
                        result=VerificationResult.REFUTED,
                        explanation="Constraints claimed unsatisfiable but are satisfiable",
                        counterexample=satisfying_assignment,
                        claim_text=claim_text,
                        verification_time_ms=self._elapsed_ms(start_time),
                        proof_steps=proof_steps + ["REFUTED"],
                    )

            elif result == unsat:
                proof_steps.append("No satisfying assignment exists")

                if not should_be_satisfiable:
                    self.verified_count += 1
                    return SymbolicVerificationOutput(
                        result=VerificationResult.VERIFIED,
                        explanation="Correctly identified as unsatisfiable",
                        claim_text=claim_text,
                        verification_time_ms=self._elapsed_ms(start_time),
                        proof_steps=proof_steps + ["VERIFIED"],
                    )
                else:
                    self.refuted_count += 1
                    return SymbolicVerificationOutput(
                        result=VerificationResult.REFUTED,
                        explanation="Constraints claimed satisfiable but are unsatisfiable",
                        claim_text=claim_text,
                        verification_time_ms=self._elapsed_ms(start_time),
                        proof_steps=proof_steps + ["REFUTED"],
                    )

            else:  # unknown
                return SymbolicVerificationOutput(
                    result=VerificationResult.UNKNOWN,
                    explanation=f"Could not determine satisfiability within {self.timeout_ms}ms",
                    claim_text=claim_text,
                    verification_time_ms=self._elapsed_ms(start_time),
                    proof_steps=proof_steps + ["UNKNOWN - timeout or complexity limit"],
                )

        except Exception as e:
            return SymbolicVerificationOutput(
                result=VerificationResult.NOT_APPLICABLE,
                explanation=f"Verification error: {e}",
                claim_text=claim_text,
                verification_time_ms=self._elapsed_ms(start_time),
            )

    def verify_implication(
        self,
        premises: List[str],
        conclusion: str,
        variable_types: Dict[str, str]
    ) -> SymbolicVerificationOutput:
        """
        Verify that premises logically imply the conclusion.

        Uses proof by contradiction: if (premises AND NOT conclusion)
        is unsatisfiable, then the implication holds.

        Args:
            premises: List of premise expressions
            conclusion: The conclusion to verify
            variable_types: Mapping of variable names to types

        Returns:
            SymbolicVerificationOutput with verification result

        Example:
            # Verify: if x > 5 and y = x + 1, then y > 5
            result = verifier.verify_implication(
                premises=["x > 5", "y == x + 1"],
                conclusion="y > 5",
                variable_types={"x": "int", "y": "int"}
            )
            assert result.is_verified
        """
        start_time = time.time()
        self.verification_count += 1

        claim_text = f"Given {premises}, conclude {conclusion}"

        if not Z3_AVAILABLE:
            return SymbolicVerificationOutput(
                result=VerificationResult.Z3_UNAVAILABLE,
                explanation="Z3 theorem prover is not installed",
                claim_text=claim_text,
                verification_time_ms=self._elapsed_ms(start_time),
            )

        try:
            s = Solver()
            s.set("timeout", self.timeout_ms)

            # Create variables
            z3_vars = self._create_z3_variables(variable_types)
            parser = SafeExpressionParser(z3_vars)

            proof_steps = ["Setting up implication proof by contradiction"]

            # Add premises
            for premise in premises:
                try:
                    z3_premise = parser.parse_constraint(premise)
                    s.add(z3_premise)
                    proof_steps.append(f"Added premise: {premise}")
                except Exception as e:
                    return SymbolicVerificationOutput(
                        result=VerificationResult.NOT_APPLICABLE,
                        explanation=f"Could not parse premise '{premise}': {e}",
                        claim_text=claim_text,
                        verification_time_ms=self._elapsed_ms(start_time),
                    )

            # Add negation of conclusion
            try:
                z3_conclusion = parser.parse_constraint(conclusion)
                s.add(Not(z3_conclusion))
                proof_steps.append(f"Added negation of conclusion: NOT({conclusion})")
            except Exception as e:
                return SymbolicVerificationOutput(
                    result=VerificationResult.NOT_APPLICABLE,
                    explanation=f"Could not parse conclusion '{conclusion}': {e}",
                    claim_text=claim_text,
                    verification_time_ms=self._elapsed_ms(start_time),
                )

            # Check satisfiability
            proof_steps.append("Checking if premises AND NOT(conclusion) is satisfiable...")
            result = s.check()

            if result == unsat:
                self.verified_count += 1
                proof_steps.append("Unsatisfiable - implication holds")
                return SymbolicVerificationOutput(
                    result=VerificationResult.VERIFIED,
                    explanation=f"Conclusion '{conclusion}' logically follows from premises",
                    claim_text=claim_text,
                    verification_time_ms=self._elapsed_ms(start_time),
                    proof_steps=proof_steps + ["VERIFIED"],
                )

            elif result == sat:
                self.refuted_count += 1
                model = s.model()
                counterexample = {str(d): str(model[d]) for d in model.decls()}
                proof_steps.append(f"Found counterexample: {counterexample}")
                return SymbolicVerificationOutput(
                    result=VerificationResult.REFUTED,
                    explanation="Conclusion does not follow from premises",
                    counterexample=counterexample,
                    claim_text=claim_text,
                    verification_time_ms=self._elapsed_ms(start_time),
                    proof_steps=proof_steps + ["REFUTED"],
                )

            else:  # unknown
                return SymbolicVerificationOutput(
                    result=VerificationResult.UNKNOWN,
                    explanation="Could not verify implication within timeout",
                    claim_text=claim_text,
                    verification_time_ms=self._elapsed_ms(start_time),
                    proof_steps=proof_steps + ["UNKNOWN"],
                )

        except Exception as e:
            return SymbolicVerificationOutput(
                result=VerificationResult.NOT_APPLICABLE,
                explanation=f"Verification error: {e}",
                claim_text=claim_text,
                verification_time_ms=self._elapsed_ms(start_time),
            )

    def verify_equality(
        self,
        expr1: str,
        expr2: str,
        variable_types: Dict[str, str]
    ) -> SymbolicVerificationOutput:
        """
        Verify that two expressions are always equal.

        Args:
            expr1: First expression
            expr2: Second expression
            variable_types: Variable types

        Returns:
            SymbolicVerificationOutput
        """
        start_time = time.time()
        self.verification_count += 1

        claim_text = f"{expr1} == {expr2} for all values"

        if not Z3_AVAILABLE:
            return SymbolicVerificationOutput(
                result=VerificationResult.Z3_UNAVAILABLE,
                explanation="Z3 theorem prover is not installed",
                claim_text=claim_text,
                verification_time_ms=self._elapsed_ms(start_time),
            )

        try:
            s = Solver()
            s.set("timeout", self.timeout_ms)

            z3_vars = self._create_z3_variables(variable_types)
            parser = SafeExpressionParser(z3_vars)

            # Parse both expressions
            z3_expr1 = parser._parse_term(expr1)
            z3_expr2 = parser._parse_term(expr2)

            # Add inequality - if unsatisfiable, they're always equal
            s.add(z3_expr1 != z3_expr2)

            result = s.check()

            if result == unsat:
                self.verified_count += 1
                return SymbolicVerificationOutput(
                    result=VerificationResult.VERIFIED,
                    explanation=f"Expressions {expr1} and {expr2} are always equal",
                    claim_text=claim_text,
                    verification_time_ms=self._elapsed_ms(start_time),
                )
            elif result == sat:
                self.refuted_count += 1
                model = s.model()
                counterexample = {str(d): str(model[d]) for d in model.decls()}
                return SymbolicVerificationOutput(
                    result=VerificationResult.REFUTED,
                    explanation="Expressions are not always equal",
                    counterexample=counterexample,
                    claim_text=claim_text,
                    verification_time_ms=self._elapsed_ms(start_time),
                )
            else:
                return SymbolicVerificationOutput(
                    result=VerificationResult.UNKNOWN,
                    explanation="Could not determine equality within timeout",
                    claim_text=claim_text,
                    verification_time_ms=self._elapsed_ms(start_time),
                )

        except Exception as e:
            return SymbolicVerificationOutput(
                result=VerificationResult.NOT_APPLICABLE,
                explanation=f"Verification error: {e}",
                claim_text=claim_text,
                verification_time_ms=self._elapsed_ms(start_time),
            )

    def _create_z3_variables(self, variable_types: Dict[str, str]) -> Dict[str, Any]:
        """Create Z3 variables from type specifications."""
        if not Z3_AVAILABLE:
            return {}

        z3_vars = {}
        for name, vtype in variable_types.items():
            if vtype == "int":
                z3_vars[name] = Int(name)
            elif vtype == "real":
                z3_vars[name] = Real(name)
            elif vtype == "bool":
                z3_vars[name] = Bool(name)
            else:
                raise ValueError(f"Unknown variable type: {vtype}")
        return z3_vars

    def _elapsed_ms(self, start_time: float) -> int:
        """Calculate elapsed time in milliseconds."""
        return int((time.time() - start_time) * 1000)

    def get_stats(self) -> Dict[str, Any]:
        """Get verification statistics."""
        return {
            "total_verifications": self.verification_count,
            "verified": self.verified_count,
            "refuted": self.refuted_count,
            "verification_rate": (
                self.verified_count / self.verification_count
                if self.verification_count > 0 else 0.0
            ),
            "z3_available": Z3_AVAILABLE,
        }


def is_z3_available() -> bool:
    """Check if Z3 is available."""
    return Z3_AVAILABLE
