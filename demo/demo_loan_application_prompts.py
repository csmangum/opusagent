# Loan Application Flow Prompts

loan_intent_confirmation_prompt = """
I'd be happy to help you with a loan application! We offer several types of loans:

- Personal loans ($1,000 - $50,000)
- Auto loans (new and used vehicles)
- Home mortgages (purchase and refinance)
- Business loans ($5,000 - $500,000)

What type of loan are you interested in today?
"""

loan_amount_prompt = """
For your {loan_type}, what loan amount are you looking for?

{loan_type_info}
"""

income_verification_prompt = """
To process your {loan_type} application for ${loan_amount:,.2f}, I'll need to verify your income.

What is your annual gross income?
"""

employment_verification_prompt = """
Thank you. For verification purposes, can you tell me:

1. Your current employer
2. How long you've been with this employer
3. Your job title
"""

credit_check_consent_prompt = """
To complete your {loan_type} application, I need your consent to run a credit check. 

This will be a soft inquiry that won't affect your credit score. Do I have your permission to proceed?
"""

application_summary_prompt = """
Perfect! Let me summarize your loan application:

- Loan Type: {loan_type}
- Loan Amount: ${loan_amount:,.2f}
- Annual Income: ${annual_income:,.2f}
- Employer: {employer}
- Employment Duration: {employment_duration}

I'm now submitting your application for review. You should receive a decision within 24-48 hours via email.

Is there anything else I can help you with today?
"""

loan_approval_prompt = """
Great news! Your {loan_type} application for ${loan_amount:,.2f} has been pre-approved!

Next steps:
1. You'll receive an email with detailed terms
2. Required documents list will be attached
3. You can complete the final application online

Your reference number is: {reference_number}

Do you have any questions about the next steps?
""" 