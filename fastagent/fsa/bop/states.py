"""
Bank of Peril States Module

This module implements a conversational banking agent using an Finite State Agent (FSA) approach.
Each state represents a distinct phase in the banking interaction, with clear responsibilities and transition rules.

The finite state machine approach provides several benefits for this banking application:
1. Clear Separation of Concerns: Each state handles a specific part of the conversation flow
2. Predictable Transitions: All possible state changes are explicitly defined
3. Maintainability: Easy to modify individual states without affecting the entire flow
4. Security: Authentication and authorization steps are enforced through state transitions
5. Error Handling: Dedicated states for managing different failure scenarios

The conversation flow follows a structured pattern:
- Initial greeting and authentication
- Main menu presenting banking options
- Specialized states for gathering transaction details
- Confirmation before executing sensitive operations
- Success/failure reporting
- Clean session termination

Each state implements the FSAState interface and defines its processing logic and allowed transitions.
"""

from typing import Any, Dict, List, Optional, Tuple

from ..states.base import FSAState, StateContext, StateTransition


class IdleState(FSAState):
    """Initial idle state when no interaction is happening."""

    def __init__(self):
        transitions = [
            StateTransition(
                target_state="greeting", condition="User initiates conversation"
            )
        ]
        super().__init__(
            name="idle",
            description="Initial state before user interaction begins",
            allowed_transitions=transitions,
        )

    async def process(
        self, input_text: str, context: StateContext
    ) -> Tuple[str, Optional[str], Dict[str, Any]]:
        # When user sends any input from idle state, transition to greeting
        self.write_to_scratchpad(
            f"User initiated conversation with: '{input_text}'\n"
            "Transitioning to greeting state."
        )

        # Add to conversation history
        context.conversation_history.append({"role": "user", "content": input_text})

        # Simply transition to greeting state with no response
        return "", "greeting", {"conversation_history": context.conversation_history}


class GreetingState(FSAState):
    """Greeting state that welcomes the user."""

    def __init__(self):
        transitions = [
            StateTransition(
                target_state="authenticating", condition="Authentication needed"
            )
        ]
        super().__init__(
            name="greeting",
            description="Welcome user and prepare for authentication",
            allowed_transitions=transitions,
        )

    async def process(
        self, input_text: str, context: StateContext
    ) -> Tuple[str, Optional[str], Dict[str, Any]]:
        self.write_to_scratchpad(
            "User has connected. Providing welcome message and requesting authentication.\n"
        )

        response = (
            "Welcome to the Bank of Peril! Your security is our second priority.\n"
            "To access your account, I'll need to verify your identity.\n"
            "Please provide your account number and PIN."
        )

        context.conversation_history.append({"role": "assistant", "content": response})

        # Always transition to authentication after greeting
        return (
            response,
            "authenticating",
            {"conversation_history": context.conversation_history},
        )


class AuthenticatingState(FSAState):
    """Handles user authentication."""

    def __init__(self):
        transitions = [
            StateTransition(
                target_state="authentication_failed", condition="Authentication failed"
            ),
            StateTransition(
                target_state="main_menu", condition="Authentication successful"
            ),
        ]
        super().__init__(
            name="authenticating",
            description="Verifies user credentials",
            allowed_transitions=transitions,
        )

    async def process(
        self, input_text: str, context: StateContext
    ) -> Tuple[str, Optional[str], Dict[str, Any]]:
        self.write_to_scratchpad(
            f"Processing authentication input: '{input_text}'\n"
            "Checking for account number and PIN format."
        )

        # Add to conversation history
        context.conversation_history.append({"role": "user", "content": input_text})

        # Simple validation logic - in a real system this would verify against a database
        # For demo purposes, accept input that looks like "account: 1234, pin: 5678"
        input_lower = input_text.lower()

        # Simulate authentication logic
        # In a real implementation, this would validate against secure storage
        is_authenticated = False

        # Very simple check for demo purposes
        if (
            ("account" in input_lower or "number" in input_lower)
            and ("pin" in input_lower or "password" in input_lower)
            and any(c.isdigit() for c in input_lower)
        ):
            is_authenticated = True

        if is_authenticated:
            self.write_to_scratchpad(
                "Authentication successful. Transitioning to main menu."
            )

            response = (
                "Authentication successful. Welcome to your Bank of Peril account."
            )

            # Update authentication status in context
            context.metadata["authenticated"] = True

            context.conversation_history.append(
                {"role": "assistant", "content": response}
            )

            return (
                response,
                "main_menu",
                {
                    "conversation_history": context.conversation_history,
                    "metadata": context.metadata,
                },
            )
        else:
            self.write_to_scratchpad(
                "Authentication failed. Transitioning to authentication_failed state."
            )

            response = "I couldn't verify your credentials. Please ensure you're providing both your account number and PIN."

            context.conversation_history.append(
                {"role": "assistant", "content": response}
            )

            return (
                response,
                "authentication_failed",
                {"conversation_history": context.conversation_history},
            )


class AuthenticationFailedState(FSAState):
    """Handles failed authentication attempts."""

    def __init__(self):
        transitions = [
            StateTransition(
                target_state="authenticating", condition="Retry authentication"
            ),
            StateTransition(target_state="ending_interaction", condition="End session"),
        ]
        super().__init__(
            name="authentication_failed",
            description="Handles failed authentication attempts",
            allowed_transitions=transitions,
        )

    async def process(
        self, input_text: str, context: StateContext
    ) -> Tuple[str, Optional[str], Dict[str, Any]]:
        self.write_to_scratchpad(
            f"User response after authentication failure: '{input_text}'\n"
            "Determining if user wants to retry or end session."
        )

        # Add to conversation history
        context.conversation_history.append({"role": "user", "content": input_text})

        input_lower = input_text.lower()

        # Check if user wants to retry
        if any(
            term in input_lower
            for term in ["retry", "try again", "account", "pin", "number"]
        ):
            self.write_to_scratchpad("User wants to retry authentication.")

            response = "Let's try again. Please provide your account number and PIN."

            context.conversation_history.append(
                {"role": "assistant", "content": response}
            )

            return (
                response,
                "authenticating",
                {"conversation_history": context.conversation_history},
            )
        else:
            self.write_to_scratchpad("User doesn't want to retry. Ending session.")

            response = "I understand. For security reasons, this session will now end. Please try again later if needed."

            context.conversation_history.append(
                {"role": "assistant", "content": response}
            )

            return (
                response,
                "ending_interaction",
                {"conversation_history": context.conversation_history},
            )


class MainMenuState(FSAState):
    """Main menu state after successful authentication."""

    def __init__(self):
        transitions = [
            StateTransition(
                target_state="identify_intent", condition="User makes request"
            ),
            StateTransition(
                target_state="ending_interaction", condition="User wants to exit"
            ),
        ]
        super().__init__(
            name="main_menu",
            description="Main menu offering banking options",
            allowed_transitions=transitions,
        )

    async def process(
        self, input_text: str, context: StateContext
    ) -> Tuple[str, Optional[str], Dict[str, Any]]:
        self.write_to_scratchpad(
            f"At main menu, processing: '{input_text}'\n"
            "Displaying available options."
        )

        # For first entry to main menu, provide options
        if not input_text or "main menu" in input_text.lower():
            response = (
                "What would you like to do today?\n"
                "- Check account balance\n"
                "- Transfer money\n"
                "- Pay bills\n"
                "- Exit"
            )

            context.conversation_history.append(
                {"role": "assistant", "content": response}
            )

            # Stay in current state until user makes a selection
            return (
                response,
                None,
                {"conversation_history": context.conversation_history},
            )

        # Add to conversation history
        context.conversation_history.append({"role": "user", "content": input_text})

        input_lower = input_text.lower()

        # Check for exit request
        if any(
            term in input_lower
            for term in ["exit", "quit", "log out", "logout", "sign out"]
        ):
            self.write_to_scratchpad("User wants to exit. Ending interaction.")

            response = "Thank you for banking with Bank of Peril. Have a marginally secure day!"

            context.conversation_history.append(
                {"role": "assistant", "content": response}
            )

            return (
                response,
                "ending_interaction",
                {"conversation_history": context.conversation_history},
            )

        # Otherwise, transition to intent identification
        self.write_to_scratchpad(
            "User has made a request. Transitioning to identify intent."
        )

        # No response here as the identify_intent state will generate the response
        return (
            "",
            "identify_intent",
            {"conversation_history": context.conversation_history},
        )


class IdentifyIntentState(FSAState):
    """Identifies user intent from their request."""

    def __init__(self):
        transitions = [
            StateTransition(
                target_state="gather_balance_details", condition="Balance inquiry"
            ),
            StateTransition(
                target_state="gather_transfer_details", condition="Transfer request"
            ),
            StateTransition(
                target_state="gather_bill_pay_details", condition="Bill payment request"
            ),
            StateTransition(
                target_state="clarification_needed", condition="Intent unclear"
            ),
            StateTransition(target_state="main_menu", condition="Return to main menu"),
        ]
        super().__init__(
            name="identify_intent",
            description="Identifies the user's banking intent",
            allowed_transitions=transitions,
        )

    async def process(
        self, input_text: str, context: StateContext
    ) -> Tuple[str, Optional[str], Dict[str, Any]]:
        self.write_to_scratchpad(
            f"Identifying intent from: '{input_text}'\n"
            "Looking for balance, transfer, or bill payment indicators."
        )

        # Ensure we have input to analyze
        if not input_text and context.conversation_history:
            # Get the last user message if current input is empty
            for msg in reversed(context.conversation_history):
                if msg.get("role") == "user":
                    input_text = msg.get("content", "")
                    break

        input_lower = input_text.lower()

        # Identify intent based on keywords
        if any(term in input_lower for term in ["balance", "how much", "account"]):
            self.write_to_scratchpad("Detected balance inquiry intent.")
            context.metadata["intent"] = "balance_inquiry"
            return "", "gather_balance_details", {"metadata": context.metadata}

        elif any(
            term in input_lower for term in ["transfer", "send money", "move money"]
        ):
            self.write_to_scratchpad("Detected transfer money intent.")
            context.metadata["intent"] = "money_transfer"
            return "", "gather_transfer_details", {"metadata": context.metadata}

        elif any(term in input_lower for term in ["bill", "pay", "payment"]):
            self.write_to_scratchpad("Detected bill payment intent.")
            context.metadata["intent"] = "bill_payment"
            return "", "gather_bill_pay_details", {"metadata": context.metadata}

        else:
            self.write_to_scratchpad("Intent unclear. Requesting clarification.")

            response = "I'm not sure what you'd like to do. Would you like to check your balance, transfer money, or pay a bill?"

            context.conversation_history.append(
                {"role": "assistant", "content": response}
            )

            return (
                response,
                "clarification_needed",
                {"conversation_history": context.conversation_history},
            )


class GatherBalanceDetailsState(FSAState):
    """Gathers details needed for a balance inquiry."""

    def __init__(self):
        transitions = [
            StateTransition(
                target_state="confirm_action", condition="Details collected"
            ),
            StateTransition(target_state="main_menu", condition="Cancel operation"),
        ]
        super().__init__(
            name="gather_balance_details",
            description="Collects account details for balance inquiry",
            allowed_transitions=transitions,
        )

    async def process(
        self, input_text: str, context: StateContext
    ) -> Tuple[str, Optional[str], Dict[str, Any]]:
        self.write_to_scratchpad(
            "Gathering details for balance inquiry.\n"
            "For simplicity, we'll just ask which account the user wants to check."
        )

        # If no account type is specified yet, ask for it
        if "account_type" not in context.metadata:
            response = "Which account would you like to check the balance for? (Checking, Savings, Credit Card)"

            context.conversation_history.append(
                {"role": "assistant", "content": response}
            )

            # Stay in current state until user provides account type
            return (
                response,
                None,
                {"conversation_history": context.conversation_history},
            )

        # Add to conversation history
        context.conversation_history.append({"role": "user", "content": input_text})

        input_lower = input_text.lower()

        # Check for cancellation
        if any(term in input_lower for term in ["cancel", "stop", "back", "main menu"]):
            self.write_to_scratchpad("User wants to cancel. Returning to main menu.")

            # Clear the current operation data
            if "account_type" in context.metadata:
                del context.metadata["account_type"]

            response = "Operation cancelled. Returning to main menu."

            context.conversation_history.append(
                {"role": "assistant", "content": response}
            )

            return (
                response,
                "main_menu",
                {
                    "conversation_history": context.conversation_history,
                    "metadata": context.metadata,
                },
            )

        # Process account type selection
        account_type = None
        if "checking" in input_lower:
            account_type = "checking"
        elif "savings" in input_lower:
            account_type = "savings"
        elif "credit" in input_lower or "card" in input_lower:
            account_type = "credit_card"

        if account_type:
            self.write_to_scratchpad(
                f"User selected {account_type} account. All details collected."
            )

            # Store account type in context
            context.metadata["account_type"] = account_type

            # Transition to confirm action
            return "", "confirm_action", {"metadata": context.metadata}
        else:
            # Invalid account type, ask again
            response = "I didn't recognize that account type. Please specify Checking, Savings, or Credit Card."

            context.conversation_history.append(
                {"role": "assistant", "content": response}
            )

            return (
                response,
                None,
                {"conversation_history": context.conversation_history},
            )


class GatherTransferDetailsState(FSAState):
    """Gathers details needed for a money transfer."""

    def __init__(self):
        transitions = [
            StateTransition(
                target_state="confirm_action", condition="Details collected"
            ),
            StateTransition(target_state="main_menu", condition="Cancel operation"),
            StateTransition(
                target_state="clarification_needed",
                condition="Information missing or ambiguous",
            ),
        ]
        super().__init__(
            name="gather_transfer_details",
            description="Collects details for money transfer",
            allowed_transitions=transitions,
        )

    async def process(
        self, input_text: str, context: StateContext
    ) -> Tuple[str, Optional[str], Dict[str, Any]]:
        self.write_to_scratchpad(
            f"Processing transfer input: '{input_text}'\n"
            "Gathering source account, destination account, and amount."
        )

        # Add to conversation history
        context.conversation_history.append({"role": "user", "content": input_text})

        input_lower = input_text.lower()

        # Check for cancellation
        if any(term in input_lower for term in ["cancel", "stop", "back", "main menu"]):
            self.write_to_scratchpad("User wants to cancel. Returning to main menu.")

            # Clear the current operation data
            transfer_fields = ["source_account", "destination_account", "amount"]
            for field in transfer_fields:
                if field in context.metadata:
                    del context.metadata[field]

            response = "Transfer cancelled. Returning to main menu."

            context.conversation_history.append(
                {"role": "assistant", "content": response}
            )

            return (
                response,
                "main_menu",
                {
                    "conversation_history": context.conversation_history,
                    "metadata": context.metadata,
                },
            )

        # Gather transfer details in sequence
        if "source_account" not in context.metadata:
            # First, get the source account
            response = "From which account would you like to transfer funds? (Checking or Savings)"

            context.conversation_history.append(
                {"role": "assistant", "content": response}
            )

            # Stay in current state until user provides source account
            return (
                response,
                None,
                {"conversation_history": context.conversation_history},
            )

        elif (
            "source_account" in context.metadata
            and "destination_account" not in context.metadata
        ):
            # Process source account input
            source_account = None
            if "checking" in input_lower:
                source_account = "checking"
            elif "savings" in input_lower:
                source_account = "savings"

            if source_account:
                # Store source account and ask for destination
                context.metadata["source_account"] = source_account

                response = "To which account or recipient would you like to transfer? (Account number or name)"

                context.conversation_history.append(
                    {"role": "assistant", "content": response}
                )

                return (
                    response,
                    None,
                    {
                        "conversation_history": context.conversation_history,
                        "metadata": context.metadata,
                    },
                )
            else:
                # Invalid source account, ask again
                response = "I didn't recognize that account. Please specify Checking or Savings."

                context.conversation_history.append(
                    {"role": "assistant", "content": response}
                )

                return (
                    response,
                    None,
                    {"conversation_history": context.conversation_history},
                )

        elif "destination_account" not in context.metadata:
            # Store destination and ask for amount
            context.metadata["destination_account"] = input_text

            response = "How much would you like to transfer?"

            context.conversation_history.append(
                {"role": "assistant", "content": response}
            )

            return (
                response,
                None,
                {
                    "conversation_history": context.conversation_history,
                    "metadata": context.metadata,
                },
            )

        elif "amount" not in context.metadata:
            # Process amount input - extract numeric value
            import re

            amount_match = re.search(r"\$?(\d+(?:\.\d+)?)", input_text)

            if amount_match:
                amount = float(amount_match.group(1))
                context.metadata["amount"] = amount

                self.write_to_scratchpad(
                    "All transfer details collected. Moving to confirmation."
                )

                # All details collected, move to confirmation
                return "", "confirm_action", {"metadata": context.metadata}
            else:
                # Invalid amount, ask again
                response = "I couldn't identify a valid amount. Please enter a dollar amount (e.g., $100.50)."

                context.conversation_history.append(
                    {"role": "assistant", "content": response}
                )

                return (
                    response,
                    None,
                    {"conversation_history": context.conversation_history},
                )

        # Should not reach here if state is working correctly
        return "", "main_menu", {"conversation_history": context.conversation_history}


class GatherBillPayDetailsState(FSAState):
    """Gathers details needed for bill payment."""

    def __init__(self):
        transitions = [
            StateTransition(
                target_state="confirm_action", condition="Details collected"
            ),
            StateTransition(target_state="main_menu", condition="Cancel operation"),
            StateTransition(
                target_state="clarification_needed",
                condition="Information missing or ambiguous",
            ),
        ]
        super().__init__(
            name="gather_bill_pay_details",
            description="Collects details for bill payment",
            allowed_transitions=transitions,
        )

    async def process(
        self, input_text: str, context: StateContext
    ) -> Tuple[str, Optional[str], Dict[str, Any]]:
        self.write_to_scratchpad(
            f"Processing bill payment input: '{input_text}'\n"
            "Gathering payee, source account, and amount."
        )

        # Add to conversation history
        context.conversation_history.append({"role": "user", "content": input_text})

        input_lower = input_text.lower()

        # Check for cancellation
        if any(term in input_lower for term in ["cancel", "stop", "back", "main menu"]):
            self.write_to_scratchpad("User wants to cancel. Returning to main menu.")

            # Clear the current operation data
            bill_pay_fields = ["payee", "source_account", "amount"]
            for field in bill_pay_fields:
                if field in context.metadata:
                    del context.metadata[field]

            response = "Bill payment cancelled. Returning to main menu."

            context.conversation_history.append(
                {"role": "assistant", "content": response}
            )

            return (
                response,
                "main_menu",
                {
                    "conversation_history": context.conversation_history,
                    "metadata": context.metadata,
                },
            )

        # Gather bill payment details in sequence
        if "payee" not in context.metadata:
            # First, get the payee
            response = "Which company or service would you like to pay?"

            context.conversation_history.append(
                {"role": "assistant", "content": response}
            )

            # Stay in current state until user provides payee
            return (
                response,
                None,
                {"conversation_history": context.conversation_history},
            )

        elif "payee" in context.metadata and "source_account" not in context.metadata:
            # Store payee and ask for source account
            context.metadata["payee"] = input_text

            response = "From which account would you like to make this payment? (Checking or Savings)"

            context.conversation_history.append(
                {"role": "assistant", "content": response}
            )

            return (
                response,
                None,
                {
                    "conversation_history": context.conversation_history,
                    "metadata": context.metadata,
                },
            )

        elif "source_account" not in context.metadata:
            # Process source account input
            source_account = None
            if "checking" in input_lower:
                source_account = "checking"
            elif "savings" in input_lower:
                source_account = "savings"

            if source_account:
                # Store source account and ask for amount
                context.metadata["source_account"] = source_account

                response = "How much would you like to pay?"

                context.conversation_history.append(
                    {"role": "assistant", "content": response}
                )

                return (
                    response,
                    None,
                    {
                        "conversation_history": context.conversation_history,
                        "metadata": context.metadata,
                    },
                )
            else:
                # Invalid source account, ask again
                response = "I didn't recognize that account. Please specify Checking or Savings."

                context.conversation_history.append(
                    {"role": "assistant", "content": response}
                )

                return (
                    response,
                    None,
                    {"conversation_history": context.conversation_history},
                )

        elif "amount" not in context.metadata:
            # Process amount input - extract numeric value
            import re

            amount_match = re.search(r"\$?(\d+(?:\.\d+)?)", input_text)

            if amount_match:
                amount = float(amount_match.group(1))
                context.metadata["amount"] = amount

                self.write_to_scratchpad(
                    "All bill payment details collected. Moving to confirmation."
                )

                # All details collected, move to confirmation
                return "", "confirm_action", {"metadata": context.metadata}
            else:
                # Invalid amount, ask again
                response = "I couldn't identify a valid amount. Please enter a dollar amount (e.g., $100.50)."

                context.conversation_history.append(
                    {"role": "assistant", "content": response}
                )

                return (
                    response,
                    None,
                    {"conversation_history": context.conversation_history},
                )

        # Should not reach here if state is working correctly
        return "", "main_menu", {"conversation_history": context.conversation_history}


class ConfirmActionState(FSAState):
    """Asks for confirmation before executing a banking transaction."""

    def __init__(self):
        transitions = [
            StateTransition(
                target_state="executing_transaction", condition="User confirms"
            ),
            StateTransition(target_state="main_menu", condition="User cancels"),
        ]
        super().__init__(
            name="confirm_action",
            description="Gets user confirmation before proceeding",
            allowed_transitions=transitions,
        )

    async def process(
        self, input_text: str, context: StateContext
    ) -> Tuple[str, Optional[str], Dict[str, Any]]:
        # First check if we need to display the confirmation message
        if not input_text:
            # Generate confirmation message based on intent
            intent = context.metadata.get("intent")
            confirmation_message = ""

            if intent == "balance_inquiry":
                account_type = context.metadata.get("account_type", "unknown")
                confirmation_message = f"You're about to check the balance of your {account_type} account. Proceed? (Yes/No)"

            elif intent == "money_transfer":
                source = context.metadata.get("source_account", "unknown")
                destination = context.metadata.get("destination_account", "unknown")
                amount = context.metadata.get("amount", 0)
                confirmation_message = f"You're about to transfer ${amount:.2f} from your {source} account to {destination}. Proceed? (Yes/No)"

            elif intent == "bill_payment":
                payee = context.metadata.get("payee", "unknown")
                source = context.metadata.get("source_account", "unknown")
                amount = context.metadata.get("amount", 0)
                confirmation_message = f"You're about to pay ${amount:.2f} to {payee} from your {source} account. Proceed? (Yes/No)"

            self.write_to_scratchpad(f"Asking for confirmation: {confirmation_message}")

            context.conversation_history.append(
                {"role": "assistant", "content": confirmation_message}
            )

            return (
                confirmation_message,
                None,
                {"conversation_history": context.conversation_history},
            )

        # Add to conversation history
        context.conversation_history.append({"role": "user", "content": input_text})

        # Process the user's confirmation response
        input_lower = input_text.lower()

        if any(
            term in input_lower
            for term in ["yes", "yeah", "proceed", "confirm", "ok", "sure"]
        ):
            self.write_to_scratchpad(
                "User confirmed the action. Proceeding to execute transaction."
            )
            return (
                "",
                "executing_transaction",
                {"conversation_history": context.conversation_history},
            )

        else:
            self.write_to_scratchpad(
                "User cancelled the action. Returning to main menu."
            )

            response = "Operation cancelled. Returning to main menu."

            context.conversation_history.append(
                {"role": "assistant", "content": response}
            )

            return (
                response,
                "main_menu",
                {"conversation_history": context.conversation_history},
            )


class ExecutingTransactionState(FSAState):
    """Executes the banking transaction."""

    def __init__(self):
        transitions = [
            StateTransition(
                target_state="reporting_success", condition="Transaction successful"
            ),
            StateTransition(
                target_state="reporting_failure", condition="Transaction failed"
            ),
            StateTransition(target_state="handling_error", condition="Error occurred"),
        ]
        super().__init__(
            name="executing_transaction",
            description="Processes the banking transaction",
            allowed_transitions=transitions,
        )

    async def process(
        self, input_text: str, context: StateContext
    ) -> Tuple[str, Optional[str], Dict[str, Any]]:
        self.write_to_scratchpad(
            "Executing the requested transaction.\n"
            "In a real system, this would interact with banking APIs."
        )

        intent = context.metadata.get("intent")

        # Simulate transaction processing
        import random

        success_rate = 0.95  # 5% chance of failure for demo purposes
        transaction_success = random.random() < success_rate

        if transaction_success:
            self.write_to_scratchpad("Transaction completed successfully.")

            # For balance inquiries, generate a random balance
            if intent == "balance_inquiry":
                account_type = context.metadata.get("account_type")
                if account_type == "checking":
                    balance = random.uniform(500, 5000)
                elif account_type == "savings":
                    balance = random.uniform(1000, 10000)
                elif account_type == "credit_card":
                    balance = random.uniform(0, 3000)
                else:
                    balance = 0

                # Store the result in the context for the reporting state
                context.metadata["transaction_result"] = {
                    "success": True,
                    "balance": balance,
                    "account_type": account_type,
                }

            # For transfers and bill payments, just store success
            else:
                context.metadata["transaction_result"] = {
                    "success": True,
                    "amount": context.metadata.get("amount", 0),
                }

            return "", "reporting_success", {"metadata": context.metadata}

        else:
            self.write_to_scratchpad("Transaction failed.")

            # Store the failure in the context for the reporting state
            error_reasons = [
                "Insufficient funds",
                "System temporarily unavailable",
                "Account restrictions",
                "Daily limit exceeded",
            ]
            error_reason = random.choice(error_reasons)

            context.metadata["transaction_result"] = {
                "success": False,
                "error_reason": error_reason,
            }

            return "", "reporting_failure", {"metadata": context.metadata}


class ReportingSuccessState(FSAState):
    """Reports successful transaction to the user."""

    def __init__(self):
        transitions = [
            StateTransition(target_state="main_menu", condition="Return to main menu"),
            StateTransition(
                target_state="ending_interaction", condition="End interaction"
            ),
        ]
        super().__init__(
            name="reporting_success",
            description="Informs user of successful transaction",
            allowed_transitions=transitions,
        )

    async def process(
        self, input_text: str, context: StateContext
    ) -> Tuple[str, Optional[str], Dict[str, Any]]:
        self.write_to_scratchpad(
            "Reporting successful transaction to user.\n"
            "Generating appropriate success message based on transaction type."
        )

        intent = context.metadata.get("intent")
        result = context.metadata.get("transaction_result", {})
        success_message = ""

        if intent == "balance_inquiry":
            account_type = result.get("account_type", "account")
            balance = result.get("balance", 0)
            success_message = f"Your {account_type} balance is ${balance:.2f}."

        elif intent == "money_transfer":
            amount = result.get("amount", 0)
            destination = context.metadata.get("destination_account", "the recipient")
            success_message = (
                f"Successfully transferred ${amount:.2f} to {destination}."
            )

        elif intent == "bill_payment":
            amount = result.get("amount", 0)
            payee = context.metadata.get("payee", "the payee")
            success_message = f"Successfully paid ${amount:.2f} to {payee}."

        success_message += " Is there anything else you'd like to do today? (or type 'exit' to end the session)"

        context.conversation_history.append(
            {"role": "assistant", "content": success_message}
        )

        # If this is the first time processing, return the success message
        if not input_text:
            return (
                success_message,
                None,
                {"conversation_history": context.conversation_history},
            )

        # Otherwise process the user's response
        context.conversation_history.append({"role": "user", "content": input_text})

        input_lower = input_text.lower()

        if any(
            term in input_lower
            for term in ["exit", "quit", "log out", "logout", "no", "bye"]
        ):
            return (
                "",
                "ending_interaction",
                {"conversation_history": context.conversation_history},
            )
        else:
            return (
                "",
                "main_menu",
                {"conversation_history": context.conversation_history},
            )


class ReportingFailureState(FSAState):
    """Reports failed transaction to the user."""

    def __init__(self):
        transitions = [
            StateTransition(target_state="main_menu", condition="Return to main menu"),
            StateTransition(
                target_state="ending_interaction", condition="End interaction"
            ),
        ]
        super().__init__(
            name="reporting_failure",
            description="Informs user of transaction failure",
            allowed_transitions=transitions,
        )

    async def process(
        self, input_text: str, context: StateContext
    ) -> Tuple[str, Optional[str], Dict[str, Any]]:
        self.write_to_scratchpad(
            "Reporting transaction failure to user.\n"
            "Generating appropriate failure message based on error reason."
        )

        result = context.metadata.get("transaction_result", {})
        error_reason = result.get("error_reason", "Unknown error")

        failure_message = f"I'm sorry, but the transaction could not be completed. Reason: {error_reason}. "
        failure_message += "Would you like to return to the main menu or end the session? (Main Menu/Exit)"

        context.conversation_history.append(
            {"role": "assistant", "content": failure_message}
        )

        # If this is the first time processing, return the failure message
        if not input_text:
            return (
                failure_message,
                None,
                {"conversation_history": context.conversation_history},
            )

        # Otherwise process the user's response
        context.conversation_history.append({"role": "user", "content": input_text})

        input_lower = input_text.lower()

        if any(
            term in input_lower for term in ["exit", "quit", "log out", "logout", "end"]
        ):
            return (
                "",
                "ending_interaction",
                {"conversation_history": context.conversation_history},
            )
        else:
            return (
                "",
                "main_menu",
                {"conversation_history": context.conversation_history},
            )


class ClarificationNeededState(FSAState):
    """Handles unclear user requests by asking for clarification."""

    def __init__(self):
        transitions = [
            StateTransition(
                target_state="identify_intent", condition="Clear intent provided"
            ),
            StateTransition(target_state="main_menu", condition="Return to main menu"),
        ]
        super().__init__(
            name="clarification_needed",
            description="Requests clarification for unclear intents",
            allowed_transitions=transitions,
        )

    async def process(
        self, input_text: str, context: StateContext
    ) -> Tuple[str, Optional[str], Dict[str, Any]]:
        self.write_to_scratchpad(
            f"Processing clarification response: '{input_text}'\n"
            "Determining if user has clarified their intent."
        )

        # Add to conversation history
        context.conversation_history.append({"role": "user", "content": input_text})

        input_lower = input_text.lower()

        # Check if user has provided clear intent
        if any(term in input_lower for term in ["balance", "check"]):
            self.write_to_scratchpad("User clarified they want to check balance.")
            context.metadata["intent"] = "balance_inquiry"
            return "", "identify_intent", {"metadata": context.metadata}

        elif any(term in input_lower for term in ["transfer", "send", "move"]):
            self.write_to_scratchpad("User clarified they want to transfer money.")
            context.metadata["intent"] = "money_transfer"
            return "", "identify_intent", {"metadata": context.metadata}

        elif any(term in input_lower for term in ["bill", "pay"]):
            self.write_to_scratchpad("User clarified they want to pay a bill.")
            context.metadata["intent"] = "bill_payment"
            return "", "identify_intent", {"metadata": context.metadata}

        elif any(term in input_lower for term in ["menu", "options", "main", "back"]):
            self.write_to_scratchpad("User wants to return to main menu.")

            response = "Returning to the main menu."

            context.conversation_history.append(
                {"role": "assistant", "content": response}
            )

            return (
                response,
                "main_menu",
                {"conversation_history": context.conversation_history},
            )

        else:
            self.write_to_scratchpad(
                "Still unclear what user wants. Asking again with more specific options."
            )

            response = (
                "I'm still not clear on what you'd like to do. Please choose one of the following:\n"
                "1. Check account balance\n"
                "2. Transfer money\n"
                "3. Pay a bill\n"
                "4. Return to main menu"
            )

            context.conversation_history.append(
                {"role": "assistant", "content": response}
            )

            # Stay in current state
            return (
                response,
                None,
                {"conversation_history": context.conversation_history},
            )


class HandlingErrorState(FSAState):
    """Handles unexpected errors during processing."""

    def __init__(self):
        transitions = [
            StateTransition(target_state="main_menu", condition="Return to main menu"),
            StateTransition(
                target_state="ending_interaction", condition="End interaction"
            ),
        ]
        super().__init__(
            name="handling_error",
            description="Manages unexpected system errors",
            allowed_transitions=transitions,
        )

    async def process(
        self, input_text: str, context: StateContext
    ) -> Tuple[str, Optional[str], Dict[str, Any]]:
        self.write_to_scratchpad(
            "Handling unexpected error.\n"
            "In a production system, this would log details and potentially alert support."
        )

        # Generate error message if first time entering this state
        if not input_text:
            error_message = (
                "I apologize, but an unexpected error occurred while processing your request. "
                "Would you like to return to the main menu or end this session? (Main Menu/Exit)"
            )

            context.conversation_history.append(
                {"role": "assistant", "content": error_message}
            )

            return (
                error_message,
                None,
                {"conversation_history": context.conversation_history},
            )

        # Add to conversation history
        context.conversation_history.append({"role": "user", "content": input_text})

        input_lower = input_text.lower()

        # Determine where to go based on user input
        if any(term in input_lower for term in ["main", "menu", "continue"]):
            self.write_to_scratchpad("User wants to continue to main menu.")

            response = "Returning to the main menu."

            context.conversation_history.append(
                {"role": "assistant", "content": response}
            )

            return (
                response,
                "main_menu",
                {"conversation_history": context.conversation_history},
            )

        else:
            self.write_to_scratchpad("Ending the session due to error.")

            response = (
                "I understand. Ending this session. Thank you for using Bank of Peril."
            )

            context.conversation_history.append(
                {"role": "assistant", "content": response}
            )

            return (
                response,
                "ending_interaction",
                {"conversation_history": context.conversation_history},
            )


class EndingInteractionState(FSAState):
    """Final state for ending the interaction."""

    def __init__(self):
        transitions = [StateTransition(target_state="idle", condition="New session")]
        super().__init__(
            name="ending_interaction",
            description="Concludes the banking interaction",
            allowed_transitions=transitions,
        )

    async def process(
        self, input_text: str, context: StateContext
    ) -> Tuple[str, Optional[str], Dict[str, Any]]:
        self.write_to_scratchpad(
            "Ending the interaction with user.\n"
            "Providing farewell message and resetting for next interaction."
        )

        # Generate farewell message
        farewell_message = "Thank you for banking with Bank of Peril. Have a nice day!"

        context.conversation_history.append(
            {"role": "assistant", "content": farewell_message}
        )

        # Clear sensitive context data
        for key in list(context.metadata.keys()):
            if key not in ["session_id"]:
                del context.metadata[key]

        # Return to idle state for next interaction
        return (
            farewell_message,
            "idle",
            {
                "conversation_history": context.conversation_history,
                "metadata": context.metadata,
            },
        )


# Dictionary of all states for easy access by name
BANK_OF_PERIL_STATES = {
    "idle": IdleState(),
    "greeting": GreetingState(),
    "authenticating": AuthenticatingState(),
    "authentication_failed": AuthenticationFailedState(),
    "main_menu": MainMenuState(),
    "identify_intent": IdentifyIntentState(),
    "gather_balance_details": GatherBalanceDetailsState(),
    "gather_transfer_details": GatherTransferDetailsState(),
    "gather_bill_pay_details": GatherBillPayDetailsState(),
    "confirm_action": ConfirmActionState(),
    "executing_transaction": ExecutingTransactionState(),
    "reporting_success": ReportingSuccessState(),
    "reporting_failure": ReportingFailureState(),
    "clarification_needed": ClarificationNeededState(),
    "handling_error": HandlingErrorState(),
    "ending_interaction": EndingInteractionState(),
}
