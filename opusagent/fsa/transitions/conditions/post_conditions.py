from typing import Any, Callable, Dict, Optional


class PostCondition:
    """
    A condition that is applied after a transition occurs.
    Post-conditions can modify the context after the transition is applied.
    """
    
    def __init__(
        self, 
        condition_func: Callable[[Dict[str, Any]], Dict[str, Any]],
        description: str = ""
    ):
        """
        Initialize a post-condition.
        
        Args:
            condition_func: Function that applies the post-condition logic
                           Takes a context dict and returns a modified context dict
            description: Human-readable description of the post-condition
        """
        self.condition_func = condition_func
        self.description = description
        
    def apply(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply this post-condition to the context.
        
        Args:
            context: Current context dict
            
        Returns:
            Modified context dict
        """
        return self.condition_func(context)


# Common post-conditions
def clear_variable(variable_name: str) -> PostCondition:
    """
    Create a post-condition that clears a variable from the context.
    
    Args:
        variable_name: Name of the variable to clear
        
    Returns:
        PostCondition that clears the variable
    """
    def _clear_variable(context: Dict[str, Any]) -> Dict[str, Any]:
        if variable_name in context:
            del context[variable_name]
        return context
        
    return PostCondition(
        _clear_variable,
        f"Clear {variable_name} from context"
    )
    
    
def log_transition(log_key: str = 'transition_history') -> PostCondition:
    """
    Create a post-condition that logs the transition to the context.
    
    Args:
        log_key: Key in the context to use for logging
        
    Returns:
        PostCondition that logs the transition
    """
    def _log_transition(context: Dict[str, Any]) -> Dict[str, Any]:
        if 'last_transition' in context:
            # Initialize log if it doesn't exist
            if log_key not in context:
                context[log_key] = []
                
            # Add transition to log
            if isinstance(context[log_key], list):
                context[log_key].append(context['last_transition'])
                
        return context
        
    return PostCondition(
        _log_transition,
        f"Log transition to {log_key}"
    ) 