"""
Agent Factory for creating and managing agent instances.

This module provides functionality for creating agents based on intent detection,
managing agent lifecycle, and handling agent switching during conversations.
"""

from typing import Optional, List, Dict, Any
import asyncio

from opusagent.config.logging_config import configure_logging
from .base_agent import BaseAgent, AgentContext, AgentStatus
from .agent_registry import agent_registry, AgentRegistry

logger = configure_logging("agent_factory")


class AgentFactory:
    """
    Factory for creating and managing conversation agents.
    
    Handles:
    - Agent creation based on intent detection
    - Agent lifecycle management
    - Agent switching during conversations
    - Default agent fallback logic
    """
    
    def __init__(self, registry: Optional[AgentRegistry] = None):
        """
        Initialize the agent factory.
        
        Args:
            registry: Agent registry to use (defaults to global registry)
        """
        self.registry = registry or agent_registry
        self._active_agents: Dict[str, BaseAgent] = {}  # conversation_id -> agent
        
    async def create_agent(
        self, 
        agent_id: str,
        context: AgentContext
    ) -> Optional[BaseAgent]:
        """
        Create a new agent instance.
        
        Args:
            agent_id: ID of the agent to create
            context: Conversation context
            
        Returns:
            Agent instance if successful, None otherwise
        """
        agent_class = self.registry.get_agent_class(agent_id)
        if not agent_class:
            logger.error(f"Agent class not found for ID: {agent_id}")
            return None
        
        try:
            # Get agent info for initialization
            agent_info = self.registry.get_agent_info(agent_id)
            if not agent_info:
                logger.error(f"Agent info not found for ID: {agent_id}")
                return None
            
            # Create agent instance
            agent = agent_class(agent_id, agent_info.name)
            
            # Initialize agent with context
            response = await agent.initialize(context)
            if response.response_type.value == "error":
                logger.error(f"Failed to initialize agent {agent_id}: {response.error_details}")
                return None
            
            # Store agent as active
            self._active_agents[context.conversation_id] = agent
            
            logger.info(f"Created and initialized agent: {agent_id} for conversation: {context.conversation_id}")
            return agent
            
        except Exception as e:
            logger.error(f"Error creating agent {agent_id}: {e}")
            return None
    
    async def create_agent_by_intent(
        self,
        intent_keywords: List[str],
        context: AgentContext,
        fallback_to_default: bool = True
    ) -> Optional[BaseAgent]:
        """
        Create an agent based on intent keywords.
        
        Args:
            intent_keywords: Keywords describing the user's intent
            context: Conversation context
            fallback_to_default: Whether to fall back to default agent if no match
            
        Returns:
            Agent instance if successful, None otherwise
        """
        # Find best matching agent
        agent_id = self.registry.get_best_agent(intent_keywords)
        
        if not agent_id and fallback_to_default:
            agent_id = self.registry.get_default_agent()
            logger.info(f"No specific agent found for intent {intent_keywords}, using default: {agent_id}")
        
        if not agent_id:
            logger.warning(f"No agent found for intent: {intent_keywords}")
            return None
        
        logger.info(f"Selected agent {agent_id} for intent: {intent_keywords}")
        return await self.create_agent(agent_id, context)
    
    async def get_or_create_agent(
        self,
        conversation_id: str,
        agent_id: Optional[str] = None,
        intent_keywords: Optional[List[str]] = None,
        context: Optional[AgentContext] = None
    ) -> Optional[BaseAgent]:
        """
        Get existing agent or create a new one.
        
        Args:
            conversation_id: Conversation identifier
            agent_id: Specific agent ID to create (optional)
            intent_keywords: Intent keywords for agent selection (optional)
            context: Conversation context (required for new agents)
            
        Returns:
            Agent instance if successful, None otherwise
        """
        # Check if agent already exists for this conversation
        existing_agent = self._active_agents.get(conversation_id)
        if existing_agent and existing_agent.status != AgentStatus.ERROR:
            logger.debug(f"Using existing agent for conversation: {conversation_id}")
            return existing_agent
        
        # Need to create new agent
        if not context:
            logger.error("Context required to create new agent")
            return None
        
        if agent_id:
            return await self.create_agent(agent_id, context)
        elif intent_keywords:
            return await self.create_agent_by_intent(intent_keywords, context)
        else:
            # Use default agent
            default_agent_id = self.registry.get_default_agent()
            if default_agent_id:
                logger.info(f"Creating default agent: {default_agent_id}")
                return await self.create_agent(default_agent_id, context)
            else:
                logger.error("No default agent available")
                return None
    
    async def switch_agent(
        self,
        conversation_id: str,
        new_agent_id: str,
        context: AgentContext,
        transfer_data: Optional[Dict[str, Any]] = None
    ) -> Optional[BaseAgent]:
        """
        Switch to a different agent during a conversation.
        
        Args:
            conversation_id: Conversation identifier
            new_agent_id: ID of the new agent
            context: Current conversation context
            transfer_data: Data to transfer to the new agent
            
        Returns:
            New agent instance if successful, None otherwise
        """
        # Clean up existing agent
        await self.cleanup_agent(conversation_id)
        
        # Transfer data to context if provided
        if transfer_data:
            context.customer_data.update(transfer_data)
            context.add_conversation_entry(
                "system", 
                f"Transferred to agent: {new_agent_id}",
                {"transfer_data": transfer_data}
            )
        
        # Create new agent
        new_agent = await self.create_agent(new_agent_id, context)
        if new_agent:
            logger.info(f"Successfully switched to agent {new_agent_id} for conversation {conversation_id}")
        else:
            logger.error(f"Failed to switch to agent {new_agent_id} for conversation {conversation_id}")
        
        return new_agent
    
    def get_active_agent(self, conversation_id: str) -> Optional[BaseAgent]:
        """Get the active agent for a conversation."""
        return self._active_agents.get(conversation_id)
    
    async def cleanup_agent(self, conversation_id: str) -> bool:
        """
        Clean up an agent for a conversation.
        
        Args:
            conversation_id: Conversation identifier
            
        Returns:
            True if cleanup was successful, False otherwise
        """
        agent = self._active_agents.get(conversation_id)
        if not agent:
            return False
        
        try:
            await agent.cleanup()
            del self._active_agents[conversation_id]
            logger.info(f"Cleaned up agent for conversation: {conversation_id}")
            return True
        except Exception as e:
            logger.error(f"Error cleaning up agent for conversation {conversation_id}: {e}")
            return False
    
    async def cleanup_all_agents(self):
        """Clean up all active agents."""
        conversation_ids = list(self._active_agents.keys())
        for conversation_id in conversation_ids:
            await self.cleanup_agent(conversation_id)
        
        logger.info("Cleaned up all active agents")
    
    def get_factory_stats(self) -> Dict[str, Any]:
        """Get factory statistics."""
        active_agents = {}
        for conv_id, agent in self._active_agents.items():
            active_agents[conv_id] = {
                "agent_id": agent.agent_id,
                "name": agent.name,
                "status": agent.status.value,
                "current_stage": agent.current_stage
            }
        
        return {
            "active_agents_count": len(self._active_agents),
            "active_agents": active_agents,
            "registry_stats": self.registry.get_registry_stats()
        }
    
    def list_available_agents(self) -> List[Dict[str, Any]]:
        """List all available agents from the registry."""
        return self.registry.list_agents()
    
    async def validate_agent_health(self, conversation_id: str) -> bool:
        """
        Validate that an agent is healthy and functioning.
        
        Args:
            conversation_id: Conversation identifier
            
        Returns:
            True if agent is healthy, False otherwise
        """
        agent = self._active_agents.get(conversation_id)
        if not agent:
            return False
        
        # Check agent status
        if agent.status in [AgentStatus.ERROR, AgentStatus.COMPLETED]:
            return False
        
        # Validate agent configuration
        try:
            config = agent.validate_configuration()
            return config.get("has_system_instruction", False) and config.get("functions_count", 0) > 0
        except Exception as e:
            logger.error(f"Error validating agent health: {e}")
            return False


# Create default factory instance
default_factory = AgentFactory() 