import unittest
from typing import Any, Dict
from unittest.mock import MagicMock, patch

from app.transitions.base import BaseTransition
from app.transitions.evaluator import TransitionEvaluator
from app.transitions.registry import TransitionRegistry


class MockTransition(BaseTransition):
    """Mock transition for testing with configurable confidence"""

    def __init__(
        self,
        source_state: str,
        target_state: str,
        confidence: float = 1.0,
        priority: int = 0,
        description: str = "",
    ):
        super().__init__(source_state, target_state, priority, description)
        self.confidence = confidence
        self.context_for_pre = None
        self.context_for_post = None

    def evaluate(self, context: Dict[str, Any]) -> float:
        return self.confidence

    def apply_pre_conditions(self, context: Dict[str, Any]) -> Dict[str, Any]:
        self.context_for_pre = context
        updated_context = context.copy()
        updated_context["pre_applied"] = True
        return updated_context

    def apply_post_conditions(self, context: Dict[str, Any]) -> Dict[str, Any]:
        self.context_for_post = context
        updated_context = context.copy()
        updated_context["post_applied"] = True
        return updated_context


class TestTransitionEvaluator(unittest.TestCase):
    """Tests for the TransitionEvaluator class"""

    def setUp(self):
        """Set up test fixtures"""
        self.registry = TransitionRegistry()
        self.evaluator = TransitionEvaluator(self.registry)

        # Create some mock transitions
        self.transition1 = MockTransition("state1", "state2", 0.7, 5, "Transition 1")
        self.transition2 = MockTransition("state1", "state3", 0.8, 3, "Transition 2")
        self.transition3 = MockTransition("state1", "state4", 0.9, 1, "Transition 3")
        self.transition4 = MockTransition("state2", "state3", 0.6, 2, "Transition 4")

        # Register the transitions
        self.registry.register_many(
            [self.transition1, self.transition2, self.transition3, self.transition4]
        )

    def test_initialization(self):
        """Test that the evaluator is properly initialized"""
        self.assertIs(self.evaluator.registry, self.registry)

    def test_evaluate_transitions_with_no_candidates(self):
        """Test evaluation when there are no candidate transitions"""
        # Use a state with no outgoing transitions
        result = self.evaluator.evaluate_transitions("nonexistent_state", {})

        # Should return None
        self.assertIsNone(result)

    def test_evaluate_transitions_with_no_confidence(self):
        """Test evaluation when no transitions have confidence"""
        # Set all confidences to 0
        self.transition1.confidence = 0.0
        self.transition2.confidence = 0.0
        self.transition3.confidence = 0.0

        result = self.evaluator.evaluate_transitions("state1", {})

        # Should return None
        self.assertIsNone(result)

    def test_evaluate_transitions_priority_ordering(self):
        """Test that transitions are ordered by priority first"""
        # All transitions have the same confidence but different priorities
        self.transition1.confidence = 0.5  # Priority 5
        self.transition2.confidence = 0.5  # Priority 3
        self.transition3.confidence = 0.5  # Priority 1

        result = self.evaluator.evaluate_transitions("state1", {})

        # Should return the transition with highest priority (transition1)
        self.assertIsNotNone(result)
        self.assertEqual(result[0], self.transition1)
        self.assertEqual(result[1], 0.5)

    def test_evaluate_transitions_confidence_ordering(self):
        """Test that transitions with equal priority are ordered by confidence"""
        # Set all transitions to the same priority but different confidences
        self.transition1.priority = 5
        self.transition2.priority = 5
        self.transition3.priority = 5

        self.transition1.confidence = 0.7
        self.transition2.confidence = 0.9
        self.transition3.confidence = 0.8

        result = self.evaluator.evaluate_transitions("state1", {})

        # Should return the transition with highest confidence (transition2)
        self.assertIsNotNone(result)
        self.assertEqual(result[0], self.transition2)
        self.assertEqual(result[1], 0.9)

    def test_get_best_transition(self):
        """Test getting the best transition without confidence"""
        result = self.evaluator.get_best_transition("state1", {})

        # Should return the transition with highest priority and confidence
        self.assertEqual(result, self.transition1)

    def test_get_best_transition_none(self):
        """Test that get_best_transition returns None when there are no candidates"""
        result = self.evaluator.get_best_transition("nonexistent_state", {})

        self.assertIsNone(result)

    def test_apply_transition(self):
        """Test applying a transition"""
        context = {"key": "value"}

        next_state, updated_context = self.evaluator.apply_transition("state1", context)

        # Should transition to state2 (target of transition1)
        self.assertEqual(next_state, "state2")

        # Context should be updated
        self.assertEqual(updated_context["key"], "value")
        self.assertTrue(updated_context["pre_applied"])
        self.assertTrue(updated_context["post_applied"])
        self.assertIn("last_transition", updated_context)
        self.assertEqual(updated_context["last_transition"]["source"], "state1")
        self.assertEqual(updated_context["last_transition"]["target"], "state2")
        self.assertEqual(updated_context["last_transition"]["confidence"], 0.7)

    def test_apply_transition_no_match(self):
        """Test applying a transition when there is no match"""
        context = {"key": "value"}

        next_state, updated_context = self.evaluator.apply_transition(
            "nonexistent_state", context
        )

        # Should return None for next state
        self.assertIsNone(next_state)

        # Context should be unchanged
        self.assertEqual(updated_context, context)

    def test_apply_transition_order(self):
        """Test that pre-conditions, last_transition, and post-conditions are applied in order"""
        # Create a mock transition that records the order of calls
        call_order = []

        class OrderTrackingTransition(BaseTransition):
            def evaluate(self, context):
                return 1.0

            def apply_pre_conditions(self, context):
                call_order.append("pre")
                return context

            def apply_post_conditions(self, context):
                # Verify that last_transition was set before post-conditions
                call_order.append("post")
                self.last_transition_set = "last_transition" in context
                return context

        transition = OrderTrackingTransition("state5", "state6")
        self.registry.register(transition)

        context = {}
        self.evaluator.apply_transition("state5", context)

        # Check order: pre, then post
        self.assertEqual(call_order, ["pre", "post"])

        # Check that last_transition was set before post-conditions
        self.assertTrue(getattr(transition, "last_transition_set", False))


if __name__ == "__main__":
    unittest.main()
