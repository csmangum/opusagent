# Agent Encapsulation Improvement Plan

## Executive Summary

Based on analysis of the current OpusAgent codebase, this plan proposes a comprehensive restructuring to improve agent encapsulation, making it easier to define, use, and pass different agents to bridges. The current architecture has several coupling issues and lacks a unified agent interface that would enable better modularity and testability.

## Current State Analysis

### Problems Identified

1. **Tight Coupling**: Bridges are tightly coupled to specific agent implementations through direct imports and function registration
2. **Hardcoded Dependencies**: BaseRealtimeBridge hardcodes customer service agent registration
3. **Inconsistent Interfaces**: Different agent types (customer service, caller) have different APIs and registration patterns
4. **Manual Wiring**: Function registration requires manual calls scattered throughout the codebase
5. **Limited Flexibility**: Difficult to swap agent implementations without code changes
6. **Testing Challenges**: Hard to mock or substitute agents for testing

### Current Architecture Issues

```python
# Current problematic pattern in base_bridge.py
from opusagent.customer_service_agent import register_customer_service_functions
register_customer_service_functions(self.function_handler)  # Hardcoded!
```

## Proposed Solution: Agent Encapsulation Framework

### 1. Core Agent Interface (Abstract Base Class)

Create a unified agent interface that all agents must implement:

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from opusagent.models.openai_api import SessionConfig

class BaseAgent(ABC):
    """Base class for all agents with unified interface"""
    
    @abstractmethod
    def get_session_config(self) -> SessionConfig:
        """Return the OpenAI session configuration for this agent"""
        pass
    
    @abstractmethod
    def register_functions(self, function_handler) -> None:
        """Register agent-specific functions with the function handler"""
        pass
    
    @abstractmethod
    def get_agent_info(self) -> Dict[str, Any]:
        """Return metadata about the agent (name, role, capabilities, etc.)"""
        pass
    
    @property
    @abstractmethod
    def agent_type(self) -> str:
        """Return the agent type identifier"""
        pass
```

### 2. Agent Registry Pattern

Implement a registry for agent discovery and instantiation:

```python
class AgentRegistry:
    """Central registry for agent types and factories"""
    
    _agents: Dict[str, Type[BaseAgent]] = {}
    
    @classmethod
    def register(cls, agent_type: str, agent_class: Type[BaseAgent]):
        """Register an agent class with a type identifier"""
        cls._agents[agent_type] = agent_class
    
    @classmethod
    def create_agent(cls, agent_type: str, **kwargs) -> BaseAgent:
        """Create an agent instance by type"""
        if agent_type not in cls._agents:
            raise ValueError(f"Unknown agent type: {agent_type}")
        return cls._agents[agent_type](**kwargs)
    
    @classmethod
    def get_available_types(cls) -> List[str]:
        """Get list of registered agent types"""
        return list(cls._agents.keys())
```

### 3. Agent Factory Pattern

Implement factories for different agent categories:

```python
class CustomerServiceAgentFactory:
    """Factory for customer service agents"""
    
    @staticmethod
    def create_standard_cs_agent() -> BaseAgent:
        return StandardCustomerServiceAgent()
    
    @staticmethod
    def create_specialized_cs_agent(domain: str) -> BaseAgent:
        return SpecializedCustomerServiceAgent(domain=domain)

class CallerAgentFactory:
    """Factory for caller agents with different personalities"""
    
    @staticmethod
    def create_caller_agent(personality_type: str, scenario_type: str) -> BaseAgent:
        return CallerAgent(personality_type=personality_type, scenario_type=scenario_type)
```

### 4. Dependency Injection for Bridges

Refactor bridges to accept agents as dependencies instead of hardcoding them:

```python
class BaseRealtimeBridge(ABC):
    def __init__(
        self,
        platform_websocket,
        realtime_websocket: ClientConnection,
        agent: BaseAgent,  # Injected dependency
    ):
        self.platform_websocket = platform_websocket
        self.realtime_websocket = realtime_websocket
        self.agent = agent
        
        # Get session config from agent
        self.session_config = agent.get_session_config()
        
        # Initialize components
        self._initialize_components()
        
        # Register agent functions
        agent.register_functions(self.function_handler)
```

### 5. Configuration-Driven Agent Selection

Enable agent selection through configuration:

```yaml
# agents.yaml
agents:
  customer_service:
    default:
      type: "standard_cs"
      config:
        voice: "verse"
        temperature: 0.8
    banking:
      type: "specialized_cs"
      config:
        domain: "banking"
        voice: "verse"
        
  caller:
    typical:
      type: "caller"
      config:
        personality: "typical"
        scenario: "card_replacement"
    frustrated:
      type: "caller"
      config:
        personality: "frustrated"
        scenario: "complaint"
```

## Implementation Plan

### Phase 1: Core Infrastructure

1. **Create BaseAgent Interface**
   - Define abstract base class with unified methods
   - Establish common patterns for session config and function registration

2. **Implement Agent Registry**
   - Create central registry for agent discovery
   - Add registration decorators for easy agent registration

3. **Refactor Existing Agents**
   - Migrate CustomerServiceAgent to implement BaseAgent
   - Migrate CallerAgent to implement BaseAgent
   - Update all caller personality variants

### Phase 2: Bridge Refactoring

1. **Update BaseRealtimeBridge**
   - Remove hardcoded agent imports
   - Accept agent as constructor parameter
   - Use agent interface methods instead of direct imports

2. **Update Specialized Bridges**
   - Modify TwilioBridge, AudioCodesBridge, etc.
   - Ensure they work with new agent injection pattern

3. **Update DualAgentBridge**
   - Accept two agent parameters instead of hardcoding
   - Use agent factories for agent creation

### Phase 3: Configuration and Factories

1. **Create Agent Factories**
   - Implement factories for different agent categories
   - Add configuration-based agent creation

2. **Configuration System**
   - Create YAML/JSON configuration for agent selection
   - Add environment-based agent switching

3. **CLI and API Updates**
   - Update run_opus_server.py to use new agent system
   - Add CLI options for agent selection

### Phase 4: Testing and Documentation

1. **Comprehensive Testing**
   - Unit tests for all agent implementations
   - Integration tests for bridge-agent combinations
   - Mock agent implementations for testing

2. **Documentation Updates**
   - Update README with new agent system
   - Create agent development guide
   - Add configuration examples

## Benefits of New Architecture

### 1. Improved Modularity
- Agents are self-contained with clear interfaces
- Easy to add new agent types without modifying bridges
- Better separation of concerns

### 2. Enhanced Testability
- Mock agents can be easily injected for testing
- Isolated testing of individual components
- Better unit test coverage

### 3. Configuration Flexibility
- Agents can be selected through configuration
- Environment-specific agent deployments
- A/B testing different agent configurations

### 4. Easier Development
- Clear patterns for adding new agents
- Reduced boilerplate code
- Better code organization

### 5. Production Benefits
- Hot-swappable agent configurations
- Better monitoring and observability
- Easier troubleshooting and debugging

## Migration Strategy

### Backward Compatibility
- Maintain existing APIs during transition
- Add deprecation warnings for old patterns
- Provide migration guides for custom implementations

### Gradual Rollout
1. Implement new infrastructure alongside existing code
2. Migrate one agent type at a time
3. Update bridges incrementally
4. Remove deprecated code after migration

### Testing Strategy
- Extensive integration testing during migration
- Parallel testing of old and new implementations
- Performance benchmarking to ensure no regressions

## Success Metrics

1. **Code Quality**
   - Reduced coupling between components
   - Improved test coverage (target: >90%)
   - Decreased cyclomatic complexity

2. **Developer Experience**
   - Time to add new agent type (target: <2 hours)
   - Lines of boilerplate code for new agents (target: <50 lines)
   - Documentation clarity ratings

3. **Operational Benefits**
   - Configuration deployment time
   - System restart requirements for agent changes
   - Error rates during agent swapping

## Conclusion

This agent encapsulation improvement plan addresses the current architectural limitations while providing a clear path forward for better modularity, testability, and maintainability. The proposed dependency injection and factory patterns align with industry best practices and will significantly improve the developer experience when working with different agents and callers.

The phased implementation approach ensures minimal disruption to existing functionality while progressively improving the architecture. The end result will be a more flexible, maintainable, and robust system that can easily adapt to future requirements.