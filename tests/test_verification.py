"""
Tests for Symbolic Verification Module (NESY-005).

Tests symbolic solver, claim classifier, and hybrid verifier.
"""

import pytest
import asyncio

from src.verification.symbolic_solver import (
    VerificationResult,
    SymbolicVerificationOutput,
    SymbolicVerifier,
    SafeExpressionParser,
    is_z3_available,
)
from src.verification.claim_classifier import (
    ClaimType,
    ClassifiedClaim,
    ClaimClassifier,
    extract_claims_from_text,
)
from src.verification.hybrid_verifier import (
    HybridVerifier,
    VerificationReport,
    ClaimVerificationResult,
    quick_verify,
)


# =============================================================================
# SYMBOLIC SOLVER TESTS
# =============================================================================

class TestVerificationResult:
    """Tests for VerificationResult enum."""

    def test_all_results_have_values(self):
        """All results should have string values."""
        for result in VerificationResult:
            assert isinstance(result.value, str)

    def test_result_count(self):
        """Should have expected result types."""
        assert len(VerificationResult) >= 4
        assert VerificationResult.VERIFIED in VerificationResult
        assert VerificationResult.REFUTED in VerificationResult
        assert VerificationResult.UNKNOWN in VerificationResult
        assert VerificationResult.NOT_APPLICABLE in VerificationResult


class TestSymbolicVerificationOutput:
    """Tests for SymbolicVerificationOutput dataclass."""

    def test_create_verified(self):
        """Create verified output."""
        output = SymbolicVerificationOutput(
            result=VerificationResult.VERIFIED,
            explanation="Test verified",
        )
        assert output.is_verified
        assert not output.is_refuted

    def test_create_refuted(self):
        """Create refuted output."""
        output = SymbolicVerificationOutput(
            result=VerificationResult.REFUTED,
            explanation="Test refuted",
            counterexample={"x": 5},
        )
        assert output.is_refuted
        assert not output.is_verified

    def test_to_dict(self):
        """Convert to dictionary."""
        output = SymbolicVerificationOutput(
            result=VerificationResult.VERIFIED,
            explanation="Test",
            verification_time_ms=100,
        )
        d = output.to_dict()
        assert d["result"] == "verified"
        assert d["verification_time_ms"] == 100
        assert "timestamp" in d


class TestSafeExpressionParser:
    """Tests for SafeExpressionParser."""

    def test_parse_simple_addition(self):
        """Parse simple addition."""
        parser = SafeExpressionParser({})
        result = parser.parse_arithmetic("a + b", {"a": 10, "b": 20})
        assert result == 30

    def test_parse_subtraction(self):
        """Parse subtraction."""
        parser = SafeExpressionParser({})
        result = parser.parse_arithmetic("total - spent", {"total": 50000, "spent": 42000})
        assert result == 8000

    def test_parse_multiplication(self):
        """Parse multiplication."""
        parser = SafeExpressionParser({})
        result = parser.parse_arithmetic("price * quantity", {"price": 100, "quantity": 5})
        assert result == 500

    def test_parse_division(self):
        """Parse division."""
        parser = SafeExpressionParser({})
        result = parser.parse_arithmetic("total / count", {"total": 100, "count": 4})
        assert result == 25

    def test_parse_complex_expression(self):
        """Parse complex expression."""
        parser = SafeExpressionParser({})
        result = parser.parse_arithmetic("a + b * c", {"a": 10, "b": 5, "c": 3})
        # Should respect precedence: 10 + (5 * 3) = 25
        assert result == 25

    def test_parse_with_parentheses(self):
        """Parse expression with parentheses."""
        parser = SafeExpressionParser({})
        result = parser.parse_arithmetic("(a + b) * c", {"a": 10, "b": 5, "c": 3})
        assert result == 45


class TestSymbolicVerifier:
    """Tests for SymbolicVerifier class."""

    @pytest.fixture
    def verifier(self):
        return SymbolicVerifier(timeout_ms=5000)

    def test_verify_arithmetic_correct(self, verifier):
        """Verify correct arithmetic."""
        result = verifier.verify_arithmetic(
            values={"total": 50000, "spent": 42000},
            claimed_result=8000,
            operation="total - spent"
        )
        assert result.is_verified
        assert "8000" in result.explanation

    def test_verify_arithmetic_incorrect(self, verifier):
        """Refute incorrect arithmetic."""
        result = verifier.verify_arithmetic(
            values={"total": 50000, "spent": 42000},
            claimed_result=10000,
            operation="total - spent"
        )
        assert result.is_refuted
        assert result.counterexample["actual"] == 8000
        assert result.counterexample["expected"] == 10000

    def test_verify_arithmetic_with_tolerance(self, verifier):
        """Verify arithmetic with tolerance."""
        result = verifier.verify_arithmetic(
            values={"a": 1.0, "b": 3.0},
            claimed_result=0.333,
            operation="a / b",
            tolerance=0.01
        )
        assert result.is_verified

    def test_verify_arithmetic_invalid_operation(self, verifier):
        """Handle invalid operation."""
        result = verifier.verify_arithmetic(
            values={"a": 10},
            claimed_result=0,
            operation="undefined_var + a"
        )
        assert result.result == VerificationResult.NOT_APPLICABLE

    @pytest.mark.skipif(not is_z3_available(), reason="Z3 not installed")
    def test_verify_constraints_satisfiable(self, verifier):
        """Verify satisfiable constraints."""
        result = verifier.verify_constraints(
            constraints=["x > 0", "x < 10"],
            variable_types={"x": "int"},
            should_be_satisfiable=True
        )
        assert result.is_verified

    @pytest.mark.skipif(not is_z3_available(), reason="Z3 not installed")
    def test_verify_constraints_unsatisfiable(self, verifier):
        """Refute satisfiability claim for unsatisfiable constraints."""
        result = verifier.verify_constraints(
            constraints=["x > 0", "x < 0"],
            variable_types={"x": "real"},
            should_be_satisfiable=True
        )
        assert result.is_refuted

    @pytest.mark.skipif(not is_z3_available(), reason="Z3 not installed")
    def test_verify_implication_valid(self, verifier):
        """Verify valid implication."""
        result = verifier.verify_implication(
            premises=["x > 5"],
            conclusion="x > 0",
            variable_types={"x": "int"}
        )
        assert result.is_verified

    @pytest.mark.skipif(not is_z3_available(), reason="Z3 not installed")
    def test_verify_implication_invalid(self, verifier):
        """Refute invalid implication."""
        result = verifier.verify_implication(
            premises=["x > 0"],
            conclusion="x > 5",
            variable_types={"x": "int"}
        )
        assert result.is_refuted
        assert "counterexample" in result.to_dict() or result.counterexample is not None

    def test_get_stats(self, verifier):
        """Get verification statistics."""
        verifier.verify_arithmetic(
            values={"a": 1, "b": 2},
            claimed_result=3,
            operation="a + b"
        )
        stats = verifier.get_stats()
        assert stats["total_verifications"] == 1
        assert stats["verified"] == 1


# =============================================================================
# CLAIM CLASSIFIER TESTS
# =============================================================================

class TestClaimType:
    """Tests for ClaimType enum."""

    def test_all_types_have_values(self):
        """All types should have string values."""
        for claim_type in ClaimType:
            assert isinstance(claim_type.value, str)


class TestClassifiedClaim:
    """Tests for ClassifiedClaim dataclass."""

    def test_create_classified_claim(self):
        """Create classified claim."""
        claim = ClassifiedClaim(
            claim_text="x equals 5",
            claim_type=ClaimType.EQUALITY,
            confidence=0.9,
            symbolic_applicable=True,
        )
        assert claim.claim_type == ClaimType.EQUALITY
        assert claim.symbolic_applicable

    def test_to_dict(self):
        """Convert to dictionary."""
        claim = ClassifiedClaim(
            claim_text="test",
            claim_type=ClaimType.ARITHMETIC,
            confidence=0.85,
        )
        d = claim.to_dict()
        assert d["claim_type"] == "arithmetic"
        assert d["confidence"] == 0.85


class TestClaimClassifier:
    """Tests for ClaimClassifier class."""

    @pytest.fixture
    def classifier(self):
        return ClaimClassifier()

    def test_classify_arithmetic_simple(self, classifier):
        """Classify simple arithmetic claim."""
        result = classifier.classify("10 + 5 = 15")
        assert result.claim_type == ClaimType.ARITHMETIC
        assert result.symbolic_applicable

    def test_classify_arithmetic_with_result(self, classifier):
        """Classify arithmetic with result keyword."""
        result = classifier.classify("The total equals 500")
        assert result.claim_type == ClaimType.ARITHMETIC

    def test_classify_implication(self, classifier):
        """Classify implication claim."""
        result = classifier.classify("If x is greater than 5, then y must be positive")
        assert result.claim_type == ClaimType.IMPLICATION
        assert result.symbolic_applicable

    def test_classify_constraint(self, classifier):
        """Classify constraint claim."""
        result = classifier.classify("The value must be between 0 and 100")
        assert result.claim_type == ClaimType.CONSTRAINT

    def test_classify_comparison(self, classifier):
        """Classify comparison claim."""
        result = classifier.classify("100 > 50")
        assert result.claim_type == ClaimType.COMPARISON

    def test_classify_textual(self, classifier):
        """Classify textual claim (no patterns)."""
        result = classifier.classify("The quick brown fox jumps over the lazy dog")
        assert result.claim_type == ClaimType.TEXTUAL
        assert not result.symbolic_applicable

    def test_batch_classify(self, classifier):
        """Classify multiple claims."""
        claims = [
            "10 + 5 = 15",
            "If x > 0 then y > 0",
            "The sky is blue"
        ]
        results = classifier.classify_batch(claims)
        assert len(results) == 3
        assert results[0].claim_type == ClaimType.ARITHMETIC
        assert results[1].claim_type == ClaimType.IMPLICATION
        assert results[2].claim_type == ClaimType.TEXTUAL


class TestExtractClaims:
    """Tests for extract_claims_from_text function."""

    def test_extract_simple_claims(self):
        """Extract claims from simple text."""
        text = "The result is 500. The total equals 100."
        claims = extract_claims_from_text(text)
        assert len(claims) >= 1

    def test_extract_no_claims(self):
        """Handle text with no claims."""
        text = "Hello world"
        claims = extract_claims_from_text(text)
        assert len(claims) == 0

    def test_skip_questions(self):
        """Skip questions."""
        text = "What is the result? The answer is 42."
        claims = extract_claims_from_text(text)
        # Should only include the statement, not the question
        assert not any("?" in c for c in claims)


# =============================================================================
# HYBRID VERIFIER TESTS
# =============================================================================

class TestHybridVerifier:
    """Tests for HybridVerifier class."""

    @pytest.fixture
    def verifier(self):
        return HybridVerifier()

    @pytest.mark.asyncio
    async def test_verify_arithmetic_claim(self, verifier):
        """Verify arithmetic claim through hybrid verifier."""
        result = await verifier.verify_claim(
            "50 - 20 = 30",
            context={}
        )
        assert result.verification_method == "symbolic"
        assert result.result == VerificationResult.VERIFIED

    @pytest.mark.asyncio
    async def test_verify_incorrect_arithmetic(self, verifier):
        """Refute incorrect arithmetic claim."""
        result = await verifier.verify_claim(
            "50 - 20 = 40",
            context={}
        )
        assert result.result == VerificationResult.REFUTED

    @pytest.mark.asyncio
    async def test_verify_content(self, verifier):
        """Verify content with multiple claims."""
        report = await verifier.verify_content(
            content="The budget is $50. We spent $20. Remaining is $30.",
            claims=["50 - 20 = 30"]
        )
        assert isinstance(report, VerificationReport)
        assert report.total_claims >= 1

    @pytest.mark.asyncio
    async def test_fallback_to_llm(self, verifier):
        """Fall back to LLM for non-symbolic claims."""
        result = await verifier.verify_claim(
            "The implementation is well-designed",
            context={}
        )
        # Should fall back (no LLM configured, so result is UNKNOWN)
        assert result.verification_method == "llm"

    @pytest.mark.asyncio
    async def test_verification_report_properties(self, verifier):
        """Test VerificationReport properties."""
        report = await verifier.verify_content(
            content="10 + 5 = 15",
            claims=["10 + 5 = 15"]
        )
        assert isinstance(report.verification_rate, float)
        assert report.verification_time_ms >= 0

    def test_get_stats(self, verifier):
        """Get verifier statistics."""
        stats = verifier.get_stats()
        assert "total_verifications" in stats
        assert "symbolic_verifications" in stats
        assert "llm_verifications" in stats


class TestClaimVerificationResult:
    """Tests for ClaimVerificationResult dataclass."""

    def test_to_dict(self):
        """Convert to dictionary."""
        claim = ClassifiedClaim(
            claim_text="test",
            claim_type=ClaimType.ARITHMETIC,
            confidence=0.9,
        )
        output = SymbolicVerificationOutput(
            result=VerificationResult.VERIFIED,
            explanation="Test verified",
        )
        result = ClaimVerificationResult(
            claim=claim,
            verification_method="symbolic",
            result=VerificationResult.VERIFIED,
            output=output,
        )
        d = result.to_dict()
        assert d["verification_method"] == "symbolic"
        assert d["result"] == "verified"


class TestVerificationReport:
    """Tests for VerificationReport dataclass."""

    def test_all_verified_property(self):
        """Test all_verified property."""
        report = VerificationReport(
            content_summary="test",
            total_claims=2,
            verified_claims=[],  # Would have actual claims
            refuted_claims=[],
            uncertain_claims=[],
            symbolic_count=1,
            llm_count=1,
            overall_confidence=0.9,
            verification_time_ms=100,
        )
        # Note: This shows all_verified is True when no refuted/uncertain
        # In real use, verified_claims would have items
        assert report.all_verified

    def test_has_refuted_property(self):
        """Test has_refuted property."""
        claim = ClassifiedClaim("test", ClaimType.ARITHMETIC, 0.9)
        output = SymbolicVerificationOutput(
            result=VerificationResult.REFUTED,
            explanation="Refuted",
        )
        refuted = ClaimVerificationResult(
            claim=claim,
            verification_method="symbolic",
            result=VerificationResult.REFUTED,
            output=output,
        )
        report = VerificationReport(
            content_summary="test",
            total_claims=1,
            verified_claims=[],
            refuted_claims=[refuted],
            uncertain_claims=[],
            symbolic_count=1,
            llm_count=0,
            overall_confidence=0.5,
            verification_time_ms=50,
        )
        assert report.has_refuted


class TestQuickVerify:
    """Tests for quick_verify function."""

    @pytest.mark.asyncio
    async def test_quick_verify_correct(self):
        """Quick verify correct claim."""
        result = await quick_verify("100 + 50 = 150")
        assert result.result == VerificationResult.VERIFIED

    @pytest.mark.asyncio
    async def test_quick_verify_incorrect(self):
        """Quick verify incorrect claim."""
        result = await quick_verify("100 + 50 = 200")
        assert result.result == VerificationResult.REFUTED


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestVerificationIntegration:
    """Integration tests for verification system."""

    @pytest.mark.asyncio
    async def test_full_verification_workflow(self):
        """Test complete verification workflow."""
        verifier = HybridVerifier()

        content = """
        Financial Report Summary:
        Total budget: $100,000
        Amount spent: $75,000
        Remaining budget: $25,000
        """

        # Extract and verify claims
        report = await verifier.verify_content(
            content=content,
            claims=["100000 - 75000 = 25000"]
        )

        assert report.total_claims >= 1
        assert report.verification_time_ms >= 0

    @pytest.mark.asyncio
    async def test_mixed_claim_types(self):
        """Test verification with mixed claim types."""
        verifier = HybridVerifier()

        claims = [
            "50 + 50 = 100",  # Arithmetic
            "The implementation is robust",  # Textual
        ]

        report = await verifier.verify_content(
            content="Test content",
            claims=claims
        )

        assert report.symbolic_count >= 1
        assert report.llm_count >= 1

    @pytest.mark.skipif(not is_z3_available(), reason="Z3 not installed")
    @pytest.mark.asyncio
    async def test_constraint_verification_integration(self):
        """Test constraint verification in hybrid mode."""
        verifier = HybridVerifier()

        # Provide structured context for constraint verification
        result = await verifier.verify_claim(
            claim="x must be positive and less than 10",
            context={
                "constraints": ["x > 0", "x < 10"],
                "variable_types": {"x": "int"},
                "should_be_satisfiable": True
            }
        )

        assert result.result in (
            VerificationResult.VERIFIED,
            VerificationResult.NOT_APPLICABLE  # If parsing fails
        )


class TestZ3Availability:
    """Tests for Z3 availability checking."""

    def test_is_z3_available_returns_bool(self):
        """is_z3_available should return boolean."""
        result = is_z3_available()
        assert isinstance(result, bool)

    @pytest.mark.skipif(not is_z3_available(), reason="Z3 not installed")
    def test_z3_imports_work(self):
        """Verify Z3 imports when available."""
        from z3 import Int, Real, Bool, Solver
        s = Solver()
        x = Int('x')
        s.add(x > 0)
        assert s.check().r == 1  # sat
