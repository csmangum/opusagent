# Agent Abstraction Layer - Refactor Plan & Implementation

## Current State Analysis

### Existing Components
- **Flow System**: Well-structured with `BaseFlow`, concrete flows (`CardReplacementFlow`, `AccountInquiryFlow`), and `FlowManager`
- **Bridge Architecture**: Handles communication between platforms and OpenAI
- **Function Handler**: Contains hardcoded business logic mixed with OpenAI function management
- **Session/State Management**: Distributed across multiple classes

### Key Issues Identified
1. Agent logic is embedded in infrastructure classes (bridges, handlers)
2. Business logic is hardcoded in `FunctionHandler` 
3. Flow system exists but isn't well-integrated with the runtime system
4. No clear separation between communication layer and conversation logic
5. Difficult to create new agents without modifying core infrastructure

## Proposed Solution: Agent-Centric Architecture

### 1. Agent Abstraction Layer

Create a clean `Agent` abstraction that:
- Encapsulates conversation state and business logic
- Manages flow progression and state transitions
- Coordinates with the existing flow system
- Provides a clean interface for the bridge to interact with

### 2. Agent Class Hierarchy

```
BaseAgent (Abstract)
├── CardReplacementAgent
├── AccountInquiryAgent  
├── LoanApplicationAgent
└── ... (future agents)
```

### 3. Agent Responsibilities

#### State Management
- Track conversation progress and current step
- Maintain customer context and collected information
- Handle state persistence across the session

#### Flow Orchestration
- Use existing flow system but add session-specific logic
- Manage transitions between flow stages
- Handle error states and fallback scenarios

#### Business Logic
- Execute agent-specific business rules
- Validate customer inputs and actions
- Determine next steps based on current state

#### Integration Points
- Clean interface with bridge for communication
- Leverage existing flow system for tools/functions
- Coordinate with function handler for OpenAI interactions

### 4. Bridge Integration

#### Modify Bridge Architecture
- Accept an `Agent` instance at creation time
- Delegate business logic decisions to the agent
- Keep bridges focused purely on communication protocol

#### Agent Factory
- Create agents based on intent detection or explicit selection
- Support dynamic agent switching during conversation
- Handle agent lifecycle and cleanup

## Implementation Status: ✅ COMPLETED

### Core Components Implemented

#### 1. Base Agent Framework (`opusagent/agents/base_agent.py`)
- `BaseAgent` abstract class with conversation state management
- `AgentStatus` enum (initializing, active, waiting_for_input, processing, completed, error, transferring)
- `ResponseType` enum (continue, complete, transfer, error, switch_agent)
- `AgentContext` dataclass for conversation context with customer data, history, platform metadata
- `AgentResponse` dataclass for agent responses with function calls, next stage, metadata
- Abstract methods: `initialize()`, `process_user_input()`, `handle_function_result()`, `get_available_functions()`, `get_system_instruction()`

#### 2. Agent Registry System (`opusagent/agents/agent_registry.py`)
- `AgentRegistration` dataclass with agent class, ID, name, description, keywords, priority
- `AgentRegistry` class for managing available agents
- Intent matching based on keywords with scoring system
- Methods for registration, discovery, enabling/disabling agents
- Global `agent_registry` instance

#### 3. Agent Factory (`opusagent/agents/agent_factory.py`)
- `AgentFactory` class for creating and managing agent instances
- Agent creation by ID or intent keywords
- Agent lifecycle management and cleanup
- Agent switching during conversations
- Health validation and statistics
- Global `default_factory` instance

#### 4. Concrete Agent Implementation (`opusagent/agents/card_replacement_agent.py`)
- `CardReplacementAgent` extending `BaseAgent`
- Integration with existing `CardReplacementFlow`
- Stage-based conversation management with `CardReplacementStage` enum
- Function result handlers for each card replacement function
- State tracking (customer_verified, replacement_reason, address_confirmed, card_ordered)

#### 5. Agent Bridge Interface (`opusagent/agents/agent_bridge_interface.py`)
- `AgentBridgeInterface` class connecting agents to existing bridge infrastructure
- Agent lifecycle management within bridge connections
- Translation between bridge events and agent method calls
- Conversation context management
- Function call coordination

#### 6. Bootstrap System (`opusagent/agents/bootstrap.py`)
- Agent registration and initialization system
- System validation functionality
- Auto-bootstrap on module import (can be disabled)
- Comprehensive system information and statistics

#### 7. Module Organization (`opusagent/agents/__init__.py`)
- Clean exports of all agent system components
- Integration of bootstrap system

#### 8. Test Suite (`test_agent_system.py`)
- Comprehensive test suite demonstrating all functionality
- Agent registration testing
- Factory functionality testing
- Bridge interface testing
- Complete card replacement flow simulation
- System validation testing

## Architecture Benefits Achieved

### Separation of Concerns
- Clear boundary between communication (bridges) and business logic (agents)
- Infrastructure classes focus on their core responsibilities
- Business logic consolidated in agent classes

### Extensibility
- Easy to add new agents without touching infrastructure
- Agent-specific customizations without affecting others
- Clean testing and development workflow

### Maintainability
- Business logic centralized and well-organized
- Easier to understand conversation flows
- Better error handling and state management

### Reusability
- Agents can work with different bridge types
- Flow system remains reusable across agents
- Function definitions can be shared between agents

## Integration with Existing Infrastructure

### Bridge Integration Pattern
```python
# Instead of hardcoded logic in bridge:
async def handle_user_input(self, user_input: str):
    # Old way: hardcoded business logic here
    
    # New way: delegate to agent
    response = await self.agent_interface.process_user_input(user_input)
    return response
```

### Flow System Integration
- Agents use existing `Flow` classes for tools and system instructions
- Flow system provides the "knowledge" while agents provide the "intelligence"
- No changes needed to existing flow definitions

### Function Handler Coordination
- Function calls still go through existing `FunctionHandler`
- Agent processes function results and determines next steps
- Clean separation between OpenAI integration and business logic

## Usage Examples

### Creating an Agent
```python
from opusagent.agents import AgentBridgeInterface

# In your bridge class
agent_interface = AgentBridgeInterface(
    conversation_id="conv-123",
    session_id="session-456"
)

# Initialize with specific agent
await agent_interface.initialize_agent(agent_id="card_replacement")

# Or initialize by intent
await agent_interface.initialize_agent(
    intent_keywords=["card", "replacement", "lost"]
)
```

### Processing Conversations
```python
# Process user input
response = await agent_interface.process_user_input("I lost my card")

# Handle function results
function_result = {"verified": True, "account_details": {...}}
response = await agent_interface.handle_function_result(
    "member_account_confirmation", 
    function_result
)
```

### Agent Switching
```python
# Switch to different agent during conversation
success = await agent_interface.switch_agent(
    "loan_application", 
    transfer_data={"customer_id": "123"}
)
```

## Future Enhancements

### Additional Agents
- Account Inquiry Agent
- Loan Application Agent
- General Banking Agent
- Transfer/Escalation Agent

### Advanced Features
- Multi-agent workflows
- Agent persistence across sessions
- Advanced intent detection
- Conversation analytics and optimization

### Integration Improvements
- Update existing bridges to use agent interfaces
- Refactor function handler to work through agents
- Enhanced error handling and recovery

## Testing and Validation

The implementation includes comprehensive testing:
- ✅ Agent registration and discovery
- ✅ Factory functionality and lifecycle management
- ✅ Bridge interface integration
- ✅ Complete conversation flow simulation
- ✅ System validation and health checks

All tests pass successfully, demonstrating that the agent abstraction layer is working correctly and ready for integration with the existing infrastructure.

## Conclusion

This agent abstraction layer provides a clean, extensible, and maintainable architecture for conversation management while preserving the excellent flow system and infrastructure already in place. The implementation separates concerns appropriately, making it easy to add new agents and modify existing behavior without touching core infrastructure code. 