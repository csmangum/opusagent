from typing import Any, Dict, List, Optional, Tuple

from .base import BaseTransition
from .registry import TransitionRegistry


class TransitionEvaluator:
    """
    Evaluates multiple possible transitions and determines the best one
    to take based on confidence scores and priorities.
    """
    
    def __init__(self, registry: TransitionRegistry):
        """
        Initialize a transition evaluator.
        
        Args:
            registry: The transition registry to use
        """
        self.registry = registry
        
    def evaluate_transitions(
        self, current_state: str, context: Dict[str, Any]
    ) -> Optional[Tuple[BaseTransition, float]]:
        """
        Evaluate all possible transitions from the current state and
        determine the best one to take.
        
        Args:
            current_state: The current state of the system
            context: Current context dict containing state information
            
        Returns:
            Tuple of (best_transition, confidence) if a transition should be taken,
            None otherwise
        """
        candidate_transitions = self.registry.get_transitions_from_state(current_state)
        
        if not candidate_transitions:
            return None
            
        # Evaluate each transition and collect results
        evaluated_transitions = []
        for transition in candidate_transitions:
            confidence = transition.evaluate(context)
            if confidence > 0:
                evaluated_transitions.append((transition, confidence))
                
        if not evaluated_transitions:
            return None
            
        # Sort by priority (higher is better) and then by confidence (higher is better)
        evaluated_transitions.sort(
            key=lambda x: (x[0].priority, x[1]), 
            reverse=True
        )
        
        # Return the best transition
        return evaluated_transitions[0]
        
    def get_best_transition(
        self, current_state: str, context: Dict[str, Any]
    ) -> Optional[BaseTransition]:
        """
        Get the best transition to take from the current state.
        
        Args:
            current_state: The current state of the system
            context: Current context dict containing state information
            
        Returns:
            The best transition if one should be taken, None otherwise
        """
        result = self.evaluate_transitions(current_state, context)
        return result[0] if result else None
        
    def apply_transition(
        self, current_state: str, context: Dict[str, Any]
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Evaluate transitions, select the best one, and apply it if found.
        
        Args:
            current_state: The current state of the system
            context: Current context dict containing state information
            
        Returns:
            Tuple of (new_state, updated_context) if a transition was applied,
            (None, original_context) otherwise
        """
        result = self.evaluate_transitions(current_state, context)
        
        if not result:
            return None, context
            
        transition, confidence = result
        
        # Apply pre-conditions
        updated_context = transition.apply_pre_conditions(context.copy())
        
        # Add transition information to context
        updated_context['last_transition'] = {
            'source': transition.source_state,
            'target': transition.target_state,
            'confidence': confidence,
            'description': transition.description
        }
        
        # Apply post-conditions
        updated_context = transition.apply_post_conditions(updated_context)
        
        return transition.target_state, updated_context 