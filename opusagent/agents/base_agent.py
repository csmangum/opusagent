"""
Base Agent class for handling conversation logic and business flows.

This module provides the abstract base class that all conversation agents
must implement, along with supporting data structures for agent communication.
"""

import asyncio
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Union

from opusagent.call_recorder import CallRecorder
from opusagent.config.logging_config import configure_logging

logger = configure_logging("base_agent")


class AgentStatus(str, Enum):
    """Status of an agent during conversation."""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    WAITING_FOR_INPUT = "waiting_for_input"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"
    TRANSFERRING = "transferring"


class ResponseType(str, Enum):
    """Type of response from an agent."""
    CONTINUE = "continue"  # Continue conversation
    COMPLETE = "complete"  # End conversation successfully
    TRANSFER = "transfer"  # Transfer to human
    ERROR = "error"  # Error occurred
    SWITCH_AGENT = "switch_agent"  # Switch to different agent


@dataclass
class AgentContext:
    """Context information passed to agents during conversation."""
    conversation_id: str
    session_id: str
    customer_data: Dict[str, Any] = field(default_factory=dict)
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    platform_metadata: Dict[str, Any] = field(default_factory=dict)
    call_recorder: Optional[CallRecorder] = None
    
    def add_conversation_entry(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add an entry to the conversation history."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "role": role,
            "content": content,
            "metadata": metadata or {}
        }
        self.conversation_history.append(entry)
    
    def get_customer_data(self, key: str, default=None):
        """Get customer data with fallback."""
        return self.customer_data.get(key, default)
    
    def set_customer_data(self, key: str, value: Any):
        """Set customer data."""
        self.customer_data[key] = value


@dataclass 
class AgentResponse:
    """Response from an agent after processing input."""
    response_type: ResponseType
    message: Optional[str] = None
    function_calls: List[Dict[str, Any]] = field(default_factory=list)
    next_stage: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    transfer_reason: Optional[str] = None
    error_details: Optional[str] = None
    
    def is_terminal(self) -> bool:
        """Check if this response ends the conversation."""
        return self.response_type in [ResponseType.COMPLETE, ResponseType.TRANSFER, ResponseType.ERROR]


class BaseAgent(ABC):
    """
    Abstract base class for all conversation agents.
    
    Agents are responsible for:
    - Managing conversation state and flow progression
    - Executing business logic specific to their domain
    - Coordinating with the flow system for tools and functions
    - Providing responses and determining next steps
    """
    
    def __init__(self, agent_id: str, name: str):
        """
        Initialize the base agent.
        
        Args:
            agent_id: Unique identifier for this agent type
            name: Human-readable name for the agent
        """
        self.agent_id = agent_id
        self.name = name
        self.status = AgentStatus.INITIALIZING
        self.current_stage: Optional[str] = None
        self.session_data: Dict[str, Any] = {}
        self.conversation_context: Optional[AgentContext] = None
        self.created_at = datetime.utcnow()
        
    # Core Agent Interface
    
    @abstractmethod
    async def initialize(self, context: AgentContext) -> AgentResponse:
        """
        Initialize the agent with conversation context.
        
        Args:
            context: The conversation context
            
        Returns:
            Initial agent response
        """
        pass
    
    @abstractmethod
    async def process_user_input(self, user_input: str, context: AgentContext) -> AgentResponse:
        """
        Process user input and return appropriate response.
        
        Args:
            user_input: The user's spoken or text input
            context: Current conversation context
            
        Returns:
            Agent response with next steps
        """
        pass
    
    @abstractmethod
    async def handle_function_result(self, function_name: str, result: Dict[str, Any], context: AgentContext) -> AgentResponse:
        """
        Handle the result of a function call.
        
        Args:
            function_name: Name of the function that was executed
            result: Result returned by the function
            context: Current conversation context
            
        Returns:
            Agent response based on function result
        """
        pass
    
    @abstractmethod
    def get_available_functions(self) -> List[Dict[str, Any]]:
        """
        Get the list of functions this agent can use.
        
        Returns:
            List of OpenAI function tool definitions
        """
        pass
    
    @abstractmethod
    def get_system_instruction(self) -> str:
        """
        Get the system instruction for this agent.
        
        Returns:
            System instruction text for OpenAI
        """
        pass
    
    # State Management
    
    def get_current_stage(self) -> Optional[str]:
        """Get the current conversation stage."""
        return self.current_stage
    
    def set_current_stage(self, stage: str):
        """Set the current conversation stage."""
        logger.info(f"Agent {self.agent_id} transitioning to stage: {stage}")
        self.current_stage = stage
        
    def get_session_data(self, key: str, default=None):
        """Get session-specific data."""
        return self.session_data.get(key, default)
    
    def set_session_data(self, key: str, value: Any):
        """Set session-specific data."""
        self.session_data[key] = value
        
    def update_status(self, status: AgentStatus):
        """Update agent status."""
        logger.info(f"Agent {self.agent_id} status: {self.status} -> {status}")
        self.status = status
    
    # Helper Methods
    
    def create_response(
        self,
        response_type: ResponseType,
        message: Optional[str] = None,
        function_calls: Optional[List[Dict[str, Any]]] = None,
        next_stage: Optional[str] = None,
        **kwargs
    ) -> AgentResponse:
        """Create a standardized agent response."""
        return AgentResponse(
            response_type=response_type,
            message=message,
            function_calls=function_calls or [],
            next_stage=next_stage,
            metadata=kwargs
        )
    
    def create_error_response(self, error_message: str, details: Optional[str] = None) -> AgentResponse:
        """Create an error response."""
        return AgentResponse(
            response_type=ResponseType.ERROR,
            message=error_message,
            error_details=details
        )
    
    def create_transfer_response(self, reason: str, message: Optional[str] = None) -> AgentResponse:
        """Create a transfer response."""
        return AgentResponse(
            response_type=ResponseType.TRANSFER,
            message=message or f"Transferring you to a human agent: {reason}",
            transfer_reason=reason
        )
    
    def create_complete_response(self, message: Optional[str] = None) -> AgentResponse:
        """Create a completion response."""
        return AgentResponse(
            response_type=ResponseType.COMPLETE,
            message=message or "Thank you for calling. Have a great day!"
        )
    
    # Lifecycle Management
    
    async def cleanup(self):
        """Clean up agent resources."""
        logger.info(f"Cleaning up agent {self.agent_id}")
        self.status = AgentStatus.COMPLETED
    
    # Validation and Diagnostics
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate agent configuration."""
        functions = self.get_available_functions()
        system_instruction = self.get_system_instruction()
        
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "functions_count": len(functions),
            "has_system_instruction": bool(system_instruction),
            "status": self.status.value,
            "current_stage": self.current_stage,
            "session_data_keys": list(self.session_data.keys())
        }
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get comprehensive agent information."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "status": self.status.value,
            "current_stage": self.current_stage,
            "created_at": self.created_at.isoformat(),
            "session_data": self.session_data,
            "conversation_id": self.conversation_context.conversation_id if self.conversation_context else None
        } 