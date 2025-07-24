"""
Insurance Caller Agent

This module provides insurance-specific caller personalities and scenarios
for testing insurance call center flows.
"""

import logging
from typing import Any, Dict

from opusagent.config.logging_config import configure_logging
from opusagent.models.openai_api import SessionConfig
from opusagent.models.tool_models import (
    HumanHandoffTool,
    OpenAITool,
    ToolParameter,
    ToolParameters,
)
from opusagent.callers.constants import FailureConditions

logger = configure_logging("insurance_caller")

# ==============================
# Caller Personality
# ==============================

class InsuranceCallerPersonality:
    """Defines the personality traits for insurance callers."""
    
    def __init__(
        self,
        type: str,
        traits: list[str],
        communication_style: str,
        patience_level: int,
        tech_comfort: int,
        tendency_to_interrupt: float,
        provides_clear_info: float,
    ):
        self.type = type
        self.traits = traits
        self.communication_style = communication_style
        self.patience_level = patience_level
        self.tech_comfort = tech_comfort
        self.tendency_to_interrupt = tendency_to_interrupt
        self.provides_clear_info = provides_clear_info
    
    def get_system_prompt(self) -> str:
        """Generate system prompt based on personality traits."""
        return f"""
You are a customer calling an insurance company. Your personality type is: {self.type}

Personality Traits:
- {', '.join(self.traits)}
- Communication Style: {self.communication_style}
- Patience Level: {self.patience_level}/10
- Tech Comfort: {self.tech_comfort}/10
- Tendency to Interrupt: {self.tendency_to_interrupt}
- Provides Clear Info: {self.provides_clear_info}

Remember: You are the CALLER, not the agent. You're calling the insurance company for help.
Respond as a customer would, not as a customer service representative.
Keep responses natural and conversational.
"""


class InsuranceCallerGoal:
    """Defines the caller's goals and success criteria."""
    
    def __init__(
        self,
        primary_goal: str,
        secondary_goals: list[str],
        success_criteria: list[str],
        failure_conditions: list[str],
        max_conversation_turns: int,
    ):
        self.primary_goal = primary_goal
        self.secondary_goals = secondary_goals
        self.success_criteria = success_criteria
        self.failure_conditions = failure_conditions
        self.max_conversation_turns = max_conversation_turns
    
    def get_goal_prompt(self) -> str:
        """Generate goal prompt."""
        return f"""
Your Goals:
- Primary: {self.primary_goal}
- Secondary: {', '.join(self.secondary_goals)}

Success Criteria:
- {', '.join(self.success_criteria)}

Failure Conditions:
- {', '.join(self.failure_conditions)}

Maximum conversation turns: {self.max_conversation_turns}
"""


class InsuranceCallerScenario:
    """Defines the insurance scenario context."""
    
    def __init__(
        self,
        scenario_type: str,
        goal: InsuranceCallerGoal,
        context: dict[str, Any],
    ):
        self.scenario_type = scenario_type
        self.goal = goal
        self.context = context
    
    def get_scenario_prompt(self) -> str:
        """Generate scenario prompt."""
        context_str = "\n".join([f"- {k}: {v}" for k, v in self.context.items()])
        return f"""
Insurance Scenario: {self.scenario_type}

Context:
{context_str}

{self.goal.get_goal_prompt()}
"""


# ==============================
# Insurance Caller Types
# ==============================

# ---------- Typical insurance caller ----------
personality = InsuranceCallerPersonality(
    type="Typical Insurance Customer",
    traits=[
        "cooperative",
        "patient",
        "provides information willingly",
        "polite and respectful",
        "concerned about coverage",
    ],
    communication_style="Friendly and cooperative",
    patience_level=8,
    tech_comfort=6,
    tendency_to_interrupt=0.2,
    provides_clear_info=0.8,
)

goal = InsuranceCallerGoal(
    primary_goal="File a claim for my car accident",
    secondary_goals=["Understand the claims process", "Get timeline for resolution"],
    success_criteria=["claim filed successfully", "claim number received", "next steps explained"],
    failure_conditions=[
        FailureConditions.TRANSFERRED_TO_HUMAN.value,
        FailureConditions.CALL_TERMINATED.value,
    ],
    max_conversation_turns=15,
)

scenario = InsuranceCallerScenario(
    scenario_type="AUTO_CLAIM",
    goal=goal,
    context={
        "policy_type": "auto insurance",
        "incident_type": "car accident",
        "cooperative": True,
        "concerned_about_coverage": True,
        "has_policy_number": True,
    },
)

SYSTEM_PROMPT = f"""
{personality.get_system_prompt()}

{scenario.get_scenario_prompt()}

IMPORTANT: You are the CALLER, not the agent. You're calling the insurance company for help.
Respond as a customer would, not as a customer service representative.
Keep responses natural and conversational. Don't be overly helpful or professional.

CONVERSATION FLOW:
- WAIT for the customer service agent to greet you first
- When they ask how they can help, explain your problem: "Hi, I was in a car accident yesterday and need to file a claim"
- Answer their questions clearly and provide any information they request
- Continue the conversation until your problem is fully resolved
- Ask follow-up questions if you need clarification
- Don't end the call until you have a complete solution

Remember: The agent will speak first to greet you. Then you explain that you need to file a claim for your car accident. Be persistent but polite in getting this done.
"""

# ==============================
# Tools for Insurance Caller
# ==============================

class InsuranceCallerParameters(ToolParameters):
    """Parameters for insurance caller tools."""

    type: str = "object"
    properties: Dict[str, ToolParameter] = {
        "policy_number": ToolParameter(
            type="string", description="Customer's policy number"
        ),
        "claim_type": ToolParameter(
            type="string",
            enum=["Auto", "Home", "Health", "Life", "Other"],
            description="Type of insurance claim",
        ),
        "incident_date": ToolParameter(
            type="string", description="Date of the incident (YYYY-MM-DD)"
        ),
        "description": ToolParameter(
            type="string", description="Description of the incident"
        ),
    }


class InsuranceCallerTool(OpenAITool):
    """Tool for insurance caller interactions."""

    name: str = "provide_insurance_info"
    description: str = "Provide insurance-related information to the agent."
    parameters: InsuranceCallerParameters = InsuranceCallerParameters()


def get_insurance_caller_tools() -> list[dict[str, Any]]:
    """
    Get all OpenAI tool definitions for insurance callers.

    Returns:
        List of OpenAI function tool schemas as dictionaries
    """
    tools = [
        InsuranceCallerTool(),
        HumanHandoffTool(),
    ]
    return [tool.model_dump() for tool in tools]


# ==============================
# Session Config
# ==============================

TOOLS = get_insurance_caller_tools()

session_config = SessionConfig(
    model="gpt-4o-realtime-preview-2025-06-03",
    input_audio_format="pcm16",
    output_audio_format="pcm16",
    voice="alloy",  # Use distinct voice for caller agent
    instructions=SYSTEM_PROMPT,
    modalities=["text", "audio"],
    temperature=0.7,
    tools=TOOLS,
    input_audio_noise_reduction={"type": "near_field"},
    input_audio_transcription={"model": "whisper-1"},
    max_response_output_tokens=4096,
    tool_choice="auto",
)

# ==============================
# Export Functions
# ==============================

def get_insurance_caller_config() -> SessionConfig:
    """Get the insurance caller session configuration."""
    return session_config


def get_insurance_caller_personality() -> InsuranceCallerPersonality:
    """Get the insurance caller personality."""
    return personality


def get_insurance_caller_scenario() -> InsuranceCallerScenario:
    """Get the insurance caller scenario."""
    return scenario 