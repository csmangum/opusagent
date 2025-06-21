from typing import Any, Dict

from opusagent.config.constants import VOICE
from opusagent.models.openai_api import SessionConfig
from opusagent.models.tool_models import (
    HumanHandoffTool,
    OpenAITool,
    ToolParameter,
    ToolParameters,
)

#! Need to define and register function for each tool
#! remove call_intent tool, not needed

SESSION_PROMPT = """
You are a customer service agent handling a call from a customer.

You must determine the intent of the call and call the appropriate function based on the intent.

The intent of the call can be one of the following:
* Card Replacement --> call the `process_replacement` function
* Account Inquiry --> call the `get_balance` function
* Account Management --> call the `transfer_funds` function
* Transaction Dispute --> call the `call_intent` function
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


class CallIntentParameters(ToolParameters):
    """Parameters for the call_intent function."""

    type: str = "object"
    properties: Dict[str, ToolParameter] = {
        "intent": ToolParameter(
            type="string",
            enum=[
                "Card Replacement",
                "Account Inquiry",
                "Account Management",
                "Transaction Dispute",
                "Other",
            ],
            description="The determined intent of the call",
        ),
        "confidence": ToolParameter(
            type="number",
            description="Confidence level in the intent determination (0-1)",
        ),
        "additional_context": ToolParameter(
            type="string", description="Any additional context about the call"
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


class CallIntentTool(OpenAITool):
    """Tool for determining call intent."""

    name: str = "call_intent"
    description: str = "Determine the intent of the customer's call."
    parameters: CallIntentParameters = CallIntentParameters()


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
        CallIntentTool(),
        HumanHandoffTool(),
    ]
    return [tool.model_dump() for tool in tools]


# ==============================
# Session Config
# ==============================

TOOLS = get_customer_service_tools()

session_config = SessionConfig(
    model="gpt-4o-realtime-preview-2025-06-03",
    input_audio_format="pcm16",
    output_audio_format="pcm16",
    voice=VOICE,
    instructions=SESSION_PROMPT,
    modalities=["text", "audio"],
    temperature=0.8,
    tools=TOOLS,
    input_audio_noise_reduction={"type": "near_field"},
    input_audio_transcription={"model": "whisper-1"},
    max_response_output_tokens=4096,
    tool_choice="auto",
)
