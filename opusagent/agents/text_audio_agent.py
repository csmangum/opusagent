"""
Text-to-Audio Agent for OpenAI Realtime API Integration

This module provides a specialized agent that connects to the real OpenAI Realtime API
using text modality only, but includes a function tool that allows the LLM to trigger
local audio file playback. This enables the AI to "speak" by choosing appropriate
audio files to play rather than generating audio directly.

Key Features:
    - **Text-Only Communication**: Uses only text modality with OpenAI API to reduce latency and costs
    - **Local Audio Control**: LLM can trigger local audio playback through function calls
    - **Audio File Selection**: AI can choose from available audio files based on context
    - **Real-time Response**: Maintains conversational flow while controlling audio output
    - **Flexible Audio Library**: Supports any audio files available in the configured directory

Architecture:
    The TextAudioAgent maintains a real WebSocket connection to OpenAI's Realtime API
    but configures it for text-only operation. When the AI wants to "speak", it calls
    the play_audio function with a filename, which triggers local audio playback.

    Flow:
    1. User input → Text → OpenAI Realtime API
    2. OpenAI responds with text + play_audio function call
    3. Local system plays the specified audio file
    4. Conversation continues with text

Usage Example:
    ```python
    # Initialize the agent
    agent = TextAudioAgent(audio_directory="demo/audio/")
    
    # Start the agent
    await agent.connect()
    
    # The agent will now respond to text input by choosing appropriate audio files
    ```
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import uuid

from opusagent.config.logging_config import configure_logging
from opusagent.models.openai_api import SessionConfig
from opusagent.models.tool_models import (
    OpenAITool,
    ToolParameter,
    ToolParameters,
)
from opusagent.handlers.websocket_manager import get_websocket_manager
from opusagent.handlers.function_handler import FunctionHandler
from opusagent.handlers.realtime_handler import RealtimeHandler
from opusagent.handlers.audio_stream_handler import AudioStreamHandler
from opusagent.handlers.session_manager import SessionManager
from opusagent.handlers.event_router import EventRouter
from opusagent.handlers.transcript_manager import TranscriptManager

logger = configure_logging("text_audio_agent")

# Add these imports at the top after the existing imports
from pathlib import Path
try:
    from tui.utils.audio_utils import AudioUtils
    from tui.models.audio_manager import AudioManager, AudioConfig, AudioFormat
    import sounddevice as sd
    import numpy as np
    AUDIO_PLAYBACK_AVAILABLE = True
except ImportError:
    AudioUtils = None
    AudioManager = None
    AudioConfig = None
    AudioFormat = None
    sd = None
    np = None
    AUDIO_PLAYBACK_AVAILABLE = False
    logger.warning("Audio playback not available. Install sounddevice and other audio dependencies.")

# Global audio manager instance for playback
_global_audio_manager = None

def _get_audio_manager():
    """Get or create the global audio manager instance."""
    global _global_audio_manager
    if _global_audio_manager is None and AUDIO_PLAYBACK_AVAILABLE and AudioManager and AudioConfig and AudioFormat:
        try:
            config = AudioConfig(
                sample_rate=16000,
                channels=1,
                chunk_size=1024,
                format=AudioFormat.PCM16,
                latency=0.1
            )
            _global_audio_manager = AudioManager(config)
            success = _global_audio_manager.start_playback()
            if success:
                logger.info("Global audio manager initialized for playback")
            else:
                logger.error("Failed to start global audio manager playback")
                _global_audio_manager = None
        except Exception as e:
            logger.error(f"Failed to initialize global audio manager: {e}")
            _global_audio_manager = None
    elif _global_audio_manager and not _global_audio_manager.playing:
        # Restart playback if it was stopped
        logger.warning("Global audio manager playback stopped, restarting...")
        try:
            _global_audio_manager.stop_playback()
            success = _global_audio_manager.start_playback()
            if not success:
                logger.error("Failed to restart global audio manager playback")
                _global_audio_manager = None
        except Exception as e:
            logger.error(f"Failed to restart global audio manager: {e}")
            _global_audio_manager = None
    return _global_audio_manager

# Default system prompt
DEFAULT_SYSTEM_PROMPT = """
You are a helpful voice assistant that communicates through text but can play audio files for responses.

You have access to a play_audio function that allows you to play audio files to respond to the user.
When you want to "speak" to the user, call the play_audio function with an appropriate filename.

Available audio files are organized in categories with numbered files:
- greetings/greetings_01.wav through greetings_10.wav - for welcoming users
- farewells/farewells_01.wav through farewells_10.wav - for farewells  
- thank_you/thank_you_01.wav through thank_you_10.wav - for expressing gratitude
- errors/errors_01.wav through errors_10.wav - for error situations
- default/default_01.wav through default_10.wav - for general responses
- confirmations/confirmations_01.wav through confirmations_10.wav - for confirmations
- sales/sales_01.wav through sales_10.wav - for sales interactions
- customer_service/customer_service_01.wav through customer_service_10.wav - for customer service
- technical_support/technical_support_01.wav through technical_support_10.wav - for technical support
- card_replacement/card_replacement_01.wav through card_replacement_10.wav - for card replacement

IMPORTANT: Use the exact filename including the category folder and number, for example:
- play_audio("greetings/greetings_01.wav") for a greeting
- play_audio("farewells/farewells_03.wav") for a farewell
- play_audio("default/default_05.wav") for a general response

Choose the most appropriate audio file based on the context of the conversation.
You should use text responses to provide detailed information and audio files to add personality and engagement.

Always be helpful, friendly, and engaging in your responses.
"""


# ==============================
# Tool Parameters
# ==============================


class PlayAudioParameters(ToolParameters):
    """Parameters for the play_audio function."""

    type: str = "object"
    properties: Dict[str, ToolParameter] = {
        "filename": ToolParameter(
            type="string", 
            description="Name of the audio file to play (e.g., 'greeting.wav'). Should include the file extension."
        ),
        "context": ToolParameter(
            type="string", 
            description="Optional context for why this audio file was chosen",
            default=""
        ),
    }
    required: List[str] = ["filename"]


# ==============================
# Tools
# ==============================


class PlayAudioTool(OpenAITool):
    """Tool for playing audio files locally."""

    name: str = "play_audio"
    description: str = "Play a specified audio file to respond to the user. Use this to 'speak' by selecting appropriate audio files."
    parameters: PlayAudioParameters = PlayAudioParameters()


def get_text_audio_tools() -> List[Dict[str, Any]]:
    """
    Get all OpenAI tool definitions for the text-audio agent.

    Returns:
        List of OpenAI function tool schemas as dictionaries
    """
    tools = [
        PlayAudioTool(),
    ]
    return [tool.model_dump() for tool in tools]


# ==============================
# Function Implementations
# ==============================


async def func_play_audio(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Play an audio file locally.

    Args:
        arguments: Function arguments containing filename and optional context

    Returns:
        Playback status information
    """
    filename = arguments.get("filename", "")
    context = arguments.get("context", "")

    if not filename:
        logger.error("No filename provided for audio playback")
        return {
            "status": "error",
            "error": "No filename provided",
            "function_name": "play_audio"
        }

    if not AUDIO_PLAYBACK_AVAILABLE:
        logger.error("Audio playback not available - missing dependencies")
        return {
            "status": "error",
            "error": "Audio playback not available - install sounddevice and related dependencies",
            "function_name": "play_audio",
            "filename": filename
        }

    logger.info(f"Audio playback requested: {filename} (context: {context})")

    try:
        # Get the global audio manager
        audio_manager = _get_audio_manager()
        if not audio_manager:
            return {
                "status": "error",
                "error": "Failed to initialize audio manager",
                "function_name": "play_audio",
                "filename": filename
            }

        # Ensure audio manager is playing
        if not audio_manager.playing:
            logger.warning("Audio manager not playing, restarting playback...")
            audio_manager.stop_playback()
            success = audio_manager.start_playback()
            if not success:
                return {
                    "status": "error",
                    "error": "Failed to start audio playback",
                    "function_name": "play_audio",
                    "filename": filename
                }
            # Give the playback thread time to start
            await asyncio.sleep(0.2)

        # Get the audio directory from the global context (will be set by TextAudioAgent)
        audio_directory = getattr(func_play_audio, '_audio_directory', 'demo/audio/')
        audio_path = Path(audio_directory) / filename

        if not audio_path.exists():
            logger.error(f"Audio file not found: {audio_path}")
            return {
                "status": "error",
                "error": f"Audio file not found: {filename}",
                "function_name": "play_audio",
                "filename": filename
            }

        # Load the audio file (only if AudioUtils is available)
        if not AudioUtils:
            return {
                "status": "error",
                "error": "AudioUtils not available",
                "function_name": "play_audio",
                "filename": filename
            }

        # Load audio file with proper format conversion
        logger.info(f"Loading audio file: {audio_path}")
        audio_data, sample_rate, channels = AudioUtils.load_audio_file(str(audio_path), target_sample_rate=16000)
        
        if not audio_data:
            logger.error(f"Failed to load audio data from: {audio_path}")
            return {
                "status": "error",
                "error": f"Failed to load audio data from: {filename}",
                "function_name": "play_audio",
                "filename": filename
            }

        logger.info(f"Loaded audio: {filename} - {sample_rate}Hz, {channels}ch, {len(audio_data)} bytes")

        # Ensure audio data is in the correct format (16-bit PCM)
        if len(audio_data) % 2 != 0:
            logger.warning(f"Audio data length is odd ({len(audio_data)}), padding with zero")
            audio_data += b'\x00'

        # Chunk the audio for streaming playback (200ms chunks)
        chunks = AudioUtils.chunk_audio_by_duration(audio_data, sample_rate, 200, channels, 2)  # 2 bytes per sample for 16-bit
        
        logger.info(f"Created {len(chunks)} audio chunks for {filename}")
        
        # Queue all chunks for playback synchronously
        for i, chunk in enumerate(chunks):
            # Ensure chunk is properly formatted for playback
            if len(chunk) % 2 != 0:
                chunk += b'\x00'  # Pad to even length for 16-bit samples
            
            logger.debug(f"Queuing chunk {i+1}/{len(chunks)}: {len(chunk)} bytes")
            await audio_manager.play_audio_chunk(chunk)
            # Add a small delay between chunks to ensure proper queuing
            await asyncio.sleep(0.01)

        logger.info(f"Successfully queued {len(chunks)} audio chunks for playback: {filename}")
        
        # Add a longer delay to ensure audio starts playing and has time to process
        await asyncio.sleep(0.5)
        
        # Log audio manager statistics for debugging
        stats = audio_manager.get_statistics()
        logger.info(f"Audio manager stats: {stats}")
        
        # Check if audio was actually processed
        if stats['chunks_played'] == 0:
            logger.warning("No audio chunks were processed - audio may not be playing")
            # Try to restart the audio manager
            logger.info("Attempting to restart audio manager...")
            audio_manager.stop_playback()
            await asyncio.sleep(0.1)
            success = audio_manager.start_playback()
            if success:
                logger.info("Audio manager restarted successfully")
            else:
                logger.error("Failed to restart audio manager")
        else:
            logger.info(f"Audio chunks queued successfully: {stats['chunks_played']}")
            logger.info(f"Playback queue size: {stats['queue_size_playback']}")
            
            # Check if audio is actually being played by monitoring queue size
            initial_queue_size = stats['queue_size_playback']
            await asyncio.sleep(1.0)  # Wait for some audio to be played
            stats_after = audio_manager.get_statistics()
            final_queue_size = stats_after['queue_size_playback']
            
            if final_queue_size < initial_queue_size:
                logger.info(f"Audio is being played! Queue size decreased from {initial_queue_size} to {final_queue_size}")
            else:
                logger.warning(f"Audio may not be playing. Queue size unchanged: {initial_queue_size} -> {final_queue_size}")
        
        return {
            "status": "success",
            "filename": filename,
            "context": context,
            "function_name": "play_audio",
            "message": f"Playing audio file: {filename}",
            "chunks_queued": len(chunks),
            "chunks_processed": stats['chunks_played'],
            "queue_size": stats['queue_size_playback'],
            "duration_ms": len(audio_data) * 1000 // (sample_rate * channels * 2)  # Approximate duration
        }

    except Exception as e:
        logger.error(f"Error playing audio file {filename}: {e}")
        return {
            "status": "error",
            "error": f"Error playing audio file: {str(e)}",
            "function_name": "play_audio",
            "filename": filename
        }


# ==============================
# Text Audio Agent
# ==============================


class TextAudioAgent:
    """
    Agent that uses text-only OpenAI Realtime API communication but can trigger local audio playback.
    
    This agent maintains a real connection to OpenAI's Realtime API but configures it for
    text-only communication. The AI can trigger local audio file playback through function calls,
    allowing it to "speak" by selecting appropriate audio files.
    
    Attributes:
        audio_directory (str): Directory containing audio files
        system_prompt (str): System prompt for the AI
        available_files (List[str]): List of available audio files
        connection: WebSocket connection to OpenAI
        function_handler: Handler for function calls
        realtime_handler: Handler for OpenAI communication
        connected (bool): Connection status
    """
    
    def __init__(
        self,
        audio_directory: str = "opusagent/mock/audio/",
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ):
        """
        Initialize the TextAudioAgent.
        
        Args:
            audio_directory (str): Directory containing audio files to play
            system_prompt (Optional[str]): Custom system prompt for the AI
            temperature (float): AI response temperature (0.0-1.0)
        """
        self.audio_directory = Path(audio_directory)
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        self.temperature = temperature
        
        # Connection state
        self.connected = False
        self.connection = None
        self.function_handler = None
        self.realtime_handler = None
        
        # Audio management
        self.available_files = self._scan_audio_files()
        
        # Update system prompt with available files
        self._update_system_prompt_with_files()
        
        logger.info(f"TextAudioAgent initialized with {len(self.available_files)} audio files")
    
    def _scan_audio_files(self) -> List[str]:
        """
        Scan the audio directory for available audio files.
        
        Returns:
            List of audio filenames with relative paths
        """
        if not self.audio_directory.exists():
            logger.warning(f"Audio directory does not exist: {self.audio_directory}")
            return []
        
        audio_extensions = {'.wav', '.mp3', '.m4a', '.flac', '.ogg'}
        audio_files = []
        
        # Scan recursively through all subdirectories
        for file_path in self.audio_directory.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in audio_extensions:
                # Get relative path from audio directory
                relative_path = file_path.relative_to(self.audio_directory)
                audio_files.append(str(relative_path))
        
        logger.info(f"Found {len(audio_files)} audio files: {audio_files}")
        return sorted(audio_files)
    
    def _update_system_prompt_with_files(self):
        """Update the system prompt to include the list of available audio files."""
        if self.available_files:
            # Group files by category
            categories = {}
            for filename in self.available_files:
                if '/' in filename:
                    category = filename.split('/')[0]
                    if category not in categories:
                        categories[category] = []
                    categories[category].append(filename)
                else:
                    if 'other' not in categories:
                        categories['other'] = []
                    categories['other'].append(filename)
            
            # Build file list by category
            file_list = []
            for category, files in categories.items():
                if category == 'other':
                    file_list.append(f"Other files:")
                else:
                    file_list.append(f"{category.capitalize()} files:")
                
                # Show first few files in each category
                for filename in sorted(files)[:5]:  # Show first 5 files per category
                    file_list.append(f"  - {filename}")
                
                if len(files) > 5:
                    file_list.append(f"  - ... and {len(files) - 5} more files")
                file_list.append("")
            
            file_list_text = "\n".join(file_list)
            
            self.system_prompt = self.system_prompt.replace(
                "Available audio files are organized in categories:",
                f"Available audio files are organized in categories:\n\n{file_list_text}\n"
            )
        else:
            self.system_prompt += "\n\nNote: No audio files are currently available in the audio directory."
    
    def get_session_config(self) -> SessionConfig:
        """
        Get the session configuration for the text-audio agent.
        
        Returns:
            SessionConfig: Configuration for OpenAI Realtime API
        """
        tools = get_text_audio_tools()
        
        return SessionConfig(
            model="gpt-4o-realtime-preview-2025-06-03",
            modalities=["text"],  # Text only - no audio input/output from OpenAI
            instructions=self.system_prompt,
            temperature=self.temperature,
            tools=tools,
            tool_choice="auto",
            max_response_output_tokens=4096,
        )
    
    def _initialize_handlers(self):
        """Initialize the necessary handlers for OpenAI communication."""
        session_config = self.get_session_config()
        
        if not self.connection or not self.connection.websocket:
            logger.error("No valid WebSocket connection available")
            return
        
        # Initialize function handler for handling play_audio calls
        self.function_handler = FunctionHandler(
            realtime_websocket=self.connection.websocket,
            voice="verse"  # Provide a default voice even though we're text-only
        )
        
        # Register our play_audio function
        self.function_handler.register_function("play_audio", func_play_audio)
        
        # Set the audio directory for the play_audio function
        func_play_audio._audio_directory = str(self.audio_directory)
        
        logger.info(f"Function handler initialized with audio directory: {self.audio_directory}")

    async def send_text_message(self, text: str) -> bool:
        """
        Send a text message to the AI.
        
        Args:
            text (str): Text message to send
            
        Returns:
            bool: True if message sent successfully
        """
        if not self.connected or not self.connection:
            logger.error("Not connected to OpenAI API")
            return False
        
        try:
            # Initialize session if not done already
            await self._ensure_session_initialized()
            
            # Create conversation item for user input
            message = {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": text
                        }
                    ]
                }
            }
            
            await self.connection.websocket.send(json.dumps(message))
            
            # Create response
            response_message = {
                "type": "response.create",
                "response": {
                    "modalities": ["text"],
                    "instructions": "Respond to the user's message and call play_audio with an appropriate filename if you want to play audio."
                }
            }
            
            await self.connection.websocket.send(json.dumps(response_message))
            
            logger.info(f"Sent text message: {text}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send text message: {e}")
            return False
    
    async def _ensure_session_initialized(self):
        """Ensure the OpenAI session is properly initialized."""
        if not hasattr(self, '_session_initialized') or not self._session_initialized:
            if not self.connection or not self.connection.websocket:
                logger.error("No valid connection for session initialization")
                return
                
            session_config = self.get_session_config()
            
            # Send session update to configure the session
            session_update = {
                "type": "session.update",
                "session": {
                    "modalities": session_config.modalities,
                    "instructions": session_config.instructions,
                    "temperature": session_config.temperature,
                    "tools": session_config.tools,
                    "tool_choice": session_config.tool_choice,
                    "max_response_output_tokens": session_config.max_response_output_tokens,
                }
            }
            
            await self.connection.websocket.send(json.dumps(session_update))
            self._session_initialized = True
            logger.info("Session initialized with text-only configuration")
    
    async def start_message_handler(self):
        """Start handling incoming messages from OpenAI."""
        if not self.connected or not self.connection or not self.connection.websocket:
            logger.error("Not connected to OpenAI API")
            return
        
        try:
            # Use proper websocket message iteration
            websocket = self.connection.websocket
            while self.connected:
                try:
                    # Use a more robust method for receiving messages
                    message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    await self._handle_openai_message(message)
                except asyncio.TimeoutError:
                    # Send a ping to keep connection alive
                    logger.debug("WebSocket timeout, sending ping")
                    try:
                        await websocket.ping()
                    except:
                        logger.error("Failed to ping websocket, connection may be lost")
                        break
                except Exception as e:
                    logger.error(f"Error receiving message: {e}")
                    break
        except Exception as e:
            logger.error(f"Error in message handler: {e}")
            self.connected = False
    
    async def _handle_openai_message(self, message):
        """Handle incoming message from OpenAI."""
        try:
            if isinstance(message, (bytes, bytearray)):
                message = message.decode('utf-8')
            elif isinstance(message, memoryview):
                message = message.tobytes().decode('utf-8')
            
            data = json.loads(message)
            event_type = data.get("type", "")
            
            logger.debug(f"Received OpenAI event: {event_type}")
            
            # Handle function call events
            if event_type == "response.function_call_arguments.delta":
                if self.function_handler:
                    await self.function_handler.handle_function_call_arguments_delta(data)
            elif event_type == "response.function_call_arguments.done":
                if self.function_handler:
                    # Extract function name from the response
                    function_name = data.get("name")
                    if function_name and self.function_handler.active_function_calls:
                        call_id = data.get("call_id")
                        if call_id in self.function_handler.active_function_calls:
                            self.function_handler.active_function_calls[call_id]["function_name"] = function_name
                    
                    await self.function_handler.handle_function_call_arguments_done(data)
            elif event_type == "response.text.delta":
                # Handle text response
                text_delta = data.get("delta", "")
                logger.info(f"AI response: {text_delta}")
            elif event_type == "response.done":
                logger.info("Response completed")
            elif event_type == "error":
                error_msg = data.get("message", "Unknown error")
                logger.error(f"OpenAI error: {error_msg}")
            else:
                logger.debug(f"Unhandled event type: {event_type}")
                
        except Exception as e:
            logger.error(f"Error handling OpenAI message: {e}")

    async def connect(self) -> bool:
        """
        Connect to the OpenAI Realtime API.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            logger.info("Connecting to OpenAI Realtime API...")
            
            # Get WebSocket connection
            websocket_manager = get_websocket_manager()
            self.connection = await websocket_manager.get_connection()
            
            if not self.connection or not self.connection.websocket:
                logger.error("Failed to get WebSocket connection")
                return False
            
            # Initialize handlers
            self._initialize_handlers()
            
            # Start message handler in background
            asyncio.create_task(self.start_message_handler())
            
            self.connected = True
            logger.info("Successfully connected to OpenAI Realtime API")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to OpenAI Realtime API: {e}")
            self.connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from the OpenAI API and clean up resources."""
        try:
            # Stop the message handler
            self.connected = False
            
            if self.connection:
                # The connection will be managed by the WebSocket manager
                pass
            
            logger.info("Disconnected from OpenAI API")
            
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
    
    def register_audio_playback_callback(self, callback):
        """
        Register a callback function to handle actual audio playback.
        
        Args:
            callback: Function that takes (filename, audio_directory) and plays the audio
        """
        # This would be used to integrate with actual audio playback systems
        # For now, we'll just modify the function to accept this callback
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the agent.
        
        Returns:
            Dict containing status information
        """
        return {
            "connected": self.connected,
            "audio_directory": str(self.audio_directory),
            "available_files": self.available_files,
            "file_count": len(self.available_files)
        }


# ==============================
# Example Usage
# ==============================


async def example_usage():
    """Example of how to use the TextAudioAgent."""
    
    # Initialize the agent
    agent = TextAudioAgent(
        audio_directory="demo/audio/",
        system_prompt="You are a friendly assistant that can play audio files to communicate."
    )
    
    # Connect to OpenAI
    if await agent.connect():
        print("Connected to OpenAI API")
        
        # Send some example messages
        await agent.send_text_message("Hello, can you greet me?")
        await asyncio.sleep(2)
        
        await agent.send_text_message("Thank you for your help!")
        await asyncio.sleep(2)
        
        await agent.send_text_message("Goodbye!")
        await asyncio.sleep(2)
        
        # Disconnect
        await agent.disconnect()
    else:
        print("Failed to connect to OpenAI API")


if __name__ == "__main__":
    # Run the example
    asyncio.run(example_usage()) 