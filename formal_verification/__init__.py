"""Formal Verification Cognitive Dissonance Detection Module.

This module combines DSPy-based cognitive dissonance detection with formal 
verification methods using theorem provers like Coq to provide mathematically
rigorous conflict resolution for agent claims about code properties.
"""

from .detector import FormalVerificationConflictDetector
from .translator import ClaimTranslator  
from .prover import CoqProver
from .types import Claim, FormalSpec, ProofResult, PropertyType

__version__ = "0.1.0"

__all__ = [
    "FormalVerificationConflictDetector",
    "ClaimTranslator",
    "CoqProver", 
    "Claim",
    "FormalSpec",
    "ProofResult",
    "PropertyType",
]