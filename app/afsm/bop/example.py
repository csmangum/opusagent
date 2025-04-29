"""
Bank of Peril FSM Example

This script demonstrates a complete user interaction flow with the Bank of Peril finite state machine.
It shows how transitions work between different states based on user inputs.
"""
import asyncio
from typing import Dict, Any, Optional

from .states import BANK_OF_PERIL_STATES
from .transitions import create_transition_registry
from ..core.fsm import AgentFiniteStateMachine


async def simulate_conversation(fsm: AgentFiniteStateMachine, messages: list) -> None:
    """Simulate a conversation with the Bank of Peril FSM using predefined messages."""
    print("\n===== Bank of Peril FSM Demonstration =====\n")
    
    # Initialize with empty user input to start from idle state
    state = "idle"
    context = {
        "conversation_history": [],
        "metadata": {}
    }
    
    print(f"Initial state: {state}")
    print("-" * 40)
    
    # Process each message in sequence
    for message in messages:
        print(f"User: {message}")
        
        # Process the message through the current state
        response, next_state, updated_context = await fsm.process_input(message, state, context)
        
        # Update state and context for next iteration
        if next_state:
            print(f"Transition: {state} -> {next_state}")
            state = next_state
        
        context = updated_context
        
        if response:
            print(f"Assistant: {response}")
        
        print(f"Current state: {state}")
        print("-" * 40)


async def main() -> None:
    # Create FSM with states and transitions
    states = BANK_OF_PERIL_STATES
    transition_registry = create_transition_registry()
    
    fsm = AgentFiniteStateMachine(
        states=states,
        transition_registry=transition_registry,
        initial_state="idle"
    )
    
    # Define a sample conversation flow
    sample_conversation = [
        # Start conversation (idle -> greeting -> authenticating)
        "Hello, I need to access my account",
        
        # Authentication (authenticating -> main_menu)
        "My account number is 1234 and my PIN is 5678",
        
        # Main menu selection (main_menu -> identify_intent -> gather_balance_details)
        "I want to check my account balance",
        
        # Provide account details (gather_balance_details -> confirm_action)
        "Checking account",
        
        # Confirm action (confirm_action -> executing_transaction)
        "Yes, please proceed",
        
        # After transaction completes (executing_transaction -> reporting_success)
        # No input needed, automatic transition
        "",
        
        # After success report (reporting_success -> main_menu)
        "I'd like to do something else",
        
        # Main menu to transfer (main_menu -> identify_intent -> gather_transfer_details)
        "I want to transfer some money",
        
        # Provide transfer details (source, destination, amount)
        "From my savings account",
        "To account number 9876",
        "Transfer $500",
        
        # Confirm transfer (confirm_action -> executing_transaction)
        "No, I've changed my mind",
        
        # Return to main menu and exit (main_menu -> ending_interaction)
        "I want to exit",
        
        # End interaction (ending_interaction -> idle)
        "Thank you"
    ]
    
    # Run the simulation
    await simulate_conversation(fsm, sample_conversation)
    
    # Show an error scenario
    print("\n===== Error Handling Scenario =====\n")
    
    error_conversation = [
        # Start conversation (idle -> greeting -> authenticating)
        "Hello",
        
        # Failed authentication (authenticating -> authentication_failed)
        "I don't remember my details",
        
        # End session (authentication_failed -> ending_interaction -> idle)
        "I'll try later"
    ]
    
    await simulate_conversation(fsm, error_conversation)
    
    # Show ambiguous input scenario
    print("\n===== Ambiguous Input Scenario =====\n")
    
    ambiguous_conversation = [
        # Start conversation (idle -> greeting -> authenticating)
        "Hi there",
        
        # Authentication (authenticating -> main_menu)
        "Account 5555 PIN 9999",
        
        # Unclear intent (main_menu -> identify_intent -> clarification_needed)
        "I need to do something with my money",
        
        # Clarify intent (clarification_needed -> identify_intent -> gather_bill_pay_details)
        "I want to pay a bill",
        
        # Provide bill details
        "Electric company",
        "From checking",
        "$75.50",
        
        # Confirm and execute (confirm_action -> executing_transaction -> reporting_success)
        "Yes, that's correct",
        "",
        
        # Exit (reporting_success -> ending_interaction -> idle)
        "Log out please"
    ]
    
    await simulate_conversation(fsm, ambiguous_conversation)


if __name__ == "__main__":
    asyncio.run(main()) 