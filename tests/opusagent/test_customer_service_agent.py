"""
Tests for Customer Service Agent

Tests the customer service agent's tool definitions and configuration.
"""

import pytest
from opusagent.customer_service_agent import (
    ProcessReplacementParameters,
    GetBalanceParameters,
    TransferFundsParameters,
    CallIntentParameters,
    ProcessReplacementTool,
    GetBalanceTool,
    TransferFundsTool,
    CallIntentTool,
    get_customer_service_tools,
    session_config,
)


class TestCustomerServiceToolParameters:
    """Test the customer service specific tool parameters."""
    
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
    
    def test_call_intent_parameters(self):
        """Test CallIntentParameters structure."""
        params = CallIntentParameters()
        assert params.type == "object"
        
        expected_properties = ["intent", "confidence", "additional_context"]
        for prop in expected_properties:
            assert prop in params.properties
        
        # Check intent parameter
        intent_param = params.properties["intent"]
        assert intent_param.type == "string"
        assert intent_param.enum == ["Card Replacement", "Account Inquiry", "Account Management", "Transaction Dispute", "Other"]
        assert intent_param.description == "The determined intent of the call"
        
        # Check confidence parameter
        confidence_param = params.properties["confidence"]
        assert confidence_param.type == "number"
        assert confidence_param.description == "Confidence level in the intent determination (0-1)"
        
        # Check additional_context parameter
        context_param = params.properties["additional_context"]
        assert context_param.type == "string"
        assert context_param.description == "Any additional context about the call"


class TestCustomerServiceTools:
    """Test the customer service specific tools."""
    
    def test_process_replacement_tool(self):
        """Test ProcessReplacementTool structure."""
        tool = ProcessReplacementTool()
        
        assert tool.type == "function"
        assert tool.name == "process_replacement"
        assert tool.description == "Process a card replacement request for the customer."
        assert isinstance(tool.parameters, ProcessReplacementParameters)
    
    def test_get_balance_tool(self):
        """Test GetBalanceTool structure."""
        tool = GetBalanceTool()
        
        assert tool.type == "function"
        assert tool.name == "get_balance"
        assert tool.description == "Get the current balance for a customer's account."
        assert isinstance(tool.parameters, GetBalanceParameters)
    
    def test_transfer_funds_tool(self):
        """Test TransferFundsTool structure."""
        tool = TransferFundsTool()
        
        assert tool.type == "function"
        assert tool.name == "transfer_funds"
        assert tool.description == "Transfer funds between customer accounts."
        assert isinstance(tool.parameters, TransferFundsParameters)
    
    def test_call_intent_tool(self):
        """Test CallIntentTool structure."""
        tool = CallIntentTool()
        
        assert tool.type == "function"
        assert tool.name == "call_intent"
        assert tool.description == "Determine the intent of the customer's call."
        assert isinstance(tool.parameters, CallIntentParameters)


class TestCustomerServiceToolFunctions:
    """Test the utility functions for customer service tools."""
    
    def test_get_customer_service_tools(self):
        """Test getting all customer service tools."""
        tools = get_customer_service_tools()
        
        assert len(tools) == 5
        
        tool_names = {tool["name"] for tool in tools}
        expected_names = {"process_replacement", "get_balance", "transfer_funds", "call_intent", "human_handoff"}
        assert tool_names == expected_names
        
        # Verify each tool has the required structure
        for tool in tools:
            assert "type" in tool
            assert "name" in tool
            assert "description" in tool
            assert "parameters" in tool
            assert tool["type"] == "function"


class TestSessionConfig:
    """Test the session configuration."""
    
    def test_session_config_has_tools(self):
        """Test that session config has the expected tools."""
        assert hasattr(session_config, 'tools')
        assert session_config.tools is not None
        assert len(session_config.tools) == 5
        
        tool_names = {tool["name"] for tool in session_config.tools}
        expected_names = {"process_replacement", "get_balance", "transfer_funds", "call_intent", "human_handoff"}
        assert tool_names == expected_names
    
    def test_session_config_has_instructions(self):
        """Test that session config has instructions."""
        assert hasattr(session_config, 'instructions')
        assert session_config.instructions is not None
        assert "customer service agent" in session_config.instructions.lower()
        assert "process_replacement" in session_config.instructions
        assert "get_balance" in session_config.instructions
        assert "transfer_funds" in session_config.instructions
        assert "call_intent" in session_config.instructions
        assert "human_handoff" in session_config.instructions 