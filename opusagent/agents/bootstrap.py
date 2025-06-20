"""
Agent Bootstrap System

This module handles the registration and initialization of all available agents
in the system. It provides a centralized way to configure and bootstrap the
agent ecosystem.
"""

from typing import List, Dict, Any

from opusagent.config.logging_config import configure_logging
from .agent_registry import agent_registry
from .card_replacement_agent import CardReplacementAgent

logger = configure_logging("agent_bootstrap")


def register_core_agents():
    """Register all core agents with the agent registry."""
    
    # Register Card Replacement Agent
    agent_registry.register_agent(
        agent_class=CardReplacementAgent,
        agent_id="card_replacement",
        name="Card Replacement Agent",
        description="Handles card replacement requests including verification, reason collection, and processing",
        keywords=[
            "card", "replacement", "replace", "lost", "stolen", "damaged", 
            "broken", "new card", "reissue", "debit", "credit"
        ],
        priority=10,  # High priority for card replacement
        enabled=True
    )
    
    logger.info("Registered core agents with the registry")


def register_additional_agents():
    """Register additional/optional agents."""
    # Future agents can be registered here
    # - Account Inquiry Agent
    # - Loan Application Agent
    # - General Banking Agent
    # - Transfer Agent
    pass


def bootstrap_agent_system() -> Dict[str, Any]:
    """
    Bootstrap the complete agent system.
    
    Returns:
        Dictionary with bootstrap results and statistics
    """
    logger.info("Bootstrapping agent system...")
    
    try:
        # Clear any existing registrations
        agent_registry.clear_registry()
        
        # Register all agents
        register_core_agents()
        register_additional_agents()
        
        # Get system statistics
        stats = agent_registry.get_registry_stats()
        agents = agent_registry.list_agents()
        
        logger.info(f"Agent system bootstrapped successfully: {stats}")
        
        return {
            "success": True,
            "message": "Agent system bootstrapped successfully",
            "stats": stats,
            "agents": agents
        }
        
    except Exception as e:
        logger.error(f"Failed to bootstrap agent system: {e}")
        return {
            "success": False,
            "message": f"Failed to bootstrap agent system: {e}",
            "error": str(e)
        }


def validate_agent_system() -> Dict[str, Any]:
    """
    Validate the agent system configuration.
    
    Returns:
        Dictionary with validation results
    """
    logger.info("Validating agent system...")
    
    validation_results = {
        "valid": True,
        "issues": [],
        "warnings": [],
        "agents": {}
    }
    
    try:
        # Get all registered agents
        agents = agent_registry.list_agents(enabled_only=False)
        
        if not agents:
            validation_results["valid"] = False
            validation_results["issues"].append("No agents registered")
            return validation_results
        
        # Check if we have a default agent
        default_agent = agent_registry.get_default_agent()
        if not default_agent:
            validation_results["warnings"].append("No default agent configured")
        
        # Validate each agent
        for agent_info in agents:
            agent_id = agent_info["agent_id"]
            agent_class = agent_registry.get_agent_class(agent_id)
            
            if not agent_class:
                validation_results["issues"].append(f"Agent class not found for {agent_id}")
                validation_results["valid"] = False
                continue
            
            # Try to create a test instance
            try:
                test_agent = agent_class(agent_id, agent_info["name"])
                config_validation = test_agent.validate_configuration()
                validation_results["agents"][agent_id] = config_validation
                
                # Check for critical issues
                if not config_validation.get("has_system_instruction"):
                    validation_results["issues"].append(f"Agent {agent_id} missing system instruction")
                    validation_results["valid"] = False
                
                if config_validation.get("functions_count", 0) == 0:
                    validation_results["warnings"].append(f"Agent {agent_id} has no functions")
                
            except Exception as e:
                validation_results["issues"].append(f"Failed to instantiate agent {agent_id}: {e}")
                validation_results["valid"] = False
        
        # Summary
        total_agents = len(agents)
        enabled_agents = len([a for a in agents if a["enabled"]])
        
        validation_results["summary"] = {
            "total_agents": total_agents,
            "enabled_agents": enabled_agents,
            "disabled_agents": total_agents - enabled_agents,
            "has_default": default_agent is not None,
            "default_agent": default_agent
        }
        
        if validation_results["valid"]:
            logger.info("Agent system validation passed")
        else:
            logger.error(f"Agent system validation failed: {validation_results['issues']}")
        
        if validation_results["warnings"]:
            logger.warning(f"Agent system validation warnings: {validation_results['warnings']}")
        
        return validation_results
        
    except Exception as e:
        logger.error(f"Error during agent system validation: {e}")
        return {
            "valid": False,
            "issues": [f"Validation error: {e}"],
            "error": str(e)
        }


def get_agent_system_info() -> Dict[str, Any]:
    """
    Get comprehensive information about the agent system.
    
    Returns:
        Dictionary with system information
    """
    return {
        "registry_stats": agent_registry.get_registry_stats(),
        "available_agents": agent_registry.list_agents(),
        "default_agent": agent_registry.get_default_agent(),
        "validation": validate_agent_system()
    }


# Auto-bootstrap when module is imported (can be disabled by setting environment variable)
import os
if not os.getenv("DISABLE_AGENT_BOOTSTRAP", "").lower() in ["true", "1", "yes"]:
    try:
        bootstrap_result = bootstrap_agent_system()
        if not bootstrap_result["success"]:
            logger.error(f"Auto-bootstrap failed: {bootstrap_result.get('message')}")
    except Exception as e:
        logger.error(f"Auto-bootstrap error: {e}") 