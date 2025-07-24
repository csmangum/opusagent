"""
Dual Agent Bridge for routing audio between caller agent and CS agent.

This bridge manages two OpenAI Realtime API sessions simultaneously and routes
audio between a caller agent and customer service agent.
"""

import asyncio
import json
import logging
import uuid
from typing import Optional, Dict, Any

from opusagent.config.logging_config import configure_logging
from opusagent.websocket_manager import get_websocket_manager, RealtimeConnection
from opusagent.agents.banking_agent import session_config as cs_session_config
from opusagent.call_recorder import CallRecorder, AudioChannel, TranscriptType
from opusagent.callers import get_caller_config, register_caller_functions, CallerType
from opusagent.transcript_manager import TranscriptManager

logger = configure_logging("dual_agent_bridge")


class DualAgentBridge:
    """Bridge that manages two AI agents and routes audio between them.
    
    This bridge creates and manages two separate OpenAI Realtime API sessions:
    - One for the caller agent (with caller personality and tools)
    - One for the customer service agent (with CS tools and behavior)
    
    Audio is routed bidirectionally between the agents to enable conversation.
    """
    
    def __init__(self, caller_type: str = CallerType.TYPICAL, conversation_id: Optional[str] = None):
        """Initialize the dual agent bridge.
        
        Args:
            caller_type: Type of caller to use (typical, frustrated, elderly, hurried)
            conversation_id: Optional conversation ID for tracking
        """
        self.conversation_id = conversation_id or str(uuid.uuid4())
        self.caller_type = caller_type
        
        # OpenAI Realtime connections
        self.caller_connection: Optional[RealtimeConnection] = None
        self.cs_connection: Optional[RealtimeConnection] = None
        
        # Session configurations
        self.caller_session_config = get_caller_config(caller_type)
        self.cs_session_config = cs_session_config
        
        # Audio routing state
        self.caller_audio_buffer = []
        self.cs_audio_buffer = []
        
        # Connection state
        self._closed = False
        self._caller_ready = False
        self._cs_ready = False
        
        # Turn management
        self._current_speaker = None  # "caller" or "cs" or None
        self._turn_lock = asyncio.Lock()
        self._waiting_for_response = False
        
        # Call recording
        self.call_recorder: Optional[CallRecorder] = None
        
        # Transcript managers for both agents
        self.caller_transcript_manager: Optional[TranscriptManager] = None
        self.cs_transcript_manager: Optional[TranscriptManager] = None
        
        logger.info(f"DualAgentBridge created for conversation: {self.conversation_id} with {caller_type} caller")
    
    async def initialize_connections(self):
        """Initialize both OpenAI Realtime connections."""
        try:
            # Get separate OpenAI connections for both agents
            # Force creation of separate connections by getting them sequentially
            websocket_mgr = get_websocket_manager()
            caller_conn = await websocket_mgr.get_connection()
            cs_conn = await websocket_mgr.get_connection()
            
            # Ensure we have different connections
            if caller_conn.connection_id == cs_conn.connection_id:
                # Force creation of a new connection for CS agent
                cs_conn = await websocket_mgr._create_connection()
                cs_conn.mark_used()
            
            self.caller_connection = caller_conn
            self.cs_connection = cs_conn
            
            logger.info(f"Caller connection: {caller_conn.connection_id}")
            logger.info(f"CS connection: {cs_conn.connection_id}")
            
            # Log voice configuration for clarity
            logger.info(f"Caller agent voice: {self.caller_session_config.voice}")
            logger.info(f"CS agent voice: {self.cs_session_config.voice}")
            logger.info(f"Caller type: {self.caller_type}")
            
            # Initialize call recording
            await self._initialize_call_recording()
            
            # Initialize sessions for both agents
            await self._initialize_caller_session()
            await self._initialize_cs_session()
            
            # Start message handling for both connections
            await asyncio.gather(
                self._handle_caller_messages(),
                self._handle_cs_messages(),
                self._manage_conversation_flow(),
                return_exceptions=True
            )
                    
        except Exception as e:
            logger.error(f"Error initializing connections: {e}")
            await self.close()
            raise
    
    async def _initialize_call_recording(self):
        """Initialize call recording for the agent conversation."""
        try:
            self.call_recorder = CallRecorder(
                conversation_id=self.conversation_id,
                session_id=self.conversation_id,
                base_output_dir="agent_conversations",
                bot_sample_rate=24000  # OpenAI Realtime API uses 24kHz
            )
            
            # For agent-to-agent conversations, both agents use 24kHz
            # Override the default caller sample rate
            self.call_recorder.caller_sample_rate = 24000
            logger.info("Configured call recorder for agent-to-agent conversation (both agents at 24kHz)")
            
            await self.call_recorder.start_recording()
            logger.info(f"Call recording started for agent conversation: {self.conversation_id}")
            
            # Initialize transcript managers
            self.caller_transcript_manager = TranscriptManager(self.call_recorder)
            self.cs_transcript_manager = TranscriptManager(self.call_recorder)
            logger.info("Transcript managers initialized for both agents")
            
        except Exception as e:
            logger.error(f"Failed to initialize call recording: {e}")
            # Continue without recording rather than fail the entire conversation
            self.call_recorder = None
            self.caller_transcript_manager = None
            self.cs_transcript_manager = None
        
        return True
    
    async def _initialize_caller_session(self):
        """Initialize the caller agent OpenAI session."""
        if not self.caller_connection:
            raise RuntimeError("Caller connection not available")
            
        session_update = {
            "type": "session.update",
            "session": self.caller_session_config.model_dump()
        }
        
        await self.caller_connection.websocket.send(json.dumps(session_update))
        logger.info("Caller session initialized")
        
        # Set up caller context but don't trigger initial response
        # The caller will respond after hearing the CS agent's greeting
        initial_message = {
            "type": "conversation.item.create",
            "item": {
                "type": "message", 
                "role": "user",
                "content": [{
                    "type": "input_text",
                    "text": "You are calling the bank's customer service. Wait for the agent to greet you, then explain your problem."
                }]
            }
        }
        
        await self.caller_connection.websocket.send(json.dumps(initial_message))
        self._caller_ready = True
    
    async def _initialize_cs_session(self):
        """Initialize the CS agent OpenAI session."""
        if not self.cs_connection:
            raise RuntimeError("CS connection not available")
            
        session_update = {
            "type": "session.update", 
            "session": self.cs_session_config.model_dump()
        }
        
        await self.cs_connection.websocket.send(json.dumps(session_update))
        logger.info("CS session initialized")
        
        # Add initial context for CS agent to start with greeting
        initial_message = {
            "type": "conversation.item.create",
            "item": {
                "type": "message", 
                "role": "user",
                "content": [{
                    "type": "input_text",
                    "text": "A customer is calling. Answer the phone and greet them professionally."
                }]
            }
        }
        
        await self.cs_connection.websocket.send(json.dumps(initial_message))
        self._cs_ready = True
    
    async def _create_response(self, websocket, agent_type: str):
        """Create a response for the specified agent."""
        # Use appropriate configuration for each agent
        if agent_type == "caller":
            voice = self.caller_session_config.voice
            temperature = self.caller_session_config.temperature
            max_tokens = self.caller_session_config.max_response_output_tokens
        else:  # cs agent
            voice = self.cs_session_config.voice
            temperature = self.cs_session_config.temperature
            max_tokens = self.cs_session_config.max_response_output_tokens
        
        response_create = {
            "type": "response.create",
            "response": {
                "modalities": ["text", "audio"],
                "output_audio_format": "pcm16",
                "temperature": temperature,
                "max_output_tokens": max_tokens,
                "voice": voice
            }
        }
        
        await websocket.send(json.dumps(response_create))
        logger.info(f"Response triggered for {agent_type} (voice: {voice})")
    
    async def _handle_caller_messages(self):
        """Handle messages from caller agent OpenAI session."""
        if not self.caller_connection:
            return
            
        try:
            async for message in self.caller_connection.websocket:
                if self._closed:
                    break
                    
                data = json.loads(message)
                await self._process_caller_message(data)
                
        except Exception as e:
            logger.error(f"Error handling caller messages: {e}")
            await self.close()
    
    async def _handle_cs_messages(self):
        """Handle messages from CS agent OpenAI session."""
        if not self.cs_connection:
            return
            
        try:
            async for message in self.cs_connection.websocket:
                if self._closed:
                    break
                    
                data = json.loads(message)
                await self._process_cs_message(data)
                
        except Exception as e:
            logger.error(f"Error handling CS messages: {e}")
            await self.close()
    
    async def _process_caller_message(self, data: Dict[str, Any]):
        """Process message from caller agent and route to CS agent."""
        if not self.cs_connection:
            return
            
        message_type = data.get("type")
        
        if message_type == "response.created":
            # Caller started speaking
            async with self._turn_lock:
                self._current_speaker = "caller"
                self._waiting_for_response = False
                logger.debug("Caller started speaking")
        
        elif message_type == "response.audio.delta":
            # Route caller audio to CS agent
            audio_data = data.get("delta", "")
            if audio_data:
                await self._route_audio_to_cs(audio_data)
                # Record caller audio
                if self.call_recorder:
                    await self.call_recorder.record_caller_audio(audio_data)
                
        elif message_type == "response.audio.done":
            # Caller finished speaking, trigger CS response
            async with self._turn_lock:
                if self._current_speaker == "caller" and not self._waiting_for_response:
                    logger.info("Caller finished speaking, triggering CS response")
                    self._current_speaker = None
                    self._waiting_for_response = True
                    await self._create_response(self.cs_connection.websocket, "cs")
                
        elif message_type == "response.done":
            # Caller completely finished their turn
            async with self._turn_lock:
                if self._current_speaker == "caller":
                    self._current_speaker = None
                    logger.debug("Caller turn completed")
            
        elif message_type == "response.audio_transcript.delta":
            # Log and record caller transcript using transcript manager
            transcript = data.get("delta", "")
            if transcript and self.caller_transcript_manager:
                await self.caller_transcript_manager.handle_output_transcript_delta(transcript)
            elif transcript:
                logger.info(f"Caller transcript: {transcript}")
                # Fallback: Record transcript for caller (treat as input from caller perspective)
                if self.call_recorder:
                    await self.call_recorder.add_transcript(
                        text=transcript,
                        channel=AudioChannel.CALLER,
                        transcript_type=TranscriptType.OUTPUT  # Caller's output
                    )
                
        elif message_type == "response.audio_transcript.done":
            # Handle caller transcript completion
            if self.caller_transcript_manager:
                await self.caller_transcript_manager.handle_output_transcript_completed()
            logger.debug("Caller transcript completed")
                
        elif message_type == "error":
            # Handle error messages from caller agent
            error_code = data.get("error", {}).get("code", "unknown")
            error_message = data.get("error", {}).get("message", "Unknown error")
            logger.error(f"Caller agent error: {error_code} - {error_message}")
            # Don't close the connection immediately, just log the error
                
        logger.debug(f"Caller message: {message_type}")
    
    async def _process_cs_message(self, data: Dict[str, Any]):
        """Process message from CS agent and route to caller agent."""
        if not self.caller_connection:
            return
            
        message_type = data.get("type")
        
        if message_type == "response.created":
            # CS started speaking
            async with self._turn_lock:
                self._current_speaker = "cs"
                self._waiting_for_response = False
                logger.debug("CS started speaking")
        
        elif message_type == "response.audio.delta":
            # Route CS audio to caller agent as input
            audio_data = data.get("delta", "")
            if audio_data:
                await self._route_audio_to_caller(audio_data)
                # Record CS agent audio (as bot audio)
                if self.call_recorder:
                    await self.call_recorder.record_bot_audio(audio_data)
                
        elif message_type == "response.audio.done":
            # CS finished speaking, trigger caller response
            async with self._turn_lock:
                if self._current_speaker == "cs" and not self._waiting_for_response:
                    logger.info("CS finished speaking, triggering caller response")
                    self._current_speaker = None
                    self._waiting_for_response = True
                    await self._create_response(self.caller_connection.websocket, "caller")
                
        elif message_type == "response.done":
            # CS completely finished their turn
            async with self._turn_lock:
                if self._current_speaker == "cs":
                    self._current_speaker = None
                    logger.debug("CS turn completed")
            
        elif message_type == "response.audio_transcript.delta":
            # Log and record CS transcript using transcript manager
            transcript = data.get("delta", "")
            if transcript and self.cs_transcript_manager:
                await self.cs_transcript_manager.handle_output_transcript_delta(transcript)
            elif transcript:
                logger.info(f"CS transcript: {transcript}")
                # Fallback: Record transcript for CS agent (as bot response)
                if self.call_recorder:
                    await self.call_recorder.add_transcript(
                        text=transcript,
                        channel=AudioChannel.BOT,
                        transcript_type=TranscriptType.OUTPUT  # Bot's output
                    )
                    
        elif message_type == "response.audio_transcript.done":
            # Handle CS transcript completion
            if self.cs_transcript_manager:
                await self.cs_transcript_manager.handle_output_transcript_completed()
            logger.debug("CS transcript completed")
                
        elif message_type == "error":
            # Handle error messages from CS agent
            error_code = data.get("error", {}).get("code", "unknown")
            error_message = data.get("error", {}).get("message", "Unknown error")
            logger.error(f"CS agent error: {error_code} - {error_message}")
            # Don't close the connection immediately, just log the error
                
        elif message_type == "response.function_call_arguments.done":
            # Record function calls made by CS agent
            if self.call_recorder:
                try:
                    function_name = data.get("name", "unknown_function")
                    arguments_str = data.get("arguments", "{}")
                    call_id = data.get("call_id")
                    
                    # Parse arguments if possible
                    import json
                    try:
                        arguments = json.loads(arguments_str) if arguments_str else {}
                    except json.JSONDecodeError:
                        arguments = {"raw_arguments": arguments_str}
                    
                    await self.call_recorder.log_function_call(
                        function_name=function_name,
                        arguments=arguments,
                        call_id=call_id
                    )
                    logger.info(f"Recorded function call: {function_name}")
                except Exception as e:
                    logger.error(f"Error recording function call: {e}")
                
        logger.debug(f"CS message: {message_type}")
    
    async def _route_audio_to_caller(self, audio_data: str):
        """Route CS agent audio to caller agent as input."""
        if not self.caller_connection:
            return
            
        audio_append = {
            "type": "input_audio_buffer.append",
            "audio": audio_data
        }
        
        await self.caller_connection.websocket.send(json.dumps(audio_append))
        
        # Commit audio after a small buffer
        self.cs_audio_buffer.append(audio_data)
        if len(self.cs_audio_buffer) >= 5:  # Buffer a few chunks
            await self._commit_caller_audio_buffer()
    
    async def _commit_caller_audio_buffer(self):
        """Commit audio buffer to caller agent."""
        if not self.caller_connection or not self.cs_audio_buffer:
            return
            
        commit_message = {
            "type": "input_audio_buffer.commit"
        }
        
        await self.caller_connection.websocket.send(json.dumps(commit_message))
        self.cs_audio_buffer.clear()
        logger.debug("Committed audio buffer to caller agent")
    
    async def _route_audio_to_cs(self, audio_data: str):
        """Route caller audio to CS agent as input."""
        if not self.cs_connection:
            return
            
        audio_append = {
            "type": "input_audio_buffer.append",
            "audio": audio_data
        }
        
        await self.cs_connection.websocket.send(json.dumps(audio_append))
        
        # Commit audio after a small buffer
        self.caller_audio_buffer.append(audio_data)
        if len(self.caller_audio_buffer) >= 5:  # Buffer a few chunks
            await self._commit_cs_audio_buffer()
    
    async def _commit_cs_audio_buffer(self):
        """Commit audio buffer to CS agent."""
        if not self.cs_connection or not self.caller_audio_buffer:
            return
            
        commit_message = {
            "type": "input_audio_buffer.commit"
        }
        
        await self.cs_connection.websocket.send(json.dumps(commit_message))
        self.caller_audio_buffer.clear()
        logger.debug("Committed audio buffer to CS agent")
    
    async def _manage_conversation_flow(self):
        """Manage the overall conversation flow between agents."""
        # Wait for both agents to be ready
        while not (self._caller_ready and self._cs_ready) and not self._closed:
            await asyncio.sleep(0.1)
        
        if self._closed:
            return
            
        logger.info("Both agents ready, conversation can begin")
        
        # Log recording status
        if self.call_recorder:
            logger.info(f"Recording agent conversation to: {self.call_recorder.recording_dir}")
        else:
            logger.warning("No call recorder available - conversation will not be recorded")
        
        # Start conversation with CS agent greeting
        await asyncio.sleep(1)  # Brief pause before starting
        if self.cs_connection:
            logger.info("Starting conversation with CS agent greeting")
            await self._create_response(self.cs_connection.websocket, "cs")
        
        # Monitor for conversation end conditions
        conversation_duration = 0
        max_duration = 300  # 5 minutes max
        
        while not self._closed and conversation_duration < max_duration:
            await asyncio.sleep(1)
            conversation_duration += 1
            
        if conversation_duration >= max_duration:
            logger.info("Maximum conversation duration reached, ending conversation")
            await self.close()
    
    async def close(self):
        """Close the dual agent bridge and cleanup resources."""
        if not self._closed:
            self._closed = True
            
            logger.info(f"Closing dual agent bridge for conversation: {self.conversation_id}")
            
            # Stop and finalize call recording
            if self.call_recorder:
                try:
                    await self.call_recorder.stop_recording()
                    summary = self.call_recorder.get_recording_summary()
                    logger.info(f"Agent conversation recording finalized: {summary}")
                except Exception as e:
                    logger.error(f"Error finalizing call recording: {e}")
            
            # Close both connections
            if self.caller_connection:
                await self.caller_connection.close()
                self.caller_connection = None
                
            if self.cs_connection:
                await self.cs_connection.close()
                self.cs_connection = None 