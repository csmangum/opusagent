from typing import Tuple, Optional, Dict, Any
from .base import AFSMState, StateContext, StateTransition

class GreetingState(AFSMState):
    """Initial greeting state for a conversation."""
    
    def __init__(self):
        transitions = [
            StateTransition(target_state="authentication", condition="Authentication request"),
            StateTransition(target_state="general_inquiry", condition="General question")
        ]
        super().__init__(
            name="greeting",
            description="Initial greeting state that welcomes the user and identifies their needs",
            allowed_transitions=transitions
        )
    
    async def process(self, input_text: str, context: StateContext) -> Tuple[str, Optional[str], Dict[str, Any]]:
        # Example scratchpad reasoning
        self.write_to_scratchpad(
            "User has connected. I'll greet them and identify their primary need.\n"
            f"Input received: '{input_text}'\n"
            f"User context: {context.user_id or 'Unknown user'}\n"
        )
        
        # Simple example of intent detection (in reality, would likely use NLU)
        input_lower = input_text.lower()
        
        if any(term in input_lower for term in ["account", "balance", "transfer", "payment"]):
            self.write_to_scratchpad(
                "Detected finance-related inquiry. User likely needs authentication first."
            )
            
            # Add to conversation history
            context.conversation_history.append({
                "role": "user",
                "content": input_text
            })
            
            response = (
                "Welcome to our service! I'll be happy to help with your account. "
                "For security purposes, I'll need to verify your identity first."
            )
            
            context.conversation_history.append({
                "role": "assistant",
                "content": response
            })
            
            # Return response, next state, and updated context
            return response, "authentication", {"conversation_history": context.conversation_history}
            
        else:
            self.write_to_scratchpad(
                "Detected general inquiry. No authentication needed at this point."
            )
            
            # Add to conversation history
            context.conversation_history.append({
                "role": "user",
                "content": input_text
            })
            
            response = (
                "Hello! Welcome to our service. How can I help you today?"
            )
            
            context.conversation_history.append({
                "role": "assistant",
                "content": response
            })
            
            # Stay in current state for general inquiries until more specific intent is detected
            return response, "general_inquiry", {"conversation_history": context.conversation_history}


class AuthenticationState(AFSMState):
    """Handles user authentication."""
    
    def __init__(self):
        transitions = [
            StateTransition(target_state="account_verification", condition="Authentication successful"),
            StateTransition(target_state="failed_authentication", condition="Authentication failed")
        ]
        super().__init__(
            name="authentication",
            description="Verifies user identity through secure authentication",
            allowed_transitions=transitions
        )
    
    async def process(self, input_text: str, context: StateContext) -> Tuple[str, Optional[str], Dict[str, Any]]:
        # In a real implementation, this would verify credentials against a database
        self.write_to_scratchpad(
            "Need to verify user identity safely.\n"
            f"Input: '{input_text}'\n"
            "In a production system, would validate against secure credential store.\n"
            "For this example, simulating successful authentication.\n"
        )
        
        # Add to conversation history
        context.conversation_history.append({
            "role": "user",
            "content": input_text
        })
        
        # Simulate successful authentication for this example
        response = "Thank you for providing your information. Your identity has been verified."
        
        # Update context with auth status
        context.metadata["authenticated"] = True
        
        context.conversation_history.append({
            "role": "assistant",
            "content": response
        })
        
        return response, "account_verification", {
            "conversation_history": context.conversation_history,
            "metadata": context.metadata
        }


class GeneralInquiryState(AFSMState):
    """Handles general questions and inquiries."""
    
    def __init__(self):
        transitions = [
            StateTransition(target_state="authentication", condition="Account request requiring auth"),
            StateTransition(target_state="greeting", condition="New conversation topic")
        ]
        super().__init__(
            name="general_inquiry",
            description="Handles general questions that don't require authentication",
            allowed_transitions=transitions
        )
    
    async def process(self, input_text: str, context: StateContext) -> Tuple[str, Optional[str], Dict[str, Any]]:
        self.write_to_scratchpad(
            "Processing general inquiry.\n"
            f"Input: '{input_text}'\n"
            "Determining if this requires authentication or can be answered directly.\n"
        )
        
        # Add to conversation history
        context.conversation_history.append({
            "role": "user",
            "content": input_text
        })
        
        input_lower = input_text.lower()
        
        # Check if user is asking about something that requires authentication
        if any(term in input_lower for term in ["account", "balance", "login", "password"]):
            self.write_to_scratchpad(
                "User needs authentication to proceed with this request."
            )
            
            response = (
                "To access your account information, I'll need to verify your identity first. "
                "Could you please provide your account ID?"
            )
            
            context.conversation_history.append({
                "role": "assistant",
                "content": response
            })
            
            return response, "authentication", {"conversation_history": context.conversation_history}
            
        else:
            self.write_to_scratchpad(
                "This is a general question that doesn't require authentication."
            )
            
            # Simple response logic - in real implementation would use a more sophisticated system
            if "hours" in input_lower or "open" in input_lower:
                response = "Our service is available 24/7 for your convenience."
            elif "help" in input_lower:
                response = "I can assist with account inquiries, transactions, and general information. What do you need help with specifically?"
            else:
                response = "I'm here to help with any questions you might have about our services. Is there something specific you'd like to know?"
            
            context.conversation_history.append({
                "role": "assistant",
                "content": response
            })
            
            # Stay in current state
            return response, None, {"conversation_history": context.conversation_history}


class AccountVerificationState(AFSMState):
    """Handles verified account interactions."""
    
    def __init__(self):
        transitions = [
            StateTransition(target_state="account_inquiry", condition="Account inquiry"),
            StateTransition(target_state="transaction_request", condition="Transaction request")
        ]
        super().__init__(
            name="account_verification",
            description="Handles interaction after successful authentication",
            allowed_transitions=transitions
        )
    
    async def process(self, input_text: str, context: StateContext) -> Tuple[str, Optional[str], Dict[str, Any]]:
        self.write_to_scratchpad(
            "User has been authenticated. Processing their account-related request.\n"
            f"Input: '{input_text}'\n"
            "Determining if they want account information or to make a transaction.\n"
        )
        
        # Add to conversation history
        context.conversation_history.append({
            "role": "user",
            "content": input_text
        })
        
        input_lower = input_text.lower()
        
        if any(term in input_lower for term in ["balance", "statement", "transaction history", "activity"]):
            self.write_to_scratchpad(
                "User wants account information. Directing to account inquiry state."
            )
            
            response = "I'd be happy to help you with your account information. What specifically would you like to know?"
            
            context.conversation_history.append({
                "role": "assistant",
                "content": response
            })
            
            return response, "account_inquiry", {"conversation_history": context.conversation_history}
            
        elif any(term in input_lower for term in ["transfer", "send money", "payment", "pay"]):
            self.write_to_scratchpad(
                "User wants to make a transaction. Directing to transaction request state."
            )
            
            response = "I can help you with making a transaction. Please provide the details of the transaction you'd like to make."
            
            context.conversation_history.append({
                "role": "assistant",
                "content": response
            })
            
            return response, "transaction_request", {"conversation_history": context.conversation_history}
            
        else:
            self.write_to_scratchpad(
                "User's request is not specific enough. Asking for clarification while staying in current state."
            )
            
            response = "Now that you're verified, I can help with viewing your account information or making transactions. What would you like to do?"
            
            context.conversation_history.append({
                "role": "assistant",
                "content": response
            })
            
            # Stay in current state until intent is clear
            return response, None, {"conversation_history": context.conversation_history} 