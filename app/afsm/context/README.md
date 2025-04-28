# Context Management for Agentic Finite State Machines

This module provides a comprehensive context management system for Agentic Finite State Machines, allowing for structured, controlled, and dynamic conversational context handling.

## Key Components

### ContextItem
The base unit of context with content and metadata.
- Stores actual information along with metadata
- Includes relevance scoring and expiration policies
- Maintains confidence levels and source information

### ContextCategory
Named collections of related context items with customizable retention policies.
- Groups related context items
- Applies category-specific policies for retention and relevance
- Handles automatic pruning of outdated or low-relevance items

### StateContext
Primary container for conversation context.
- Maintains categorized data structures
- Provides interfaces for adding and retrieving context
- Handles state transitions and context persistence

### ContextFilter
Determines what context should persist across transitions.
- Implements strategies for context relevance scoring
- Prevents context pollution through selective maintenance
- Provides state-specific context filtering

### ContextManager
Central orchestrator for context operations.
- Handles persistence, retrieval, and prioritization
- Provides interfaces for states to access and modify context
- Manages context during state transitions

## Common Use Patterns

### Managing Session Context

```python
# Initialize context manager
context_manager = ContextManager(storage_dir="./contexts")

# Create a new context for a user
context = context_manager.create_context(user_id="user123")
session_id = context.session_id

# Add various types of context
context.add_session_data("user_name", "John")
context.add_salient("User is a premium customer")
context.add_history("User requested account balance")

# Handle state transitions
context_manager.handle_state_transition(
    session_id, 
    from_state="greeting", 
    to_state="account_inquiry"
)

# Get context for a specific state
state_context = context_manager.get_context_for_state(
    session_id, 
    state_name="account_inquiry"
)

# End a session
context_manager.end_session(session_id)
```

### Context Persistence

```python
# Save context to persistent storage
context_manager.save_context(session_id)

# Load context from persistent storage
loaded_context = context_manager.load_context(session_id)
```

## Integration with AFSM States

State implementations can access context by receiving the `state_context` dictionary which contains:
- `session_id`: The current session identifier
- `user_id`: The user identifier
- `current_state`: The current state name
- `prev_state`: The previous state name
- `salient`: List of salient context items
- `history`: List of historical interactions
- `session_data`: Dictionary of session metadata
- `state_data`: Dictionary of state-specific data
- `relevant_items`: List of context items relevant to this state

## Examples

See the `examples` directory for complete examples demonstrating the context management system in action. 