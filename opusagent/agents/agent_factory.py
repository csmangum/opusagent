"""
Agent factory for OpusAgent.

This module provides factory classes for creating agents from configuration
and managing different agent creation patterns.
"""

import logging
from typing import Dict, Any, Optional, Union
from .base_agent import BaseAgent
from .agent_registry import AgentRegistry

logger = logging.getLogger(__name__)


class AgentFactory:
    """Factory for creating agents from configuration.
    
    This factory provides a high-level interface for creating agents
    using configuration dictionaries, allowing for flexible agent
    instantiation based on runtime parameters.
    """

    @staticmethod
    def create_from_config(config: Dict[str, Any]) -> BaseAgent:
        """Create an agent from a configuration dictionary.
        
        Args:
            config: Configuration dictionary with required keys:
                - type: Agent type identifier
                - name: Agent name (optional)
                - role: Agent role (optional)
                - Additional keys are passed as kwargs to the agent
                
        Returns:
            BaseAgent: Configured agent instance
            
        Raises:
            ValueError: If required configuration is missing or invalid
            
        Example:
            config = {
                "type": "customer_service",
                "name": "CS Agent",
                "role": "Customer Support Representative",
                "voice": "verse",
                "temperature": 0.8
            }
            agent = AgentFactory.create_from_config(config)
        """
        if not isinstance(config, dict):
            raise ValueError("Configuration must be a dictionary")
            
        agent_type = config.get("type")
        if not agent_type:
            raise ValueError("Agent configuration must include 'type' field")
            
        # Extract standard fields
        name = config.get("name", f"{agent_type}_agent")
        role = config.get("role", "AI Assistant")
        
        # Extract additional configuration
        agent_kwargs = {k: v for k, v in config.items() if k not in ["type", "name", "role"]}
        
        try:
            agent = AgentRegistry.create_agent(
                agent_type,
                name=name,
                role=role,
                **agent_kwargs
            )
            logger.info(f"Created agent '{name}' of type '{agent_type}'")
            return agent
        except Exception as e:
            logger.error(f"Failed to create agent of type '{agent_type}': {e}")
            raise

    @staticmethod
    def create_customer_service_agent(
        name: str = "Customer Service Agent",
        role: str = "Customer Support Representative",
        **kwargs
    ) -> BaseAgent:
        """Create a customer service agent with default configuration.
        
        Args:
            name: Agent name
            role: Agent role
            **kwargs: Additional configuration
            
        Returns:
            BaseAgent: Customer service agent instance
        """
        config = {
            "type": "customer_service",
            "name": name,
            "role": role,
            **kwargs
        }
        return AgentFactory.create_from_config(config)

    @staticmethod
    def create_caller_agent(
        personality_type: str = "typical",
        scenario_type: str = "general_inquiry",
        name: str = "Caller Agent",
        role: str = "Customer Caller",
        **kwargs
    ) -> BaseAgent:
        """Create a caller agent with specified personality and scenario.
        
        Args:
            personality_type: Type of caller personality
            scenario_type: Type of call scenario
            name: Agent name
            role: Agent role
            **kwargs: Additional configuration
            
        Returns:
            BaseAgent: Caller agent instance
        """
        config = {
            "type": "caller",
            "name": name,
            "role": role,
            "personality_type": personality_type,
            "scenario_type": scenario_type,
            **kwargs
        }
        return AgentFactory.create_from_config(config)

    @staticmethod
    def create_specialized_agent(
        agent_type: str,
        specialization: str,
        name: Optional[str] = None,
        role: Optional[str] = None,
        **kwargs
    ) -> BaseAgent:
        """Create a specialized agent with domain-specific configuration.
        
        Args:
            agent_type: Base agent type
            specialization: Specialization domain (e.g., "banking", "healthcare")
            name: Agent name (defaults to "{specialization} {agent_type} Agent")
            role: Agent role (defaults based on specialization)
            **kwargs: Additional configuration
            
        Returns:
            BaseAgent: Specialized agent instance
        """
        if name is None:
            name = f"{specialization.title()} {agent_type.title()} Agent"
            
        if role is None:
            role = f"{specialization.title()} Specialist"
            
        config = {
            "type": agent_type,
            "name": name,
            "role": role,
            "specialization": specialization,
            **kwargs
        }
        return AgentFactory.create_from_config(config)


class CustomerServiceAgentFactory:
    """Specialized factory for customer service agents."""

    @staticmethod
    def create_standard_agent(**kwargs) -> BaseAgent:
        """Create a standard customer service agent."""
        return AgentFactory.create_customer_service_agent(**kwargs)

    @staticmethod
    def create_banking_agent(**kwargs) -> BaseAgent:
        """Create a banking-specialized customer service agent."""
        return AgentFactory.create_specialized_agent(
            agent_type="customer_service",
            specialization="banking",
            **kwargs
        )

    @staticmethod
    def create_healthcare_agent(**kwargs) -> BaseAgent:
        """Create a healthcare-specialized customer service agent."""
        return AgentFactory.create_specialized_agent(
            agent_type="customer_service",
            specialization="healthcare",
            **kwargs
        )

    @staticmethod
    def create_retail_agent(**kwargs) -> BaseAgent:
        """Create a retail-specialized customer service agent."""
        return AgentFactory.create_specialized_agent(
            agent_type="customer_service",
            specialization="retail",
            **kwargs
        )


class CallerAgentFactory:
    """Specialized factory for caller agents with different personalities."""

    @staticmethod
    def create_typical_caller(scenario: str = "general_inquiry", **kwargs) -> BaseAgent:
        """Create a typical, cooperative caller."""
        return AgentFactory.create_caller_agent(
            personality_type="typical",
            scenario_type=scenario,
            **kwargs
        )

    @staticmethod
    def create_frustrated_caller(scenario: str = "complaint", **kwargs) -> BaseAgent:
        """Create a frustrated, impatient caller."""
        return AgentFactory.create_caller_agent(
            personality_type="frustrated",
            scenario_type=scenario,
            **kwargs
        )

    @staticmethod
    def create_elderly_caller(scenario: str = "account_inquiry", **kwargs) -> BaseAgent:
        """Create an elderly caller who needs more guidance."""
        return AgentFactory.create_caller_agent(
            personality_type="elderly",
            scenario_type=scenario,
            **kwargs
        )

    @staticmethod
    def create_hurried_caller(scenario: str = "card_replacement", **kwargs) -> BaseAgent:
        """Create a hurried caller who wants quick service."""
        return AgentFactory.create_caller_agent(
            personality_type="hurried",
            scenario_type=scenario,
            **kwargs
        )


def create_agent_from_config_file(config_path: str, agent_id: str) -> BaseAgent:
    """Create an agent from a configuration file.
    
    Args:
        config_path: Path to YAML or JSON configuration file
        agent_id: Identifier for the specific agent configuration
        
    Returns:
        BaseAgent: Configured agent instance
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If agent_id not found in config
    """
    import os
    import yaml
    import json

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    # Load configuration based on file extension
    with open(config_path, 'r') as f:
        if config_path.endswith('.yaml') or config_path.endswith('.yml'):
            config_data = yaml.safe_load(f)
        elif config_path.endswith('.json'):
            config_data = json.load(f)
        else:
            raise ValueError("Configuration file must be YAML or JSON")

    # Navigate to agent configuration
    if "agents" not in config_data:
        raise ValueError("Configuration file must contain 'agents' section")

    agents_config = config_data["agents"]
    
    # Find the specific agent configuration
    agent_config = None
    for category, agents in agents_config.items():
        if agent_id in agents:
            agent_config = agents[agent_id]
            break

    if agent_config is None:
        available_agents = []
        for category, agents in agents_config.items():
            available_agents.extend(agents.keys())
        raise ValueError(f"Agent '{agent_id}' not found. Available agents: {available_agents}")

    return AgentFactory.create_from_config(agent_config)