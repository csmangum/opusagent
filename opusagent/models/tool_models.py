"""
OpenAI Function Tool Models

Base Pydantic models for defining OpenAI function tools in a type-safe way.
These are generic models that can be extended for specific use cases.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class PriorityLevel(str, Enum):
    """Enumeration of transfer priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class ToolParameter(BaseModel):
    """Base model for tool parameters."""

    type: str
    description: Optional[str] = None
    enum: Optional[List[str]] = None
    default: Optional[Any] = None

    def model_dump(self, **kwargs):
        data = super().model_dump(**kwargs)
        # Remove fields that are None
        return {k: v for k, v in data.items() if v is not None}


class ToolParameters(BaseModel):
    """Model for tool parameters schema."""

    type: str = "object"
    properties: Dict[str, ToolParameter]
    required: Optional[List[str]] = None

    def model_dump(self, **kwargs):
        data = super().model_dump(**kwargs)
        # Convert ToolParameter objects to dictionaries and remove None values
        if "properties" in data:
            def clean(d):
                return {k: v for k, v in d.items() if v is not None}
            data["properties"] = {
                key: clean(param.model_dump() if hasattr(param, 'model_dump') else param)
                for key, param in data["properties"].items()
            }
        # Remove required field if it's None to avoid validation errors
        if data.get("required") is None:
            data.pop("required", None)
        return data


class OpenAITool(BaseModel):
    """Model for OpenAI function tool definition."""

    type: str = "function"
    name: str
    description: str
    parameters: ToolParameters

    def model_dump(self, **kwargs):
        data = super().model_dump(**kwargs)
        # Ensure parameters are properly serialized
        if hasattr(self.parameters, 'model_dump'):
            data['parameters'] = self.parameters.model_dump()
        return data


class HumanHandoffParameters(ToolParameters):
    """Parameters for the human_handoff function."""

    type: str = "object"
    properties: Dict[str, ToolParameter] = {
        "reason": ToolParameter(
            type="string", description="The reason for transferring to a human agent"
        ),
        "priority": ToolParameter(
            type="string",
            enum=[priority.value for priority in PriorityLevel],
            description="The priority level of the transfer",
        ),
        "context": ToolParameter(
            type="object", description="Additional context for the human agent"
        ),
    }


class HumanHandoffTool(OpenAITool):
    """Tool for transferring to human agent."""

    name: str = "human_handoff"
    description: str = "Transfer the conversation to a human agent."
    parameters: HumanHandoffParameters = HumanHandoffParameters()


def get_tool_by_name(tool_name: str) -> Dict[str, Any]:
    """
    Get a specific tool definition by name.

    Args:
        tool_name: Name of the tool to retrieve

    Returns:
        Tool definition dictionary

    Raises:
        ValueError: If tool name is not found
    """
    tool_map = {
        "human_handoff": HumanHandoffTool(),
    }

    if tool_name not in tool_map:
        available_tools = list(tool_map.keys())
        raise ValueError(
            f"Tool '{tool_name}' not found. Available tools: {available_tools}"
        )

    return tool_map[tool_name].model_dump()
