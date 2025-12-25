"""
Hybrid Verification combining Symbolic and LLM approaches.

Routes claims to appropriate verification method based on type,
providing formal proofs where possible and LLM evaluation otherwise.

Version: 2.6.0
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Callable, Union

from .symbolic_solver import (
    SymbolicVerifier,
    SymbolicVerificationOutput,
    VerificationResult,
)
from .claim_classifier import (
    ClaimClassifier,
    ClassifiedClaim,
    ClaimType,
    extract_claims_from_text,
)

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


@dataclass
class ClaimVerificationResult:
    """
    Result of verifying a single claim.

    Attributes:
        claim: The classified claim
        verification_method: "symbolic" or "llm"
        result: Verification result
        output: Detailed verification output
        fallback_used: Whether LLM fallback was used
    """
    claim: ClassifiedClaim
    verification_method: str
    result: VerificationResult
    output: Union[SymbolicVerificationOutput, Dict[str, Any]]
    fallback_used: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        output_dict = (
            self.output.to_dict()
            if isinstance(self.output, SymbolicVerificationOutput)
            else self.output
        )
        return {
            "claim": self.claim.to_dict(),
            "verification_method": self.verification_method,
            "result": self.result.value,
            "output": output_dict,
            "fallback_used": self.fallback_used,
        }


@dataclass
class VerificationReport:
    """
    Complete verification report for content.

    Attributes:
        content_summary: Summary of verified content
        total_claims: Number of claims analyzed
        verified_claims: Claims that passed verification
        refuted_claims: Claims that failed verification
        uncertain_claims: Claims with unknown/not applicable results
        symbolic_count: Claims verified symbolically
        llm_count: Claims verified by LLM
        overall_confidence: Aggregate confidence score
        verification_time_ms: Total verification time
    """
    content_summary: str
    total_claims: int
    verified_claims: List[ClaimVerificationResult]
    refuted_claims: List[ClaimVerificationResult]
    uncertain_claims: List[ClaimVerificationResult]
    symbolic_count: int
    llm_count: int
    overall_confidence: float
    verification_time_ms: int
    timestamp: datetime = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "content_summary": self.content_summary[:200],
            "total_claims": self.total_claims,
            "verified_count": len(self.verified_claims),
            "refuted_count": len(self.refuted_claims),
            "uncertain_count": len(self.uncertain_claims),
            "symbolic_count": self.symbolic_count,
            "llm_count": self.llm_count,
            "overall_confidence": self.overall_confidence,
            "verification_time_ms": self.verification_time_ms,
            "timestamp": self.timestamp.isoformat(),
            "verified_claims": [c.to_dict() for c in self.verified_claims],
            "refuted_claims": [c.to_dict() for c in self.refuted_claims],
            "uncertain_claims": [c.to_dict() for c in self.uncertain_claims],
        }

    @property
    def all_verified(self) -> bool:
        """Check if all claims were verified."""
        return len(self.refuted_claims) == 0 and len(self.uncertain_claims) == 0

    @property
    def has_refuted(self) -> bool:
        """Check if any claims were refuted."""
        return len(self.refuted_claims) > 0

    @property
    def verification_rate(self) -> float:
        """Calculate rate of verified claims."""
        if self.total_claims == 0:
            return 0.0
        return len(self.verified_claims) / self.total_claims


class HybridVerifier:
    """
    Combines LLM judges with symbolic verification.

    Routes claims to appropriate verification method:
    - Arithmetic claims → Symbolic verifier
    - Constraint claims → Symbolic verifier
    - Implication claims → Symbolic verifier
    - Other claims → LLM judge

    Example:
        verifier = HybridVerifier()
        report = await verifier.verify_content(
            content="The budget is $50,000. We spent $42,000. Remaining is $10,000.",
            context={"domain": "finance"}
        )
        if report.has_refuted:
            print("Found errors:", report.refuted_claims)
    """

    def __init__(
        self,
        symbolic_verifier: Optional[SymbolicVerifier] = None,
        llm_judge: Optional[Callable] = None,
        timeout_ms: int = 5000,
    ):
        """
        Initialize the hybrid verifier.

        Args:
            symbolic_verifier: SymbolicVerifier instance (created if not provided)
            llm_judge: Async function for LLM verification (optional)
            timeout_ms: Timeout for symbolic verification
        """
        self.symbolic = symbolic_verifier or SymbolicVerifier(timeout_ms=timeout_ms)
        self.llm_judge = llm_judge
        self.classifier = ClaimClassifier()

        # Statistics
        self.verifications_run = 0
        self.symbolic_verifications = 0
        self.llm_verifications = 0
        self.fallbacks = 0

    async def verify_content(
        self,
        content: str,
        context: Optional[Dict[str, Any]] = None,
        claims: Optional[List[str]] = None,
    ) -> VerificationReport:
        """
        Verify all claims in content.

        Args:
            content: Content to verify
            context: Additional context for verification
            claims: Pre-extracted claims (if not provided, will extract)

        Returns:
            VerificationReport with all results
        """
        import time
        start_time = time.time()

        context = context or {}

        # Extract claims if not provided
        if claims is None:
            claims = extract_claims_from_text(content)

        # Classify all claims
        classified_claims = self.classifier.classify_batch(claims)

        # Verify each claim
        results: List[ClaimVerificationResult] = []
        for classified in classified_claims:
            result = await self._verify_claim(classified, context)
            results.append(result)

        # Aggregate results
        verified = [r for r in results if r.result == VerificationResult.VERIFIED]
        refuted = [r for r in results if r.result == VerificationResult.REFUTED]
        uncertain = [r for r in results if r.result not in (
            VerificationResult.VERIFIED, VerificationResult.REFUTED
        )]

        symbolic_count = sum(1 for r in results if r.verification_method == "symbolic")
        llm_count = sum(1 for r in results if r.verification_method == "llm")

        # Calculate overall confidence
        if results:
            confidences = [r.claim.confidence for r in results]
            overall_confidence = sum(confidences) / len(confidences)
        else:
            overall_confidence = 0.0

        elapsed_ms = int((time.time() - start_time) * 1000)

        self.verifications_run += 1

        return VerificationReport(
            content_summary=content[:500],
            total_claims=len(results),
            verified_claims=verified,
            refuted_claims=refuted,
            uncertain_claims=uncertain,
            symbolic_count=symbolic_count,
            llm_count=llm_count,
            overall_confidence=overall_confidence,
            verification_time_ms=elapsed_ms,
        )

    async def verify_claim(
        self,
        claim: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> ClaimVerificationResult:
        """
        Verify a single claim.

        Args:
            claim: Claim text to verify
            context: Additional context

        Returns:
            ClaimVerificationResult
        """
        classified = self.classifier.classify(claim)
        return await self._verify_claim(classified, context or {})

    async def _verify_claim(
        self,
        claim: ClassifiedClaim,
        context: Dict[str, Any],
    ) -> ClaimVerificationResult:
        """Internal claim verification with routing."""
        # Try symbolic verification first if applicable
        if claim.symbolic_applicable:
            result = self._try_symbolic_verification(claim, context)
            if result.result != VerificationResult.NOT_APPLICABLE:
                self.symbolic_verifications += 1
                return ClaimVerificationResult(
                    claim=claim,
                    verification_method="symbolic",
                    result=result.result,
                    output=result,
                    fallback_used=False,
                )

        # Fall back to LLM verification
        self.fallbacks += 1
        result = await self._llm_verification(claim, context)
        self.llm_verifications += 1

        return ClaimVerificationResult(
            claim=claim,
            verification_method="llm",
            result=result.get("result", VerificationResult.UNKNOWN),
            output=result,
            fallback_used=claim.symbolic_applicable,
        )

    def _try_symbolic_verification(
        self,
        claim: ClassifiedClaim,
        context: Dict[str, Any],
    ) -> SymbolicVerificationOutput:
        """Attempt symbolic verification based on claim type."""
        try:
            if claim.claim_type == ClaimType.ARITHMETIC:
                return self._verify_arithmetic_claim(claim, context)

            elif claim.claim_type == ClaimType.CONSTRAINT:
                return self._verify_constraint_claim(claim, context)

            elif claim.claim_type == ClaimType.IMPLICATION:
                return self._verify_implication_claim(claim, context)

            elif claim.claim_type == ClaimType.COMPARISON:
                return self._verify_comparison_claim(claim, context)

            elif claim.claim_type == ClaimType.EQUALITY:
                return self._verify_equality_claim(claim, context)

            else:
                return SymbolicVerificationOutput(
                    result=VerificationResult.NOT_APPLICABLE,
                    explanation=f"No symbolic verification for {claim.claim_type.value}",
                )

        except Exception as e:
            logger.warning(f"Symbolic verification failed: {e}")
            return SymbolicVerificationOutput(
                result=VerificationResult.NOT_APPLICABLE,
                explanation=f"Symbolic verification error: {e}",
            )

    def _verify_arithmetic_claim(
        self,
        claim: ClassifiedClaim,
        context: Dict[str, Any],
    ) -> SymbolicVerificationOutput:
        """Verify an arithmetic claim."""
        # Try to extract values and operation from claim text
        import re

        text = claim.claim_text

        # Pattern: "A op B = C" or similar (note: - must be at end of char class or escaped)
        match = re.search(
            r"(\d+(?:,\d{3})*(?:\.\d+)?)\s*([+*/\-])\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:=|equals?|is)\s*(\d+(?:,\d{3})*(?:\.\d+)?)",
            text
        )

        if match:
            a = float(match.group(1).replace(",", ""))
            op = match.group(2)
            b = float(match.group(3).replace(",", ""))
            claimed = float(match.group(4).replace(",", ""))

            return self.symbolic.verify_arithmetic(
                values={"a": a, "b": b},
                claimed_result=claimed,
                operation=f"a {op} b"
            )

        # Try simpler pattern for expressions like "50 - 20 = 30"
        simple_match = re.search(
            r"(\d+)\s*([+\-*/])\s*(\d+)\s*=\s*(\d+)",
            text
        )
        if simple_match:
            a = float(simple_match.group(1))
            op = simple_match.group(2)
            b = float(simple_match.group(3))
            claimed = float(simple_match.group(4))

            return self.symbolic.verify_arithmetic(
                values={"a": a, "b": b},
                claimed_result=claimed,
                operation=f"a {op} b"
            )

        # Try context-based verification
        if "values" in context and "operation" in context and "claimed_result" in context:
            return self.symbolic.verify_arithmetic(
                values=context["values"],
                claimed_result=context["claimed_result"],
                operation=context["operation"]
            )

        return SymbolicVerificationOutput(
            result=VerificationResult.NOT_APPLICABLE,
            explanation="Could not extract arithmetic components from claim",
        )

    def _verify_constraint_claim(
        self,
        claim: ClassifiedClaim,
        context: Dict[str, Any],
    ) -> SymbolicVerificationOutput:
        """Verify a constraint claim."""
        # Check if context provides structured constraints
        if "constraints" in context and "variable_types" in context:
            return self.symbolic.verify_constraints(
                constraints=context["constraints"],
                variable_types=context["variable_types"],
                should_be_satisfiable=context.get("should_be_satisfiable", True)
            )

        # Try to parse simple constraints from claim text
        # This would need more sophisticated NLP in production
        return SymbolicVerificationOutput(
            result=VerificationResult.NOT_APPLICABLE,
            explanation="Constraint extraction from natural language not yet implemented",
        )

    def _verify_implication_claim(
        self,
        claim: ClassifiedClaim,
        context: Dict[str, Any],
    ) -> SymbolicVerificationOutput:
        """Verify an implication claim."""
        # Check if context provides structured premises and conclusion
        if "premises" in context and "conclusion" in context and "variable_types" in context:
            return self.symbolic.verify_implication(
                premises=context["premises"],
                conclusion=context["conclusion"],
                variable_types=context["variable_types"]
            )

        return SymbolicVerificationOutput(
            result=VerificationResult.NOT_APPLICABLE,
            explanation="Implication extraction from natural language not yet implemented",
        )

    def _verify_comparison_claim(
        self,
        claim: ClassifiedClaim,
        context: Dict[str, Any],
    ) -> SymbolicVerificationOutput:
        """Verify a comparison claim."""
        import re

        text = claim.claim_text

        # Pattern: "A > B" style comparisons
        match = re.search(
            r"(\d+(?:\.\d+)?)\s*(>|<|>=|<=|==|!=)\s*(\d+(?:\.\d+)?)",
            text
        )

        if match:
            a = float(match.group(1))
            op = match.group(2)
            b = float(match.group(3))

            # Verify the comparison
            import operator
            ops = {
                ">": operator.gt,
                "<": operator.lt,
                ">=": operator.ge,
                "<=": operator.le,
                "==": operator.eq,
                "!=": operator.ne,
            }

            actual_result = ops[op](a, b)

            if actual_result:
                return SymbolicVerificationOutput(
                    result=VerificationResult.VERIFIED,
                    explanation=f"Comparison verified: {a} {op} {b} is True",
                    claim_text=claim.claim_text,
                )
            else:
                return SymbolicVerificationOutput(
                    result=VerificationResult.REFUTED,
                    explanation=f"Comparison false: {a} {op} {b} is False",
                    claim_text=claim.claim_text,
                )

        return SymbolicVerificationOutput(
            result=VerificationResult.NOT_APPLICABLE,
            explanation="Could not extract comparison from claim",
        )

    def _verify_equality_claim(
        self,
        claim: ClassifiedClaim,
        context: Dict[str, Any],
    ) -> SymbolicVerificationOutput:
        """Verify an equality claim."""
        # Check for structured context
        if "expr1" in context and "expr2" in context and "variable_types" in context:
            return self.symbolic.verify_equality(
                expr1=context["expr1"],
                expr2=context["expr2"],
                variable_types=context["variable_types"]
            )

        return SymbolicVerificationOutput(
            result=VerificationResult.NOT_APPLICABLE,
            explanation="Equality verification requires structured expressions",
        )

    async def _llm_verification(
        self,
        claim: ClassifiedClaim,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Fall back to LLM verification."""
        if self.llm_judge is None:
            return {
                "result": VerificationResult.UNKNOWN,
                "explanation": "No LLM judge configured",
                "method": "llm",
            }

        try:
            result = await self.llm_judge(claim.claim_text, context)
            return result
        except Exception as e:
            logger.error(f"LLM verification failed: {e}")
            return {
                "result": VerificationResult.UNKNOWN,
                "explanation": f"LLM verification error: {e}",
                "method": "llm",
            }

    def get_stats(self) -> Dict[str, Any]:
        """Get verification statistics."""
        return {
            "total_verifications": self.verifications_run,
            "symbolic_verifications": self.symbolic_verifications,
            "llm_verifications": self.llm_verifications,
            "fallbacks": self.fallbacks,
            "symbolic_rate": (
                self.symbolic_verifications / (self.symbolic_verifications + self.llm_verifications)
                if (self.symbolic_verifications + self.llm_verifications) > 0 else 0.0
            ),
            "classifier_stats": self.classifier.get_stats(),
            "symbolic_stats": self.symbolic.get_stats(),
        }


async def quick_verify(
    claim: str,
    context: Optional[Dict[str, Any]] = None,
) -> ClaimVerificationResult:
    """
    Quick verification of a single claim.

    Args:
        claim: Claim text to verify
        context: Optional context

    Returns:
        ClaimVerificationResult
    """
    verifier = HybridVerifier()
    return await verifier.verify_claim(claim, context)
