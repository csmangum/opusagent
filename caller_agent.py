#!/usr/bin/env python3
"""
Intelligent Caller Agent

Creates realistic AI-powered callers that interact with the bridge system.
Each caller has its own OpenAI Realtime connection and can follow scenarios
with different personalities (difficult, confused, angry, etc.).
"""

import asyncio
import base64
import io
import json
import logging
import tempfile
import uuid
import wave
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np
import websockets
from pydantic import BaseModel

from opusagent.config.logging_config import configure_logging
from opusagent.websocket_manager import create_websocket_manager

from validate.mock_audiocodes_client import MockAudioCodesClient

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


class CallerAgent:
    """
    Intelligent caller agent that uses OpenAI Realtime API to have realistic conversations.

    Combines MockAudioCodesClient with its own OpenAI connection to create
    human-like callers with different personalities and goals.
    """

    def __init__(
        self,
        bridge_url: str,
        personality: CallerPersonality,
        scenario: CallerScenario,
        caller_name: str = "TestCaller",
        caller_phone: str = "+15551234567",
        logger: Optional[logging.Logger] = None,
    ):
        self.bridge_url = bridge_url
        self.personality = personality
        self.scenario = scenario
        self.caller_name = caller_name
        self.caller_phone = caller_phone
        self.logger = logger or logging.getLogger(__name__)

        # Initialize components
        self.mock_client: Optional[MockAudioCodesClient] = None
        self.openai_websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.websocket_manager = create_websocket_manager()

        # State tracking
        self.conversation_active = True
        self.conversation_turns = 0
        self.goals_achieved = []
        self.conversation_log = []

        # Audio handling
        self.audio_buffer = []
        self.current_response = ""

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()

    async def connect(self):
        """Connect both the mock client and OpenAI Realtime API."""
        try:
            # Create mock AudioCodes client
            self.mock_client = MockAudioCodesClient(
                bridge_url=self.bridge_url,
                bot_name=f"{self.caller_name}Agent",
                caller=self.caller_phone,
                logger=self.logger,
            )

            # Get OpenAI connection
            connection = await self.websocket_manager.get_connection()
            self.openai_websocket = connection.websocket

            # Initialize OpenAI session for caller
            await self._initialize_openai_session()

            self.logger.info(f"CallerAgent {self.caller_name} connected successfully")

        except Exception as e:
            self.logger.error(f"Failed to connect CallerAgent: {e}")
            raise

    async def disconnect(self):
        """Disconnect all connections."""
        try:
            if self.mock_client:
                await self.mock_client.__aexit__(None, None, None)

            if self.openai_websocket and not self.openai_websocket.closed:
                await self.openai_websocket.close()

            await self.websocket_manager.shutdown()

            self.logger.info(f"CallerAgent {self.caller_name} disconnected")

        except Exception as e:
            self.logger.error(f"Error disconnecting CallerAgent: {e}")

    async def _initialize_openai_session(self):
        """Initialize the OpenAI Realtime API session for the caller."""
        # Combine personality and scenario prompts
        system_prompt = f"""
{self.personality.get_system_prompt()}

{self.scenario.get_scenario_prompt()}

IMPORTANT: You are the CALLER, not the agent. You're calling the bank for help.
Respond as a customer would, not as a customer service representative.
Keep responses natural and conversational. Don't be overly helpful or professional.
"""

        session_config = {
            "modalities": ["text", "audio"],
            "instructions": system_prompt,
            "voice": "alloy",  # Different voice from the agent
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16",
            "turn_detection": {"type": "server_vad"},
            "temperature": 0.8,
            "max_response_output_tokens": 4096,
        }

        session_update = {"type": "session.update", "session": session_config}

        await self.openai_websocket.send(json.dumps(session_update))
        self.logger.info(
            f"Initialized OpenAI session for {self.personality.type.value} caller"
        )

    async def start_call(self, timeout: float = 30.0) -> bool:
        """
        Start a call with the bridge and begin the conversation.

        Returns:
            True if call started successfully, False otherwise
        """
        try:
            async with self.mock_client:
                # Initiate session with bridge
                success = await self.mock_client.initiate_session()
                if not success:
                    self.logger.error("Failed to initiate session with bridge")
                    return False

                # Wait for greeting from agent
                greeting = await self.mock_client.wait_for_llm_greeting(timeout=timeout)
                if greeting:
                    self.logger.info(
                        f"Received greeting from agent: {len(greeting)} chunks"
                    )

                    # For now, we'll simulate text conversion and generate a simple response
                    # In a full implementation, you'd use actual audio-to-text conversion
                    greeting_text = (
                        "Hello, thank you for calling. How can I help you today?"
                    )
                    self.logger.info(f"Agent said: {greeting_text}")

                    # Generate response using OpenAI
                    response_audio = await self._generate_response_to_text(
                        greeting_text
                    )

                    # Send response back to bridge
                    if response_audio:
                        await self._send_audio_response(response_audio)

                    # Start the conversation loop
                    await self._conversation_loop()

                else:
                    self.logger.warning(
                        "No greeting received, starting conversation anyway"
                    )
                    await self._start_conversation()

                return True

        except Exception as e:
            self.logger.error(f"Error during call: {e}")
            return False

    async def _conversation_loop(self):
        """Main conversation loop between caller and agent."""
        max_turns = self.scenario.goal.max_conversation_turns

        while self.conversation_turns < max_turns and self.conversation_active:
            try:
                # Wait for agent response
                agent_audio = await self.mock_client.wait_for_llm_response(timeout=45.0)

                if agent_audio:
                    # For now, simulate text conversion
                    # In production, you'd use actual audio-to-text
                    agent_text = f"[Agent response {self.conversation_turns + 1}]"
                    self.logger.info(f"Agent: {agent_text}")

                    # Check if conversation goals are met
                    if self._check_goals_achieved(agent_text):
                        self.logger.info("Conversation goals achieved!")
                        await self._end_call_successfully()
                        break

                    # Check if we should end the call based on failure conditions
                    if self._check_failure_conditions(agent_text):
                        self.logger.info("Failure conditions detected, ending call")
                        await self._end_call_unsuccessfully()
                        break

                    # Generate caller response
                    caller_response = await self._generate_response_to_text(agent_text)

                    if caller_response:
                        await self._send_audio_response(caller_response)

                    self.conversation_turns += 1

                    # Add some personality-based delays
                    await self._personality_delay()

                else:
                    self.logger.warning("No response from agent, ending conversation")
                    await self._end_call_unsuccessfully()
                    break

            except Exception as e:
                self.logger.error(f"Error in conversation loop: {e}")
                await self._end_call_unsuccessfully()
                break

        # If we reach max turns without achieving goals, end the call
        if self.conversation_turns >= max_turns and self.conversation_active:
            self.logger.info(f"Reached maximum turns ({max_turns}), ending call")
            await self._end_call_unsuccessfully()

        self.logger.info(f"Conversation ended after {self.conversation_turns} turns")

    async def _end_call_successfully(self):
        """End the call successfully with a farewell message."""
        self.logger.info("Ending call successfully")
        self.conversation_active = False
        
        try:
            # Generate farewell message
            farewell_audio = await self._generate_farewell_message(success=True)
            
            if farewell_audio:
                await self._send_audio_response(farewell_audio)
                # Give the farewell time to play
                await asyncio.sleep(2.0)
            
            # End session with success reason
            await self.mock_client.end_session("Call completed successfully - goals achieved")
            
        except Exception as e:
            self.logger.error(f"Error ending call successfully: {e}")
            # Still try to end the session
            await self.mock_client.end_session("Call completed")

    async def _end_call_unsuccessfully(self):
        """End the call unsuccessfully."""
        self.logger.info("Ending call unsuccessfully")
        self.conversation_active = False
        
        try:
            # Generate farewell message (if personality allows)
            if self.personality.type not in [PersonalityType.ANGRY, PersonalityType.DIFFICULT]:
                farewell_audio = await self._generate_farewell_message(success=False)
                
                if farewell_audio:
                    await self._send_audio_response(farewell_audio)
                    # Give the farewell time to play
                    await asyncio.sleep(1.5)
            
            # End session with appropriate reason
            reason = "Call ended - goals not achieved"
            if self.conversation_turns >= self.scenario.goal.max_conversation_turns:
                reason = "Call ended - maximum turns reached"
            
            await self.mock_client.end_session(reason)
            
        except Exception as e:
            self.logger.error(f"Error ending call unsuccessfully: {e}")
            # Still try to end the session
            await self.mock_client.end_session("Call ended")

    async def _generate_farewell_message(self, success: bool = True) -> Optional[bytes]:
        """Generate a farewell message based on success and personality."""
        if success:
            prompt = f"Thank the agent for their help and end the call politely. Be {self.personality.type.value} but grateful."
        else:
            if self.personality.type == PersonalityType.ANGRY:
                prompt = "End the call with frustration, but don't be overly rude. Be {self.personality.type.value}."
            elif self.personality.type == PersonalityType.DIFFICULT:
                prompt = "End the call with dissatisfaction, but be civil. Be {self.personality.type.value}."
            else:
                prompt = f"End the call politely even though you're not completely satisfied. Be {self.personality.type.value}."

        # Send conversation item to OpenAI
        conversation_item = {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}],
            },
        }

        await self.openai_websocket.send(json.dumps(conversation_item))

        # Create response
        response_create = {
            "type": "response.create",
            "response": {
                "modalities": ["audio", "text"],
                "voice": "alloy",
                "output_audio_format": "pcm16",
            },
        }

        await self.openai_websocket.send(json.dumps(response_create))

        # Collect audio response
        return await self._collect_audio_response()

    def _check_failure_conditions(self, agent_text: str) -> bool:
        """Check if any failure conditions have been met."""
        text_lower = agent_text.lower()
        
        for condition in self.scenario.goal.failure_conditions:
            if condition.lower() in text_lower:
                self.logger.info(f"Failure condition detected: {condition}")
                return True
        
        return False

    async def _start_conversation(self):
        """Start the conversation with an opening statement."""
        opening = await self._generate_opening_statement()
        if opening:
            await self._send_audio_response(opening)
            await self._conversation_loop()

    async def _generate_opening_statement(self) -> Optional[bytes]:
        """Generate the opening statement for the call."""
        prompt = f"Start the call by greeting and explaining why you're calling. Be natural and {self.personality.type.value}."

        # Send conversation item to OpenAI
        conversation_item = {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}],
            },
        }

        await self.openai_websocket.send(json.dumps(conversation_item))

        # Create response
        response_create = {
            "type": "response.create",
            "response": {
                "modalities": ["audio", "text"],
                "voice": "alloy",
                "output_audio_format": "pcm16",
            },
        }

        await self.openai_websocket.send(json.dumps(response_create))

        # Collect audio response
        return await self._collect_audio_response()

    async def _generate_response_to_text(self, text: str) -> Optional[bytes]:
        """Generate audio response to text input."""
        self.logger.info(f"Generating response to: {text}")
        
        # Send text to OpenAI
        conversation_item = {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": text}],
            },
        }

        await self.openai_websocket.send(json.dumps(conversation_item))
        self.logger.debug("Sent conversation item to OpenAI")

        # Create response
        response_create = {
            "type": "response.create",
            "response": {
                "modalities": ["audio", "text"],
                "voice": "alloy",
                "output_audio_format": "pcm16",
            },
        }

        await self.openai_websocket.send(json.dumps(response_create))
        self.logger.debug("Sent response create to OpenAI")

        # Collect audio response
        audio_response = await self._collect_audio_response()
        if audio_response:
            self.logger.info(f"Generated audio response: {len(audio_response)} bytes")
        else:
            self.logger.warning("No audio response generated")
        return audio_response

    async def _collect_audio_response(self) -> Optional[bytes]:
        """Collect audio response from OpenAI."""
        audio_chunks = []
        self.logger.debug("Starting to collect audio response from OpenAI")

        try:
            timeout = 10.0  # 10 second timeout
            start_time = asyncio.get_event_loop().time()

            async for message in self.openai_websocket:
                if asyncio.get_event_loop().time() - start_time > timeout:
                    self.logger.warning("Timeout while collecting audio response")
                    break

                data = json.loads(message)
                msg_type = data.get("type")
                self.logger.debug(f"Received OpenAI message: {msg_type}")

                if msg_type == "response.audio.delta":
                    delta = data.get("delta", "")
                    audio_chunks.append(delta)
                    self.logger.debug(f"Collected audio delta: {len(delta)} chars")
                elif msg_type == "response.done":
                    self.logger.debug("Response complete signal received")
                    break
                elif msg_type == "error":
                    error_msg = data.get("error", {})
                    self.logger.error(f"OpenAI error: {error_msg}")
                    break

        except Exception as e:
            self.logger.error(f"Error collecting audio response: {e}")

        if audio_chunks:
            # Combine audio chunks
            combined_audio = b""
            for chunk in audio_chunks:
                combined_audio += base64.b64decode(chunk)
            self.logger.info(f"Combined {len(audio_chunks)} audio chunks into {len(combined_audio)} bytes")
            return combined_audio
        else:
            self.logger.warning("No audio chunks collected")

        return None

    async def _send_audio_response(self, audio_data: bytes):
        """Send audio response to the bridge."""
        self.logger.info(f"Sending audio response: {len(audio_data)} bytes")
        
        # Convert to WAV format and save temporarily
        temp_file_path = None
        try:
            # Resample from 24kHz (OpenAI) to 16kHz (bridge expected)
            resampled_audio = self._resample_audio_24k_to_16k(audio_data)
            
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file_path = temp_file.name
                with wave.open(temp_file, "wb") as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(16000)
                    wav_file.writeframes(resampled_audio)

            self.logger.debug(f"Created temp audio file: {temp_file_path}")

            # Send using mock client
            success = await self.mock_client.send_user_audio(temp_file_path)
            if success:
                self.logger.info("Audio response sent successfully")
            else:
                self.logger.error("Failed to send audio response")

        except Exception as e:
            self.logger.error(f"Error sending audio response: {e}")
        finally:
            # Clean up temp file
            if temp_file_path:
                try:
                    Path(temp_file_path).unlink()
                    self.logger.debug(f"Cleaned up temp file: {temp_file_path}")
                except Exception as e:
                    self.logger.warning(f"Failed to clean up temp file: {e}")

    def _resample_audio_24k_to_16k(self, audio_data: bytes) -> bytes:
        """Resample audio from 24kHz to 16kHz using high-quality interpolation."""
        try:
            import audioop
            
            # Use audioop.ratecv for proper resampling
            resampled_data, _ = audioop.ratecv(
                audio_data,
                2,  # Sample width in bytes (2 for PCM16)
                1,  # Number of channels
                24000,  # From rate (OpenAI's rate)
                16000,  # To rate (bridge expected rate)
                None  # State for continuous resampling
            )
            
            self.logger.debug(f"Resampled audio: {len(audio_data)} bytes (24kHz) -> {len(resampled_data)} bytes (16kHz)")
            return resampled_data
            
        except ImportError:
            # Fallback to simple resampling if audioop is not available
            self.logger.warning("audioop not available, using fallback resampling")
            
            # Convert bytes to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            # Calculate resampling ratio (24kHz -> 16kHz = 2/3)
            ratio = 16000 / 24000  # 2/3
            original_length = len(audio_array)
            new_length = int(original_length * ratio)
            
            # Use linear interpolation for resampling
            old_indices = np.linspace(0, original_length - 1, new_length)
            resampled_array = np.interp(old_indices, np.arange(original_length), audio_array)
            
            # Convert back to bytes
            resampled_data = resampled_array.astype(np.int16).tobytes()
            
            self.logger.debug(f"Fallback resampled: {len(audio_data)} bytes -> {len(resampled_data)} bytes")
            return resampled_data
            
        except Exception as e:
            self.logger.error(f"Error resampling audio: {e}")
            # Return original data if resampling fails
            return audio_data

    async def _personality_delay(self):
        """Add personality-based delays between responses."""
        if self.personality.type == PersonalityType.IMPATIENT:
            delay = 0.5  # Very quick responses
        elif self.personality.type == PersonalityType.ELDERLY:
            delay = 3.0  # Slower responses
        elif self.personality.type == PersonalityType.CONFUSED:
            delay = 2.0  # Thinking time
        else:
            delay = 1.0  # Normal delay

        await asyncio.sleep(delay)

    def _check_goals_achieved(self, agent_text: str) -> bool:
        """Check if conversation goals have been achieved."""
        for criterion in self.scenario.goal.success_criteria:
            if criterion.lower() in agent_text.lower():
                if criterion not in self.goals_achieved:
                    self.goals_achieved.append(criterion)
                    self.logger.info(f"Goal achieved: {criterion}")

        # Check if all criteria met
        return len(self.goals_achieved) >= len(self.scenario.goal.success_criteria)

    def get_call_status(self) -> Dict[str, Any]:
        """Get the current status of the call."""
        return {
            "conversation_active": self.conversation_active,
            "conversation_turns": self.conversation_turns,
            "goals_achieved": self.goals_achieved,
            "total_goals": len(self.scenario.goal.success_criteria),
            "max_turns": self.scenario.goal.max_conversation_turns,
            "personality": self.personality.type.value,
            "scenario": self.scenario.type.value,
            "caller_name": self.caller_name,
            "caller_phone": self.caller_phone
        }

    def get_call_results(self) -> Dict[str, Any]:
        """Get the final results of the call."""
        goals_achieved_count = len(self.goals_achieved)
        total_goals = len(self.scenario.goal.success_criteria)
        success_rate = goals_achieved_count / total_goals if total_goals > 0 else 0.0
        
        return {
            "success": goals_achieved_count >= total_goals,
            "success_rate": success_rate,
            "goals_achieved": self.goals_achieved,
            "total_goals": total_goals,
            "conversation_turns": self.conversation_turns,
            "max_turns_reached": self.conversation_turns >= self.scenario.goal.max_conversation_turns,
            "personality": self.personality.type.value,
            "scenario": self.scenario.type.value,
            "caller_name": self.caller_name,
            "caller_phone": self.caller_phone,
            "conversation_log": self.conversation_log.copy()
        }

    async def end_call(self, reason: str = "Manual call termination"):
        """Manually end the call from outside the conversation loop."""
        if not self.conversation_active:
            self.logger.info("Call already ended")
            return
        
        self.logger.info(f"Manually ending call: {reason}")
        self.conversation_active = False
        
        try:
            # Generate a brief farewell if appropriate
            if self.personality.type not in [PersonalityType.ANGRY, PersonalityType.DIFFICULT]:
                farewell_audio = await self._generate_farewell_message(success=False)
                if farewell_audio:
                    await self._send_audio_response(farewell_audio)
                    await asyncio.sleep(1.0)
            
            # End the session
            await self.mock_client.end_session(reason)
            
        except Exception as e:
            self.logger.error(f"Error ending call manually: {e}")
            # Still try to end the session
            await self.mock_client.end_session("Call ended manually")


# Predefined Personalities and Scenarios


def create_difficult_card_replacement_caller(
    bridge_url: str = "ws://localhost:8000/caller-agent",
) -> CallerAgent:
    """Create a difficult caller who needs card replacement."""

    personality = CallerPersonality(
        type=PersonalityType.DIFFICULT,
        traits=[
            "stubborn",
            "argues with agent",
            "reluctant to provide info",
            "questions everything",
        ],
        communication_style="Confrontational and suspicious",
        patience_level=2,
        tech_comfort=3,
        tendency_to_interrupt=0.8,
        provides_clear_info=0.3,
    )

    goal = CallerGoal(
        primary_goal="Get my lost gold card replaced",
        secondary_goals=["Complain about security", "Question fees"],
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
            "difficult": True,
            "suspicious_of_security": True,
        },
    )

    return CallerAgent(
        bridge_url=bridge_url,
        personality=personality,
        scenario=scenario,
        caller_name="DifficultDan",
        caller_phone="+15551234567",
    )


def create_confused_elderly_caller(
    bridge_url: str = "ws://localhost:8000/caller-agent",
) -> CallerAgent:
    """Create a confused elderly caller who lost a card but isn't sure which one it was."""

    personality = CallerPersonality(
        type=PersonalityType.ELDERLY,
        traits=[
            "confused about technology",
            "asks for clarification",
            "polite but slow",
            "unsure about details",
            "needs help remembering",
        ],
        communication_style="Polite but needs lots of help",
        patience_level=8,
        tech_comfort=2,
        tendency_to_interrupt=0.1,
        provides_clear_info=0.4,
    )

    goal = CallerGoal(
        primary_goal="Replace my lost card but I'm not sure which one it was",
        secondary_goals=["Figure out which card I lost", "Get help with card replacement"],
        success_criteria=["card identified", "replacement ordered", "delivery confirmed"],
        failure_conditions=["hung up in frustration", "transferred to human"],
        max_conversation_turns=20,
    )

    scenario = CallerScenario(
        scenario_type=ScenarioType.CARD_REPLACEMENT,
        goal=goal,
        context={
            "card_type": "unknown",
            "reason": "lost",
            "confused_about_which_card": True,
            "needs_simple_explanations": True,
            "may_have_multiple_cards": True,
        },
    )

    return CallerAgent(
        bridge_url=bridge_url,
        personality=personality,
        scenario=scenario,
        caller_name="ElderlyEllen",
        caller_phone="+15559876543",
    )


def create_angry_complaint_caller(
    bridge_url: str = "ws://localhost:8000/caller-agent",
) -> CallerAgent:
    """Create an angry caller with a complaint."""

    personality = CallerPersonality(
        type=PersonalityType.ANGRY,
        traits=["frustrated", "demands immediate action", "raises voice", "impatient"],
        communication_style="Aggressive and demanding",
        patience_level=1,
        tech_comfort=7,
        tendency_to_interrupt=0.9,
        provides_clear_info=0.6,
    )

    goal = CallerGoal(
        primary_goal="Complain about unauthorized charges",
        secondary_goals=["Get charges reversed", "Speak to manager"],
        success_criteria=["charges investigated", "resolution offered"],
        failure_conditions=["dismissed without help"],
        max_conversation_turns=10,
    )

    scenario = CallerScenario(
        scenario_type=ScenarioType.COMPLAINT,
        goal=goal,
        context={
            "complaint_about": "unauthorized charges",
            "urgency": "high",
            "amount": "$500",
        },
    )

    return CallerAgent(
        bridge_url=bridge_url,
        personality=personality,
        scenario=scenario,
        caller_name="AngryAndy",
        caller_phone="+15558888888",
    )


def create_perfect_card_replacement_caller(
    bridge_url: str = "ws://localhost:8000/ws/telephony",
) -> CallerAgent:
    """Create a perfect caller who provides all necessary information upfront."""

    personality = CallerPersonality(
        type=PersonalityType.NORMAL,
        traits=[
            "clear and direct",
            "prepared with information",
            "cooperative",
            "efficient",
            "polite but concise",
        ],
        communication_style="Direct and helpful",
        patience_level=7,
        tech_comfort=8,
        tendency_to_interrupt=0.1,
        provides_clear_info=1.0,  # Perfect information provision
    )

    goal = CallerGoal(
        primary_goal="Replace lost gold card efficiently",
        secondary_goals=["Confirm delivery to address on file", "Get replacement card quickly"],
        success_criteria=["card replacement confirmed", "delivery address confirmed", "replacement ordered"],
        failure_conditions=["transferred to human", "call terminated", "asked for additional verification"],
        max_conversation_turns=5,  # Should be very quick
    )

    scenario = CallerScenario(
        scenario_type=ScenarioType.CARD_REPLACEMENT,
        goal=goal,
        context={
            "card_type": "gold card",
            "reason": "lost",
            "perfect_caller": True,
            "has_all_info": True,
            "wants_efficient_service": True,
        },
    )

    return CallerAgent(
        bridge_url=bridge_url,
        personality=personality,
        scenario=scenario,
        caller_name="PerfectPat",
        caller_phone="+15551111111",
    )


# Example usage script
async def run_caller_agent_demo():
    """Run a demo of different caller agents."""

    logger.info("Starting Caller Agent Demo")

    # Test different caller types
    callers = [
        ("Difficult Card Replacement", create_difficult_card_replacement_caller),
        ("Confused Elderly", create_confused_elderly_caller),
        ("Angry Complaint", create_angry_complaint_caller),
        ("Perfect Card Replacement", create_perfect_card_replacement_caller),
    ]

    for caller_name, caller_factory in callers:
        logger.info(f"\n{'='*50}")
        logger.info(f"Testing: {caller_name}")
        logger.info(f"{'='*50}")

        try:
            async with caller_factory() as caller:
                success = await caller.start_call(timeout=30.0)

                if success:
                    logger.info(f"✅ {caller_name} call completed successfully")
                    logger.info(f"   Goals achieved: {caller.goals_achieved}")
                    logger.info(f"   Conversation turns: {caller.conversation_turns}")
                else:
                    logger.error(f"❌ {caller_name} call failed")

        except Exception as e:
            logger.error(f"❌ {caller_name} failed with error: {e}")

        # Wait between calls
        await asyncio.sleep(5.0)

    logger.info("\nCaller Agent Demo completed")


if __name__ == "__main__":
    import sys

    try:
        asyncio.run(run_caller_agent_demo())
        sys.exit(0)
    except KeyboardInterrupt:
        logger.info("Demo interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        sys.exit(1)
