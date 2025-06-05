"""
Tests for the FlowManager class.
"""

import pytest
from typing import Any, Dict, List

from opusagent.flows.flow_manager import FlowManager, create_default_flow_manager
from opusagent.flows.base_flow import BaseFlow
from opusagent.flows.card_replacement import CardReplacementFlow
from opusagent.flows.loan_application import LoanApplicationFlow


class TestFlow(BaseFlow):
    """Mock flow for testing."""
    def __init__(self, name: str):
        super().__init__(name)
    
    def get_tools(self) -> List[Dict[str, Any]]:
        return [{"name": f"{self.name}_tool"}]
    
    def get_functions(self) -> Dict[str, Any]:
        return {f"{self.name}_function": lambda x: x}
    
    def get_prompts(self) -> Dict[str, str]:
        return {f"{self.name}_prompt": "test"}
    
    def get_system_instruction(self) -> str:
        return f"{self.name} instruction"
    
    def get_flow_info(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "tools": self.get_tools(),
            "functions": list(self.get_functions().keys()),
            "prompts": list(self.get_prompts().keys()),
            "system_instruction": self.get_system_instruction()
        }


def test_flow_manager_initialization():
    """Test that FlowManager initializes correctly."""
    manager = FlowManager()
    assert manager.flows == {}
    assert manager.active_flows == []


def test_flow_registration():
    """Test flow registration functionality."""
    manager = FlowManager()
    flow = TestFlow("test")
    
    manager.register_flow(flow)
    assert "test" in manager.flows
    assert manager.flows["test"] == flow


def test_flow_unregistration():
    """Test flow unregistration functionality."""
    manager = FlowManager()
    flow = TestFlow("test")
    
    manager.register_flow(flow)
    assert manager.unregister_flow("test") is True
    assert "test" not in manager.flows
    assert manager.unregister_flow("nonexistent") is False


def test_flow_activation():
    """Test flow activation functionality."""
    manager = FlowManager()
    flow = TestFlow("test")
    
    manager.register_flow(flow)
    manager.activate_flow("test")
    assert "test" in manager.active_flows


def test_flow_activation_nonexistent():
    """Test that activating a nonexistent flow raises an error."""
    manager = FlowManager()
    with pytest.raises(ValueError):
        manager.activate_flow("nonexistent")


def test_flow_deactivation():
    """Test flow deactivation functionality."""
    manager = FlowManager()
    flow = TestFlow("test")
    
    manager.register_flow(flow)
    manager.activate_flow("test")
    manager.deactivate_flow("test")
    assert "test" not in manager.active_flows


def test_get_all_tools():
    """Test that get_all_tools returns tools from all active flows."""
    manager = FlowManager()
    flow1 = TestFlow("test1")
    flow2 = TestFlow("test2")
    
    manager.register_flow(flow1)
    manager.register_flow(flow2)
    manager.activate_flow("test1")
    manager.activate_flow("test2")
    
    tools = manager.get_all_tools()
    assert len(tools) == 2
    assert any(t["name"] == "test1_tool" for t in tools)
    assert any(t["name"] == "test2_tool" for t in tools)


def test_get_all_functions():
    """Test that get_all_functions returns functions from all active flows."""
    manager = FlowManager()
    flow1 = TestFlow("test1")
    flow2 = TestFlow("test2")
    
    manager.register_flow(flow1)
    manager.register_flow(flow2)
    manager.activate_flow("test1")
    manager.activate_flow("test2")
    
    functions = manager.get_all_functions()
    assert len(functions) == 2
    assert "test1_function" in functions
    assert "test2_function" in functions


def test_get_combined_system_instruction():
    """Test that get_combined_system_instruction combines instructions from all active flows."""
    manager = FlowManager()
    flow1 = TestFlow("test1")
    flow2 = TestFlow("test2")
    
    manager.register_flow(flow1)
    manager.register_flow(flow2)
    manager.activate_flow("test1")
    manager.activate_flow("test2")
    
    instruction = manager.get_combined_system_instruction()
    assert "test1 instruction" in instruction
    assert "test2 instruction" in instruction


def test_register_with_function_handler():
    """Test that register_with_function_handler registers functions from all active flows."""
    class MockHandler:
        def __init__(self):
            self.registered_functions = {}
        
        def register_function(self, name, func):
            self.registered_functions[name] = func
    
    manager = FlowManager()
    flow1 = TestFlow("test1")
    flow2 = TestFlow("test2")
    
    manager.register_flow(flow1)
    manager.register_flow(flow2)
    manager.activate_flow("test1")
    manager.activate_flow("test2")
    
    handler = MockHandler()
    manager.register_with_function_handler(handler)
    
    assert "test1_function" in handler.registered_functions
    assert "test2_function" in handler.registered_functions


def test_get_flow_info():
    """Test that get_flow_info returns correct information about flows."""
    manager = FlowManager()
    flow = TestFlow("test")
    
    manager.register_flow(flow)
    manager.activate_flow("test")
    
    info = manager.get_flow_info()
    assert "registered_flows" in info
    assert "active_flows" in info
    assert "total_tools" in info
    assert "total_functions" in info
    assert "flows" in info
    
    specific_info = manager.get_flow_info("test")
    assert specific_info["name"] == "test"
    assert len(specific_info["tools"]) == 1
    assert len(specific_info["functions"]) == 1


def test_create_default_flow_manager():
    """Test that create_default_flow_manager creates a manager with default flows."""
    manager = create_default_flow_manager()
    
    assert isinstance(manager, FlowManager)
    assert "card_replacement" in manager.flows
    assert "loan_application" in manager.flows
    assert "card_replacement" in manager.active_flows


def test_flow_manager_reset():
    """Test that reset clears all flows and active flows."""
    manager = FlowManager()
    flow = TestFlow("test")
    
    manager.register_flow(flow)
    manager.activate_flow("test")
    manager.reset()
    
    assert manager.flows == {}
    assert manager.active_flows == [] 