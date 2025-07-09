# Caller Configurations

This module provides different caller personality types for testing various customer service scenarios. Each caller type has unique characteristics that simulate real-world customer interactions.

## Available Caller Types

### 1. Typical Caller (`typical`)
- **Description**: A cooperative, patient caller who provides clear information and is easy to work with
- **Characteristics**:
  - Cooperative and patient
  - Provides information willingly
  - Polite and respectful
  - Clear communicator
  - Patience level: 8/10
  - Tech comfort: 7/10

### 2. Frustrated Caller (`frustrated`)
- **Description**: An impatient, demanding caller who is easily frustrated and may interrupt frequently
- **Characteristics**:
  - Impatient and easily frustrated
  - Skeptical of automated systems
  - Demanding and interrupts frequently
  - Complains about wait times
  - Patience level: 3/10
  - Tech comfort: 4/10

### 3. Elderly Caller (`elderly`)
- **Description**: A patient, polite caller who may need more guidance and has lower tech comfort
- **Characteristics**:
  - Patient and polite
  - Appreciates clear explanations
  - May need things repeated
  - Concerned about security
  - Prefers human interaction
  - Patience level: 9/10
  - Tech comfort: 2/10

### 4. Hurried Caller (`hurried`)
- **Description**: A caller in a rush who wants quick service and may interrupt to speed things up
- **Characteristics**:
  - In a hurry and wants quick service
  - Efficient communicator
  - Interrupts to speed things up
  - Focused on getting to the point
  - Patience level: 4/10
  - Tech comfort: 8/10

## Usage

### Basic Usage

```python
from opusagent.callers import (
    CallerType,
    get_caller_config,
    register_caller_functions,
    get_available_caller_types,
    get_caller_description,
)

# Get a specific caller configuration
config = get_caller_config(CallerType.TYPICAL)

# Register functions for a caller type
function_handler = FunctionHandler(realtime_websocket=None)
register_caller_functions(CallerType.FRUSTRATED, function_handler)

# Get all available caller types
available_types = get_available_caller_types()
print(available_types)  # ['typical', 'frustrated', 'elderly', 'hurried']

# Get description of a caller type
description = get_caller_description(CallerType.ELDERLY)
print(description)  # "A patient, polite caller who may need more guidance..."
```

### Using Individual Caller Configurations

```python
from opusagent.callers import (
    get_typical_caller_config,
    get_frustrated_caller_config,
    get_elderly_caller_config,
    get_hurried_caller_config,
)

# Get specific caller configurations
typical_config = get_typical_caller_config()
frustrated_config = get_frustrated_caller_config()
elderly_config = get_elderly_caller_config()
hurried_config = get_hurried_caller_config()
```

### Example: Testing Different Scenarios

```python
def test_customer_service_with_different_callers():
    """Test how your customer service agent handles different caller types."""
    
    caller_types = [
        CallerType.TYPICAL,
        CallerType.FRUSTRATED,
        CallerType.ELDERLY,
        CallerType.HURRIED,
    ]
    
    for caller_type in caller_types:
        print(f"\nTesting with {caller_type} caller...")
        
        # Get the caller configuration
        config = get_caller_config(caller_type)
        
        # Use this configuration to create a caller session
        # Your customer service agent will interact with this caller
        print(f"Caller temperature: {config.temperature}")
        print(f"Caller voice: {config.voice}")
        print(f"Description: {get_caller_description(caller_type)}")
```

## Configuration Details

Each caller type has the following configuration parameters:

- **Model**: `gpt-4o-realtime-preview-2025-06-03`
- **Voice**: `alloy` (distinct from customer service agent voice)
- **Temperature**: Varies by caller type (0.6-0.9)
- **Tools**: Hang up functionality
- **Modalities**: Text and audio

### Temperature Settings

- **Typical**: 0.7 (balanced responses)
- **Frustrated**: 0.9 (more varied, emotional responses)
- **Elderly**: 0.6 (more consistent, patient responses)
- **Hurried**: 0.8 (efficient, varied responses)

## Scenario: Card Replacement

All caller types are configured for the card replacement scenario where the caller has lost their gold card and needs it replaced. Each caller type approaches this scenario differently:

- **Typical**: "Hi, I lost my gold card and need to get it replaced"
- **Frustrated**: "Finally! I've been waiting forever. I lost my gold card and I need it replaced right now"
- **Elderly**: "Hello, I'm calling because I seem to have lost my gold card and I need to get it replaced"
- **Hurried**: "Hi, I lost my gold card and need it replaced quickly. I'm in a hurry"

## Running the Example

To see all caller types in action, run the example script:

```bash
python -m opusagent.callers.example_usage
```

This will demonstrate how to use each caller type and show their different characteristics. 