import unittest
import pytest
import asyncio
from app.states import AFSMState, StateTransition, StateManager

class MockState(AFSMState):
    """Mock implementation of AFSMState for testing"""
    
    def __init__(self, name, description, allowed_transitions=None, return_values=None):
        super().__init__(name, description, allowed_transitions)
        self.process_called = False
        self.last_input = None
        self.last_context = None
        
        # Default return values: response, next_state_name, updated_context
        self.return_values = return_values or ("Default response", None, {})
    
    async def process(self, input_text, context):
        self.process_called = True
        self.last_input = input_text
        self.last_context = context
        return self.return_values


class TestStateManager(unittest.TestCase):
    """Tests for the StateManager class"""
    
    def setUp(self):
        """Set up test fixtures for each test"""
        self.initial_state = "greeting"
        self.manager = StateManager(self.initial_state)
        
        # Create and register some test states
        self.greeting_state = MockState(
            name="greeting",
            description="Greeting state",
            allowed_transitions=[
                StateTransition(target_state="inquiry")
            ],
            return_values=("Hello there!", None, {})
        )
        
        self.inquiry_state = MockState(
            name="inquiry",
            description="Inquiry state",
            allowed_transitions=[
                StateTransition(target_state="greeting")
            ],
            return_values=("How can I help?", None, {})
        )
        
        self.manager.register_state(self.greeting_state)
        self.manager.register_state(self.inquiry_state)
        
    def test_initialization(self):
        """Test state manager initialization"""
        manager = StateManager("initial_state")
        self.assertEqual(manager.current_state_name, "initial_state")
        self.assertIsNone(manager.context)
    
    def test_register_state(self):
        """Test registering a state"""
        manager = StateManager("test")
        state = MockState("test", "Test state")
        
        manager.register_state(state)
        
        self.assertIn("test", manager.states)
        self.assertEqual(manager.states["test"], state)
    
    def test_register_states(self):
        """Test registering multiple states"""
        manager = StateManager("test")
        states = [
            MockState("state1", "State 1"),
            MockState("state2", "State 2")
        ]
        
        manager.register_states(states)
        
        self.assertIn("state1", manager.states)
        self.assertIn("state2", manager.states)
        self.assertEqual(len(manager.states), 2)
    
    def test_get_state(self):
        """Test getting a state by name"""
        self.assertEqual(self.manager.get_state("greeting"), self.greeting_state)
        self.assertEqual(self.manager.get_state("inquiry"), self.inquiry_state)
        self.assertIsNone(self.manager.get_state("nonexistent"))
    
    def test_get_current_state(self):
        """Test getting the current state"""
        self.assertEqual(self.manager.get_current_state(), self.greeting_state)
        
        # Change the current state and test again
        self.manager.current_state_name = "inquiry"
        self.assertEqual(self.manager.get_current_state(), self.inquiry_state)
    
    def test_initialize_context(self):
        """Test initializing the context"""
        session_id = "test_session"
        user_id = "test_user"
        metadata = {"key": "value"}
        
        context = self.manager.initialize_context(session_id, user_id, metadata)
        
        self.assertEqual(context.session_id, session_id)
        self.assertEqual(context.user_id, user_id)
        self.assertEqual(context.metadata, metadata)
        self.assertEqual(self.manager.context, context)
    
    def test_transition_to_valid_state(self):
        """Test transitioning to a valid state"""
        # Set up a valid transition
        self.manager.current_state_name = "greeting"
        
        # Transition to the inquiry state
        result = self.manager.transition_to("inquiry")
        
        self.assertTrue(result)
        self.assertEqual(self.manager.current_state_name, "inquiry")
    
    def test_transition_to_invalid_state(self):
        """Test transitioning to an invalid state"""
        # Set up an invalid transition target
        result = self.manager.transition_to("nonexistent")
        
        self.assertFalse(result)
        self.assertEqual(self.manager.current_state_name, self.initial_state)
    
    def test_transition_to_disallowed_state(self):
        """Test transitioning to a state that is not in allowed_transitions"""
        # Create a state with no allowed transitions
        no_transitions_state = MockState(
            name="no_transitions",
            description="State with no transitions"
        )
        self.manager.register_state(no_transitions_state)
        
        # Set current state to the one with no transitions
        self.manager.current_state_name = "no_transitions"
        
        # Try to transition to another state
        result = self.manager.transition_to("greeting")
        
        self.assertFalse(result)
        self.assertEqual(self.manager.current_state_name, "no_transitions")
    
    @pytest.mark.asyncio
    async def test_process_input(self):
        """Test processing input through the current state"""
        # Initialize context
        self.manager.initialize_context("test_session")
        
        # Process input
        response = await self.manager.process_input("Hello")
        
        # Verify that the state's process method was called
        self.assertTrue(self.greeting_state.process_called)
        self.assertEqual(self.greeting_state.last_input, "Hello")
        
        # Verify the response
        self.assertEqual(response, "Hello there!")
    
    @pytest.mark.asyncio
    async def test_process_input_with_state_transition(self):
        """Test processing input that triggers a state transition"""
        # Initialize context
        self.manager.initialize_context("test_session")
        
        # Set up the greeting state to trigger a transition to the inquiry state
        self.greeting_state.return_values = ("Hello there!", "inquiry", {})
        
        # Process input
        response = await self.manager.process_input("Hello")
        
        # Verify the response
        self.assertEqual(response, "Hello there!")
        
        # Verify that the state transitioned
        self.assertEqual(self.manager.current_state_name, "inquiry")
    
    @pytest.mark.asyncio
    async def test_process_input_with_context_update(self):
        """Test processing input that updates the context"""
        # Initialize context
        self.manager.initialize_context("test_session")
        
        # Set up the greeting state to update the context
        updated_context = {
            "conversation_history": [{"role": "user", "content": "Hello"}],
            "metadata": {"key": "value"}
        }
        self.greeting_state.return_values = ("Hello there!", None, updated_context)
        
        # Process input
        await self.manager.process_input("Hello")
        
        # Verify that the context was updated
        self.assertEqual(self.manager.context.conversation_history, updated_context["conversation_history"])
        self.assertEqual(self.manager.context.metadata, updated_context["metadata"])
    
    def test_process_input_without_context(self):
        """Test that processing input without initializing context raises an error"""
        with pytest.raises(ValueError):
            asyncio.run(self.manager.process_input("Hello"))
    
    def test_process_input_with_nonexistent_state(self):
        """Test that processing input with a nonexistent current state raises an error"""
        # Initialize context
        self.manager.initialize_context("test_session")
        
        # Set current state to a nonexistent state
        self.manager.current_state_name = "nonexistent"
        
        with pytest.raises(ValueError):
            asyncio.run(self.manager.process_input("Hello")) 