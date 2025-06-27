from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List
import logging
import uuid

from opusagent.config.constants import VOICE

# Use a different voice for the caller agent to distinguish from CS agent
CALLER_VOICE = "alloy"  # CS agent uses "verse", caller uses "alloy"
from opusagent.config.logging_config import configure_logging
from opusagent.models.openai_api import SessionConfig
from opusagent.models.tool_models import (
    OpenAITool,
    ToolParameter,
    ToolParameters,
)

logger = configure_logging("caller_agent")


class PersonalityType(Enum):
    """Different caller personality types."""

    NORMAL = "normal"
    DIFFICULT = "difficult"
    CONFUSED = "confused"
    ANGRY = "angry"
    IMPATIENT = "impatient"
    ELDERLY = "elderly"
    TECH_SAVVY = "tech_savvy"
    SUSPICIOUS = "suspicious"


class ScenarioType(Enum):
    """Different call scenarios."""

    CARD_REPLACEMENT = "card_replacement"
    ACCOUNT_INQUIRY = "account_inquiry"
    LOAN_APPLICATION = "loan_application"
    COMPLAINT = "complaint"
    GENERAL_INQUIRY = "general_inquiry"


@dataclass
class CallerGoal:
    """Defines what the caller wants to achieve."""

    primary_goal: str
    secondary_goals: List[str]
    success_criteria: List[str]
    failure_conditions: List[str]
    max_conversation_turns: int = 20


@dataclass
class CallerPersonality:
    """Defines how the caller behaves."""

    type: PersonalityType
    traits: List[str]
    communication_style: str
    patience_level: int  # 1-10, 1 being very impatient
    tech_comfort: int  # 1-10, 1 being very uncomfortable with tech
    tendency_to_interrupt: float  # 0.0-1.0
    provides_clear_info: float  # 0.0-1.0

    def get_system_prompt(self) -> str:
        """Generate system prompt for this personality."""
        base_prompt = f"""You are a {self.type.value} caller with the following traits: {', '.join(self.traits)}.

Communication style: {self.communication_style}
Patience level: {self.patience_level}/10
Tech comfort: {self.tech_comfort}/10

IMPORTANT BEHAVIOR GUIDELINES:
- Stay in character at all times
- Be realistic and human-like in your responses
- {"Provide clear, complete information" if self.provides_clear_info > 0.7 else "Sometimes be vague or provide incomplete information"}
- {"Be patient and wait for responses" if self.patience_level > 7 else "Show impatience if calls take too long"}
- {"Interrupt occasionally if you're eager" if self.tendency_to_interrupt > 0.5 else "Wait politely for responses"}

{"PERFECT CALLER BEHAVIOR: Provide ALL necessary information in your FIRST message. Be direct and efficient. Don't wait for the agent to ask questions." if self.provides_clear_info >= 1.0 else ""}

Respond naturally as a human caller would. Keep responses concise and conversational.
"""
        return base_prompt


class CallerScenario:
    """Defines the specific scenario the caller is trying to accomplish."""

    def __init__(
        self, scenario_type: ScenarioType, goal: CallerGoal, context: Dict[str, Any]
    ):
        self.type = scenario_type
        self.goal = goal
        self.context = context

    def get_scenario_prompt(self) -> str:
        """Generate scenario-specific prompt."""
        prompts = {
            ScenarioType.CARD_REPLACEMENT: self._card_replacement_prompt(),
            ScenarioType.ACCOUNT_INQUIRY: self._account_inquiry_prompt(),
            ScenarioType.LOAN_APPLICATION: self._loan_application_prompt(),
            ScenarioType.COMPLAINT: self._complaint_prompt(),
            ScenarioType.GENERAL_INQUIRY: self._general_inquiry_prompt(),
        }
        return prompts.get(self.type, "You are calling for general assistance.")

    def _card_replacement_prompt(self) -> str:
        card_type = self.context.get("card_type", "gold card")
        reason = self.context.get("reason", "lost")

        # Check if this is a perfect caller
        if self.context.get("perfect_caller", False):
            return f"""
SCENARIO: You need to replace your {card_type} because you {reason} it.

GOAL: {self.goal.primary_goal}

CONTEXT:
- Card type: {card_type}
- Reason for replacement: {reason}
- You are a PERFECT caller with all information ready

IMPORTANT: In your FIRST message, provide ALL necessary information:
"Hi, I need to replace my lost gold card. Can you send it to the address on file?"

Be direct, efficient, and provide complete information upfront. Don't wait for the agent to ask questions.
"""
        # Check if this is a minimal caller
        elif self.context.get("minimal_caller", False):
            return f"""
SCENARIO: You need a new card but you're not sure about the details.

GOAL: {self.goal.primary_goal}

CONTEXT:
- You are a MINIMAL caller who provides basic information
- You start with just "Hi I need a new card"
- You wait for the agent to ask questions
- You provide information when asked, but don't volunteer details

IMPORTANT: Start your FIRST message with just:
"Hi I need a new card"

Don't provide additional details unless the agent asks. Be cooperative when questioned, but start minimal.
"""
        else:
            return f"""
SCENARIO: You need to replace your {card_type} because you {reason} it.

GOAL: {self.goal.primary_goal}

CONTEXT:
- Card type: {card_type}
- Reason for replacement: {reason}
- Urgency: {"High" if "urgent" in self.context else "Normal"}

SUCCESS: Complete the card replacement process
CHALLENGES: {"Be difficult about providing information" if "difficult" in str(self.context) else "Cooperate but ask many questions"}

Start by explaining why you're calling.
"""

    def _account_inquiry_prompt(self) -> str:
        return f"""
SCENARIO: You're calling to inquire about your account.

GOAL: {self.goal.primary_goal}

Ask about balance, recent transactions, or account status.
"""

    def _loan_application_prompt(self) -> str:
        return f"""
SCENARIO: You're interested in applying for a loan.

GOAL: {self.goal.primary_goal}

Be interested but ask lots of questions about rates, terms, and requirements.
"""

    def _complaint_prompt(self) -> str:
        issue = self.context.get("complaint_about", "poor service")
        return f"""
SCENARIO: You're calling to complain about {issue}.

GOAL: {self.goal.primary_goal}

Express frustration and demand resolution.
"""

    def _general_inquiry_prompt(self) -> str:
        return f"""
SCENARIO: You have a general question about banking services.

GOAL: {self.goal.primary_goal}

Ask about services, hours, or general banking information.
"""

# ---------- Regular caller ----------
personality = CallerPersonality(
    type=PersonalityType.NORMAL,
    traits=[
        "cooperative",
        "patient",
        "provides information willingly",
        "polite and respectful",
    ],
    communication_style="Friendly and cooperative",
    patience_level=8,
    tech_comfort=6,
    tendency_to_interrupt=0.2,
    provides_clear_info=0.8,
)

goal = CallerGoal(
    primary_goal="Get my lost gold card replaced",
    secondary_goals=["Confirm delivery timeline", "Verify security measures"],
    success_criteria=["card replacement confirmed", "delivery address confirmed"],
    failure_conditions=["transferred to human", "call terminated"],
    max_conversation_turns=15,
)

scenario = CallerScenario(
    scenario_type=ScenarioType.CARD_REPLACEMENT,
    goal=goal,
    context={
        "card_type": "gold card",
        "reason": "lost",
        "cooperative": True,
        "concerned_about_security": True,
    },
)



SYSTEM_PROMPT = f"""
{personality.get_system_prompt()}

{scenario.get_scenario_prompt()}

IMPORTANT: You are the CALLER, not the agent. You're calling the bank for help.
Respond as a customer would, not as a customer service representative.
Keep responses natural and conversational. Don't be overly helpful or professional.

CONVERSATION FLOW:
- WAIT for the customer service agent to greet you first
- When they ask how they can help, explain your problem: "I've lost my gold card and need to get it replaced"
- Answer their questions clearly and provide any information they request
- Continue the conversation until your problem is fully resolved
- Ask follow-up questions if you need clarification
- Don't end the call until you have a complete solution

Remember: The agent will speak first to greet you. Then you explain that you need to get your lost gold card replaced. Be persistent but polite in getting this done.
"""

# ==============================
# Tool Parameters
# ==============================

class HangUpParameters(ToolParameters):
    """Parameters for the hang_up function."""

    type: str = "object"
    properties: Dict[str, ToolParameter] = {
        "reason": ToolParameter(
            type="string", 
            description="Reason for hanging up the call"
        ),
        "satisfaction_level": ToolParameter(
            type="string",
            enum=["very_satisfied", "satisfied", "neutral", "dissatisfied", "very_dissatisfied"],
            description="Level of satisfaction with the call"
        ),
        "context": ToolParameter(
            type="object", 
            description="Additional context about why the call is ending"
        ),
    }


# ==============================
# Tools
# ==============================

class HangUpTool(OpenAITool):
    """Tool for hanging up the call."""

    name: str = "hang_up"
    description: str = "End the call when the caller's needs are met or they want to end the conversation."
    parameters: HangUpParameters = HangUpParameters()


def get_caller_tools() -> list[dict[str, Any]]:
    """
    Get all OpenAI tool definitions for the caller agent.

    Returns:
        List of OpenAI function tool schemas as dictionaries
    """
    tools = [
        HangUpTool(),
    ]
    return [tool.model_dump() for tool in tools]


# ==============================
# Function Implementations
# ==============================

def func_hang_up(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle call hang up.

    Args:
        arguments: Function arguments containing hang up details

    Returns:
        Formatted prompt and guidance for ending the call
    """
    reason = arguments.get("reason", "call completed")
    satisfaction_level = arguments.get("satisfaction_level", "satisfied")
    context = arguments.get("context", {})

    # Log the hang up request
    logger.info(f"Call hang up requested. Reason: {reason}, Satisfaction: {satisfaction_level}")

    # Generate a call reference number
    call_id = f"CALL-{uuid.uuid4().hex[:8].upper()}"

    # Format the hang up message based on satisfaction level
    satisfaction_messages = {
        "very_satisfied": "Thank you so much for your help! I really appreciate it.",
        "satisfied": "Thank you for your help today.",
        "neutral": "Thanks for your time.",
        "dissatisfied": "I guess that's all I can do for now.",
        "very_dissatisfied": "This isn't working out. I'll call back later."
    }

    hang_up_message = satisfaction_messages.get(satisfaction_level, "Thank you for your time.")

    return {
        "status": "success",
        "function_name": "hang_up",
        "prompt_guidance": hang_up_message,
        "next_action": "end_call",
        "call_id": call_id,
        "reason": reason,
        "satisfaction_level": satisfaction_level,
        "context": {
            "stage": "call_ending",
            "reason": reason,
            "satisfaction_level": satisfaction_level,
            "call_id": call_id,
            **context,
        },
    }


def register_caller_functions(function_handler) -> None:
    """
    Register all caller functions with the function handler.

    Args:
        function_handler: The FunctionHandler instance to register functions with
    """
    logger.info("Registering caller functions with function handler")

    function_handler.register_function("hang_up", func_hang_up)

    logger.info("Caller functions registered successfully")


# ==============================
# Session Config
# ==============================

TOOLS = get_caller_tools()

session_config = SessionConfig(
    model="gpt-4o-realtime-preview-2025-06-03",
    input_audio_format="pcm16",
    output_audio_format="pcm16",
    voice=CALLER_VOICE,  # Use distinct voice for caller agent
    instructions=SYSTEM_PROMPT,
    modalities=["text", "audio"],
    temperature=0.8,
    tools=TOOLS,
    input_audio_noise_reduction={"type": "near_field"},
    input_audio_transcription={"model": "whisper-1"},
    max_response_output_tokens=4096,
    tool_choice="auto",
)

