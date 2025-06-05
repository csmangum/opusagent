"""
Loan Application Flow Functions

Contains the function implementations for the loan application flow.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def get_loan_application_functions() -> Dict[str, Any]:
    """
    Get the function implementations for the loan application flow.
    
    Returns:
        Dictionary mapping function names to callable implementations
    """
    return {
        "loan_type_selection": _func_loan_type_selection,
        "loan_amount_collection": _func_loan_amount_collection,
        "income_verification": _func_income_verification,
        "employment_verification": _func_employment_verification,
        "credit_check_consent": _func_credit_check_consent,
        "submit_loan_application": _func_submit_loan_application,
        "loan_pre_approval": _func_loan_pre_approval,
        "wrap_up": _func_wrap_up
    }


def _func_loan_type_selection(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle loan type selection and provide information.
    
    Args:
        arguments: Function arguments containing loan type preference
        
    Returns:
        Formatted prompt and guidance for loan type selection
    """
    from .prompts import LOAN_TYPE_SELECTION_PROMPT
    
    selected_loan_type = arguments.get("loan_type", "")
    
    logger.info(f"Loan type selection function called with type: {selected_loan_type}")
    
    return {
        "status": "success",
        "function_name": "loan_type_selection",
        "prompt_guidance": LOAN_TYPE_SELECTION_PROMPT,
        "next_action": "collect_loan_amount" if selected_loan_type else "ask_loan_type",
        "available_loan_types": [
            "Personal loan", 
            "Auto loan", 
            "Home mortgage", 
            "Business loan"
        ],
        "selected_loan_type": selected_loan_type,
        "context": {
            "stage": "loan_type_selection",
            "selected_loan_type": selected_loan_type
        }
    }


def _func_loan_amount_collection(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Collect and validate loan amount.
    
    Args:
        arguments: Function arguments containing loan amount
        
    Returns:
        Formatted prompt and guidance for loan amount collection
    """
    from .prompts import LOAN_AMOUNT_PROMPT
    
    loan_amount = arguments.get("loan_amount", 0)
    loan_type = arguments.get("loan_type", "loan")
    
    logger.info(f"Loan amount collection function called with amount: {loan_amount}")
    
    # Add loan type specific information
    loan_type_info = {
        "Personal loan": "Range: $1,000 - $50,000",
        "Auto loan": "Range: $5,000 - $100,000",
        "Home mortgage": "Range: $50,000 - $1,000,000",
        "Business loan": "Range: $5,000 - $500,000"
    }.get(loan_type, "")
    
    formatted_prompt = LOAN_AMOUNT_PROMPT.format(
        loan_type=loan_type,
        loan_type_info=loan_type_info
    )
    
    return {
        "status": "success",
        "function_name": "loan_amount_collection",
        "prompt_guidance": formatted_prompt,
        "next_action": "verify_income",
        "loan_amount": loan_amount,
        "context": {
            "stage": "loan_amount_collection",
            "loan_amount": loan_amount
        }
    }


def _func_income_verification(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify income information.
    
    Args:
        arguments: Function arguments containing income details
        
    Returns:
        Formatted prompt and guidance for income verification
    """
    from .prompts import INCOME_VERIFICATION_PROMPT
    
    annual_income = arguments.get("annual_income", 0)
    loan_type = arguments.get("loan_type", "loan")
    loan_amount = arguments.get("loan_amount", 0)
    
    logger.info(f"Income verification function called with income: {annual_income}")
    
    formatted_prompt = INCOME_VERIFICATION_PROMPT.format(
        loan_type=loan_type,
        loan_amount=loan_amount
    )
    
    return {
        "status": "success",
        "function_name": "income_verification",
        "prompt_guidance": formatted_prompt,
        "next_action": "verify_employment",
        "annual_income": annual_income,
        "context": {
            "stage": "income_verification",
            "annual_income": annual_income
        }
    }


def _func_employment_verification(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify employment details.
    
    Args:
        arguments: Function arguments containing employment details
        
    Returns:
        Formatted prompt and guidance for employment verification
    """
    from .prompts import EMPLOYMENT_VERIFICATION_PROMPT
    
    employer = arguments.get("employer", "")
    employment_duration = arguments.get("employment_duration", "")
    job_title = arguments.get("job_title", "")
    
    logger.info(f"Employment verification function called for employer: {employer}")
    
    return {
        "status": "success",
        "function_name": "employment_verification",
        "prompt_guidance": EMPLOYMENT_VERIFICATION_PROMPT,
        "next_action": "get_credit_check_consent",
        "employer": employer,
        "employment_duration": employment_duration,
        "job_title": job_title,
        "context": {
            "stage": "employment_verification",
            "employer": employer,
            "employment_duration": employment_duration,
            "job_title": job_title
        }
    }


def _func_credit_check_consent(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get consent for credit check.
    
    Args:
        arguments: Function arguments containing consent information
        
    Returns:
        Formatted prompt and guidance for credit check consent
    """
    from .prompts import CREDIT_CHECK_CONSENT_PROMPT
    
    consent_given = arguments.get("consent_given", False)
    loan_type = arguments.get("loan_type", "loan")
    
    logger.info(f"Credit check consent function called with consent: {consent_given}")
    
    formatted_prompt = CREDIT_CHECK_CONSENT_PROMPT.format(
        loan_type=loan_type
    )
    
    return {
        "status": "success",
        "function_name": "credit_check_consent",
        "prompt_guidance": formatted_prompt,
        "next_action": "submit_application" if consent_given else "explain_credit_check",
        "consent_given": consent_given,
        "context": {
            "stage": "credit_check_consent",
            "consent_given": consent_given
        }
    }


def _func_submit_loan_application(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Submit loan application for processing.
    
    Args:
        arguments: Function arguments containing complete application data
        
    Returns:
        Formatted prompt and guidance for application submission
    """
    from .prompts import APPLICATION_SUMMARY_PROMPT
    
    loan_type = arguments.get("loan_type", "loan")
    loan_amount = arguments.get("loan_amount", 0)
    annual_income = arguments.get("annual_income", 0)
    employer = arguments.get("employer", "")
    employment_duration = arguments.get("employment_duration", "")
    job_title = arguments.get("job_title", "")
    
    formatted_prompt = APPLICATION_SUMMARY_PROMPT.format(
        loan_type=loan_type,
        loan_amount=loan_amount,
        annual_income=annual_income,
        employer=employer,
        employment_duration=employment_duration,
        job_title=job_title
    )
    
    logger.info(f"Submitting loan application: {loan_type} for ${loan_amount}")
    
    return {
        "status": "success",
        "function_name": "submit_loan_application",
        "prompt_guidance": formatted_prompt,
        "next_action": "check_pre_approval",
        "application_submitted": True,
        "context": {
            "stage": "application_submitted",
            "loan_type": loan_type,
            "loan_amount": loan_amount,
            "annual_income": annual_income,
            "employer": employer,
            "employment_duration": employment_duration,
            "job_title": job_title
        }
    }


def _func_loan_pre_approval(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process loan pre-approval.
    
    Args:
        arguments: Function arguments containing application ID
        
    Returns:
        Formatted prompt and guidance for pre-approval process
    """
    from .prompts import LOAN_APPROVAL_PROMPT
    
    application_id = arguments.get("application_id", "")
    loan_type = arguments.get("loan_type", "loan")
    loan_amount = arguments.get("loan_amount", 0)
    
    # Generate a reference number (in real implementation, this would come from the system)
    reference_number = f"LOAN-{application_id[:8].upper()}"
    
    formatted_prompt = LOAN_APPROVAL_PROMPT.format(
        loan_type=loan_type,
        loan_amount=loan_amount,
        reference_number=reference_number
    )
    
    logger.info(f"Processing pre-approval for application: {application_id}")
    
    return {
        "status": "success",
        "function_name": "loan_pre_approval",
        "prompt_guidance": formatted_prompt,
        "next_action": "wrap_up",
        "pre_approved": True,
        "reference_number": reference_number,
        "context": {
            "stage": "pre_approval",
            "application_id": application_id,
            "reference_number": reference_number
        }
    }


def _func_wrap_up(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Wrap up the loan application process.
    
    Args:
        arguments: Function arguments containing application status and next steps
        
    Returns:
        Formatted prompt and guidance for call wrap-up
    """
    application_status = arguments.get("application_status", "")
    next_steps = arguments.get("next_steps", "")
    
    logger.info(f"Wrapping up loan application with status: {application_status}")
    
    return {
        "status": "success",
        "function_name": "wrap_up",
        "next_action": "end_call",
        "application_status": application_status,
        "next_steps": next_steps,
        "context": {
            "stage": "call_complete",
            "application_status": application_status,
            "next_steps": next_steps
        }
    } 