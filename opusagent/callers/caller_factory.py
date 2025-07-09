from typing import Dict, Any, Optional
from opusagent.models.openai_api import SessionConfig

from .typical_caller import get_typical_caller_config, register_typical_caller_functions
from .frustrated_caller import get_frustrated_caller_config, register_frustrated_caller_functions
from .elderly_caller import get_elderly_caller_config, register_elderly_caller_functions
from .hurried_caller import get_hurried_caller_config, register_hurried_caller_functions


class CallerType:
    """Enumeration of available caller types."""
    TYPICAL = "typical"
    FRUSTRATED = "frustrated"
    ELDERLY = "elderly"
    HURRIED = "hurried"


# Configuration mapping
CALLER_CONFIGS = {
    CallerType.TYPICAL: get_typical_caller_config,
    CallerType.FRUSTRATED: get_frustrated_caller_config,
    CallerType.ELDERLY: get_elderly_caller_config,
    CallerType.HURRIED: get_hurried_caller_config,
}

# Function registration mapping
CALLER_FUNCTION_REGISTRARS = {
    CallerType.TYPICAL: register_typical_caller_functions,
    CallerType.FRUSTRATED: register_frustrated_caller_functions,
    CallerType.ELDERLY: register_elderly_caller_functions,
    CallerType.HURRIED: register_hurried_caller_functions,
}


def get_caller_config(caller_type: str) -> SessionConfig:
    """
    Get the session configuration for a specific caller type.
    
    Args:
        caller_type: The type of caller (typical, frustrated, elderly, hurried)
        
    Returns:
        SessionConfig for the specified caller type
        
    Raises:
        ValueError: If caller_type is not recognized
    """
    if caller_type not in CALLER_CONFIGS:
        available_types = ", ".join(CALLER_CONFIGS.keys())
        raise ValueError(f"Unknown caller type '{caller_type}'. Available types: {available_types}")
    
    return CALLER_CONFIGS[caller_type]()


def register_caller_functions(caller_type: str, function_handler) -> None:
    """
    Register functions for a specific caller type.
    
    Args:
        caller_type: The type of caller (typical, frustrated, elderly, hurried)
        function_handler: The FunctionHandler instance to register functions with
        
    Raises:
        ValueError: If caller_type is not recognized
    """
    if caller_type not in CALLER_FUNCTION_REGISTRARS:
        available_types = ", ".join(CALLER_FUNCTION_REGISTRARS.keys())
        raise ValueError(f"Unknown caller type '{caller_type}'. Available types: {available_types}")
    
    CALLER_FUNCTION_REGISTRARS[caller_type](function_handler)


def get_available_caller_types() -> list[str]:
    """
    Get a list of all available caller types.
    
    Returns:
        List of available caller type names
    """
    return list(CALLER_CONFIGS.keys())


def get_caller_description(caller_type: str) -> str:
    """
    Get a description of what each caller type represents.
    
    Args:
        caller_type: The type of caller
        
    Returns:
        Description of the caller type
        
    Raises:
        ValueError: If caller_type is not recognized
    """
    descriptions = {
        CallerType.TYPICAL: "A cooperative, patient caller who provides clear information and is easy to work with",
        CallerType.FRUSTRATED: "An impatient, demanding caller who is easily frustrated and may interrupt frequently",
        CallerType.ELDERLY: "A patient, polite caller who may need more guidance and has lower tech comfort",
        CallerType.HURRIED: "A caller in a rush who wants quick service and may interrupt to speed things up",
    }
    
    if caller_type not in descriptions:
        available_types = ", ".join(descriptions.keys())
        raise ValueError(f"Unknown caller type '{caller_type}'. Available types: {available_types}")
    
    return descriptions[caller_type] 