from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseTransition(ABC):
    """
    Abstract base class for all transition types in the state machine.
    """
    def __init__(
        self,
        source_state: str,
        target_state: str,
        priority: int = 0,
        description: str = ""
    ):
        """
        Initialize a base transition.
        
        Args:
            source_state: The state from which the transition starts
            target_state: The state to which the transition leads
            priority: Priority level for this transition (higher values have precedence)
            description: Human-readable description of the transition
        """
        self.source_state = source_state
        self.target_state = target_state
        self.priority = priority
        self.description = description
        
    @abstractmethod
    def evaluate(self, context: Dict[str, Any]) -> float:
        """
        Evaluate if this transition should be triggered based on the current context.
        
        Args:
            context: Current context dict containing state information
            
        Returns:
            A confidence score between 0.0 and 1.0 where:
              0.0 = transition should not be taken
              1.0 = transition should definitely be taken
        """
        pass
    
    def apply_pre_conditions(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply pre-conditions before transitioning to the target state.
        
        Args:
            context: Current context dict
            
        Returns:
            Modified context dict
        """
        return context
    
    def apply_post_conditions(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply post-conditions after transitioning to the target state.
        
        Args:
            context: Current context dict
            
        Returns:
            Modified context dict
        """
        return context
        
    def __str__(self) -> str:
        return f"{self.__class__.__name__}: {self.source_state} -> {self.target_state} (priority: {self.priority})" 