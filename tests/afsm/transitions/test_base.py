import unittest
from typing import Any, Dict
from unittest.mock import MagicMock, patch

from app.afsm.transitions.base import BaseTransition


class MockTransition(BaseTransition):
    """A concrete implementation of BaseTransition for testing"""

    def evaluate(self, context: Dict[str, Any]) -> float:
        # Simple implementation that returns 1.0 if 'test' is in context
        return 1.0 if context.get("test", False) else 0.0


class TestBaseTransition(unittest.TestCase):
    """Tests for the BaseTransition abstract base class"""

    def setUp(self):
        """Set up test fixtures"""
        self.transition = MockTransition(
            source_state="source",
            target_state="target",
            priority=5,
            description="Test transition",
        )

    def test_initialization(self):
        """Test that a transition can be properly initialized"""
        self.assertEqual(self.transition.source_state, "source")
        self.assertEqual(self.transition.target_state, "target")
        self.assertEqual(self.transition.priority, 5)
        self.assertEqual(self.transition.description, "Test transition")

    def test_str_representation(self):
        """Test the string representation of a transition"""
        expected = "MockTransition: source -> target (priority: 5)"
        self.assertEqual(str(self.transition), expected)

    def test_evaluate_abstract(self):
        """Test that evaluate is an abstract method that must be implemented"""
        with self.assertRaises(TypeError):
            # Try to instantiate the abstract class directly
            BaseTransition("source", "target")

    def test_evaluate_implementation(self):
        """Test a concrete implementation of evaluate"""
        # Should return 1.0 when 'test' is True
        context = {"test": True}
        self.assertEqual(self.transition.evaluate(context), 1.0)

        # Should return 0.0 when 'test' is False
        context = {"test": False}
        self.assertEqual(self.transition.evaluate(context), 0.0)

        # Should return 0.0 when 'test' is missing
        context = {}
        self.assertEqual(self.transition.evaluate(context), 0.0)

    def test_apply_pre_conditions(self):
        """Test that apply_pre_conditions returns the original context by default"""
        context = {"key": "value"}
        self.assertEqual(self.transition.apply_pre_conditions(context), context)

    def test_apply_post_conditions(self):
        """Test that apply_post_conditions returns the original context by default"""
        context = {"key": "value"}
        self.assertEqual(self.transition.apply_post_conditions(context), context)


if __name__ == "__main__":
    unittest.main()
