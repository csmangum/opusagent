"""
States module for Finite State Agents (FSA) implementation.

This module provides the core components for building and managing Finite State Agents, which enhance traditional finite state machines with embedded agent
reasoning capabilities to create structured, controllable, and dynamic conversational flows.

Key components:
- FSAState: Base class for defining states with embedded reasoning and processing logic
- StateContext: Container for maintaining context across state transitions
- StateTransition: Class representing transitions between states with conditions
- StateManager: Orchestrator that manages the state machine, transitions, and context

The states module forms the backbone of the FSA architecture, enabling predictable
conversation flows while maintaining the flexibility and intelligence of modern
language models.

Usage examples:
```python
# Define a custom state
from opusagent.fsa.states import FSAState, StateTransition, StateContext

class GreetingState(FSAState):
    def __init__(self):
        super().__init__(
            name="greeting",
            description="Initial greeting state that welcomes the user"
        )
    
    async def process(self, input_text, context):
        # Process user input in the greeting context
        response = f"Hello! How can I help you today?"
        
        # Determine possible transitions based on user input
        if "account" in input_text.lower():
            return response, [StateTransition(target="account_services")]
        
        return response, []

# Use the state manager to handle conversations
from opusagent.fsa.states import StateManager

async def conversation_handler():
    manager = StateManager()
    manager.add_state(GreetingState())
    # Add more states...
    
    context = StateContext()
    response, new_state = await manager.process("Hi there", context)
    # Continue conversation flow...
```
"""

from .base import FSAState, StateContext, StateTransition
from .manager import StateManager

__all__ = ['FSAState', 'StateContext', 'StateTransition', 'StateManager'] 