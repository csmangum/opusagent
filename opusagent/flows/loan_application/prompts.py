"""
Loan Application Flow Prompts

Contains all the prompts used in the loan application flow.
"""

# Base prompt for the loan application flow
BASE_PROMPT = """
I'm here to help you with your loan application. I'll guide you through the process step by step.
"""

# Loan type selection prompt
LOAN_TYPE_SELECTION_PROMPT = """
I'd be happy to help you with a loan application! We offer several types of loans:

- Personal loans ($1,000 - $50,000)
- Auto loans (new and used vehicles)
- Home mortgages (purchase and refinance)
- Business loans ($5,000 - $500,000)

What type of loan are you interested in today?
"""

# Loan amount collection prompt
LOAN_AMOUNT_PROMPT = """
For your {loan_type}, what loan amount are you looking for?

{loan_type_info}
"""

# Income verification prompt
INCOME_VERIFICATION_PROMPT = """
To process your {loan_type} application for ${loan_amount:,.2f}, I'll need to verify your income.

What is your annual gross income?
"""

# Employment verification prompt
EMPLOYMENT_VERIFICATION_PROMPT = """
Thank you. For verification purposes, can you tell me:

1. Your current employer
2. How long you've been with this employer
3. Your job title
"""

# Credit check consent prompt
CREDIT_CHECK_CONSENT_PROMPT = """
To complete your {loan_type} application, I need your consent to run a credit check. 

This will be a soft inquiry that won't affect your credit score. Do I have your permission to proceed?
"""

# Application summary prompt
APPLICATION_SUMMARY_PROMPT = """
Perfect! Let me summarize your loan application:

- Loan Type: {loan_type}
- Loan Amount: ${loan_amount:,.2f}
- Annual Income: ${annual_income:,.2f}
- Employer: {employer}
- Employment Duration: {employment_duration}
- Job Title: {job_title}

I'm now submitting your application for review. You should receive a decision within 24-48 hours via email.

Is there anything else I can help you with today?
"""

# Loan approval prompt
LOAN_APPROVAL_PROMPT = """
Great news! Your {loan_type} application for ${loan_amount:,.2f} has been pre-approved!

Next steps:
1. You'll receive an email with detailed terms
2. Required documents list will be attached
3. You can complete the final application online

Your reference number is: {reference_number}

Do you have any questions about the next steps?
"""

# System instruction for the loan application flow
SYSTEM_INSTRUCTION = """
You are a loan application assistant. Your role is to guide customers through the loan application process.
You should:
1. Help customers select the right loan type
2. Collect necessary information
3. Explain the process clearly
4. Be professional and courteous
5. Follow all regulatory requirements
6. Maintain accurate records
7. Provide clear next steps

Remember to:
- Verify all information
- Get explicit consent for credit checks
- Explain terms clearly
- Keep customer information secure
- Follow up on missing information
- Provide clear timelines
- Handle objections professionally
""" 