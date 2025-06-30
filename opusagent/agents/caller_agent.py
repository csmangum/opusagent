"""
Caller Agent implementation for OpusAgent.

This module provides caller agents with different personalities and scenarios
that implement the BaseAgent interface for testing customer service interactions.
"""

import uuid
from typing import Dict, Any
from .base_agent import BaseAgent
from .agent_registry import register_agent
from opusagent.models.openai_api import SessionConfig
from opusagent.models.tool_models import (
    OpenAITool,
    ToolParameter,
    ToolParameters,
)

# Use a different voice for the caller agent to distinguish from CS agent  
CALLER_VOICE = "alloy"  # CS agent uses "verse", caller uses "alloy"


@register_agent("caller")
class CallerAgent(BaseAgent):
    """Caller Agent with configurable personality and scenario.
    
    This agent simulates different types of callers with various personalities
    and scenarios for testing customer service interactions.
    """

    def __init__(
        self,
        name: str = "Caller Agent",
        role: str = "Customer Caller",
        personality_type: str = "typical",
        scenario_type: str = "general_inquiry",
        voice: str = CALLER_VOICE,
        temperature: float = 0.8,
        max_response_output_tokens: int = 4096,
        **kwargs
    ):
        """Initialize the Caller Agent.
        
        Args:
            name: Agent name
            role: Agent role
            personality_type: Type of caller personality (typical, frustrated, elderly, hurried)
            scenario_type: Type of call scenario (card_replacement, account_inquiry, etc.)
            voice: Voice identifier for OpenAI
            temperature: Response temperature
            max_response_output_tokens: Maximum tokens in response
            **kwargs: Additional configuration
        """
        super().__init__(name, role, **kwargs)
        
        self.personality_type = personality_type
        self.scenario_type = scenario_type
        self.voice = voice
        self.temperature = temperature
        self.max_response_output_tokens = max_response_output_tokens
        
        # Generate instructions based on personality and scenario
        self.instructions = self._generate_instructions()

    def _generate_instructions(self) -> str:
        """Generate instructions based on personality and scenario."""
        personality_instructions = self._get_personality_instructions()
        scenario_instructions = self._get_scenario_instructions()
        
        return f"""
{personality_instructions}

{scenario_instructions}

IMPORTANT: You are the CALLER, not the agent. You're calling the bank for help.
Respond as a customer would, not as a customer service representative.
Keep responses natural and conversational. Don't be overly helpful or professional.

CONVERSATION FLOW:
- WAIT for the customer service agent to greet you first
- When they ask how they can help, explain your problem clearly
- Answer their questions and provide any information they request
- Continue the conversation until your problem is fully resolved
- Ask follow-up questions if you need clarification
- Don't end the call until you have a complete solution

Remember: The agent will speak first to greet you. Then you explain your issue. Be persistent but polite in getting this resolved.
"""

    def _get_personality_instructions(self) -> str:
        """Get personality-specific instructions."""
        personalities = {
            "typical": """
You are a typical, cooperative caller with the following traits: cooperative, patient, provides information willingly, polite and respectful.

Communication style: Friendly and cooperative
Patience level: 8/10
Tech comfort: 6/10

BEHAVIOR GUIDELINES:
- Stay calm and courteous throughout the call
- Provide clear, complete information when asked
- Be patient and wait for responses
- Ask clarifying questions when needed
""",
            "frustrated": """
You are a frustrated, impatient caller with the following traits: impatient, demanding, easily annoyed, interrupts frequently.

Communication style: Direct and demanding
Patience level: 3/10
Tech comfort: 5/10

BEHAVIOR GUIDELINES:
- Show impatience if the call takes too long
- Be direct about what you want
- Express frustration with delays or complications
- Interrupt occasionally if you're eager to move forward
""",
            "elderly": """
You are an elderly caller with the following traits: patient, polite, needs more guidance, lower tech comfort.

Communication style: Polite and courteous but needs help
Patience level: 9/10
Tech comfort: 2/10

BEHAVIOR GUIDELINES:
- Be very polite and respectful
- Ask for clarification on technical terms
- Take time to understand instructions
- Appreciate patience and clear explanations
""",
            "hurried": """
You are a hurried caller with the following traits: in a rush, wants quick service, efficient, may interrupt to speed things up.

Communication style: Quick and to the point
Patience level: 4/10
Tech comfort: 7/10

BEHAVIOR GUIDELINES:
- Emphasize that you're in a hurry
- Want the quickest solution possible
- Provide information quickly and efficiently
- May interrupt to speed up the process
""",
        }
        
        return personalities.get(self.personality_type, personalities["typical"])

    def _get_scenario_instructions(self) -> str:
        """Get scenario-specific instructions."""
        scenarios = {
            "card_replacement": """
SCENARIO: You need to replace your lost gold card.

GOAL: Get your lost gold card replaced

CONTEXT:
- Card type: gold card
- Reason for replacement: lost
- You need the card replaced quickly

Start by explaining: "Hi, I've lost my gold card and need to get it replaced."
""",
            "account_inquiry": """
SCENARIO: You're calling to inquire about your account balance and recent transactions.

GOAL: Get information about your account

CONTEXT:
- You want to check your balance
- You're concerned about some recent charges
- You need account information

Start by explaining: "Hi, I'd like to check my account balance and review some recent transactions."
""",
            "complaint": """
SCENARIO: You're calling to complain about poor service you received.

GOAL: Express your complaint and get resolution

CONTEXT:
- You received poor customer service recently
- You want to file a formal complaint
- You expect some form of compensation

Start by explaining: "Hi, I need to file a complaint about the poor service I received."
""",
            "general_inquiry": """
SCENARIO: You have general questions about banking services.

GOAL: Get information about services and offerings

CONTEXT:
- You're interested in learning about services
- You may have questions about fees or policies
- You're considering new products

Start by explaining: "Hi, I have some questions about your banking services."
""",
        }
        
        return scenarios.get(self.scenario_type, scenarios["general_inquiry"])

    @property
    def agent_type(self) -> str:
        """Return the agent type identifier."""
        return "caller"

    def get_session_config(self) -> SessionConfig:
        """Return the OpenAI session configuration for this agent."""
        return SessionConfig(
            model="gpt-4o-realtime-preview-2025-06-03",
            input_audio_format="pcm16",
            output_audio_format="pcm16",
            voice=self.voice,
            instructions=self.instructions,
            modalities=["text", "audio"],
            temperature=self.temperature,
            tools=self._get_tools(),
            input_audio_noise_reduction={"type": "near_field"},
            input_audio_transcription={"model": "whisper-1"},
            max_response_output_tokens=self.max_response_output_tokens,
            tool_choice="auto",
        )

    def register_functions(self, function_handler) -> None:
        """Register caller functions with the function handler."""
        function_handler.register_function("hang_up", self._func_hang_up)

    def get_agent_info(self) -> Dict[str, Any]:
        """Return metadata about the agent."""
        return {
            "name": self.name,
            "role": self.role,
            "agent_type": self.agent_type,
            "personality_type": self.personality_type,
            "scenario_type": self.scenario_type,
            "voice": self.voice,
            "temperature": self.temperature,
            "capabilities": [
                "simulated_calling",
                "personality_simulation",
                "scenario_testing"
            ],
            "tools": [tool["function"]["name"] for tool in self._get_tools()],
        }

    def _get_tools(self) -> list[dict[str, Any]]:
        """Get all OpenAI tool definitions for the caller agent."""
        tools = [
            HangUpTool(),
        ]
        return [tool.model_dump() for tool in tools]

    def _func_hang_up(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle call hang up."""
        reason = arguments.get("reason", "call completed")
        satisfaction_level = arguments.get("satisfaction_level", "satisfied")
        context = arguments.get("context", {})

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


# Tool parameter definitions
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


# Tool definitions
class HangUpTool(OpenAITool):
    """Tool for hanging up the call."""

    name: str = "hang_up"
    description: str = "End the call when the caller's needs are met or they want to end the conversation."
    parameters: HangUpParameters = HangUpParameters()