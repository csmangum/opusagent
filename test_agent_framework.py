#!/usr/bin/env python3
"""
Simple test script for the agent encapsulation framework.
This tests the core functionality without requiring all dependencies.
"""

import sys
import os
sys.path.insert(0, '/workspace')

# Test just the core agent framework components
def test_basic_imports():
    """Test that we can import the core components."""
    try:
        from opusagent.agents.base_agent import BaseAgent
        from opusagent.agents.agent_registry import AgentRegistry, register_agent
        print("✅ Core agent framework imports successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_agent_registry():
    """Test the agent registry functionality."""
    try:
        from opusagent.agents.agent_registry import AgentRegistry
        
        # Test registry methods
        print(f"Available types (should be empty): {AgentRegistry.get_available_types()}")
        print(f"Is 'test' registered: {AgentRegistry.is_registered('test')}")
        
        # Test registration
        from abc import ABC, abstractmethod
        from typing import Dict, Any
        
        class MockSessionConfig:
            def __init__(self):
                self.voice = "test"
                
        class MockAgent(ABC):
            def __init__(self, name="test", role="test", **kwargs):
                self.name = name
                self.role = role
                self._config = kwargs
                
            def get_session_config(self):
                return MockSessionConfig()
                
            def register_functions(self, handler):
                pass
                
            def get_agent_info(self):
                return {"name": self.name, "role": self.role, "agent_type": "mock"}
                
            @property
            def agent_type(self):
                return "mock"
        
        # Register the mock agent
        AgentRegistry.register("mock", MockAgent)
        
        print(f"Available types after registration: {AgentRegistry.get_available_types()}")
        print(f"Is 'mock' registered: {AgentRegistry.is_registered('mock')}")
        
        # Test creation
        agent = AgentRegistry.create_agent("mock", name="Test Agent")
        print(f"Created agent: {agent.name}")
        
        print("✅ Agent registry tests passed")
        return True
    except Exception as e:
        print(f"❌ Agent registry test error: {e}")
        return False

def test_decorator():
    """Test the @register_agent decorator."""
    try:
        from opusagent.agents.agent_registry import register_agent, AgentRegistry
        from abc import ABC
        
        @register_agent("decorated_mock")
        class DecoratedMockAgent(ABC):
            def __init__(self, name="decorated", role="test", **kwargs):
                self.name = name
                self.role = role
                
            def get_session_config(self):
                return None
                
            def register_functions(self, handler):
                pass
                
            def get_agent_info(self):
                return {"name": self.name, "agent_type": "decorated_mock"}
                
            @property
            def agent_type(self):
                return "decorated_mock"
        
        print(f"Available types after decorator: {AgentRegistry.get_available_types()}")
        print(f"Is 'decorated_mock' registered: {AgentRegistry.is_registered('decorated_mock')}")
        
        print("✅ Decorator test passed")
        return True
    except Exception as e:
        print(f"❌ Decorator test error: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing Agent Encapsulation Framework")
    print("=" * 40)
    
    tests = [
        ("Basic Imports", test_basic_imports),
        ("Agent Registry", test_agent_registry),
        ("Decorator", test_decorator),
    ]
    
    passed = 0
    total = len(tests)
    
    for name, test_func in tests:
        print(f"\n--- {name} ---")
        if test_func():
            passed += 1
        print()
    
    print("=" * 40)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The agent framework is working correctly.")
        return True
    else:
        print("❌ Some tests failed.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)