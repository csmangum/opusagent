import unittest
from typing import Any, Dict
from unittest.mock import MagicMock, patch

from app.afsm.transitions.rule_based import Condition, RuleBasedTransition


class TestCondition(unittest.TestCase):
    """Tests for the Condition class"""

    def test_initialization(self):
        """Test that a condition can be properly initialized"""
        predicate = lambda ctx: "value" in ctx
        condition = Condition(predicate, "Check if value is in context")

        self.assertEqual(condition.description, "Check if value is in context")
        self.assertIs(condition.predicate, predicate)

    def test_evaluate_true(self):
        """Test that a condition evaluates to True when its predicate returns True"""
        condition = Condition(
            lambda ctx: "value" in ctx, "Check if value is in context"
        )
        context = {"value": 42}

        self.assertTrue(condition.evaluate(context))

    def test_evaluate_false(self):
        """Test that a condition evaluates to False when its predicate returns False"""
        condition = Condition(
            lambda ctx: "value" in ctx, "Check if value is in context"
        )
        context = {"other_key": 42}

        self.assertFalse(condition.evaluate(context))


class TestRuleBasedTransition(unittest.TestCase):
    """Tests for the RuleBasedTransition class"""

    def setUp(self):
        """Set up test fixtures"""
        self.condition1 = Condition(
            lambda ctx: ctx.get("key1") == "value1", "Condition 1"
        )
        self.condition2 = Condition(
            lambda ctx: ctx.get("key2") == "value2", "Condition 2"
        )

        # Default transition requiring all conditions
        self.transition = RuleBasedTransition(
            source_state="source",
            target_state="target",
            conditions=[self.condition1, self.condition2],
            require_all=True,
            priority=5,
            description="Test transition",
        )

    def test_initialization(self):
        """Test that a rule-based transition can be properly initialized"""
        self.assertEqual(self.transition.source_state, "source")
        self.assertEqual(self.transition.target_state, "target")
        self.assertEqual(self.transition.priority, 5)
        self.assertEqual(self.transition.description, "Test transition")
        self.assertEqual(len(self.transition.conditions), 2)
        self.assertTrue(self.transition.require_all)

    def test_evaluate_all_conditions_true(self):
        """Test that evaluate returns 1.0 when all conditions are met and require_all is True"""
        context = {"key1": "value1", "key2": "value2"}

        self.assertEqual(self.transition.evaluate(context), 1.0)

    def test_evaluate_one_condition_false(self):
        """Test that evaluate returns 0.0 when one condition is not met and require_all is True"""
        context = {"key1": "value1", "key2": "wrong"}

        self.assertEqual(self.transition.evaluate(context), 0.0)

    def test_evaluate_any_condition(self):
        """Test that evaluate returns 1.0 when any condition is met and require_all is False"""
        # Set require_all to False
        self.transition.require_all = False

        # Context where only one condition is met
        context = {"key1": "value1", "key2": "wrong"}

        self.assertEqual(self.transition.evaluate(context), 1.0)

    def test_evaluate_no_conditions_met(self):
        """Test that evaluate returns 0.0 when no conditions are met"""
        # Set require_all to False to make it easier to pass
        self.transition.require_all = False

        # Context where no conditions are met
        context = {"key1": "wrong", "key2": "wrong"}

        self.assertEqual(self.transition.evaluate(context), 0.0)

    def test_evaluate_empty_conditions(self):
        """Test that evaluate returns 0.0 when there are no conditions"""
        transition = RuleBasedTransition(
            source_state="source", target_state="target", conditions=[]
        )

        context = {"key1": "value1", "key2": "value2"}

        self.assertEqual(transition.evaluate(context), 0.0)

    def test_add_condition(self):
        """Test that a condition can be added to a transition"""
        transition = RuleBasedTransition(
            source_state="source", target_state="target", conditions=[]
        )

        self.assertEqual(len(transition.conditions), 0)

        condition = Condition(lambda ctx: True, "Always true")
        transition.add_condition(condition)

        self.assertEqual(len(transition.conditions), 1)
        self.assertIs(transition.conditions[0], condition)


if __name__ == "__main__":
    unittest.main()
