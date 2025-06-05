"""
Tests for the CardReplacementFlow class and its components.
"""

import pytest
from typing import Any, Dict, List

from fastagent.flows.card_replacement import CardReplacementFlow
from fastagent.flows.card_replacement.tools import get_card_replacement_tools
from fastagent.flows.card_replacement.functions import get_card_replacement_functions
from fastagent.flows.card_replacement.prompts import (
    BASE_PROMPT,
    MEMBER_ACCOUNT_CONFIRMATION_PROMPT,
    REPLACEMENT_REASON_PROMPT,
    CONFIRM_ADDRESS_PROMPT,
    START_CARD_REPLACEMENT_PROMPT,
    FINISH_CARD_REPLACEMENT_PROMPT,
    WRAP_UP_PROMPT,
    SYSTEM_INSTRUCTION,
)


def test_card_replacement_flow_initialization():
    """Test that CardReplacementFlow initializes correctly."""
    flow = CardReplacementFlow()
    assert flow.name == "card_replacement"


def test_card_replacement_flow_tools():
    """Test that get_tools returns the correct tools."""
    flow = CardReplacementFlow()
    tools = flow.get_tools()
    
    # Check that all expected tools are present
    tool_names = {tool["name"] for tool in tools}
    expected_tools = {
        "call_intent",
        "member_account_confirmation",
        "replacement_reason",
        "confirm_address",
        "start_card_replacement",
        "finish_card_replacement",
        "wrap_up",
        "transfer_to_human"
    }
    assert tool_names == expected_tools


def test_card_replacement_flow_functions():
    """Test that get_functions returns the correct functions."""
    flow = CardReplacementFlow()
    functions = flow.get_functions()
    
    # Check that all expected functions are present
    expected_functions = {
        "call_intent",
        "member_account_confirmation",
        "replacement_reason",
        "confirm_address",
        "start_card_replacement",
        "finish_card_replacement",
        "wrap_up",
        "transfer_to_human"
    }
    assert set(functions.keys()) == expected_functions


def test_card_replacement_flow_prompts():
    """Test that get_prompts returns the correct prompts."""
    flow = CardReplacementFlow()
    prompts = flow.get_prompts()
    
    assert prompts["base_prompt"] == BASE_PROMPT
    assert prompts["member_account_confirmation"] == MEMBER_ACCOUNT_CONFIRMATION_PROMPT
    assert prompts["replacement_reason"] == REPLACEMENT_REASON_PROMPT
    assert prompts["confirm_address"] == CONFIRM_ADDRESS_PROMPT
    assert prompts["start_card_replacement"] == START_CARD_REPLACEMENT_PROMPT
    assert prompts["finish_card_replacement"] == FINISH_CARD_REPLACEMENT_PROMPT
    assert prompts["wrap_up"] == WRAP_UP_PROMPT
    assert prompts["system_instruction"] == SYSTEM_INSTRUCTION


def test_card_replacement_flow_system_instruction():
    """Test that get_system_instruction returns the correct instruction."""
    flow = CardReplacementFlow()
    assert flow.get_system_instruction() == SYSTEM_INSTRUCTION


def test_card_replacement_flow_stages():
    """Test that get_flow_stages returns the correct stages."""
    flow = CardReplacementFlow()
    stages = flow.get_flow_stages()
    
    expected_stages = [
        "intent_identification",
        "account_confirmation",
        "reason_collection",
        "address_confirmation",
        "replacement_started",
        "replacement_complete",
        "call_complete"
    ]
    assert stages == expected_stages


def test_card_replacement_flow_stage_info():
    """Test that get_stage_info returns correct information for each stage."""
    flow = CardReplacementFlow()
    
    # Test a valid stage
    stage_info = flow.get_stage_info("intent_identification")
    assert stage_info["description"] == "Identify that customer wants card replacement"
    assert "call_intent" in stage_info["functions"]
    assert stage_info["next_stage"] == "account_confirmation"
    
    # Test an invalid stage
    with pytest.raises(ValueError):
        flow.get_stage_info("invalid_stage")


def test_card_replacement_flow_validation():
    """Test that validate_flow_configuration returns correct validation results."""
    flow = CardReplacementFlow()
    validation = flow.validate_flow_configuration()
    
    assert validation["valid"] is True
    assert validation["tool_count"] > 0
    assert validation["function_count"] > 0
    assert validation["prompt_count"] > 0
    assert len(validation["missing_functions"]) == 0
    assert len(validation["extra_functions"]) == 0
    assert "stages" in validation


def test_card_replacement_functions():
    """Test individual card replacement functions."""
    functions = get_card_replacement_functions()
    
    # Test call_intent
    result = functions["call_intent"]({"intent": "card_replacement"})
    assert result["status"] == "success"
    assert result["intent"] == "card_replacement"
    assert "next_action" in result
    assert "available_cards" in result
    
    # Test member_account_confirmation
    result = functions["member_account_confirmation"]({
        "member_accounts": ["Gold card", "Silver card"],
        "organization_name": "Test Bank"
    })
    assert result["status"] == "success"
    assert "prompt_guidance" in result
    assert "next_action" in result
    
    # Test replacement_reason
    result = functions["replacement_reason"]({
        "card_in_context": "Gold card",
        "reason": "Lost"
    })
    assert result["status"] == "success"
    assert result["selected_reason"] == "Lost"
    assert "next_action" in result
    
    # Test confirm_address
    result = functions["confirm_address"]({
        "card_in_context": "Gold card",
        "address_on_file": "123 Main St",
        "confirmed_address": "123 Main St"
    })
    assert result["status"] == "success"
    assert result["confirmed_address"] == "123 Main St"
    assert "next_action" in result
    
    # Test start_card_replacement
    result = functions["start_card_replacement"]({
        "card_in_context": "Gold card",
        "address_in_context": "123 Main St"
    })
    assert result["status"] == "success"
    assert "prompt_guidance" in result
    assert "next_action" in result
    
    # Test finish_card_replacement
    result = functions["finish_card_replacement"]({
        "card_in_context": "Gold card",
        "address_in_context": "123 Main St",
        "delivery_time": "5-7 business days"
    })
    assert result["status"] == "success"
    assert "delivery_time" in result
    assert "next_action" in result
    
    # Test wrap_up
    result = functions["wrap_up"]({
        "organization_name": "Test Bank"
    })
    assert result["status"] == "success"
    assert "prompt_guidance" in result
    assert "next_action" in result
    
    # Test transfer_to_human
    result = functions["transfer_to_human"]({
        "reason": "complex issue",
        "priority": "normal",
        "context": {"stage": "test"}
    })
    assert result["status"] == "success"
    assert "transfer_id" in result
    assert "priority" in result
    assert "next_action" in result


def test_card_replacement_tools():
    """Test card replacement tool definitions."""
    tools = get_card_replacement_tools()
    
    # Verify all required tools are present
    tool_names = {tool["name"] for tool in tools}
    expected_tools = {
        "call_intent",
        "member_account_confirmation",
        "replacement_reason",
        "confirm_address",
        "start_card_replacement",
        "finish_card_replacement",
        "wrap_up",
        "transfer_to_human"
    }
    assert tool_names == expected_tools
    
    # Verify tool parameters
    for tool in tools:
        assert "type" in tool
        assert "name" in tool
        assert "description" in tool
        assert "parameters" in tool
        assert "type" in tool["parameters"]
        assert "properties" in tool["parameters"] 