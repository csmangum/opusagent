# Agentic Finite State Machine (AFSM)

The AFSM module implements an advanced state machine architecture designed specifically for building structured, controllable, and dynamic conversational agents. It enhances traditional finite state machines with embedded agent reasoning capabilities, context management, and transition logic.

## Core Components

### States

States represent discrete phases in a conversation flow, each with its own processing logic:

- **Base State**: Abstract foundation for all states
- **State Manager**: Orchestrates state transitions and context flow
- **State Context**: Maintains and transfers relevant information between states

[Learn more about States](./states/README.md)

### Transitions

Transitions define when and how to move between states:

- **Rule-Based**: Deterministic transitions based on explicit conditions
- **Intent-Based**: Transitions triggered by user intent detection
- **Reasoning-Based**: AI-driven transitions using contextual reasoning
- **Hybrid**: Combines multiple transition strategies

[Learn more about Transitions](./transitions/README.md)

### Context Management

Sophisticated context handling system for maintaining conversation state:

- **Context Items**: Base units of information with metadata
- **Context Categories**: Named collections with retention policies
- **Context Filtering**: Intelligent selection of relevant context
- **Persistence**: Mechanisms for saving and loading context

[Learn more about Context](./context/README.md)

### Scratchpad

Structured system for agent reasoning and thought tracking:

- **Reasoning Sections**: Specialized containers for different types of thoughts
- **Content Management**: Timestamped entries with relationships
- **Integration**: Seamless connection with states for reasoning transfer
- **Persistence**: Optional storage of reasoning processes

[Learn more about Scratchpad](./scratchpad/README.md)

## Key Features

- **Structured Conversations**: Design clear conversational flows with defined states
- **Dynamic Routing**: Intelligent state transitions based on context and input
- **Context Preservation**: Maintain relevant information across the conversation
- **Transparent Reasoning**: Track and transfer agent thought processes
- **Modular Design**: Easily extend with custom states and transition logic

## Example Usage

```python
from fastagent.afsm.states import AFSMState, StateManager
from fastagent.afsm.transitions import RuleBasedTransition
from fastagent.afsm.context import ContextManager
from fastagent.afsm.scratchpad.integration import ScratchpadStateMixin

# Define a state with reasoning capabilities
class ProductInfoState(AFSMState, ScratchpadStateMixin):
    def __init__(self):
        transitions = [
            RuleBasedTransition(
                target_state="pricing_state",
                condition=lambda ctx: "price" in ctx.current_input.lower()
            )
        ]
        super().__init__(
            name="product_info",
            description="Provides information about products",
            allowed_transitions=transitions
        )
    
    async def process(self, input_text, context):
        # Record reasoning in scratchpad
        self.write_to_scratchpad("Analyzing product inquiry...")
        self.write_fact(f"User asked: {input_text}")
        
        # Process the request and update context
        response = "Our product helps you build conversational agents with finite state machines."
        
        # Determine if we should transition based on the input
        if "price" in input_text.lower():
            self.write_conclusion("User is interested in pricing")
            return response, "pricing_state", context
        
        return response, self.name, context

# Set up the state manager with context
manager = StateManager(initial_state="greeting")
context_manager = ContextManager()
scratchpad_manager = ScratchpadManager()

# Initialize a conversation
session_id = "user123"
context = context_manager.create_context(session_id)
```

## Integration

AFSM is designed to work with modern LLM-based agents, providing structure and control while maintaining the flexibility needed for natural conversations.

## Best Practices

1. **State Design**: Keep states focused on specific conversation phases
2. **Context Management**: Store only relevant information in context
3. **Transition Logic**: Define clear conditions for state transitions
4. **Scratchpad Usage**: Use structured reasoning for complex decisions
5. **Testing**: Validate conversation flows with comprehensive test cases 