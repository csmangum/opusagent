import asyncio
import unittest

import pytest

from app.states import StateContext, StateManager
from app.states.examples import (
    AccountVerificationState,
    AuthenticationState,
    GeneralInquiryState,
    GreetingState,
)


class TestConversationFlows(unittest.TestCase):
    """Integration tests for complete conversation flows through multiple states"""

    def setUp(self):
        """Set up the state manager with all example states"""
        self.manager = StateManager("greeting")

        # Register all the example states
        self.manager.register_states(
            [
                GreetingState(),
                AuthenticationState(),
                GeneralInquiryState(),
                AccountVerificationState(),
            ]
        )

        # Initialize the context
        self.manager.initialize_context("test_session", "test_user")

    @pytest.mark.asyncio
    async def test_account_inquiry_flow(self):
        """Test the complete flow for an account inquiry"""
        # Step 1: Start with a greeting and account-related question
        response1 = await self.manager.process_input("What's my account balance?")

        # Verify we're now in the authentication state
        self.assertEqual(self.manager.current_state_name, "authentication")
        self.assertIn("verify your identity", response1.lower())

        # Step 2: Provide authentication credentials
        response2 = await self.manager.process_input(
            "1234"
        )  # Example authentication code

        # Verify we're now in the account verification state
        self.assertEqual(self.manager.current_state_name, "account_verification")
        self.assertIn("verified", response2.lower())

        # Step 3: Ask about balance again
        response3 = await self.manager.process_input("What's my balance?")

        # Verify we're now in the account inquiry state
        self.assertEqual(self.manager.current_state_name, "account_inquiry")
        self.assertIn("account information", response3.lower())

        # Verify that the context has been properly maintained
        self.assertTrue(self.manager.context.metadata.get("authenticated", False))
        self.assertEqual(
            len(self.manager.context.conversation_history), 6
        )  # 3 user messages + 3 assistant responses

    @pytest.mark.asyncio
    async def test_general_inquiry_flow(self):
        """Test the flow for general inquiries"""
        # Step 1: Start with a general greeting
        response1 = await self.manager.process_input("Hello")

        # Verify we're in the general inquiry state
        self.assertEqual(self.manager.current_state_name, "general_inquiry")
        self.assertIn("hello", response1.lower())

        # Step 2: Ask about hours
        response2 = await self.manager.process_input("What are your hours?")

        # Should stay in general inquiry state
        self.assertEqual(self.manager.current_state_name, "general_inquiry")
        self.assertIn("24/7", response2)

        # Step 3: Now ask about account
        response3 = await self.manager.process_input("I need to check my balance")

        # Should transition to authentication
        self.assertEqual(self.manager.current_state_name, "authentication")
        self.assertIn("verify your identity", response3.lower())

    @pytest.mark.asyncio
    async def test_mixed_conversation_flow(self):
        """Test a more complex conversation with various state transitions"""
        # Track conversation history manually for verification
        conversation = []

        # Step 1: General greeting
        user_msg = "Hi there"
        conversation.append(("user", user_msg))
        response = await self.manager.process_input(user_msg)
        conversation.append(("assistant", response))

        self.assertEqual(self.manager.current_state_name, "general_inquiry")

        # Step 2: Ask about services
        user_msg = "What services do you offer?"
        conversation.append(("user", user_msg))
        response = await self.manager.process_input(user_msg)
        conversation.append(("assistant", response))

        # Should still be in general inquiry
        self.assertEqual(self.manager.current_state_name, "general_inquiry")

        # Step 3: Switch to account-related inquiry
        user_msg = "I need to transfer some money"
        conversation.append(("user", user_msg))
        response = await self.manager.process_input(user_msg)
        conversation.append(("assistant", response))

        # Should transition to authentication
        self.assertEqual(self.manager.current_state_name, "authentication")

        # Step 4: Provide authentication
        user_msg = "My ID is 12345"
        conversation.append(("user", user_msg))
        response = await self.manager.process_input(user_msg)
        conversation.append(("assistant", response))

        # Should transition to account verification
        self.assertEqual(self.manager.current_state_name, "account_verification")
        self.assertTrue(self.manager.context.metadata.get("authenticated", False))

        # Step 5: Request a transaction
        user_msg = "I want to transfer $100 to John"
        conversation.append(("user", user_msg))
        response = await self.manager.process_input(user_msg)
        conversation.append(("assistant", response))

        # Should transition to transaction request
        self.assertEqual(self.manager.current_state_name, "transaction_request")

        # Verify conversation history length matches our manual tracking
        self.assertEqual(
            len(self.manager.context.conversation_history), len(conversation)
        )

    @pytest.mark.asyncio
    async def test_error_recovery_flow(self):
        """Test that the system can recover from errors in a conversation flow"""
        # Start in greeting state
        self.assertEqual(self.manager.current_state_name, "greeting")

        # Move to authentication
        response1 = await self.manager.process_input("Check my account")
        self.assertEqual(self.manager.current_state_name, "authentication")

        # Simulate an invalid transition by directly changing the state name
        # This is not how it would happen in practice, but allows us to test recovery
        original_state = self.manager.current_state_name
        self.manager.current_state_name = "nonexistent_state"

        # Try to process input - should fail
        with pytest.raises(ValueError):
            await self.manager.process_input("Hello")

        # Recover by setting back to a valid state
        self.manager.current_state_name = original_state

        # Now should be able to process normally
        response2 = await self.manager.process_input("1234")
        self.assertEqual(self.manager.current_state_name, "account_verification")
        self.assertIn("verified", response2.lower())

    @pytest.mark.asyncio
    async def test_conversation_with_empty_inputs(self):
        """Test conversation flow with empty inputs interspersed"""
        # Start with normal input
        response1 = await self.manager.process_input("Hello")
        self.assertEqual(self.manager.current_state_name, "general_inquiry")

        # Send empty input
        response2 = await self.manager.process_input("")
        # Should still be in the same state
        self.assertEqual(self.manager.current_state_name, "general_inquiry")

        # Continue with normal input
        response3 = await self.manager.process_input("I need to access my account")
        self.assertEqual(self.manager.current_state_name, "authentication")

        # Another empty input
        response4 = await self.manager.process_input("")
        # Should still be in authentication
        self.assertEqual(self.manager.current_state_name, "authentication")


# Fixture for async tests
@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
