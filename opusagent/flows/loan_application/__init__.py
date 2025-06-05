"""
Loan Application Flow Package

Contains all components for the loan application conversation flow including
tools, functions, prompts, and flow orchestration.
"""

from typing import Any, Callable, Dict, List

from ..base_flow import BaseFlow
from .tools import get_loan_application_tools
from .functions import get_loan_application_functions
from .prompts import (
    BASE_PROMPT,
    LOAN_TYPE_SELECTION_PROMPT,
    LOAN_AMOUNT_PROMPT,
    INCOME_VERIFICATION_PROMPT,
    EMPLOYMENT_VERIFICATION_PROMPT,
    CREDIT_CHECK_CONSENT_PROMPT,
    APPLICATION_SUMMARY_PROMPT,
    LOAN_APPROVAL_PROMPT,
    SYSTEM_INSTRUCTION,
)


class LoanApplicationFlow(BaseFlow):
    """
    Loan application conversation flow implementation.
    
    This flow handles the complete loan application process including:
    - Loan type selection
    - Amount collection
    - Income verification
    - Employment verification
    - Credit check consent
    - Application submission
    - Pre-approval process
    """

    def __init__(self):
        """Initialize the loan application flow."""
        super().__init__("loan_application")

    def get_tools(self) -> List[Dict[str, Any]]:
        """
        Get the OpenAI tool definitions for this flow.
        
        Returns:
            List of OpenAI function tool schemas
        """
        return get_loan_application_tools()

    def get_functions(self) -> Dict[str, Callable]:
        """
        Get the function implementations for this flow.
        
        Returns:
            Dictionary mapping function names to callable implementations
        """
        return get_loan_application_functions()

    def get_prompts(self) -> Dict[str, str]:
        """
        Get the prompts used in this flow.
        
        Returns:
            Dictionary mapping prompt names to prompt templates
        """
        return {
            "base_prompt": BASE_PROMPT,
            "loan_type_selection": LOAN_TYPE_SELECTION_PROMPT,
            "loan_amount": LOAN_AMOUNT_PROMPT,
            "income_verification": INCOME_VERIFICATION_PROMPT,
            "employment_verification": EMPLOYMENT_VERIFICATION_PROMPT,
            "credit_check_consent": CREDIT_CHECK_CONSENT_PROMPT,
            "application_summary": APPLICATION_SUMMARY_PROMPT,
            "loan_approval": LOAN_APPROVAL_PROMPT,
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
            "loan_type_selection",
            "loan_amount_collection",
            "income_verification",
            "employment_verification",
            "credit_check_consent",
            "application_submission",
            "pre_approval",
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
            "loan_type_selection": {
                "description": "Select type of loan",
                "functions": ["loan_type_selection"],
                "next_stage": "loan_amount_collection"
            },
            "loan_amount_collection": {
                "description": "Collect loan amount",
                "functions": ["loan_amount_collection"],
                "next_stage": "income_verification"
            },
            "income_verification": {
                "description": "Verify income information",
                "functions": ["income_verification"],
                "next_stage": "employment_verification"
            },
            "employment_verification": {
                "description": "Verify employment details",
                "functions": ["employment_verification"],
                "next_stage": "credit_check_consent"
            },
            "credit_check_consent": {
                "description": "Get consent for credit check",
                "functions": ["credit_check_consent"],
                "next_stage": "application_submission"
            },
            "application_submission": {
                "description": "Submit loan application",
                "functions": ["submit_loan_application"],
                "next_stage": "pre_approval"
            },
            "pre_approval": {
                "description": "Process pre-approval",
                "functions": ["loan_pre_approval"],
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


__all__ = ["LoanApplicationFlow"] 