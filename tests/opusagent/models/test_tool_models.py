"""
Tests for OpenAI Function Tool Models

Tests the Pydantic models for defining OpenAI function tools.
"""

import pytest
from opusagent.models.tool_models import (
    PriorityLevel,
    ToolParameter,
    ToolParameters,
    OpenAITool,
    HumanHandoffParameters,
    HumanHandoffTool,
)


class TestEnums:
    """Test the enumeration classes."""
    
    def test_priority_level_values(self):
        """Test that PriorityLevel has the expected values."""
        assert PriorityLevel.LOW == "low"
        assert PriorityLevel.NORMAL == "normal"
        assert PriorityLevel.HIGH == "high"


class TestToolParameter:
    """Test the ToolParameter model."""
    
    def test_basic_tool_parameter(self):
        """Test creating a basic tool parameter."""
        param = ToolParameter(type="string", description="Test parameter")
        assert param.type == "string"
        assert param.description == "Test parameter"
        assert param.enum is None
        assert param.default is None
    
    def test_tool_parameter_with_enum(self):
        """Test creating a tool parameter with enum values."""
        param = ToolParameter(
            type="string",
            enum=["option1", "option2"],
            description="Test parameter with enum"
        )
        assert param.type == "string"
        assert param.enum == ["option1", "option2"]
        assert param.description == "Test parameter with enum"


class TestToolParameters:
    """Test the ToolParameters model."""
    
    def test_basic_tool_parameters(self):
        """Test creating basic tool parameters."""
        properties = {
            "test_param": ToolParameter(type="string", description="Test")
        }
        params = ToolParameters(properties=properties)
        assert params.type == "object"
        assert "test_param" in params.properties
        assert params.required is None
    
    def test_tool_parameters_with_required(self):
        """Test creating tool parameters with required fields."""
        properties = {
            "test_param": ToolParameter(type="string", description="Test")
        }
        required = ["test_param"]
        params = ToolParameters(properties=properties, required=required)
        assert params.required == ["test_param"]


class TestOpenAITool:
    """Test the OpenAITool base model."""
    
    def test_basic_openai_tool(self):
        """Test creating a basic OpenAI tool."""
        properties = {
            "test_param": ToolParameter(type="string", description="Test")
        }
        parameters = ToolParameters(properties=properties)
        
        tool = OpenAITool(
            name="test_tool",
            description="Test tool description",
            parameters=parameters
        )
        
        assert tool.type == "function"
        assert tool.name == "test_tool"
        assert tool.description == "Test tool description"
        assert tool.parameters == parameters


class TestHumanHandoffParameters:
    """Test the HumanHandoffParameters model."""
    
    def test_human_handoff_parameters_structure(self):
        """Test that HumanHandoffParameters has the correct structure."""
        params = HumanHandoffParameters()
        assert params.type == "object"
        
        expected_properties = ["reason", "priority", "context"]
        for prop in expected_properties:
            assert prop in params.properties
        
        # Check reason parameter
        reason_param = params.properties["reason"]
        assert reason_param.type == "string"
        assert reason_param.description == "The reason for transferring to a human agent"
        
        # Check priority parameter
        priority_param = params.properties["priority"]
        assert priority_param.type == "string"
        assert priority_param.enum == [priority.value for priority in PriorityLevel]
        assert priority_param.description == "The priority level of the transfer"
        
        # Check context parameter
        context_param = params.properties["context"]
        assert context_param.type == "object"
        assert context_param.description == "Additional context for the human agent"


class TestHumanHandoffTool:
    """Test the HumanHandoffTool model."""
    
    def test_human_handoff_tool_structure(self):
        """Test that HumanHandoffTool has the correct structure."""
        tool = HumanHandoffTool()
        
        assert tool.type == "function"
        assert tool.name == "human_handoff"
        assert tool.description == "Transfer the conversation to a human agent."
        assert isinstance(tool.parameters, HumanHandoffParameters)
    
    def test_human_handoff_tool_serialization(self):
        """Test that HumanHandoffTool serializes to the expected JSON structure."""
        tool = HumanHandoffTool()
        tool_dict = tool.model_dump()
        
        assert tool_dict["type"] == "function"
        assert tool_dict["name"] == "human_handoff"
        assert tool_dict["description"] == "Transfer the conversation to a human agent."
        assert tool_dict["parameters"]["type"] == "object"
        
        expected_properties = ["reason", "priority", "context"]
        for prop in expected_properties:
            assert prop in tool_dict["parameters"]["properties"] 