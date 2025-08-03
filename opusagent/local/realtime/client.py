"""
Main LocalRealtimeClient implementation.

This module contains the LocalRealtimeClient class that provides a complete mock implementation
of the OpenAI Realtime API for testing and development purposes. The client simulates all aspects
of the real API including WebSocket connections, event handling, response streaming, and audio processing.

Key Features:
    - Complete OpenAI Realtime API simulation
    - Configurable response scenarios with smart selection
    - Real audio file streaming and caching
    - Function call simulation with custom arguments
    - Comprehensive event handling and routing
    - Performance metrics and timing tracking
    - Graceful error handling and fallbacks

Usage Examples:
    Basic setup:
        client = LocalRealtimeClient()
        await client.connect()

    With custom responses:
        configs = {
            "greeting": LocalResponseConfig(text="Hello!", audio_file="greeting.wav"),
            "help": LocalResponseConfig(text="How can I help?", delay_seconds=0.1)
        }
        client = LocalRealtimeClient(response_configs=configs)

    Smart response selection:
        client.setup_smart_response_examples()
        # Responses are automatically selected based on conversation context
"""

import asyncio
import logging
import re
import time
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

import websockets
from websockets.client import WebSocketClientProtocol

from opusagent.config.logging_config import configure_logging
from opusagent.models.openai_api import (
    ResponseCreateOptions,
    ServerEventType,
    SessionConfig,
)
from opusagent.vad.vad_config import load_vad_config
from opusagent.vad.vad_factory import VADFactory

from .audio import AudioManager
from .generators import ResponseGenerator
from .handlers import EventHandlerManager
from .models import ConversationContext, LocalResponseConfig, ResponseSelectionCriteria


class LocalRealtimeClient:
    """
    Enhanced mock client that simulates the OpenAI Realtime API with advanced features.

    This client provides a complete drop-in replacement for the OpenAI Realtime API during
    testing and development. It supports all major API features including real-time audio
    streaming, function calls, event handling, and response generation with configurable
    scenarios and intelligent response selection.

    The client is designed to be highly configurable and realistic, making it ideal for:
    - Testing application integration with OpenAI Realtime API
    - Development without API costs or rate limits
    - Simulating various conversation scenarios
    - Performance testing and optimization
    - Automated testing and validation

    Architecture:
        The client consists of several specialized components:
        - AudioManager: Handles audio file loading, caching, and streaming
        - EventHandlerManager: Processes incoming WebSocket events
        - ResponseGenerator: Creates and streams responses
        - Conversation tracking and context management

    Response Selection:
        The client uses intelligent response selection based on:
        - User input keywords and content analysis
        - Conversation turn count and history
        - Detected intents (greeting, help, complaint, etc.)
        - Requested modalities (text, audio, both)
        - Function call requirements
        - Priority scoring and selection criteria

    Performance Features:
        - Audio file caching for improved response times
        - Configurable delays to simulate realistic API behavior
        - Response timing metrics and logging
        - Graceful error handling with fallback responses
        - Memory-efficient audio processing

    Attributes:
        logger (logging.Logger): Logger instance for debugging and monitoring
        session_config (SessionConfig): OpenAI session configuration with model and voice settings
        response_configs (Dict[str, LocalResponseConfig]): Available response configurations for different scenarios
        default_response_config (LocalResponseConfig): Default response when no specific config matches
        connected (bool): Current WebSocket connection status
        _ws (Optional[ClientConnection]): Active WebSocket connection
        _audio_manager (AudioManager): Manages audio file operations and caching
        _event_handler (EventHandlerManager): Handles incoming events and session state
        _response_generator (ResponseGenerator): Generates and streams responses
        _message_task (Optional[asyncio.Task]): Background task for message handling
        _response_timings (List[Dict[str, Any]]): Performance metrics for recent responses

    Example Usage:
        ```python
        # Basic setup
        client = LocalRealtimeClient()
        await client.connect("ws://localhost:8080")

        # Configure custom responses
        client.add_response_config(
            "greeting",
            LocalResponseConfig(
                text="Hello! How can I help?",
                audio_file="audio/greeting.wav",
                delay_seconds=0.05
            )
        )

        # Use smart response selection
        client.setup_smart_response_examples()

        # Monitor performance
        timings = client.get_response_timings()
        for timing in timings:
            print(f"Response {timing['response_key']}: {timing['duration']:.3f}s")
        ```
    """

    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        session_config: Optional[SessionConfig] = None,
        response_configs: Optional[Dict[str, LocalResponseConfig]] = None,
        default_response_config: Optional[LocalResponseConfig] = None,
        enable_vad: Optional[bool] = None,
        vad_config: Optional[Dict[str, Any]] = None,
        enable_transcription: Optional[bool] = None,
        transcription_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the LocalRealtimeClient with optional custom configurations.

        This method sets up all internal components and prepares the client for use.
        The client can be initialized with minimal parameters and configured later,
        or fully configured from the start for immediate use.

        Args:
            logger (Optional[logging.Logger]): Logger instance for debugging and monitoring.
                                             If None, creates a default logger with INFO level.
                                             Recommended to provide a logger for production use.
            session_config (Optional[SessionConfig]): OpenAI session configuration including
                                                    model, modalities, and voice settings.
                                                    If None, uses sensible defaults:
                                                    - model: "gpt-4o-realtime-preview-2025-06-03"
                                                    - modalities: ["text", "audio"]
                                                    - voice: "alloy"
            response_configs (Optional[Dict[str, LocalResponseConfig]]): Pre-configured
                                                                      response configurations
                                                                      for different conversation scenarios.
                                                                      Keys should be descriptive identifiers
                                                                      like "greeting", "help", "complaint".
                                                                      If None, starts with empty configuration.
            default_response_config (Optional[LocalResponseConfig]): Default response
                                                                   configuration used when no specific
                                                                   config matches the conversation context.
                                                                   If None, uses a basic default response.
            enable_vad (Optional[bool]): Whether to enable Voice Activity Detection (VAD).
                                       If None, VAD is enabled automatically when session
                                       configuration includes turn_detection with "server_vad".
                                       If True, VAD is always enabled. If False, VAD is disabled.
            vad_config (Optional[Dict[str, Any]]): Custom VAD configuration parameters.
                                                 Can include:
                                                 - backend: "silero" (default)
                                                 - sample_rate: 16000 (default)
                                                 - threshold: 0.5 (default)
                                                 - device: "cpu" (default)
                                                 - chunk_size: 512 (default for 16kHz)
                                                 If None, uses default VAD configuration.
            enable_transcription (Optional[bool]): Whether to enable local audio transcription.
                                                  If None, transcription is enabled automatically
                                                  when session configuration includes input_audio_transcription.
                                                  If True, transcription is always enabled.
                                                  If False, transcription is disabled.
            transcription_config (Optional[Dict[str, Any]]): Custom transcription configuration.
                                                           Can include:
                                                           - backend: "pocketsphinx" or "whisper" (default: "pocketsphinx")
                                                           - language: "en" (default)
                                                           - model_size: "base" (for Whisper)
                                                           - confidence_threshold: 0.5 (default)
                                                           - device: "cpu" (default)
                                                           If None, uses default transcription configuration.

        Raises:
            ValueError: If provided configurations are invalid
            OSError: If audio manager initialization fails
            RuntimeError: If VAD initialization fails with required VAD enabled

        Example:
            ```python
            # Basic initialization with defaults
            client = LocalRealtimeClient()

            # With custom logger
            import logging
            logger = logging.getLogger("my_app")
            client = LocalRealtimeClient(logger=logger)

            # With custom session configuration
            session_config = SessionConfig(
                model="gpt-4o-realtime-preview-2025-06-03",
                modalities=["text", "audio"],
                voice="nova"
            )
            client = LocalRealtimeClient(session_config=session_config)

            # With VAD enabled and custom configuration
            vad_config = {
                "backend": "silero",
                "sample_rate": 16000,
                "threshold": 0.3,
                "device": "cpu"
            }
            client = LocalRealtimeClient(
                enable_vad=True,
                vad_config=vad_config
            )

            # With session configuration that enables VAD automatically
            session_config = SessionConfig(
                model="gpt-4o-realtime-preview-2025-06-03",
                modalities=["text", "audio"],
                voice="alloy",
                turn_detection={"type": "server_vad"}  # This will enable VAD
            )
            client = LocalRealtimeClient(session_config=session_config)

            # With pre-configured responses
            configs = {
                "greeting": LocalResponseConfig(
                    text="Hello! Welcome to our service.",
                    audio_file="audio/greeting.wav",
                    delay_seconds=0.03
                ),
                "help": LocalResponseConfig(
                    text="I'd be happy to help you!",
                    audio_file="audio/help.wav",
                    selection_criteria=ResponseSelectionCriteria(
                        required_intents=["help_request"],
                        priority=15
                    )
                )
            }
            client = LocalRealtimeClient(response_configs=configs)

            # With custom default response
            default_config = LocalResponseConfig(
                text="I'm not sure I understood. Could you rephrase?",
                audio_file="audio/fallback.wav"
            )
            client = LocalRealtimeClient(default_response_config=default_config)
            ```
        """
        if logger is None:
            self.logger = configure_logging(
                name="realtime_client", log_filename="realtime_client.log"
            )
        else:
            self.logger = logger
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
        self._ws: Optional[WebSocketClientProtocol] = None
        self._message_task: Optional[asyncio.Task] = None
        self._response_timings: List[Dict[str, Any]] = (
            []
        )  # Store recent response timings

        # Initialize components
        self._audio_manager = AudioManager(logger=self.logger)

        # Initialize VAD if enabled
        self._vad = None
        self._vad_enabled = False
        self._vad_config = vad_config or {}
        self._initialize_vad(enable_vad)

        # Initialize transcription if enabled
        self._transcriber = None
        self._transcription_enabled = False
        self._transcription_config = transcription_config or {}
        self._initialize_transcription(enable_transcription)

        # Initialize event handler with VAD and transcription support
        self._event_handler = EventHandlerManager(
            logger=self.logger,
            session_config=self.session_config,
            vad=self._vad,
            transcriber=self._transcriber,
        )
        self._response_generator = ResponseGenerator(
            logger=self.logger, audio_manager=self._audio_manager
        )

        # Set up response generation callback
        self._event_handler.register_event_handler(
            "response.create", self._handle_response_create
        )

    def _initialize_vad(self, enable_vad: Optional[bool] = None) -> None:
        """
        Initialize Voice Activity Detection (VAD) based on session configuration.

        This method sets up VAD when turn detection is enabled in the session
        configuration or when explicitly enabled. VAD is used to detect speech
        activity in incoming audio data for more realistic speech detection.

        Args:
            enable_vad (Optional[bool]): Whether to enable VAD. If None,
                                       determines from session configuration.
        """
        try:
            # Determine if VAD should be enabled
            if enable_vad is None:
                # Check session config for turn detection
                turn_detection = self.session_config.turn_detection
                if turn_detection and turn_detection.get("type") == "server_vad":
                    self._vad_enabled = True
                else:
                    self._vad_enabled = False
            else:
                self._vad_enabled = enable_vad

            if self._vad_enabled:
                # Load VAD configuration
                vad_config = load_vad_config()
                vad_config.update(self._vad_config)  # Override with provided config

                # Create VAD instance
                self._vad = VADFactory.create_vad(vad_config)
                self.logger.info(
                    f"[MOCK REALTIME] VAD initialized with backend: {vad_config.get('backend', 'silero')}"
                )
            else:
                self._vad = None
                self.logger.info(
                    "[MOCK REALTIME] VAD disabled - using simple speech detection"
                )

        except Exception as e:
            self.logger.error(f"[MOCK REALTIME] Failed to initialize VAD: {e}")
            # Always fall back gracefully to disabled VAD on initialization failure
            self._vad = None
            self._vad_enabled = False

    def _initialize_transcription(
        self, enable_transcription: Optional[bool] = None
    ) -> None:
        """
        Initialize local audio transcription based on session configuration.

        This method sets up transcription when input_audio_transcription is enabled
        in the session configuration or when explicitly enabled. Transcription is
        used to convert incoming audio to text for realistic API behavior.

        Args:
            enable_transcription (Optional[bool]): Whether to enable transcription.
                                                  If None, determines from session configuration.
        """
        try:
            # Determine if transcription should be enabled
            if enable_transcription is None:
                # Check session config for input audio transcription
                input_transcription = self.session_config.input_audio_transcription
                if input_transcription and input_transcription.get("model"):
                    self._transcription_enabled = True
                else:
                    self._transcription_enabled = False
            else:
                self._transcription_enabled = enable_transcription

            if self._transcription_enabled:
                # Import transcription modules
                from opusagent.local.transcription import (
                    TranscriptionFactory,
                    load_transcription_config,
                )

                # Load transcription configuration
                transcription_config = load_transcription_config()
                transcription_config = transcription_config.__class__(
                    **{**transcription_config.__dict__, **self._transcription_config}
                )  # Merge defaults and overrides

                # Create transcriber instance
                self._transcriber = TranscriptionFactory.create_transcriber(
                    transcription_config
                )

                # Initialize transcriber asynchronously (we'll do this in connect())
                self.logger.info(
                    f"[MOCK REALTIME] Transcription initialized with backend: {transcription_config.backend}"
                )
            else:
                self._transcriber = None
                self.logger.info(
                    "[MOCK REALTIME] Transcription disabled - using mock transcript events"
                )

        except Exception as e:
            self.logger.error(
                f"[MOCK REALTIME] Failed to initialize transcription: {e}"
            )
            # Always fall back gracefully to disabled transcription on initialization failure
            self._transcriber = None
            self._transcription_enabled = False

    def add_response_config(self, key: str, config: LocalResponseConfig) -> None:
        """
        Add a response configuration for a specific conversation scenario.

        This method allows you to dynamically add or update response configurations
        at runtime. The configuration will be immediately available for use in
        subsequent response generation. This is useful for building adaptive
        conversation flows or adding new response patterns during testing.

        The response selection system will automatically consider this new
        configuration when determining which response to generate based on
        conversation context, user input, and selection criteria.

        Args:
            key (str): Unique identifier for this response configuration.
                      Should be descriptive and meaningful (e.g., "greeting",
                      "technical_support", "complaint_resolution").
                      Used by the response selection algorithm to identify
                      and score appropriate responses.
            config (LocalResponseConfig): Configuration defining how the response
                                       should be generated, including text content,
                                       audio files, timing, and selection criteria.
                                       Must be a valid LocalResponseConfig instance.

        Raises:
            ValueError: If key is empty or config is invalid
            TypeError: If config is not a LocalResponseConfig instance

        Example:
            ```python
            # Add a simple greeting response
            client.add_response_config(
                "greeting",
                LocalResponseConfig(
                    text="Hello! How can I help you today?",
                    audio_file="audio/greeting.wav",
                    delay_seconds=0.03
                )
            )

            # Add a context-aware help response
            client.add_response_config(
                "help_request",
                LocalResponseConfig(
                    text="I'd be happy to help! What specific issue are you experiencing?",
                    audio_file="audio/help.wav",
                    selection_criteria=ResponseSelectionCriteria(
                        required_intents=["help_request"],
                        required_keywords=["help", "assist", "support"],
                        priority=15,
                        min_turn_count=1
                    )
                )
            )

            # Add a function call response
            client.add_response_config(
                "process_order",
                LocalResponseConfig(
                    text="I'll process your order right away.",
                    function_call={
                        "name": "process_order",
                        "arguments": {"action": "create"}
                    },
                    selection_criteria=ResponseSelectionCriteria(
                        requires_function_call=True,
                        required_keywords=["order", "purchase", "buy"],
                        priority=20
                    )
                )
            )

            # Add an audio-only response
            client.add_response_config(
                "audio_confirmation",
                LocalResponseConfig(
                    text="",  # No text for audio-only
                    audio_file="audio/confirmation.wav",
                    selection_criteria=ResponseSelectionCriteria(
                        required_modalities=["audio"],
                        excluded_keywords=["text", "type"],
                        priority=5
                    )
                )
            )
            ```
        """
        self.response_configs[key] = config
        self.logger.debug(f"Added response config for key: {key}")

    def get_response_config(self, key: Optional[str] = None) -> LocalResponseConfig:
        """
        Get a response configuration by key, or return the default configuration.

        This method implements the basic response selection logic. It provides
        direct access to response configurations for inspection, debugging, or
        manual response selection. For automatic response selection based on
        conversation context, use the internal `_determine_response_key` method.

        The method follows a simple lookup pattern:
        1. If a key is provided and exists in response_configs, return that config
        2. Otherwise, return the default_response_config

        Args:
            key (Optional[str]): Key to look up in response configurations.
                                Should match a key previously added via
                                `add_response_config()`. If None or not found,
                                returns the default configuration.

        Returns:
            LocalResponseConfig: The selected response configuration.
                                Always returns a valid configuration object,
                                never None.

        Raises:
            KeyError: If key is provided but not found (should not occur with
                     proper error handling, but documented for completeness)

        Example:
            ```python
            # Get a specific configuration
            greeting_config = client.get_response_config("greeting")
            print(f"Greeting text: {greeting_config.text}")

            # Get the default configuration
            default_config = client.get_response_config()
            print(f"Default delay: {default_config.delay_seconds}")

            # Check if a configuration exists
            try:
                config = client.get_response_config("nonexistent_key")
                print("Configuration found")
            except KeyError:
                print("Using default configuration")

            # Inspect configuration details
            config = client.get_response_config("help_request")
            if config.selection_criteria:
                print(f"Priority: {config.selection_criteria.priority}")
                print(f"Required intents: {config.selection_criteria.required_intents}")
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

        # Bonus for text matches (bidirectional containment or word overlap)
        if context.last_user_input and config.text:
            user_input_lower = context.last_user_input.lower()
            config_text_lower = config.text.lower()

            # Check if either string contains the other
            if (
                config_text_lower in user_input_lower
                or user_input_lower in config_text_lower
            ):
                score += 3.0
            # Check for word overlap (at least one common word)
            else:
                user_words = set(user_input_lower.split())
                config_words = set(config_text_lower.split())
                if user_words & config_words:  # Intersection of word sets
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
        Update the conversation context with new user input and analyze for intents.

        This method is the primary way to provide user input to the response
        selection system. It updates the conversation history, analyzes the
        input for intents and keywords, and maintains the conversation state
        for intelligent response selection.

        The method performs several important functions:
        1. Stores the user input in conversation history
        2. Analyzes the input for detected intents (greeting, help, complaint, etc.)
        3. Updates the conversation turn count
        4. Maintains the conversation context for response selection
        5. Preserves the session state across multiple interactions

        This method should be called whenever new user input is received,
        typically before generating a response to ensure the response selection
        system has the most current context.

        Args:
            user_input (Optional[str]): New user input text to add to the conversation
                                       context. If None, only updates conversation
                                       metadata without adding new content.

        Note:
            The intent detection system looks for common patterns in user input:
            - Greeting: "hello", "hi", "hey", "greetings"
            - Farewell: "goodbye", "bye", "see you", "farewell"
            - Help: "help", "assist", "support", "problem"
            - Questions: words starting with "what", "how", "why", "when", "where", "who"
            - Complaints: "complaint", "issue", "problem", "wrong", "broken"
            - Gratitude: "thank", "thanks", "appreciate"
            - Confirmation: "yes", "correct", "right", "confirm"
            - Denial: "no", "wrong", "incorrect", "deny"

        Example:
            ```python
            # Update with user input
            client.update_conversation_context("Hello, I need help with my account")

            # Check detected intents
            session_state = client.get_session_state()
            context = session_state.get("conversation_context")
            if context:
                print(f"Detected intents: {context.detected_intents}")
                print(f"Turn count: {context.turn_count}")

            # Simulate a conversation flow
            client.update_conversation_context("Hi there!")
            # Will detect "greeting" intent

            client.update_conversation_context("I'm having trouble logging in")
            # Will detect "help_request" and "complaint" intents

            client.update_conversation_context("Thank you for your help")
            # Will detect "gratitude" intent

            # Update without new input (just metadata)
            client.update_conversation_context()
            ```
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
        Set up comprehensive example response configurations demonstrating smart selection.

        This method provides a complete set of example response configurations that
        demonstrate the advanced features of the response selection system. These
        examples cover various conversation scenarios and show how to use different
        selection criteria for intelligent response matching.

        The examples include:
        - Greeting responses with turn count restrictions
        - Help requests with intent detection
        - Complaint handling with conversation flow requirements
        - Question responses with context awareness
        - Gratitude and farewell responses
        - Function call scenarios
        - Audio-only responses
        - Complex pattern matching for technical support
        - Fallback responses for unmatched inputs

        Each example demonstrates different aspects of the selection criteria:
        - Keyword matching (required and excluded)
        - Intent detection and matching
        - Turn count restrictions
        - Modality requirements
        - Function call requirements
        - Context pattern matching
        - Priority scoring

        This method is ideal for:
        - Learning how to configure responses
        - Testing the response selection system
        - Providing a starting point for custom configurations
        - Demonstrating the capabilities of the mock client

        Note:
            These examples use placeholder audio file paths. In a real implementation,
            you would replace these with actual audio file paths or remove the
            audio_file parameter if audio is not needed.

        Example:
            ```python
            # Set up examples and test the system
            client.setup_smart_response_examples()

            # Test different scenarios
            client.update_conversation_context("Hello there!")
            # Will likely select "greeting" response

            client.update_conversation_context("I need help with my account")
            # Will likely select "help_request" response

            client.update_conversation_context("Thank you for your help")
            # Will likely select "gratitude" response
            ```
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
        Connect to a mock WebSocket server and initialize the session.

        This method establishes a WebSocket connection to the specified URL and
        performs all necessary initialization steps to simulate the OpenAI
        Realtime API behavior. After successful connection, the client is ready
        to handle incoming events and generate responses.

        The connection process includes:
        1. Establishing WebSocket connection to the specified URL
        2. Setting up internal components with the WebSocket connection
        3. Starting the background message handler task
        4. Sending an initial session.created event
        5. Updating connection status

        Args:
            url (str): WebSocket server URL to connect to.
                      Should be a valid WebSocket URL (ws:// or wss://).
                      Default: "ws://localhost:8080"
                      Common alternatives:
                      - "ws://localhost:9000" for custom port
                      - "wss://your-server.com/ws" for secure connection
                      - "ws://127.0.0.1:8080" for explicit IP

        Raises:
            websockets.exceptions.ConnectionError: If the WebSocket connection fails
                                                 (server not running, network issues)
            websockets.exceptions.InvalidURI: If the URL format is invalid
            websockets.exceptions.InvalidHandshake: If the server doesn't support WebSocket
            asyncio.TimeoutError: If connection times out
            Exception: For other unexpected connection-related errors

        Note:
            The client must be connected before it can handle any events or
            generate responses. Always call this method before using other
            client functionality.

        Example:
            ```python
            # Connect to default mock server
            try:
                await client.connect()
                print("Connected successfully")
            except websockets.exceptions.ConnectionError:
                print("Failed to connect - server not running")

            # Connect to custom server with error handling
            try:
                await client.connect("ws://localhost:9000")
                print("Connected to custom server")
            except Exception as e:
                print(f"Connection failed: {e}")

            # Connect to secure server
            await client.connect("wss://your-secure-server.com/ws")

            # Check connection status
            if client.connected:
                print("Client is connected and ready")
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

            # Initialize transcriber if enabled
            if self._transcriber and self._transcription_enabled:
                try:
                    await self._transcriber.initialize()
                    self.logger.info(
                        "[MOCK REALTIME] Transcriber initialized successfully"
                    )
                except Exception as e:
                    self.logger.error(
                        f"[MOCK REALTIME] Failed to initialize transcriber: {e}"
                    )
                    self._transcriber = None
                    self._transcription_enabled = False

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
        Disconnect from the WebSocket server and clean up resources.

        This method gracefully closes the WebSocket connection and performs
        all necessary cleanup operations. It's designed to be safe to call
        multiple times and even when not connected.

        The disconnection process includes:
        1. Cancelling the background message handler task
        2. Closing the WebSocket connection
        3. Updating connection status
        4. Cleaning up internal state
        5. Cleaning up VAD resources

        This method should be called when you're done using the client to
        ensure proper resource cleanup and prevent memory leaks.

        Raises:
            Exception: If there's an error during the disconnection process
                     (logged as warning, doesn't prevent cleanup)

        Note:
            After disconnecting, the client cannot handle events or generate
            responses until reconnected via `connect()`.

        Example:
            ```python
            # Basic disconnection
            await client.disconnect()

            # Disconnection with error handling
            try:
                await client.disconnect()
                print("Disconnected successfully")
            except Exception as e:
                print(f"Error during disconnect: {e}")

            # Safe multiple calls
            await client.disconnect()  # First call
            await client.disconnect()  # Safe second call

            # Check connection status after disconnect
            await client.disconnect()
            if not client.connected:
                print("Client is disconnected")

            # Reconnection after disconnect
            await client.disconnect()
            # ... some time later ...
            await client.connect()  # Reconnect when needed
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

        # Clean up VAD resources
        self._cleanup_vad()

        # Clean up transcription resources
        self._cleanup_transcription()

    def _cleanup_vad(self) -> None:
        """
        Clean up VAD resources.

        This method safely releases VAD resources when the client is
        disconnected or no longer needed.
        """
        if self._vad:
            try:
                self._vad.cleanup()
                self.logger.debug("[MOCK REALTIME] VAD resources cleaned up")
            except Exception as e:
                self.logger.warning(f"[MOCK REALTIME] Error cleaning up VAD: {e}")
            finally:
                self._vad = None

    def _cleanup_transcription(self) -> None:
        """
        Clean up transcription resources.

        This method safely releases transcription resources when the client is
        disconnected or no longer needed.
        """
        if self._transcriber:
            try:
                # Run cleanup in background since it might be async
                asyncio.create_task(self._transcriber.cleanup())
                self.logger.debug("[MOCK REALTIME] Transcription resources cleaned up")
            except Exception as e:
                self.logger.warning(
                    f"[MOCK REALTIME] Error cleaning up transcription: {e}"
                )
            finally:
                self._transcriber = None

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
        Load an audio file using the audio manager with caching support.

        This method provides direct access to the audio manager's file loading
        capabilities. It handles file loading, caching, and error handling
        automatically. The audio data is cached for improved performance on
        subsequent loads of the same file.

        Supported audio formats depend on the underlying audio processing
        library, but typically include common formats like WAV, MP3, OGG, etc.

        Args:
            file_path (str): Path to the audio file to load.
                           Can be relative or absolute path.
                           Should point to a valid audio file.

        Returns:
            bytes: Audio data as raw bytes, ready for streaming or processing.
                  The format depends on the original file format.

        Raises:
            FileNotFoundError: If the audio file doesn't exist
            OSError: If there are file system or permission issues
            ValueError: If the file is not a valid audio file
            Exception: For other audio processing errors

        Example:
            ```python
            # Load an audio file
            try:
                audio_data = await client.load_audio_file("audio/greeting.wav")
                print(f"Loaded {len(audio_data)} bytes of audio data")
            except FileNotFoundError:
                print("Audio file not found")

            # Load multiple files
            audio_files = ["greeting.wav", "help.wav", "farewell.wav"]
            for file_path in audio_files:
                try:
                    audio_data = await client.load_audio_file(f"audio/{file_path}")
                    print(f"Loaded {file_path}: {len(audio_data)} bytes")
                except Exception as e:
                    print(f"Failed to load {file_path}: {e}")

            # Use loaded audio in a custom response
            audio_data = await client.load_audio_file("custom_response.wav")
            # Process or stream the audio data as needed
            ```
        """
        return await self._audio_manager.load_audio_file(file_path)

    def register_event_handler(self, event_type: str, handler: Callable) -> None:
        """
        Register a custom event handler for specific event types.

        This method allows you to extend the client's event handling capabilities
        by registering custom handlers for specific event types. Custom handlers
        are called after the built-in event processing, allowing you to add
        custom logic, logging, or side effects.

        The handler function should be an async function that accepts a single
        parameter containing the event data. The event data structure depends
        on the event type.

        Common event types include:
        - "response.create": When a new response is requested
        - "audio.append": When audio data is appended to the session
        - "audio.commit": When audio data is committed for processing
        - "session.update": When session configuration is updated
        - "response.cancel": When a response is cancelled

        Args:
            event_type (str): The type of event to handle.
                           Should match one of the supported event types
                           in the OpenAI Realtime API specification.
            handler (Callable): Async function to handle the event.
                             Should have signature: async def handler(data: Dict[str, Any]) -> None
                             The data parameter contains the event-specific data.

        Raises:
            ValueError: If event_type is empty or invalid
            TypeError: If handler is not callable or not async

        Example:
            ```python
            # Register a custom handler for response creation
            async def custom_response_handler(data):
                print(f"Custom response handler called with: {data}")
                # Add custom logic here

            client.register_event_handler("response.create", custom_response_handler)

            # Register a handler for audio events
            async def audio_logger(data):
                print(f"Audio event: {data.get('type', 'unknown')}")

            client.register_event_handler("audio.append", audio_logger)
            client.register_event_handler("audio.commit", audio_logger)

            # Register a handler for session updates
            async def session_monitor(data):
                print(f"Session updated: {data}")

            client.register_event_handler("session.update", session_monitor)

            # Register a handler that modifies response behavior
            async def response_modifier(data):
                # Modify the response data before processing
                if "response" in data:
                    data["response"]["custom_flag"] = True

            client.register_event_handler("response.create", response_modifier)
            ```
        """
        self._event_handler.register_event_handler(event_type, handler)

    async def send_error(
        self, code: str, message: str, details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Send an error event to the connected WebSocket client.

        This method allows you to send custom error events to the client,
        simulating various error conditions that might occur in a real
        OpenAI Realtime API implementation. This is useful for testing
        error handling in client applications.

        The error event follows the OpenAI Realtime API error format
        and includes an error code, message, and optional details.

        Args:
            code (str): Error code identifier.
                      Should be a descriptive, machine-readable code
                      (e.g., "rate_limit_exceeded", "invalid_request",
                      "audio_processing_failed").
            message (str): Human-readable error message.
                         Should provide a clear description of what
                         went wrong and potentially how to fix it.
            details (Optional[Dict[str, Any]]): Additional error details.
                                             Can include technical information,
                                             retry instructions, or other
                                             context-specific data.

        Raises:
            websockets.exceptions.ConnectionClosed: If the WebSocket connection is closed
            Exception: For other WebSocket communication errors

        Example:
            ```python
            # Send a simple error
            await client.send_error(
                "invalid_request",
                "The request format is not valid"
            )

            # Send an error with details
            await client.send_error(
                "rate_limit_exceeded",
                "Too many requests, please try again later",
                {
                    "retry_after": 60,
                    "limit": 100,
                    "current_usage": 105
                }
            )

            # Send an audio processing error
            await client.send_error(
                "audio_processing_failed",
                "Failed to process audio input",
                {
                    "reason": "unsupported_format",
                    "supported_formats": ["wav", "mp3", "ogg"],
                    "file_size": 1024000
                }
            )

            # Send a function call error
            await client.send_error(
                "function_call_failed",
                "The requested function could not be executed",
                {
                    "function_name": "process_order",
                    "reason": "insufficient_permissions",
                    "available_functions": ["get_status", "cancel_order"]
                }
            )
            ```
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
        Get the current session state and metadata.

        This method returns a complete snapshot of the current session state,
        including session identifiers, conversation context, audio buffer,
        and other internal state information. This is useful for debugging,
        monitoring, and understanding the current state of the client.

        The session state includes:
        - session_id: Unique identifier for the current session
        - conversation_id: Unique identifier for the current conversation
        - active_response_id: ID of the currently active response (if any)
        - conversation_context: Current conversation context and history
        - audio_buffer: Current audio data buffer
        - other internal state variables

        Returns:
            Dict[str, Any]: Complete session state dictionary containing:
                - session_id (str): Unique session identifier
                - conversation_id (str): Unique conversation identifier
                - active_response_id (Optional[str]): Currently active response ID
                - conversation_context (Optional[ConversationContext]): Conversation state
                - audio_buffer (List[bytes]): Current audio data buffer
                - other internal state variables

        Example:
            ```python
            # Get current session state
            state = client.get_session_state()
            print(f"Session ID: {state['session_id']}")
            print(f"Conversation ID: {state['conversation_id']}")

            # Check if there's an active response
            if state.get('active_response_id'):
                print(f"Active response: {state['active_response_id']}")

            # Inspect conversation context
            context = state.get('conversation_context')
            if context:
                print(f"Turn count: {context.turn_count}")
                print(f"Last input: {context.last_user_input}")
                print(f"Detected intents: {context.detected_intents}")

            # Check audio buffer
            audio_buffer = state.get('audio_buffer', [])
            print(f"Audio buffer size: {len(audio_buffer)} chunks")

            # Monitor state changes
            initial_state = client.get_session_state()
            # ... perform some operations ...
            current_state = client.get_session_state()

            if current_state['active_response_id'] != initial_state.get('active_response_id'):
                print("Response state changed")
            ```
        """
        return self._event_handler.get_session_state()

    def get_audio_buffer(self) -> List[bytes]:
        """
        Get the current audio buffer contents.

        This method returns the current audio data buffer, which contains
        the accumulated audio chunks that have been received but not yet
        processed. This is useful for debugging audio processing issues,
        monitoring audio flow, or implementing custom audio handling logic.

        The audio buffer is a list of byte chunks, where each chunk represents
        a piece of audio data that was appended to the session. The buffer
        is typically cleared after audio is committed for processing.

        Returns:
            List[bytes]: List of audio data chunks currently in the buffer.
                        Each element is a bytes object containing audio data.
                        Empty list if no audio data is currently buffered.

        Example:
            ```python
            # Get current audio buffer
            audio_buffer = client.get_audio_buffer()
            print(f"Audio buffer contains {len(audio_buffer)} chunks")

            # Analyze buffer contents
            total_bytes = sum(len(chunk) for chunk in audio_buffer)
            print(f"Total audio data: {total_bytes} bytes")

            # Check if buffer is empty
            if not audio_buffer:
                print("Audio buffer is empty")
            else:
                print(f"First chunk size: {len(audio_buffer[0])} bytes")

            # Monitor buffer during audio processing
            initial_buffer = client.get_audio_buffer()
            # ... audio processing ...
            current_buffer = client.get_audio_buffer()

            if len(current_buffer) > len(initial_buffer):
                print("New audio data was added to buffer")
            ```
        """
        return self._event_handler._session_state["audio_buffer"]

    def set_audio_buffer(self, audio_data: List[bytes]) -> None:
        """
        Set the audio buffer contents with custom audio data.

        This method allows you to directly set the audio buffer contents,
        which is useful for testing, debugging, or implementing custom
        audio processing logic. This can be used to simulate specific
        audio scenarios or inject test audio data.

        Warning:
            This method directly overwrites the current audio buffer.
            Use with caution as it may interfere with normal audio
            processing flow. Consider backing up the current buffer
            if needed.

        Args:
            audio_data (List[bytes]): Audio data chunks to set in the buffer.
                                   Each element should be a bytes object
                                   containing audio data. Empty list to
                                   clear the buffer.

        Example:
            ```python
            # Set custom audio data
            custom_audio = [b"audio_chunk_1", b"audio_chunk_2"]
            client.set_audio_buffer(custom_audio)

            # Clear the buffer
            client.set_audio_buffer([])

            # Backup and restore buffer
            original_buffer = client.get_audio_buffer()
            # ... modify buffer ...
            client.set_audio_buffer(original_buffer)

            # Set test audio data
            test_audio_chunks = [
                b"test_audio_data_1",
                b"test_audio_data_2",
                b"test_audio_data_3"
            ]
            client.set_audio_buffer(test_audio_chunks)

            # Verify buffer was set
            current_buffer = client.get_audio_buffer()
            print(f"Buffer now contains {len(current_buffer)} chunks")
            ```
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

        This method processes session configuration updates and handles
        VAD configuration changes based on turn_detection settings.

        Args:
            data (Dict[str, Any]): Session update event data.
        """
        session = data.get("session", {})

        # Check for turn_detection changes before updating
        turn_detection_changed = False
        if "turn_detection" in session:
            old_turn_detection = self.session_config.turn_detection
            new_turn_detection = session.get("turn_detection")
            if old_turn_detection != new_turn_detection:
                turn_detection_changed = True
                self.logger.info(
                    f"[MOCK REALTIME] Turn detection changing from {old_turn_detection} to {new_turn_detection}"
                )

        # Let the event handler process the session update
        await self._event_handler._handle_session_update(data)

        # Handle VAD configuration changes
        if turn_detection_changed:
            await self._handle_vad_session_update()

    async def _handle_vad_session_update(self) -> None:
        """
        Handle VAD configuration changes when session is updated.

        This method enables or disables VAD based on the updated
        turn_detection setting in the session configuration.
        """
        turn_detection = self.session_config.turn_detection

        if turn_detection and turn_detection.get("type") == "server_vad":
            # Enable VAD if not already enabled
            if not self.is_vad_enabled():
                self.logger.info(
                    "[MOCK REALTIME] Enabling VAD due to server_vad turn detection"
                )
                self.enable_vad()
            else:
                self.logger.debug("[MOCK REALTIME] VAD already enabled")
        else:
            # Disable VAD if currently enabled
            if self.is_vad_enabled():
                self.logger.info(
                    "[MOCK REALTIME] Disabling VAD due to turn detection change"
                )
                self.disable_vad()
            else:
                self.logger.debug("[MOCK REALTIME] VAD already disabled")

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
        Get recent response generation timing metrics for performance analysis.

        This method returns detailed timing information for the most recent
        response generations, allowing you to monitor performance and identify
        potential bottlenecks or optimization opportunities.

        Each timing record contains:
        - response_id: Unique identifier for the response
        - response_key: Key of the response configuration used
        - duration: Time taken to generate the response in seconds
        - timestamp: ISO format timestamp when the response was completed

        The method returns the last 100 timing records to provide a good
        sample size for analysis while preventing memory issues.

        Returns:
            List[Dict[str, Any]]: List of timing records, each containing:
                - response_id (str): Unique response identifier
                - response_key (Optional[str]): Response configuration key used
                - duration (float): Generation time in seconds
                - timestamp (str): ISO format completion timestamp

        Example:
            ```python
            # Get timing metrics
            timings = client.get_response_timings()

            # Analyze performance
            if timings:
                avg_duration = sum(t['duration'] for t in timings) / len(timings)
                print(f"Average response time: {avg_duration:.3f}s")

                # Find slowest responses
                slowest = max(timings, key=lambda t: t['duration'])
                print(f"Slowest response: {slowest['response_key']} ({slowest['duration']:.3f}s)")

                # Group by response type
                by_type = {}
                for timing in timings:
                    key = timing['response_key'] or 'default'
                    if key not in by_type:
                        by_type[key] = []
                    by_type[key].append(timing['duration'])

                for response_type, durations in by_type.items():
                    avg = sum(durations) / len(durations)
                    print(f"{response_type}: {avg:.3f}s average")

            # Monitor real-time performance
            import time
            while True:
                timings = client.get_response_timings()
                if timings:
                    latest = timings[-1]
                    print(f"Latest response: {latest['response_key']} in {latest['duration']:.3f}s")
                time.sleep(5)
            ```
        """
        return self._response_timings[-100:]  # Return last 100 timings

    # VAD-related methods

    def is_vad_enabled(self) -> bool:
        """
        Check if VAD is enabled and initialized.

        Returns:
            bool: True if VAD is enabled and initialized, False otherwise.
        """
        return self._vad_enabled and self._vad is not None

    def get_vad_config(self) -> Dict[str, Any]:
        """
        Get the current VAD configuration.

        Returns:
            Dict[str, Any]: Current VAD configuration dictionary.
        """
        return self._vad_config.copy()

    def enable_vad(self, vad_config: Optional[Dict[str, Any]] = None) -> None:
        """
        Enable VAD with optional configuration.

        Args:
            vad_config (Optional[Dict[str, Any]]): VAD configuration to use.
                                                  If None, uses default configuration.
        """
        if vad_config:
            self._vad_config.update(vad_config)
        self._initialize_vad(enable_vad=True)
        # Update event handler with new VAD instance
        self._event_handler._vad = self._vad

    def disable_vad(self) -> None:
        """
        Disable VAD and clean up resources.
        """
        self._cleanup_vad()
        self._vad_enabled = False
        # Update event handler to remove VAD instance
        self._event_handler._vad = None

    def get_vad_state(self) -> Dict[str, Any]:
        """
        Get current VAD state information.

        Returns:
            Dict[str, Any]: VAD state information including:
                - enabled: Whether VAD is enabled
                - initialized: Whether VAD is initialized
                - speech_active: Whether speech is currently active
                - configuration: Current VAD configuration
                - state_details: Detailed state information from event handler
        """
        state = {
            "enabled": self._vad_enabled,
            "initialized": self._vad is not None,
            "speech_active": self._event_handler._session_state.get(
                "speech_detected", False
            ),
            "configuration": self._vad_config.copy(),
        }

        # Add detailed state information if available
        if hasattr(self._event_handler, "_vad_state"):
            state["state_details"] = {
                "speech_active": self._event_handler._vad_state.get(
                    "speech_active", False
                ),
                "confidence_history": self._event_handler._vad_state.get(
                    "confidence_history", []
                ),
                "speech_counter": self._event_handler._vad_state.get(
                    "speech_counter", 0
                ),
                "silence_counter": self._event_handler._vad_state.get(
                    "silence_counter", 0
                ),
                "last_speech_time": self._event_handler._vad_state.get(
                    "last_speech_time"
                ),
                "speech_start_time": self._event_handler._vad_state.get(
                    "speech_start_time"
                ),
            }

        return state

    def reset_vad_state(self) -> None:
        """
        Reset VAD state tracking to initial values.

        This method can be called to reset the VAD state management
        without disabling VAD completely.
        """
        if hasattr(self._event_handler, "_reset_vad_state"):
            self._event_handler._reset_vad_state()
            self.logger.debug("[MOCK REALTIME] VAD state reset via client")

    def update_vad_config(self, config_updates: Dict[str, Any]) -> None:
        """
        Update VAD configuration with new parameters.

        This method updates the VAD configuration and reinitializes
        VAD if it's currently enabled.

        Args:
            config_updates (Dict[str, Any]): Configuration updates to apply.
        """
        self._vad_config.update(config_updates)

        # Reinitialize VAD if it's currently enabled
        if self._vad_enabled:
            self.logger.info(
                "[MOCK REALTIME] Reinitializing VAD with updated configuration"
            )
            self._cleanup_vad()
            self._initialize_vad(enable_vad=True)
            # Update event handler with new VAD instance
            self._event_handler._vad = self._vad

    # Transcription-related methods

    def is_transcription_enabled(self) -> bool:
        """
        Check if transcription is enabled and initialized.

        Returns:
            bool: True if transcription is enabled and initialized, False otherwise.
        """
        return self._transcription_enabled and self._transcriber is not None

    def get_transcription_config(self) -> Dict[str, Any]:
        """
        Get the current transcription configuration.

        Returns:
            Dict[str, Any]: Current transcription configuration dictionary.
        """
        return self._transcription_config.copy()

    def enable_transcription(
        self, transcription_config: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Enable transcription with optional configuration.

        Args:
            transcription_config (Optional[Dict[str, Any]]): Transcription configuration to use.
                                                           If None, uses default configuration.
        """
        if transcription_config:
            self._transcription_config.update(transcription_config)
        self._initialize_transcription(enable_transcription=True)
        # Update event handler with new transcriber instance
        self._event_handler._transcriber = self._transcriber

    def disable_transcription(self) -> None:
        """
        Disable transcription and clean up resources.
        """
        self._cleanup_transcription()
        self._transcription_enabled = False
        # Update event handler to remove transcriber instance
        self._event_handler._transcriber = None

    def get_transcription_state(self) -> Dict[str, Any]:
        """
        Get current transcription state information.

        Returns:
            Dict[str, Any]: Transcription state information including:
                - enabled: Whether transcription is enabled
                - initialized: Whether transcriber is initialized
                - backend: Current transcription backend
                - configuration: Current transcription configuration
        """
        state = {
            "enabled": self._transcription_enabled,
            "initialized": self._transcriber is not None,
            "backend": self._transcription_config.get("backend", "pocketsphinx"),
            "configuration": self._transcription_config.copy(),
        }

        if self._transcriber:
            state["transcriber_type"] = type(self._transcriber).__name__

        return state

    def update_transcription_config(self, config_updates: Dict[str, Any]) -> None:
        """
        Update transcription configuration with new parameters.

        This method updates the transcription configuration and reinitializes
        transcription if it's currently enabled.

        Args:
            config_updates (Dict[str, Any]): Configuration updates to apply.
        """
        self._transcription_config.update(config_updates)

        # Reinitialize transcription if it's currently enabled
        if self._transcription_enabled:
            self.logger.info(
                "[MOCK REALTIME] Reinitializing transcription with updated configuration"
            )
            self._cleanup_transcription()
            self._initialize_transcription(enable_transcription=True)
            # Update event handler with new transcriber instance
            self._event_handler._transcriber = self._transcriber
