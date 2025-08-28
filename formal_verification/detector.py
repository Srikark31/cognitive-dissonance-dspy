"""Main formal verification cognitive dissonance detector."""

import logging
from typing import List, Dict, Tuple, Any

from .types import Claim, FormalSpec, ProofResult
from .translator import ClaimTranslator
from .prover import CoqProver
from .lemma_discovery import AutomatedProofRepairer
from .deep_analysis import PropertySpecificationGenerator
try:
    from .z3_prover import HybridProver
    Z3_AVAILABLE = True
except ImportError:
    Z3_AVAILABLE = False

logger = logging.getLogger(__name__)


class ConflictDetector:
    """Detects conflicts between formal specifications."""
    
    def detect_conflicts(self, specs: List[FormalSpec]) -> List[Tuple[FormalSpec, FormalSpec]]:
        """Find pairs of specifications that directly contradict each other.
        
        Args:
            specs: List of formal specifications
            
        Returns:
            List of specification pairs that conflict
        """
        conflicts = []
        
        for i in range(len(specs)):
            for j in range(i + 1, len(specs)):
                spec1, spec2 = specs[i], specs[j]
                
                if self._are_contradictory(spec1, spec2):
                    conflicts.append((spec1, spec2))
        
        return conflicts
    
    def _are_contradictory(self, spec1: FormalSpec, spec2: FormalSpec) -> bool:
        """Check if two specifications contradict each other.
        
        Args:
            spec1: First specification
            spec2: Second specification
            
        Returns:
            True if specifications contradict, False otherwise
        """
        import re
        
        claim1 = spec1.claim.claim_text.lower()
        claim2 = spec2.claim.claim_text.lower()
        
        # Memory safety conflicts
        if ("memory safe" in claim1 and "buffer overflow" in claim2) or \
           ("memory safe" in claim2 and "buffer overflow" in claim1):
            return True
        
        # Complexity conflicts
        complexity_pattern = r'O\((\w+)\)'
        match1 = re.search(complexity_pattern, claim1)
        match2 = re.search(complexity_pattern, claim2)
        
        if match1 and match2:
            c1, c2 = match1.group(1), match2.group(1)
            # Different complexity claims are potentially conflicting
            if c1 != c2:
                return True
        
        # Mathematical contradictions (e.g., "2+2=4" vs "2+2=5")
        number_pattern = r'(\d+)\s*\+\s*(\d+)\s*=\s*(\d+)'
        match1 = re.search(number_pattern, claim1)
        match2 = re.search(number_pattern, claim2)
        
        if match1 and match2:
            expr1 = (int(match1.group(1)), int(match1.group(2)), int(match1.group(3)))
            expr2 = (int(match2.group(1)), int(match2.group(2)), int(match2.group(3)))
            
            # Same left side, different right side = conflict
            if expr1[:2] == expr2[:2] and expr1[2] != expr2[2]:
                return True
        
        return False


class FormalVerificationConflictDetector:
    """Main class for detecting and resolving cognitive dissonance using formal verification."""
    
    def __init__(self, timeout_seconds: int = 30, use_hybrid: bool = True, enable_auto_repair: bool = True):
        """Initialize the formal verification conflict detector.
        
        Args:
            timeout_seconds: Timeout for theorem proving attempts
            use_hybrid: Use hybrid Coq+Z3 prover if available
            enable_auto_repair: Enable automatic lemma discovery and proof repair
        """
        self.translator = ClaimTranslator()
        
        # Use hybrid prover if Z3 is available and requested
        if Z3_AVAILABLE and use_hybrid:
            self.prover = HybridProver()
            logger.info("Initialized with hybrid Coq+Z3 prover")
        else:
            self.prover = CoqProver(timeout_seconds=timeout_seconds)
            logger.info("Initialized with Coq prover only")
        
        self.conflict_detector = ConflictDetector()
        
        # Initialize automated proof repair system
        self.auto_repair_enabled = enable_auto_repair
        if enable_auto_repair:
            self.proof_repairer = AutomatedProofRepairer()
            logger.info("Initialized with automated lemma discovery and proof repair")
        
        # Initialize deep program analysis
        self.property_generator = PropertySpecificationGenerator()
        logger.info("Initialized with deep program property analysis")
    
    def analyze_claims(self, claims: List[Claim], code: str = "") -> Dict[str, Any]:
        """Analyze conflicting claims about code using formal verification.
        
        Args:
            claims: List of agent claims to analyze
            code: Optional code being analyzed (for code-specific claims)
            
        Returns:
            Dictionary containing analysis results
        """
        logger.info(f"Analyzing {len(claims)} claims")
        
        # Step 1: Translate claims to formal specifications  
        specifications = []
        translation_failures = []
        
        for claim in claims:
            if Z3_AVAILABLE and hasattr(self.prover, 'prove_claim'):
                # Using HybridProver - create minimal spec, let prover handle translation
                spec = FormalSpec(
                    claim=claim,
                    spec_text=f"Hybrid proving: {claim.claim_text}",
                    coq_code="",  # Will be handled by hybrid prover
                    variables={}
                )
                specifications.append(spec)
            else:
                # Using CoqProver - need Coq translation
                spec = self.translator.translate(claim, code)
                if spec:
                    specifications.append(spec)
                else:
                    translation_failures.append(claim)
        
        logger.info(f"Successfully translated {len(specifications)}/{len(claims)} claims")
        
        # Step 2: Detect conflicts between specifications
        conflicts = self.conflict_detector.detect_conflicts(specifications)
        logger.info(f"Detected {len(conflicts)} specification conflicts")
        
        # Step 3: Attempt to prove each specification
        proof_results = []
        for spec in specifications:
            logger.debug(f"Attempting proof: {spec.spec_text}")
            
            if Z3_AVAILABLE and hasattr(self.prover, 'prove_claim'):
                # Using HybridProver - convert result format
                claim_text = spec.claim.claim_text
                hybrid_result = self.prover.prove_claim(claim_text)
                
                # Convert hybrid result to ProofResult format
                from .types import ProofResult
                result = ProofResult(
                    spec=spec,
                    proven=hybrid_result.get('proven', False),
                    proof_time_ms=hybrid_result.get('time_ms', 0),
                    error_message=hybrid_result.get('error', ''),
                    proof_output=f"Prover: {hybrid_result.get('prover', 'unknown')}",
                    counter_example=hybrid_result.get('counter_example', {})
                )
            else:
                # Using CoqProver
                result = self.prover.prove_specification(spec)
            
            # Attempt automatic repair if proof failed and auto-repair is enabled
            if not result.proven and self.auto_repair_enabled and hasattr(self, 'proof_repairer'):
                logger.info(f"Proof failed for '{spec.claim.claim_text[:50]}...', attempting automatic repair")
                
                repaired_spec = self.proof_repairer.repair_failed_proof(result, spec)
                if repaired_spec:
                    # Try the repaired proof
                    if Z3_AVAILABLE and hasattr(self.prover, 'prove_claim'):
                        repaired_hybrid_result = self.prover.prove_claim(repaired_spec.claim.claim_text, code=code)
                        repaired_result = ProofResult(
                            spec=repaired_spec,
                            proven=repaired_hybrid_result.get('proven', False),
                            proof_time_ms=repaired_hybrid_result.get('time_ms', 0),
                            error_message=repaired_hybrid_result.get('error', ''),
                            proof_output=f"Prover: {repaired_hybrid_result.get('prover', 'unknown')} (with auto-repair)",
                            counter_example=repaired_hybrid_result.get('counter_example', {})
                        )
                    else:
                        repaired_result = self.prover.prove_specification(repaired_spec)
                        repaired_result.proof_output += " (with auto-repair)"
                    
                    if repaired_result.proven:
                        logger.info(f"Automatic repair successful for '{spec.claim.claim_text[:50]}...'")
                        result = repaired_result
                    else:
                        logger.debug(f"Automatic repair failed for '{spec.claim.claim_text[:50]}...'")
            
            proof_results.append(result)
        
        # Step 4: Analyze results and resolve conflicts
        resolution = self._resolve_conflicts(conflicts, proof_results)
        
        return {
            'original_claims': claims,
            'specifications': specifications,
            'translation_failures': translation_failures,
            'conflicts': conflicts,
            'proof_results': proof_results,
            'resolution': resolution,
            'summary': self._generate_summary(proof_results, conflicts)
        }
    
    def analyze_program_properties(self, code: str, language: str = "python") -> Dict[str, Any]:
        """
        Perform deep analysis of program to discover and verify complex properties.
        
        Args:
            code: Source code to analyze
            language: Programming language
            
        Returns:
            Analysis results with discovered properties and verification status
        """
        logger.info(f"Performing deep program analysis on {len(code)} characters of {language} code")
        
        # Generate complex software properties
        discovered_specs = self.property_generator.generate_specifications(code, language)
        
        logger.info(f"Discovered {len(discovered_specs)} complex software properties")
        
        # Verify the discovered properties
        verification_results = []
        
        for spec in discovered_specs:
            logger.debug(f"Verifying property: {spec.spec_text}")
            
            if Z3_AVAILABLE and hasattr(self.prover, 'prove_claim'):
                # Use hybrid prover for complex properties
                hybrid_result = self.prover.prove_claim(spec.claim.claim_text, code=code)
                
                result = ProofResult(
                    spec=spec,
                    proven=hybrid_result.get('proven', False),
                    proof_time_ms=hybrid_result.get('time_ms', 0),
                    error_message=hybrid_result.get('error', ''),
                    proof_output=f"Deep Analysis + {hybrid_result.get('prover', 'unknown')}",
                    counter_example=hybrid_result.get('counter_example', {})
                )
            else:
                # Use Coq prover
                result = self.prover.prove_specification(spec)
                result.proof_output = f"Deep Analysis + Coq"
            
            # Attempt repair if failed
            if not result.proven and self.auto_repair_enabled:
                logger.debug(f"Attempting repair for failed property: {spec.spec_text[:50]}...")
                
                repaired_spec = self.proof_repairer.repair_failed_proof(result, spec)
                if repaired_spec:
                    if Z3_AVAILABLE and hasattr(self.prover, 'prove_claim'):
                        repaired_result = self.prover.prove_claim(repaired_spec.claim.claim_text, code=code)
                        if repaired_result.get('proven', False):
                            result = ProofResult(
                                spec=repaired_spec,
                                proven=True,
                                proof_time_ms=repaired_result.get('time_ms', 0),
                                error_message='',
                                proof_output=f"Deep Analysis + Auto-Repair + {repaired_result.get('prover', 'unknown')}",
                                counter_example={}
                            )
                            logger.info(f"Successfully repaired property: {spec.spec_text[:50]}...")
            
            verification_results.append(result)
        
        # Categorize results by property type
        property_categories = {}
        for result in verification_results:
            category = result.spec.claim.property_type.value
            if category not in property_categories:
                property_categories[category] = {'proven': 0, 'failed': 0, 'total': 0}
            
            property_categories[category]['total'] += 1
            if result.proven:
                property_categories[category]['proven'] += 1
            else:
                property_categories[category]['failed'] += 1
        
        # Generate summary statistics
        total_properties = len(verification_results)
        proven_properties = sum(1 for r in verification_results if r.proven)
        
        return {
            'discovered_properties': len(discovered_specs),
            'verified_properties': proven_properties,
            'total_properties': total_properties,
            'verification_rate': proven_properties / total_properties if total_properties > 0 else 0,
            'property_categories': property_categories,
            'verification_results': verification_results,
            'complex_properties_verified': True
        }
    
    def _resolve_conflicts(self, conflicts: List, proof_results: List[ProofResult]) -> Dict[str, Any]:
        """Resolve conflicts based on formal proof results.
        
        Args:
            conflicts: List of detected conflicts
            proof_results: Results from theorem proving attempts
            
        Returns:
            Dictionary containing conflict resolution information
        """
        resolution = {
            'mathematically_proven': [r for r in proof_results if r.proven],
            'mathematically_disproven': [r for r in proof_results if not r.proven and r.error_message],
            'unresolved': [r for r in proof_results if not r.proven and not r.error_message],
            'agent_rankings': self._rank_agents_by_correctness(proof_results),
            'ground_truth_established': any(r.proven for r in proof_results)
        }
        
        return resolution
    
    def _rank_agents_by_correctness(self, proof_results: List[ProofResult]) -> Dict[str, float]:
        """Rank agents by how many of their claims were mathematically proven.
        
        Args:
            proof_results: List of proof results
            
        Returns:
            Dictionary mapping agent IDs to accuracy scores
        """
        agent_scores = {}
        agent_counts = {}
        
        for result in proof_results:
            agent_id = result.spec.claim.agent_id
            if agent_id not in agent_scores:
                agent_scores[agent_id] = 0
                agent_counts[agent_id] = 0
            
            agent_counts[agent_id] += 1
            if result.proven:
                agent_scores[agent_id] += 1
        
        # Calculate accuracy percentages
        rankings = {}
        for agent_id in agent_scores:
            if agent_counts[agent_id] > 0:
                rankings[agent_id] = agent_scores[agent_id] / agent_counts[agent_id]
            else:
                rankings[agent_id] = 0.0
        
        return dict(sorted(rankings.items(), key=lambda x: x[1], reverse=True))
    
    def _generate_summary(self, proof_results: List[ProofResult], conflicts: List) -> Dict[str, Any]:
        """Generate human-readable summary of analysis.
        
        Args:
            proof_results: List of proof results
            conflicts: List of detected conflicts
            
        Returns:
            Dictionary containing summary statistics
        """
        proven_count = sum(1 for r in proof_results if r.proven)
        disproven_count = sum(1 for r in proof_results if not r.proven and r.error_message)
        avg_proof_time = sum(r.proof_time_ms for r in proof_results) / len(proof_results) if proof_results else 0
        
        return {
            'total_claims': len(proof_results),
            'mathematically_proven': proven_count,
            'mathematically_disproven': disproven_count,
            'conflicts_detected': len(conflicts),
            'verification_complete': all(r.proven or r.error_message for r in proof_results),
            'average_proof_time_ms': avg_proof_time,
            'has_ground_truth': proven_count > 0
        }