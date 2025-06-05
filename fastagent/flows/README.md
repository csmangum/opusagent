# Flow System

This directory contains a modular flow system for organizing conversation flows, tools, function implementations, and prompts.

## Structure

```
flows/
├── __init__.py                 # Package initialization
├── README.md                   # This documentation
├── base_flow.py               # Abstract base class for all flows
├── flow_manager.py            # Flow registration and management
├── integration_example.py     # Integration examples
├── card_replacement/          # Card replacement flow
│   ├── __init__.py
│   ├── flow.py               # Main flow orchestration
│   ├── tools.py              # OpenAI tool definitions
│   ├── functions.py          # Function implementations
│   └── prompts.py            # Flow-specific prompts
└── loan_application/          # Loan application flow (placeholder)
    └── __init__.py
```

## Key Concepts

### BaseFlow
All flows inherit from `BaseFlow` and must implement:
- `get_tools()`: Return OpenAI tool definitions
- `get_functions()`: Return function implementations
- `get_prompts()`: Return prompt templates
- `get_system_instruction()`: Return system instruction text

### FlowManager
Manages multiple flows and provides:
- Flow registration/activation
- Tool and function aggregation
- System instruction composition
- Integration with function handlers

## Creating a New Flow

1. **Create the flow directory:**
   ```
   mkdir fastagent/flows/my_new_flow
   ```

2. **Create the required files:**
   - `__init__.py`: Package initialization
   - `prompts.py`: All prompts for the flow
   - `tools.py`: OpenAI tool definitions
   - `functions.py`: Function implementations
   - `flow.py`: Main flow class

3. **Implement the flow class:**
   ```python
   # flow.py
   from ..base_flow import BaseFlow
   from .tools import get_my_flow_tools
   from .functions import get_my_flow_functions
   from .prompts import SYSTEM_INSTRUCTION
   
   class MyNewFlow(BaseFlow):
       def __init__(self):
           super().__init__("my_new_flow")
       
       def get_tools(self):
           return get_my_flow_tools()
       
       def get_functions(self):
           return get_my_flow_functions()
       
       def get_prompts(self):
           return {"system": SYSTEM_INSTRUCTION}
       
       def get_system_instruction(self):
           return SYSTEM_INSTRUCTION
   ```

4. **Register with the flow manager:**
   ```python
   # In flow_manager.py or your initialization code
   manager.register_flow(MyNewFlow())
   manager.activate_flow("my_new_flow")
   ```

## Integration with Existing System

### Option 1: Modify TelephonyRealtimeBridge

```python
from fastagent.flows import create_default_flow_manager

class TelephonyRealtimeBridge:
    def __init__(self, telephony_websocket, realtime_websocket):
        # ... existing code ...
        
        # Replace existing function handler setup
        self.flow_manager = create_default_flow_manager()
        self.flow_manager.activate_flow("card_replacement")
        
        self.function_handler = FunctionHandler(realtime_websocket)
        self.flow_manager.register_with_function_handler(self.function_handler)
```

### Option 2: Modify initialize_session

```python
async def initialize_session(realtime_websocket):
    # Create flow manager
    flow_manager = create_default_flow_manager()
    flow_manager.activate_flow("card_replacement")
    
    # Get tools and instructions from flows
    tools = flow_manager.get_all_tools()
    instructions = flow_manager.get_combined_system_instruction()
    
    session_config = SessionConfig(
        # ... other config ...
        tools=tools,
        instructions=instructions,
    )
    
    # Send session update
    session_update = SessionUpdateEvent(type="session.update", session=session_config)
    await realtime_websocket.send(session_update.model_dump_json())
```

## Example: Card Replacement Flow

The card replacement flow demonstrates the complete pattern:

### Tools (`tools.py`)
```python
CALL_INTENT_TOOL = {
    "type": "function",
    "name": "call_intent",
    "description": "Get the user's intent.",
    "parameters": {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "enum": ["card_replacement", "account_inquiry", "other"],
            },
        },
        "required": ["intent"],
    },
}
```

### Functions (`functions.py`)
```python
def call_intent(arguments: Dict[str, Any]) -> Dict[str, Any]:
    intent = arguments.get("intent", "")
    if intent == "card_replacement":
        return {
            "status": "success",
            "intent": intent,
            "next_action": "ask_card_type",
            "available_cards": ["Gold card", "Silver card", "Basic card"],
        }
    # ... handle other intents
```

### Prompts (`prompts.py`)
```python
SYSTEM_INSTRUCTION = """
You are a customer service agent for Bank of Peril. 
When a customer contacts you, first greet them warmly, then listen to their request 
and call the call_intent function to identify their intent.

For card replacement specifically:
1. First identify which card needs replacement using member_account_confirmation
2. Collect the reason for replacement using replacement_reason
3. Confirm the delivery address using confirm_address
4. Start the replacement process using start_card_replacement
5. Complete the process using finish_card_replacement
6. Wrap up the call using wrap_up
"""
```

### Flow Class (`flow.py`)
```python
class CardReplacementFlow(BaseFlow):
    def __init__(self):
        super().__init__("card_replacement")
    
    def get_tools(self):
        return get_card_replacement_tools()
    
    def get_functions(self):
        return get_card_replacement_functions()
    
    def get_system_instruction(self):
        return SYSTEM_INSTRUCTION
```

## Benefits

1. **Modularity**: Each flow is self-contained with its own tools, functions, and prompts
2. **Reusability**: Flows can be easily activated/deactivated or mixed and matched
3. **Maintainability**: Changes to one flow don't affect others
4. **Testability**: Individual flows can be tested in isolation
5. **Scalability**: New flows can be added without modifying existing code

## Flow Lifecycle

1. **Registration**: Flow is registered with the FlowManager
2. **Activation**: Flow is activated for use in the session
3. **Integration**: Flow's tools and functions are registered with the FunctionHandler
4. **Execution**: Functions are called during conversation
5. **Deactivation**: Flow can be deactivated if needed

## Testing Flows

```python
# Test a single flow
flow = CardReplacementFlow()
tools = flow.get_tools()
functions = flow.get_functions()

# Validate flow configuration
validation = flow.validate_flow_configuration()
assert validation["valid"], f"Flow validation failed: {validation}"

# Test function execution
result = functions["call_intent"]({"intent": "card_replacement"})
assert result["status"] == "success"
```

## Migration Guide

To migrate from the current system to the flow system:

1. **Extract existing tools**: Move tool definitions from `telephony_realtime_bridge.py` to flow-specific `tools.py` files
2. **Extract functions**: Move function implementations from `function_handler.py` to flow-specific `functions.py` files
3. **Extract prompts**: Move prompts from `demo/rc_prompts.py` to flow-specific `prompts.py` files
4. **Create flow classes**: Implement flow classes that tie everything together
5. **Update initialization**: Modify session initialization to use flows
6. **Update bridge**: Modify the bridge to use the flow manager

This provides better organization while maintaining backward compatibility. 