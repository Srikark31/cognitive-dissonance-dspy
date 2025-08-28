"""Verifier modules for detecting and resolving cognitive dissonance."""

import random
import logging
import dspy

logger = logging.getLogger(__name__)


class ExtractClaim(dspy.Signature):
    """Extract a single, concise factual claim from text."""
    
    text: str = dspy.InputField(desc="text to analyze")
    claim: str = dspy.OutputField(desc="concise factual claim")
    confidence: str = dspy.OutputField(desc="confidence level: high, medium, or low")


class DetectDissonance(dspy.Signature):
    """Determine if two claims are contradictory."""
    
    claim1: str = dspy.InputField(desc="first claim")
    claim2: str = dspy.InputField(desc="second claim") 
    are_contradictory: str = dspy.OutputField(desc="'yes' if contradictory, 'no' if compatible")
    reason: str = dspy.OutputField(desc="explanation of the relationship")


class ReconcileClaims(dspy.Signature):
    """Generate a reconciled claim from potentially contradictory ones."""
    
    claim1: str = dspy.InputField(desc="first claim")
    claim2: str = dspy.InputField(desc="second claim")
    has_conflict: str = dspy.InputField(desc="whether claims conflict")
    reconciled_claim: str = dspy.OutputField(desc="single, consistent, reconciled claim")


class BeliefAgent(dspy.Module):
    """Agent that forms beliefs from text."""
    
    def __init__(self, use_cot: bool = False):
        """
        Initialize the belief agent.
        
        Args:
            use_cot: Whether to use Chain of Thought reasoning
        """
        super().__init__()
        self.use_cot = use_cot
        self.extract = (dspy.ChainOfThought if use_cot else dspy.Predict)(ExtractClaim)
        logger.debug(f"Initialized BeliefAgent with use_cot={use_cot}")
    
    def forward(self, text: str) -> dspy.Prediction:
        """
        Extract a belief/claim from text.
        
        Args:
            text: Input text to analyze
            
        Returns:
            Prediction with claim and confidence
        """
        logger.debug(f"Extracting claim from: {text[:100]}...")
        
        try:
            out = self.extract(text=text)
            
            # Normalize confidence
            confidence = (out.confidence or "medium").strip().lower()
            if confidence not in ["high", "medium", "low"]:
                confidence = "medium"
            
            out.confidence = confidence
            logger.debug(f"Extracted claim: {out.claim} (confidence: {confidence})")
            
            return out
        
        except Exception as e:
            logger.warning(f"Failed to extract claim: {e}")
            # Return a safe default
            prediction = dspy.Prediction()
            prediction.claim = text[:100] if len(text) > 100 else text
            prediction.confidence = "low"
            return prediction


class DissonanceDetector(dspy.Module):
    """Agent that detects cognitive dissonance between beliefs."""
    
    def __init__(self, use_cot: bool = False):
        """
        Initialize the dissonance detector.
        
        Args:
            use_cot: Whether to use Chain of Thought reasoning
        """
        super().__init__()
        self.use_cot = use_cot
        self.detect = (dspy.ChainOfThought if use_cot else dspy.Predict)(DetectDissonance)
        logger.debug(f"Initialized DissonanceDetector with use_cot={use_cot}")
    
    def forward(self, claim1: str, claim2: str) -> dspy.Prediction:
        """
        Detect if two claims are contradictory.
        
        Args:
            claim1: First claim
            claim2: Second claim
            
        Returns:
            Prediction with contradiction verdict and reason
        """
        logger.debug(f"Detecting dissonance between: '{claim1}' and '{claim2}'")
        
        try:
            out = self.detect(claim1=claim1, claim2=claim2)
            
            # Normalize verdict
            raw_verdict = (out.are_contradictory or "").strip().lower()
            
            if "yes" in raw_verdict and "no" not in raw_verdict:
                verdict = "yes"
            elif "no" in raw_verdict:
                verdict = "no"
            else:
                # Uncertain cases default to no
                verdict = "no"
                logger.debug(f"Uncertain verdict '{raw_verdict}', defaulting to 'no'")
            
            out.are_contradictory = verdict
            logger.debug(f"Dissonance detected: {verdict} - {out.reason}")
            
            return out
        
        except Exception as e:
            logger.warning(f"Failed to detect dissonance: {e}")
            prediction = dspy.Prediction()
            prediction.are_contradictory = "no"
            prediction.reason = "Unable to determine relationship"
            return prediction


class ReconciliationAgent(dspy.Module):
    """Agent that reconciles conflicting beliefs."""
    
    def __init__(self, use_cot: bool = False):
        """
        Initialize the reconciliation agent.
        
        Args:
            use_cot: Whether to use Chain of Thought reasoning
        """
        super().__init__()
        self.use_cot = use_cot
        self.reconcile = (dspy.ChainOfThought if use_cot else dspy.Predict)(ReconcileClaims)
        logger.debug(f"Initialized ReconciliationAgent with use_cot={use_cot}")
    
    def forward(self, claim1: str, claim2: str, has_conflict: str = "yes") -> dspy.Prediction:
        """
        Reconcile two potentially conflicting claims.
        
        Args:
            claim1: First claim
            claim2: Second claim
            has_conflict: Whether the claims conflict
            
        Returns:
            Prediction with reconciled claim
        """
        logger.debug(f"Reconciling claims: '{claim1}' and '{claim2}' (conflict: {has_conflict})")
        
        try:
            out = self.reconcile(
                claim1=claim1, 
                claim2=claim2,
                has_conflict=has_conflict
            )
            
            # Ensure we have a reconciled claim
            if not out.reconciled_claim:
                # Fallback to simple combination
                if has_conflict == "yes":
                    out.reconciled_claim = claim1  # Default to first claim
                else:
                    out.reconciled_claim = f"{claim1}. {claim2}"
            
            logger.debug(f"Reconciled to: {out.reconciled_claim}")
            return out
        
        except Exception as e:
            logger.warning(f"Failed to reconcile claims: {e}")
            prediction = dspy.Prediction()
            # Simple fallback reconciliation
            if has_conflict == "yes":
                prediction.reconciled_claim = claim1
            else:
                prediction.reconciled_claim = f"{claim1}. {claim2}"
            return prediction


class CognitiveDissonanceResolver(dspy.Module):
    """Complete system for detecting and resolving cognitive dissonance."""
    
    def __init__(self, use_cot: bool = False):
        """
        Initialize the complete resolver system.
        
        Args:
            use_cot: Whether to use Chain of Thought reasoning
        """
        super().__init__()
        self.belief_agent = BeliefAgent(use_cot=use_cot)
        self.dissonance_detector = DissonanceDetector(use_cot=use_cot)
        self.reconciliation_agent = ReconciliationAgent(use_cot=use_cot)
        logger.debug(f"Initialized CognitiveDissonanceResolver with use_cot={use_cot}")
    
    def forward(self, text1: str, text2: str) -> dspy.Prediction:
        """
        Process two texts to detect and resolve cognitive dissonance.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Prediction with claims, dissonance detection, and reconciliation
        """
        logger.debug("Processing texts for cognitive dissonance")
        
        # Extract claims from both texts
        belief1 = self.belief_agent(text=text1)
        belief2 = self.belief_agent(text=text2)
        
        # Detect dissonance
        dissonance = self.dissonance_detector(
            claim1=belief1.claim,
            claim2=belief2.claim
        )
        
        # Reconcile if needed
        reconciliation = self.reconciliation_agent(
            claim1=belief1.claim,
            claim2=belief2.claim,
            has_conflict=dissonance.are_contradictory
        )
        
        # Create combined prediction
        result = dspy.Prediction()
        result.claim1 = belief1.claim
        result.claim2 = belief2.claim
        result.confidence1 = belief1.confidence
        result.confidence2 = belief2.confidence
        result.has_dissonance = dissonance.are_contradictory
        result.dissonance_reason = dissonance.reason
        result.reconciled = reconciliation.reconciled_claim
        
        logger.debug(f"Resolution complete: dissonance={result.has_dissonance}")
        
        return result