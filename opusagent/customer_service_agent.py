import logging
import uuid
from typing import Any, Dict

from opusagent.config.constants import VOICE
from opusagent.config.logging_config import configure_logging
from opusagent.models.openai_api import SessionConfig
from opusagent.models.tool_models import (
    HumanHandoffTool,
    OpenAITool,
    ToolParameter,
    ToolParameters,
)

logger = configure_logging("customer_service_agent")

SESSION_PROMPT = """
You are a customer service agent handling a call from a customer.

You must determine the intent of the call and call the appropriate function based on the intent.

The intent of the call can be one of the following:
* Card Replacement --> call the `process_replacement` function
* Account Inquiry --> call the `get_balance` function
* Account Management --> call the `transfer_funds` function
* Transaction Dispute --> call the `human_handoff` function
* Other --> call the `human_handoff` function

If the call is for another reason or the caller ever asks to speak to a human, call the `human_handoff` function.

Start by greeting the customer: "Thank you for calling, how can I help you today?"
"""

# ==============================
# Tool Parameters
# ==============================


class ProcessReplacementParameters(ToolParameters):
    """Parameters for the process_replacement function."""

    type: str = "object"
    properties: Dict[str, ToolParameter] = {
        "card_type": ToolParameter(
            type="string", description="Type of card that needs replacement"
        ),
        "reason": ToolParameter(
            type="string",
            enum=["Lost", "Damaged", "Stolen", "Other"],
            description="Reason for card replacement",
        ),
        "delivery_address": ToolParameter(
            type="string", description="Address for card delivery"
        ),
    }


class GetBalanceParameters(ToolParameters):
    """Parameters for the get_balance function."""

    type: str = "object"
    properties: Dict[str, ToolParameter] = {
        "account_number": ToolParameter(
            type="string", description="Customer's account number"
        ),
        "include_pending": ToolParameter(
            type="boolean",
            description="Whether to include pending transactions",
            default=True,
        ),
    }


class TransferFundsParameters(ToolParameters):
    """Parameters for the transfer_funds function."""

    type: str = "object"
    properties: Dict[str, ToolParameter] = {
        "from_account": ToolParameter(
            type="string", description="Source account number"
        ),
        "to_account": ToolParameter(
            type="string", description="Destination account number"
        ),
        "amount": ToolParameter(type="number", description="Amount to transfer"),
        "transfer_type": ToolParameter(
            type="string",
            enum=["internal", "external", "wire"],
            description="Type of transfer",
        ),
    }


# ==============================
# Tools
# ==============================


class ProcessReplacementTool(OpenAITool):
    """Tool for processing card replacement requests."""

    name: str = "process_replacement"
    description: str = "Process a card replacement request for the customer."
    parameters: ProcessReplacementParameters = ProcessReplacementParameters()


class GetBalanceTool(OpenAITool):
    """Tool for getting account balance."""

    name: str = "get_balance"
    description: str = "Get the current balance for a customer's account."
    parameters: GetBalanceParameters = GetBalanceParameters()


class TransferFundsTool(OpenAITool):
    """Tool for transferring funds between accounts."""

    name: str = "transfer_funds"
    description: str = "Transfer funds between customer accounts."
    parameters: TransferFundsParameters = TransferFundsParameters()


def get_customer_service_tools() -> list[dict[str, Any]]:
    """
    Get all OpenAI tool definitions for customer service.

    Returns:
        List of OpenAI function tool schemas as dictionaries
    """
    tools = [
        ProcessReplacementTool(),
        GetBalanceTool(),
        TransferFundsTool(),
        HumanHandoffTool(),
    ]
    return [tool.model_dump() for tool in tools]


# ==============================
# Function Implementations
# ==============================


def func_get_balance(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulate a balance lookup.

    Args:
        arguments: Function arguments containing account information

    Returns:
        Simulated balance information
    """
    account_number = arguments.get("account_number", "unknown")
    include_pending = arguments.get("include_pending", True)

    logger.info(
        f"Balance lookup for account {account_number}, include_pending: {include_pending}"
    )

    return {
        "status": "success",
        "balance": 1234.56,
        "currency": "USD",
        "account_number": account_number,
        "pending_transactions": include_pending,
        "context": {
            "stage": "balance_inquiry",
            "account_number": account_number,
        },
    }


def func_transfer_funds(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulate a fund transfer.

    Args:
        arguments: Function arguments containing transfer details

    Returns:
        Transfer status information
    """
    from_account = arguments.get("from_account", "unknown")
    to_account = arguments.get("to_account", "unknown")
    amount = arguments.get("amount", 0)
    transfer_type = arguments.get("transfer_type", "internal")

    logger.info(
        f"Fund transfer: ${amount} from {from_account} to {to_account} ({transfer_type})"
    )

    return {
        "status": "success",
        "amount": amount,
        "from_account": from_account,
        "to_account": to_account,
        "transfer_type": transfer_type,
        "transaction_id": f"TX-{uuid.uuid4().hex[:8].upper()}",
        "context": {
            "stage": "transfer_complete",
            "amount": amount,
            "transfer_type": transfer_type,
        },
    }



def func_process_replacement(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle card replacement processing.

    Args:
        arguments: Function arguments containing card replacement details

    Returns:
        Formatted prompt and guidance for card replacement
    """
    card_type = arguments.get("card_type", None)
    reason = arguments.get("reason", None)
    delivery_address = arguments.get("delivery_address", None)

    # Generate a replacement reference number
    replacement_id = f"CR-{uuid.uuid4().hex[:8].upper()}"
    
    if card_type is None:
        prompt_guidance = "Ask the customer which type of card they need to replace: Gold card, Silver card, or Basic card."
        next_action = "ask_card_type"
    elif reason is None:
        prompt_guidance = "Ask the customer why they need to replace their card."
        next_action = "ask_reason"
    elif delivery_address is None:
        prompt_guidance = "Ask the customer where they want their replacement card delivered."
        next_action = "ask_delivery_address"
    else:
        prompt_guidance = f"Your {card_type} replacement has been processed. Your replacement ID is {replacement_id}. The new card will be delivered to {delivery_address} within 5-7 business days."
        next_action = "wrap_up"

    return {
        "status": "success",
        "function_name": "process_replacement",
        "prompt_guidance": prompt_guidance,
        "next_action": next_action,
        "context": {
            "stage": "replacement_processing",
            "card_type": card_type,
            "reason": reason,
            "delivery_address": delivery_address,
            "replacement_id": replacement_id,
        },
    }


def func_transfer_to_human(arguments: Dict[str, Any]) -> Dict[str, Any]:
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
        "next_action": "end_call",
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


def register_customer_service_functions(function_handler) -> None:
    """
    Register all customer service functions with the function handler.

    Args:
        function_handler: The FunctionHandler instance to register functions with
    """
    logger.info("Registering customer service functions with function handler")

    function_handler.register_function("get_balance", func_get_balance)
    function_handler.register_function("transfer_funds", func_transfer_funds)
    function_handler.register_function("process_replacement", func_process_replacement)
    function_handler.register_function("transfer_to_human", func_transfer_to_human)

    logger.info("Customer service functions registered successfully")


# ==============================
# Session Config
# ==============================

TOOLS = get_customer_service_tools()

session_config = SessionConfig(
    model="gpt-4o-realtime-preview-2025-06-03",
    input_audio_format="pcm16",
    output_audio_format="pcm16",
    voice=VOICE,  # CS agent uses "verse" voice
    instructions=SESSION_PROMPT,
    modalities=["text", "audio"],
    temperature=0.6,  # Minimum allowed by API, reduced from 0.8 for consistency
    tools=TOOLS,
    input_audio_noise_reduction={"type": "near_field"},
    input_audio_transcription={"model": "whisper-1"},
    max_response_output_tokens=4096,
    tool_choice="auto",  # Keep as auto since "required" is not supported in SessionConfig
)
