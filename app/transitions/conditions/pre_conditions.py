from typing import Any, Callable, Dict, Optional


class PreCondition:
    """
    A condition that is applied before a transition occurs.
    Pre-conditions can modify the context before the transition is applied.
    """
    
    def __init__(
        self, 
        condition_func: Callable[[Dict[str, Any]], Dict[str, Any]],
        description: str = ""
    ):
        """
        Initialize a pre-condition.
        
        Args:
            condition_func: Function that applies the pre-condition logic
                           Takes a context dict and returns a modified context dict
            description: Human-readable description of the pre-condition
        """
        self.condition_func = condition_func
        self.description = description
        
    def apply(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply this pre-condition to the context.
        
        Args:
            context: Current context dict
            
        Returns:
            Modified context dict
        """
        return self.condition_func(context)


# Common pre-conditions
def set_variable(variable_name: str, value: Any) -> PreCondition:
    """
    Create a pre-condition that sets a variable in the context.
    
    Args:
        variable_name: Name of the variable to set
        value: Value to set
        
    Returns:
        PreCondition that sets the variable
    """
    def _set_variable(context: Dict[str, Any]) -> Dict[str, Any]:
        context[variable_name] = value
        return context
        
    return PreCondition(
        _set_variable,
        f"Set {variable_name} to {value}"
    )
    
    
def merge_variables(source_name: str, target_name: str) -> PreCondition:
    """
    Create a pre-condition that merges one variable into another.
    
    Args:
        source_name: Name of the source variable
        target_name: Name of the target variable
        
    Returns:
        PreCondition that merges the variables
    """
    def _merge_variables(context: Dict[str, Any]) -> Dict[str, Any]:
        if source_name in context and target_name in context:
            # Handle different variable types
            if isinstance(context[source_name], dict) and isinstance(context[target_name], dict):
                context[target_name].update(context[source_name])
            elif isinstance(context[source_name], list) and isinstance(context[target_name], list):
                context[target_name].extend(context[source_name])
            elif isinstance(context[source_name], str) and isinstance(context[target_name], str):
                context[target_name] += context[source_name]
            else:
                # Default to overwrite
                context[target_name] = context[source_name]
                
        return context
        
    return PreCondition(
        _merge_variables,
        f"Merge {source_name} into {target_name}"
    ) 