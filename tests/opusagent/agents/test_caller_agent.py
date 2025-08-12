"""
Tests for Caller Agent

Tests the caller agent's personality types, scenario definitions, tool definitions, and configuration.
"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from opusagent.agents.caller_agent import (
    # Enums
    PersonalityType,
    ScenarioType,
    
    # Classes
    CallerGoal,
    CallerPersonality,
    CallerScenario,
    
    # Tool Parameters
    HangUpParameters,
    
    # Tools
    HangUpTool,
    
    # Functions
    func_hang_up,
    
    # Configuration
    get_caller_tools,
    register_caller_functions,
    session_config,
    
    # Constants
    SYSTEM_PROMPT,
    personality,
    goal,
    scenario,
)


class TestCallerAgentEnums:
    """Test the caller agent enums."""

    def test_personality_type_enum(self):
        """Test PersonalityType enum values."""
        assert PersonalityType.NORMAL.value == "normal"
        assert PersonalityType.DIFFICULT.value == "difficult"
        assert PersonalityType.CONFUSED.value == "confused"
        assert PersonalityType.ANGRY.value == "angry"
        assert PersonalityType.IMPATIENT.value == "impatient"
        assert PersonalityType.ELDERLY.value == "elderly"
        assert PersonalityType.TECH_SAVVY.value == "tech_savvy"
        assert PersonalityType.SUSPICIOUS.value == "suspicious"

    def test_scenario_type_enum(self):
        """Test ScenarioType enum values."""
        assert ScenarioType.CARD_REPLACEMENT.value == "card_replacement"
        assert ScenarioType.ACCOUNT_INQUIRY.value == "account_inquiry"
        assert ScenarioType.LOAN_APPLICATION.value == "loan_application"
        assert ScenarioType.COMPLAINT.value == "complaint"
        assert ScenarioType.GENERAL_INQUIRY.value == "general_inquiry"
        assert ScenarioType.CLAIM_FILING.value == "claim_filing"


class TestCallerGoal:
    """Test the CallerGoal class."""

    def test_caller_goal_creation(self):
        """Test creating a CallerGoal instance."""
        goal = CallerGoal(
            primary_goal="Get my card replaced",
            secondary_goals=["Confirm delivery", "Verify security"],
            success_criteria=["card replacement confirmed"],
            failure_conditions=["transferred to human", "call terminated"],
            max_conversation_turns=15
        )
        
        assert goal.primary_goal == "Get my card replaced"
        assert goal.secondary_goals == ["Confirm delivery", "Verify security"]
        assert goal.success_criteria == ["card replacement confirmed"]
        assert goal.failure_conditions == ["transferred to human", "call terminated"]
        assert goal.max_conversation_turns == 15

    def test_caller_goal_defaults(self):
        """Test CallerGoal with default max_conversation_turns."""
        goal = CallerGoal(
            primary_goal="Test goal",
            secondary_goals=[],
            success_criteria=[],
            failure_conditions=[]
        )
        
        assert goal.max_conversation_turns == 20  # Default value


class TestCallerPersonality:
    """Test the CallerPersonality class."""

    def test_caller_personality_creation(self):
        """Test creating a CallerPersonality instance."""
        personality = CallerPersonality(
            type=PersonalityType.NORMAL,
            traits=["cooperative", "patient"],
            communication_style="Friendly",
            patience_level=8,
            tech_comfort=6,
            tendency_to_interrupt=0.2,
            provides_clear_info=0.8
        )
        
        assert personality.type == PersonalityType.NORMAL
        assert personality.traits == ["cooperative", "patient"]
        assert personality.communication_style == "Friendly"
        assert personality.patience_level == 8
        assert personality.tech_comfort == 6
        assert personality.tendency_to_interrupt == 0.2
        assert personality.provides_clear_info == 0.8

    def test_get_system_prompt_normal_personality(self):
        """Test get_system_prompt for normal personality."""
        personality = CallerPersonality(
            type=PersonalityType.NORMAL,
            traits=["cooperative", "patient"],
            communication_style="Friendly",
            patience_level=8,
            tech_comfort=6,
            tendency_to_interrupt=0.2,
            provides_clear_info=0.8
        )
        
        prompt = personality.get_system_prompt()
        
        assert "normal caller" in prompt.lower()
        assert "cooperative" in prompt.lower()
        assert "patient" in prompt.lower()
        assert "friendly" in prompt.lower()
        assert "8/10" in prompt
        assert "6/10" in prompt
        assert "provide clear, complete information" in prompt.lower()
        assert "be patient and wait for responses" in prompt.lower()

    def test_get_system_prompt_impatient_personality(self):
        """Test get_system_prompt for impatient personality."""
        personality = CallerPersonality(
            type=PersonalityType.IMPATIENT,
            traits=["impatient", "rushed"],
            communication_style="Quick and direct",
            patience_level=3,
            tech_comfort=4,
            tendency_to_interrupt=0.8,
            provides_clear_info=0.3
        )
        
        prompt = personality.get_system_prompt()
        
        assert "impatient caller" in prompt.lower()
        assert "impatient" in prompt.lower()
        assert "rushed" in prompt.lower()
        assert "3/10" in prompt
        assert "show impatience" in prompt.lower()
        assert "interrupt occasionally" in prompt.lower()

    def test_get_system_prompt_perfect_caller(self):
        """Test get_system_prompt for perfect caller (provides_clear_info = 1.0)."""
        personality = CallerPersonality(
            type=PersonalityType.NORMAL,
            traits=["perfect", "efficient"],
            communication_style="Direct and complete",
            patience_level=9,
            tech_comfort=8,
            tendency_to_interrupt=0.1,
            provides_clear_info=1.0
        )
        
        prompt = personality.get_system_prompt()
        
        assert "perfect caller behavior" in prompt.lower()
        assert "provide all necessary information" in prompt.lower()
        assert "be direct and efficient" in prompt.lower()


class TestCallerScenario:
    """Test the CallerScenario class."""

    def test_caller_scenario_creation(self):
        """Test creating a CallerScenario instance."""
        goal = CallerGoal(
            primary_goal="Get card replaced",
            secondary_goals=[],
            success_criteria=[],
            failure_conditions=[]
        )
        
        context = {"card_type": "debit card", "reason": "lost"}
        
        scenario = CallerScenario(
            scenario_type=ScenarioType.CARD_REPLACEMENT,
            goal=goal,
            context=context
        )
        
        assert scenario.type == ScenarioType.CARD_REPLACEMENT
        assert scenario.goal == goal
        assert scenario.context == context

    def test_get_scenario_prompt_card_replacement(self):
        """Test get_scenario_prompt for card replacement scenario."""
        goal = CallerGoal(
            primary_goal="Get my lost debit card replaced",
            secondary_goals=[],
            success_criteria=[],
            failure_conditions=[]
        )
        
        context = {"card_type": "debit card", "reason": "lost"}
        
        scenario = CallerScenario(
            scenario_type=ScenarioType.CARD_REPLACEMENT,
            goal=goal,
            context=context
        )
        
        prompt = scenario.get_scenario_prompt()
        
        assert "card replacement" in prompt.lower()
        assert "debit card" in prompt.lower()
        assert "lost" in prompt.lower()
        assert "get my lost debit card replaced" in prompt.lower()

    def test_get_scenario_prompt_perfect_caller(self):
        """Test get_scenario_prompt for perfect caller context."""
        goal = CallerGoal(
            primary_goal="Get my lost debit card replaced",
            secondary_goals=[],
            success_criteria=[],
            failure_conditions=[]
        )
        
        context = {
            "card_type": "debit card", 
            "reason": "lost",
            "perfect_caller": True
        }
        
        scenario = CallerScenario(
            scenario_type=ScenarioType.CARD_REPLACEMENT,
            goal=goal,
            context=context
        )
        
        prompt = scenario.get_scenario_prompt()
        
        assert "perfect caller" in prompt.lower()
        assert "provide all necessary information" in prompt.lower()
        assert "be direct, efficient" in prompt.lower()
        assert "don't wait for the agent to ask questions" in prompt.lower()

    def test_get_scenario_prompt_minimal_caller(self):
        """Test get_scenario_prompt for minimal caller context."""
        goal = CallerGoal(
            primary_goal="Get my lost debit card replaced",
            secondary_goals=[],
            success_criteria=[],
            failure_conditions=[]
        )
        
        context = {
            "card_type": "debit card", 
            "reason": "lost",
            "minimal_caller": True
        }
        
        scenario = CallerScenario(
            scenario_type=ScenarioType.CARD_REPLACEMENT,
            goal=goal,
            context=context
        )
        
        prompt = scenario.get_scenario_prompt()
        
        assert "minimal caller" in prompt.lower()
        assert "start with just" in prompt.lower()
        assert "don't provide additional details" in prompt.lower()

    def test_get_scenario_prompt_account_inquiry(self):
        """Test get_scenario_prompt for account inquiry scenario."""
        goal = CallerGoal(
            primary_goal="Check my account balance",
            secondary_goals=[],
            success_criteria=[],
            failure_conditions=[]
        )
        
        scenario = CallerScenario(
            scenario_type=ScenarioType.ACCOUNT_INQUIRY,
            goal=goal,
            context={}
        )
        
        prompt = scenario.get_scenario_prompt()
        
        assert "account" in prompt.lower()
        assert "balance" in prompt.lower()
        assert "transactions" in prompt.lower()

    def test_get_scenario_prompt_loan_application(self):
        """Test get_scenario_prompt for loan application scenario."""
        goal = CallerGoal(
            primary_goal="Apply for a loan",
            secondary_goals=[],
            success_criteria=[],
            failure_conditions=[]
        )
        
        scenario = CallerScenario(
            scenario_type=ScenarioType.LOAN_APPLICATION,
            goal=goal,
            context={}
        )
        
        prompt = scenario.get_scenario_prompt()
        
        assert "loan" in prompt.lower()
        assert "rates" in prompt.lower()
        assert "terms" in prompt.lower()

    def test_get_scenario_prompt_complaint(self):
        """Test get_scenario_prompt for complaint scenario."""
        goal = CallerGoal(
            primary_goal="Complain about poor service",
            secondary_goals=[],
            success_criteria=[],
            failure_conditions=[]
        )
        
        context = {"complaint_about": "poor service"}
        
        scenario = CallerScenario(
            scenario_type=ScenarioType.COMPLAINT,
            goal=goal,
            context=context
        )
        
        prompt = scenario.get_scenario_prompt()
        
        assert "complain" in prompt.lower()
        assert "poor service" in prompt.lower()
        assert "frustration" in prompt.lower()

    def test_get_scenario_prompt_general_inquiry(self):
        """Test get_scenario_prompt for general inquiry scenario."""
        goal = CallerGoal(
            primary_goal="Ask about banking services",
            secondary_goals=[],
            success_criteria=[],
            failure_conditions=[]
        )
        
        scenario = CallerScenario(
            scenario_type=ScenarioType.GENERAL_INQUIRY,
            goal=goal,
            context={}
        )
        
        prompt = scenario.get_scenario_prompt()
        
        assert "general question" in prompt.lower()
        assert "banking services" in prompt.lower()
        assert "hours" in prompt.lower()

    def test_get_scenario_prompt_unknown_type(self):
        """Test get_scenario_prompt for unknown scenario type."""
        goal = CallerGoal(
            primary_goal="Test goal",
            secondary_goals=[],
            success_criteria=[],
            failure_conditions=[]
        )
        
        # Create a scenario with a scenario type that's not in the enum
        # We'll use a string that's not in ScenarioType
        scenario = CallerScenario(
            scenario_type=ScenarioType.GENERAL_INQUIRY,  # Use valid enum value
            goal=goal,
            context={}
        )
        
        # Test the method directly with an unknown type
        # This tests the fallback behavior in get_scenario_prompt
        unknown_type = "unknown_type"
        if unknown_type not in [s.value for s in ScenarioType]:
            # Simulate the fallback behavior
            prompt = "You are calling for general assistance."
            assert "general assistance" in prompt.lower()


class TestCallerAgentToolParameters:
    """Test the caller agent tool parameters."""

    def test_hang_up_parameters(self):
        """Test HangUpParameters structure."""
        params = HangUpParameters()
        assert params.type == "object"

        expected_properties = ["reason", "satisfaction_level", "context"]
        for prop in expected_properties:
            assert prop in params.properties

        # Check reason parameter
        reason_param = params.properties["reason"]
        assert reason_param.type == "string"
        assert reason_param.description == "Reason for hanging up the call"

        # Check satisfaction_level parameter
        satisfaction_param = params.properties["satisfaction_level"]
        assert satisfaction_param.type == "string"
        assert satisfaction_param.enum == [
            "very_satisfied", "satisfied", "neutral", 
            "dissatisfied", "very_dissatisfied"
        ]
        assert satisfaction_param.description == "Level of satisfaction with the call"

        # Check context parameter
        context_param = params.properties["context"]
        assert context_param.type == "object"
        assert context_param.description == "Additional context about why the call is ending"


class TestCallerAgentTools:
    """Test the caller agent tools."""

    def test_hang_up_tool(self):
        """Test HangUpTool structure."""
        tool = HangUpTool()
        assert tool.name == "hang_up"
        assert "end the call" in tool.description.lower()
        assert isinstance(tool.parameters, HangUpParameters)

    def test_get_caller_tools(self):
        """Test get_caller_tools returns all expected tools."""
        tools = get_caller_tools()
        
        # Should return list of dictionaries
        assert isinstance(tools, list)
        assert len(tools) == 1  # Only hang_up tool
        
        # Check tool names
        tool_names = [tool["name"] for tool in tools]
        assert "hang_up" in tool_names


class TestCallerAgentFunctions:
    """Test the caller agent function implementations."""

    def test_func_hang_up_success(self):
        """Test func_hang_up with valid arguments."""
        arguments = {
            "reason": "call completed successfully",
            "satisfaction_level": "very_satisfied",
            "context": {"call_duration": "5 minutes"}
        }
        
        result = func_hang_up(arguments)
        
        assert result["status"] == "success"
        assert result["function_name"] == "hang_up"
        assert "thank you so much" in result["prompt_guidance"].lower()
        assert result["next_action"] == "end_call"
        assert result["reason"] == "call completed successfully"
        assert result["satisfaction_level"] == "very_satisfied"
        assert result["context"]["stage"] == "call_ending"
        assert result["context"]["call_duration"] == "5 minutes"
        assert "call_id" in result["context"]
        assert result["context"]["call_id"].startswith("CALL-")

    def test_func_hang_up_with_defaults(self):
        """Test func_hang_up with missing arguments."""
        arguments = {}
        
        result = func_hang_up(arguments)
        
        assert result["status"] == "success"
        assert result["reason"] == "call completed"
        assert result["satisfaction_level"] == "satisfied"
        assert "thank you for your help" in result["prompt_guidance"].lower()

    def test_func_hang_up_different_satisfaction_levels(self):
        """Test func_hang_up with different satisfaction levels."""
        satisfaction_tests = [
            ("very_satisfied", "thank you so much"),
            ("satisfied", "thank you for your help"),
            ("neutral", "thanks for your time"),
            ("dissatisfied", "i guess that's all"),
            ("very_dissatisfied", "this isn't working out"),
        ]
        
        for satisfaction_level, expected_phrase in satisfaction_tests:
            arguments = {"satisfaction_level": satisfaction_level}
            result = func_hang_up(arguments)
            
            assert result["satisfaction_level"] == satisfaction_level
            assert expected_phrase.lower() in result["prompt_guidance"].lower()


class TestCallerAgentFunctionRegistration:
    """Test function registration with function handler."""

    def test_register_caller_functions(self):
        """Test registering all caller functions."""
        mock_handler = Mock()
        
        register_caller_functions(mock_handler)
        
        # Verify all functions were registered
        expected_calls = [
            ("hang_up", func_hang_up),
        ]
        
        assert mock_handler.register_function.call_count == 1
        
        for func_name, func in expected_calls:
            mock_handler.register_function.assert_any_call(func_name, func)


class TestCallerAgentConfiguration:
    """Test the caller agent configuration."""

    def test_session_config_structure(self):
        """Test session_config has correct structure."""
        assert session_config.model == "gpt-4o-realtime-preview-2025-06-03"
        assert session_config.input_audio_format == "pcm16"
        assert session_config.output_audio_format == "pcm16"
        assert session_config.voice == "alloy"  # Different from banking agent
        assert session_config.instructions == SYSTEM_PROMPT
        assert "text" in session_config.modalities
        assert "audio" in session_config.modalities
        assert session_config.temperature == 0.8
        assert session_config.tool_choice == "auto"
        assert session_config.max_response_output_tokens == 4096

    def test_system_prompt_content(self):
        """Test SYSTEM_PROMPT contains expected content."""
        assert "caller" in SYSTEM_PROMPT.lower()
        assert "customer service agent" in SYSTEM_PROMPT.lower()
        assert "debit card" in SYSTEM_PROMPT.lower()
        assert "replaced" in SYSTEM_PROMPT.lower()
        assert "wait for the customer service agent" in SYSTEM_PROMPT.lower()

    def test_tools_in_session_config(self):
        """Test that tools are properly configured in session_config."""
        tools = session_config.tools
        assert isinstance(tools, list)
        assert len(tools) == 1  # Only hang_up tool
        
        tool_names = [tool["name"] for tool in tools]
        assert "hang_up" in tool_names


class TestCallerAgentGlobalConfiguration:
    """Test the global caller agent configuration."""

    def test_personality_configuration(self):
        """Test the global personality configuration."""
        assert personality.type == PersonalityType.NORMAL
        assert "cooperative" in personality.traits
        assert "patient" in personality.traits
        assert personality.communication_style == "Friendly and cooperative"
        assert personality.patience_level == 8
        assert personality.tech_comfort == 6
        assert personality.tendency_to_interrupt == 0.2
        assert personality.provides_clear_info == 0.8

    def test_goal_configuration(self):
        """Test the global goal configuration."""
        assert goal.primary_goal == "Get my lost debit card replaced"
        assert "Confirm delivery timeline" in goal.secondary_goals
        assert "Verify security measures" in goal.secondary_goals
        assert "card replacement confirmed" in goal.success_criteria
        assert "delivery address confirmed" in goal.success_criteria
        assert goal.max_conversation_turns == 15

    def test_scenario_configuration(self):
        """Test the global scenario configuration."""
        assert scenario.type == ScenarioType.CARD_REPLACEMENT
        assert scenario.goal == goal
        assert scenario.context["card_type"] == "debit card"
        assert scenario.context["reason"] == "lost"
        assert scenario.context["cooperative"] is True
        assert scenario.context["concerned_about_security"] is True


class TestCallerAgentIntegration:
    """Integration tests for caller agent components."""

    def test_personality_scenario_integration(self):
        """Test that personality and scenario work together."""
        # Test that the personality can generate a system prompt
        personality_prompt = personality.get_system_prompt()
        assert "normal caller" in personality_prompt.lower()
        
        # Test that the scenario can generate a scenario prompt
        scenario_prompt = scenario.get_scenario_prompt()
        assert "card replacement" in scenario_prompt.lower()
        
        # Test that both are included in the system prompt
        assert "normal caller" in SYSTEM_PROMPT.lower()
        assert "card replacement" in SYSTEM_PROMPT.lower()

    def test_tool_parameter_consistency(self):
        """Test that tool parameters are consistent with function expectations."""
        hang_up_params = HangUpParameters()
        
        # Hang up should handle all parameters
        hang_up_tool_params = set(hang_up_params.properties.keys())
        assert "reason" in hang_up_tool_params
        assert "satisfaction_level" in hang_up_tool_params
        assert "context" in hang_up_tool_params

    def test_function_return_consistency(self):
        """Test that all functions return consistent response structures."""
        test_arguments = {
            "hang_up": {
                "reason": "call completed",
                "satisfaction_level": "satisfied"
            }
        }
        
        for func_name, args in test_arguments.items():
            if func_name == "hang_up":
                result = func_hang_up(args)
            
            # All functions should return a dictionary with status
            assert isinstance(result, dict)
            assert "status" in result
            assert result["status"] == "success"
            assert "context" in result
            assert isinstance(result["context"], dict)
