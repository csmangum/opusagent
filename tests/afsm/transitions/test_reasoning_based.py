import unittest
from typing import Any, Dict
from unittest.mock import MagicMock, patch

from fastagent.afsm.transitions.reasoning_based import ReasoningBasedTransition


class TestReasoningBasedTransition(unittest.TestCase):
    """Tests for the ReasoningBasedTransition class"""

    def setUp(self):
        """Set up test fixtures"""
        # Simple reasoning function that returns 0.8 if 'key' equals 'value'
        self.reasoning_func = lambda ctx: 0.8 if ctx.get("key") == "value" else 0.0

        self.transition = ReasoningBasedTransition(
            source_state="source",
            target_state="target",
            reasoning_function=self.reasoning_func,
            priority=5,
            description="Test reasoning transition",
        )

    def test_initialization(self):
        """Test that a reasoning-based transition can be properly initialized"""
        self.assertEqual(self.transition.source_state, "source")
        self.assertEqual(self.transition.target_state, "target")
        self.assertEqual(self.transition.priority, 5)
        self.assertEqual(self.transition.description, "Test reasoning transition")
        self.assertIs(self.transition.reasoning_function, self.reasoning_func)

    def test_evaluate_positive_case(self):
        """Test that evaluate returns the expected confidence when condition is met"""
        context = {"key": "value"}

        self.assertEqual(self.transition.evaluate(context), 0.8)

    def test_evaluate_negative_case(self):
        """Test that evaluate returns 0.0 when condition is not met"""
        context = {"key": "wrong_value"}

        self.assertEqual(self.transition.evaluate(context), 0.0)

    def test_evaluate_with_error(self):
        """Test that evaluate handles errors in the reasoning function gracefully"""
        # Create a function that raises an exception
        error_func = lambda ctx: 1 / 0  # This will raise a ZeroDivisionError

        transition = ReasoningBasedTransition(
            source_state="source", target_state="target", reasoning_function=error_func
        )

        # Should return 0.0 instead of raising an exception
        context = {"key": "value"}
        self.assertEqual(transition.evaluate(context), 0.0)

    def test_evaluate_bounds_checking(self):
        """Test that evaluate ensures the confidence is between 0.0 and 1.0"""
        # Create functions that return values outside the valid range
        below_range_func = lambda ctx: -0.5
        above_range_func = lambda ctx: 1.5

        # Create transitions with these functions
        below_transition = ReasoningBasedTransition(
            source_state="source",
            target_state="target",
            reasoning_function=below_range_func,
        )

        above_transition = ReasoningBasedTransition(
            source_state="source",
            target_state="target",
            reasoning_function=above_range_func,
        )

        context = {}
        # Should clamp to 0.0
        self.assertEqual(below_transition.evaluate(context), 0.0)
        # Should clamp to 1.0
        self.assertEqual(above_transition.evaluate(context), 1.0)

    def test_apply_post_conditions_with_string_scratchpad(self):
        """Test apply_post_conditions updates a string scratchpad correctly"""
        context = {"scratchpad": "Previous reasoning"}

        updated_context = self.transition.apply_post_conditions(context)

        # Check that the scratchpad was updated
        self.assertIn("Previous reasoning", updated_context["scratchpad"])
        self.assertIn("source", updated_context["scratchpad"])
        self.assertIn("target", updated_context["scratchpad"])
        self.assertIn("Test reasoning transition", updated_context["scratchpad"])

    def test_apply_post_conditions_with_list_scratchpad(self):
        """Test apply_post_conditions updates a list scratchpad correctly"""
        context = {"scratchpad": ["Previous reasoning"]}

        updated_context = self.transition.apply_post_conditions(context)

        # Check that the scratchpad was updated
        self.assertEqual(len(updated_context["scratchpad"]), 2)
        self.assertEqual(updated_context["scratchpad"][0], "Previous reasoning")
        self.assertIn("source", updated_context["scratchpad"][1])
        self.assertIn("target", updated_context["scratchpad"][1])

    def test_apply_post_conditions_without_scratchpad(self):
        """Test apply_post_conditions doesn't modify context without scratchpad"""
        context = {"key": "value"}

        updated_context = self.transition.apply_post_conditions(context)

        # Context should be unchanged
        self.assertEqual(updated_context, {"key": "value"})


if __name__ == "__main__":
    unittest.main()
