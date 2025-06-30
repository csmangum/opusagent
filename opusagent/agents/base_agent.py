"""
Base agent interface for OpusAgent.

This module defines the abstract base class that all agents must implement
to ensure consistent interfaces and enable dependency injection.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from opusagent.models.openai_api import SessionConfig


class BaseAgent(ABC):
    """Abstract base class for all agents in the OpusAgent system.
    
    This class defines the interface that all agents must implement to ensure
    consistent behavior and enable dependency injection patterns. Agents are
    responsible for their own configuration, function registration, and metadata.
    """

    def __init__(self, name: str, role: str, **kwargs):
        """Initialize the base agent.
        
        Args:
            name: Human-readable name for the agent
            role: The role or purpose of the agent
            **kwargs: Additional agent-specific configuration
        """
        self.name = name
        self.role = role
        self._config = kwargs

    @abstractmethod
    def get_session_config(self) -> SessionConfig:
        """Return the OpenAI session configuration for this agent.
        
        This method must return a properly configured SessionConfig object
        that defines how the agent will interact with the OpenAI API.
        
        Returns:
            SessionConfig: Configuration for OpenAI realtime API session
        """
        pass

    @abstractmethod
    def register_functions(self, function_handler) -> None:
        """Register agent-specific functions with the function handler.
        
        This method is called during agent initialization to register
        all functions that this agent can call during conversation.
        
        Args:
            function_handler: The FunctionHandler instance to register functions with
        """
        pass

    @abstractmethod
    def get_agent_info(self) -> Dict[str, Any]:
        """Return metadata about the agent.
        
        This method should return a dictionary containing information about
        the agent's capabilities, configuration, and other metadata.
        
        Returns:
            Dict containing agent metadata
        """
        pass

    @property
    @abstractmethod
    def agent_type(self) -> str:
        """Return the agent type identifier.
        
        This should return a unique string identifier for the agent type,
        used for registration and factory creation.
        
        Returns:
            String identifier for the agent type
        """
        pass

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value for this agent.
        
        Args:
            key: Configuration key to retrieve
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        return self._config.get(key, default)

    def update_config(self, **kwargs) -> None:
        """Update agent configuration.
        
        Args:
            **kwargs: Configuration updates to apply
        """
        self._config.update(kwargs)

    def __str__(self) -> str:
        """String representation of the agent."""
        return f"{self.__class__.__name__}(name='{self.name}', role='{self.role}', type='{self.agent_type}')"

    def __repr__(self) -> str:
        """Developer representation of the agent."""
        return f"{self.__class__.__name__}(name='{self.name}', role='{self.role}', type='{self.agent_type}', config={self._config})"