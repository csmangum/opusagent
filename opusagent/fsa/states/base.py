import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel


class StateTransition(BaseModel):
    """Represents a transition from one state to another."""

    target_state: str
    condition: Optional[str] = None
    priority: int = 0

    def __str__(self) -> str:
        return f"Transition to {self.target_state}" + (
            f" when {self.condition}" if self.condition else ""
        )


class StateContext(BaseModel):
    """Context information maintained across state transitions."""

    user_id: Optional[str] = None
    session_id: str
    conversation_history: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}

    class Config:
        arbitrary_types_allowed = True


class FSAState:
    """Base class for all states in the Finite State Agent."""

    def __init__(
        self,
        name: str,
        description: str,
        allowed_transitions: List[StateTransition] = None,
    ):
        """
        Initialize a new state.

        Args:
            name: Unique identifier for the state
            description: Human-readable description of the state's purpose
            allowed_transitions: List of possible transitions from this state
        """
        self.name = name
        self.description = description
        self.allowed_transitions = allowed_transitions or []
        self.scratchpad = ""
        self.logger = logging.getLogger(f"opusagent.states.{name}")

    def clear_scratchpad(self) -> None:
        """Clear the scratchpad content."""
        self.scratchpad = ""

    def write_to_scratchpad(self, content: str) -> None:
        """Add content to the scratchpad."""
        self.scratchpad += content

    def get_scratchpad(self) -> str:
        """Get the current scratchpad content."""
        return self.scratchpad

    async def process(
        self, input_text: str, context: StateContext
    ) -> Tuple[str, Optional[str], Dict[str, Any]]:
        """
        Process input in the context of this state.

        Args:
            input_text: The text input from the user
            context: The current conversation context

        Returns:
            Tuple containing:
            - Response text to be sent to the user
            - Name of the next state (if transition should occur), or None to stay in current state
            - Updated context information
        """
        raise NotImplementedError("Subclasses must implement process()")

    def can_transition_to(self, state_name: str) -> bool:
        """Check if this state can transition to the specified state."""
        return any(t.target_state == state_name for t in self.allowed_transitions)

    def get_valid_transitions(self, context: StateContext) -> List[StateTransition]:
        """Get all valid transitions based on current context."""
        # In a more advanced implementation, this would evaluate conditions
        return self.allowed_transitions

    def __str__(self) -> str:
        return f"State({self.name}): {self.description}"
