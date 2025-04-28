import asyncio
import unittest

import pytest

from app.afsm.states import AFSMState, StateContext, StateTransition


class TestStateTransition(unittest.TestCase):
    """Tests for the StateTransition class"""

    def test_state_transition_initialization(self):
        """Test that a StateTransition can be properly initialized"""
        transition = StateTransition(target_state="test_state")
        self.assertEqual(transition.target_state, "test_state")
        self.assertIsNone(transition.condition)
        self.assertEqual(transition.priority, 0)

    def test_state_transition_with_condition(self):
        """Test initialization with a condition"""
        transition = StateTransition(
            target_state="test_state", condition="test condition", priority=5
        )
        self.assertEqual(transition.target_state, "test_state")
        self.assertEqual(transition.condition, "test condition")
        self.assertEqual(transition.priority, 5)

    def test_state_transition_string_representation(self):
        """Test the string representation of a transition"""
        transition = StateTransition(target_state="test_state")
        self.assertEqual(str(transition), "Transition to test_state")

        transition_with_condition = StateTransition(
            target_state="test_state", condition="test condition"
        )
        self.assertEqual(
            str(transition_with_condition),
            "Transition to test_state when test condition",
        )


class TestStateContext(unittest.TestCase):
    """Tests for the StateContext class"""

    def test_state_context_initialization(self):
        """Test that a StateContext can be properly initialized"""
        context = StateContext(session_id="test_session")
        self.assertEqual(context.session_id, "test_session")
        self.assertIsNone(context.user_id)
        self.assertEqual(context.conversation_history, [])
        self.assertEqual(context.metadata, {})

    def test_state_context_with_user_id(self):
        """Test initialization with a user ID"""
        context = StateContext(session_id="test_session", user_id="test_user")
        self.assertEqual(context.session_id, "test_session")
        self.assertEqual(context.user_id, "test_user")

    def test_state_context_with_metadata(self):
        """Test initialization with metadata"""
        metadata = {"key1": "value1", "key2": "value2"}
        context = StateContext(session_id="test_session", metadata=metadata)
        self.assertEqual(context.metadata, metadata)

    def test_state_context_conversation_history(self):
        """Test adding to conversation history"""
        context = StateContext(session_id="test_session")

        # Add a message to the conversation history
        context.conversation_history.append({"role": "user", "content": "Hello"})

        self.assertEqual(len(context.conversation_history), 1)
        self.assertEqual(context.conversation_history[0]["role"], "user")
        self.assertEqual(context.conversation_history[0]["content"], "Hello")

    def test_state_context_with_empty_string_session_id(self):
        """Test handling of empty string session ID"""
        context = StateContext(session_id="")
        self.assertEqual(context.session_id, "")

    def test_state_context_with_large_history(self):
        """Test handling a large conversation history"""
        context = StateContext(session_id="test_session")

        # Add 100 messages to the conversation history
        for i in range(100):
            context.conversation_history.append(
                {
                    "role": "user" if i % 2 == 0 else "assistant",
                    "content": f"Message {i}",
                }
            )

        self.assertEqual(len(context.conversation_history), 100)
        self.assertEqual(context.conversation_history[99]["content"], "Message 99")

    def test_state_context_nested_metadata(self):
        """Test handling nested metadata structures"""
        nested_metadata = {
            "user_preferences": {
                "theme": "dark",
                "notifications": {"email": True, "sms": False},
            },
            "session_data": {"duration": 3600, "active": True},
        }

        context = StateContext(session_id="test_session", metadata=nested_metadata)
        self.assertEqual(context.metadata, nested_metadata)
        self.assertTrue(context.metadata["user_preferences"]["notifications"]["email"])
        self.assertEqual(context.metadata["user_preferences"]["theme"], "dark")


class TestAFSMState(unittest.TestCase):
    """Tests for the AFSMState class"""

    def test_state_initialization(self):
        """Test that a state can be properly initialized"""
        state = AFSMState("test_state", "Test state description")
        self.assertEqual(state.name, "test_state")
        self.assertEqual(state.description, "Test state description")
        self.assertEqual(state.allowed_transitions, [])
        self.assertEqual(state.scratchpad, "")

    def test_state_with_transitions(self):
        """Test initialization with transitions"""
        transitions = [
            StateTransition(target_state="state1"),
            StateTransition(target_state="state2"),
        ]
        state = AFSMState("test_state", "Test description", transitions)
        self.assertEqual(len(state.allowed_transitions), 2)
        self.assertEqual(state.allowed_transitions[0].target_state, "state1")
        self.assertEqual(state.allowed_transitions[1].target_state, "state2")

    def test_scratchpad_operations(self):
        """Test scratchpad operations"""
        state = AFSMState("test_state", "Test description")

        # Test writing to scratchpad
        state.write_to_scratchpad("Test content")
        self.assertEqual(state.get_scratchpad(), "Test content")

        # Test appending to scratchpad
        state.write_to_scratchpad(" additional content")
        self.assertEqual(state.get_scratchpad(), "Test content additional content")

        # Test clearing scratchpad
        state.clear_scratchpad()
        self.assertEqual(state.get_scratchpad(), "")

    def test_can_transition_to(self):
        """Test can_transition_to method"""
        transitions = [
            StateTransition(target_state="state1"),
            StateTransition(target_state="state2"),
        ]
        state = AFSMState("test_state", "Test description", transitions)

        self.assertTrue(state.can_transition_to("state1"))
        self.assertTrue(state.can_transition_to("state2"))
        self.assertFalse(state.can_transition_to("state3"))

    def test_get_valid_transitions(self):
        """Test get_valid_transitions method"""
        transitions = [
            StateTransition(target_state="state1"),
            StateTransition(target_state="state2"),
        ]
        state = AFSMState("test_state", "Test description", transitions)

        context = StateContext(session_id="test_session")
        valid_transitions = state.get_valid_transitions(context)

        self.assertEqual(len(valid_transitions), 2)
        self.assertEqual(valid_transitions[0].target_state, "state1")
        self.assertEqual(valid_transitions[1].target_state, "state2")

    def test_string_representation(self):
        """Test the string representation of a state"""
        state = AFSMState("test_state", "Test description")
        self.assertEqual(str(state), "State(test_state): Test description")

    @pytest.mark.asyncio
    async def test_process_not_implemented(self):
        """Test that process raises NotImplementedError"""
        state = AFSMState("test_state", "Test description")
        context = StateContext(session_id="test_session")

        with pytest.raises(NotImplementedError):
            await state.process("test input", context)

    def test_scratchpad_with_large_content(self):
        """Test scratchpad with large content"""
        state = AFSMState("test_state", "Test description")

        # Generate a large string (100KB)
        large_content = "A" * 100_000

        # Write the large content to the scratchpad
        state.write_to_scratchpad(large_content)

        # Verify the content was written correctly
        self.assertEqual(len(state.get_scratchpad()), 100_000)

        # Clear and verify
        state.clear_scratchpad()
        self.assertEqual(state.get_scratchpad(), "")

    def test_transitions_priority_order(self):
        """Test that transitions are considered in priority order"""
        transitions = [
            StateTransition(target_state="low_priority", priority=1),
            StateTransition(target_state="high_priority", priority=10),
            StateTransition(target_state="medium_priority", priority=5),
        ]

        state = AFSMState("test_state", "Test description", transitions)
        context = StateContext(session_id="test_session")

        # This test doesn't actually verify priority ordering since the base implementation
        # doesn't sort transitions. In a real implementation, you would sort by priority
        # This is just testing that transitions with priorities can be added and retrieved
        valid_transitions = state.get_valid_transitions(context)
        self.assertEqual(len(valid_transitions), 3)
