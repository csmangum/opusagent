#!/usr/bin/env python3
"""
Example demonstrating the new agent encapsulation framework.

This example shows how to:
1. Create agents using factories
2. Use configuration-driven agent creation
3. Inject agents into bridges
4. Swap agents dynamically
"""

import asyncio
import logging
from typing import Optional

# Import the new agent framework
from opusagent.agents import (
    AgentRegistry,
    AgentFactory,
    CustomerServiceAgentFactory,
    CallerAgentFactory,
    create_agent_from_config_file,
    BaseAgent,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def example_agent_creation():
    """Demonstrate different ways to create agents."""
    print("=== Agent Creation Examples ===\n")
    
    # 1. Using the registry directly
    print("1. Creating agents using registry:")
    cs_agent = AgentRegistry.create_agent(
        "customer_service",
        name="Bank CS Agent",
        role="Banking Representative",
        specialization="banking"
    )
    print(f"   Created: {cs_agent}")
    print(f"   Agent info: {cs_agent.get_agent_info()}")
    print()
    
    # 2. Using factories
    print("2. Creating agents using factories:")
    typical_caller = CallerAgentFactory.create_typical_caller(
        scenario="card_replacement",
        name="John Doe"
    )
    print(f"   Created: {typical_caller}")
    print()
    
    banking_agent = CustomerServiceAgentFactory.create_banking_agent(
        name="Banking Specialist",
        voice="verse"
    )
    print(f"   Created: {banking_agent}")
    print()
    
    # 3. Using configuration dictionaries
    print("3. Creating agents from configuration:")
    config = {
        "type": "caller",
        "name": "Frustrated Customer",
        "role": "Angry Caller",
        "personality_type": "frustrated",
        "scenario_type": "complaint",
        "temperature": 0.9
    }
    frustrated_caller = AgentFactory.create_from_config(config)
    print(f"   Created: {frustrated_caller}")
    print(f"   Agent info: {frustrated_caller.get_agent_info()}")
    print()


def example_configuration_file():
    """Demonstrate loading agents from configuration files."""
    print("=== Configuration File Example ===\n")
    
    try:
        # Try to load agent from config file
        agent = create_agent_from_config_file("config/agents.yaml", "banking")
        print(f"Loaded banking agent from config: {agent}")
        print(f"Agent info: {agent.get_agent_info()}")
    except FileNotFoundError:
        print("Config file not found - this is expected in demo")
    except Exception as e:
        print(f"Error loading from config: {e}")
    print()


def example_agent_registry():
    """Demonstrate agent registry functionality."""
    print("=== Agent Registry Examples ===\n")
    
    # List available agent types
    available_types = AgentRegistry.get_available_types()
    print(f"Available agent types: {available_types}")
    print()
    
    # Check if agent types are registered
    print("Checking agent registration:")
    print(f"   customer_service registered: {AgentRegistry.is_registered('customer_service')}")
    print(f"   caller registered: {AgentRegistry.is_registered('caller')}")
    print(f"   unknown_type registered: {AgentRegistry.is_registered('unknown_type')}")
    print()


class MockBridge:
    """Mock bridge for demonstration purposes."""
    
    def __init__(self, agent: BaseAgent):
        self.agent = agent
        print(f"Bridge initialized with agent: {agent.get_agent_info()['name']}")
        
    def get_current_agent_info(self):
        """Get information about the current agent."""
        return self.agent.get_agent_info()
        
    def swap_agent(self, new_agent: BaseAgent):
        """Swap the current agent."""
        old_name = self.agent.get_agent_info()['name']
        self.agent = new_agent
        new_name = new_agent.get_agent_info()['name']
        print(f"Agent swapped from '{old_name}' to '{new_name}'")


def example_dependency_injection():
    """Demonstrate dependency injection with bridges."""
    print("=== Dependency Injection Example ===\n")
    
    # Create different agents
    cs_agent = CustomerServiceAgentFactory.create_standard_agent(
        name="Standard CS Agent"
    )
    banking_agent = CustomerServiceAgentFactory.create_banking_agent(
        name="Banking Specialist"
    )
    
    # Inject agent into bridge
    print("Creating bridge with standard CS agent:")
    bridge = MockBridge(cs_agent)
    print(f"Current agent: {bridge.get_current_agent_info()['name']}")
    print()
    
    # Swap to a different agent
    print("Swapping to banking specialist:")
    bridge.swap_agent(banking_agent)
    print(f"Current agent: {bridge.get_current_agent_info()['name']}")
    print()


def example_specialized_agents():
    """Demonstrate creating specialized agents."""
    print("=== Specialized Agents Example ===\n")
    
    # Create specialized customer service agents
    agents = [
        CustomerServiceAgentFactory.create_banking_agent(name="Banking CS"),
        CustomerServiceAgentFactory.create_healthcare_agent(name="Healthcare CS"),
        CustomerServiceAgentFactory.create_retail_agent(name="Retail CS"),
    ]
    
    for agent in agents:
        info = agent.get_agent_info()
        print(f"Agent: {info['name']}")
        print(f"   Type: {info['agent_type']}")
        print(f"   Specialization: {info.get('specialization', 'N/A')}")
        print(f"   Capabilities: {info['capabilities']}")
        print()


def example_caller_personalities():
    """Demonstrate different caller personalities."""
    print("=== Caller Personalities Example ===\n")
    
    # Create callers with different personalities
    callers = [
        CallerAgentFactory.create_typical_caller(name="Typical Customer"),
        CallerAgentFactory.create_frustrated_caller(name="Frustrated Customer"),
        CallerAgentFactory.create_elderly_caller(name="Elderly Customer"),
        CallerAgentFactory.create_hurried_caller(name="Hurried Customer"),
    ]
    
    for caller in callers:
        info = caller.get_agent_info()
        print(f"Caller: {info['name']}")
        print(f"   Personality: {info['personality_type']}")
        print(f"   Scenario: {info['scenario_type']}")
        print(f"   Voice: {info['voice']}")
        print()


def example_agent_session_configs():
    """Demonstrate how agents provide session configurations."""
    print("=== Agent Session Configurations ===\n")
    
    # Create agents and show their session configs
    agents = [
        CustomerServiceAgentFactory.create_standard_agent(),
        CallerAgentFactory.create_typical_caller(),
    ]
    
    for agent in agents:
        info = agent.get_agent_info()
        config = agent.get_session_config()
        
        print(f"Agent: {info['name']} ({info['agent_type']})")
        print(f"   Voice: {config.voice}")
        print(f"   Temperature: {config.temperature}")
        print(f"   Model: {config.model}")
        print(f"   Max tokens: {config.max_response_output_tokens}")
        print(f"   Tools: {len(config.tools or [])}")
        print()


def main():
    """Run all examples."""
    print("OpusAgent - Agent Encapsulation Framework Examples")
    print("=" * 60)
    print()
    
    try:
        example_agent_creation()
        example_agent_registry()
        example_dependency_injection()
        example_specialized_agents()
        example_caller_personalities()
        example_agent_session_configs()
        example_configuration_file()
        
        print("=== Summary ===")
        print("✅ All examples completed successfully!")
        print("\nKey benefits demonstrated:")
        print("  • Dependency injection enables flexible agent selection")
        print("  • Factory patterns simplify agent creation")
        print("  • Configuration-driven agent instantiation")
        print("  • Dynamic agent swapping capabilities")
        print("  • Better separation of concerns")
        print("  • Improved testability with mock agents")
        
    except Exception as e:
        logger.error(f"Error running examples: {e}")
        raise


if __name__ == "__main__":
    main()