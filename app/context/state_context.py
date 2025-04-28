"""
Primary container for conversation context in Agentic Finite State Machines.
"""
from typing import Any, Dict, List, Optional, Set, Union
import json
import time

from app.context.context_item import ContextItem, ContextCategory, ExpirationPolicy


class StateContext:
    """
    Primary container for conversation context.
    
    Maintains categorized data structures:
      - Salient Context: High-priority, immediately relevant information
      - Historical Memory: Time-ordered interaction history
      - Session Metadata: User information, conversation parameters
      - State-Specific Data: Context relevant only to particular states
    
    Attributes:
        categories: Dictionary of named context categories
        current_state: Name of the current state in the AFSM
        session_id: Unique identifier for this conversation session
        user_id: Identifier for the user in this conversation
    """
    
    def __init__(self, session_id: str, user_id: Optional[str] = None):
        self.session_id = session_id
        self.user_id = user_id
        self.current_state: Optional[str] = None
        self.prev_state: Optional[str] = None
        self.categories: Dict[str, ContextCategory] = {}
        
        # Initialize standard categories
        self._init_standard_categories()
        
    def _init_standard_categories(self) -> None:
        """Initialize the standard context categories."""
        self.categories["salient"] = ContextCategory(
            name="salient",
            description="High-priority, immediately relevant information",
            priority_weight=0.9
        )
        
        self.categories["history"] = ContextCategory(
            name="history",
            description="Time-ordered interaction history",
            priority_weight=0.6,
            max_items=50  # Limit history to last 50 interactions
        )
        
        self.categories["session"] = ContextCategory(
            name="session",
            description="User information and conversation parameters",
            priority_weight=0.8,
            default_expiration=ExpirationPolicy.AFTER_SESSION
        )
        
        self.categories["state_data"] = ContextCategory(
            name="state_data",
            description="Context relevant only to particular states",
            priority_weight=0.7,
            default_expiration=ExpirationPolicy.AFTER_TRANSITION
        )
    
    def add_category(self, name: str, category: Optional[ContextCategory] = None, **kwargs) -> ContextCategory:
        """
        Add a new context category.
        
        Args:
            name: Unique identifier for this category
            category: Existing ContextCategory object (optional)
            **kwargs: Arguments to pass to ContextCategory constructor if category is None
            
        Returns:
            The created or provided ContextCategory
        """
        if name in self.categories:
            raise ValueError(f"Category '{name}' already exists")
            
        if category is None:
            category = ContextCategory(name=name, **kwargs)
            
        self.categories[name] = category
        return category
    
    def get_category(self, name: str) -> ContextCategory:
        """Get a context category by name, creating it if it doesn't exist."""
        if name not in self.categories:
            self.categories[name] = ContextCategory(name=name)
            
        return self.categories[name]
    
    def add_to_category(self, category_name: str, item: Union[ContextItem, Any]) -> ContextItem:
        """
        Add an item to a specific category.
        
        Args:
            category_name: Name of the category to add to
            item: Item to add (either a ContextItem or raw content)
            
        Returns:
            The added ContextItem
        """
        category = self.get_category(category_name)
        return category.add_item(item)
    
    def add_salient(self, item: Union[ContextItem, Any]) -> ContextItem:
        """Add an item to the salient context category."""
        return self.add_to_category("salient", item)
    
    def add_history(self, item: Union[ContextItem, Any]) -> ContextItem:
        """Add an item to the history category."""
        return self.add_to_category("history", item)
    
    def add_session_data(self, key: str, value: Any) -> ContextItem:
        """Add a key-value pair to the session metadata category."""
        return self.add_to_category("session", {"key": key, "value": value})
    
    def add_state_data(self, key: str, value: Any, state_name: Optional[str] = None) -> ContextItem:
        """
        Add data specific to a state.
        
        Args:
            key: The data key
            value: The data value
            state_name: The state this data is relevant to (defaults to current_state)
            
        Returns:
            The added ContextItem
        """
        state = state_name or self.current_state or "global"
        
        # Create a state-specific category if it doesn't exist
        category_name = f"state_{state}"
        if category_name not in self.categories:
            self.add_category(
                category_name,
                description=f"Data specific to the '{state}' state",
                default_expiration=ExpirationPolicy.AFTER_TRANSITION
            )
            
        return self.add_to_category(category_name, {"key": key, "value": value})
    
    def get_all_items(self, min_relevance: float = 0.0) -> List[ContextItem]:
        """Get all context items with relevance >= min_relevance."""
        items = []
        for category in self.categories.values():
            items.extend(category.get_items(min_relevance))
            
        # Sort by relevance (highest first)
        return sorted(items, key=lambda item: item.relevance_score, reverse=True)
    
    def get_all_by_category(self) -> Dict[str, List[ContextItem]]:
        """Get all context items organized by category."""
        return {name: category.items.copy() for name, category in self.categories.items()}
    
    def on_state_transition(self, from_state: str, to_state: str) -> None:
        """
        Handle context updates when transitioning between states.
        
        This method:
        1. Updates current_state and prev_state
        2. Expires items with AFTER_TRANSITION policy
        3. Prunes expired items from all categories
        
        Args:
            from_state: Name of the state being exited
            to_state: Name of the state being entered
        """
        self.prev_state = from_state
        self.current_state = to_state
        
        # Mark items with AFTER_TRANSITION policy as expired
        for category in self.categories.values():
            for item in category.items:
                if item.expiration_policy == ExpirationPolicy.AFTER_TRANSITION:
                    # Set expiration_time to now
                    item.expiration_time = time.time()
            
            # Prune expired items
            category.prune_expired()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the context to a dictionary representation."""
        result = {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "current_state": self.current_state,
            "prev_state": self.prev_state,
            "categories": {}
        }
        
        for name, category in self.categories.items():
            result["categories"][name] = {
                "description": category.description,
                "priority_weight": category.priority_weight,
                "items": [
                    {
                        "content": item.content,
                        "source": item.source,
                        "timestamp": item.timestamp,
                        "confidence": item.confidence,
                        "relevance_score": item.relevance_score,
                        "metadata": item.metadata
                    }
                    for item in category.items
                ]
            }
            
        return result
    
    def to_json(self, **kwargs) -> str:
        """Convert the context to a JSON string."""
        return json.dumps(self.to_dict(), **kwargs)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StateContext':
        """Create a StateContext from a dictionary representation."""
        context = cls(
            session_id=data.get("session_id", "unknown"),
            user_id=data.get("user_id")
        )
        
        context.current_state = data.get("current_state")
        context.prev_state = data.get("prev_state")
        
        # Restore categories and items
        for name, cat_data in data.get("categories", {}).items():
            # Skip standard categories as they're already initialized
            if name not in context.categories:
                context.add_category(
                    name=name,
                    description=cat_data.get("description", ""),
                    priority_weight=cat_data.get("priority_weight", 0.5)
                )
                
            category = context.categories[name]
            
            # Add items to the category
            for item_data in cat_data.get("items", []):
                item = ContextItem(
                    content=item_data.get("content"),
                    source=item_data.get("source", "unknown"),
                    timestamp=item_data.get("timestamp", time.time()),
                    confidence=item_data.get("confidence", 1.0),
                    relevance_score=item_data.get("relevance_score", 0.5),
                    metadata=item_data.get("metadata", {})
                )
                
                category.add_item(item)
                
        return context
    
    @classmethod
    def from_json(cls, json_str: str) -> 'StateContext':
        """Create a StateContext from a JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data) 