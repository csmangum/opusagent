"""
Agent registry for OpusAgent.

This module provides a centralized registry for agent types and factories,
enabling dynamic agent creation and discovery.
"""

import logging
from typing import Dict, List, Type, Any, Callable, Optional
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Central registry for agent types and factories.
    
    This class maintains a registry of available agent types and provides
    methods for registering new agents, creating agent instances, and
    discovering available agent types.
    """

    _agents: Dict[str, Type[BaseAgent]] = {}
    _agent_factories: Dict[str, Callable[..., BaseAgent]] = {}

    @classmethod
    def register(cls, agent_type: str, agent_class: Type[BaseAgent]) -> None:
        """Register an agent class with a type identifier.
        
        Args:
            agent_type: Unique identifier for the agent type
            agent_class: Agent class that implements BaseAgent
            
        Raises:
            ValueError: If agent_type is already registered or agent_class doesn't implement BaseAgent
        """
        if not issubclass(agent_class, BaseAgent):
            raise ValueError(f"Agent class {agent_class.__name__} must implement BaseAgent")
            
        if agent_type in cls._agents:
            logger.warning(f"Agent type '{agent_type}' is already registered. Overwriting.")
            
        cls._agents[agent_type] = agent_class
        logger.info(f"Registered agent type '{agent_type}' with class {agent_class.__name__}")

    @classmethod
    def register_factory(cls, agent_type: str, factory_func: Callable[..., BaseAgent]) -> None:
        """Register a factory function for creating agents.
        
        Args:
            agent_type: Unique identifier for the agent type
            factory_func: Function that creates and returns a BaseAgent instance
        """
        if agent_type in cls._agent_factories:
            logger.warning(f"Agent factory for type '{agent_type}' is already registered. Overwriting.")
            
        cls._agent_factories[agent_type] = factory_func
        logger.info(f"Registered agent factory for type '{agent_type}'")

    @classmethod
    def create_agent(cls, agent_type: str, **kwargs) -> BaseAgent:
        """Create an agent instance by type.
        
        Args:
            agent_type: Type identifier for the agent to create
            **kwargs: Arguments to pass to the agent constructor or factory
            
        Returns:
            BaseAgent: Configured agent instance
            
        Raises:
            ValueError: If agent_type is not registered
        """
        # Try factory first, then class constructor
        if agent_type in cls._agent_factories:
            logger.debug(f"Creating agent '{agent_type}' using factory")
            return cls._agent_factories[agent_type](**kwargs)
        elif agent_type in cls._agents:
            logger.debug(f"Creating agent '{agent_type}' using class constructor")
            return cls._agents[agent_type](**kwargs)
        else:
            available_types = cls.get_available_types()
            raise ValueError(
                f"Unknown agent type: '{agent_type}'. Available types: {available_types}"
            )

    @classmethod
    def get_available_types(cls) -> List[str]:
        """Get list of registered agent types.
        
        Returns:
            List of registered agent type identifiers
        """
        agent_types = set(cls._agents.keys())
        factory_types = set(cls._agent_factories.keys())
        return sorted(list(agent_types.union(factory_types)))

    @classmethod
    def get_agent_class(cls, agent_type: str) -> Optional[Type[BaseAgent]]:
        """Get the agent class for a given type.
        
        Args:
            agent_type: Type identifier for the agent
            
        Returns:
            Agent class if registered via register(), None otherwise
        """
        return cls._agents.get(agent_type)

    @classmethod
    def is_registered(cls, agent_type: str) -> bool:
        """Check if an agent type is registered.
        
        Args:
            agent_type: Type identifier to check
            
        Returns:
            True if the agent type is registered
        """
        return agent_type in cls._agents or agent_type in cls._agent_factories

    @classmethod
    def unregister(cls, agent_type: str) -> bool:
        """Unregister an agent type.
        
        Args:
            agent_type: Type identifier to unregister
            
        Returns:
            True if the agent was unregistered, False if it wasn't registered
        """
        removed = False
        if agent_type in cls._agents:
            del cls._agents[agent_type]
            removed = True
            
        if agent_type in cls._agent_factories:
            del cls._agent_factories[agent_type]
            removed = True
            
        if removed:
            logger.info(f"Unregistered agent type '{agent_type}'")
        else:
            logger.warning(f"Attempted to unregister unknown agent type '{agent_type}'")
            
        return removed

    @classmethod
    def clear(cls) -> None:
        """Clear all registered agents and factories.
        
        This is primarily useful for testing.
        """
        cls._agents.clear()
        cls._agent_factories.clear()
        logger.info("Cleared all registered agents and factories")


def register_agent(agent_type: str):
    """Decorator for registering agent classes.
    
    Args:
        agent_type: Unique identifier for the agent type
        
    Returns:
        Decorator function
        
    Example:
        @register_agent("customer_service")
        class CustomerServiceAgent(BaseAgent):
            pass
    """
    def decorator(agent_class: Type[BaseAgent]) -> Type[BaseAgent]:
        AgentRegistry.register(agent_type, agent_class)
        return agent_class
    return decorator