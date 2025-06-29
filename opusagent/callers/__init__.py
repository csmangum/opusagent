"""
Caller configurations for different personality types.

This module provides various caller configurations for testing different
customer service scenarios with different types of callers.
"""

from .caller_factory import (
    CallerType,
    get_caller_config,
    register_caller_functions,
    get_available_caller_types,
    get_caller_description,
)

# Individual caller configurations
from .typical_caller import get_typical_caller_config, register_typical_caller_functions
from .frustrated_caller import get_frustrated_caller_config, register_frustrated_caller_functions
from .elderly_caller import get_elderly_caller_config, register_elderly_caller_functions
from .hurried_caller import get_hurried_caller_config, register_hurried_caller_functions

__all__ = [
    # Factory functions
    "CallerType",
    "get_caller_config",
    "register_caller_functions",
    "get_available_caller_types",
    "get_caller_description",
    
    # Individual caller configurations
    "get_typical_caller_config",
    "register_typical_caller_functions",
    "get_frustrated_caller_config",
    "register_frustrated_caller_functions",
    "get_elderly_caller_config",
    "register_elderly_caller_functions",
    "get_hurried_caller_config",
    "register_hurried_caller_functions",
]
