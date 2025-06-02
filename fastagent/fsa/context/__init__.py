"""
Context management module for Finite State Agents.

This module provides a structured system for managing contextual information within the Finite State Agent (FSA) architecture. It enables states to maintain, filter, and access 
relevant contextual data throughout the agent's lifecycle and across state transitions.

Key components:
- ContextItem: Base unit of context with content and metadata including confidence, relevance, and expiration
- ContextCategory: Named collection of related context items with customizable retention policies
- StateContext: Primary container for conversation context with categorized data structures
- ContextManager: Central orchestrator for context persistence, retrieval, and prioritization
- ContextFilter: Determines what context should persist across transitions to prevent context pollution

The context module enhances the FSA architecture by providing explicit memory and information
persistence capabilities to states, allowing for more informed decision-making and preservation
of critical information across the agent's operational flow.

Usage examples:
```python
# Basic context management
from fastagent.fsa.context import ContextItem, ContextCategory, ContextManager
from fastagent.fsa.context.context_item import ExpirationPolicy

# Create context items
user_info = ContextItem(
    content="prefers email communication",
    source="user_preference", 
    confidence=0.9,
    relevance_score=0.8,
    expiration_policy=ExpirationPolicy.NEVER
)

# Create a context category
category = ContextCategory(
    name="user_preferences",
    description="User communication preferences",
    priority_weight=0.8,
    max_items=10,
    default_expiration=ExpirationPolicy.AFTER_SESSION
)

# Add items to category
category.add_item(user_info)

# Use the context manager
context_manager = ContextManager(storage_dir="./contexts")
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

# Filter context based on relevance
from fastagent.fsa.context import ContextFilter
context_filter = ContextFilter(default_min_relevance=0.3)
relevant_items = context_filter.filter_items(
    context,
    target_state="account_inquiry"
)
```
"""

from fastagent.fsa.context.context_item import ContextItem, ContextCategory
from fastagent.fsa.context.state_context import StateContext
from fastagent.fsa.context.context_manager import ContextManager
from fastagent.fsa.context.context_filter import ContextFilter

__all__ = [
    'ContextItem', 
    'ContextCategory',
    'StateContext',
    'ContextManager',
    'ContextFilter'
]
