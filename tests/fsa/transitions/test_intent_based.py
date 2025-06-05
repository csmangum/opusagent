import unittest
from typing import Any, Dict
from unittest.mock import MagicMock, patch

from opusagent.fsa.transitions.intent_based import IntentBasedTransition


class TestIntentBasedTransition(unittest.TestCase):
    """Tests for the IntentBasedTransition class"""

    def setUp(self):
        """Set up test fixtures"""
        self.transition_single = IntentBasedTransition(
            source_state="source",
            target_state="target",
            intents="greeting",
            min_confidence=0.7,
            priority=5,
            description="Test transition with single intent",
        )

        self.transition_multi = IntentBasedTransition(
            source_state="source",
            target_state="target",
            intents=["greeting", "farewell"],
            min_confidence=0.8,
            priority=3,
            description="Test transition with multiple intents",
        )

    def test_initialization_with_string(self):
        """Test initialization with a single intent string"""
        self.assertEqual(self.transition_single.source_state, "source")
        self.assertEqual(self.transition_single.target_state, "target")
        self.assertEqual(self.transition_single.priority, 5)
        self.assertEqual(
            self.transition_single.description, "Test transition with single intent"
        )
        self.assertEqual(self.transition_single.intents, {"greeting"})
        self.assertEqual(self.transition_single.min_confidence, 0.7)

    def test_initialization_with_list(self):
        """Test initialization with a list of intents"""
        self.assertEqual(self.transition_multi.source_state, "source")
        self.assertEqual(self.transition_multi.target_state, "target")
        self.assertEqual(self.transition_multi.priority, 3)
        self.assertEqual(
            self.transition_multi.description, "Test transition with multiple intents"
        )
        self.assertEqual(self.transition_multi.intents, {"greeting", "farewell"})
        self.assertEqual(self.transition_multi.min_confidence, 0.8)

    def test_initialization_with_set(self):
        """Test initialization with a set of intents"""
        transition = IntentBasedTransition(
            source_state="source",
            target_state="target",
            intents={"greeting", "farewell", "help"},
            min_confidence=0.6,
        )

        self.assertEqual(transition.intents, {"greeting", "farewell", "help"})
        self.assertEqual(transition.min_confidence, 0.6)

    def test_evaluate_matching_intent_sufficient_confidence(self):
        """Test evaluate returns confidence when intent matches and confidence is sufficient"""
        context = {"intent": "greeting", "intent_confidence": 0.9}

        # Should return the confidence
        self.assertEqual(self.transition_single.evaluate(context), 0.9)

    def test_evaluate_matching_intent_insufficient_confidence(self):
        """Test evaluate returns 0.0 when intent matches but confidence is insufficient"""
        context = {
            "intent": "greeting",
            "intent_confidence": 0.6,  # Below the 0.7 threshold
        }

        # Should return 0.0
        self.assertEqual(self.transition_single.evaluate(context), 0.0)

    def test_evaluate_non_matching_intent(self):
        """Test evaluate returns 0.0 when intent doesn't match"""
        context = {"intent": "help", "intent_confidence": 0.9}

        # Should return 0.0
        self.assertEqual(self.transition_single.evaluate(context), 0.0)

    def test_evaluate_multiple_intents(self):
        """Test evaluate with multiple possible intents"""
        # Test with greeting intent
        context1 = {"intent": "greeting", "intent_confidence": 0.85}
        self.assertEqual(self.transition_multi.evaluate(context1), 0.85)

        # Test with farewell intent
        context2 = {"intent": "farewell", "intent_confidence": 0.9}
        self.assertEqual(self.transition_multi.evaluate(context2), 0.9)

    def test_evaluate_missing_context_info(self):
        """Test evaluate returns 0.0 when intent info is missing from context"""
        # Missing intent
        context1 = {"intent_confidence": 0.9}
        self.assertEqual(self.transition_single.evaluate(context1), 0.0)

        # Missing confidence
        context2 = {"intent": "greeting"}
        self.assertEqual(self.transition_single.evaluate(context2), 0.0)

        # Empty context
        context3 = {}
        self.assertEqual(self.transition_single.evaluate(context3), 0.0)

    def test_add_intent(self):
        """Test that an intent can be added to the transition"""
        self.transition_single.add_intent("help")

        self.assertEqual(self.transition_single.intents, {"greeting", "help"})

        # Test that the new intent works in evaluation
        context = {"intent": "help", "intent_confidence": 0.8}
        self.assertEqual(self.transition_single.evaluate(context), 0.8)


if __name__ == "__main__":
    unittest.main()
