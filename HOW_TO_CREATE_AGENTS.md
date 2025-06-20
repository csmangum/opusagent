# How to Create and Add a New Agent

This guide walks you through creating a new conversation agent for the voice agent system. We'll use a Loan Application Agent as an example to demonstrate all the necessary steps.

## Overview

The agent system provides a clean abstraction for handling different types of conversations. Each agent:
- Manages conversation state and flow progression
- Coordinates with the existing flow system for tools and functions
- Provides business logic specific to its domain
- Integrates seamlessly with any platform bridge (AudioCodes, Twilio, etc.)

## Step 1: Define Your Agent's Workflow

Before coding, map out your agent's conversation stages and the data you need to collect.

**Example: Loan Application Agent Stages**
```
1. Greeting - Welcome the customer
2. Loan Type Selection - Determine loan type (personal, auto, mortgage)
3. Amount Collection - Get desired loan amount
4. Income Verification - Collect income information
5. Employment Verification - Verify employment details
6. Credit Check Consent - Get permission for credit check
7. Application Submission - Submit the application
8. Pre-approval - Provide pre-approval decision
9. Completion - Wrap up or transfer to human
```

## Step 2: Create the Agent Class

Create a new file `opusagent/agents/loan_application_agent.py`:

```python
"""
Loan Application Agent implementation.

This agent handles the complete loan application conversation flow,
managing state transitions and business logic for loan requests.
"""

from typing import Dict, List, Any, Optional
from enum import Enum

from opusagent.config.logging_config import configure_logging
from opusagent.flows.loan_application.flow import LoanApplicationFlow
from opusagent.flows.loan_application.functions import get_loan_application_functions
from .base_agent import BaseAgent, AgentContext, AgentResponse, AgentStatus, ResponseType

logger = configure_logging("loan_application_agent")


class LoanApplicationStage(str, Enum):
    """Stages in the loan application flow."""
    GREETING = "greeting"
    LOAN_TYPE_SELECTION = "loan_type_selection"
    AMOUNT_COLLECTION = "amount_collection"
    INCOME_VERIFICATION = "income_verification"
    EMPLOYMENT_VERIFICATION = "employment_verification"
    CREDIT_CHECK_CONSENT = "credit_check_consent"
    APPLICATION_SUBMISSION = "application_submission"
    PRE_APPROVAL = "pre_approval"
    COMPLETION = "completion"
    TRANSFER = "transfer"


class LoanApplicationAgent(BaseAgent):
    """
    Agent for handling loan application conversations.
    
    This agent manages the complete loan application flow including:
    - Loan type and amount collection
    - Income and employment verification
    - Credit check consent
    - Application submission and pre-approval
    """
    
    def __init__(self, agent_id: str = "loan_application", name: str = "Loan Application Agent"):
        """Initialize the loan application agent."""
        super().__init__(agent_id, name)
        
        # Initialize flow system
        self.flow = LoanApplicationFlow()
        self.functions = get_loan_application_functions()
        
        # Stage tracking
        self.current_stage = LoanApplicationStage.GREETING
        
        # Application data tracking
        self.customer_verified = False
        self.loan_type = None
        self.loan_amount = None
        self.income_verified = False
        self.employment_verified = False
        self.credit_consent = False
        self.application_submitted = False
        
    async def initialize(self, context: AgentContext) -> AgentResponse:
        """Initialize the agent with conversation context."""
        self.conversation_context = context
        self.update_status(AgentStatus.ACTIVE)
        self.set_current_stage(LoanApplicationStage.GREETING.value)
        
        logger.info(f"Initialized loan application agent for conversation: {context.conversation_id}")
        
        # Start with greeting
        return self.create_response(
            ResponseType.CONTINUE,
            message="Hello! I'm here to help you with your loan application. Let's get started!",
            next_stage=LoanApplicationStage.LOAN_TYPE_SELECTION.value
        )
    
    async def process_user_input(self, user_input: str, context: AgentContext) -> AgentResponse:
        """Process user input and determine next steps."""
        self.update_status(AgentStatus.PROCESSING)
        
        # Update conversation history
        context.add_conversation_entry("user", user_input)
        
        # Process based on current stage
        try:
            if self.current_stage == LoanApplicationStage.GREETING.value:
                return await self._handle_greeting(user_input, context)
            elif self.current_stage == LoanApplicationStage.LOAN_TYPE_SELECTION.value:
                return await self._handle_loan_type_selection(user_input, context)
            elif self.current_stage == LoanApplicationStage.AMOUNT_COLLECTION.value:
                return await self._handle_amount_collection(user_input, context)
            elif self.current_stage == LoanApplicationStage.INCOME_VERIFICATION.value:
                return await self._handle_income_verification(user_input, context)
            elif self.current_stage == LoanApplicationStage.EMPLOYMENT_VERIFICATION.value:
                return await self._handle_employment_verification(user_input, context)
            elif self.current_stage == LoanApplicationStage.CREDIT_CHECK_CONSENT.value:
                return await self._handle_credit_check_consent(user_input, context)
            elif self.current_stage == LoanApplicationStage.APPLICATION_SUBMISSION.value:
                return await self._handle_application_submission(user_input, context)
            elif self.current_stage == LoanApplicationStage.PRE_APPROVAL.value:
                return await self._handle_pre_approval(user_input, context)
            elif self.current_stage == LoanApplicationStage.COMPLETION.value:
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
            if function_name == "loan_type_selection":
                return await self._handle_loan_type_result(result, context)
            elif function_name == "loan_amount_collection":
                return await self._handle_amount_result(result, context)
            elif function_name == "income_verification":
                return await self._handle_income_result(result, context)
            elif function_name == "employment_verification":
                return await self._handle_employment_result(result, context)
            elif function_name == "credit_check_consent":
                return await self._handle_credit_consent_result(result, context)
            elif function_name == "submit_loan_application":
                return await self._handle_submission_result(result, context)
            elif function_name == "loan_pre_approval":
                return await self._handle_pre_approval_result(result, context)
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
    
    # Stage Handlers (implement each stage's logic)
    
    async def _handle_greeting(self, user_input: str, context: AgentContext) -> AgentResponse:
        """Handle initial greeting stage."""
        self.set_current_stage(LoanApplicationStage.LOAN_TYPE_SELECTION.value)
        return self.create_response(
            ResponseType.CONTINUE,
            function_calls=[{"name": "loan_type_selection", "arguments": {"user_input": user_input}}],
            next_stage=LoanApplicationStage.LOAN_TYPE_SELECTION.value
        )
    
    async def _handle_loan_type_selection(self, user_input: str, context: AgentContext) -> AgentResponse:
        """Handle loan type selection stage."""
        return self.create_response(
            ResponseType.CONTINUE,
            function_calls=[{"name": "loan_type_selection", "arguments": {"loan_type": user_input}}]
        )
    
    async def _handle_amount_collection(self, user_input: str, context: AgentContext) -> AgentResponse:
        """Handle amount collection stage."""
        return self.create_response(
            ResponseType.CONTINUE,
            function_calls=[{"name": "loan_amount_collection", "arguments": {"amount": user_input}}]
        )
    
    # ... implement other stage handlers ...
    
    # Function Result Handlers (handle responses from each function)
    
    async def _handle_loan_type_result(self, result: Dict[str, Any], context: AgentContext) -> AgentResponse:
        """Handle loan type selection result."""
        if result.get("type_selected"):
            self.loan_type = result.get("loan_type")
            context.set_customer_data("loan_type", self.loan_type)
            
            self.set_current_stage(LoanApplicationStage.AMOUNT_COLLECTION.value)
            return self.create_response(
                ResponseType.CONTINUE,
                message=result.get("message", "Great! Now let's discuss the loan amount."),
                next_stage=LoanApplicationStage.AMOUNT_COLLECTION.value
            )
        else:
            return self.create_response(
                ResponseType.CONTINUE,
                message=result.get("message", "What type of loan are you interested in?")
            )
    
    # ... implement other function result handlers ...
    
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
        
        # Add loan application specific validation
        loan_validation = {
            "customer_verified": self.customer_verified,
            "loan_type_collected": self.loan_type is not None,
            "loan_amount_collected": self.loan_amount is not None,
            "income_verified": self.income_verified,
            "employment_verified": self.employment_verified,
            "credit_consent": self.credit_consent,
            "application_submitted": self.application_submitted,
            "flow_valid": self.flow.validate_flow_configuration()["valid"]
        }
        
        base_validation.update(loan_validation)
        return base_validation
```

## Step 3: Register the Agent

Update `opusagent/agents/bootstrap.py` to register your new agent:

```python
def register_core_agents():
    """Register all core agents with the agent registry."""
    
    # Existing card replacement agent registration...
    
    # Register Loan Application Agent
    agent_registry.register_agent(
        agent_class=LoanApplicationAgent,
        agent_id="loan_application",
        name="Loan Application Agent",
        description="Handles loan application requests including type selection, verification, and approval",
        keywords=[
            "loan", "application", "apply", "borrow", "lending", "personal loan",
            "auto loan", "mortgage", "finance", "credit", "money"
        ],
        priority=9,  # High priority for loan applications
        enabled=True
    )
    
    logger.info("Registered core agents with the registry")
```

## Step 4: Update Agent Module Exports

Add your new agent to `opusagent/agents/__init__.py`:

```python
from .loan_application_agent import LoanApplicationAgent

__all__ = [
    # ... existing exports ...
    "LoanApplicationAgent",
]
```

## Step 5: Create Tests

Create `test_loan_application_agent.py`:

```python
import asyncio
import pytest
from opusagent.agents.loan_application_agent import LoanApplicationAgent, LoanApplicationStage
from opusagent.agents.base_agent import AgentContext, AgentStatus, ResponseType


@pytest.mark.asyncio
async def test_loan_application_agent_initialization():
    """Test loan application agent initialization."""
    agent = LoanApplicationAgent()
    context = AgentContext(
        conversation_id="test-loan-001",
        session_id="test-session-001"
    )
    
    response = await agent.initialize(context)
    
    assert response.response_type == ResponseType.CONTINUE
    assert agent.status == AgentStatus.ACTIVE
    assert agent.current_stage == LoanApplicationStage.GREETING.value
    assert "loan application" in response.message.lower()


@pytest.mark.asyncio
async def test_loan_type_selection():
    """Test loan type selection process."""
    agent = LoanApplicationAgent()
    context = AgentContext(
        conversation_id="test-loan-002",
        session_id="test-session-002"
    )
    
    # Initialize agent
    await agent.initialize(context)
    
    # Process loan type input
    response = await agent.process_user_input("I need a personal loan", context)
    
    assert response.response_type == ResponseType.CONTINUE
    assert len(response.function_calls) == 1
    assert response.function_calls[0]["name"] == "loan_type_selection"


@pytest.mark.asyncio
async def test_full_loan_application_flow():
    """Test complete loan application conversation flow."""
    agent = LoanApplicationAgent()
    context = AgentContext(
        conversation_id="test-loan-003",
        session_id="test-session-003"
    )
    
    # Initialize
    response = await agent.initialize(context)
    assert response.response_type == ResponseType.CONTINUE
    
    # Simulate successful progression through stages
    test_inputs = [
        ("I need a personal loan", "loan_type_selection"),
        ("I want to borrow $25,000", "loan_amount_collection"),
        ("I make $75,000 per year", "income_verification"),
        ("I work at Tech Corp for 3 years", "employment_verification"),
        ("Yes, you can check my credit", "credit_check_consent"),
        ("Please submit my application", "submit_loan_application"),
        ("Thank you", "wrap_up")
    ]
    
    for user_input, expected_function in test_inputs:
        response = await agent.process_user_input(user_input, context)
        
        assert response.response_type == ResponseType.CONTINUE
        if response.function_calls:
            assert response.function_calls[0]["name"] == expected_function


if __name__ == "__main__":
    asyncio.run(test_loan_application_agent_initialization())
    asyncio.run(test_loan_type_selection())
    asyncio.run(test_full_loan_application_flow())
    print("✅ All loan application agent tests passed!")
```

## Step 6: Test Your Agent

Run the test to verify your agent works:

```bash
python test_loan_application_agent.py
```

Test with the main system:

```python
# In test_agent_system.py or a new test file
from opusagent.agents import bootstrap_agent_system, get_agent_system_info

# Bootstrap system with your new agent
bootstrap_result = bootstrap_agent_system()
print("Bootstrap result:", bootstrap_result)

# Check that your agent is registered
system_info = get_agent_system_info()
agents = system_info["available_agents"]
print("Available agents:", [agent["agent_id"] for agent in agents])

# Test agent creation by intent
from opusagent.agents import default_factory, AgentContext

context = AgentContext(
    conversation_id="test-loan-intent",
    session_id="test-session-intent"
)

# Should select your loan agent
agent = await default_factory.create_agent_by_intent(
    intent_keywords=["loan", "application"],
    context=context
)

print(f"Created agent: {agent.agent_id} ({agent.name})")
```

## Step 7: Use Your Agent

Your agent can now be used in several ways:

### Via WebSocket with Intent
```
ws://localhost:8000/ws/telephony?intent=loan,application,personal
```

### Via WebSocket with Agent ID
```
ws://localhost:8000/ws/telephony?agent_id=loan_application
```

### Programmatically
```python
from opusagent.agents import default_factory, AgentContext

context = AgentContext(conversation_id="loan-123", session_id="session-123")
agent = await default_factory.create_agent("loan_application", context)
```

## Best Practices

### 1. State Management
- Always update agent state in function result handlers
- Store important data in both agent instance and context
- Use meaningful stage names that reflect the conversation flow

### 2. Error Handling
- Wrap stage handlers in try-catch blocks
- Provide helpful error messages to users
- Log errors for debugging

### 3. Function Integration
- Leverage existing flow system functions when possible
- Create agent-specific functions only when needed
- Keep function logic separate from agent logic

### 4. Testing
- Test each stage transition
- Test error conditions and edge cases
- Test integration with the bridge system

### 5. Keywords and Intent
- Choose keywords that users naturally say
- Include variations and synonyms
- Test intent matching with real user phrases

### 6. System Instructions
- Write clear, specific system instructions
- Include information about the agent's capabilities
- Provide examples of how the agent should respond

## Advanced Features

### Agent Switching
Your agent can transfer to another agent:

```python
def create_switch_response(self, new_agent_id: str, transfer_data: Dict[str, Any]) -> AgentResponse:
    """Create an agent switch response."""
    return AgentResponse(
        response_type=ResponseType.SWITCH_AGENT,
        message="Let me transfer you to a specialist.",
        metadata={"new_agent_id": new_agent_id, "transfer_data": transfer_data}
    )
```

### Dynamic Function Registration
Register additional functions at runtime:

```python
def __init__(self, agent_id: str = "loan_application", name: str = "Loan Application Agent"):
    super().__init__(agent_id, name)
    
    # Register additional functions
    self.register_custom_function("special_loan_check", self._special_loan_check)

def register_custom_function(self, name: str, func):
    """Register a custom function for this agent."""
    # Implementation depends on your flow system
    pass
```

### Context Persistence
Save and restore agent state:

```python
def save_state(self) -> Dict[str, Any]:
    """Save agent state for persistence."""
    return {
        "current_stage": self.current_stage,
        "loan_type": self.loan_type,
        "loan_amount": self.loan_amount,
        # ... other state data
    }

def restore_state(self, state: Dict[str, Any]):
    """Restore agent state from persistence."""
    self.current_stage = state.get("current_stage", LoanApplicationStage.GREETING.value)
    self.loan_type = state.get("loan_type")
    self.loan_amount = state.get("loan_amount")
    # ... restore other state data
```

## Troubleshooting

### Agent Not Found
- Check that bootstrap system ran successfully
- Verify agent is registered in `bootstrap.py`
- Check for import errors in agent module

### Intent Not Matching
- Test your keywords with different user phrases
- Check keyword priority and scoring
- Add more variations to your keyword list

### Functions Not Working
- Ensure your flow system provides the required functions
- Check function names match between agent and flow
- Verify function signatures are correct

### State Not Persisting
- Make sure you're updating both agent and context state
- Check that stage transitions are working correctly
- Verify context is being passed correctly

Your new agent is now ready to handle conversations in your voice agent system! 