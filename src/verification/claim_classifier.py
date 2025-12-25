"""
Claim Classification for Verification Routing.

Classifies claims by type to route them to the appropriate
verification method (symbolic or LLM).

Version: 2.6.0
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional, List, Tuple, Pattern


def utc_now() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


class ClaimType(Enum):
    """Types of claims for verification routing."""
    ARITHMETIC = "arithmetic"
    CONSTRAINT = "constraint"
    IMPLICATION = "implication"
    COMPARISON = "comparison"
    EQUALITY = "equality"
    BOOLEAN = "boolean"
    TEXTUAL = "textual"
    UNKNOWN = "unknown"


@dataclass
class ClassifiedClaim:
    """
    A claim with its classification for verification routing.

    Attributes:
        claim_text: Original claim text
        claim_type: Classified type
        confidence: Classification confidence (0.0-1.0)
        extracted_values: Values extracted from the claim
        extracted_operation: Operation if applicable
        variables: Variables detected in the claim
        variable_types: Inferred variable types
        symbolic_applicable: Whether symbolic verification applies
        classification_reason: Why this classification was chosen
    """
    claim_text: str
    claim_type: ClaimType
    confidence: float
    extracted_values: Dict[str, Any] = field(default_factory=dict)
    extracted_operation: Optional[str] = None
    variables: List[str] = field(default_factory=list)
    variable_types: Dict[str, str] = field(default_factory=dict)
    symbolic_applicable: bool = False
    classification_reason: str = ""
    timestamp: datetime = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "claim_text": self.claim_text,
            "claim_type": self.claim_type.value,
            "confidence": self.confidence,
            "extracted_values": self.extracted_values,
            "extracted_operation": self.extracted_operation,
            "variables": self.variables,
            "variable_types": self.variable_types,
            "symbolic_applicable": self.symbolic_applicable,
            "classification_reason": self.classification_reason,
        }


class ClaimClassifier:
    """
    Classifies claims for verification routing.

    Analyzes claim text to determine:
    - What type of claim it is
    - What values/variables are involved
    - Whether symbolic verification can be applied

    Example:
        classifier = ClaimClassifier()
        result = classifier.classify("50000 - 42000 = 8000")
        assert result.claim_type == ClaimType.ARITHMETIC
        assert result.symbolic_applicable
    """

    # Patterns for claim detection
    ARITHMETIC_PATTERNS: List[Tuple[Pattern, str]] = [
        (re.compile(r"(\d+(?:\.\d+)?)\s*([+\-*/])\s*(\d+(?:\.\d+)?)\s*=\s*(\d+(?:\.\d+)?)"),
         "simple arithmetic equation"),
        (re.compile(r"(?:sum|total|difference|product|quotient|result)\s+(?:is|equals|=)\s*(\d+(?:\.\d+)?)"),
         "named arithmetic result"),
        (re.compile(r"(\w+)\s*([+\-*/])\s*(\w+)\s*=\s*(\d+(?:\.\d+)?)"),
         "variable arithmetic equation"),
        (re.compile(r"(?:calculated?|computed?|equals?|is)\s+(\d+(?:,\d{3})*(?:\.\d+)?)"),
         "calculated result"),
    ]

    CONSTRAINT_PATTERNS: List[Tuple[Pattern, str]] = [
        (re.compile(r"(?:must\s+be|should\s+be|is)\s+(?:greater|less|at\s+least|at\s+most)"),
         "constraint requirement"),
        (re.compile(r"\b(?:satisf(?:y|ies|iable)|feasible|possible|valid)\b", re.I),
         "satisfiability claim"),
        (re.compile(r"(?:between|within|range|limit)"),
         "range constraint"),
        (re.compile(r"(?:and|or|not)\s+(?:greater|less|equal)"),
         "compound constraint"),
    ]

    IMPLICATION_PATTERNS: List[Tuple[Pattern, str]] = [
        (re.compile(r"\b(?:if|when|given|assuming)\b.*\b(?:then|therefore|implies|means)\b", re.I),
         "if-then implication"),
        (re.compile(r"\b(?:because|since|as)\b.*\b(?:therefore|thus|so|hence)\b", re.I),
         "causal implication"),
        (re.compile(r"\b(?:implies|entails|leads\s+to|results\s+in)\b", re.I),
         "explicit implication"),
        (re.compile(r"(?:follows\s+from|derived\s+from|consequence\s+of)"),
         "derived conclusion"),
    ]

    COMPARISON_PATTERNS: List[Tuple[Pattern, str]] = [
        (re.compile(r"(\w+)\s*(>|<|>=|<=|==|!=)\s*(\w+)"),
         "direct comparison"),
        (re.compile(r"\b(?:greater|larger|bigger|more)\s+than\b", re.I),
         "greater than"),
        (re.compile(r"\b(?:less|smaller|fewer)\s+than\b", re.I),
         "less than"),
        (re.compile(r"\b(?:equal|same|identical)\s+(?:to|as)\b", re.I),
         "equality comparison"),
    ]

    EQUALITY_PATTERNS: List[Tuple[Pattern, str]] = [
        (re.compile(r"(\w+)\s*(?:=|==|equals?)\s*(\w+|\d+(?:\.\d+)?)"),
         "equality assertion"),
        (re.compile(r"\b(?:is|are|was|were)\s+(?:equal\s+to|the\s+same\s+as)\b", re.I),
         "equality claim"),
    ]

    # Number extraction pattern
    NUMBER_PATTERN = re.compile(r"-?\d+(?:,\d{3})*(?:\.\d+)?")

    # Variable name pattern
    VARIABLE_PATTERN = re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\b")

    def __init__(self):
        """Initialize the claim classifier."""
        self.classifications_done = 0

    def classify(self, claim: str) -> ClassifiedClaim:
        """
        Classify a claim for verification routing.

        Args:
            claim: The claim text to classify

        Returns:
            ClassifiedClaim with type and extracted information
        """
        self.classifications_done += 1
        claim = claim.strip()

        # Try each classification in order of specificity
        classifiers = [
            (self._check_arithmetic, ClaimType.ARITHMETIC),
            (self._check_implication, ClaimType.IMPLICATION),
            (self._check_constraint, ClaimType.CONSTRAINT),
            (self._check_comparison, ClaimType.COMPARISON),
            (self._check_equality, ClaimType.EQUALITY),
        ]

        for check_fn, claim_type in classifiers:
            result = check_fn(claim)
            if result is not None:
                confidence, reason, extras = result
                return self._build_classified_claim(
                    claim, claim_type, confidence, reason, extras
                )

        # Default to textual/unknown
        return ClassifiedClaim(
            claim_text=claim,
            claim_type=ClaimType.TEXTUAL,
            confidence=0.5,
            symbolic_applicable=False,
            classification_reason="No patterns matched - treating as textual claim",
        )

    def classify_batch(self, claims: List[str]) -> List[ClassifiedClaim]:
        """Classify multiple claims."""
        return [self.classify(claim) for claim in claims]

    def _check_arithmetic(
        self, claim: str
    ) -> Optional[Tuple[float, str, Dict[str, Any]]]:
        """Check if claim is arithmetic."""
        for pattern, description in self.ARITHMETIC_PATTERNS:
            match = pattern.search(claim)
            if match:
                # Extract numbers
                numbers = self._extract_numbers(claim)
                variables = self._extract_variables(claim)

                return (
                    0.9 if len(numbers) >= 2 else 0.7,
                    f"Matched arithmetic pattern: {description}",
                    {
                        "numbers": numbers,
                        "variables": variables,
                        "match_groups": match.groups() if match else [],
                    }
                )
        return None

    def _check_constraint(
        self, claim: str
    ) -> Optional[Tuple[float, str, Dict[str, Any]]]:
        """Check if claim is a constraint."""
        for pattern, description in self.CONSTRAINT_PATTERNS:
            if pattern.search(claim):
                variables = self._extract_variables(claim)
                return (
                    0.85,
                    f"Matched constraint pattern: {description}",
                    {"variables": variables}
                )
        return None

    def _check_implication(
        self, claim: str
    ) -> Optional[Tuple[float, str, Dict[str, Any]]]:
        """Check if claim is an implication."""
        for pattern, description in self.IMPLICATION_PATTERNS:
            if pattern.search(claim):
                # Try to split into premise and conclusion
                parts = self._split_implication(claim)
                return (
                    0.85,
                    f"Matched implication pattern: {description}",
                    {"parts": parts}
                )
        return None

    def _check_comparison(
        self, claim: str
    ) -> Optional[Tuple[float, str, Dict[str, Any]]]:
        """Check if claim is a comparison."""
        for pattern, description in self.COMPARISON_PATTERNS:
            match = pattern.search(claim)
            if match:
                variables = self._extract_variables(claim)
                return (
                    0.8,
                    f"Matched comparison pattern: {description}",
                    {
                        "variables": variables,
                        "match_groups": match.groups() if match else [],
                    }
                )
        return None

    def _check_equality(
        self, claim: str
    ) -> Optional[Tuple[float, str, Dict[str, Any]]]:
        """Check if claim is an equality assertion."""
        for pattern, description in self.EQUALITY_PATTERNS:
            match = pattern.search(claim)
            if match:
                return (
                    0.8,
                    f"Matched equality pattern: {description}",
                    {"match_groups": match.groups() if match else []}
                )
        return None

    def _extract_numbers(self, text: str) -> List[float]:
        """Extract all numbers from text."""
        matches = self.NUMBER_PATTERN.findall(text)
        numbers = []
        for m in matches:
            try:
                # Remove commas from numbers like "50,000"
                clean = m.replace(",", "")
                numbers.append(float(clean))
            except ValueError:
                pass
        return numbers

    def _extract_variables(self, text: str) -> List[str]:
        """Extract potential variable names from text."""
        # Get all identifiers
        matches = self.VARIABLE_PATTERN.findall(text)

        # Filter out common words and keywords
        stopwords = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "must", "shall",
            "if", "then", "else", "when", "where", "which", "that", "this",
            "and", "or", "not", "true", "false", "null", "none",
            "greater", "less", "equal", "than", "to", "from", "between",
            "sum", "total", "difference", "product", "result", "value",
            "calculated", "computed", "equals", "implies", "therefore",
        }

        variables = []
        for m in matches:
            if m.lower() not in stopwords and len(m) > 1:
                variables.append(m)

        return list(set(variables))

    def _split_implication(self, claim: str) -> Dict[str, str]:
        """Try to split an implication into premise and conclusion."""
        # Common patterns for splitting
        splitters = [
            (r"\bthen\b", "if-then"),
            (r"\btherefore\b", "therefore"),
            (r"\bimplies\b", "implies"),
            (r"\bso\b", "so"),
            (r"\bhence\b", "hence"),
        ]

        for pattern, name in splitters:
            match = re.search(pattern, claim, re.I)
            if match:
                premise = claim[:match.start()].strip()
                conclusion = claim[match.end():].strip()
                # Clean up common prefixes
                premise = re.sub(r"^(?:if|when|given|assuming)\s+", "", premise, flags=re.I)
                return {
                    "premise": premise,
                    "conclusion": conclusion,
                    "pattern": name,
                }

        return {"full": claim}

    def _build_classified_claim(
        self,
        claim: str,
        claim_type: ClaimType,
        confidence: float,
        reason: str,
        extras: Dict[str, Any]
    ) -> ClassifiedClaim:
        """Build a ClassifiedClaim from classification results."""
        variables = extras.get("variables", [])

        # Infer variable types (default to real)
        variable_types = {}
        for var in variables:
            # Simple heuristics for type inference
            if var.lower() in ("count", "num", "index", "i", "j", "k", "n"):
                variable_types[var] = "int"
            elif var.lower() in ("flag", "is_", "has_", "should", "can"):
                variable_types[var] = "bool"
            else:
                variable_types[var] = "real"

        # Determine if symbolic verification is applicable
        symbolic_applicable = claim_type in (
            ClaimType.ARITHMETIC,
            ClaimType.CONSTRAINT,
            ClaimType.IMPLICATION,
            ClaimType.COMPARISON,
            ClaimType.EQUALITY,
        )

        return ClassifiedClaim(
            claim_text=claim,
            claim_type=claim_type,
            confidence=confidence,
            extracted_values=extras.get("numbers", {}),
            extracted_operation=None,  # Would need more parsing
            variables=variables,
            variable_types=variable_types,
            symbolic_applicable=symbolic_applicable,
            classification_reason=reason,
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get classification statistics."""
        return {
            "total_classifications": self.classifications_done,
        }


def extract_claims_from_text(text: str) -> List[str]:
    """
    Extract individual claims from a text block.

    Simple heuristic: split by sentences and filter.

    Args:
        text: Block of text potentially containing claims

    Returns:
        List of claim strings
    """
    # Split by sentence endings
    sentences = re.split(r"[.!?]\s+", text)

    claims = []
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 10:
            continue

        # Skip questions
        if sentence.endswith("?"):
            continue

        # Look for claim-like patterns
        if any(pattern in sentence.lower() for pattern in [
            "equals", "is", "are", "was", "were", "=",
            "greater", "less", "more", "fewer",
            "implies", "therefore", "must", "should",
            "calculated", "computed", "result",
        ]):
            claims.append(sentence)

    return claims
