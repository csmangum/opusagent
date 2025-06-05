"""
Basic data structures for context management.
"""
import time
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum


class ExpirationPolicy(Enum):
    """Enumeration of possible expiration policies for context items."""
    NEVER = "never"
    AFTER_TRANSITION = "after_transition"
    AFTER_SESSION = "after_session"
    AFTER_TIME = "after_time"  # Requires expiration_time to be set


@dataclass
class ContextItem:
    """
    Base unit of context with content and metadata.
    
    Attributes:
        content: The actual information stored
        source: Where this context originated from
        timestamp: When this context was created
        confidence: How confident we are in this context (0.0-1.0)
        relevance_score: Dynamic priority value (higher = more important)
        expiration_policy: When/if this context should be discarded
        expiration_time: Specific time for expiration (if policy is AFTER_TIME)
        metadata: Additional metadata about this context item
    """
    content: Any
    source: str = "unknown"
    timestamp: float = field(default_factory=time.time)
    confidence: float = 1.0
    relevance_score: float = 0.5
    expiration_policy: ExpirationPolicy = ExpirationPolicy.NEVER
    expiration_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self, current_time: Optional[float] = None) -> bool:
        """Check if this context item is expired based on its policy."""
        if self.expiration_policy == ExpirationPolicy.NEVER:
            return False
            
        if self.expiration_policy == ExpirationPolicy.AFTER_TIME:
            if self.expiration_time is None:
                return False
            
            current = current_time or time.time()
            return current > self.expiration_time
            
        if self.expiration_policy == ExpirationPolicy.AFTER_TRANSITION:
            # If expiration_time is set, this item was marked for expiration during transition
            return self.expiration_time is not None
            
        # Other policies (AFTER_SESSION) are handled externally
        return False
    
    def update_relevance(self, new_score: float) -> None:
        """Update the relevance score of this context item."""
        self.relevance_score = new_score


class ContextCategory:
    """
    Named collection of related context items with customizable retention policies.
    
    Attributes:
        name: Unique identifier for this category
        description: Human-readable description of this category
        priority_weight: Default importance of items in this category (0.0-1.0)
        items: Collection of context items in this category
        max_items: Maximum number of items to keep (oldest are removed first)
        default_expiration: Default expiration policy for new items
    """
    def __init__(
        self, 
        name: str, 
        description: str = "",
        priority_weight: float = 0.5,
        max_items: Optional[int] = None,
        default_expiration: ExpirationPolicy = ExpirationPolicy.NEVER
    ):
        self.name = name
        self.description = description
        self.priority_weight = priority_weight
        self.items: List[ContextItem] = []
        self.max_items = max_items
        self.default_expiration = default_expiration
    
    def add_item(self, item: Union[ContextItem, Any]) -> ContextItem:
        """
        Add a new item to this category.
        
        If the item is not a ContextItem, it will be wrapped in one with default metadata.
        
        Args:
            item: The item to add (either a ContextItem or raw content)
            
        Returns:
            The added ContextItem
        """
        # If it's raw content, wrap it in a ContextItem
        if not isinstance(item, ContextItem):
            item = ContextItem(
                content=item,
                source=self.name,
                expiration_policy=self.default_expiration,
                relevance_score=self.priority_weight
            )
        
        self.items.append(item)
        
        # Enforce max_items limit if specified
        if self.max_items and len(self.items) > self.max_items:
            # Remove oldest item (could also remove lowest relevance)
            self.items.pop(0)
            
        return item
    
    def get_items(self, min_relevance: float = 0.0) -> List[ContextItem]:
        """Get all items with relevance >= min_relevance."""
        return [item for item in self.items if item.relevance_score >= min_relevance]
    
    def clear(self) -> None:
        """Remove all items from this category."""
        self.items.clear()
    
    def prune_expired(self) -> int:
        """
        Remove all expired items from this category.
        
        Returns:
            Number of items removed
        """
        current_time = time.time()
        initial_count = len(self.items)
        
        self.items = [item for item in self.items if not item.is_expired(current_time)]
        
        return initial_count - len(self.items) 