"""
Symbolic Verification Module.

Provides formal verification using Z3 theorem prover for claims
with logical or mathematical structure. Complements LLM-based
evaluation with provably correct verification.

Version: 2.6.0
"""

from .symbolic_solver import (
    VerificationResult,
    SymbolicVerificationOutput,
    SymbolicVerifier,
)
from .claim_classifier import (
    ClaimType,
    ClassifiedClaim,
    ClaimClassifier,
)
from .hybrid_verifier import (
    HybridVerifier,
    VerificationReport,
)

__all__ = [
    # Symbolic Solver
    "VerificationResult",
    "SymbolicVerificationOutput",
    "SymbolicVerifier",
    # Claim Classifier
    "ClaimType",
    "ClassifiedClaim",
    "ClaimClassifier",
    # Hybrid Verifier
    "HybridVerifier",
    "VerificationReport",
]
