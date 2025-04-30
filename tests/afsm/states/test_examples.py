import unittest
import pytest
import asyncio
from fastagent.afsm.states.base import StateContext
from fastagent.afsm.states.examples import (
    GreetingState,
    AuthenticationState,
    GeneralInquiryState,
    AccountVerificationState
)

# Add this import at the top
import pytest_asyncio


class TestGreetingState(unittest.TestCase):
    """Tests for the GreetingState implementation"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.state = GreetingState()
        self.context = StateContext(session_id="test_session")
    
    def test_initialization(self):
        """Test state initialization"""
        self.assertEqual(self.state.name, "greeting")
        self.assertEqual(len(self.state.allowed_transitions), 2)
        
        # Check that the allowed transitions are to the expected states
        target_states = {t.target_state for t in self.state.allowed_transitions}
        self.assertIn("authentication", target_states)
        self.assertIn("general_inquiry", target_states)
    
    @pytest.mark.asyncio
    async def test_process_account_related_input(self):
        """Test processing account-related input"""
        # Test with account-related input
        account_inputs = ["What's my account balance?", "I need to transfer money", "Check my payment status"]
        
        for input_text in account_inputs:
            response, next_state, updated_context = await self.state.process(input_text, self.context)
            
            # Verify that we transition to authentication state
            self.assertEqual(next_state, "authentication")
            
            # Verify that the response mentions verification
            self.assertIn("verify your identity", response.lower())
            
            # Verify that the conversation history was updated
            self.assertIn(input_text, str(updated_context.get("conversation_history", [])))
    
    @pytest.mark.asyncio
    async def test_process_general_inquiry(self):
        """Test processing general inquiry input"""
        # Test with general inquiries
        general_inputs = ["Hello", "Hi there", "What services do you offer?"]
        
        for input_text in general_inputs:
            response, next_state, updated_context = await self.state.process(input_text, self.context)
            
            # Verify that we transition to general_inquiry state
            self.assertEqual(next_state, "general_inquiry")
            
            # Verify that the response is a general greeting
            self.assertIn("hello", response.lower())
            
            # Verify that the conversation history was updated
            self.assertIn(input_text, str(updated_context.get("conversation_history", [])))
    
    @pytest.mark.asyncio
    async def test_scratchpad_content(self):
        """Test that scratchpad is being used for reasoning"""
        await self.state.process("Hello", self.context)
        
        # Check that the scratchpad contains reasoning about the user input
        scratchpad = self.state.get_scratchpad()
        self.assertIn("User has connected", scratchpad)
        self.assertIn("Input received", scratchpad)
        self.assertIn("Detected general inquiry", scratchpad)


class TestAuthenticationState(unittest.TestCase):
    """Tests for the AuthenticationState implementation"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.state = AuthenticationState()
        self.context = StateContext(session_id="test_session")
    
    def test_initialization(self):
        """Test state initialization"""
        self.assertEqual(self.state.name, "authentication")
        self.assertEqual(len(self.state.allowed_transitions), 2)
        
        # Check that the allowed transitions are to the expected states
        target_states = {t.target_state for t in self.state.allowed_transitions}
        self.assertIn("account_verification", target_states)
        self.assertIn("failed_authentication", target_states)
    
    @pytest.mark.asyncio
    async def test_process_authentication(self):
        """Test processing authentication input"""
        # For the example implementation, any input leads to successful authentication
        response, next_state, updated_context = await self.state.process("1234", self.context)
        
        # Verify that we transition to account_verification state
        self.assertEqual(next_state, "account_verification")
        
        # Verify that the response confirms verification
        self.assertIn("verified", response.lower())
        
        # Verify that the metadata was updated with authentication status
        self.assertTrue(updated_context.get("metadata", {}).get("authenticated", False))


class TestGeneralInquiryState(unittest.TestCase):
    """Tests for the GeneralInquiryState implementation"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.state = GeneralInquiryState()
        self.context = StateContext(session_id="test_session")
    
    def test_initialization(self):
        """Test state initialization"""
        self.assertEqual(self.state.name, "general_inquiry")
        self.assertEqual(len(self.state.allowed_transitions), 2)
        
        # Check that the allowed transitions are to the expected states
        target_states = {t.target_state for t in self.state.allowed_transitions}
        self.assertIn("authentication", target_states)
        self.assertIn("greeting", target_states)
    
    @pytest.mark.asyncio
    async def test_process_account_related_inquiry(self):
        """Test processing account-related input"""
        # Test with account-related input
        account_inputs = ["What's my account balance?", "I need to login", "Reset my password"]
        
        for input_text in account_inputs:
            response, next_state, updated_context = await self.state.process(input_text, self.context)
            
            # Verify that we transition to authentication state
            self.assertEqual(next_state, "authentication")
            
            # Verify that the response mentions verification
            self.assertIn("verify your identity", response.lower())
    
    @pytest.mark.asyncio
    async def test_process_hours_inquiry(self):
        """Test processing hours inquiry"""
        response, next_state, updated_context = await self.state.process("What are your hours?", self.context)
        
        # Verify that we stay in the same state (next_state is None)
        self.assertIsNone(next_state)
        
        # Verify that the response mentions hours
        self.assertIn("24/7", response)
    
    @pytest.mark.asyncio
    async def test_process_help_inquiry(self):
        """Test processing help inquiry"""
        response, next_state, updated_context = await self.state.process("Can you help me?", self.context)
        
        # Verify that we stay in the same state (next_state is None)
        self.assertIsNone(next_state)
        
        # Verify that the response offers assistance
        self.assertIn("assist", response.lower())


class TestAccountVerificationState(unittest.TestCase):
    """Tests for the AccountVerificationState implementation"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.state = AccountVerificationState()
        self.context = StateContext(session_id="test_session")
        
        # Set authentication status in context metadata
        self.context.metadata["authenticated"] = True
    
    def test_initialization(self):
        """Test state initialization"""
        self.assertEqual(self.state.name, "account_verification")
        self.assertEqual(len(self.state.allowed_transitions), 2)
        
        # Check that the allowed transitions are to the expected states
        target_states = {t.target_state for t in self.state.allowed_transitions}
        self.assertIn("account_inquiry", target_states)
        self.assertIn("transaction_request", target_states)
    
    @pytest.mark.asyncio
    async def test_process_balance_inquiry(self):
        """Test processing balance inquiry"""
        balance_inquiries = ["What's my balance?", "Show me my statement", "View transaction history"]
        
        for input_text in balance_inquiries:
            response, next_state, updated_context = await self.state.process(input_text, self.context)
            
            # Verify that we transition to account_inquiry state
            self.assertEqual(next_state, "account_inquiry")
            
            # Verify that the response offers account information assistance
            self.assertIn("account information", response.lower())
    
    @pytest.mark.asyncio
    async def test_process_transaction_request(self):
        """Test processing transaction request"""
        transaction_requests = ["I want to transfer money", "Make a payment", "Send $100 to John"]
        
        for input_text in transaction_requests:
            response, next_state, updated_context = await self.state.process(input_text, self.context)
            
            # Verify that we transition to transaction_request state
            self.assertEqual(next_state, "transaction_request")
            
            # Verify that the response offers transaction assistance
            self.assertIn("transaction", response.lower()) 