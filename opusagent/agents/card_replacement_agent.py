"""
Card Replacement Agent implementation.

This agent handles the complete card replacement conversation flow,
managing state transitions and business logic for card replacement requests.
"""

from typing import Dict, List, Any, Optional
from enum import Enum

from opusagent.config.logging_config import configure_logging
from opusagent.flows.card_replacement.flow import CardReplacementFlow
from opusagent.flows.card_replacement.functions import get_card_replacement_functions
from .base_agent import BaseAgent, AgentContext, AgentResponse, AgentStatus, ResponseType

logger = configure_logging("card_replacement_agent")


class CardReplacementStage(str, Enum):
    """Stages in the card replacement flow."""
    GREETING = "greeting"
    INTENT_CONFIRMATION = "intent_confirmation"
    ACCOUNT_VERIFICATION = "account_verification"
    REASON_COLLECTION = "reason_collection"
    ADDRESS_CONFIRMATION = "address_confirmation"
    CARD_PROCESSING = "card_processing"
    COMPLETION = "completion"
    TRANSFER = "transfer"


class CardReplacementAgent(BaseAgent):
    """
    Agent for handling card replacement conversations.
    
    This agent manages the complete card replacement flow including:
    - Intent confirmation
    - Account verification
    - Reason collection
    - Address confirmation
    - Card processing
    - Completion or transfer to human
    """
    
    def __init__(self, agent_id: str = "card_replacement", name: str = "Card Replacement Agent"):
        """Initialize the card replacement agent."""
        super().__init__(agent_id, name)
        
        # Initialize flow system
        self.flow = CardReplacementFlow()
        self.functions = get_card_replacement_functions()
        
        # Stage tracking
        self.current_stage = CardReplacementStage.GREETING
        
        # Customer data tracking
        self.customer_verified = False
        self.replacement_reason = None
        self.address_confirmed = False
        self.card_ordered = False
        
    async def initialize(self, context: AgentContext) -> AgentResponse:
        """Initialize the agent with conversation context."""
        self.conversation_context = context
        self.update_status(AgentStatus.ACTIVE)
        self.set_current_stage(CardReplacementStage.GREETING.value)
        
        logger.info(f"Initialized card replacement agent for conversation: {context.conversation_id}")
        
        # Start with greeting and intent confirmation
        return self.create_response(
            ResponseType.CONTINUE,
            message="Hello! I understand you need help with a card replacement. I'm here to help you with that process.",
            next_stage=CardReplacementStage.INTENT_CONFIRMATION.value
        )
    
    async def process_user_input(self, user_input: str, context: AgentContext) -> AgentResponse:
        """Process user input and determine next steps."""
        self.update_status(AgentStatus.PROCESSING)
        
        # Update conversation history
        context.add_conversation_entry("user", user_input)
        
        # Process based on current stage
        try:
            if self.current_stage == CardReplacementStage.GREETING.value:
                return await self._handle_greeting(user_input, context)
            elif self.current_stage == CardReplacementStage.INTENT_CONFIRMATION.value:
                return await self._handle_intent_confirmation(user_input, context)
            elif self.current_stage == CardReplacementStage.ACCOUNT_VERIFICATION.value:
                return await self._handle_account_verification(user_input, context)
            elif self.current_stage == CardReplacementStage.REASON_COLLECTION.value:
                return await self._handle_reason_collection(user_input, context)
            elif self.current_stage == CardReplacementStage.ADDRESS_CONFIRMATION.value:
                return await self._handle_address_confirmation(user_input, context)
            elif self.current_stage == CardReplacementStage.CARD_PROCESSING.value:
                return await self._handle_card_processing(user_input, context)
            elif self.current_stage == CardReplacementStage.COMPLETION.value:
                return await self._handle_completion(user_input, context)
            else:
                return self.create_error_response(f"Unknown stage: {self.current_stage}")
                
        except Exception as e:
            logger.error(f"Error processing user input: {e}")
            return self.create_error_response("An error occurred while processing your request.")
        finally:
            self.update_status(AgentStatus.WAITING_FOR_INPUT)
    
    async def handle_function_result(self, function_name: str, result: Dict[str, Any], context: AgentContext) -> AgentResponse:
        """Handle the result of a function call."""
        logger.info(f"Handling function result: {function_name}")
        
        try:
            if function_name == "call_intent":
                return await self._handle_intent_result(result, context)
            elif function_name == "member_account_confirmation":
                return await self._handle_verification_result(result, context)
            elif function_name == "replacement_reason":
                return await self._handle_reason_result(result, context)
            elif function_name == "confirm_address":
                return await self._handle_address_result(result, context)
            elif function_name == "start_card_replacement":
                return await self._handle_card_start_result(result, context)
            elif function_name == "finish_card_replacement":
                return await self._handle_card_finish_result(result, context)
            elif function_name == "wrap_up":
                return await self._handle_wrap_up_result(result, context)
            elif function_name == "transfer_to_human":
                return await self._handle_transfer_result(result, context)
            else:
                logger.warning(f"Unknown function: {function_name}")
                return self.create_response(ResponseType.CONTINUE)
                
        except Exception as e:
            logger.error(f"Error handling function result for {function_name}: {e}")
            return self.create_error_response(f"Error processing {function_name} result.")
    
    # Stage Handlers
    
    async def _handle_greeting(self, user_input: str, context: AgentContext) -> AgentResponse:
        """Handle initial greeting stage."""
        # Move to intent confirmation
        self.set_current_stage(CardReplacementStage.INTENT_CONFIRMATION.value)
        
        # Trigger intent confirmation function
        return self.create_response(
            ResponseType.CONTINUE,
            function_calls=[{"name": "call_intent", "arguments": {"user_input": user_input}}],
            next_stage=CardReplacementStage.INTENT_CONFIRMATION.value
        )
    
    async def _handle_intent_confirmation(self, user_input: str, context: AgentContext) -> AgentResponse:
        """Handle intent confirmation stage."""
        # Let the function call handle this
        return self.create_response(
            ResponseType.CONTINUE,
            function_calls=[{"name": "call_intent", "arguments": {"user_input": user_input}}]
        )
    
    async def _handle_account_verification(self, user_input: str, context: AgentContext) -> AgentResponse:
        """Handle account verification stage."""
        return self.create_response(
            ResponseType.CONTINUE,
            function_calls=[{"name": "member_account_confirmation", "arguments": {"user_input": user_input}}]
        )
    
    async def _handle_reason_collection(self, user_input: str, context: AgentContext) -> AgentResponse:
        """Handle reason collection stage."""
        return self.create_response(
            ResponseType.CONTINUE,
            function_calls=[{"name": "replacement_reason", "arguments": {"reason": user_input}}]
        )
    
    async def _handle_address_confirmation(self, user_input: str, context: AgentContext) -> AgentResponse:
        """Handle address confirmation stage."""
        return self.create_response(
            ResponseType.CONTINUE,
            function_calls=[{"name": "confirm_address", "arguments": {"user_response": user_input}}]
        )
    
    async def _handle_card_processing(self, user_input: str, context: AgentContext) -> AgentResponse:
        """Handle card processing stage."""
        if not self.card_ordered:
            return self.create_response(
                ResponseType.CONTINUE,
                function_calls=[{"name": "start_card_replacement", "arguments": {}}]
            )
        else:
            return self.create_response(
                ResponseType.CONTINUE,
                function_calls=[{"name": "finish_card_replacement", "arguments": {}}]
            )
    
    async def _handle_completion(self, user_input: str, context: AgentContext) -> AgentResponse:
        """Handle completion stage."""
        return self.create_response(
            ResponseType.CONTINUE,
            function_calls=[{"name": "wrap_up", "arguments": {}}]
        )
    
    # Function Result Handlers
    
    async def _handle_intent_result(self, result: Dict[str, Any], context: AgentContext) -> AgentResponse:
        """Handle call_intent function result."""
        if result.get("intent_confirmed"):
            self.set_current_stage(CardReplacementStage.ACCOUNT_VERIFICATION.value)
            return self.create_response(
                ResponseType.CONTINUE,
                message=result.get("message", "Great! Let me verify your account."),
                next_stage=CardReplacementStage.ACCOUNT_VERIFICATION.value
            )
        elif result.get("transfer_requested"):
            return self.create_transfer_response(
                reason="Customer requested transfer",
                message=result.get("message")
            )
        else:
            # Stay in intent confirmation
            return self.create_response(
                ResponseType.CONTINUE,
                message=result.get("message", "I'm here to help with card replacement. How can I assist you?")
            )
    
    async def _handle_verification_result(self, result: Dict[str, Any], context: AgentContext) -> AgentResponse:
        """Handle verification function result."""
        if result.get("verified"):
            self.customer_verified = True
            context.set_customer_data("verified", True)
            context.set_customer_data("account_details", result.get("account_details", {}))
            
            self.set_current_stage(CardReplacementStage.REASON_COLLECTION.value)
            return self.create_response(
                ResponseType.CONTINUE,
                message=result.get("message", "Account verified. What's the reason for the card replacement?"),
                next_stage=CardReplacementStage.REASON_COLLECTION.value
            )
        elif result.get("transfer_to_human"):
            return self.create_transfer_response(
                reason="Verification failed",
                message=result.get("message")
            )
        else:
            # Continue verification process
            return self.create_response(
                ResponseType.CONTINUE,
                message=result.get("message", "Let me help verify your account.")
            )
    
    async def _handle_reason_result(self, result: Dict[str, Any], context: AgentContext) -> AgentResponse:
        """Handle reason collection result."""
        if result.get("reason_collected"):
            self.replacement_reason = result.get("reason")
            context.set_customer_data("replacement_reason", self.replacement_reason)
            
            self.set_current_stage(CardReplacementStage.ADDRESS_CONFIRMATION.value)
            return self.create_response(
                ResponseType.CONTINUE,
                message=result.get("message", "Thank you. Let me confirm your address."),
                next_stage=CardReplacementStage.ADDRESS_CONFIRMATION.value
            )
        else:
            return self.create_response(
                ResponseType.CONTINUE,
                message=result.get("message", "Could you tell me why you need a replacement card?")
            )
    
    async def _handle_address_result(self, result: Dict[str, Any], context: AgentContext) -> AgentResponse:
        """Handle address confirmation result."""
        if result.get("address_confirmed"):
            self.address_confirmed = True
            context.set_customer_data("address_confirmed", True)
            context.set_customer_data("address", result.get("address", {}))
            
            self.set_current_stage(CardReplacementStage.CARD_PROCESSING.value)
            return self.create_response(
                ResponseType.CONTINUE,
                message=result.get("message", "Address confirmed. Processing your card replacement."),
                next_stage=CardReplacementStage.CARD_PROCESSING.value
            )
        else:
            return self.create_response(
                ResponseType.CONTINUE,
                message=result.get("message", "Let me confirm your mailing address.")
            )
    
    async def _handle_card_start_result(self, result: Dict[str, Any], context: AgentContext) -> AgentResponse:
        """Handle card replacement start result."""
        if result.get("replacement_started"):
            self.card_ordered = True
            context.set_customer_data("card_ordered", True)
            context.set_customer_data("replacement_details", result.get("replacement_details", {}))
            
            return self.create_response(
                ResponseType.CONTINUE,
                function_calls=[{"name": "finish_card_replacement", "arguments": {}}]
            )
        else:
            return self.create_error_response(
                "Failed to start card replacement process.",
                result.get("error")
            )
    
    async def _handle_card_finish_result(self, result: Dict[str, Any], context: AgentContext) -> AgentResponse:
        """Handle card replacement completion result."""
        if result.get("replacement_completed"):
            self.set_current_stage(CardReplacementStage.COMPLETION.value)
            return self.create_response(
                ResponseType.CONTINUE,
                message=result.get("message", "Your card replacement has been processed."),
                next_stage=CardReplacementStage.COMPLETION.value
            )
        else:
            return self.create_error_response(
                "Failed to complete card replacement.",
                result.get("error")
            )
    
    async def _handle_wrap_up_result(self, result: Dict[str, Any], context: AgentContext) -> AgentResponse:
        """Handle wrap up result."""
        if result.get("call_completed"):
            return self.create_complete_response(
                result.get("message", "Thank you for calling. Your card replacement is being processed.")
            )
        else:
            return self.create_response(
                ResponseType.CONTINUE,
                message=result.get("message", "Is there anything else I can help you with?")
            )
    
    async def _handle_transfer_result(self, result: Dict[str, Any], context: AgentContext) -> AgentResponse:
        """Handle transfer to human result."""
        return self.create_transfer_response(
            reason=result.get("reason", "Customer requested transfer"),
            message=result.get("message")
        )
    
    # BaseAgent Implementation
    
    def get_available_functions(self) -> List[Dict[str, Any]]:
        """Get the list of functions this agent can use."""
        return self.flow.get_tools()
    
    def get_system_instruction(self) -> str:
        """Get the system instruction for this agent."""
        return self.flow.get_system_instruction()
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate agent configuration."""
        base_validation = super().validate_configuration()
        
        # Add card replacement specific validation
        card_validation = {
            "customer_verified": self.customer_verified,
            "replacement_reason": self.replacement_reason is not None,
            "address_confirmed": self.address_confirmed,
            "card_ordered": self.card_ordered,
            "flow_valid": self.flow.validate_flow_configuration()["valid"]
        }
        
        base_validation.update(card_validation)
        return base_validation 