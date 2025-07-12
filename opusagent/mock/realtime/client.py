"""
Main LocalRealtimeClient implementation.

This module contains the main LocalRealtimeClient class that orchestrates
all the components (audio management, event handling, response generation)
to provide a complete mock implementation of the OpenAI Realtime API.
"""

import asyncio
import logging
import re
import time
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

import websockets
from websockets.asyncio.client import ClientConnection

from opusagent.models.openai_api import (
    ResponseCreateOptions,
    ServerEventType,
    SessionConfig,
)

from .audio import AudioManager
from .generators import ResponseGenerator
from .handlers import EventHandlerManager
from .models import ConversationContext, LocalResponseConfig, ResponseSelectionCriteria


class LocalRealtimeClient:
    """
    Enhanced mock client that simulates the OpenAI Realtime API.

    This client provides a complete simulation of the OpenAI Realtime API
    WebSocket connection, including all event types, response streaming,
    audio handling, and function calls. It's designed to be a drop-in
    replacement for the real API during testing and development.

    The LocalRealtimeClient supports:
    - Multiple response configurations for different scenarios
    - Saved audio phrases from actual audio files
    - Configurable timing for realistic streaming simulation
    - Function call simulation with custom arguments
    - Audio file caching for performance
    - Automatic fallback to silence for missing audio files
    - Complete WebSocket event handling

    Key Features:
        - **Response Configuration**: Define different responses for different
          scenarios using LocalResponseConfig objects
        - **Audio Support**: Load and stream actual audio files instead of silence
        - **Function Calls**: Simulate function calls with custom arguments
        - **Event Handling**: Handle all OpenAI Realtime API event types
        - **Caching**: Cache audio files for improved performance
        - **Fallbacks**: Graceful handling of missing files and errors

    Attributes:
        logger (logging.Logger): Logger instance for debugging and monitoring
        session_config (SessionConfig): OpenAI session configuration
        response_configs (Dict[str, LocalResponseConfig]): Available response configurations
        default_response_config (LocalResponseConfig): Default response when no specific config matches
        connected (bool): Connection status
        _ws (Optional[ClientConnection]): WebSocket connection
        _audio_manager (AudioManager): Audio file management
        _event_handler (EventHandlerManager): Event handling
        _response_generator (ResponseGenerator): Response generation
        _message_task (Optional[asyncio.Task]): Message handling task
        _response_timings (List[Dict[str, Any]]): Store recent response timings
    """

    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        session_config: Optional[SessionConfig] = None,
        response_configs: Optional[Dict[str, LocalResponseConfig]] = None,
        default_response_config: Optional[LocalResponseConfig] = None,
    ):
        """
        Initialize the LocalRealtimeClient.

        Args:
            logger (Optional[logging.Logger]): Logger instance for debugging.
                                             If None, creates a default logger.
            session_config (Optional[SessionConfig]): OpenAI session configuration.
                                                    If None, uses default settings.
            response_configs (Optional[Dict[str, LocalResponseConfig]]): Pre-configured
                                                                      response configurations
                                                                      for different scenarios.
            default_response_config (Optional[LocalResponseConfig]): Default response
                                                                   configuration when no
                                                                   specific config matches.

        Example:
            ```python
            # Basic initialization
            mock_client = LocalRealtimeClient()

            # With custom configurations
            configs = {
                "greeting": LocalResponseConfig(text="Hello!"),
                "help": LocalResponseConfig(text="How can I help?")
            }
            mock_client = LocalRealtimeClient(response_configs=configs)
            ```
        """
        self.logger = logger or logging.getLogger(__name__)
        self.session_config = session_config or SessionConfig(
            model="gpt-4o-realtime-preview-2025-06-03",
            modalities=["text", "audio"],
            voice="alloy",
        )

        # Response configuration
        self.response_configs = response_configs or {}
        self.default_response_config = default_response_config or LocalResponseConfig()

        # Connection state
        self.connected = False
        self._ws: Optional[ClientConnection] = None
        self._message_task: Optional[asyncio.Task] = None
        self._response_timings: List[Dict[str, Any]] = (
            []
        )  # Store recent response timings

        # Initialize components
        self._audio_manager = AudioManager(logger=self.logger)
        self._event_handler = EventHandlerManager(
            logger=self.logger, session_config=self.session_config
        )
        self._response_generator = ResponseGenerator(
            logger=self.logger, audio_manager=self._audio_manager
        )

        # Set up response generation callback
        self._event_handler.register_event_handler(
            "response.create", self._handle_response_create
        )

    def add_response_config(self, key: str, config: LocalResponseConfig) -> None:
        """
        Add a response configuration for a specific scenario.

        This method allows you to dynamically add response configurations
        at runtime. The configuration will be available for use in subsequent
        response generation.

        Args:
            key (str): Unique identifier for this response configuration.
                      Used to select the appropriate response during generation.
            config (LocalResponseConfig): Configuration defining how the response
                                       should be generated.

        Example:
            ```python
            mock_client.add_response_config(
                "greeting",
                LocalResponseConfig(
                    text="Hello! How can I help you?",
                    audio_file="audio/greeting.wav",
                    delay_seconds=0.03
                )
            )
            ```
        """
        self.response_configs[key] = config
        self.logger.debug(f"Added response config for key: {key}")

    def get_response_config(self, key: Optional[str] = None) -> LocalResponseConfig:
        """
        Get a response configuration by key, or return the default configuration.

        This method implements the response selection logic. If a specific key
        is provided and exists in the response configurations, it returns that
        configuration. Otherwise, it returns the default configuration.

        Args:
            key (Optional[str]): Key to look up in response configurations.
                                If None or not found, returns default config.

        Returns:
            LocalResponseConfig: The selected response configuration.

        Example:
            ```python
            # Get specific configuration
            config = mock_client.get_response_config("greeting")

            # Get default configuration
            default_config = mock_client.get_response_config()
            ```
        """
        if key and key in self.response_configs:
            return self.response_configs[key]
        return self.default_response_config

    def _determine_response_key(self, options: ResponseCreateOptions) -> Optional[str]:
        """
        Determine which response configuration to use based on conversation context.

        This method implements sophisticated response selection logic that considers:
        - User input keywords and content
        - Conversation turn count and history
        - Detected intents and entities
        - Requested modalities
        - Function call requirements
        - Response priority and selection criteria

        Args:
            options (ResponseCreateOptions): Response creation options from the client.

        Returns:
            Optional[str]: Key for the response configuration to use, or None for default.
        """
        if not self.response_configs:
            return None

        # Get conversation context
        context = self._get_conversation_context(options)

        # Score each response configuration
        scored_responses = self._score_response_configurations(context, options)

        if not scored_responses:
            return None

        # Return the highest scoring response
        best_response = max(scored_responses, key=lambda x: x[1])
        selected_key = best_response[0]

        self.logger.debug(
            f"[MOCK REALTIME] Selected response '{selected_key}' with score {best_response[1]}"
        )
        return selected_key

    def _get_conversation_context(
        self, options: ResponseCreateOptions
    ) -> ConversationContext:
        """
        Build conversation context from current session state and options.

        Args:
            options (ResponseCreateOptions): Response creation options.

        Returns:
            ConversationContext: Current conversation context.
        """
        session_state = self._event_handler.get_session_state()

        # Get or create conversation context
        context = session_state.get("conversation_context")
        if not context:
            context = ConversationContext(
                session_id=session_state["session_id"],
                conversation_id=session_state["conversation_id"],
            )

        # Update context with current information
        context.turn_count = len(context.conversation_history)

        # Analyze user input for intents and keywords
        if context.last_user_input:
            context.detected_intents = self._detect_intents(context.last_user_input)

        # Update modality preferences based on options
        if options.modalities:
            context.preferred_modalities = [
                str(modality) for modality in options.modalities
            ]

        # Update function call context
        if options.tools and options.tool_choice != "none":
            context.function_call_context = {
                "tools": options.tools,
                "tool_choice": options.tool_choice,
            }

        return context

    def _detect_intents(self, user_input: str) -> List[str]:
        """
        Detect conversation intents from user input.

        Args:
            user_input (str): User input text to analyze.

        Returns:
            List[str]: List of detected intents.
        """
        intents = []
        input_lower = user_input.lower()

        # Greeting intents
        if any(word in input_lower for word in ["hello", "hi", "hey", "greetings"]):
            intents.append("greeting")

        # Farewell intents
        if any(
            word in input_lower for word in ["goodbye", "bye", "see you", "farewell"]
        ):
            intents.append("farewell")

        # Help intents
        if any(
            word in input_lower for word in ["help", "assist", "support", "problem"]
        ):
            intents.append("help_request")

        # Question intents
        if (
            any(
                word in input_lower
                for word in ["what", "how", "why", "when", "where", "who"]
            )
            or "?" in user_input
        ):
            intents.append("question")

        # Complaint intents
        if any(
            word in input_lower
            for word in ["complaint", "issue", "problem", "wrong", "broken"]
        ):
            intents.append("complaint")

        # Thank you intents
        if any(word in input_lower for word in ["thank", "thanks", "appreciate"]):
            intents.append("gratitude")

        # Confirmation intents
        if any(word in input_lower for word in ["yes", "correct", "right", "confirm"]):
            intents.append("confirmation")

        # Denial intents
        if any(word in input_lower for word in ["no", "wrong", "incorrect", "deny"]):
            intents.append("denial")

        return intents

    def _score_response_configurations(
        self, context: ConversationContext, options: ResponseCreateOptions
    ) -> List[Tuple[str, float]]:
        """
        Score response configurations based on conversation context.

        Args:
            context (ConversationContext): Current conversation context.
            options (ResponseCreateOptions): Response creation options.

        Returns:
            List[Tuple[str, float]]: List of (response_key, score) tuples.
        """
        scored_responses = []

        for key, config in self.response_configs.items():
            score = self._calculate_response_score(config, context, options)
            if score > 0:  # Only include responses that match criteria
                scored_responses.append((key, score))

        return scored_responses

    def _calculate_response_score(
        self,
        config: LocalResponseConfig,
        context: ConversationContext,
        options: ResponseCreateOptions,
    ) -> float:
        """
        Calculate a score for a response configuration based on context match.

        Args:
            config (LocalResponseConfig): Response configuration to score.
            context (ConversationContext): Current conversation context.
            options (ResponseCreateOptions): Response creation options.

        Returns:
            float: Score for this response (0.0 = no match, higher = better match).
        """
        score = 0.0

        # Start with base priority
        if config.selection_criteria:
            score += config.selection_criteria.priority

        # Check keyword matching
        if config.selection_criteria and config.selection_criteria.required_keywords:
            if not self._check_keyword_match(
                context.last_user_input, config.selection_criteria.required_keywords
            ):
                return 0.0  # Required keywords not found
            score += 10.0

        # Check excluded keywords
        if config.selection_criteria and config.selection_criteria.excluded_keywords:
            if self._check_keyword_match(
                context.last_user_input, config.selection_criteria.excluded_keywords
            ):
                return 0.0  # Excluded keywords found

        # Check intent matching
        if config.selection_criteria and config.selection_criteria.required_intents:
            if not self._check_intent_match(
                context.detected_intents, config.selection_criteria.required_intents
            ):
                return 0.0  # Required intents not found
            score += 15.0

        # Check turn count conditions
        if config.selection_criteria:
            if (
                config.selection_criteria.min_turn_count is not None
                and context.turn_count < config.selection_criteria.min_turn_count
            ):
                return 0.0

            if (
                config.selection_criteria.max_turn_count is not None
                and context.turn_count > config.selection_criteria.max_turn_count
            ):
                return 0.0

        # Check modality requirements
        if config.selection_criteria and config.selection_criteria.required_modalities:
            if not self._check_modality_match(
                options.modalities, config.selection_criteria.required_modalities
            ):
                return 0.0  # Required modalities not available
            score += 5.0

        # Check function call requirements
        if (
            config.selection_criteria
            and config.selection_criteria.requires_function_call is not None
        ):
            has_function_call = bool(options.tools and options.tool_choice != "none")
            if config.selection_criteria.requires_function_call != has_function_call:
                return 0.0  # Function call requirement mismatch
            score += 8.0

        # Check context patterns
        if config.selection_criteria and config.selection_criteria.context_patterns:
            if self._check_context_patterns(
                context, config.selection_criteria.context_patterns
            ):
                score += 12.0

        # Bonus for exact text matches
        if (
            context.last_user_input
            and config.text.lower() in context.last_user_input.lower()
        ):
            score += 3.0

        return score

    def _check_keyword_match(
        self, user_input: Optional[str], keywords: List[str]
    ) -> bool:
        """
        Check if any keywords are present in user input.

        Args:
            user_input (Optional[str]): User input text.
            keywords (List[str]): Keywords to check for.

        Returns:
            bool: True if any keyword is found.
        """
        if not user_input:
            return False

        user_input_lower = user_input.lower()
        return any(keyword.lower() in user_input_lower for keyword in keywords)

    def _check_intent_match(
        self, detected_intents: List[str], required_intents: List[str]
    ) -> bool:
        """
        Check if any required intents are detected.

        Args:
            detected_intents (List[str]): Currently detected intents.
            required_intents (List[str]): Required intents.

        Returns:
            bool: True if any required intent is detected.
        """
        return any(intent in detected_intents for intent in required_intents)

    def _check_modality_match(
        self, available_modalities: List[Any], required_modalities: List[str]
    ) -> bool:
        """
        Check if required modalities are available.

        Args:
            available_modalities (List[str]): Available modalities.
            required_modalities (List[str]): Required modalities.

        Returns:
            bool: True if all required modalities are available.
        """
        # Convert to strings for comparison
        available_str = [str(modality) for modality in available_modalities]
        required_str = [str(modality) for modality in required_modalities]
        return all(modality in available_str for modality in required_str)

    def _check_context_patterns(
        self, context: ConversationContext, patterns: List[str]
    ) -> bool:
        """
        Check if any context patterns match the conversation context.

        Args:
            context (ConversationContext): Current conversation context.
            patterns (List[str]): Regex patterns to check.

        Returns:
            bool: True if any pattern matches.
        """
        context_text = (
            f"{context.last_user_input or ''} {' '.join(context.detected_intents)}"
        )

        for pattern in patterns:
            try:
                if re.search(pattern, context_text, re.IGNORECASE):
                    return True
            except re.error:
                self.logger.warning(f"[MOCK REALTIME] Invalid regex pattern: {pattern}")

        return False

    def update_conversation_context(self, user_input: Optional[str] = None) -> None:
        """
        Update the conversation context with new user input.

        Args:
            user_input (Optional[str]): New user input to add to context.
        """
        session_state = self._event_handler.get_session_state()

        # Get or create conversation context
        context = session_state.get("conversation_context")
        if not context:
            context = ConversationContext(
                session_id=session_state["session_id"],
                conversation_id=session_state["conversation_id"],
            )

        # Update with new user input
        if user_input:
            context.last_user_input = user_input
            context.detected_intents = self._detect_intents(user_input)

            # Add to conversation history
            context.conversation_history.append(
                {
                    "type": "user_input",
                    "text": user_input,
                    "intents": context.detected_intents,
                    "timestamp": datetime.now().isoformat(),
                }
            )

        # Update session state
        self._event_handler.update_session_state({"conversation_context": context})

    def setup_smart_response_examples(self) -> None:
        """
        Set up example response configurations demonstrating smart selection.

        This method provides examples of how to configure responses with
        different selection criteria for various conversation scenarios.
        """
        # Greeting responses (high priority, first turn only)
        self.add_response_config(
            "greeting",
            LocalResponseConfig(
                text="Hello! Welcome to our service. How can I help you today?",
                audio_file="audio/greetings/greeting_01.wav",
                delay_seconds=0.03,
                selection_criteria=ResponseSelectionCriteria(
                    required_keywords=["hello", "hi", "hey", "greetings"],
                    max_turn_count=1,
                    priority=20,
                ),
            ),
        )

        # Help request responses
        self.add_response_config(
            "help_request",
            LocalResponseConfig(
                text="I'd be happy to help! What specific issue are you experiencing?",
                audio_file="audio/help/help_01.wav",
                selection_criteria=ResponseSelectionCriteria(
                    required_intents=["help_request"], priority=15
                ),
            ),
        )

        # Complaint responses (requires multiple turns)
        self.add_response_config(
            "complaint",
            LocalResponseConfig(
                text="I understand you're having an issue. Let me help you resolve this.",
                audio_file="audio/complaints/complaint_01.wav",
                selection_criteria=ResponseSelectionCriteria(
                    required_intents=["complaint"], min_turn_count=2, priority=18
                ),
            ),
        )

        # Question responses
        self.add_response_config(
            "question",
            LocalResponseConfig(
                text="That's a great question! Let me provide you with the information you need.",
                audio_file="audio/questions/question_01.wav",
                selection_criteria=ResponseSelectionCriteria(
                    required_intents=["question"], priority=12
                ),
            ),
        )

        # Gratitude responses
        self.add_response_config(
            "gratitude",
            LocalResponseConfig(
                text="You're very welcome! I'm glad I could help.",
                audio_file="audio/gratitude/thanks_01.wav",
                selection_criteria=ResponseSelectionCriteria(
                    required_intents=["gratitude"], priority=10
                ),
            ),
        )

        # Farewell responses
        self.add_response_config(
            "farewell",
            LocalResponseConfig(
                text="Goodbye! Have a great day and feel free to contact us again if you need anything.",
                audio_file="audio/farewells/farewell_01.wav",
                selection_criteria=ResponseSelectionCriteria(
                    required_intents=["farewell"], priority=8
                ),
            ),
        )

        # Function call responses
        self.add_response_config(
            "function_call",
            LocalResponseConfig(
                text="I'll help you with that by calling the appropriate function.",
                function_call={
                    "name": "process_request",
                    "arguments": {"action": "default"},
                },
                selection_criteria=ResponseSelectionCriteria(
                    requires_function_call=True, priority=25
                ),
            ),
        )

        # Audio-only responses
        self.add_response_config(
            "audio_only",
            LocalResponseConfig(
                text="",  # No text for audio-only
                audio_file="audio/audio_only/response_01.wav",
                selection_criteria=ResponseSelectionCriteria(
                    required_modalities=["audio"],
                    excluded_keywords=["text", "type"],
                    priority=5,
                ),
            ),
        )

        # Complex pattern matching
        self.add_response_config(
            "technical_support",
            LocalResponseConfig(
                text="I can see you're experiencing a technical issue. Let me guide you through the troubleshooting process.",
                audio_file="audio/technical/tech_support_01.wav",
                selection_criteria=ResponseSelectionCriteria(
                    context_patterns=[r"error|bug|crash|broken|not working"],
                    min_turn_count=1,
                    priority=16,
                ),
            ),
        )

        # Fallback response (lowest priority)
        self.add_response_config(
            "fallback",
            LocalResponseConfig(
                text="I'm not sure I understood that. Could you please rephrase or provide more details?",
                audio_file="audio/fallback/fallback_01.wav",
                selection_criteria=ResponseSelectionCriteria(
                    priority=1  # Lowest priority
                ),
            ),
        )

        self.logger.info(
            "[MOCK REALTIME] Smart response examples configured with context-aware selection"
        )

    async def connect(self, url: str = "ws://localhost:8080") -> None:
        """
        Connect to a mock WebSocket server.

        This method establishes a WebSocket connection to the specified URL.
        After connecting, it starts the message handler and sends an initial
        session.created event to simulate the OpenAI Realtime API behavior.

        Args:
            url (str): WebSocket server URL to connect to.
                      Default: "ws://localhost:8080"

        Raises:
            websockets.exceptions.ConnectionError: If connection fails
            Exception: For other connection-related errors

        Example:
            ```python
            # Connect to default mock server
            await mock_client.connect()

            # Connect to custom server
            await mock_client.connect("ws://localhost:9000")
            ```
        """
        self.logger.info(f"[MOCK REALTIME] Connecting to {url}...")
        try:
            self._ws = await websockets.connect(url)
            self.connected = True
            self.logger.info("[MOCK REALTIME] Connected successfully")

            # Set up components with WebSocket connection
            self._event_handler.set_websocket_connection(self._ws)
            self._response_generator.set_websocket_connection(self._ws)

            # Start message handler
            self._message_task = asyncio.create_task(self._message_handler())

            # Send session created event
            await self._event_handler.send_session_created()

        except Exception as e:
            self.logger.error(f"[MOCK REALTIME] Connection failed: {e}")
            self.connected = False
            raise

    async def disconnect(self) -> None:
        """
        Disconnect from the WebSocket server.

        This method gracefully closes the WebSocket connection and updates
        the connection status. It's safe to call even if not connected.

        Example:
            ```python
            await mock_client.disconnect()
            ```
        """
        if self._message_task:
            self._message_task.cancel()
            try:
                await self._message_task
            except asyncio.CancelledError:
                pass

        if self._ws:
            try:
                await self._ws.close()
                self.logger.info("[MOCK REALTIME] Disconnected successfully")
            except Exception as e:
                self.logger.warning(f"[MOCK REALTIME] Error during disconnect: {e}")
            finally:
                self.connected = False
                self._ws = None

    async def _message_handler(self) -> None:
        """
        Handle incoming WebSocket messages.

        This method continuously listens for messages from the WebSocket
        connection and processes them using the event handler manager.
        It handles connection closure gracefully.

        The message handler:
        - Listens for incoming WebSocket messages
        - Routes messages to the event handler manager
        - Handles connection closure gracefully
        - Logs errors and warnings for debugging

        Note:
            This method runs as a background task after connection
            and continues until the connection is closed.
        """
        if not self._ws:
            return

        try:
            async for message in self._ws:
                # Decode message if it's bytes or bytearray
                if isinstance(message, (bytes, bytearray)):
                    message = message.decode("utf-8")
                elif isinstance(message, memoryview):
                    message = message.tobytes().decode("utf-8")
                await self._event_handler.handle_message(message)

        except websockets.ConnectionClosed:
            self.logger.info("[MOCK REALTIME] Connection closed")
        except Exception as e:
            self.logger.error(f"[MOCK REALTIME] Message handler error: {e}")

    async def _handle_response_create(self, data: Dict[str, Any]) -> None:
        """
        Handle response.create events and generate responses.
        Tracks and logs response generation time.
        """
        start_time = time.perf_counter()
        response_id = None
        response_key = None
        try:
            # Set up response context
            options = await self._setup_response_context(data)

            # Determine response configuration
            config = await self._prepare_response_config(options)
            response_key = self._determine_response_key(options)
            response_id = self._response_generator._active_response_id

            # Generate response based on type
            await self._generate_response(options, config)

        except Exception as e:
            self.logger.error(f"[MOCK REALTIME] Error generating response: {e}")
            await self._response_generator.send_error(
                "response_generation_failed", str(e)
            )

        finally:
            # Clean up response context
            await self._cleanup_response_context()
            end_time = time.perf_counter()
            duration = end_time - start_time
            timing_record = {
                "response_id": response_id,
                "response_key": response_key,
                "duration": duration,
                "timestamp": datetime.now().isoformat(),
            }
            self._response_timings.append(timing_record)
            self.logger.info(
                f"[METRICS] Response {response_id or ''} (key={response_key}) generated in {duration:.4f} seconds"
            )

    async def _setup_response_context(
        self, data: Dict[str, Any]
    ) -> ResponseCreateOptions:
        """
        Set up the response context and ensure proper response ID.

        This method handles the initial setup for response generation,
        including parsing options and ensuring a valid response ID exists.

        Args:
            data (Dict[str, Any]): Response creation data.

        Returns:
            ResponseCreateOptions: Parsed response creation options.

        Raises:
            Exception: If response context setup fails.
        """
        # Parse response options
        options = ResponseCreateOptions(**data.get("response", {}))

        # Get or create active response ID
        session_state = self._event_handler.get_session_state()
        active_response_id = session_state.get("active_response_id")

        if not active_response_id:
            active_response_id = await self._create_response_id()

        # Set active response ID in generator
        self._response_generator.set_active_response_id(active_response_id)

        # Simulate response generation delay
        await asyncio.sleep(0.1)

        return options

    async def _create_response_id(self) -> str:
        """
        Create a new response ID and send response.created event.

        Returns:
            str: The newly created response ID.
        """
        active_response_id = str(uuid.uuid4())
        self._event_handler.update_session_state(
            {"active_response_id": active_response_id}
        )

        # Send response.created event
        event = {
            "type": ServerEventType.RESPONSE_CREATED,
            "response": {
                "id": active_response_id,
                "created_at": int(datetime.now().timestamp() * 1000),
            },
        }
        await self._event_handler._send_event(event)

        return active_response_id

    async def _prepare_response_config(
        self, options: ResponseCreateOptions
    ) -> LocalResponseConfig:
        """
        Prepare the response configuration based on the request options.

        This method determines which response configuration to use and
        logs the selection for debugging purposes.

        Args:
            options (ResponseCreateOptions): Response creation options.

        Returns:
            LocalResponseConfig: The selected response configuration.
        """
        # Determine which response config to use
        response_key = self._determine_response_key(options)
        config = self.get_response_config(response_key)

        self.logger.info(
            f"[MOCK REALTIME] Generating response with config: {response_key or 'default'}"
        )

        return config

    async def _generate_response(
        self, options: ResponseCreateOptions, config: LocalResponseConfig
    ) -> None:
        """
        Generate the appropriate response based on options and configuration.

        This method handles the core response generation logic, including
        function calls, text responses, and audio responses.

        Args:
            options (ResponseCreateOptions): Response creation options.
            config (LocalResponseConfig): Response configuration.
        """
        # Handle function calls if tools are enabled
        if self._should_generate_function_call(options):
            await self._generate_function_call_response(options, config)
            return

        # Generate content responses based on modalities
        await self._generate_content_responses(options, config)

        # Complete the response
        await self._complete_response()

    def _should_generate_function_call(self, options: ResponseCreateOptions) -> bool:
        """
        Determine if a function call response should be generated.

        Args:
            options (ResponseCreateOptions): Response creation options.

        Returns:
            bool: True if function call should be generated.
        """
        return bool(options.tools and options.tool_choice != "none")

    async def _generate_function_call_response(
        self, options: ResponseCreateOptions, config: LocalResponseConfig
    ) -> None:
        """
        Generate a function call response.

        Args:
            options (ResponseCreateOptions): Response creation options.
            config (LocalResponseConfig): Response configuration.
        """
        await self._response_generator.generate_function_call(options, config)
        await self._response_generator.generate_response_done()

    async def _generate_content_responses(
        self, options: ResponseCreateOptions, config: LocalResponseConfig
    ) -> None:
        """
        Generate content responses (text and/or audio) based on modalities.

        Args:
            options (ResponseCreateOptions): Response creation options.
            config (LocalResponseConfig): Response configuration.
        """
        # Generate text response if requested
        if "text" in options.modalities:
            await self._response_generator.generate_text_response(options, config)

        # Generate audio response if requested
        if "audio" in options.modalities:
            await self._response_generator.generate_audio_response(options, config)

    async def _complete_response(self) -> None:
        """
        Complete the response generation by sending response.done event.
        """
        await self._response_generator.generate_response_done()

        active_response_id = self._response_generator._active_response_id
        self.logger.info(
            f"[MOCK REALTIME] Response generation completed: {active_response_id}"
        )

    async def _cleanup_response_context(self) -> None:
        """
        Clean up the response context after generation.

        This method ensures that the active response ID is cleared
        and any resources are properly released.
        """
        self._event_handler.update_session_state({"active_response_id": None})

    # Additional utility methods for advanced usage

    async def load_audio_file(self, file_path: str) -> bytes:
        """
        Load an audio file using the audio manager.

        Args:
            file_path (str): Path to the audio file to load.

        Returns:
            bytes: Audio data as bytes.
        """
        return await self._audio_manager.load_audio_file(file_path)

    def register_event_handler(self, event_type: str, handler: Callable) -> None:
        """
        Register a custom event handler.

        Args:
            event_type (str): The type of event to handle.
            handler (Callable): Async function to handle the event.
        """
        self._event_handler.register_event_handler(event_type, handler)

    async def send_error(
        self, code: str, message: str, details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Send an error event.

        Args:
            code (str): Error code.
            message (str): Error message.
            details (Optional[Dict[str, Any]]): Additional error details.
        """
        await self._response_generator.send_error(code, message, details)

    async def send_transcript_delta(self, text: str, final: bool = False) -> None:
        """
        Send a transcript delta event for generated audio.

        Args:
            text (str): Transcript text to send.
            final (bool): Whether this is the final transcript chunk.
        """
        await self._response_generator.send_transcript_delta(text, final)

    async def send_input_transcript_delta(
        self, item_id: str, text: str, final: bool = False
    ) -> None:
        """
        Send an input audio transcription delta event.

        Args:
            item_id (str): ID of the conversation item.
            text (str): Transcript text to send.
            final (bool): Whether this is the final transcript chunk.
        """
        await self._response_generator.send_input_transcript_delta(item_id, text, final)

    async def send_input_transcript_failed(
        self, item_id: str, error: Dict[str, Any]
    ) -> None:
        """
        Send an input audio transcription failed event.

        Args:
            item_id (str): ID of the conversation item.
            error (Dict[str, Any]): Error details.
        """
        await self._response_generator.send_input_transcript_failed(item_id, error)

    # Public API methods for session state and event handling

    def get_session_state(self) -> Dict[str, Any]:
        """
        Get the current session state.

        Returns:
            Dict[str, Any]: Current session state including session_id, conversation_id, etc.
        """
        return self._event_handler.get_session_state()

    def get_audio_buffer(self) -> List[bytes]:
        """
        Get the current audio buffer.

        Returns:
            List[bytes]: Current audio buffer contents.
        """
        return self._event_handler._session_state["audio_buffer"]

    def set_audio_buffer(self, audio_data: List[bytes]) -> None:
        """
        Set the audio buffer contents.

        Args:
            audio_data (List[bytes]): Audio data to set in buffer.
        """
        self._event_handler._session_state["audio_buffer"] = audio_data

    def get_active_response_id(self) -> Optional[str]:
        """
        Get the currently active response ID.

        Returns:
            Optional[str]: Active response ID or None if no active response.
        """
        return self._response_generator._active_response_id

    def set_active_response_id(self, response_id: Optional[str]) -> None:
        """
        Set the active response ID.

        Args:
            response_id (Optional[str]): Response ID to set as active.
        """
        self._response_generator._active_response_id = response_id
        self._event_handler._session_state["active_response_id"] = response_id

    async def handle_session_update(self, data: Dict[str, Any]) -> None:
        """
        Handle session update events.

        Args:
            data (Dict[str, Any]): Session update event data.
        """
        await self._event_handler._handle_session_update(data)

    async def handle_audio_append(self, data: Dict[str, Any]) -> None:
        """
        Handle audio append events.

        Args:
            data (Dict[str, Any]): Audio append event data.
        """
        await self._event_handler._handle_audio_append(data)

    async def handle_audio_commit(self, data: Dict[str, Any]) -> None:
        """
        Handle audio commit events.

        Args:
            data (Dict[str, Any]): Audio commit event data.
        """
        await self._event_handler._handle_audio_commit(data)

    async def handle_response_cancel(self, data: Dict[str, Any]) -> None:
        """
        Handle response cancel events.

        Args:
            data (Dict[str, Any]): Response cancel event data.
        """
        # Ensure the response ID is set in session state for consistency
        response_id = data.get("response_id")
        if response_id and not self._event_handler._session_state.get(
            "active_response_id"
        ):
            self._event_handler._session_state["active_response_id"] = response_id

        await self._event_handler._handle_response_cancel(data)

        # Clear the response generator's active response ID if session state is cleared
        if self._event_handler._session_state.get("active_response_id") is None:
            self._response_generator._active_response_id = None

    async def send_rate_limits(self, limits: List[Dict[str, Any]]) -> None:
        """
        Send rate limits update event.

        Args:
            limits (List[Dict[str, Any]]): Rate limits data to send.
        """
        await self._event_handler._send_event(
            {"type": ServerEventType.RATE_LIMITS_UPDATED, "rate_limits": limits}
        )

    async def send_content_part_added(self, part: Dict[str, Any]) -> None:
        """
        Send content part added event.

        Args:
            part (Dict[str, Any]): Content part data to send.
        """
        await self._response_generator._send_event(
            {"type": ServerEventType.RESPONSE_CONTENT_PART_ADDED, "part": part}
        )

    async def send_content_part_done(self, part: Dict[str, Any]) -> None:
        """
        Send content part done event.

        Args:
            part (Dict[str, Any]): Content part data to send.
        """
        await self._response_generator._send_event(
            {
                "type": ServerEventType.RESPONSE_CONTENT_PART_DONE,
                "part": part,
                "status": "completed",
            }
        )

    def get_response_timings(self) -> List[Dict[str, Any]]:
        """
        Get recent response generation timing metrics.
        Returns:
            List[Dict[str, Any]]: List of timing records with keys: response_id, response_key, duration, timestamp
        """
        return self._response_timings[-100:]  # Return last 100 timings
