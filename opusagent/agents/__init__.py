"""
Agent system for managing conversation logic and business flows.

This module provides the core agent abstraction layer that separates
conversation logic from communication infrastructure.
"""

from .base_agent import BaseAgent, AgentContext, AgentResponse
from .agent_registry import AgentRegistry, agent_registry
from .agent_factory import AgentFactory, default_factory
from .agent_bridge_interface import AgentBridgeInterface
from .card_replacement_agent import CardReplacementAgent
from .bootstrap import (
    bootstrap_agent_system,
    validate_agent_system,
    get_agent_system_info
)

__all__ = [
    "BaseAgent",
    "AgentContext", 
    "AgentResponse",
    "AgentRegistry",
    "agent_registry",
    "AgentFactory",
    "default_factory",
    "AgentBridgeInterface",
    "CardReplacementAgent",
    "bootstrap_agent_system",
    "validate_agent_system", 
    "get_agent_system_info",
] 