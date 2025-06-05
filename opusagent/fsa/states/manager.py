from typing import Dict, Optional, List, Any, Type
import logging
from .base import FSAState, StateContext, StateTransition

logger = logging.getLogger("opusagent.states.manager")

class StateManager:
    """
    Manages the states in an Finite State Agent and handles transitions
    between them.
    """
    
    def __init__(self, initial_state: str):
        """
        Initialize the state manager.
        
        Args:
            initial_state: The name of the initial state
        """
        self.states: Dict[str, FSAState] = {}
        self.current_state_name = initial_state
        self.context = None
    
    def register_state(self, state: FSAState) -> None:
        """
        Register a state with the manager.
        
        Args:
            state: The state to register
        """
        if state.name in self.states:
            logger.warning(f"State '{state.name}' already registered, overwriting")
        
        self.states[state.name] = state
        logger.debug(f"Registered state: {state.name}")
    
    def register_states(self, states: List[FSAState]) -> None:
        """
        Register multiple states with the manager.
        
        Args:
            states: List of states to register
        """
        for state in states:
            self.register_state(state)
    
    def get_state(self, state_name: str) -> Optional[FSAState]:
        """
        Get a state by name.
        
        Args:
            state_name: The name of the state to retrieve
            
        Returns:
            The state if found, None otherwise
        """
        return self.states.get(state_name)
    
    def get_current_state(self) -> Optional[FSAState]:
        """
        Get the current state.
        
        Returns:
            The current state if set, None otherwise
        """
        return self.get_state(self.current_state_name)
    
    def initialize_context(self, session_id: str, user_id: Optional[str] = None, 
                          metadata: Dict[str, Any] = None) -> StateContext:
        """
        Initialize a new context.
        
        Args:
            session_id: Unique identifier for the session
            user_id: Optional identifier for the user
            metadata: Optional additional metadata
            
        Returns:
            The initialized context
        """
        self.context = StateContext(
            session_id=session_id,
            user_id=user_id,
            metadata=metadata or {}
        )
        return self.context
    
    def transition_to(self, state_name: str) -> bool:
        """
        Transition to a new state.
        
        Args:
            state_name: The name of the state to transition to
            
        Returns:
            True if transition was successful, False otherwise
        """
        current_state = self.get_current_state()
        if not current_state:
            logger.error(f"Cannot transition: current state '{self.current_state_name}' not found")
            return False
        
        target_state = self.get_state(state_name)
        if not target_state:
            logger.error(f"Cannot transition: target state '{state_name}' not found")
            return False
        
        if not current_state.can_transition_to(state_name):
            logger.warning(
                f"Invalid transition from '{current_state.name}' to '{state_name}'"
            )
            return False
        
        # Log the transition
        logger.info(f"Transitioning from '{current_state.name}' to '{state_name}'")
        
        # Update the current state
        self.current_state_name = state_name
        
        # Clear the scratchpad for the new state
        target_state.clear_scratchpad()
        
        return True
    
    async def process_input(self, input_text: str) -> str:
        """
        Process input through the current state.
        
        Args:
            input_text: The text input from the user
            
        Returns:
            The response from the current state
        """
        if not self.context:
            raise ValueError("Context not initialized. Call initialize_context() first")
        
        current_state = self.get_current_state()
        if not current_state:
            raise ValueError(f"Current state '{self.current_state_name}' not found")
        
        # Process the input through the current state
        response, next_state_name, updated_context = await current_state.process(
            input_text, self.context
        )
        
        # Update the context with any changes
        for key, value in updated_context.items():
            setattr(self.context, key, value)
        
        # Transition to the next state if specified
        if next_state_name and next_state_name != current_state.name:
            success = self.transition_to(next_state_name)
            if not success:
                logger.warning(
                    f"Failed to transition to '{next_state_name}', staying in '{current_state.name}'"
                )
        
        return response 