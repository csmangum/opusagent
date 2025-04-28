from typing import Any, Dict, List, Optional, Set, Tuple, Union

from .base import BaseTransition


class TransitionRegistry:
    """
    Central registry for managing available transitions in the state machine.
    Provides methods for registration, retrieval, and validation of transitions.
    """

    def __init__(self):
        """Initialize an empty transition registry."""
        self._transitions: Dict[str, Dict[str, List[BaseTransition]]] = {}
        self._all_transitions: List[BaseTransition] = []

    def register(self, transition: BaseTransition) -> None:
        """
        Register a transition in the registry.

        Args:
            transition: The transition to register
        """
        # Initialize source state dict if it doesn't exist
        if transition.source_state not in self._transitions:
            self._transitions[transition.source_state] = {}

        # Initialize target state list if it doesn't exist
        if transition.target_state not in self._transitions[transition.source_state]:
            self._transitions[transition.source_state][transition.target_state] = []

        # Add the transition to the appropriate list
        self._transitions[transition.source_state][transition.target_state].append(
            transition
        )

        # Add to the list of all transitions
        self._all_transitions.append(transition)

    def register_many(self, transitions: List[BaseTransition]) -> None:
        """
        Register multiple transitions at once.

        Args:
            transitions: List of transitions to register
        """
        for transition in transitions:
            self.register(transition)

    def get_transitions_from_state(self, state: str) -> List[BaseTransition]:
        """
        Get all transitions from a given state.

        Args:
            state: The source state

        Returns:
            List of transitions starting from the given state
        """
        if state not in self._transitions:
            return []

        result = []
        for target_transitions in self._transitions[state].values():
            result.extend(target_transitions)

        return result

    def get_transitions_between_states(
        self, source_state: str, target_state: str
    ) -> List[BaseTransition]:
        """
        Get all transitions between two specific states.

        Args:
            source_state: The source state
            target_state: The target state

        Returns:
            List of transitions from source_state to target_state
        """
        if (
            source_state not in self._transitions
            or target_state not in self._transitions[source_state]
        ):
            return []

        return self._transitions[source_state][target_state]

    def get_all_transitions(self) -> List[BaseTransition]:
        """
        Get all registered transitions.

        Returns:
            List of all transitions
        """
        return self._all_transitions

    def get_all_states(self) -> Set[str]:
        """
        Get all states that have registered transitions.

        Returns:
            Set of all states (both source and target)
        """
        states = set(self._transitions.keys())

        # Add target states
        for source_dict in self._transitions.values():
            states.update(source_dict.keys())

        return states

    def validate(self) -> List[str]:
        """
        Validate the transition registry for common issues.

        Returns:
            List of validation error messages, empty if no errors
        """
        errors = []

        # Check for states with no outgoing transitions
        for state in self.get_all_states():
            if state not in self._transitions or not self._transitions[state]:
                errors.append(f"State '{state}' has no outgoing transitions")

        # Check for circular references with high priority
        # Track cycles we've already reported to avoid duplicates
        reported_cycles = set()

        for transition in self._all_transitions:
            reverse_transitions = self.get_transitions_between_states(
                transition.target_state, transition.source_state
            )
            for reverse in reverse_transitions:
                # Make sure we're not comparing transitions from different cycles
                if (
                    reverse.source_state == transition.target_state
                    and reverse.target_state == transition.source_state
                ):
                    # Create a cycle identifier (sort states to ensure uniqueness)
                    cycle_states = sorted(
                        [transition.source_state, transition.target_state]
                    )
                    cycle_id = f"{cycle_states[0]}-{cycle_states[1]}"

                    # Only report each cycle once
                    if cycle_id not in reported_cycles:
                        # Consider a cycle problematic if:
                        # 1. The priority difference is 2 or more, OR
                        # 2. Either transition has a high absolute priority (>= 6)
                        if (
                            reverse.priority - transition.priority >= 2
                            or reverse.priority >= 6
                            or transition.priority >= 6
                        ):
                            errors.append(
                                f"Possible priority cycle between '{reverse.source_state}' "
                                f"and '{reverse.target_state}'"
                            )
                            reported_cycles.add(cycle_id)

        return errors
