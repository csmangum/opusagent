"""
Loan Application Flow Tools

Contains the OpenAI function tool definitions for the loan application flow.
"""

from typing import List, Dict, Any


def get_loan_application_tools() -> List[Dict[str, Any]]:
    """
    Get the OpenAI tool definitions for the loan application flow.
    
    Returns:
        List of OpenAI function tool schemas
    """
    return [
        {
            "name": "loan_type_selection",
            "description": "Handle loan type selection and provide information",
            "parameters": {
                "type": "object",
                "properties": {
                    "loan_type": {
                        "type": "string",
                        "description": "Selected loan type (personal, auto, mortgage, business)"
                    }
                },
                "required": ["loan_type"]
            }
        },
        {
            "name": "loan_amount_collection",
            "description": "Collect and validate loan amount",
            "parameters": {
                "type": "object",
                "properties": {
                    "loan_amount": {
                        "type": "number",
                        "description": "Requested loan amount"
                    }
                },
                "required": ["loan_amount"]
            }
        },
        {
            "name": "income_verification",
            "description": "Verify income information",
            "parameters": {
                "type": "object",
                "properties": {
                    "annual_income": {
                        "type": "number",
                        "description": "Annual gross income"
                    }
                },
                "required": ["annual_income"]
            }
        },
        {
            "name": "employment_verification",
            "description": "Verify employment details",
            "parameters": {
                "type": "object",
                "properties": {
                    "employer": {
                        "type": "string",
                        "description": "Current employer name"
                    },
                    "employment_duration": {
                        "type": "string",
                        "description": "Duration of employment"
                    },
                    "job_title": {
                        "type": "string",
                        "description": "Current job title"
                    }
                },
                "required": ["employer", "employment_duration", "job_title"]
            }
        },
        {
            "name": "credit_check_consent",
            "description": "Get consent for credit check",
            "parameters": {
                "type": "object",
                "properties": {
                    "consent_given": {
                        "type": "boolean",
                        "description": "Whether consent is given for credit check"
                    }
                },
                "required": ["consent_given"]
            }
        },
        {
            "name": "submit_loan_application",
            "description": "Submit loan application for processing",
            "parameters": {
                "type": "object",
                "properties": {
                    "loan_type": {
                        "type": "string",
                        "description": "Type of loan"
                    },
                    "loan_amount": {
                        "type": "number",
                        "description": "Loan amount"
                    },
                    "annual_income": {
                        "type": "number",
                        "description": "Annual income"
                    },
                    "employer": {
                        "type": "string",
                        "description": "Employer name"
                    },
                    "employment_duration": {
                        "type": "string",
                        "description": "Employment duration"
                    },
                    "job_title": {
                        "type": "string",
                        "description": "Job title"
                    }
                },
                "required": [
                    "loan_type",
                    "loan_amount",
                    "annual_income",
                    "employer",
                    "employment_duration",
                    "job_title"
                ]
            }
        },
        {
            "name": "loan_pre_approval",
            "description": "Process loan pre-approval",
            "parameters": {
                "type": "object",
                "properties": {
                    "application_id": {
                        "type": "string",
                        "description": "Loan application ID"
                    }
                },
                "required": ["application_id"]
            }
        },
        {
            "name": "wrap_up",
            "description": "Wrap up the loan application process",
            "parameters": {
                "type": "object",
                "properties": {
                    "application_status": {
                        "type": "string",
                        "description": "Status of the application"
                    },
                    "next_steps": {
                        "type": "string",
                        "description": "Next steps for the applicant"
                    }
                },
                "required": ["application_status", "next_steps"]
            }
        }
    ] 