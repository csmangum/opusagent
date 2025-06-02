import asyncio
import logging
import sys
from typing import Dict, List, Optional

# Add parent directory to path to make imports work
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from states import StateManager
from states.examples import (
    GreetingState, 
    AuthenticationState, 
    GeneralInquiryState, 
    AccountVerificationState
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger("fastagent.examples.fsa_demo")

async def main():
    """Run a simple demonstration of the FSA."""
    # Create state instances
    greeting_state = GreetingState()
    auth_state = AuthenticationState()
    general_inquiry_state = GeneralInquiryState()
    account_verification_state = AccountVerificationState()
    
    # Initialize the state manager with the greeting state as the starting state
    manager = StateManager(initial_state="greeting")
    
    # Register all states
    manager.register_states([
        greeting_state,
        auth_state,
        general_inquiry_state,
        account_verification_state
    ])
    
    # Initialize the context
    session_id = "demo-session-123"
    manager.initialize_context(
        session_id=session_id,
        user_id="demo-user",
        metadata={"demo_mode": True}
    )
    
    print("\n" + "="*50)
    print("FSA Demo - Bank Customer Service Simulation")
    print("="*50)
    print("Type your messages below. Type 'exit' to quit.")
    print("="*50 + "\n")
    
    # Main conversation loop
    while True:
        # Get user input
        user_input = input("\nYou: ")
        
        if user_input.lower() in ["exit", "quit", "bye"]:
            print("\nThank you for using the FSA demo. Goodbye!")
            break
        
        # Process the input through the FSA
        response = await manager.process_input(user_input)
        
        # Display the response
        print(f"\nAssistant: {response}")
        
        # For demonstration purposes, show the current state and scratchpad
        current_state = manager.get_current_state()
        print(f"\n[Debug] Current state: {current_state.name}")
        print(f"[Debug] Scratchpad content:\n{'-'*50}\n{current_state.get_scratchpad()}\n{'-'*50}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDemo terminated by user.")
        sys.exit(0) 