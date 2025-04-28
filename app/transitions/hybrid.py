from typing import Any, Dict, List, Optional, Tuple

from .base import BaseTransition


class HybridTransition(BaseTransition):
    """
    Implements transitions that combine multiple transition strategies.
    Allows for weighted decision-making across different transition types.
    """
    
    def __init__(
        self,
        source_state: str,
        target_state: str,
        transitions: List[Tuple[BaseTransition, float]],
        threshold: float = 0.5,
        priority: int = 0,
        description: str = ""
    ):
        """
        Initialize a hybrid transition.
        
        Args:
            source_state: The state from which the transition starts
            target_state: The state to which the transition leads
            transitions: List of (transition, weight) tuples where weight is between 0 and 1
                         and the sum of weights should equal 1
            threshold: Minimum weighted average confidence score required to trigger the transition
            priority: Priority level for this transition (higher values have precedence)
            description: Human-readable description of the transition
        """
        super().__init__(source_state, target_state, priority, description)
        self.transitions = transitions
        self.threshold = threshold
        
        # Validate weights
        total_weight = sum(weight for _, weight in transitions)
        if transitions and not 0.99 <= total_weight <= 1.01:  # Allow for small floating point errors
            raise ValueError(f"Sum of weights must equal 1, got {total_weight}")
            
    def evaluate(self, context: Dict[str, Any]) -> float:
        """
        Evaluate if this transition should be triggered based on the current context.
        Calculates a weighted average of confidences from all constituent transitions.
        
        Args:
            context: Current context dict containing state information
            
        Returns:
            Weighted average confidence score if it meets the threshold, 0.0 otherwise
        """
        if not self.transitions:
            return 0.0
            
        weighted_confidence = 0.0
        for transition, weight in self.transitions:
            # Ensure the transition evaluates for the same source state
            if transition.source_state != self.source_state:
                continue
                
            confidence = transition.evaluate(context)
            weighted_confidence += confidence * weight
            
        # Check if the weighted confidence meets the threshold
        if weighted_confidence >= self.threshold:
            return weighted_confidence
            
        return 0.0
        
    def apply_pre_conditions(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply pre-conditions from all constituent transitions.
        
        Args:
            context: Current context dict
            
        Returns:
            Modified context dict
        """
        updated_context = context.copy()
        for transition, _ in self.transitions:
            updated_context = transition.apply_pre_conditions(updated_context)
            
        return updated_context
        
    def apply_post_conditions(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply post-conditions from all constituent transitions.
        
        Args:
            context: Current context dict
            
        Returns:
            Modified context dict
        """
        updated_context = context.copy()
        for transition, _ in self.transitions:
            updated_context = transition.apply_post_conditions(updated_context)
            
        return updated_context 