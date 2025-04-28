from typing import Any, Callable, Dict, List, Optional

from .base import BaseTransition


class ReasoningBasedTransition(BaseTransition):
    """
    Implements transitions that use LLM reasoning to determine when to trigger.
    Useful for complex decision-making that requires deep understanding of context.
    """
    
    def __init__(
        self,
        source_state: str,
        target_state: str,
        reasoning_function: Callable[[Dict[str, Any]], float],
        priority: int = 0,
        description: str = ""
    ):
        """
        Initialize a reasoning-based transition.
        
        Args:
            source_state: The state from which the transition starts
            target_state: The state to which the transition leads
            reasoning_function: Function that implements the reasoning logic
                                Takes a context dict and returns a confidence score
            priority: Priority level for this transition (higher values have precedence)
            description: Human-readable description of the transition
        """
        super().__init__(source_state, target_state, priority, description)
        self.reasoning_function = reasoning_function
        
    def evaluate(self, context: Dict[str, Any]) -> float:
        """
        Evaluate if this transition should be triggered based on the current context.
        Uses the provided reasoning function to calculate a confidence score.
        
        Args:
            context: Current context dict containing state information
                    Should include 'scratchpad' if used in reasoning
            
        Returns:
            A confidence score between 0.0 and 1.0
        """
        try:
            confidence = self.reasoning_function(context)
            # Ensure the confidence is between 0 and 1
            return max(0.0, min(1.0, confidence))
        except Exception as e:
            # If reasoning fails, don't trigger the transition
            logger.error(f"Error in reasoning function: {e}", exc_info=True)
            return 0.0
            
    def apply_post_conditions(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply post-conditions after transitioning.
        For reasoning-based transitions, this might include updating the scratchpad
        to explain the reasoning behind the transition.
        
        Args:
            context: Current context dict
            
        Returns:
            Modified context dict
        """
        # Update scratchpad with reasoning, if it exists
        if 'scratchpad' in context:
            reasoning = f"Transitioned from {self.source_state} to {self.target_state} "
            reasoning += f"based on reasoning: {self.description}"
            
            if isinstance(context['scratchpad'], str):
                context['scratchpad'] += f"\n{reasoning}"
            elif isinstance(context['scratchpad'], list):
                context['scratchpad'].append(reasoning)
                
        return context 