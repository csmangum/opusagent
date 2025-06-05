# Bank of Peril - Finite State Agent for Customer Service

This diagram illustrates how a Finite State Agent (FSA) handles customer interactions for a hypothetical company called The Bank of Peril, a financial institution known for its high-security protocols and unique "Risk Acceptance Program" for high-yield investments. The FSA provides a structured framework for managing customer conversations while maintaining context awareness and agent reasoning through scratchpads in each state.

## Key Features
- **State-Aware Conversations**: Each state has specific handling logic and allowed transitions
- **Scratchpad Reasoning**: Internal agent thinking visible in note sections
- **Security-First Design**: Multi-factor authentication required before accessing sensitive information
- **Fallback Mechanisms**: Human escalation paths for complex issues
- **Context Retention**: Customer information persists across state transitions
- **Risk Assessment**: Special states for handling the bank's unique "Risk Acceptance Program"

## Sample Conversation Flow

**Customer**: "Hi, I need to check my account balance and make a transfer."  
*(FSA State: Greeting → Authentication)*

**Agent**: "Welcome to Bank of Peril, where we secure what matters most. For account access, I'll need to verify your identity. Can you please provide your account number and the last 4 digits of your security phrase?"  
*(FSA State: Authentication)*

**Customer**: *Provides authentication information*  
*(FSA State: Authentication → AccountVerification)*

**Agent**: "Thank you, your identity has been verified. How can I help with your account today?"  
*(FSA State: AccountVerification → AccountInquiry)*

**Customer**: "I want to check my balance and transfer $500 to my Perilous Savings account."  
*(FSA State: AccountInquiry → BalanceInformation → TransactionRequest → TransferSetup)*

**Agent**: "Your current balance is $2,450 in your Peril Checking account. I can help you transfer $500 to your Perilous Savings account. The transfer will be secured with our Advanced Risk Protocol. Would you like to proceed?"  
*(FSA State: TransferSetup → TransactionConfirmation)*

**Customer**: "Yes, please proceed with the transfer."  
*(FSA State: TransactionConfirmation → TransactionSuccess)*

**Agent**: "I've completed the transfer of $500 to your Perilous Savings account. The transaction is secured with our 256-bit encryption and recorded in our secure ledger. Is there anything else I can help you with today?"  
*(FSA State: TransactionSuccess → FollowUpQuestion)*

**Customer**: "No, that's all. Thank you."  
*(FSA State: FollowUpQuestion → ThankYou → SatisfactionSurvey → EndCall)*

```mermaid
stateDiagram-v2
    [*] --> Greeting
    
    Greeting --> Authentication: Customer needs authentication
    Greeting --> GeneralInquiry: Customer has general question
    Greeting --> EndCall: Customer wants to end call
    
    Authentication --> AccountVerification: Authentication successful
    Authentication --> FailedAuthentication: Authentication failed
    FailedAuthentication --> Authentication: Retry authentication
    FailedAuthentication --> HumanEscalation: Multiple failures
    FailedAuthentication --> FraudPrevention: Suspicious activity detected
    
    AccountVerification --> AccountInquiry: Customer wants account information
    AccountVerification --> TransactionRequest: Customer wants to make transaction
    AccountVerification --> BillPayment: Customer wants to pay bills
    AccountVerification --> RiskAcceptanceProgram: Customer interested in high-yield options
    
    AccountInquiry --> BalanceInformation: Balance inquiry
    AccountInquiry --> TransactionHistory: Transaction history request
    AccountInquiry --> AccountDetails: Account details request
    AccountInquiry --> SecurityAlerts: Security notification updates
    
    BalanceInformation --> FollowUpQuestion: "Anything else?"
    TransactionHistory --> FollowUpQuestion: "Anything else?"
    AccountDetails --> FollowUpQuestion: "Anything else?"
    SecurityAlerts --> FollowUpQuestion: "Anything else?"
    
    TransactionRequest --> TransferSetup: Transfer funds
    TransactionRequest --> PaymentSetup: Make payment
    TransactionRequest --> InternationalWire: International transfer
    
    TransferSetup --> TransactionConfirmation: Customer confirms
    TransferSetup --> TransactionCancellation: Customer cancels
    TransferSetup --> FraudPrevention: High-risk transaction detected
    
    PaymentSetup --> TransactionConfirmation: Customer confirms
    PaymentSetup --> TransactionCancellation: Customer cancels
    
    InternationalWire --> ExtraVerification: Additional security check
    ExtraVerification --> TransactionConfirmation: Verification passed
    ExtraVerification --> FraudPrevention: Verification failed
    
    BillPayment --> BillSelection: Select bill to pay
    BillSelection --> PaymentSetup: Set payment amount
    
    TransactionConfirmation --> TransactionSuccess: Transaction completed
    TransactionConfirmation --> TransactionFailure: Transaction failed
    
    TransactionSuccess --> FollowUpQuestion: "Anything else?"
    TransactionFailure --> TroubleshootTransaction: Resolve issue
    TransactionCancellation --> FollowUpQuestion: "Anything else?"
    
    TroubleshootTransaction --> TransactionRequest: Retry transaction
    TroubleshootTransaction --> HumanEscalation: Cannot resolve
    
    GeneralInquiry --> ProductInformation: Product inquiries
    GeneralInquiry --> BranchLocator: Find branch/ATM
    GeneralInquiry --> OperatingHours: Branch hours
    GeneralInquiry --> RiskAcceptanceProgram: High-yield investment options
    
    RiskAcceptanceProgram --> RiskAssessment: Determine risk tolerance
    RiskAssessment --> InvestmentOptions: Present appropriate options
    RiskAssessment --> RiskAcceptanceDocumentation: Prepare required documents
    
    InvestmentOptions --> FollowUpQuestion: Customer needs time to decide
    InvestmentOptions --> ApplicationSetup: Customer wants to proceed
    
    ApplicationSetup --> TransactionConfirmation: Application submission
    RiskAcceptanceDocumentation --> HumanEscalation: Complex situation
    
    ProductInformation --> FollowUpQuestion: "Anything else?"
    BranchLocator --> FollowUpQuestion: "Anything else?"
    OperatingHours --> FollowUpQuestion: "Anything else?"
    
    FollowUpQuestion --> AccountInquiry: New account inquiry
    FollowUpQuestion --> TransactionRequest: New transaction
    FollowUpQuestion --> GeneralInquiry: New general inquiry
    FollowUpQuestion --> ThankYou: No more questions
    
    FraudPrevention --> SecurityVerification: Additional verification
    SecurityVerification --> AccountVerification: Verification successful
    SecurityVerification --> AccountLock: Verification failed
    AccountLock --> HumanEscalation: Account locked
    
    ThankYou --> SatisfactionSurvey: Request feedback
    SatisfactionSurvey --> EndCall: Call completed
    
    HumanEscalation --> EndCall: Transfer to human agent
    
    EndCall --> [*]
    
    note right of Greeting
        Scratchpad: "Customer connected. I'll greet them 
        with our Bank of Peril security-first message and
        identify their needs. Checking previous interaction
        history for context."
    end note
    
    note right of Authentication
        Scratchpad: "Need to verify customer identity 
        using our multi-factor protocol before providing account 
        access. Will ask for account number and security phrase.
        Will check against fraud patterns database."
    end note
    
    note right of TransactionConfirmation
        Scratchpad: "Customer wants to transfer $500 to 
        Perilous Savings account. Transaction appears routine
        but I should confirm details and get explicit approval.
        Will note this in the secure transaction ledger."
    end note
    
    note right of RiskAcceptanceProgram
        Scratchpad: "Customer is inquiring about our high-yield
        'Calculated Risk' investment program. Need to assess their
        risk tolerance and financial situation before proceeding.
        Must ensure they understand the disclaimer terms."
    end note
    
    note right of FraudPrevention
        Scratchpad: "Detected unusual pattern: transfer request
        differs from customer's normal behavior. Need to perform
        additional security verification while maintaining
        professional tone. Will check recent activity."
    end note
```

## FSA Implementation Notes

The Bank of Peril FSA is implemented using OpusAgent's core architecture and focuses on:

1. **Security-First Design**: Multi-factor authentication and fraud detection are deeply integrated
2. **Specialized Banking States**: Custom states for handling Bank of Peril's unique offerings 
3. **Low-Latency Responses**: Optimized for sub-300ms response times for natural conversation
4. **Comprehensive Logging**: All transactions and state transitions are securely logged
5. **Risk Assessment**: Specialized states for evaluating customer risk tolerance for high-yield products
