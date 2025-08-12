"""
Tests for Banking Agent

Tests the banking agent's tool definitions, function implementations, and configuration.
"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from opusagent.agents.banking_agent import (
    # Tool Parameters
    ProcessReplacementParameters,
    GetBalanceParameters,
    TransferFundsParameters,
    
    # Tools
    ProcessReplacementTool,
    GetBalanceTool,
    TransferFundsTool,
    
    # Functions
    func_get_balance,
    func_transfer_funds,
    func_process_replacement,
    func_transfer_to_human,
    
    # Configuration
    get_customer_service_tools,
    register_customer_service_functions,
    session_config,
    
    # Constants
    SESSION_PROMPT,
)


class TestBankingAgentToolParameters:
    """Test the banking agent tool parameters."""

    def test_process_replacement_parameters(self):
        """Test ProcessReplacementParameters structure."""
        params = ProcessReplacementParameters()
        assert params.type == "object"

        expected_properties = ["card_type", "reason", "delivery_address"]
        for prop in expected_properties:
            assert prop in params.properties

        # Check card_type parameter
        card_type_param = params.properties["card_type"]
        assert card_type_param.type == "string"
        assert card_type_param.description == "Type of card that needs replacement"

        # Check reason parameter
        reason_param = params.properties["reason"]
        assert reason_param.type == "string"
        assert reason_param.enum == ["Lost", "Damaged", "Stolen", "Other"]
        assert reason_param.description == "Reason for card replacement"

        # Check delivery_address parameter
        address_param = params.properties["delivery_address"]
        assert address_param.type == "string"
        assert address_param.description == "Address for card delivery"

    def test_get_balance_parameters(self):
        """Test GetBalanceParameters structure."""
        params = GetBalanceParameters()
        assert params.type == "object"

        expected_properties = ["account_number", "include_pending"]
        for prop in expected_properties:
            assert prop in params.properties

        # Check account_number parameter
        account_param = params.properties["account_number"]
        assert account_param.type == "string"
        assert account_param.description == "Customer's account number"

        # Check include_pending parameter
        pending_param = params.properties["include_pending"]
        assert pending_param.type == "boolean"
        assert pending_param.description == "Whether to include pending transactions"
        assert pending_param.default is True

    def test_transfer_funds_parameters(self):
        """Test TransferFundsParameters structure."""
        params = TransferFundsParameters()
        assert params.type == "object"

        expected_properties = ["from_account", "to_account", "amount", "transfer_type"]
        for prop in expected_properties:
            assert prop in params.properties

        # Check from_account parameter
        from_param = params.properties["from_account"]
        assert from_param.type == "string"
        assert from_param.description == "Source account number"

        # Check to_account parameter
        to_param = params.properties["to_account"]
        assert to_param.type == "string"
        assert to_param.description == "Destination account number"

        # Check amount parameter
        amount_param = params.properties["amount"]
        assert amount_param.type == "number"
        assert amount_param.description == "Amount to transfer"

        # Check transfer_type parameter
        type_param = params.properties["transfer_type"]
        assert type_param.type == "string"
        assert type_param.enum == ["internal", "external", "wire"]
        assert type_param.description == "Type of transfer"


class TestBankingAgentTools:
    """Test the banking agent tools."""

    def test_process_replacement_tool(self):
        """Test ProcessReplacementTool structure."""
        tool = ProcessReplacementTool()
        assert tool.name == "process_replacement"
        assert "card replacement" in tool.description.lower()
        assert isinstance(tool.parameters, ProcessReplacementParameters)

    def test_get_balance_tool(self):
        """Test GetBalanceTool structure."""
        tool = GetBalanceTool()
        assert tool.name == "get_balance"
        assert "balance" in tool.description.lower()
        assert isinstance(tool.parameters, GetBalanceParameters)

    def test_transfer_funds_tool(self):
        """Test TransferFundsTool structure."""
        tool = TransferFundsTool()
        assert tool.name == "transfer_funds"
        assert "transfer" in tool.description.lower()
        assert isinstance(tool.parameters, TransferFundsParameters)

    def test_get_customer_service_tools(self):
        """Test get_customer_service_tools returns all expected tools."""
        tools = get_customer_service_tools()
        
        # Should return list of dictionaries
        assert isinstance(tools, list)
        assert len(tools) == 4  # 3 banking tools + human handoff
        
        # Check tool names
        tool_names = [tool["name"] for tool in tools]
        expected_names = ["process_replacement", "get_balance", "transfer_funds", "human_handoff"]
        for name in expected_names:
            assert name in tool_names


class TestBankingAgentFunctions:
    """Test the banking agent function implementations."""

    def test_func_get_balance_success(self):
        """Test func_get_balance with valid arguments."""
        arguments = {
            "account_number": "1234567890",
            "include_pending": True
        }
        
        result = func_get_balance(arguments)
        
        assert result["status"] == "success"
        assert result["balance"] == 1234.56
        assert result["currency"] == "USD"
        assert result["account_number"] == "1234567890"
        assert result["pending_transactions"] is True
        assert "context" in result
        assert result["context"]["stage"] == "balance_inquiry"

    def test_func_get_balance_with_defaults(self):
        """Test func_get_balance with missing arguments."""
        arguments = {}
        
        result = func_get_balance(arguments)
        
        assert result["status"] == "success"
        assert result["account_number"] == "unknown"
        assert result["pending_transactions"] is True

    def test_func_transfer_funds_success(self):
        """Test func_transfer_funds with valid arguments."""
        arguments = {
            "from_account": "1234567890",
            "to_account": "0987654321",
            "amount": 500.00,
            "transfer_type": "internal"
        }
        
        result = func_transfer_funds(arguments)
        
        assert result["status"] == "success"
        assert result["amount"] == 500.00
        assert result["from_account"] == "1234567890"
        assert result["to_account"] == "0987654321"
        assert result["transfer_type"] == "internal"
        assert "transaction_id" in result
        assert result["transaction_id"].startswith("TX-")
        assert "context" in result
        assert result["context"]["stage"] == "transfer_complete"

    def test_func_transfer_funds_with_defaults(self):
        """Test func_transfer_funds with missing arguments."""
        arguments = {}
        
        result = func_transfer_funds(arguments)
        
        assert result["status"] == "success"
        assert result["from_account"] == "unknown"
        assert result["to_account"] == "unknown"
        assert result["amount"] == 0
        assert result["transfer_type"] == "internal"

    def test_func_process_replacement_no_card_type(self):
        """Test func_process_replacement when card_type is missing."""
        arguments = {}
        
        result = func_process_replacement(arguments)
        
        assert result["status"] == "success"
        assert result["function_name"] == "process_replacement"
        assert "ask the customer which type of card" in result["prompt_guidance"].lower()
        assert result["next_action"] == "ask_card_type"
        assert result["context"]["card_type"] is None

    def test_func_process_replacement_no_reason(self):
        """Test func_process_replacement when reason is missing."""
        arguments = {"card_type": "debit card"}
        
        result = func_process_replacement(arguments)
        
        assert result["status"] == "success"
        assert "ask the customer why" in result["prompt_guidance"].lower()
        assert result["next_action"] == "ask_reason"
        assert result["context"]["card_type"] == "debit card"
        assert result["context"]["reason"] is None

    def test_func_process_replacement_no_address(self):
        """Test func_process_replacement when delivery_address is missing."""
        arguments = {
            "card_type": "credit card",
            "reason": "Lost"
        }
        
        result = func_process_replacement(arguments)
        
        assert result["status"] == "success"
        assert "delivered" in result["prompt_guidance"].lower()
        assert result["next_action"] == "ask_delivery_address"
        assert result["context"]["card_type"] == "credit card"
        assert result["context"]["reason"] == "Lost"
        assert result["context"]["delivery_address"] is None

    def test_func_process_replacement_complete(self):
        """Test func_process_replacement with all required information."""
        arguments = {
            "card_type": "debit card",
            "reason": "Stolen",
            "delivery_address": "123 Main St, City, State 12345"
        }
        
        result = func_process_replacement(arguments)
        
        assert result["status"] == "success"
        assert "replacement has been processed" in result["prompt_guidance"]
        assert result["next_action"] == "wrap_up"
        assert result["context"]["card_type"] == "debit card"
        assert result["context"]["reason"] == "Stolen"
        assert result["context"]["delivery_address"] == "123 Main St, City, State 12345"
        assert "replacement_id" in result["context"]
        assert result["context"]["replacement_id"].startswith("CR-")

    def test_func_transfer_to_human_success(self):
        """Test func_transfer_to_human with valid arguments."""
        arguments = {
            "reason": "complex transaction",
            "priority": "high",
            "context": {"customer_id": "12345"}
        }
        
        result = func_transfer_to_human(arguments)
        
        assert result["status"] == "success"
        assert result["function_name"] == "transfer_to_human"
        assert "transfer you now" in result["prompt_guidance"]
        assert result["next_action"] == "end_call"
        assert result["priority"] == "high"
        assert result["context"]["stage"] == "human_transfer"
        assert result["context"]["reason"] == "complex transaction"
        assert result["context"]["customer_id"] == "12345"
        assert "transfer_id" in result["context"]
        assert result["context"]["transfer_id"].startswith("TR-")

    def test_func_transfer_to_human_with_defaults(self):
        """Test func_transfer_to_human with missing arguments."""
        arguments = {}
        
        result = func_transfer_to_human(arguments)
        
        assert result["status"] == "success"
        assert result["context"]["reason"] == "general inquiry"
        assert result["priority"] == "normal"
        assert "transfer you now" in result["prompt_guidance"]


class TestBankingAgentFunctionRegistration:
    """Test function registration with function handler."""

    def test_register_customer_service_functions(self):
        """Test registering all customer service functions."""
        mock_handler = Mock()
        
        register_customer_service_functions(mock_handler)
        
        # Verify all functions were registered
        expected_calls = [
            ("get_balance", func_get_balance),
            ("transfer_funds", func_transfer_funds),
            ("process_replacement", func_process_replacement),
            ("transfer_to_human", func_transfer_to_human),
            ("human_handoff", func_transfer_to_human),
        ]
        
        assert mock_handler.register_function.call_count == 5
        
        for func_name, func in expected_calls:
            mock_handler.register_function.assert_any_call(func_name, func)


class TestBankingAgentConfiguration:
    """Test the banking agent configuration."""

    def test_session_config_structure(self):
        """Test session_config has correct structure."""
        assert session_config.model == "gpt-4o-realtime-preview-2025-06-03"
        assert session_config.input_audio_format == "pcm16"
        assert session_config.output_audio_format == "pcm16"
        assert session_config.voice == "verse"
        assert session_config.instructions == SESSION_PROMPT
        assert "text" in session_config.modalities
        assert "audio" in session_config.modalities
        assert session_config.temperature == 0.6
        assert session_config.tool_choice == "auto"
        assert session_config.max_response_output_tokens == 4096

    def test_session_prompt_content(self):
        """Test SESSION_PROMPT contains expected content."""
        assert "customer service agent" in SESSION_PROMPT.lower()
        assert "card replacement" in SESSION_PROMPT.lower()
        assert "account inquiry" in SESSION_PROMPT.lower()
        assert "transfer_funds" in SESSION_PROMPT.lower()
        assert "human_handoff" in SESSION_PROMPT.lower()
        assert "greeting" in SESSION_PROMPT.lower()

    def test_tools_in_session_config(self):
        """Test that tools are properly configured in session_config."""
        tools = session_config.tools
        assert isinstance(tools, list)
        assert len(tools) == 4  # 3 banking tools + human handoff
        
        tool_names = [tool["name"] for tool in tools]
        expected_names = ["process_replacement", "get_balance", "transfer_funds", "human_handoff"]
        for name in expected_names:
            assert name in tool_names


class TestBankingAgentIntegration:
    """Integration tests for banking agent components."""

    def test_tool_parameter_consistency(self):
        """Test that tool parameters are consistent with function expectations."""
        # Test that all required parameters in tools match function expectations
        replacement_params = ProcessReplacementParameters()
        balance_params = GetBalanceParameters()
        transfer_params = TransferFundsParameters()
        
        # Process replacement should handle all parameters
        replacement_tool_params = set(replacement_params.properties.keys())
        assert "card_type" in replacement_tool_params
        assert "reason" in replacement_tool_params
        assert "delivery_address" in replacement_tool_params
        
        # Balance inquiry should handle all parameters
        balance_tool_params = set(balance_params.properties.keys())
        assert "account_number" in balance_tool_params
        assert "include_pending" in balance_tool_params
        
        # Transfer should handle all parameters
        transfer_tool_params = set(transfer_params.properties.keys())
        assert "from_account" in transfer_tool_params
        assert "to_account" in transfer_tool_params
        assert "amount" in transfer_tool_params
        assert "transfer_type" in transfer_tool_params

    def test_function_return_consistency(self):
        """Test that all functions return consistent response structures."""
        test_arguments = {
            "get_balance": {"account_number": "12345"},
            "transfer_funds": {"from_account": "12345", "to_account": "67890", "amount": 100},
            "process_replacement": {"card_type": "debit card", "reason": "Lost", "delivery_address": "123 Main St"},
        }
        
        for func_name, args in test_arguments.items():
            if func_name == "get_balance":
                result = func_get_balance(args)
            elif func_name == "transfer_funds":
                result = func_transfer_funds(args)
            elif func_name == "process_replacement":
                result = func_process_replacement(args)
            
            # All functions should return a dictionary with status
            assert isinstance(result, dict)
            assert "status" in result
            assert result["status"] == "success"
            assert "context" in result
            assert isinstance(result["context"], dict)
