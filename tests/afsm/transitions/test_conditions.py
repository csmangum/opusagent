import unittest
from typing import Any, Dict
from unittest.mock import MagicMock, patch

from fastagent.afsm.transitions.conditions import PostCondition, PreCondition
from fastagent.afsm.transitions.conditions.post_conditions import clear_variable, log_transition
from fastagent.afsm.transitions.conditions.pre_conditions import merge_variables, set_variable


class TestPreCondition(unittest.TestCase):
    """Tests for the PreCondition class"""

    def test_initialization(self):
        """Test that a pre-condition can be properly initialized"""
        func = lambda ctx: ctx
        condition = PreCondition(func, "Test condition")

        self.assertEqual(condition.description, "Test condition")
        self.assertIs(condition.condition_func, func)

    def test_apply(self):
        """Test that apply calls the condition function"""

        # Create a condition function that adds a key
        def add_key(context):
            context = context.copy()
            context["added"] = True
            return context

        condition = PreCondition(add_key, "Add a key")

        context = {"original": "value"}
        updated_context = condition.apply(context)

        # Check that the original context is unchanged
        self.assertEqual(context, {"original": "value"})

        # Check that the updated context has the added key
        self.assertEqual(updated_context, {"original": "value", "added": True})


class TestPostCondition(unittest.TestCase):
    """Tests for the PostCondition class"""

    def test_initialization(self):
        """Test that a post-condition can be properly initialized"""
        func = lambda ctx: ctx
        condition = PostCondition(func, "Test condition")

        self.assertEqual(condition.description, "Test condition")
        self.assertIs(condition.condition_func, func)

    def test_apply(self):
        """Test that apply calls the condition function"""

        # Create a condition function that adds a key
        def add_key(context):
            context = context.copy()
            context["added"] = True
            return context

        condition = PostCondition(add_key, "Add a key")

        context = {"original": "value"}
        updated_context = condition.apply(context)

        # Check that the original context is unchanged
        self.assertEqual(context, {"original": "value"})

        # Check that the updated context has the added key
        self.assertEqual(updated_context, {"original": "value", "added": True})


class TestPreConditionUtilities(unittest.TestCase):
    """Tests for the pre-condition utility functions"""

    def test_set_variable(self):
        """Test the set_variable function"""
        # Create a pre-condition that sets a variable
        condition = set_variable("key", "value")

        # Check that it's a PreCondition
        self.assertIsInstance(condition, PreCondition)
        self.assertIn("Set key to value", condition.description)

        # Test applying it
        context = {}
        updated_context = condition.apply(context)

        self.assertEqual(updated_context, {"key": "value"})

        # Test that it overwrites existing value
        context = {"key": "old_value"}
        updated_context = condition.apply(context)

        self.assertEqual(updated_context, {"key": "value"})

    def test_merge_variables_dict(self):
        """Test merging dictionary variables"""
        # Create a pre-condition that merges dictionaries
        condition = merge_variables("source", "target")

        # Test with two dictionaries
        context = {
            "source": {"key1": "value1", "key2": "value2"},
            "target": {"key3": "value3"},
        }

        updated_context = condition.apply(context)

        # Check that target now contains all keys
        self.assertEqual(
            updated_context["target"],
            {"key1": "value1", "key2": "value2", "key3": "value3"},
        )

        # Check that source is unchanged
        self.assertEqual(
            updated_context["source"], {"key1": "value1", "key2": "value2"}
        )

    def test_merge_variables_list(self):
        """Test merging list variables"""
        # Create a pre-condition that merges lists
        condition = merge_variables("source", "target")

        # Test with two lists
        context = {"source": [1, 2, 3], "target": [4, 5, 6]}

        updated_context = condition.apply(context)

        # Check that target now contains all elements
        self.assertEqual(updated_context["target"], [4, 5, 6, 1, 2, 3])

        # Check that source is unchanged
        self.assertEqual(updated_context["source"], [1, 2, 3])

    def test_merge_variables_string(self):
        """Test merging string variables"""
        # Create a pre-condition that merges strings
        condition = merge_variables("source", "target")

        # Test with two strings
        context = {"source": "world", "target": "hello "}

        updated_context = condition.apply(context)

        # Check that target now contains concatenated string
        self.assertEqual(updated_context["target"], "hello world")

        # Check that source is unchanged
        self.assertEqual(updated_context["source"], "world")

    def test_merge_variables_different_types(self):
        """Test merging variables of different types"""
        # Create a pre-condition that merges variables
        condition = merge_variables("source", "target")

        # Test with different types (should default to overwrite)
        context = {"source": "string", "target": {"key": "value"}}

        updated_context = condition.apply(context)

        # Check that target is overwritten with source
        self.assertEqual(updated_context["target"], "string")

    def test_merge_variables_missing_keys(self):
        """Test merging when keys are missing"""
        # Create a pre-condition that merges variables
        condition = merge_variables("source", "target")

        # Test with missing source
        context = {"target": "value"}
        updated_context = condition.apply(context)

        # Context should be unchanged
        self.assertEqual(updated_context, {"target": "value"})

        # Test with missing target
        context = {"source": "value"}
        updated_context = condition.apply(context)

        # Context should be unchanged
        self.assertEqual(updated_context, {"source": "value"})


class TestPostConditionUtilities(unittest.TestCase):
    """Tests for the post-condition utility functions"""

    def test_clear_variable(self):
        """Test the clear_variable function"""
        # Create a post-condition that clears a variable
        condition = clear_variable("key")

        # Check that it's a PostCondition
        self.assertIsInstance(condition, PostCondition)
        self.assertIn("Clear key from context", condition.description)

        # Test applying it
        context = {"key": "value", "other_key": "other_value"}
        updated_context = condition.apply(context)

        # Check that the key was removed
        self.assertEqual(updated_context, {"other_key": "other_value"})

        # Test when key doesn't exist
        context = {"other_key": "other_value"}
        updated_context = condition.apply(context)

        # Context should be unchanged
        self.assertEqual(updated_context, {"other_key": "other_value"})

    def test_log_transition(self):
        """Test the log_transition function"""
        # Create a post-condition that logs the transition
        condition = log_transition("transition_history")

        # Check that it's a PostCondition
        self.assertIsInstance(condition, PostCondition)
        self.assertIn("Log transition to transition_history", condition.description)

        # Test applying it when last_transition is in context
        context = {
            "last_transition": {"source": "state1", "target": "state2"},
            "transition_history": [],
        }

        updated_context = condition.apply(context)

        # Check that the transition was logged
        self.assertEqual(len(updated_context["transition_history"]), 1)
        self.assertEqual(
            updated_context["transition_history"][0],
            {"source": "state1", "target": "state2"},
        )

        # Test applying it when log doesn't exist
        context = {"last_transition": {"source": "state1", "target": "state2"}}

        updated_context = condition.apply(context)

        # Check that the log was created
        self.assertIn("transition_history", updated_context)
        self.assertEqual(len(updated_context["transition_history"]), 1)
        self.assertEqual(
            updated_context["transition_history"][0],
            {"source": "state1", "target": "state2"},
        )

        # Test when last_transition doesn't exist
        context = {"transition_history": []}
        updated_context = condition.apply(context)

        # Log should be unchanged
        self.assertEqual(updated_context, {"transition_history": []})


if __name__ == "__main__":
    unittest.main()
