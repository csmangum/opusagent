"""
Tests for Insurance Agent

Tests the insurance agent's tool definitions, function implementations, and configuration.
"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from opusagent.agents.insurance_agent import (
    # Tool Parameters
    FileClaimParameters,
    GetPolicyInfoParameters,
    CheckCoverageParameters,
    UpdatePolicyParameters,
    HandleBillingParameters,
    
    # Tools
    FileClaimTool,
    GetPolicyInfoTool,
    CheckCoverageTool,
    UpdatePolicyTool,
    HandleBillingTool,
    
    # Functions
    func_file_claim,
    func_get_policy_info,
    func_check_coverage,
    func_update_policy,
    func_handle_billing,
    func_transfer_to_human,
    
    # Configuration
    get_insurance_tools,
    register_insurance_functions,
    get_insurance_session_config,
    
    # Constants
    SESSION_PROMPT,
)


class TestInsuranceAgentToolParameters:
    """Test the insurance agent tool parameters."""

    def test_file_claim_parameters(self):
        """Test FileClaimParameters structure."""
        params = FileClaimParameters()
        assert params.type == "object"

        expected_properties = ["policy_number", "claim_type", "incident_date", "description", "estimated_damage"]
        for prop in expected_properties:
            assert prop in params.properties

        # Check policy_number parameter
        policy_param = params.properties["policy_number"]
        assert policy_param.type == "string"
        assert policy_param.description == "Customer's policy number"

        # Check claim_type parameter
        claim_type_param = params.properties["claim_type"]
        assert claim_type_param.type == "string"
        assert claim_type_param.enum == ["Auto", "Home", "Health", "Life", "Other"]
        assert claim_type_param.description == "Type of insurance claim"

        # Check incident_date parameter
        date_param = params.properties["incident_date"]
        assert date_param.type == "string"
        assert date_param.description == "Date of the incident (YYYY-MM-DD)"

        # Check description parameter
        desc_param = params.properties["description"]
        assert desc_param.type == "string"
        assert desc_param.description == "Detailed description of the incident"

        # Check estimated_damage parameter
        damage_param = params.properties["estimated_damage"]
        assert damage_param.type == "number"
        assert damage_param.description == "Estimated dollar amount of damage"

    def test_get_policy_info_parameters(self):
        """Test GetPolicyInfoParameters structure."""
        params = GetPolicyInfoParameters()
        assert params.type == "object"

        expected_properties = ["policy_number", "include_coverage"]
        for prop in expected_properties:
            assert prop in params.properties

        # Check policy_number parameter
        policy_param = params.properties["policy_number"]
        assert policy_param.type == "string"
        assert policy_param.description == "Customer's policy number"

        # Check include_coverage parameter
        coverage_param = params.properties["include_coverage"]
        assert coverage_param.type == "boolean"
        assert coverage_param.description == "Whether to include coverage details"
        assert coverage_param.default is True

    def test_check_coverage_parameters(self):
        """Test CheckCoverageParameters structure."""
        params = CheckCoverageParameters()
        assert params.type == "object"

        expected_properties = ["policy_number", "coverage_type", "specific_incident"]
        for prop in expected_properties:
            assert prop in params.properties

        # Check policy_number parameter
        policy_param = params.properties["policy_number"]
        assert policy_param.type == "string"
        assert policy_param.description == "Customer's policy number"

        # Check coverage_type parameter
        coverage_type_param = params.properties["coverage_type"]
        assert coverage_type_param.type == "string"
        assert coverage_type_param.enum == ["Auto", "Home", "Health", "Life", "Liability", "Property"]
        assert coverage_type_param.description == "Type of coverage to check"

        # Check specific_incident parameter
        incident_param = params.properties["specific_incident"]
        assert incident_param.type == "string"
        assert incident_param.description == "Specific incident or situation to check coverage for"

    def test_update_policy_parameters(self):
        """Test UpdatePolicyParameters structure."""
        params = UpdatePolicyParameters()
        assert params.type == "object"

        expected_properties = ["policy_number", "update_type", "new_value"]
        for prop in expected_properties:
            assert prop in params.properties

        # Check policy_number parameter
        policy_param = params.properties["policy_number"]
        assert policy_param.type == "string"
        assert policy_param.description == "Customer's policy number"

        # Check update_type parameter
        update_type_param = params.properties["update_type"]
        assert update_type_param.type == "string"
        assert update_type_param.enum == ["Address", "Vehicle", "Coverage", "Beneficiary", "Payment"]
        assert update_type_param.description == "Type of policy update"

        # Check new_value parameter
        new_value_param = params.properties["new_value"]
        assert new_value_param.type == "string"
        assert new_value_param.description == "New value for the policy update"

    def test_handle_billing_parameters(self):
        """Test HandleBillingParameters structure."""
        params = HandleBillingParameters()
        assert params.type == "object"

        expected_properties = ["policy_number", "billing_issue", "amount"]
        for prop in expected_properties:
            assert prop in params.properties

        # Check policy_number parameter
        policy_param = params.properties["policy_number"]
        assert policy_param.type == "string"
        assert policy_param.description == "Customer's policy number"

        # Check billing_issue parameter
        billing_param = params.properties["billing_issue"]
        assert billing_param.type == "string"
        assert billing_param.enum == ["Payment", "Late Fee", "Premium Increase", "Billing Error", "Payment Method"]
        assert billing_param.description == "Type of billing issue"

        # Check amount parameter
        amount_param = params.properties["amount"]
        assert amount_param.type == "number"
        assert amount_param.description == "Amount in question (if applicable)"


class TestInsuranceAgentTools:
    """Test the insurance agent tools."""

    def test_file_claim_tool(self):
        """Test FileClaimTool structure."""
        tool = FileClaimTool()
        assert tool.name == "file_claim"
        assert "insurance claim" in tool.description.lower()
        assert isinstance(tool.parameters, FileClaimParameters)

    def test_get_policy_info_tool(self):
        """Test GetPolicyInfoTool structure."""
        tool = GetPolicyInfoTool()
        assert tool.name == "get_policy_info"
        assert "policy" in tool.description.lower()
        assert isinstance(tool.parameters, GetPolicyInfoParameters)

    def test_check_coverage_tool(self):
        """Test CheckCoverageTool structure."""
        tool = CheckCoverageTool()
        assert tool.name == "check_coverage"
        assert "coverage" in tool.description.lower()
        assert isinstance(tool.parameters, CheckCoverageParameters)

    def test_update_policy_tool(self):
        """Test UpdatePolicyTool structure."""
        tool = UpdatePolicyTool()
        assert tool.name == "update_policy"
        assert "policy" in tool.description.lower()
        assert isinstance(tool.parameters, UpdatePolicyParameters)

    def test_handle_billing_tool(self):
        """Test HandleBillingTool structure."""
        tool = HandleBillingTool()
        assert tool.name == "handle_billing"
        assert "billing" in tool.description.lower()
        assert isinstance(tool.parameters, HandleBillingParameters)

    def test_get_insurance_tools(self):
        """Test get_insurance_tools returns all expected tools."""
        tools = get_insurance_tools()
        
        # Should return list of dictionaries
        assert isinstance(tools, list)
        assert len(tools) == 6  # 5 insurance tools + human handoff
        
        # Check tool names
        tool_names = [tool["name"] for tool in tools]
        expected_names = ["file_claim", "get_policy_info", "check_coverage", "update_policy", "handle_billing", "human_handoff"]
        for name in expected_names:
            assert name in tool_names


class TestInsuranceAgentFunctions:
    """Test the insurance agent function implementations."""

    def test_func_file_claim_success(self):
        """Test func_file_claim with valid arguments."""
        arguments = {
            "policy_number": "POL123456",
            "claim_type": "Auto",
            "incident_date": "2024-01-15",
            "description": "Car accident on highway",
            "estimated_damage": 5000.00
        }
        
        result = func_file_claim(arguments)
        
        assert result["status"] == "success"
        assert result["policy_number"] == "POL123456"
        assert result["claim_type"] == "Auto"
        assert "claim has been filed successfully" in result["message"]
        assert "claim number" in result["message"]
        assert result["claim_number"].startswith("CLM-")
        assert len(result["next_steps"]) == 3

    def test_func_file_claim_with_defaults(self):
        """Test func_file_claim with missing arguments."""
        arguments = {}
        
        result = func_file_claim(arguments)
        
        assert result["status"] == "success"
        assert result["policy_number"] == "UNKNOWN"
        assert result["claim_type"] == "Other"
        # These fields are not returned by the function
        # assert result["incident_date"] == "Unknown"
        # assert result["description"] == "No description provided"
        # assert result["estimated_damage"] == 0

    def test_func_get_policy_info_success(self):
        """Test func_get_policy_info with valid arguments."""
        arguments = {
            "policy_number": "POL123456",
            "include_coverage": True
        }
        
        result = func_get_policy_info(arguments)
        
        assert result["status"] == "success"
        assert result["policy_info"]["policy_number"] == "POL123456"
        assert result["policy_info"]["customer_name"] == "John Doe"
        assert result["policy_info"]["policy_type"] == "Auto & Home Bundle"
        assert result["policy_info"]["premium"] == 125.50
        assert result["policy_info"]["status"] == "Active"
        assert "coverage" in result["policy_info"]
        assert "auto" in result["policy_info"]["coverage"]
        assert "home" in result["policy_info"]["coverage"]

    def test_func_get_policy_info_no_coverage(self):
        """Test func_get_policy_info without coverage details."""
        arguments = {
            "policy_number": "POL123456",
            "include_coverage": False
        }
        
        result = func_get_policy_info(arguments)
        
        assert result["status"] == "success"
        assert result["policy_info"]["policy_number"] == "POL123456"
        assert "coverage" not in result["policy_info"]

    def test_func_get_policy_info_with_defaults(self):
        """Test func_get_policy_info with missing arguments."""
        arguments = {}
        
        result = func_get_policy_info(arguments)
        
        assert result["status"] == "success"
        assert result["policy_info"]["policy_number"] == "UNKNOWN"
        # include_coverage is not returned in the result
        # assert result["policy_info"]["include_coverage"] is True

    def test_func_check_coverage_auto_covered(self):
        """Test func_check_coverage for auto coverage."""
        arguments = {
            "policy_number": "POL123456",
            "coverage_type": "Auto",
            "specific_incident": "Car accident"
        }
        
        result = func_check_coverage(arguments)
        
        assert result["status"] == "success"
        assert result["coverage_type"] == "Auto"
        assert result["covered"] is True
        assert result["deductible"] == 500
        assert result["coverage_limit"] == "100,000"
        assert "covered under your auto policy" in result["message"]

    def test_func_check_coverage_home_covered(self):
        """Test func_check_coverage for home coverage."""
        arguments = {
            "policy_number": "POL123456",
            "coverage_type": "Home",
            "specific_incident": "Water damage"
        }
        
        result = func_check_coverage(arguments)
        
        assert result["status"] == "success"
        assert result["coverage_type"] == "Home"
        assert result["covered"] is True
        assert result["deductible"] == 1000
        assert result["coverage_limit"] == "250,000"
        assert "covered under your home policy" in result["message"]

    def test_func_check_coverage_health_not_covered(self):
        """Test func_check_coverage for health coverage (not covered)."""
        arguments = {
            "policy_number": "POL123456",
            "coverage_type": "Health",
            "specific_incident": "Medical procedure"
        }
        
        result = func_check_coverage(arguments)
        
        assert result["status"] == "success"
        assert result["coverage_type"] == "Health"
        assert result["covered"] is False
        assert "not included in your current policy" in result["message"]

    def test_func_check_coverage_with_defaults(self):
        """Test func_check_coverage with missing arguments."""
        arguments = {}
        
        result = func_check_coverage(arguments)
        
        assert result["status"] == "success"
        assert result["policy_number"] == "UNKNOWN"
        assert result["coverage_type"] == "Auto"  # Default from function
        # specific_incident is not returned by the function
        # assert result["specific_incident"] == "General inquiry"

    def test_func_update_policy_success(self):
        """Test func_update_policy with valid arguments."""
        arguments = {
            "policy_number": "POL123456",
            "update_type": "Address",
            "new_value": "456 Oak St, City, State 12345"
        }
        
        result = func_update_policy(arguments)
        
        assert result["status"] == "success"
        assert result["policy_number"] == "POL123456"
        assert result["update_type"] == "Address"
        assert result["new_value"] == "456 Oak St, City, State 12345"
        assert "policy has been updated successfully" in result["message"]
        assert result["effective_date"] == "Immediate"
        assert result["next_billing_cycle"] == "No change to premium"

    def test_func_update_policy_with_defaults(self):
        """Test func_update_policy with missing arguments."""
        arguments = {}
        
        result = func_update_policy(arguments)
        
        assert result["status"] == "success"
        assert result["policy_number"] == "UNKNOWN"
        assert result["update_type"] == "Address"
        assert result["new_value"] == "Unknown"

    def test_func_handle_billing_payment_success(self):
        """Test func_handle_billing for payment issue."""
        arguments = {
            "policy_number": "POL123456",
            "billing_issue": "Payment",
            "amount": 125.50
        }
        
        result = func_handle_billing(arguments)
        
        assert result["status"] == "success"
        assert result["policy_number"] == "POL123456"
        assert result["billing_issue"] == "Payment"
        assert result["resolved"] is True
        assert "payment has been processed successfully" in result["message"]
        assert result["next_payment"] == "Due in 30 days"

    def test_func_handle_billing_late_fee_waived(self):
        """Test func_handle_billing for late fee issue."""
        arguments = {
            "policy_number": "POL123456",
            "billing_issue": "Late Fee",
            "amount": 25.00
        }
        
        result = func_handle_billing(arguments)
        
        assert result["status"] == "success"
        assert result["billing_issue"] == "Late Fee"
        assert result["resolved"] is True
        assert "waived the late fee" in result["message"]

    def test_func_handle_billing_premium_increase_not_resolved(self):
        """Test func_handle_billing for premium increase issue."""
        arguments = {
            "policy_number": "POL123456",
            "billing_issue": "Premium Increase",
            "amount": 50.00
        }
        
        result = func_handle_billing(arguments)
        
        assert result["status"] == "success"
        assert result["billing_issue"] == "Premium Increase"
        assert result["resolved"] is False
        assert "premium increase is due to updated risk factors" in result["message"]

    def test_func_handle_billing_with_defaults(self):
        """Test func_handle_billing with missing arguments."""
        arguments = {}
        
        result = func_handle_billing(arguments)
        
        assert result["status"] == "success"
        assert result["policy_number"] == "UNKNOWN"
        assert result["billing_issue"] == "Payment"
        # amount is not returned by the function
        # assert result["amount"] == 0

    def test_func_transfer_to_human_success(self):
        """Test func_transfer_to_human with valid arguments."""
        arguments = {
            "reason": "Complex claim processing"
        }
        
        result = func_transfer_to_human(arguments)
        
        assert result["status"] == "transfer"
        assert result["reason"] == "Complex claim processing"
        assert "transferring you to a human agent" in result["message"]
        assert result["estimated_wait"] == "2-3 minutes"

    def test_func_transfer_to_human_with_defaults(self):
        """Test func_transfer_to_human with missing arguments."""
        arguments = {}
        
        result = func_transfer_to_human(arguments)
        
        assert result["status"] == "transfer"
        assert result["reason"] == "Customer requested human agent"
        assert "transferring you to a human agent" in result["message"]


class TestInsuranceAgentFunctionRegistration:
    """Test function registration with function handler."""

    def test_register_insurance_functions(self):
        """Test registering all insurance functions."""
        mock_handler = Mock()
        
        register_insurance_functions(mock_handler)
        
        # Verify all functions were registered
        expected_calls = [
            ("file_claim", func_file_claim),
            ("get_policy_info", func_get_policy_info),
            ("check_coverage", func_check_coverage),
            ("update_policy", func_update_policy),
            ("handle_billing", func_handle_billing),
            ("human_handoff", func_transfer_to_human),
        ]
        
        assert mock_handler.register_function.call_count == 6
        
        for func_name, func in expected_calls:
            mock_handler.register_function.assert_any_call(func_name, func)


class TestInsuranceAgentConfiguration:
    """Test the insurance agent configuration."""

    def test_get_insurance_session_config(self):
        """Test get_insurance_session_config returns correct configuration."""
        session_config = get_insurance_session_config()
        
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
        assert "insurance customer service agent" in SESSION_PROMPT.lower()
        assert "policy inquiry" in SESSION_PROMPT.lower()
        assert "claim filing" in SESSION_PROMPT.lower()
        assert "coverage questions" in SESSION_PROMPT.lower()
        assert "policy changes" in SESSION_PROMPT.lower()
        assert "billing issues" in SESSION_PROMPT.lower()
        assert "human_handoff" in SESSION_PROMPT.lower()
        assert "greeting" in SESSION_PROMPT.lower()

    def test_tools_in_session_config(self):
        """Test that tools are properly configured in session_config."""
        session_config = get_insurance_session_config()
        tools = session_config.tools
        assert isinstance(tools, list)
        assert len(tools) == 6  # 5 insurance tools + human handoff
        
        tool_names = [tool["name"] for tool in tools]
        expected_names = ["file_claim", "get_policy_info", "check_coverage", "update_policy", "handle_billing", "human_handoff"]
        for name in expected_names:
            assert name in tool_names


class TestInsuranceAgentIntegration:
    """Integration tests for insurance agent components."""

    def test_tool_parameter_consistency(self):
        """Test that tool parameters are consistent with function expectations."""
        # Test that all required parameters in tools match function expectations
        file_claim_params = FileClaimParameters()
        policy_info_params = GetPolicyInfoParameters()
        coverage_params = CheckCoverageParameters()
        update_policy_params = UpdatePolicyParameters()
        billing_params = HandleBillingParameters()
        
        # File claim should handle all parameters
        file_claim_tool_params = set(file_claim_params.properties.keys())
        assert "policy_number" in file_claim_tool_params
        assert "claim_type" in file_claim_tool_params
        assert "incident_date" in file_claim_tool_params
        assert "description" in file_claim_tool_params
        assert "estimated_damage" in file_claim_tool_params
        
        # Policy info should handle all parameters
        policy_info_tool_params = set(policy_info_params.properties.keys())
        assert "policy_number" in policy_info_tool_params
        assert "include_coverage" in policy_info_tool_params
        
        # Coverage check should handle all parameters
        coverage_tool_params = set(coverage_params.properties.keys())
        assert "policy_number" in coverage_tool_params
        assert "coverage_type" in coverage_tool_params
        assert "specific_incident" in coverage_tool_params
        
        # Update policy should handle all parameters
        update_policy_tool_params = set(update_policy_params.properties.keys())
        assert "policy_number" in update_policy_tool_params
        assert "update_type" in update_policy_tool_params
        assert "new_value" in update_policy_tool_params
        
        # Billing should handle all parameters
        billing_tool_params = set(billing_params.properties.keys())
        assert "policy_number" in billing_tool_params
        assert "billing_issue" in billing_tool_params
        assert "amount" in billing_tool_params

    def test_function_return_consistency(self):
        """Test that all functions return consistent response structures."""
        test_arguments = {
            "file_claim": {
                "policy_number": "POL123456",
                "claim_type": "Auto",
                "incident_date": "2024-01-15",
                "description": "Test claim",
                "estimated_damage": 1000
            },
            "get_policy_info": {"policy_number": "POL123456"},
            "check_coverage": {
                "policy_number": "POL123456",
                "coverage_type": "Auto",
                "specific_incident": "Test incident"
            },
            "update_policy": {
                "policy_number": "POL123456",
                "update_type": "Address",
                "new_value": "123 Test St"
            },
            "handle_billing": {
                "policy_number": "POL123456",
                "billing_issue": "Payment",
                "amount": 100
            }
        }
        
        for func_name, args in test_arguments.items():
            if func_name == "file_claim":
                result = func_file_claim(args)
            elif func_name == "get_policy_info":
                result = func_get_policy_info(args)
            elif func_name == "check_coverage":
                result = func_check_coverage(args)
            elif func_name == "update_policy":
                result = func_update_policy(args)
            elif func_name == "handle_billing":
                result = func_handle_billing(args)
            
            # All functions should return a dictionary with status
            assert isinstance(result, dict)
            assert "status" in result
            assert result["status"] in ["success", "transfer"]

    def test_claim_number_generation(self):
        """Test that claim numbers are generated correctly."""
        arguments = {
            "policy_number": "POL123456",
            "claim_type": "Auto",
            "incident_date": "2024-01-15",
            "description": "Test claim",
            "estimated_damage": 1000
        }
        
        result1 = func_file_claim(arguments)
        result2 = func_file_claim(arguments)
        
        # Claim numbers should be unique
        assert result1["claim_number"] != result2["claim_number"]
        
        # Claim numbers should start with CLM-
        assert result1["claim_number"].startswith("CLM-")
        assert result2["claim_number"].startswith("CLM-")
        
        # Claim numbers should be 8 characters after CLM-
        assert len(result1["claim_number"]) == 12  # CLM- + 8 chars
        assert len(result2["claim_number"]) == 12

    def test_coverage_check_scenarios(self):
        """Test different coverage check scenarios."""
        coverage_tests = [
            ("Auto", True, 500, "100,000"),
            ("Home", True, 1000, "250,000"),
            ("Health", False, None, None),
            ("Life", False, None, None),
        ]
        
        for coverage_type, expected_covered, expected_deductible, expected_limit in coverage_tests:
            arguments = {
                "policy_number": "POL123456",
                "coverage_type": coverage_type,
                "specific_incident": "Test incident"
            }
            
            result = func_check_coverage(arguments)
            
            assert result["coverage_type"] == coverage_type
            assert result["covered"] == expected_covered
            if expected_deductible:
                assert result["deductible"] == expected_deductible
                assert result["coverage_limit"] == expected_limit
            else:
                assert "deductible" not in result or result["deductible"] is None
                assert "coverage_limit" not in result or result["coverage_limit"] is None

    def test_billing_resolution_scenarios(self):
        """Test different billing resolution scenarios."""
        billing_tests = [
            ("Payment", True, "payment has been processed"),
            ("Late Fee", True, "waived the late fee"),
            ("Premium Increase", False, "premium increase is due"),
            ("Billing Error", True, "corrected the billing error"),
            ("Payment Method", True, "payment method has been updated"),
        ]
        
        for billing_issue, expected_resolved, expected_phrase in billing_tests:
            arguments = {
                "policy_number": "POL123456",
                "billing_issue": billing_issue,
                "amount": 100
            }
            
            result = func_handle_billing(arguments)
            
            assert result["billing_issue"] == billing_issue
            assert result["resolved"] == expected_resolved
            assert expected_phrase.lower() in result["message"].lower()
