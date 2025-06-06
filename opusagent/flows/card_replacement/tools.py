"""
Card Replacement Flow Tools

OpenAI function tool definitions for the card replacement conversation flow.
"""

from typing import Any, Dict, List

# Tool definition for intent identification
CALL_INTENT_TOOL = {
    "type": "function",
    "name": "call_intent",
    "description": "Get the user's intent and any additional context they provide upfront (like card type, reason for replacement, etc.).",
    "parameters": {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "enum": ["card_replacement", "account_inquiry", "other"],
            },
            "card_type": {
                "type": "string",
                "description": "Type of card mentioned (e.g., 'Gold card', 'Silver card', 'Basic card') - only if explicitly mentioned",
            },
            "replacement_reason": {
                "type": "string",
                "enum": ["Lost", "Damaged", "Stolen", "Other"],
                "description": "Reason for replacement - only if explicitly mentioned",
            },
            "additional_context": {
                "type": "string",
                "description": "Any other relevant context provided by the customer",
            },
        },
        "required": ["intent"],
    },
}

# Tool definition for member account confirmation
MEMBER_ACCOUNT_CONFIRMATION_TOOL = {
    "type": "function",
    "name": "member_account_confirmation",
    "description": "Confirm which member account/card needs replacement.",
    "parameters": {
        "type": "object",
        "properties": {
            "member_accounts": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of available member accounts/cards",
            },
            "organization_name": {"type": "string"},
        },
    },
}

# Tool definition for replacement reason collection
REPLACEMENT_REASON_TOOL = {
    "type": "function",
    "name": "replacement_reason",
    "description": "Collect the reason for card replacement.",
    "parameters": {
        "type": "object",
        "properties": {
            "card_in_context": {"type": "string"},
            "reason": {
                "type": "string",
                "enum": ["Lost", "Damaged", "Stolen", "Other"],
            },
        },
    },
}

# Tool definition for address confirmation
CONFIRM_ADDRESS_TOOL = {
    "type": "function",
    "name": "confirm_address",
    "description": "Confirm the address for card delivery.",
    "parameters": {
        "type": "object",
        "properties": {
            "card_in_context": {"type": "string"},
            "address_on_file": {"type": "string"},
            "confirmed_address": {"type": "string"},
        },
    },
}

# Tool definition for starting card replacement
START_CARD_REPLACEMENT_TOOL = {
    "type": "function",
    "name": "start_card_replacement",
    "description": "Start the card replacement process.",
    "parameters": {
        "type": "object",
        "properties": {
            "card_in_context": {"type": "string"},
            "address_in_context": {"type": "string"},
        },
    },
}

# Tool definition for finishing card replacement
FINISH_CARD_REPLACEMENT_TOOL = {
    "type": "function",
    "name": "finish_card_replacement",
    "description": "Finish the card replacement process and provide delivery information.",
    "parameters": {
        "type": "object",
        "properties": {
            "card_in_context": {"type": "string"},
            "address_in_context": {"type": "string"},
            "delivery_time": {"type": "string"},
        },
    },
}

# Tool definition for wrapping up the call
WRAP_UP_TOOL = {
    "type": "function",
    "name": "wrap_up",
    "description": "Wrap up the call with closing remarks.",
    "parameters": {
        "type": "object",
        "properties": {"organization_name": {"type": "string"}},
    },
}

# Tool definition for transferring to human
TRANSFER_TO_HUMAN_TOOL = {
    "type": "function",
    "name": "transfer_to_human",
    "description": "Transfer the conversation to a human agent.",
    "parameters": {
        "type": "object",
        "properties": {
            "reason": {
                "type": "string",
                "description": "The reason for transferring to a human agent",
            },
            "priority": {
                "type": "string",
                "enum": ["low", "normal", "high"],
                "description": "The priority level of the transfer",
            },
            "context": {
                "type": "object",
                "description": "Additional context to pass to the human agent",
            },
        },
        "required": ["reason"],
    },
}


def get_card_replacement_tools() -> List[Dict[str, Any]]:
    """
    Get all OpenAI tool definitions for the card replacement flow.
    
    Returns:
        List of OpenAI function tool schemas
    """
    return [
        CALL_INTENT_TOOL,
        MEMBER_ACCOUNT_CONFIRMATION_TOOL,
        REPLACEMENT_REASON_TOOL,
        CONFIRM_ADDRESS_TOOL,
        START_CARD_REPLACEMENT_TOOL,
        FINISH_CARD_REPLACEMENT_TOOL,
        WRAP_UP_TOOL,
        TRANSFER_TO_HUMAN_TOOL,
    ]


def get_tool_by_name(tool_name: str) -> Dict[str, Any]:
    """
    Get a specific tool definition by name.
    
    Args:
        tool_name: Name of the tool to retrieve
        
    Returns:
        Tool definition dictionary
        
    Raises:
        ValueError: If tool name is not found
    """
    tool_map = {
        "call_intent": CALL_INTENT_TOOL,
        "member_account_confirmation": MEMBER_ACCOUNT_CONFIRMATION_TOOL,
        "replacement_reason": REPLACEMENT_REASON_TOOL,
        "confirm_address": CONFIRM_ADDRESS_TOOL,
        "start_card_replacement": START_CARD_REPLACEMENT_TOOL,
        "finish_card_replacement": FINISH_CARD_REPLACEMENT_TOOL,
        "wrap_up": WRAP_UP_TOOL,
        "transfer_to_human": TRANSFER_TO_HUMAN_TOOL,
    }
    
    if tool_name not in tool_map:
        available_tools = list(tool_map.keys())
        raise ValueError(f"Tool '{tool_name}' not found. Available tools: {available_tools}")
    
    return tool_map[tool_name] 