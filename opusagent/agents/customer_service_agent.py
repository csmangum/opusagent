"""
Customer Service Agent implementation for OpusAgent.

This module provides a customer service agent that implements the BaseAgent
interface, handling customer inquiries, card replacements, account management,
and other banking-related tasks.
"""

import uuid
from typing import Dict, Any
from .base_agent import BaseAgent
from .agent_registry import register_agent
from opusagent.config.constants import VOICE
from opusagent.models.openai_api import SessionConfig
from opusagent.models.tool_models import (
    HumanHandoffTool,
    OpenAITool,
    ToolParameter,
    ToolParameters,
)


@register_agent("customer_service")
class CustomerServiceAgent(BaseAgent):
    """Customer Service Agent for handling customer inquiries and support.
    
    This agent specializes in customer service interactions, including
    card replacements, account inquiries, fund transfers, and human handoffs
    when needed.
    """

    DEFAULT_SESSION_PROMPT = """
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

    def __init__(
        self,
        name: str = "Customer Service Agent",
        role: str = "Customer Support Representative",
        specialization: str = "general",
        voice: str = VOICE,
        temperature: float = 0.8,
        max_response_output_tokens: int = 4096,
        **kwargs
    ):
        """Initialize the Customer Service Agent.
        
        Args:
            name: Agent name
            role: Agent role
            specialization: Domain specialization (general, banking, healthcare, etc.)
            voice: Voice identifier for OpenAI
            temperature: Response temperature
            max_response_output_tokens: Maximum tokens in response
            **kwargs: Additional configuration
        """
        super().__init__(name, role, **kwargs)
        
        self.specialization = specialization
        self.voice = voice
        self.temperature = temperature
        self.max_response_output_tokens = max_response_output_tokens
        
        # Customize prompt based on specialization
        self.instructions = self._get_specialized_instructions()

    def _get_specialized_instructions(self) -> str:
        """Get specialized instructions based on domain."""
        if self.specialization == "banking":
            return """
You are a banking customer service agent handling calls from bank customers.

You specialize in:
* Card Replacement --> call the `process_replacement` function
* Account Inquiry --> call the `get_balance` function
* Fund Transfers --> call the `transfer_funds` function
* Transaction Disputes --> call the `human_handoff` function
* General Banking Questions --> provide helpful information

If the call is for complex issues or the caller asks to speak to a human, call the `human_handoff` function.

Start by greeting the customer: "Thank you for calling [Bank Name], how can I help you today?"
"""
        elif self.specialization == "healthcare":
            return """
You are a healthcare customer service agent handling calls from patients and healthcare members.

You specialize in:
* Account Inquiries --> call the `get_balance` function
* Claims Questions --> call the `human_handoff` function
* Provider Information --> provide helpful information
* Appointment Scheduling --> call the `human_handoff` function

For medical questions or complex issues, always call the `human_handoff` function.

Start by greeting the customer: "Thank you for calling [Healthcare Provider], how can I help you today?"
"""
        else:
            return self.DEFAULT_SESSION_PROMPT

    @property
    def agent_type(self) -> str:
        """Return the agent type identifier."""
        return "customer_service"

    def get_session_config(self) -> SessionConfig:
        """Return the OpenAI session configuration for this agent."""
        return SessionConfig(
            model="gpt-4o-realtime-preview-2025-06-03",
            input_audio_format="pcm16",
            output_audio_format="pcm16",
            voice=self.voice,
            instructions=self.instructions,
            modalities=["text", "audio"],
            temperature=self.temperature,
            tools=self._get_tools(),
            input_audio_noise_reduction={"type": "near_field"},
            input_audio_transcription={"model": "whisper-1"},
            max_response_output_tokens=self.max_response_output_tokens,
            tool_choice="auto",
        )

    def register_functions(self, function_handler) -> None:
        """Register customer service functions with the function handler."""
        function_handler.register_function("get_balance", self._func_get_balance)
        function_handler.register_function("transfer_funds", self._func_transfer_funds)
        function_handler.register_function("process_replacement", self._func_process_replacement)
        function_handler.register_function("transfer_to_human", self._func_transfer_to_human)

    def get_agent_info(self) -> Dict[str, Any]:
        """Return metadata about the agent."""
        return {
            "name": self.name,
            "role": self.role,
            "agent_type": self.agent_type,
            "specialization": self.specialization,
            "voice": self.voice,
            "temperature": self.temperature,
            "capabilities": [
                "account_balance_inquiry",
                "fund_transfers",
                "card_replacement",
                "human_handoff"
            ],
            "tools": [tool["function"]["name"] for tool in self._get_tools()],
        }

    def _get_tools(self) -> list[dict[str, Any]]:
        """Get all OpenAI tool definitions for customer service."""
        tools = [
            ProcessReplacementTool(),
            GetBalanceTool(),
            TransferFundsTool(),
            HumanHandoffTool(),
        ]
        return [tool.model_dump() for tool in tools]

    # Function implementations
    def _func_get_balance(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate a balance lookup."""
        account_number = arguments.get("account_number", "unknown")
        include_pending = arguments.get("include_pending", True)

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

    def _func_transfer_funds(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate a fund transfer."""
        from_account = arguments.get("from_account", "unknown")
        to_account = arguments.get("to_account", "unknown")
        amount = arguments.get("amount", 0)
        transfer_type = arguments.get("transfer_type", "internal")

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

    def _func_process_replacement(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle card replacement processing."""
        card_type = arguments.get("card_type", None)
        reason = arguments.get("reason", None)
        delivery_address = arguments.get("delivery_address", None)

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

    def _func_transfer_to_human(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle transfer to human agent."""
        reason = arguments.get("reason", "general inquiry")
        priority = arguments.get("priority", "normal")
        context = arguments.get("context", {})

        transfer_id = f"TR-{uuid.uuid4().hex[:8].upper()}"

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


# Tool parameter definitions
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


# Tool definitions
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