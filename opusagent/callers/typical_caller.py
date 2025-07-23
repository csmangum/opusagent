from dataclasses import dataclass
from typing import Dict, Any

from opusagent.caller_agent import (
    CallerPersonality,
    CallerGoal,
    CallerScenario,
    PersonalityType,
    ScenarioType,
    SessionConfig,
    get_caller_tools,
    register_caller_functions,
    func_hang_up,
)

# ==============================
# Typical Caller Configuration
# ==============================

personality = CallerPersonality(
    type=PersonalityType.NORMAL,
    traits=[
        "cooperative",
        "patient",
        "provides information willingly",
        "polite and respectful",
        "clear communicator",
    ],
    communication_style="Friendly and cooperative",
    patience_level=8,
    tech_comfort=7,
    tendency_to_interrupt=0.2,
    provides_clear_info=0.9,
)

goal = CallerGoal(
    primary_goal="Get my lost debit card replaced",
    secondary_goals=[
        "Confirm delivery timeline",
        "Verify security measures",
        "Ensure no unauthorized charges"
    ],
    success_criteria=[
        "card replacement confirmed",
        "delivery address confirmed",
        "security concerns addressed"
    ],
    failure_conditions=[
        "transferred to human",
        "call terminated",
        "unable to verify identity"
    ],
    max_conversation_turns=15,
)

scenario = CallerScenario(
    scenario_type=ScenarioType.CARD_REPLACEMENT,
    goal=goal,
    context={
        "card_type": "debit card",
        "reason": "lost",
        "cooperative": True,
        "concerned_about_security": True,
        "has_account_info": True,
    },
)

SYSTEM_PROMPT = f"""
{personality.get_system_prompt()}

{scenario.get_scenario_prompt()}

IMPORTANT: You are the CALLER, not the agent. You're calling the bank for help.
Respond as a customer would, not as a customer service representative.
Keep responses natural and conversational.

CONVERSATION FLOW:
- WAIT for the customer service agent to greet you first
- When they ask how they can help, explain your problem clearly: "Hi, I lost my debit card and need to get it replaced"
- Provide your account information when asked (name, account number, etc.)
- Answer their security questions honestly
- Ask about delivery timeline and security measures
- Continue until you have a complete solution

TYPICAL CALLER BEHAVIOR:
- Start with: "Hi, I lost my debit card and need to get it replaced"
- Be cooperative and provide information when asked
- Ask reasonable follow-up questions about delivery and security
- Show concern about unauthorized charges
- Thank the agent when the process is complete

Remember: The agent will speak first to greet you. Then you explain that you need to get your lost debit card replaced. Be persistent but polite in getting this done.
"""

# ==============================
# Session Config
# ==============================

TOOLS = get_caller_tools()

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

def get_typical_caller_config() -> SessionConfig:
    """Get the typical caller session configuration."""
    return session_config

def register_typical_caller_functions(function_handler) -> None:
    """Register typical caller functions with the function handler."""
    register_caller_functions(function_handler) 