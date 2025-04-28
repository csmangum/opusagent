from typing import Any, Callable, Dict, List, Optional, Union

from .base import BaseTransition


class Condition:
    """A condition that can be evaluated against a context."""
    
    def __init__(self, predicate: Callable[[Dict[str, Any]], bool], description: str = ""):
        """
        Initialize a condition.
        
        Args:
            predicate: A function that takes a context dict and returns a boolean
            description: Human-readable description of the condition
        """
        self.predicate = predicate
        self.description = description
        
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """
        Evaluate this condition against the given context.
        
        Args:
            context: Current context dict
            
        Returns:
            True if the condition is met, False otherwise
        """
        return self.predicate(context)


class RuleBasedTransition(BaseTransition):
    """
    Implements deterministic transitions based on explicit conditions.
    """
    
    def __init__(
        self,
        source_state: str,
        target_state: str,
        conditions: List[Condition],
        require_all: bool = True,
        priority: int = 0,
        description: str = ""
    ):
        """
        Initialize a rule-based transition.
        
        Args:
            source_state: The state from which the transition starts
            target_state: The state to which the transition leads
            conditions: List of conditions that must be satisfied for this transition
            require_all: If True, all conditions must be met; if False, any condition is sufficient
            priority: Priority level for this transition (higher values have precedence)
            description: Human-readable description of the transition
        """
        super().__init__(source_state, target_state, priority, description)
        self.conditions = conditions
        self.require_all = require_all
        
    def evaluate(self, context: Dict[str, Any]) -> float:
        """
        Evaluate if this transition should be triggered based on the current context.
        Returns 1.0 if the conditions are met, 0.0 otherwise.
        
        Args:
            context: Current context dict containing state information
            
        Returns:
            1.0 if the conditions are met, 0.0 otherwise
        """
        if not self.conditions:
            return 0.0
            
        results = [condition.evaluate(context) for condition in self.conditions]
        
        if self.require_all:
            return 1.0 if all(results) else 0.0
        else:
            # If any condition is true, return 1.0
            return 1.0 if any(results) else 0.0
            
    def add_condition(self, condition: Condition) -> None:
        """
        Add a condition to this transition.
        
        Args:
            condition: The condition to add
        """
        self.conditions.append(condition) 