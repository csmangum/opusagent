"""
ContextFilter for determining what context should persist across state transitions.
"""
from typing import Any, Dict, List, Optional, Set
from app.context.context_item import ContextItem
from app.context.state_context import StateContext


class ContextFilter:
    """
    Determines what context should persist across transitions.
    
    Implements strategies for context relevance scoring and
    prevents context pollution through selective maintenance.
    
    Attributes:
        default_min_relevance: Default minimum relevance score for inclusion
        excluded_categories: Categories to exclude from filtering
        state_relevance_map: Maps states to relevance modifiers
    """
    
    def __init__(
        self,
        default_min_relevance: float = 0.3,
        excluded_categories: Optional[Set[str]] = None
    ):
        self.default_min_relevance = default_min_relevance
        self.excluded_categories = excluded_categories or {"session"}
        self.state_relevance_map: Dict[str, Dict[str, float]] = {}
    
    def set_state_relevance(self, state_name: str, category_name: str, modifier: float) -> None:
        """
        Set a relevance modifier for a category in a specific state.
        
        Args:
            state_name: The state name
            category_name: The category name
            modifier: The relevance modifier (added to base relevance)
        """
        if state_name not in self.state_relevance_map:
            self.state_relevance_map[state_name] = {}
            
        self.state_relevance_map[state_name][category_name] = modifier
    
    def get_relevance_modifier(self, state_name: str, category_name: str) -> float:
        """Get the relevance modifier for a category in a specific state."""
        state_map = self.state_relevance_map.get(state_name, {})
        return state_map.get(category_name, 0.0)
    
    def filter_items(
        self,
        context: StateContext,
        target_state: str,
        min_relevance: Optional[float] = None
    ) -> List[ContextItem]:
        """
        Filter context items based on relevance to the target state.
        
        Args:
            context: The current state context
            target_state: The state being transitioned to
            min_relevance: Minimum relevance score for inclusion
            
        Returns:
            List of relevant context items
        """
        if min_relevance is None:
            min_relevance = self.default_min_relevance
            
        result = []
        
        for category_name, category in context.categories.items():
            # Skip excluded categories (they're preserved automatically)
            if category_name in self.excluded_categories:
                continue
                
            # Get state-specific relevance modifier
            modifier = self.get_relevance_modifier(target_state, category_name)
            
            for item in category.items:
                # Apply modifier to item's base relevance
                effective_relevance = item.relevance_score + modifier
                
                # Include if it meets minimum relevance
                if effective_relevance >= min_relevance:
                    result.append(item)
                    
        return result
    
    def apply_to_context(
        self,
        context: StateContext,
        from_state: str,
        to_state: str,
        min_relevance: Optional[float] = None
    ) -> None:
        """
        Apply the filter to a context during state transition.
        
        This method:
        1. Scores items based on relevance to the target state
        2. Updates relevance scores for all items
        3. Calls context.on_state_transition() to handle expiration
        
        Args:
            context: The state context to filter
            from_state: The state being exited
            to_state: The state being entered
            min_relevance: Minimum relevance to keep items
        """
        # First, update relevance scores for all items
        self._update_relevance_scores(context, to_state)
        
        # Then perform the transition, which will handle expiration
        context.on_state_transition(from_state, to_state)
    
    def _update_relevance_scores(self, context: StateContext, target_state: str) -> None:
        """
        Update relevance scores for all items based on target state.
        
        Args:
            context: The state context
            target_state: The state being transitioned to
        """
        for category_name, category in context.categories.items():
            # Skip excluded categories
            if category_name in self.excluded_categories:
                continue
                
            # Get state-specific relevance modifier
            modifier = self.get_relevance_modifier(target_state, category_name)
            
            # Apply decay factor to reduce relevance of older items
            for item in category.items:
                # Simple relevance decay - could be more sophisticated
                # Items lose about 10% of their relevance on transition
                new_score = (item.relevance_score * 0.9) + modifier
                
                # Ensure relevance stays in [0, 1] range
                new_score = max(0.0, min(1.0, new_score))
                
                item.update_relevance(new_score) 