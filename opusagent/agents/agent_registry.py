"""
Agent Registry for managing available conversation agents.

This module provides centralized registration and discovery of conversation agents,
enabling dynamic agent selection and management.
"""

from typing import Dict, List, Optional, Type, Callable
from dataclasses import dataclass

from opusagent.config.logging_config import configure_logging
from .base_agent import BaseAgent

logger = configure_logging("agent_registry")


@dataclass
class AgentRegistration:
    """Registration information for an agent."""
    agent_class: Type[BaseAgent]
    agent_id: str
    name: str
    description: str
    keywords: List[str]
    priority: int = 0  # Higher numbers = higher priority
    enabled: bool = True
    
    def matches_intent(self, intent_keywords: List[str]) -> bool:
        """Check if this agent matches the given intent keywords."""
        if not intent_keywords:
            return False
            
        # Convert to lowercase for case-insensitive matching
        agent_keywords = [kw.lower() for kw in self.keywords]
        intent_keywords_lower = [kw.lower() for kw in intent_keywords]
        
        # Check for any keyword matches
        return any(kw in agent_keywords for kw in intent_keywords_lower)
    
    def get_match_score(self, intent_keywords: List[str]) -> int:
        """Get a score for how well this agent matches the intent."""
        if not self.enabled or not intent_keywords:
            return 0
            
        agent_keywords = [kw.lower() for kw in self.keywords]
        intent_keywords_lower = [kw.lower() for kw in intent_keywords]
        
        # Count exact matches
        matches = sum(1 for kw in intent_keywords_lower if kw in agent_keywords)
        
        # Factor in priority
        return matches * 10 + self.priority


class AgentRegistry:
    """
    Registry for managing conversation agents.
    
    Provides functionality for:
    - Registering new agents
    - Discovering agents by intent or keywords
    - Managing agent lifecycle and availability
    """
    
    def __init__(self):
        """Initialize the agent registry."""
        self._agents: Dict[str, AgentRegistration] = {}
        self._intent_handlers: Dict[str, str] = {}  # intent -> agent_id mapping
        
    def register_agent(
        self,
        agent_class: Type[BaseAgent],
        agent_id: str,
        name: str,
        description: str,
        keywords: List[str],
        priority: int = 0,
        enabled: bool = True
    ) -> None:
        """
        Register a new agent.
        
        Args:
            agent_class: The agent class to register
            agent_id: Unique identifier for the agent
            name: Human-readable name
            description: Description of what the agent does
            keywords: Keywords that identify when to use this agent
            priority: Priority level (higher = more preferred)
            enabled: Whether the agent is currently enabled
        """
        if agent_id in self._agents:
            logger.warning(f"Agent {agent_id} is already registered, overwriting")
        
        registration = AgentRegistration(
            agent_class=agent_class,
            agent_id=agent_id,
            name=name,
            description=description,
            keywords=keywords,
            priority=priority,
            enabled=enabled
        )
        
        self._agents[agent_id] = registration
        logger.info(f"Registered agent: {agent_id} ({name})")
    
    def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent.
        
        Args:
            agent_id: ID of the agent to unregister
            
        Returns:
            True if agent was found and removed, False otherwise
        """
        if agent_id in self._agents:
            del self._agents[agent_id]
            logger.info(f"Unregistered agent: {agent_id}")
            return True
        return False
    
    def get_agent_class(self, agent_id: str) -> Optional[Type[BaseAgent]]:
        """
        Get the agent class for a given agent ID.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Agent class if found, None otherwise
        """
        registration = self._agents.get(agent_id)
        return registration.agent_class if registration and registration.enabled else None
    
    def get_agent_info(self, agent_id: str) -> Optional[AgentRegistration]:
        """
        Get registration info for an agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Agent registration info if found, None otherwise
        """
        return self._agents.get(agent_id)
    
    def find_agents_by_intent(self, intent_keywords: List[str]) -> List[str]:
        """
        Find agents that match the given intent keywords.
        
        Args:
            intent_keywords: Keywords describing the user's intent
            
        Returns:
            List of agent IDs, sorted by match quality (best first)
        """
        if not intent_keywords:
            return []
        
        # Score all agents
        scored_agents = []
        for agent_id, registration in self._agents.items():
            score = registration.get_match_score(intent_keywords)
            if score > 0:
                scored_agents.append((agent_id, score))
        
        # Sort by score (descending) and return agent IDs
        scored_agents.sort(key=lambda x: x[1], reverse=True)
        return [agent_id for agent_id, _ in scored_agents]
    
    def get_best_agent(self, intent_keywords: List[str]) -> Optional[str]:
        """
        Get the best agent for the given intent.
        
        Args:
            intent_keywords: Keywords describing the user's intent
            
        Returns:
            Agent ID of the best match, or None if no match found
        """
        matching_agents = self.find_agents_by_intent(intent_keywords)
        return matching_agents[0] if matching_agents else None
    
    def get_default_agent(self) -> Optional[str]:
        """
        Get the default agent (highest priority enabled agent).
        
        Returns:
            Agent ID of the default agent, or None if no agents registered
        """
        enabled_agents = [
            (agent_id, reg) for agent_id, reg in self._agents.items() 
            if reg.enabled
        ]
        
        if not enabled_agents:
            return None
        
        # Sort by priority (descending)
        enabled_agents.sort(key=lambda x: x[1].priority, reverse=True)
        return enabled_agents[0][0]
    
    def list_agents(self, enabled_only: bool = True) -> List[Dict[str, str]]:
        """
        List all registered agents.
        
        Args:
            enabled_only: If True, only return enabled agents
            
        Returns:
            List of agent information dictionaries
        """
        agents = []
        for agent_id, registration in self._agents.items():
            if enabled_only and not registration.enabled:
                continue
                
            agents.append({
                "agent_id": agent_id,
                "name": registration.name,
                "description": registration.description,
                "keywords": registration.keywords,
                "priority": registration.priority,
                "enabled": registration.enabled
            })
        
        # Sort by priority (descending)
        agents.sort(key=lambda x: x["priority"], reverse=True)
        return agents
    
    def enable_agent(self, agent_id: str) -> bool:
        """Enable an agent."""
        if agent_id in self._agents:
            self._agents[agent_id].enabled = True
            logger.info(f"Enabled agent: {agent_id}")
            return True
        return False
    
    def disable_agent(self, agent_id: str) -> bool:
        """Disable an agent."""
        if agent_id in self._agents:
            self._agents[agent_id].enabled = False
            logger.info(f"Disabled agent: {agent_id}")
            return True
        return False
    
    def clear_registry(self):
        """Clear all registered agents."""
        self._agents.clear()
        self._intent_handlers.clear()
        logger.info("Cleared agent registry")
    
    def get_registry_stats(self) -> Dict[str, int]:
        """Get statistics about the registry."""
        enabled_count = sum(1 for reg in self._agents.values() if reg.enabled)
        return {
            "total_agents": len(self._agents),
            "enabled_agents": enabled_count,
            "disabled_agents": len(self._agents) - enabled_count
        }


# Global registry instance
agent_registry = AgentRegistry() 