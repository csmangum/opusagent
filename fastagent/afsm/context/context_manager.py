"""
Central orchestrator for context operations in Agentic Finite State Machines.
"""
import os
import json
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import uuid

from fastagent.afsm.context.context_item import ContextItem, ContextCategory, ExpirationPolicy
from fastagent.afsm.context.state_context import StateContext
from fastagent.afsm.context.context_filter import ContextFilter


class ContextManager:
    """
    Central orchestrator for context operations.
    
    Handles persistence, retrieval, prioritization and provides
    interfaces for states to access and modify context.
    
    Attributes:
        contexts: Dictionary of active contexts by session_id
        context_filter: Filter used for context transitions
        storage_dir: Directory for persistent storage (if used)
    """
    
    def __init__(
        self,
        storage_dir: Optional[str] = None,
        default_min_relevance: float = 0.3
    ):
        self.contexts: Dict[str, StateContext] = {}
        self.context_filter = ContextFilter(default_min_relevance=default_min_relevance)
        self.storage_dir = storage_dir
        
        # Create storage directory if it doesn't exist
        if storage_dir and not os.path.exists(storage_dir):
            os.makedirs(storage_dir)
    
    def create_context(self, user_id: Optional[str] = None) -> StateContext:
        """
        Create a new context for a session.
        
        Args:
            user_id: Optional user identifier
            
        Returns:
            The newly created StateContext
        """
        session_id = str(uuid.uuid4())
        context = StateContext(session_id=session_id, user_id=user_id)
        self.contexts[session_id] = context
        return context
    
    def get_context(self, session_id: str) -> Optional[StateContext]:
        """Get a context by session ID."""
        return self.contexts.get(session_id)
    
    def get_or_create_context(self, session_id: str, user_id: Optional[str] = None) -> StateContext:
        """Get an existing context or create a new one if it doesn't exist."""
        context = self.get_context(session_id)
        if context is None:
            context = StateContext(session_id=session_id, user_id=user_id)
            self.contexts[session_id] = context
        return context
    
    def handle_state_transition(
        self,
        session_id: str,
        from_state: str,
        to_state: str
    ) -> Optional[StateContext]:
        """
        Handle context updates during a state transition.
        
        Args:
            session_id: The session identifier
            from_state: The state being exited
            to_state: The state being entered
            
        Returns:
            The updated StateContext or None if not found
        """
        context = self.get_context(session_id)
        if context is None:
            return None
            
        # Apply the context filter
        self.context_filter.apply_to_context(context, from_state, to_state)
        
        # Save the context
        if self.storage_dir:
            self.save_context(session_id)
            
        return context
    
    def add_context_item(
        self,
        session_id: str,
        category: str,
        content: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[ContextItem]:
        """
        Add a context item to a specific category.
        
        Args:
            session_id: The session identifier
            category: The category to add to
            content: The content to add
            metadata: Optional metadata for the item
            
        Returns:
            The added ContextItem or None if context not found
        """
        context = self.get_context(session_id)
        if context is None:
            return None
            
        item = ContextItem(
            content=content,
            source=category,
            metadata=metadata or {}
        )
        
        return context.add_to_category(category, item)
    
    def get_context_for_state(
        self,
        session_id: str,
        state_name: str,
        min_relevance: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Get a formatted context dictionary for a specific state.
        
        This is used to provide relevant context to a state for processing.
        
        Args:
            session_id: The session identifier
            state_name: The target state name
            min_relevance: Minimum relevance score for inclusion
            
        Returns:
            Dictionary of context data organized for state consumption
        """
        context = self.get_context(session_id)
        if context is None:
            return {}
            
        # Use the context filter to get relevant items
        relevant_items = self.context_filter.filter_items(
            context,
            state_name,
            min_relevance
        )
        
        # Structure the context for state consumption
        result = {
            "session_id": session_id,
            "user_id": context.user_id,
            "current_state": context.current_state,
            "prev_state": context.prev_state,
            "salient": [],
            "history": [],
            "session_data": {},
            "state_data": {}
        }
        
        # Add items from standard categories
        for category_name in ["salient", "history"]:
            category = context.get_category(category_name)
            items = [item.content for item in category.items]
            result[category_name] = items
            
        # Add session data
        session_category = context.get_category("session")
        for item in session_category.items:
            if isinstance(item.content, dict) and "key" in item.content and "value" in item.content:
                result["session_data"][item.content["key"]] = item.content["value"]
                
        # Add state-specific data
        state_category_name = f"state_{state_name}"
        if state_category_name in context.categories:
            state_category = context.categories[state_category_name]
            for item in state_category.items:
                if isinstance(item.content, dict) and "key" in item.content and "value" in item.content:
                    result["state_data"][item.content["key"]] = item.content["value"]
                    
        # Add all relevant items
        result["relevant_items"] = [
            {
                "content": item.content,
                "source": item.source,
                "relevance": item.relevance_score
            }
            for item in relevant_items
        ]
        
        return result
    
    def save_context(self, session_id: str) -> bool:
        """
        Save a context to persistent storage.
        
        Args:
            session_id: The session identifier
            
        Returns:
            True if successful, False otherwise
        """
        if not self.storage_dir:
            return False
            
        context = self.get_context(session_id)
        if context is None:
            return False
            
        # Create the filename
        filename = os.path.join(self.storage_dir, f"{session_id}.json")
        
        try:
            # Convert context to JSON and save
            with open(filename, 'w') as f:
                json.dump(context.to_dict(), f, indent=2)
            return True
        except Exception:
            # Log the error in a real implementation
            return False
    
    def load_context(self, session_id: str) -> Optional[StateContext]:
        """
        Load a context from persistent storage.
        
        Args:
            session_id: The session identifier
            
        Returns:
            The loaded StateContext or None if not found
        """
        if not self.storage_dir:
            return None
            
        # Create the filename
        filename = os.path.join(self.storage_dir, f"{session_id}.json")
        
        if not os.path.exists(filename):
            return None
            
        try:
            # Load the JSON file
            with open(filename, 'r') as f:
                data = json.load(f)
                
            # Create a context from the data
            context = StateContext.from_dict(data)
            
            # Store in the active contexts
            self.contexts[session_id] = context
            
            return context
        except Exception:
            # Log the error in a real implementation
            return None
    
    def end_session(self, session_id: str) -> bool:
        """
        End a session and clean up resources.
        
        Args:
            session_id: The session identifier
            
        Returns:
            True if successful, False otherwise
        """
        context = self.get_context(session_id)
        if context is None:
            return False
            
        # Save the context before removing it
        if self.storage_dir:
            self.save_context(session_id)
            
        # Remove from active contexts
        del self.contexts[session_id]
        
        return True 