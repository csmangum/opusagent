import unittest
from typing import Any, Dict
from unittest.mock import MagicMock, patch

from fastagent.afsm.transitions.base import BaseTransition
from fastagent.afsm.transitions.hybrid import HybridTransition


class MockTransition(BaseTransition):
    """Mock transition for testing that returns a specified confidence"""

    def __init__(
        self,
        source_state: str,
        target_state: str,
        confidence: float,
        priority: int = 0,
        description: str = "",
    ):
        super().__init__(source_state, target_state, priority, description)
        self.confidence = confidence
        self.pre_conditions_called = False
        self.post_conditions_called = False

    def evaluate(self, context: Dict[str, Any]) -> float:
        return self.confidence

    def apply_pre_conditions(self, context: Dict[str, Any]) -> Dict[str, Any]:
        self.pre_conditions_called = True
        updated_context = context.copy()
        updated_context[f"pre_condition_{id(self)}"] = True
        return updated_context

    def apply_post_conditions(self, context: Dict[str, Any]) -> Dict[str, Any]:
        self.post_conditions_called = True
        updated_context = context.copy()
        updated_context[f"post_condition_{id(self)}"] = True
        return updated_context


class TestHybridTransition(unittest.TestCase):
    """Tests for the HybridTransition class"""

    def setUp(self):
        """Set up test fixtures"""
        # Create mock transitions with different confidences
        self.transition1 = MockTransition("source", "target", 0.7)
        self.transition2 = MockTransition("source", "target", 0.9)
        self.transition3 = MockTransition("source", "target", 0.5)

        # Create a hybrid transition using these mock transitions
        self.hybrid = HybridTransition(
            source_state="source",
            target_state="target",
            transitions=[
                (self.transition1, 0.5),  # 50% weight
                (self.transition2, 0.3),  # 30% weight
                (self.transition3, 0.2),  # 20% weight
            ],
            threshold=0.6,
            priority=5,
            description="Test hybrid transition",
        )

    def test_initialization(self):
        """Test that a hybrid transition can be properly initialized"""
        self.assertEqual(self.hybrid.source_state, "source")
        self.assertEqual(self.hybrid.target_state, "target")
        self.assertEqual(self.hybrid.priority, 5)
        self.assertEqual(self.hybrid.description, "Test hybrid transition")
        self.assertEqual(self.hybrid.threshold, 0.6)
        self.assertEqual(len(self.hybrid.transitions), 3)

    def test_initialization_with_invalid_weights(self):
        """Test that invalid weights raise a ValueError"""
        with self.assertRaises(ValueError):
            # Total weight (0.5 + 0.3 + 0.3 = 1.1) exceeds 1.0
            HybridTransition(
                source_state="source",
                target_state="target",
                transitions=[
                    (self.transition1, 0.5),
                    (self.transition2, 0.3),
                    (self.transition3, 0.3),
                ],
            )

        with self.assertRaises(ValueError):
            # Total weight (0.5 + 0.3 = 0.8) is less than 1.0
            HybridTransition(
                source_state="source",
                target_state="target",
                transitions=[(self.transition1, 0.5), (self.transition2, 0.3)],
            )

    def test_evaluate_weighted_confidence(self):
        """Test that evaluate returns the correct weighted confidence"""
        context = {}

        # Expected confidence: 0.7 * 0.5 + 0.9 * 0.3 + 0.5 * 0.2 = 0.35 + 0.27 + 0.1 = 0.72
        self.assertEqual(self.hybrid.evaluate(context), 0.72)

    def test_evaluate_with_threshold(self):
        """Test that evaluate returns 0.0 when confidence is below threshold"""
        # Create a hybrid transition with a higher threshold
        hybrid = HybridTransition(
            source_state="source",
            target_state="target",
            transitions=[
                (self.transition1, 0.5),
                (self.transition2, 0.3),
                (self.transition3, 0.2),
            ],
            threshold=0.8,  # Higher than the expected 0.72
        )

        context = {}

        # Should return 0.0 since 0.72 < 0.8
        self.assertEqual(hybrid.evaluate(context), 0.0)

    def test_evaluate_with_no_transitions(self):
        """Test that evaluate returns 0.0 when there are no transitions"""
        hybrid = HybridTransition(
            source_state="source", target_state="target", transitions=[]  # Empty list
        )

        context = {}

        self.assertEqual(hybrid.evaluate(context), 0.0)

    def test_evaluate_skips_wrong_source_state(self):
        """Test that evaluate skips transitions with non-matching source states"""
        # Create a transition with a different source state
        other_transition = MockTransition("other_source", "target", 0.9)

        hybrid = HybridTransition(
            source_state="source",
            target_state="target",
            transitions=[
                (self.transition1, 0.5),
                (other_transition, 0.5),  # Should be skipped in evaluation
            ],
        )

        context = {}

        # Should only include the matching transition: 0.7 * 0.5 = 0.35
        # Since the threshold is 0.5 by default, this should return 0.0
        self.assertEqual(hybrid.evaluate(context), 0.0)

    def test_apply_pre_conditions(self):
        """Test that apply_pre_conditions applies all constituent transitions' pre-conditions"""
        context = {"initial": "value"}

        updated_context = self.hybrid.apply_pre_conditions(context)

        # Check that all pre-conditions were applied
        self.assertTrue(self.transition1.pre_conditions_called)
        self.assertTrue(self.transition2.pre_conditions_called)
        self.assertTrue(self.transition3.pre_conditions_called)

        # Check that the context was updated correctly
        self.assertEqual(updated_context["initial"], "value")
        self.assertTrue(f"pre_condition_{id(self.transition1)}" in updated_context)
        self.assertTrue(f"pre_condition_{id(self.transition2)}" in updated_context)
        self.assertTrue(f"pre_condition_{id(self.transition3)}" in updated_context)

    def test_apply_post_conditions(self):
        """Test that apply_post_conditions applies all constituent transitions' post-conditions"""
        context = {"initial": "value"}

        updated_context = self.hybrid.apply_post_conditions(context)

        # Check that all post-conditions were applied
        self.assertTrue(self.transition1.post_conditions_called)
        self.assertTrue(self.transition2.post_conditions_called)
        self.assertTrue(self.transition3.post_conditions_called)

        # Check that the context was updated correctly
        self.assertEqual(updated_context["initial"], "value")
        self.assertTrue(f"post_condition_{id(self.transition1)}" in updated_context)
        self.assertTrue(f"post_condition_{id(self.transition2)}" in updated_context)
        self.assertTrue(f"post_condition_{id(self.transition3)}" in updated_context)


if __name__ == "__main__":
    unittest.main()
