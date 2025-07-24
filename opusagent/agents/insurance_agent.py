import logging
import uuid
from typing import Any, Dict

from opusagent.config import get_config
from opusagent.config.logging_config import configure_logging

# Get voice constant from centralized config
VOICE = "verse"  # This is the default voice setting
from opusagent.models.openai_api import SessionConfig
from opusagent.models.tool_models import (
    HumanHandoffTool,
    OpenAITool,
    ToolParameter,
    ToolParameters,
)

logger = configure_logging("insurance_agent")

SESSION_PROMPT = """
You are an insurance customer service agent handling a call from a customer.

You must determine the intent of the call and call the appropriate function based on the intent.

The intent of the call can be one of the following:
* Policy Inquiry --> call the `get_policy_info` function
* Claim Filing --> call the `file_claim` function
* Coverage Questions --> call the `check_coverage` function
* Policy Changes --> call the `update_policy` function
* Billing Issues --> call the `handle_billing` function
* Other --> call the `human_handoff` function

If the call is for another reason or the caller ever asks to speak to a human, call the `human_handoff` function.

Start by greeting the customer: "Thank you for calling our insurance company, how can I help you today?"
"""

# ==============================
# Tool Parameters
# ==============================


class FileClaimParameters(ToolParameters):
    """Parameters for the file_claim function."""

    type: str = "object"
    properties: Dict[str, ToolParameter] = {
        "policy_number": ToolParameter(
            type="string", description="Customer's policy number"
        ),
        "claim_type": ToolParameter(
            type="string",
            enum=["Auto", "Home", "Health", "Life", "Other"],
            description="Type of insurance claim",
        ),
        "incident_date": ToolParameter(
            type="string", description="Date of the incident (YYYY-MM-DD)"
        ),
        "description": ToolParameter(
            type="string", description="Detailed description of the incident"
        ),
        "estimated_damage": ToolParameter(
            type="number", description="Estimated dollar amount of damage"
        ),
    }


class GetPolicyInfoParameters(ToolParameters):
    """Parameters for the get_policy_info function."""

    type: str = "object"
    properties: Dict[str, ToolParameter] = {
        "policy_number": ToolParameter(
            type="string", description="Customer's policy number"
        ),
        "include_coverage": ToolParameter(
            type="boolean",
            description="Whether to include coverage details",
            default=True,
        ),
    }


class CheckCoverageParameters(ToolParameters):
    """Parameters for the check_coverage function."""

    type: str = "object"
    properties: Dict[str, ToolParameter] = {
        "policy_number": ToolParameter(
            type="string", description="Customer's policy number"
        ),
        "coverage_type": ToolParameter(
            type="string",
            enum=["Auto", "Home", "Health", "Life", "Liability", "Property"],
            description="Type of coverage to check",
        ),
        "specific_incident": ToolParameter(
            type="string", description="Specific incident or situation to check coverage for"
        ),
    }


class UpdatePolicyParameters(ToolParameters):
    """Parameters for the update_policy function."""

    type: str = "object"
    properties: Dict[str, ToolParameter] = {
        "policy_number": ToolParameter(
            type="string", description="Customer's policy number"
        ),
        "update_type": ToolParameter(
            type="string",
            enum=["Address", "Vehicle", "Coverage", "Beneficiary", "Payment"],
            description="Type of policy update",
        ),
        "new_value": ToolParameter(
            type="string", description="New value for the policy update"
        ),
    }


class HandleBillingParameters(ToolParameters):
    """Parameters for the handle_billing function."""

    type: str = "object"
    properties: Dict[str, ToolParameter] = {
        "policy_number": ToolParameter(
            type="string", description="Customer's policy number"
        ),
        "billing_issue": ToolParameter(
            type="string",
            enum=["Payment", "Late Fee", "Premium Increase", "Billing Error", "Payment Method"],
            description="Type of billing issue",
        ),
        "amount": ToolParameter(
            type="number", description="Amount in question (if applicable)"
        ),
    }


# ==============================
# Tools
# ==============================


class FileClaimTool(OpenAITool):
    """Tool for filing insurance claims."""

    name: str = "file_claim"
    description: str = "File a new insurance claim for the customer."
    parameters: FileClaimParameters = FileClaimParameters()


class GetPolicyInfoTool(OpenAITool):
    """Tool for getting policy information."""

    name: str = "get_policy_info"
    description: str = "Get information about a customer's insurance policy."
    parameters: GetPolicyInfoParameters = GetPolicyInfoParameters()


class CheckCoverageTool(OpenAITool):
    """Tool for checking coverage details."""

    name: str = "check_coverage"
    description: str = "Check coverage details for a specific situation."
    parameters: CheckCoverageParameters = CheckCoverageParameters()


class UpdatePolicyTool(OpenAITool):
    """Tool for updating policy information."""

    name: str = "update_policy"
    description: str = "Update customer's policy information."
    parameters: UpdatePolicyParameters = UpdatePolicyParameters()


class HandleBillingTool(OpenAITool):
    """Tool for handling billing issues."""

    name: str = "handle_billing"
    description: str = "Handle billing-related issues and questions."
    parameters: HandleBillingParameters = HandleBillingParameters()


def get_insurance_tools() -> list[dict[str, Any]]:
    """
    Get all OpenAI tool definitions for insurance services.

    Returns:
        List of OpenAI function tool schemas as dictionaries
    """
    tools = [
        FileClaimTool(),
        GetPolicyInfoTool(),
        CheckCoverageTool(),
        UpdatePolicyTool(),
        HandleBillingTool(),
        HumanHandoffTool(),
    ]
    return [tool.model_dump() for tool in tools]


# ==============================
# Function Implementations
# ==============================


def func_file_claim(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulate filing an insurance claim.

    Args:
        arguments: Dictionary containing claim details

    Returns:
        Dictionary with claim filing result
    """
    policy_number = arguments.get("policy_number", "UNKNOWN")
    claim_type = arguments.get("claim_type", "Other")
    incident_date = arguments.get("incident_date", "Unknown")
    description = arguments.get("description", "No description provided")
    estimated_damage = arguments.get("estimated_damage", 0)

    claim_number = f"CLM-{uuid.uuid4().hex[:8].upper()}"
    
    result = {
        "status": "success",
        "claim_number": claim_number,
        "policy_number": policy_number,
        "claim_type": claim_type,
        "message": f"Your {claim_type.lower()} claim has been filed successfully. Your claim number is {claim_number}. A claims adjuster will contact you within 24-48 hours to discuss your claim further.",
        "next_steps": [
            "A claims adjuster will contact you within 24-48 hours",
            "Please have any relevant documentation ready",
            "You can track your claim status online or by calling our claims hotline"
        ]
    }
    
    logger.info(f"Claim filed: {claim_number} for policy {policy_number}")
    return result


def func_get_policy_info(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulate retrieving policy information.

    Args:
        arguments: Dictionary containing policy details

    Returns:
        Dictionary with policy information
    """
    policy_number = arguments.get("policy_number", "UNKNOWN")
    include_coverage = arguments.get("include_coverage", True)

    # Simulate policy data
    policy_data = {
        "policy_number": policy_number,
        "customer_name": "John Doe",
        "policy_type": "Auto & Home Bundle",
        "effective_date": "2024-01-01",
        "expiration_date": "2025-01-01",
        "premium": 125.50,
        "payment_frequency": "Monthly",
        "status": "Active"
    }
    
    if include_coverage:
        policy_data["coverage"] = {
            "auto": {
                "liability": "100,000/300,000",
                "comprehensive": "500 deductible",
                "collision": "500 deductible"
            },
            "home": {
                "dwelling": "250,000",
                "personal_property": "125,000",
                "liability": "300,000"
            }
        }

    result = {
        "status": "success",
        "policy_info": policy_data,
        "message": f"Here's your policy information. Your policy is active and covers both auto and home insurance. Your monthly premium is ${policy_data['premium']}."
    }
    
    logger.info(f"Policy info retrieved for: {policy_number}")
    return result


def func_check_coverage(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulate checking coverage for a specific situation.

    Args:
        arguments: Dictionary containing coverage check details

    Returns:
        Dictionary with coverage information
    """
    policy_number = arguments.get("policy_number", "UNKNOWN")
    coverage_type = arguments.get("coverage_type", "Auto")
    specific_incident = arguments.get("specific_incident", "General inquiry")

    # Simulate coverage check results
    coverage_results = {
        "Auto": {
            "covered": True,
            "deductible": 500,
            "coverage_limit": "100,000",
            "message": "This incident is covered under your auto policy."
        },
        "Home": {
            "covered": True,
            "deductible": 1000,
            "coverage_limit": "250,000",
            "message": "This incident is covered under your home policy."
        },
        "Health": {
            "covered": False,
            "message": "Health coverage is not included in your current policy."
        },
        "Life": {
            "covered": False,
            "message": "Life insurance coverage is not included in your current policy."
        }
    }

    coverage = coverage_results.get(coverage_type, coverage_results["Auto"])
    
    result = {
        "status": "success",
        "coverage_type": coverage_type,
        "covered": coverage["covered"],
        "deductible": coverage.get("deductible"),
        "coverage_limit": coverage.get("coverage_limit"),
        "message": coverage["message"],
        "policy_number": policy_number
    }
    
    logger.info(f"Coverage checked for {coverage_type} on policy {policy_number}")
    return result


def func_update_policy(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulate updating policy information.

    Args:
        arguments: Dictionary containing update details

    Returns:
        Dictionary with update result
    """
    policy_number = arguments.get("policy_number", "UNKNOWN")
    update_type = arguments.get("update_type", "Address")
    new_value = arguments.get("new_value", "Unknown")

    result = {
        "status": "success",
        "policy_number": policy_number,
        "update_type": update_type,
        "new_value": new_value,
        "message": f"Your policy has been updated successfully. The {update_type.lower()} has been changed to {new_value}. You'll receive a confirmation letter within 5-7 business days.",
        "effective_date": "Immediate",
        "next_billing_cycle": "No change to premium"
    }
    
    logger.info(f"Policy updated: {update_type} for policy {policy_number}")
    return result


def func_handle_billing(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulate handling billing issues.

    Args:
        arguments: Dictionary containing billing details

    Returns:
        Dictionary with billing resolution
    """
    policy_number = arguments.get("policy_number", "UNKNOWN")
    billing_issue = arguments.get("billing_issue", "Payment")
    amount = arguments.get("amount", 0)

    # Simulate billing resolutions
    billing_resolutions = {
        "Payment": {
            "resolved": True,
            "message": "Your payment has been processed successfully.",
            "next_payment": "Due in 30 days"
        },
        "Late Fee": {
            "resolved": True,
            "message": "I've waived the late fee as a courtesy. Please ensure future payments are made on time.",
            "next_payment": "Due in 30 days"
        },
        "Premium Increase": {
            "resolved": False,
            "message": "The premium increase is due to updated risk factors. I can review your policy to see if we can find ways to reduce your premium.",
            "next_payment": "Updated amount due immediately"
        },
        "Billing Error": {
            "resolved": True,
            "message": "I've corrected the billing error and credited your account.",
            "next_payment": "Due in 30 days"
        },
        "Payment Method": {
            "resolved": True,
            "message": "Your payment method has been updated successfully.",
            "next_payment": "Due in 30 days"
        }
    }

    resolution = billing_resolutions.get(billing_issue, billing_resolutions["Payment"])
    
    result = {
        "status": "success",
        "policy_number": policy_number,
        "billing_issue": billing_issue,
        "resolved": resolution["resolved"],
        "message": resolution["message"],
        "next_payment": resolution["next_payment"]
    }
    
    logger.info(f"Billing issue handled: {billing_issue} for policy {policy_number}")
    return result


def func_transfer_to_human(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transfer the call to a human agent.

    Args:
        arguments: Dictionary containing transfer details

    Returns:
        Dictionary with transfer result
    """
    reason = arguments.get("reason", "Customer requested human agent")
    
    result = {
        "status": "transfer",
        "reason": reason,
        "message": "I'm transferring you to a human agent who will be able to assist you better. Please stay on the line.",
        "estimated_wait": "2-3 minutes"
    }
    
    logger.info(f"Call transferred to human: {reason}")
    return result


# ==============================
# Function Registration
# ==============================


def register_insurance_functions(function_handler) -> None:
    """
    Register all insurance-related functions with the function handler.

    Args:
        function_handler: The function handler instance to register functions with
    """
    function_handler.register_function("file_claim", func_file_claim)
    function_handler.register_function("get_policy_info", func_get_policy_info)
    function_handler.register_function("check_coverage", func_check_coverage)
    function_handler.register_function("update_policy", func_update_policy)
    function_handler.register_function("handle_billing", func_handle_billing)
    function_handler.register_function("human_handoff", func_transfer_to_human)
    
    logger.info("Insurance functions registered successfully")


# ==============================
# Session Config
# ==============================


def get_insurance_session_config() -> SessionConfig:
    """
    Get the insurance agent session configuration.

    Returns:
        SessionConfig for insurance agent
    """
    return SessionConfig(
        model="gpt-4o-realtime-preview-2025-06-03",
        input_audio_format="pcm16",
        output_audio_format="pcm16",
        voice=VOICE,
        instructions=SESSION_PROMPT,
        modalities=["text", "audio"],
        temperature=0.6,
        tools=get_insurance_tools(),
        input_audio_noise_reduction={"type": "near_field"},
        input_audio_transcription={"model": "whisper-1"},
        max_response_output_tokens=4096,
        tool_choice="auto",
    ) 