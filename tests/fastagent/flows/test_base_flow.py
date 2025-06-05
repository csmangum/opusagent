"""
Tests for the BaseFlow abstract base class.
"""

import pytest
from typing import Any, Callable, Dict, List

from fastagent.flows.base_flow import BaseFlow


class TestFlow(BaseFlow):
    """Concrete implementation of BaseFlow for testing."""
    
    def get_tools(self) -> List[Dict[str, Any]]:
        return [{"name": "test_tool"}]
    
    def get_functions(self) -> Dict[str, Callable]:
        return {"test_function": lambda x: x}
    
    def get_prompts(self) -> Dict[str, str]:
        return {"test_prompt": "test"}
    
    def get_system_instruction(self) -> str:
        return "test instruction"


def test_base_flow_initialization():
    """Test that BaseFlow initializes correctly."""
    flow = TestFlow("test_flow")
    assert flow.name == "test_flow"
    assert flow._tools == {}
    assert flow._functions == {}
    assert flow._prompts == {}


def test_base_flow_abstract_methods():
    """Test that BaseFlow requires implementation of abstract methods."""
    with pytest.raises(TypeError):
        BaseFlow("test_flow")


def test_base_flow_get_flow_info():
    """Test that get_flow_info returns correct information."""
    flow = TestFlow("test_flow")
    info = flow.get_flow_info()
    
    assert info["name"] == "test_flow"
    assert info["tools"] == [{"name": "test_tool"}]
    assert info["functions"] == ["test_function"]
    assert info["prompts"] == ["test_prompt"]
    assert info["system_instruction"] == "test instruction"


def test_base_flow_register_with_handler():
    """Test that register_with_handler correctly registers functions."""
    class MockHandler:
        def __init__(self):
            self.registered_functions = {}
        
        def register_function(self, name, func):
            self.registered_functions[name] = func
    
    flow = TestFlow("test_flow")
    handler = MockHandler()
    
    flow.register_with_handler(handler)
    
    assert "test_function" in handler.registered_functions
    assert callable(handler.registered_functions["test_function"]) 