"""
Simple example demonstrating the FSA context management in a conversation flow.
"""
import os
import sys
import time
from typing import Dict, Any

# Add the app directory to sys.path if needed
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from opusagent.fsa.context import ContextManager, StateContext, ContextItem, ContextCategory, ContextFilter


def simulate_conversation():
    """Simulate a simple conversation using the context management system."""
    # Initialize the context manager with a temp storage directory
    storage_dir = os.path.join(os.path.dirname(__file__), "temp_contexts")
    context_manager = ContextManager(storage_dir=storage_dir)
    
    # Create a new context for this conversation
    context = context_manager.create_context(user_id="user123")
    session_id = context.session_id
    
    print(f"Starting conversation with session_id: {session_id}")
    
    # Initial state
    current_state = "greeting"
    context.current_state = current_state
    
    # Add some initial context
    context.add_session_data("user_name", "John")
    context.add_session_data("language", "en-US")
    context.add_salient("User is a new customer")
    
    # Simulate state transitions and context updates
    transitions = [
        ("greeting", "First time user greeting", "problem_identification"),
        ("problem_identification", "User has a billing issue", "solution_proposal"),
        ("solution_proposal", "Proposed a billing adjustment", "verification"),
        ("verification", "User confirmed the solution", "resolution"),
        ("resolution", "Issue resolved successfully", None)
    ]
    
    for from_state, user_input, to_state in transitions:
        print(f"\n--- State: {from_state} ---")
        
        # Add user input to history
        context.add_history(f"User: {user_input}")
        
        # Get context relevant for the current state
        state_context = context_manager.get_context_for_state(session_id, from_state)
        
        # Print the context for the current state
        print(f"Context for state '{from_state}':")
        print(f"  Salient: {state_context['salient']}")
        print(f"  Session data: {state_context['session_data']}")
        
        # Simulate agent response based on context
        response = generate_response(from_state, state_context)
        print(f"Agent: {response}")
        
        # Add agent response to history
        context.add_history(f"Agent: {response}")
        
        # Add some state-specific data
        context.add_state_data("processed", True, from_state)
        
        if to_state:
            # Transition to the next state
            print(f"Transitioning from '{from_state}' to '{to_state}'")
            context_manager.handle_state_transition(session_id, from_state, to_state)
        else:
            # End of conversation
            print("Conversation complete")
            
    # End the session
    context_manager.end_session(session_id)
    print(f"\nSession {session_id} ended")
    
    # Try to reload the context
    loaded_context = context_manager.load_context(session_id)
    if loaded_context:
        print(f"Successfully reloaded context for session {session_id}")
        print(f"User ID: {loaded_context.user_id}")
        print(f"Final state: {loaded_context.current_state}")
    else:
        print(f"Could not reload context for session {session_id}")


def generate_response(state: str, context: Dict[str, Any]) -> str:
    """
    Generate a simulated response based on the state and context.
    
    In a real FSA implementation, this would be handled by the state's process method.
    """
    responses = {
        "greeting": f"Hello {context['session_data'].get('user_name', 'there')}! Welcome to our support system. How can I help you today?",
        "problem_identification": "I understand you're having a billing issue. Could you please provide more details?",
        "solution_proposal": "Based on what you've told me, I suggest we apply a $20 credit to your account. Would that resolve your issue?",
        "verification": "Great! I've confirmed the adjustment to your account.",
        "resolution": "Your issue has been fully resolved. Is there anything else I can help you with today?"
    }
    
    return responses.get(state, "I'm not sure what to say next.")


if __name__ == "__main__":
    simulate_conversation() 