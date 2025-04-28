"""
Bank of Peril Transitions Module

This module implements the transition logic for the Bank of Peril FSM.
It defines all possible state transitions and the conditions under which they occur.
"""
from typing import Dict, Any, List, Callable
from ..transitions.rule_based import RuleBasedTransition, Condition
from ..transitions.intent_based import IntentBasedTransition
from ..transitions.registry import TransitionRegistry


# ===================== Helper Functions for Conditions =====================

def user_initiated_conversation(context: Dict[str, Any]) -> bool:
    """Check if the user has initiated a conversation."""
    # Any input in the idle state is considered as initiating conversation
    return True

def authentication_needed(context: Dict[str, Any]) -> bool:
    """Check if authentication is needed for the requested operation."""
    # In this simple implementation, we always need authentication after greeting
    return True

def is_authenticated(context: Dict[str, Any]) -> bool:
    """Check if authentication was successful."""
    return context.get("metadata", {}).get("authenticated", False)

def authentication_failed(context: Dict[str, Any]) -> bool:
    """Check if authentication failed."""
    return not is_authenticated(context)

def wants_to_retry_auth(context: Dict[str, Any]) -> bool:
    """Check if the user wants to retry authentication."""
    last_message = get_last_user_message(context)
    if not last_message:
        return False
    
    retry_terms = ["retry", "try again", "account", "pin", "number"]
    return any(term in last_message.lower() for term in retry_terms)

def wants_to_exit(context: Dict[str, Any]) -> bool:
    """Check if the user wants to exit the conversation."""
    last_message = get_last_user_message(context)
    if not last_message:
        return False
    
    exit_terms = ["exit", "quit", "log out", "logout", "sign out", "bye", "goodbye"]
    return any(term in last_message.lower() for term in exit_terms)

def has_intent_balance(context: Dict[str, Any]) -> bool:
    """Check if the user's intent is to check account balance."""
    intent = context.get("metadata", {}).get("intent")
    if intent == "balance_inquiry":
        return True
    
    last_message = get_last_user_message(context)
    if not last_message:
        return False
    
    balance_terms = ["balance", "how much", "check account", "account balance"]
    return any(term in last_message.lower() for term in balance_terms)

def has_intent_transfer(context: Dict[str, Any]) -> bool:
    """Check if the user's intent is to transfer money."""
    intent = context.get("metadata", {}).get("intent")
    if intent == "money_transfer":
        return True
    
    last_message = get_last_user_message(context)
    if not last_message:
        return False
    
    transfer_terms = ["transfer", "send money", "move money"]
    return any(term in last_message.lower() for term in transfer_terms)

def has_intent_bill_pay(context: Dict[str, Any]) -> bool:
    """Check if the user's intent is to pay a bill."""
    intent = context.get("metadata", {}).get("intent")
    if intent == "bill_payment":
        return True
    
    last_message = get_last_user_message(context)
    if not last_message:
        return False
    
    bill_terms = ["bill", "pay", "payment"]
    return any(term in last_message.lower() for term in bill_terms)

def intent_is_unclear(context: Dict[str, Any]) -> bool:
    """Check if the user's intent is unclear."""
    return not (has_intent_balance(context) or has_intent_transfer(context) or has_intent_bill_pay(context))

def has_input(context: Dict[str, Any]) -> bool:
    """Check if there is user input to process."""
    return bool(get_last_user_message(context))

def is_returning_to_main_menu(context: Dict[str, Any]) -> bool:
    """Check if the user wants to return to the main menu."""
    last_message = get_last_user_message(context)
    if not last_message:
        return False
    
    menu_terms = ["menu", "main", "options", "back"]
    return any(term in last_message.lower() for term in menu_terms)

def details_are_collected(context: Dict[str, Any]) -> bool:
    """Check if all required details for the current operation are collected."""
    metadata = context.get("metadata", {})
    intent = metadata.get("intent")
    
    if intent == "balance_inquiry":
        return "account_type" in metadata
    elif intent == "money_transfer":
        return all(field in metadata for field in ["source_account", "destination_account", "amount"])
    elif intent == "bill_payment":
        return all(field in metadata for field in ["payee", "source_account", "amount"])
    
    return False

def wants_to_cancel(context: Dict[str, Any]) -> bool:
    """Check if the user wants to cancel the current operation."""
    last_message = get_last_user_message(context)
    if not last_message:
        return False
    
    cancel_terms = ["cancel", "stop", "back", "main menu"]
    return any(term in last_message.lower() for term in cancel_terms)

def user_confirms_action(context: Dict[str, Any]) -> bool:
    """Check if the user confirmed the action."""
    last_message = get_last_user_message(context)
    if not last_message:
        return False
    
    confirm_terms = ["yes", "yeah", "proceed", "confirm", "ok", "sure"]
    return any(term in last_message.lower() for term in confirm_terms)

def user_denies_action(context: Dict[str, Any]) -> bool:
    """Check if the user denied the action."""
    return not user_confirms_action(context)

def transaction_succeeded(context: Dict[str, Any]) -> bool:
    """Check if the transaction was successful."""
    result = context.get("metadata", {}).get("transaction_result", {})
    return result.get("success", False)

def transaction_failed(context: Dict[str, Any]) -> bool:
    """Check if the transaction failed."""
    return not transaction_succeeded(context)

def error_occurred(context: Dict[str, Any]) -> bool:
    """Check if an error occurred during processing."""
    # This would be triggered by exceptions or specific error flags in the context
    return context.get("error", False)

def get_last_user_message(context: Dict[str, Any]) -> str:
    """Helper function to get the last user message from conversation history."""
    history = context.get("conversation_history", [])
    
    for msg in reversed(history):
        if msg.get("role") == "user":
            return msg.get("content", "")
    
    return ""

def info_missing_or_ambiguous(context: Dict[str, Any]) -> bool:
    """Check if required information is missing or ambiguous."""
    # This would return true when the system can't fully understand or extract necessary information
    metadata = context.get("metadata", {})
    intent = metadata.get("intent")

    if not intent:
        return True

    if intent == "balance_inquiry" and "account_type" not in metadata:
        return True
    elif intent == "money_transfer" and not all(field in metadata for field in 
                                               ["source_account", "destination_account", "amount"]):
        return True
    elif intent == "bill_payment" and not all(field in metadata for field in 
                                             ["payee", "source_account", "amount"]):
        return True
    
    return False


# ===================== Transition Registry Creation =====================

def create_transition_registry() -> TransitionRegistry:
    """Create and configure the transition registry for Bank of Peril FSM."""
    registry = TransitionRegistry()
    
    # Create all transitions
    transitions = [
        # Idle -> Greeting
        RuleBasedTransition(
            source_state="idle",
            target_state="greeting",
            conditions=[Condition(user_initiated_conversation, "User initiates conversation")],
            priority=1,
            description="User initiates conversation"
        ),
        
        # Greeting -> Authenticating
        RuleBasedTransition(
            source_state="greeting",
            target_state="authenticating",
            conditions=[Condition(authentication_needed, "Authentication needed")],
            priority=1,
            description="Move to authentication after greeting"
        ),
        
        # Authenticating -> MainMenu
        RuleBasedTransition(
            source_state="authenticating",
            target_state="main_menu",
            conditions=[Condition(is_authenticated, "Authentication successful")],
            priority=1,
            description="Authentication successful"
        ),
        
        # Authenticating -> AuthenticationFailed
        RuleBasedTransition(
            source_state="authenticating",
            target_state="authentication_failed",
            conditions=[Condition(authentication_failed, "Authentication failed")],
            priority=1,
            description="Authentication failed"
        ),
        
        # AuthenticationFailed -> Authenticating
        RuleBasedTransition(
            source_state="authentication_failed",
            target_state="authenticating",
            conditions=[Condition(wants_to_retry_auth, "User wants to retry authentication")],
            priority=1,
            description="Retry authentication"
        ),
        
        # AuthenticationFailed -> EndingInteraction
        RuleBasedTransition(
            source_state="authentication_failed",
            target_state="ending_interaction",
            conditions=[Condition(lambda ctx: not wants_to_retry_auth(ctx), "User doesn't want to retry")],
            priority=0,
            description="End session after authentication failure"
        ),
        
        # MainMenu -> IdentifyIntent
        RuleBasedTransition(
            source_state="main_menu",
            target_state="identify_intent",
            conditions=[Condition(has_input, "User makes a request")],
            priority=1,
            description="Process user request from main menu"
        ),
        
        # MainMenu -> EndingInteraction
        RuleBasedTransition(
            source_state="main_menu",
            target_state="ending_interaction",
            conditions=[Condition(wants_to_exit, "User wants to exit")],
            priority=2,  # Higher priority to take precedence over identify_intent
            description="User chooses to exit"
        ),
        
        # IdentifyIntent -> GatherBalanceDetails
        RuleBasedTransition(
            source_state="identify_intent",
            target_state="gather_balance_details",
            conditions=[Condition(has_intent_balance, "Balance inquiry intent detected")],
            priority=2,
            description="User wants to check balance"
        ),
        
        # IdentifyIntent -> GatherTransferDetails
        RuleBasedTransition(
            source_state="identify_intent",
            target_state="gather_transfer_details",
            conditions=[Condition(has_intent_transfer, "Transfer money intent detected")],
            priority=2,
            description="User wants to transfer money"
        ),
        
        # IdentifyIntent -> GatherBillPayDetails
        RuleBasedTransition(
            source_state="identify_intent",
            target_state="gather_bill_pay_details",
            conditions=[Condition(has_intent_bill_pay, "Bill payment intent detected")],
            priority=2,
            description="User wants to pay a bill"
        ),
        
        # IdentifyIntent -> ClarificationNeeded
        RuleBasedTransition(
            source_state="identify_intent",
            target_state="clarification_needed",
            conditions=[Condition(intent_is_unclear, "Intent is unclear")],
            priority=1,
            description="User intent is unclear"
        ),
        
        # IdentifyIntent -> MainMenu
        RuleBasedTransition(
            source_state="identify_intent",
            target_state="main_menu",
            conditions=[Condition(is_returning_to_main_menu, "User wants main menu")],
            priority=3,  # Highest priority to take precedence over other intents
            description="Return to main menu"
        ),
        
        # GatherBalanceDetails -> ConfirmAction
        RuleBasedTransition(
            source_state="gather_balance_details",
            target_state="confirm_action",
            conditions=[Condition(details_are_collected, "All required details collected")],
            priority=1,
            description="Balance inquiry details collected"
        ),
        
        # GatherBalanceDetails -> MainMenu
        RuleBasedTransition(
            source_state="gather_balance_details",
            target_state="main_menu",
            conditions=[Condition(wants_to_cancel, "User cancels operation")],
            priority=2,  # Higher priority to take precedence over confirm_action
            description="Cancel balance inquiry"
        ),
        
        # GatherTransferDetails -> ConfirmAction
        RuleBasedTransition(
            source_state="gather_transfer_details",
            target_state="confirm_action",
            conditions=[Condition(details_are_collected, "All required details collected")],
            priority=1,
            description="Transfer details collected"
        ),
        
        # GatherTransferDetails -> MainMenu
        RuleBasedTransition(
            source_state="gather_transfer_details",
            target_state="main_menu",
            conditions=[Condition(wants_to_cancel, "User cancels operation")],
            priority=2,  # Higher priority to take precedence over confirm_action
            description="Cancel transfer"
        ),
        
        # GatherTransferDetails -> ClarificationNeeded
        RuleBasedTransition(
            source_state="gather_transfer_details",
            target_state="clarification_needed",
            conditions=[Condition(info_missing_or_ambiguous, "Missing or ambiguous info")],
            priority=1,  # Lower priority than cancel but equal to confirm
            description="Need clarification on transfer details"
        ),
        
        # GatherBillPayDetails -> ConfirmAction
        RuleBasedTransition(
            source_state="gather_bill_pay_details",
            target_state="confirm_action",
            conditions=[Condition(details_are_collected, "All required details collected")],
            priority=1,
            description="Bill payment details collected"
        ),
        
        # GatherBillPayDetails -> MainMenu
        RuleBasedTransition(
            source_state="gather_bill_pay_details",
            target_state="main_menu",
            conditions=[Condition(wants_to_cancel, "User cancels operation")],
            priority=2,  # Higher priority to take precedence over confirm_action
            description="Cancel bill payment"
        ),
        
        # GatherBillPayDetails -> ClarificationNeeded
        RuleBasedTransition(
            source_state="gather_bill_pay_details",
            target_state="clarification_needed",
            conditions=[Condition(info_missing_or_ambiguous, "Missing or ambiguous info")],
            priority=1,  # Lower priority than cancel but equal to confirm
            description="Need clarification on bill payment details"
        ),
        
        # ConfirmAction -> ExecutingTransaction
        RuleBasedTransition(
            source_state="confirm_action",
            target_state="executing_transaction",
            conditions=[Condition(user_confirms_action, "User confirms")],
            priority=1,
            description="User confirmed the transaction"
        ),
        
        # ConfirmAction -> MainMenu
        RuleBasedTransition(
            source_state="confirm_action",
            target_state="main_menu",
            conditions=[Condition(user_denies_action, "User cancels")],
            priority=1,
            description="User cancelled the transaction"
        ),
        
        # ExecutingTransaction -> ReportingSuccess
        RuleBasedTransition(
            source_state="executing_transaction",
            target_state="reporting_success",
            conditions=[Condition(transaction_succeeded, "Transaction succeeded")],
            priority=1,
            description="Transaction completed successfully"
        ),
        
        # ExecutingTransaction -> ReportingFailure
        RuleBasedTransition(
            source_state="executing_transaction",
            target_state="reporting_failure",
            conditions=[Condition(transaction_failed, "Transaction failed")],
            priority=1,
            description="Transaction failed"
        ),
        
        # ExecutingTransaction -> HandlingError
        RuleBasedTransition(
            source_state="executing_transaction",
            target_state="handling_error",
            conditions=[Condition(error_occurred, "Error occurred")],
            priority=2,  # Higher priority to handle errors first
            description="Error during transaction execution"
        ),
        
        # ReportingSuccess -> MainMenu
        RuleBasedTransition(
            source_state="reporting_success",
            target_state="main_menu",
            conditions=[Condition(lambda ctx: not wants_to_exit(ctx), "User wants to continue")],
            priority=1,
            description="Return to main menu after success"
        ),
        
        # ReportingSuccess -> EndingInteraction
        RuleBasedTransition(
            source_state="reporting_success",
            target_state="ending_interaction",
            conditions=[Condition(wants_to_exit, "User wants to exit")],
            priority=2,  # Higher priority to take precedence over main_menu
            description="Exit after success"
        ),
        
        # ReportingFailure -> MainMenu
        RuleBasedTransition(
            source_state="reporting_failure",
            target_state="main_menu",
            conditions=[Condition(lambda ctx: not wants_to_exit(ctx), "User wants to continue")],
            priority=1,
            description="Return to main menu after failure"
        ),
        
        # ReportingFailure -> EndingInteraction
        RuleBasedTransition(
            source_state="reporting_failure",
            target_state="ending_interaction",
            conditions=[Condition(wants_to_exit, "User wants to exit")],
            priority=2,  # Higher priority to take precedence over main_menu
            description="Exit after failure"
        ),
        
        # ClarificationNeeded -> IdentifyIntent
        RuleBasedTransition(
            source_state="clarification_needed",
            target_state="identify_intent",
            conditions=[Condition(lambda ctx: not is_returning_to_main_menu(ctx), "User provided clarification")],
            priority=1,
            description="Process clarified intent"
        ),
        
        # ClarificationNeeded -> MainMenu
        RuleBasedTransition(
            source_state="clarification_needed",
            target_state="main_menu",
            conditions=[Condition(is_returning_to_main_menu, "User wants main menu")],
            priority=2,  # Higher priority to take precedence over identify_intent
            description="Return to main menu"
        ),
        
        # HandlingError -> MainMenu
        RuleBasedTransition(
            source_state="handling_error",
            target_state="main_menu",
            conditions=[Condition(lambda ctx: not wants_to_exit(ctx), "User wants to continue")],
            priority=1,
            description="Return to main menu after error"
        ),
        
        # HandlingError -> EndingInteraction
        RuleBasedTransition(
            source_state="handling_error",
            target_state="ending_interaction",
            conditions=[Condition(wants_to_exit, "User wants to exit")],
            priority=2,  # Higher priority to take precedence over main_menu
            description="Exit after error"
        ),
        
        # EndingInteraction -> Idle
        RuleBasedTransition(
            source_state="ending_interaction",
            target_state="idle",
            conditions=[Condition(lambda ctx: True, "Session ended")],
            priority=1,
            description="Reset to idle for new session"
        )
    ]
    
    # Register all transitions with the registry
    for transition in transitions:
        registry.register_transition(transition)
    
    return registry


# Get the configured transition registry
transition_registry = create_transition_registry()
