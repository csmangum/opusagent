from typing import Any, Dict, List, Optional, Set, Union

from .base import BaseTransition


class IntentBasedTransition(BaseTransition):
    """
    Implements transitions driven by NLU-detected user intents.
    Transitions are triggered when a matching intent is detected with
    sufficient confidence.
    """
    
    def __init__(
        self,
        source_state: str,
        target_state: str,
        intents: Union[str, List[str], Set[str]],
        min_confidence: float = 0.7,
        priority: int = 0,
        description: str = ""
    ):
        """
        Initialize an intent-based transition.
        
        Args:
            source_state: The state from which the transition starts
            target_state: The state to which the transition leads
            intents: Single intent or list/set of intents that can trigger this transition
            min_confidence: Minimum confidence score required to trigger the transition
            priority: Priority level for this transition (higher values have precedence)
            description: Human-readable description of the transition
        """
        super().__init__(source_state, target_state, priority, description)
        
        # Convert single intent to a set
        if isinstance(intents, str):
            self.intents = {intents}
        elif isinstance(intents, list):
            self.intents = set(intents)
        else:
            self.intents = intents
            
        self.min_confidence = min_confidence
        
    def evaluate(self, context: Dict[str, Any]) -> float:
        """
        Evaluate if this transition should be triggered based on the current context.
        
        Args:
            context: Current context dict containing state information
                    Expected to contain 'intent' and 'intent_confidence' keys
            
        Returns:
            The intent confidence score if it meets the minimum threshold and the intent matches,
            0.0 otherwise
        """
        # Check if the required intent information is in the context
        if 'intent' not in context or 'intent_confidence' not in context:
            return 0.0
            
        intent = context['intent']
        confidence = context['intent_confidence']
        
        # Check if the intent matches and confidence is sufficient
        if intent in self.intents and confidence >= self.min_confidence:
            return confidence
        
        return 0.0
        
    def add_intent(self, intent: str) -> None:
        """
        Add an intent to this transition.
        
        Args:
            intent: The intent to add
        """
        self.intents.add(intent) 