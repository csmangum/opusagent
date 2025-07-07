"""
Agent framework for OpusAgent.

This module provides the core infrastructure for agent encapsulation,
including base classes, registries, and factories for creating and managing agents.
"""

# Import core infrastructure first
from .base_agent import BaseAgent
from .agent_registry import AgentRegistry, register_agent
from .agent_factory import (
    AgentFactory,
    CustomerServiceAgentFactory,
    CallerAgentFactory,
    create_agent_from_config_file,
)

# Import concrete agent implementations
from .customer_service_agent import CustomerServiceAgent
from .caller_agent import CallerAgent

__all__ = [
    # Core infrastructure
    "BaseAgent",
    "AgentRegistry", 
    "register_agent",
    
    # Factories
    "AgentFactory",
    "CustomerServiceAgentFactory",
    "CallerAgentFactory",
    "create_agent_from_config_file",
    
    # Agent implementations
    "CustomerServiceAgent",
    "CallerAgent",
]

# Ensure agents are registered when module is imported
# This happens automatically due to the @register_agent decorators
# on the agent classes, but we can verify registration here if needed

def get_available_agent_types():
    """Get list of available agent types."""
    return AgentRegistry.get_available_types()

def create_agent(agent_type: str, **kwargs):
    """Create an agent by type. Convenience function."""
    return AgentRegistry.create_agent(agent_type, **kwargs)