"""
Card Replacement Flow

Main flow class that orchestrates the card replacement conversation flow.
"""

from typing import Any, Callable, Dict, List

from ..base_flow import BaseFlow
from .tools import get_card_replacement_tools
from .functions import get_card_replacement_functions
from .prompts import (
    BASE_PROMPT,
    MEMBER_ACCOUNT_CONFIRMATION_PROMPT,
    REPLACEMENT_REASON_PROMPT,
    CONFIRM_ADDRESS_PROMPT,
    START_CARD_REPLACEMENT_PROMPT,
    FINISH_CARD_REPLACEMENT_PROMPT,
    WRAP_UP_PROMPT,
    SYSTEM_INSTRUCTION,
)


class CardReplacementFlow(BaseFlow):
    """
    Card replacement conversation flow implementation.
    
    This flow handles the complete card replacement process including:
    - Intent identification
    - Member account confirmation
    - Replacement reason collection
    - Address confirmation
    - Process initiation and completion
    - Call wrap-up
    """

    def __init__(self):
        """Initialize the card replacement flow."""
        super().__init__("card_replacement")

    def get_tools(self) -> List[Dict[str, Any]]:
        """
        Get the OpenAI tool definitions for this flow.
        
        Returns:
            List of OpenAI function tool schemas
        """
        return get_card_replacement_tools()

    def get_functions(self) -> Dict[str, Callable]:
        """
        Get the function implementations for this flow.
        
        Returns:
            Dictionary mapping function names to callable implementations
        """
        return get_card_replacement_functions()

    def get_prompts(self) -> Dict[str, str]:
        """
        Get the prompts used in this flow.
        
        Returns:
            Dictionary mapping prompt names to prompt templates
        """
        return {
            "base_prompt": BASE_PROMPT,
            "member_account_confirmation": MEMBER_ACCOUNT_CONFIRMATION_PROMPT,
            "replacement_reason": REPLACEMENT_REASON_PROMPT,
            "confirm_address": CONFIRM_ADDRESS_PROMPT,
            "start_card_replacement": START_CARD_REPLACEMENT_PROMPT,
            "finish_card_replacement": FINISH_CARD_REPLACEMENT_PROMPT,
            "wrap_up": WRAP_UP_PROMPT,
            "system_instruction": SYSTEM_INSTRUCTION,
        }

    def get_system_instruction(self) -> str:
        """
        Get the system instruction that should be added for this flow.
        
        Returns:
            System instruction text
        """
        return SYSTEM_INSTRUCTION

    def get_flow_stages(self) -> List[str]:
        """
        Get the ordered list of stages in this flow.
        
        Returns:
            List of stage names in order
        """
        return [
            "intent_identification",
            "account_confirmation", 
            "reason_collection",
            "address_confirmation",
            "replacement_started",
            "replacement_complete",
            "call_complete"
        ]

    def get_stage_info(self, stage: str) -> Dict[str, Any]:
        """
        Get information about a specific stage in the flow.
        
        Args:
            stage: Stage name
            
        Returns:
            Dictionary containing stage information
            
        Raises:
            ValueError: If stage name is not found
        """
        stage_info = {
            "intent_identification": {
                "description": "Identify that customer wants card replacement",
                "functions": ["call_intent"],
                "next_stage": "account_confirmation"
            },
            "account_confirmation": {
                "description": "Confirm which card needs replacement",
                "functions": ["member_account_confirmation"],
                "next_stage": "reason_collection"
            },
            "reason_collection": {
                "description": "Collect reason for replacement",
                "functions": ["replacement_reason"],
                "next_stage": "address_confirmation"
            },
            "address_confirmation": {
                "description": "Confirm delivery address",
                "functions": ["confirm_address"],
                "next_stage": "replacement_started"
            },
            "replacement_started": {
                "description": "Start the replacement process",
                "functions": ["start_card_replacement"],
                "next_stage": "replacement_complete"
            },
            "replacement_complete": {
                "description": "Complete the replacement process",
                "functions": ["finish_card_replacement"],
                "next_stage": "call_complete"
            },
            "call_complete": {
                "description": "Wrap up the call",
                "functions": ["wrap_up"],
                "next_stage": None
            }
        }
        
        if stage not in stage_info:
            available_stages = list(stage_info.keys())
            raise ValueError(f"Stage '{stage}' not found. Available stages: {available_stages}")
            
        return stage_info[stage]

    def validate_flow_configuration(self) -> Dict[str, Any]:
        """
        Validate that all flow components are properly configured.
        
        Returns:
            Validation results
        """
        tools = self.get_tools()
        functions = self.get_functions()
        prompts = self.get_prompts()
        
        tool_names = {tool["name"] for tool in tools}
        function_names = set(functions.keys())
        
        # Check that all tools have corresponding functions
        missing_functions = tool_names - function_names
        extra_functions = function_names - tool_names
        
        return {
            "valid": len(missing_functions) == 0,
            "tool_count": len(tools),
            "function_count": len(functions),
            "prompt_count": len(prompts),
            "missing_functions": list(missing_functions),
            "extra_functions": list(extra_functions),
            "stages": self.get_flow_stages()
        } 