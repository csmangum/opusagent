import unittest
from typing import Any, Dict
from unittest.mock import MagicMock, patch

from fastagent.fsa.transitions.base import BaseTransition
from fastagent.fsa.transitions.registry import TransitionRegistry


class MockTransition(BaseTransition):
    """Mock transition for testing"""

    def __init__(
        self,
        source_state: str,
        target_state: str,
        priority: int = 0,
        description: str = "",
    ):
        super().__init__(source_state, target_state, priority, description)

    def evaluate(self, context: Dict[str, Any]) -> float:
        return 1.0


class TestTransitionRegistry(unittest.TestCase):
    """Tests for the TransitionRegistry class"""

    def setUp(self):
        """Set up test fixtures"""
        self.registry = TransitionRegistry()

        # Create some mock transitions
        self.transition1 = MockTransition("state1", "state2", 5, "Transition 1")
        self.transition2 = MockTransition("state1", "state3", 3, "Transition 2")
        self.transition3 = MockTransition("state2", "state3", 1, "Transition 3")
        self.transition4 = MockTransition("state3", "state1", 2, "Transition 4")

    def test_initialization(self):
        """Test that the registry is properly initialized"""
        self.assertEqual(len(self.registry.get_all_transitions()), 0)
        self.assertEqual(len(self.registry.get_all_states()), 0)

    def test_register_single(self):
        """Test registering a single transition"""
        self.registry.register(self.transition1)

        # Check that it was added
        self.assertEqual(len(self.registry.get_all_transitions()), 1)
        self.assertEqual(self.registry.get_all_transitions()[0], self.transition1)

        # Check the states
        self.assertEqual(self.registry.get_all_states(), {"state1", "state2"})

        # Check that it can be retrieved
        from_state = self.registry.get_transitions_from_state("state1")
        self.assertEqual(len(from_state), 1)
        self.assertEqual(from_state[0], self.transition1)

        between_states = self.registry.get_transitions_between_states(
            "state1", "state2"
        )
        self.assertEqual(len(between_states), 1)
        self.assertEqual(between_states[0], self.transition1)

    def test_register_many(self):
        """Test registering multiple transitions at once"""
        self.registry.register_many(
            [self.transition1, self.transition2, self.transition3]
        )

        # Check that they were all added
        self.assertEqual(len(self.registry.get_all_transitions()), 3)

        # Check the states
        self.assertEqual(self.registry.get_all_states(), {"state1", "state2", "state3"})

    def test_get_transitions_from_state(self):
        """Test retrieving transitions from a specific state"""
        self.registry.register_many(
            [self.transition1, self.transition2, self.transition3]
        )

        # State1 has two outgoing transitions
        from_state1 = self.registry.get_transitions_from_state("state1")
        self.assertEqual(len(from_state1), 2)
        self.assertIn(self.transition1, from_state1)
        self.assertIn(self.transition2, from_state1)

        # State2 has one outgoing transition
        from_state2 = self.registry.get_transitions_from_state("state2")
        self.assertEqual(len(from_state2), 1)
        self.assertEqual(from_state2[0], self.transition3)

        # State3 has no outgoing transitions yet
        from_state3 = self.registry.get_transitions_from_state("state3")
        self.assertEqual(len(from_state3), 0)

        # Non-existent state
        from_nonexistent = self.registry.get_transitions_from_state("nonexistent")
        self.assertEqual(len(from_nonexistent), 0)

    def test_get_transitions_between_states(self):
        """Test retrieving transitions between specific states"""
        self.registry.register_many(
            [self.transition1, self.transition2, self.transition3, self.transition4]
        )

        # Transitions from state1 to state2
        state1_to_state2 = self.registry.get_transitions_between_states(
            "state1", "state2"
        )
        self.assertEqual(len(state1_to_state2), 1)
        self.assertEqual(state1_to_state2[0], self.transition1)

        # No transitions from state1 to state1 (self-transition)
        state1_to_state1 = self.registry.get_transitions_between_states(
            "state1", "state1"
        )
        self.assertEqual(len(state1_to_state1), 0)

        # Non-existent source state
        nonexistent_source = self.registry.get_transitions_between_states(
            "nonexistent", "state1"
        )
        self.assertEqual(len(nonexistent_source), 0)

        # Non-existent target state
        nonexistent_target = self.registry.get_transitions_between_states(
            "state1", "nonexistent"
        )
        self.assertEqual(len(nonexistent_target), 0)

    def test_get_all_states(self):
        """Test retrieving all states"""
        # Add all transitions
        self.registry.register_many(
            [self.transition1, self.transition2, self.transition3, self.transition4]
        )

        # Check that all states are included
        states = self.registry.get_all_states()
        self.assertEqual(states, {"state1", "state2", "state3"})

    def test_validate_no_outgoing_transitions(self):
        """Test validation for states with no outgoing transitions"""
        # Add transitions leaving out state3 -> state1
        self.registry.register_many(
            [self.transition1, self.transition2, self.transition3]
        )

        # Validate
        errors = self.registry.validate()

        # Should report state3 has no outgoing transitions
        self.assertEqual(len(errors), 1)
        self.assertIn("state3", errors[0])
        self.assertIn("no outgoing transitions", errors[0])

    def test_validate_circular_references(self):
        """Test validation for circular references with high priority"""
        # Add a high-priority transition from state2 back to state1
        circular_transition = MockTransition(
            "state2", "state1", 6, "High priority circular"
        )

        self.registry.register_many([self.transition1, circular_transition])

        # Validate
        errors = self.registry.validate()

        # Should report a cycle
        self.assertEqual(len(errors), 1)
        self.assertIn("cycle", errors[0].lower())
        self.assertIn("state1", errors[0])
        self.assertIn("state2", errors[0])

    def test_validate_no_errors(self):
        """Test validation when there are no errors"""
        # Add transitions where every state has an outgoing transition
        # and there are no high-priority cycles

        # transition1: state1 -> state2, priority 5
        # transition2: state1 -> state3, priority 3
        # transition3: state2 -> state3, priority 1
        # transition4: state3 -> state1, priority 2

        self.registry.register_many(
            [self.transition1, self.transition2, self.transition3, self.transition4]
        )

        # Validate
        errors = self.registry.validate()

        # Should have no errors
        self.assertEqual(len(errors), 0)


if __name__ == "__main__":
    unittest.main()
