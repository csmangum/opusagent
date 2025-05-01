# Bank of Peril Agent FSM Demo

This module implements a conversational banking agent using an Agent Finite State Machine (AFSM) approach. 
Each state represents a distinct phase in the banking interaction, with clear responsibilities and transition rules.

## Overview

The Bank of Peril demo showcases how to build a conversational agent using a finite state machine approach.
This approach offers several benefits for banking applications:

1. Clear Separation of Concerns: Each state handles a specific part of the conversation flow
2. Predictable Transitions: All possible state changes are explicitly defined
3. Maintainability: Easy to modify individual states without affecting the entire flow
4. Security: Authentication and authorization steps are enforced through state transitions
5. Error Handling: Dedicated states for managing different failure scenarios

## States

The FSM defines the following states:

- **IdleState**: Initial state before any interaction
- **GreetingState**: Welcomes the user and introduces the system
- **AuthenticatingState**: Handles user authentication
- **AuthenticationFailedState**: Handles failed authentication attempts
- **MainMenuState**: Presents banking options after successful authentication
- **IdentifyIntentState**: Determines the user's banking intent
- **GatherBalanceDetailsState**: Collects details for balance inquiries
- **GatherTransferDetailsState**: Collects details for money transfers
- **GatherBillPayDetailsState**: Collects details for bill payments
- **ConfirmActionState**: Gets confirmation before executing sensitive operations
- **ExecutingTransactionState**: Processes the banking transaction
- **ReportingSuccessState**: Informs the user of transaction success
- **ReportingFailureState**: Informs the user of transaction failure
- **ClarificationNeededState**: Handles unclear user input
- **HandlingErrorState**: Manages system errors gracefully
- **EndingInteractionState**: Concludes the banking session

## Transition Logic

The FSM implements the following key transitions between states:

### Authentication Flow
- **Idle → Greeting**: Triggered by any initial user message
- **Greeting → Authenticating**: Always transitions after greeting
- **Authenticating → MainMenu**: When credentials are valid
- **Authenticating → AuthenticationFailed**: When credentials are invalid
- **AuthenticationFailed → Authenticating**: When user wants to retry
- **AuthenticationFailed → EndingInteraction**: When user doesn't want to retry

### Main Menu Flow
- **MainMenu → IdentifyIntent**: When user makes a request
- **MainMenu → EndingInteraction**: When user wants to exit
- **IdentifyIntent → GatherBalanceDetails**: When balance inquiry intent detected
- **IdentifyIntent → GatherTransferDetails**: When transfer intent detected
- **IdentifyIntent → GatherBillPayDetails**: When bill payment intent detected
- **IdentifyIntent → ClarificationNeeded**: When intent is unclear
- **IdentifyIntent → MainMenu**: When user wants to return to main menu

### Transaction Processing Flow
- **Gather...States → ConfirmAction**: When all required details collected
- **Gather...States → ClarificationNeeded**: When information missing/ambiguous
- **Gather...States → MainMenu**: When user cancels operation
- **ConfirmAction → ExecutingTransaction**: When user confirms action
- **ConfirmAction → MainMenu**: When user cancels action
- **ExecutingTransaction → ReportingSuccess**: When transaction succeeds
- **ExecutingTransaction → ReportingFailure**: When transaction fails
- **ExecutingTransaction → HandlingError**: When error occurs during processing

### Ending Flow
- **ReportingSuccess → MainMenu**: When user wants to continue
- **ReportingSuccess → EndingInteraction**: When user wants to exit
- **ReportingFailure → MainMenu**: When user wants to continue
- **ReportingFailure → EndingInteraction**: When user wants to exit
- **ClarificationNeeded → IdentifyIntent**: When user provides clarification
- **ClarificationNeeded → MainMenu**: When user wants to return to main menu
- **HandlingError → MainMenu**: When user wants to continue
- **HandlingError → EndingInteraction**: When user wants to exit
- **EndingInteraction → Idle**: Always transitions to reset for next session

## Transition Implementation

The transitions are implemented using a combination of different strategies:

1. **Rule-Based Transitions**: Simple condition-based transitions that evaluate boolean conditions
2. **Intent-Based Transitions**: Transitions triggered by detected user intents
3. **Hybrid Transitions**: Combining multiple transition strategies for complex scenarios

Each transition includes:
- Source state
- Target state
- Condition(s) that must be met for the transition to occur
- Priority level (higher priority transitions are evaluated first)
- Description of the transition's purpose

## Running the Demo

You can run the demo using the `example.py` script:

```python
python -m fastagent.afsm.bop.example
```

The example script simulates several conversation flows to demonstrate the transitions between states.

## Key Components

- **states.py**: Contains all state implementations
- **transitions.py**: Defines transition logic and conditions
- **example.py**: Demonstrates usage of the FSM

## State Diagram

The conversation flow follows this pattern:

```
Idle → Greeting → Authenticating → MainMenu
                               ↓
                    ┌──────────┼──────────┐
                    ↓          ↓          ↓ 
     GatherBalanceDetails  GatherTransferDetails  GatherBillPayDetails
                    |          |          |
                    └──────────┼──────────┘
                               ↓
                        ConfirmAction
                               ↓
                    ExecutingTransaction
                               ↓
                    ┌──────────┼──────────┐
                    ↓          ↓          ↓
           ReportingSuccess  ReportingFailure  HandlingError
                    |          |          |
                    └──────────┼──────────┘
                               ↓
                      EndingInteraction → Idle
```

Error states such as `AuthenticationFailed` and `ClarificationNeeded` are omitted from the diagram for clarity but are fully implemented.

## Implementation Notes

1. **Authentication**: For demo purposes, authentication is simulated. A message containing both "account" and "pin" with some numeric characters will succeed.

2. **Transaction Processing**: Transactions have a 95% success rate for demo purposes.

3. **State Persistence**: The FSM maintains conversation history and transaction details in its context.

4. **Transition Logic**: Transitions between states are determined by:
   - Explicit transitions returned from state processing methods
   - Rule-based transitions evaluated against the current context

## Example Interaction

```
System: Welcome to the Bank of Peril! Your security is our second priority.
        To access your account, I'll need to verify your identity.
        Please provide your account number and PIN.

You: My account is 12345 and my PIN is 6789

System: Authentication successful. Welcome to your Bank of Peril account.
        What would you like to do today?
        - Check account balance
        - Transfer money
        - Pay bills
        - Exit

You: I want to check my balance

System: Which account would you like to check the balance for? (Checking, Savings, Credit Card)

You: Checking

System: You're about to check the balance of your checking account. Proceed? (Yes/No)

You: Yes

System: Your checking balance is $2,534.21.
        Is there anything else you'd like to do today? (or type 'exit' to end the session)

You: exit

System: Thank you for banking with Bank of Peril. Have a nice day!
``` 