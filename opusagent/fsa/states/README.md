# States Module Documentation

## Overview

The States module implements an Finite State Agent (FSA) architecture for building structured, controllable, and dynamic conversational flows. This architecture enhances traditional finite state machines with embedded agent reasoning capabilities.

## Core Components

### FSAState

Base class for all states in the FSA system. Each state represents a discrete phase in a conversation flow with its own processing logic.

```python
from opusagent.fsa.states import FSAState

class CustomState(FSAState):
    def __init__(self):
        super().__init__(
            name="custom_state",
            description="Handles a specific conversation context",
            allowed_transitions=[...]
        )
    
    async def process(self, input_text, context):
        # Process input and determine next state
        return response, next_state_name, updated_context
```

**Key Methods:**
- `process(input_text, context)`: Main processing method that handles user input
- `write_to_scratchpad(content)`: Adds content to state's reasoning scratchpad
- `get_scratchpad()`: Retrieves the current scratchpad content
- `can_transition_to(state_name)`: Checks if transition to specified state is allowed

### StateTransition

Represents a possible transition from one state to another, with optional conditions.

```python
from opusagent.fsa.states import StateTransition

transition = StateTransition(
    target_state="next_state",
    condition="Condition for transition",
    priority=1
)
```

### StateContext

Container for maintaining context across state transitions, including conversation history and metadata.

```python
from opusagent.fsa.states import StateContext

context = StateContext(
    session_id="unique_session_id",
    user_id="optional_user_id",
    metadata={"custom": "data"}
)
```

### StateManager

Orchestrates the state machine, managing states, transitions, and context.

```python
from opusagent.fsa.states import StateManager

manager = StateManager(initial_state="greeting")
manager.register_state(GreetingState())
manager.register_state(AuthenticationState())

context = manager.initialize_context(session_id="session123")
response = await manager.process_input("Hello!")
```

**Key Methods:**
- `register_state(state)`: Add a state to the manager
- `initialize_context(session_id, user_id, metadata)`: Initialize a new conversation context
- `transition_to(state_name)`: Explicitly transition to a new state
- `process_input(input_text)`: Process user input through the current state

## Example Usage

```python
# Define states
class GreetingState(FSAState):
    def __init__(self):
        transitions = [
            StateTransition(target_state="auth", condition="Auth needed"),
            StateTransition(target_state="general", condition="General query")
        ]
        super().__init__(
            name="greeting",
            description="Initial greeting state",
            allowed_transitions=transitions
        )
    
    async def process(self, input_text, context):
        # Determine if authentication is needed
        if "account" in input_text.lower():
            return "Please authenticate first.", "auth", context
        else:
            return "How can I help you?", "general", context

# Set up the state manager
async def setup_conversation():
    manager = StateManager(initial_state="greeting")
    manager.register_state(GreetingState())
    # Register other states...
    
    context = manager.initialize_context(session_id="unique_id")
    
    # Start the conversation
    response = await manager.process_input("Hello, I need help with my account")
    # Will transition to authentication state
```

## Best Practices

1. **State Design**: Keep states focused on a single conversation phase or purpose
2. **Transition Logic**: Clearly define conditions for state transitions
3. **Context Management**: Store relevant information in context to maintain conversation flow
4. **Scratchpad Usage**: Use the scratchpad for agent reasoning and decision tracking
5. **Error Handling**: Implement fallback states for handling unexpected inputs

## Use Cases

- Multi-step forms and data collection
- Authentication flows
- Complex decision trees
- Conversational interfaces with structured progression
- Task-oriented dialogues with clear state transitions 