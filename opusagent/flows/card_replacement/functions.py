"""
Card Replacement Flow Functions

Function implementations for the card replacement conversation flow.
"""

import logging
import uuid
from collections import OrderedDict
from typing import Any, Dict

from .prompts import (
    CONFIRM_ADDRESS_PROMPT,
    FINISH_CARD_REPLACEMENT_PROMPT,
    MEMBER_ACCOUNT_CONFIRMATION_PROMPT,
    REPLACEMENT_REASON_PROMPT,
    START_CARD_REPLACEMENT_PROMPT,
    WRAP_UP_PROMPT,
)

logger = logging.getLogger(__name__)


def call_intent(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process user intent identification and capture any additional context provided upfront.

    Args:
        arguments: Function arguments containing intent and optional context

    Returns:
        Intent processing results with guidance for next actions based on provided context
    """
    intent = arguments.get("intent", "")
    card_type = arguments.get("card_type", "")
    replacement_reason = arguments.get("replacement_reason", "")
    additional_context = arguments.get("additional_context", "")

    # Prompt guidance should ideally be imported from a centralized module for consistency and maintainability.

    if intent == "card_replacement":
        logger.info(f"Card replacement intent identified with context: {arguments}")

        # Determine next action based on what context was already provided
        captured_info = []
        next_action = "ask_card_type"  #! is this really needed
        prompt_guidance = "Ask the customer which type of card they need to replace: Gold card, Silver card, or Basic card."

        # Check what information we already have
        if card_type:
            captured_info.append(f"card_type: {card_type}")
            if replacement_reason:
                captured_info.append(f"reason: {replacement_reason}")
                next_action = "confirm_address"
                prompt_guidance = f"Could you please confirm the address where you would like the new {card_type} to be delivered?"
            else:
                next_action = "ask_reason"
                prompt_guidance = f"Could you please let me know the reason for replacing your {card_type}? Is it Lost, Damaged, Stolen, or Other?"
        elif replacement_reason:
            captured_info.append(f"reason: {replacement_reason}")
            next_action = "ask_card_type_with_reason"
            prompt_guidance = f"Which type of card do you need to replace?"

        return {
            "status": "success",
            "intent": intent,
            "next_action": next_action,
            "available_cards": ["Gold card", "Silver card", "Basic card"], #! this will be dynamic per customer
            "prompt_guidance": prompt_guidance,
            "captured_context": {
                "card_type": card_type,
                "replacement_reason": replacement_reason,
                "additional_context": additional_context,
                "captured_info": captured_info,
            },
        }
    else:
        return {
            "status": "success",
            "intent": intent,
            "next_action": "continue_conversation",
        }


def member_account_confirmation(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle member account confirmation for card replacement.

    Args:
        arguments: Function arguments containing member accounts and context

    Returns:
        Formatted prompt and guidance for account confirmation
    """
    member_accounts = arguments.get(
        "member_accounts", ["Gold card", "Silver card", "Basic card"] #! this will be dynamic per customer
    )
    organization_name = arguments.get("organization_name", "Bank of Peril")

    # Check if a specific card was already mentioned/captured
    specific_card = arguments.get("card_in_context", "")

    if specific_card:
        # Card already identified, proceed to next step
        formatted_prompt = f"Could you please let me know the reason for replacing your {specific_card}? Is it Lost, Damaged, Stolen, or Other?"
        next_action = "ask_reason"
    else:
        # Format the prompt with context for card selection
        formatted_prompt = MEMBER_ACCOUNT_CONFIRMATION_PROMPT.format(
            member_accounts=", ".join(member_accounts)
        )
        next_action = "confirm_card_selection"

    logger.info(
        f"Member account confirmation function called with accounts: {member_accounts}, specific_card: {specific_card}"
    )

    return {
        "status": "success",
        "function_name": "member_account_confirmation",
        "prompt_guidance": formatted_prompt,
        "next_action": next_action,
        "available_cards": member_accounts,
        "confirmed_card": specific_card,
        "context": {
            "stage": "account_confirmation",
            "organization_name": organization_name,
            "card_in_context": specific_card,
        },
    }


def replacement_reason(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle replacement reason collection.

    Args:
        arguments: Function arguments containing card context and selected reason

    Returns:
        Formatted prompt and guidance for reason collection
    """
    card_in_context = arguments.get("card_in_context", "your card")
    reason = arguments.get("reason", "")

    # Format the prompt with context
    formatted_prompt = REPLACEMENT_REASON_PROMPT.format(card_in_context=card_in_context)

    logger.info(
        f"Replacement reason function called for {card_in_context}, reason: {reason}"
    )

    return {
        "status": "success",
        "function_name": "replacement_reason",
        "prompt_guidance": formatted_prompt,
        "next_action": "collect_address" if reason else "ask_reason",
        "valid_reasons": ["Lost", "Damaged", "Stolen", "Other"],
        "selected_reason": reason,
        "context": {
            "stage": "reason_collection",
            "card_in_context": card_in_context,
            "reason": reason,
        },
    }


def confirm_address(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle address confirmation for card replacement.

    Args:
        arguments: Function arguments containing card context and address

    Returns:
        Formatted prompt and guidance for address confirmation
    """
    card_in_context = arguments.get("card_in_context", "your card")
    address_on_file = arguments.get("address_on_file", "123 Main St, Anytown, ST 12345")
    confirmed_address = arguments.get("confirmed_address", "")

    # Format the prompt with context
    formatted_prompt = CONFIRM_ADDRESS_PROMPT.format(
        card_in_context=card_in_context, address_on_file=address_on_file
    )
    logger.info(f"!!!! Formatted prompt: {formatted_prompt}")    

    logger.info(f"Address confirmation function called for {card_in_context}")

    return {
        "status": "success",
        "function_name": "confirm_address",
        "prompt_guidance": formatted_prompt,
        "next_action": "start_replacement" if confirmed_address else "confirm_address",
        "address_on_file": address_on_file,
        "confirmed_address": confirmed_address,
        "context": {
            "stage": "address_confirmation",
            "card_in_context": card_in_context,
            "address_on_file": address_on_file,
            "confirmed_address": confirmed_address,
        },
    }


def start_card_replacement(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle starting the card replacement process.

    Args:
        arguments: Function arguments containing card and address context

    Returns:
        Formatted prompt and guidance for starting replacement
    """
    card_in_context = arguments.get("card_in_context", "your card")
    address_in_context = arguments.get("address_in_context", "your address on file")

    # Format the prompt with context
    formatted_prompt = START_CARD_REPLACEMENT_PROMPT.format(
        card_in_context=card_in_context, address_in_context=address_in_context
    )

    logger.info(
        f"Starting card replacement for {card_in_context} to {address_in_context}"
    )

    return {
        "status": "success",
        "function_name": "start_card_replacement",
        "prompt_guidance": formatted_prompt,
        "next_action": "finish_replacement",
        "context": {
            "stage": "replacement_started",
            "card_in_context": card_in_context,
            "address_in_context": address_in_context,
        },
    }


def finish_card_replacement(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle finishing the card replacement process.

    Args:
        arguments: Function arguments containing card and address context

    Returns:
        Formatted prompt and guidance for finishing replacement
    """
    card_in_context = arguments.get("card_in_context", "your card")
    address_in_context = arguments.get("address_in_context", "your address")
    delivery_time = arguments.get("delivery_time", "5-7 business days")

    # Format the prompt with context
    formatted_prompt = FINISH_CARD_REPLACEMENT_PROMPT.format(
        card_in_context=card_in_context, address_in_context=address_in_context
    )

    logger.info(f"Finishing card replacement for {card_in_context}")

    return {
        "status": "success",
        "function_name": "finish_card_replacement",
        "prompt_guidance": formatted_prompt,
        "next_action": "wrap_up",
        "delivery_time": delivery_time,
        "context": {
            "stage": "replacement_complete",
            "card_in_context": card_in_context,
            "address_in_context": address_in_context,
            "delivery_time": delivery_time,
        },
    }


def wrap_up(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle wrapping up the call.

    Args:
        arguments: Function arguments containing organization context

    Returns:
        Formatted prompt and guidance for wrapping up
    """
    organization_name = arguments.get("organization_name", "Bank of Peril")

    # Format the prompt with context
    formatted_prompt = WRAP_UP_PROMPT.format(organization_name=organization_name)

    logger.info(f"Wrapping up call for {organization_name}")

    return {
        "status": "success",
        "function_name": "wrap_up",
        "prompt_guidance": formatted_prompt,
        "next_action": "end_call",
        "context": {"stage": "call_complete", "organization_name": organization_name},
    }


def transfer_to_human(arguments: Dict[str, Any]) -> Dict[str, Any]:
    #! validate this function
    """
    Handle transfer to human agent.

    Args:
        arguments: Function arguments containing transfer context and reason

    Returns:
        Formatted prompt and guidance for human transfer
    """
    reason = arguments.get("reason", "general inquiry")
    priority = arguments.get("priority", "normal")
    context = arguments.get("context", {})

    # Log the transfer request
    logger.info(f"Transfer to human requested. Reason: {reason}, Priority: {priority}")

    # Generate a transfer reference number
    transfer_id = f"TR-{uuid.uuid4().hex[:8].upper()}"

    # Format the transfer message
    transfer_message = (
        f"I understand you'd like to speak with a human agent regarding {reason}. "
        f"I'll transfer you now. Your reference number is {transfer_id}. "
        f"Please hold while I connect you with a representative."
    )

    return {
        "status": "success",
        "function_name": "transfer_to_human",
        "prompt_guidance": transfer_message,
        "next_action": "end_conversation",
        "transfer_id": transfer_id,
        "priority": priority,
        "context": {
            "stage": "human_transfer",
            "reason": reason,
            "priority": priority,
            "transfer_id": transfer_id,
            **context,
        },
    }


# Function registry mapping for easy access
CARD_REPLACEMENT_FUNCTIONS = OrderedDict(
    [
        ("call_intent", call_intent),
        ("member_account_confirmation", member_account_confirmation),
        ("replacement_reason", replacement_reason),
        ("confirm_address", confirm_address),
        ("start_card_replacement", start_card_replacement),
        ("finish_card_replacement", finish_card_replacement),
        ("wrap_up", wrap_up),
        ("transfer_to_human", transfer_to_human),
    ]
)


def get_card_replacement_functions() -> Dict[str, Any]:
    """
    Get all function implementations for the card replacement flow.

    Returns:
        Dictionary mapping function names to callable implementations
    """
    return CARD_REPLACEMENT_FUNCTIONS.copy()


def get_function_by_name(function_name: str):
    """
    Get a specific function implementation by name.

    Args:
        function_name: Name of the function to retrieve

    Returns:
        Function implementation

    Raises:
        ValueError: If function name is not found
    """
    if function_name not in CARD_REPLACEMENT_FUNCTIONS:
        available_functions = list(CARD_REPLACEMENT_FUNCTIONS.keys())
        raise ValueError(
            f"Function '{function_name}' not found. Available functions: {available_functions}"
        )

    return CARD_REPLACEMENT_FUNCTIONS[function_name]
