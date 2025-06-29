"""
Example usage of different caller configurations.

This script demonstrates how to use the various caller types
for testing different customer service scenarios.
"""

from opusagent.callers import (
    CallerType,
    get_caller_config,
    register_caller_functions,
    get_available_caller_types,
    get_caller_description,
)
from opusagent.function_handler import FunctionHandler


def demonstrate_caller_types():
    """Demonstrate how to use different caller types."""
    
    print("Available caller types:")
    for caller_type in get_available_caller_types():
        description = get_caller_description(caller_type)
        print(f"  - {caller_type}: {description}")
    
    print("\n" + "="*50)
    
    # Example: Get configuration for a typical caller
    print("Example: Getting typical caller configuration")
    typical_config = get_caller_config(CallerType.TYPICAL)
    print(f"Model: {typical_config.model}")
    print(f"Voice: {typical_config.voice}")
    print(f"Temperature: {typical_config.temperature}")
    
    print("\n" + "="*50)
    
    # Example: Get configuration for a frustrated caller
    print("Example: Getting frustrated caller configuration")
    frustrated_config = get_caller_config(CallerType.FRUSTRATED)
    print(f"Model: {frustrated_config.model}")
    print(f"Voice: {frustrated_config.voice}")
    print(f"Temperature: {frustrated_config.temperature}")
    
    print("\n" + "="*50)
    
    # Example: Register functions for a caller type
    print("Example: Registering functions for elderly caller")
    function_handler = FunctionHandler(realtime_websocket=None)
    register_caller_functions(CallerType.ELDERLY, function_handler)
    print("Functions registered successfully!")
    
    print("\n" + "="*50)
    
    # Example: Compare different caller personalities
    print("Example: Comparing caller personalities")
    caller_types = [CallerType.TYPICAL, CallerType.FRUSTRATED, CallerType.ELDERLY, CallerType.HURRIED]
    
    for caller_type in caller_types:
        config = get_caller_config(caller_type)
        print(f"\n{caller_type.upper()} CALLER:")
        print(f"  - Temperature: {config.temperature}")
        print(f"  - Voice: {config.voice}")
        print(f"  - Description: {get_caller_description(caller_type)}")


def create_caller_session(caller_type: str):
    """
    Create a session configuration for a specific caller type.
    
    Args:
        caller_type: The type of caller to create
        
    Returns:
        SessionConfig for the caller
    """
    try:
        config = get_caller_config(caller_type)
        print(f"Created {caller_type} caller configuration successfully!")
        return config
    except ValueError as e:
        print(f"Error: {e}")
        return None


if __name__ == "__main__":
    print("Caller Configuration Examples")
    print("=" * 50)
    
    demonstrate_caller_types()
    
    print("\n" + "="*50)
    print("Interactive Example:")
    
    # Interactive example
    caller_type = input("Enter caller type (typical/frustrated/elderly/hurried): ").lower()
    config = create_caller_session(caller_type)
    
    if config:
        print(f"\nConfiguration created for {caller_type} caller:")
        print(f"  - Instructions length: {len(config.instructions) if config.instructions else 0} characters")
        print(f"  - Tools count: {len(config.tools) if config.tools else 0}")
        print(f"  - Modalities: {config.modalities}") 