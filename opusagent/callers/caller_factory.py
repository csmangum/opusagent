from typing import Any, Callable, Dict

from opusagent.agents.caller_agent import (
    CallerGoal,
    CallerPersonality,
    CallerScenario,
    PersonalityType,
    ScenarioType,
)
from opusagent.models.openai_api import SessionConfig

from .constants import FailureConditions

# Import insurance caller tools
from .insurance_caller import get_insurance_caller_tools


class CallerType:
    """Enumeration of available caller types."""

    TYPICAL = "typical"
    FRUSTRATED = "frustrated"
    ELDERLY = "elderly"
    HURRIED = "hurried"


# Configuration keys that are not part of CallerPersonality fields
# These keys are used for SessionConfig but should be excluded when creating CallerPersonality objects
CONFIG_KEYS = {"behavior_prompt", "temperature", "voice"}

# Type hint for tools functions
ToolsFunction = Callable[[], list[dict[str, Any]]]


# Tool functions that can be reused across scenarios
def get_caller_tools() -> list[dict[str, Any]]:
    """Get basic caller tools (hang_up)."""
    from opusagent.models.tool_models import HumanHandoffTool

    tools = [HumanHandoffTool()]
    return [tool.model_dump() for tool in tools]


def func_hang_up(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Basic hang up function for simulations."""
    return {"status": "success", "action": "hang_up", "message": "Call ended"}


def func_provide_insurance_info(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Provide insurance information function for simulations."""
    return {
        "status": "success",
        "info_provided": arguments,
        "next_action": "continue",
    }


# ==============================
# PERSONALITIES - Decoupled from scenarios
# ==============================

PERSONALITIES = {
    CallerType.TYPICAL: {
        "type": PersonalityType.NORMAL,
        "traits": [
            "cooperative",
            "patient",
            "provides information willingly",
            "polite and respectful",
            "clear communicator",
        ],
        "communication_style": "Friendly and cooperative",
        "patience_level": 8,
        "tech_comfort": 7,
        "tendency_to_interrupt": 0.2,
        "provides_clear_info": 0.9,
        "behavior_prompt": """
TYPICAL CALLER BEHAVIOR:
- Be cooperative and provide information when asked
- Ask reasonable follow-up questions
- Show concern appropriately
- Thank the agent when the process is complete
""",
        "temperature": 0.7,
        "voice": "alloy",
    },
    CallerType.FRUSTRATED: {
        "type": PersonalityType.ANGRY,
        "traits": [
            "impatient",
            "easily frustrated",
            "skeptical of automated systems",
            "demanding",
            "interrupts frequently",
            "complains about wait times",
        ],
        "communication_style": "Direct and demanding",
        "patience_level": 3,
        "tech_comfort": 4,
        "tendency_to_interrupt": 0.8,
        "provides_clear_info": 0.6,
        "behavior_prompt": """
FRUSTRATED CALLER BEHAVIOR:
- Show impatience with security questions
- Interrupt with phrases like "I already told you that" or "Can we hurry this up?"
- Complain about the inconvenience
- Threaten to cancel your account if service is slow
""",
        "temperature": 0.9,
        "voice": "alloy",
    },
    CallerType.ELDERLY: {
        "type": PersonalityType.ELDERLY,
        "traits": [
            "patient",
            "polite and respectful",
            "appreciates clear explanations",
            "may need things repeated",
            "concerned about security",
            "prefers human interaction",
            "speaks slowly and clearly",
        ],
        "communication_style": "Polite and patient, may need clarification",
        "patience_level": 9,
        "tech_comfort": 2,
        "tendency_to_interrupt": 0.1,
        "provides_clear_info": 0.7,
        "behavior_prompt": """
ELDERLY CALLER BEHAVIOR:
- Speak slowly and clearly
- Ask for clarification: "Could you explain that again?" or "I'm not sure I understand"
- Express concern about security: "I'm worried about someone using my card"
- Show appreciation for patience: "Thank you for being so patient with me"
- May need to repeat information: "Let me make sure I have that right"
""",
        "temperature": 0.6,
        "voice": "alloy",
    },
    CallerType.HURRIED: {
        "type": PersonalityType.IMPATIENT,
        "traits": [
            "in a hurry",
            "wants quick service",
            "efficient communicator",
            "interrupts to speed things up",
            "focused on getting to the point",
            "appreciates fast solutions",
        ],
        "communication_style": "Quick and to the point",
        "patience_level": 4,
        "tech_comfort": 8,
        "tendency_to_interrupt": 0.6,
        "provides_clear_info": 0.9,
        "behavior_prompt": """
HURRIED CALLER BEHAVIOR:
- Get straight to the point
- Interrupt with phrases like "Can we speed this up?" or "I don't have much time"
- Provide information quickly and efficiently
- Show impatience with unnecessary questions
- End the call quickly once the process is complete
""",
        "temperature": 0.8,
        "voice": "alloy",
    },
}

# ==============================
# SCENARIOS - Decoupled from personalities
# ==============================

SCENARIOS = {
    "banking_card_replacement": {
        "scenario_type": ScenarioType.CARD_REPLACEMENT,
        "goal": {
            "primary_goal": "Get my lost debit card replaced",
            "secondary_goals": [
                "Confirm delivery timeline",
                "Verify security measures",
                "Ensure no unauthorized charges",
            ],
            "success_criteria": [
                "card replacement confirmed",
                "delivery address confirmed",
                "security concerns addressed",
            ],
            "failure_conditions": [
                FailureConditions.TRANSFERRED_TO_HUMAN.value,
                FailureConditions.CALL_TERMINATED.value,
                FailureConditions.UNABLE_TO_VERIFY_IDENTITY.value,
            ],
            "max_conversation_turns": 15,
        },
        "context": {
            "card_type": "debit card",
            "reason": "lost",
            "cooperative": True,
            "concerned_about_security": True,
            "has_account_info": True,
        },
        "base_flow": """
CONVERSATION FLOW:
- WAIT for the customer service agent to greet you first
- When they ask how they can help, explain your problem clearly: "Hi, I lost my debit card and need to get it replaced"
- Provide your account information when asked (name, account number, etc.)
- Answer their security questions honestly
- Ask about delivery timeline and security measures
- Continue until you have a complete solution
""",
        "tools": get_caller_tools,
    },
    "insurance_file_claim": {
        "scenario_type": ScenarioType.CLAIM_FILING,
        "goal": {
            "primary_goal": "File a claim for my car accident",
            "secondary_goals": [
                "Understand the claims process",
                "Get timeline for resolution",
            ],
            "success_criteria": [
                "claim filed successfully",
                "claim number received",
                "next steps explained",
            ],
            "failure_conditions": [
                FailureConditions.TRANSFERRED_TO_HUMAN.value,
                FailureConditions.CALL_TERMINATED.value,
            ],
            "max_conversation_turns": 15,
        },
        "context": {
            "policy_type": "auto insurance",
            "incident_type": "car accident",
            "cooperative": True,
            "concerned_about_coverage": True,
            "has_policy_number": True,
        },
        "base_flow": """
CONVERSATION FLOW:
- WAIT for the customer service agent to greet you first
- When they ask how they can help, explain your problem: "Hi, I was in a car accident yesterday and need to file a claim"
- Answer their questions clearly and provide any information they request
- Continue the conversation until your problem is fully resolved
- Ask follow-up questions if you need clarification
- Don't end the call until you have a complete solution
""",
        "tools": get_insurance_caller_tools,
    },
}

# ==============================
# NEW API - Supports personality + scenario combinations
# ==============================


def get_caller_config(
    caller_type: str, scenario: str = "banking_card_replacement"
) -> SessionConfig:
    """
    Get the session configuration for a specific caller personality and scenario combination.

    Args:
        caller_type: The personality type of caller (typical, frustrated, elderly, hurried)
        scenario: The scenario context (banking_card_replacement, insurance_file_claim, etc.)

    Returns:
        SessionConfig for the specified caller personality and scenario combination

    Raises:
        ValueError: If caller_type or scenario is not recognized
    """
    if caller_type not in PERSONALITIES:
        available_types = ", ".join(PERSONALITIES.keys())
        raise ValueError(
            f"Unknown caller_type: {caller_type}. Available: {available_types}"
        )
    if scenario not in SCENARIOS:
        available_scenarios = ", ".join(SCENARIOS.keys())
        raise ValueError(
            f"Unknown scenario: {scenario}. Available: {available_scenarios}"
        )

    pers_dict = PERSONALITIES[caller_type]
    scen_dict = SCENARIOS[scenario]

    # Build personality object - filter out configuration keys that are not part of CallerPersonality fields
    personality = CallerPersonality(
        **{k: v for k, v in pers_dict.items() if k not in CONFIG_KEYS}
    )

    # Build goal and scenario objects
    goal = CallerGoal(**scen_dict["goal"])
    caller_scenario = CallerScenario(
        scen_dict["scenario_type"], goal, scen_dict["context"]
    )

    # Combine personality and scenario prompts
    system_prompt = f"""
{personality.get_system_prompt()}

{caller_scenario.get_scenario_prompt()}

{scen_dict["base_flow"]}

{pers_dict["behavior_prompt"]}

IMPORTANT: You are the CALLER, not the agent. You're calling for help.
Respond as a customer would, not as a customer service representative.
Keep responses natural and conversational.

Remember: The agent will speak first to greet you. Then explain your issue. Be persistent but follow your personality.
"""

    # Validate that tools is a callable function before calling it
    if "tools" not in scen_dict:
        raise KeyError(f"Scenario '{scenario}' is missing required 'tools' field")

    tools_func: ToolsFunction = scen_dict["tools"]
    if not callable(tools_func):
        raise TypeError(
            f"The 'tools' entry in scenario '{scenario}' is not callable: {type(tools_func)}"
        )

    # Additional type validation for better error messages
    try:
        tools = tools_func()
        if not isinstance(tools, list):
            raise TypeError(
                f"Tools function for scenario '{scenario}' returned {type(tools)}, expected list"
            )
    except Exception as e:
        raise RuntimeError(
            f"Error calling tools function for scenario '{scenario}': {e}"
        )

    return SessionConfig(
        model="gpt-4o-realtime-preview-2025-06-03",
        input_audio_format="pcm16",
        output_audio_format="pcm16",
        voice=pers_dict["voice"],
        instructions=system_prompt,
        modalities=["text", "audio"],
        temperature=pers_dict["temperature"],
        tools=tools,
        input_audio_noise_reduction={"type": "near_field"},
        input_audio_transcription={"model": "whisper-1"},
        max_response_output_tokens=4096,
        tool_choice="auto",
    )


def register_caller_functions(
    caller_type: str, scenario: str, function_handler
) -> None:
    """
    Register functions for a specific caller personality and scenario combination.

    Args:
        caller_type: The personality type of caller
        scenario: The scenario context
        function_handler: The FunctionHandler instance to register functions with

    Raises:
        ValueError: If caller_type or scenario is not recognized
    """
    if caller_type not in PERSONALITIES:
        available_types = ", ".join(PERSONALITIES.keys())
        raise ValueError(
            f"Unknown caller_type: {caller_type}. Available: {available_types}"
        )
    if scenario not in SCENARIOS:
        available_scenarios = ", ".join(SCENARIOS.keys())
        raise ValueError(
            f"Unknown scenario: {scenario}. Available: {available_scenarios}"
        )

    # Register common functions
    function_handler.register_function("hang_up", func_hang_up)

    # Register scenario-specific functions
    if scenario == "insurance_file_claim":
        function_handler.register_function(
            "provide_insurance_info", func_provide_insurance_info
        )


def get_available_caller_types() -> list[str]:
    """
    Get a list of all available caller personality types.

    Returns:
        List of available caller personality type names
    """
    return list(PERSONALITIES.keys())


def get_available_scenarios() -> list[str]:
    """
    Get a list of all available scenarios.

    Returns:
        List of available scenario names
    """
    return list(SCENARIOS.keys())


def get_caller_description(caller_type: str) -> str:
    """
    Get a description of what each caller personality type represents.

    Args:
        caller_type: The personality type of caller

    Returns:
        Description of the caller personality type

    Raises:
        ValueError: If caller_type is not recognized
    """
    descriptions = {
        CallerType.TYPICAL: "A cooperative, patient caller who provides clear information and is easy to work with",
        CallerType.FRUSTRATED: "An impatient, demanding caller who is easily frustrated and may interrupt frequently",
        CallerType.ELDERLY: "A patient, polite caller who may need more guidance and has lower tech comfort",
        CallerType.HURRIED: "A caller in a rush who wants quick service and may interrupt to speed things up",
    }

    if caller_type not in descriptions:
        available_types = ", ".join(descriptions.keys())
        raise ValueError(
            f"Unknown caller_type: {caller_type}. Available: {available_types}"
        )

    return descriptions[caller_type]


def get_scenario_description(scenario: str) -> str:
    """
    Get a description of what each scenario represents.

    Args:
        scenario: The scenario name

    Returns:
        Description of the scenario

    Raises:
        ValueError: If scenario is not recognized
    """
    descriptions = {
        "banking_card_replacement": "Customer calling to replace a lost or stolen debit/credit card",
        "insurance_file_claim": "Customer calling to file an insurance claim after an incident",
    }

    if scenario not in descriptions:
        available_scenarios = ", ".join(descriptions.keys())
        raise ValueError(
            f"Unknown scenario: {scenario}. Available: {available_scenarios}"
        )

    return descriptions[scenario]


# ==============================
# LEGACY API - Backwards compatibility
# ==============================

# Keep old configuration mapping for backwards compatibility
CALLER_CONFIGS = {
    CallerType.TYPICAL: lambda: get_caller_config(
        CallerType.TYPICAL, "banking_card_replacement"
    ),
    CallerType.FRUSTRATED: lambda: get_caller_config(
        CallerType.FRUSTRATED, "banking_card_replacement"
    ),
    CallerType.ELDERLY: lambda: get_caller_config(
        CallerType.ELDERLY, "banking_card_replacement"
    ),
    CallerType.HURRIED: lambda: get_caller_config(
        CallerType.HURRIED, "banking_card_replacement"
    ),
}

# Keep old function registration mapping for backwards compatibility
CALLER_FUNCTION_REGISTRARS = {
    CallerType.TYPICAL: lambda fh: register_caller_functions(
        CallerType.TYPICAL, "banking_card_replacement", fh
    ),
    CallerType.FRUSTRATED: lambda fh: register_caller_functions(
        CallerType.FRUSTRATED, "banking_card_replacement", fh
    ),
    CallerType.ELDERLY: lambda fh: register_caller_functions(
        CallerType.ELDERLY, "banking_card_replacement", fh
    ),
    CallerType.HURRIED: lambda fh: register_caller_functions(
        CallerType.HURRIED, "banking_card_replacement", fh
    ),
}
