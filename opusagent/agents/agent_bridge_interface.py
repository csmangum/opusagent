"""
Agent Bridge Interface

This module provides the interface between the agent system and the existing
bridge infrastructure, allowing agents to work seamlessly with any platform bridge.
"""

import asyncio
from typing import Dict, Any, Optional, List

from opusagent.config.logging_config import configure_logging
from opusagent.call_recorder import CallRecorder
from .base_agent import BaseAgent, AgentContext, AgentResponse, AgentStatus, ResponseType
from .agent_factory import AgentFactory, default_factory

logger = configure_logging("agent_bridge_interface")


class AgentBridgeInterface:
    """
    Interface between agents and platform bridges.
    
    This class:
    - Manages agent lifecycle within bridge connections
    - Translates between bridge events and agent method calls
    - Handles agent responses and converts them to bridge actions
    - Manages conversation context and state
    """
    
    def __init__(
        self,
        conversation_id: str,
        session_id: Optional[str] = None,
        agent_factory: Optional[AgentFactory] = None,
        call_recorder: Optional[CallRecorder] = None
    ):
        """
        Initialize the agent bridge interface.
        
        Args:
            conversation_id: Unique conversation identifier
            session_id: Session identifier (defaults to conversation_id)
            agent_factory: Agent factory instance (defaults to global factory)
            call_recorder: Call recorder for logging
        """
        self.conversation_id = conversation_id
        self.session_id = session_id or conversation_id
        self.agent_factory = agent_factory or default_factory
        self.call_recorder = call_recorder
        
        # Agent state
        self.current_agent: Optional[BaseAgent] = None
        self.agent_context: Optional[AgentContext] = None
        
        # Bridge interaction tracking
        self.pending_function_calls: Dict[str, Dict[str, Any]] = {}
        self.session_initialized = False
        
        # Initialize context
        self._initialize_context()
        
    def _initialize_context(self):
        """Initialize the agent context."""
        self.agent_context = AgentContext(
            conversation_id=self.conversation_id,
            session_id=self.session_id,
            call_recorder=self.call_recorder
        )
        
    async def initialize_agent(
        self,
        agent_id: Optional[str] = None,
        intent_keywords: Optional[List[str]] = None
    ) -> bool:
        """
        Initialize an agent for the conversation.
        
        Args:
            agent_id: Specific agent ID to use
            intent_keywords: Keywords for agent selection
            
        Returns:
            True if agent was successfully initialized, False otherwise
        """
        try:
            if not self.agent_context:
                logger.error("Agent context not initialized")
                return False
                
            if agent_id:
                self.current_agent = await self.agent_factory.create_agent(agent_id, self.agent_context)
            elif intent_keywords:
                self.current_agent = await self.agent_factory.create_agent_by_intent(
                    intent_keywords, self.agent_context
                )
            else:
                # Use default agent
                self.current_agent = await self.agent_factory.get_or_create_agent(
                    self.conversation_id, context=self.agent_context
                )
            
            if self.current_agent:
                logger.info(f"Initialized agent {self.current_agent.agent_id} for conversation {self.conversation_id}")
                self.session_initialized = True
                return True
            else:
                logger.error(f"Failed to initialize agent for conversation {self.conversation_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error initializing agent: {e}")
            return False
    
    async def process_user_input(self, user_input: str) -> AgentResponse:
        """
        Process user input through the agent.
        
        Args:
            user_input: The user's input (speech or text)
            
        Returns:
            Agent response
        """
        if not self.current_agent or not self.agent_context:
            logger.error("Agent not initialized")
            return AgentResponse(
                response_type=ResponseType.ERROR,
                message="Agent not initialized",
                error_details="No agent available to process input"
            )
        
        try:
            response = await self.current_agent.process_user_input(user_input, self.agent_context)
            logger.info(f"Agent {self.current_agent.agent_id} processed input, response type: {response.response_type}")
            return response
            
        except Exception as e:
            logger.error(f"Error processing user input: {e}")
            return AgentResponse(
                response_type=ResponseType.ERROR,
                message="Error processing your request",
                error_details=str(e)
            )
    
    async def handle_function_result(self, function_name: str, result: Dict[str, Any]) -> AgentResponse:
        """
        Handle function call result and pass to agent.
        
        Args:
            function_name: Name of the function that was called
            result: Result from the function
            
        Returns:
            Agent response
        """
        if not self.current_agent or not self.agent_context:
            logger.error("Agent not initialized for function result handling")
            return AgentResponse(
                response_type=ResponseType.ERROR,
                message="Agent not available",
                error_details="No agent to handle function result"
            )
        
        try:
            response = await self.current_agent.handle_function_result(
                function_name, result, self.agent_context
            )
            logger.info(f"Agent handled function {function_name} result, response type: {response.response_type}")
            
            # Handle agent switching if requested
            if response.response_type == ResponseType.SWITCH_AGENT:
                new_agent_id = response.metadata.get("new_agent_id")
                if new_agent_id:
                    await self.switch_agent(new_agent_id, response.metadata.get("transfer_data", {}))
            
            return response
            
        except Exception as e:
            logger.error(f"Error handling function result for {function_name}: {e}")
            return AgentResponse(
                response_type=ResponseType.ERROR,
                message="Error processing function result",
                error_details=str(e)
            )
    
    async def switch_agent(self, new_agent_id: str, transfer_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Switch to a different agent.
        
        Args:
            new_agent_id: ID of the new agent
            transfer_data: Data to transfer to the new agent
            
        Returns:
            True if switch was successful, False otherwise
        """
        if not self.agent_context:
            logger.error("No agent context for switch")
            return False
        
        try:
            new_agent = await self.agent_factory.switch_agent(
                self.conversation_id,
                new_agent_id,
                self.agent_context,
                transfer_data
            )
            
            if new_agent:
                self.current_agent = new_agent
                logger.info(f"Switched to agent {new_agent_id} for conversation {self.conversation_id}")
                return True
            else:
                logger.error(f"Failed to switch to agent {new_agent_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error switching to agent {new_agent_id}: {e}")
            return False
    
    def get_available_functions(self) -> List[Dict[str, Any]]:
        """Get functions available to the current agent."""
        if self.current_agent:
            return self.current_agent.get_available_functions()
        return []
    
    def get_system_instruction(self) -> str:
        """Get system instruction from the current agent."""
        if self.current_agent:
            return self.current_agent.get_system_instruction()
        return "You are a helpful AI assistant."
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get information about the current agent."""
        if self.current_agent:
            return self.current_agent.get_agent_info()
        return {"status": "no_agent"}
    
    def update_context_metadata(self, metadata: Dict[str, Any]):
        """Update platform metadata in the agent context."""
        if self.agent_context:
            self.agent_context.platform_metadata.update(metadata)
    
    def set_customer_data(self, key: str, value: Any):
        """Set customer data in the agent context."""
        if self.agent_context:
            self.agent_context.set_customer_data(key, value)
    
    def get_customer_data(self, key: str, default=None):
        """Get customer data from the agent context."""
        if self.agent_context:
            return self.agent_context.get_customer_data(key, default)
        return default
    
    async def cleanup(self):
        """Clean up the agent bridge interface."""
        try:
            if self.current_agent:
                await self.current_agent.cleanup()
            
            await self.agent_factory.cleanup_agent(self.conversation_id)
            
            logger.info(f"Cleaned up agent bridge interface for conversation {self.conversation_id}")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def is_agent_ready(self) -> bool:
        """Check if agent is ready to handle requests."""
        return (
            self.current_agent is not None and 
            self.agent_context is not None and
            self.current_agent.status in [AgentStatus.ACTIVE, AgentStatus.WAITING_FOR_INPUT]
        )
    
    def should_hang_up(self) -> bool:
        """Check if the conversation should be ended."""
        if not self.current_agent:
            return False
            
        return self.current_agent.status in [
            AgentStatus.COMPLETED, 
            AgentStatus.TRANSFERRING
        ]
    
    def get_interface_stats(self) -> Dict[str, Any]:
        """Get statistics about the interface."""
        agent_info = self.get_agent_info() if self.current_agent else {}
        
        return {
            "conversation_id": self.conversation_id,
            "session_id": self.session_id,
            "session_initialized": self.session_initialized,
            "agent_ready": self.is_agent_ready(),
            "should_hang_up": self.should_hang_up(),
            "current_agent": agent_info,
            "pending_function_calls": len(self.pending_function_calls),
            "context_entries": len(self.agent_context.conversation_history) if self.agent_context else 0
        } 