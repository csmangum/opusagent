"""
Base Flow Class

Provides the interface and common functionality that all conversation flows must implement.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List


class BaseFlow(ABC):
    """
    Abstract base class for conversation flows.
    
    Each flow should implement:
    - Tool definitions (OpenAI function schemas)
    - Function implementations
    - Prompts
    - Flow registration logic
    """

    def __init__(self, name: str):
        """
        Initialize the flow.
        
        Args:
            name: Unique name for this flow
        """
        self.name = name
        self._tools = {}
        self._functions = {}
        self._prompts = {}

    @abstractmethod
    def get_tools(self) -> List[Dict[str, Any]]:
        """
        Get the OpenAI tool definitions for this flow.
        
        Returns:
            List of OpenAI function tool schemas
        """
        pass

    @abstractmethod
    def get_functions(self) -> Dict[str, Callable]:
        """
        Get the function implementations for this flow.
        
        Returns:
            Dictionary mapping function names to callable implementations
        """
        pass

    @abstractmethod
    def get_prompts(self) -> Dict[str, str]:
        """
        Get the prompts used in this flow.
        
        Returns:
            Dictionary mapping prompt names to prompt templates
        """
        pass

    @abstractmethod
    def get_system_instruction(self) -> str:
        """
        Get the system instruction that should be added for this flow.
        
        Returns:
            System instruction text
        """
        pass

    def register_with_handler(self, function_handler):
        """
        Register this flow's functions with a function handler.
        
        Args:
            function_handler: FunctionHandler instance to register functions with
        """
        functions = self.get_functions()
        for name, func in functions.items():
            function_handler.register_function(name, func)

    def get_flow_info(self) -> Dict[str, Any]:
        """
        Get comprehensive information about this flow.
        
        Returns:
            Dictionary containing tools, functions, prompts, and metadata
        """
        return {
            "name": self.name,
            "tools": self.get_tools(),
            "functions": list(self.get_functions().keys()),
            "prompts": list(self.get_prompts().keys()),
            "system_instruction": self.get_system_instruction()
        } 