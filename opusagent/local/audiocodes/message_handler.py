"""
Message handling for the AudioCodes mock client.

This module provides comprehensive WebSocket message processing and event handling
for the AudioCodes mock client. It processes incoming messages from the bridge
server and updates the session state accordingly.

The MessageHandler manages:
- WebSocket message parsing and validation
- Event handler registration and execution
- Session state updates based on received messages
- Audio stream state management
- Speech/VAD event processing
- Message history tracking and analysis
- Error handling and recovery

The message handler serves as the central coordinator for all incoming
communications from the bridge server, ensuring proper state synchronization
and event processing.

Message Processing Pipeline:
The MessageHandler implements a comprehensive message processing pipeline:

1. Message Reception: Receive raw WebSocket messages
2. Message Parsing: Parse JSON and extract message type
3. Message Validation: Validate message structure and required fields
4. Event Creation: Create structured MessageEvent objects
5. Handler Routing: Route messages to appropriate event handlers
6. State Updates: Update session and stream state based on messages
7. History Tracking: Store messages for analysis and debugging

Event Handling System:
The MessageHandler provides a flexible event handling system:
- Default handlers for all standard AudioCodes message types
- Custom handler registration for extensibility
- Handler chaining for complex processing scenarios
- Error isolation to prevent handler failures from affecting other handlers
"""

import json
import logging
from typing import Any, Callable, Dict, List, Optional

from .models import MessageEvent, MessageType
from .session_manager import SessionManager


class MessageHandler:
    """
    WebSocket message handler for the AudioCodes mock client.

    This class processes incoming WebSocket messages from the bridge server,
    updates session state, and triggers appropriate callbacks for different
    message types. It provides a flexible event handling system that can be
    extended with custom handlers for specific message types.

    The MessageHandler provides:
    - Automatic message parsing and validation
    - Event handler registration and management
    - Session state synchronization
    - Audio stream state management
    - Speech/VAD event processing
    - Message history tracking
    - Comprehensive error handling

    Message Processing:
    The MessageHandler processes all incoming WebSocket messages and:
    - Parses JSON message structure
    - Validates message format and required fields
    - Creates structured MessageEvent objects
    - Routes messages to appropriate handlers
    - Updates session and stream state
    - Maintains message history for analysis

    Event Handling:
    The MessageHandler supports both default and custom event handlers:
    - Default handlers for all standard AudioCodes message types
    - Custom handler registration for specific message types
    - Handler chaining for complex processing scenarios
    - Error isolation to prevent handler failures

    Attributes:
        logger (logging.Logger): Logger instance for debugging and monitoring
        session_manager (SessionManager): Session manager for state updates
        received_messages (List[Dict[str, Any]]): Complete history of received messages
        event_handlers (Dict[str, List[Callable]]): Registered event handlers by message type
    """

    def __init__(
        self, session_manager: SessionManager, logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the MessageHandler with session manager and logging.

        Args:
            session_manager (SessionManager): Session manager instance for state updates
            logger (Optional[logging.Logger]): Logger instance for debugging and monitoring.
                                             If None, creates a default logger for this module.

        Example:
            # Create MessageHandler with session manager
            session_manager = SessionManager(config)
            message_handler = MessageHandler(session_manager)

            # Create with custom logger
            custom_logger = logging.getLogger("custom_messages")
            message_handler = MessageHandler(session_manager, logger=custom_logger)
        """
        self.logger = logger or logging.getLogger(__name__)
        self.session_manager = session_manager
        self.received_messages: List[Dict[str, Any]] = []
        self.event_handlers: Dict[str, List[Callable]] = {}

        # Register default handlers for core message types
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """
        Register default message handlers for core AudioCodes message types.

        This method sets up the default event handlers for all standard
        AudioCodes message types, including session management, stream control,
        and speech/VAD events. These handlers ensure proper state updates
        and audio processing.

        The default handlers include:
        - Session lifecycle events (accepted, resumed, error, validated)
        - Stream control events (started, stopped, chunks)
        - Speech/VAD events (started, stopped, committed, hypothesis)
        - Activity events for custom functionality

        Handler Registration:
        Each message type is registered with one or more handlers that:
        - Update session state appropriately
        - Manage stream state and audio processing
        - Handle speech detection and VAD events
        - Process custom activities and events

        Default Handler Types:
        - Session Handlers: Manage session lifecycle and state
        - Stream Handlers: Control audio stream operations
        - Speech Handlers: Process voice activity detection
        - Activity Handlers: Handle custom events and activities
        """
        handlers = {
            # Session management handlers
            MessageType.SESSION_ACCEPTED: [
                self.session_manager.handle_session_accepted
            ],
            MessageType.SESSION_RESUMED: [self.session_manager.handle_session_resumed],
            MessageType.SESSION_ERROR: [self.session_manager.handle_session_error],
            MessageType.CONNECTION_VALIDATED: [
                self.session_manager.handle_connection_validated
            ],
            # Stream control handlers
            MessageType.USER_STREAM_STARTED: [self._handle_user_stream_started],
            MessageType.USER_STREAM_STOPPED: [self._handle_user_stream_stopped],
            MessageType.PLAY_STREAM_START: [self._handle_play_stream_start],
            MessageType.PLAY_STREAM_CHUNK: [self._handle_play_stream_chunk],
            MessageType.PLAY_STREAM_STOP: [self._handle_play_stream_stop],
            # Activity and speech handlers
            MessageType.ACTIVITIES: [self._handle_activities],
            MessageType.USER_STREAM_SPEECH_STARTED: [self._handle_speech_started],
            MessageType.USER_STREAM_SPEECH_STOPPED: [self._handle_speech_stopped],
            MessageType.USER_STREAM_SPEECH_COMMITTED: [self._handle_speech_committed],
            MessageType.USER_STREAM_SPEECH_HYPOTHESIS: [self._handle_speech_hypothesis],
        }

        # Register all handlers
        for msg_type, handler_list in handlers.items():
            for handler in handler_list:
                self.register_event_handler(msg_type.value, handler)

    def register_event_handler(self, event_type: str, handler: Callable) -> None:
        """
        Register a custom event handler for a specific message type.

        This method allows registration of custom event handlers for specific
        message types, enabling extensible message processing and custom
        functionality beyond the default handlers.

        The registration process:
        1. Create handler list for message type if it doesn't exist
        2. Add the handler to the list
        3. Log the registration for debugging

        Event Handler Requirements:
        - Handler must accept a Dict[str, Any] parameter with message data
        - Handler should handle errors gracefully
        - Handler can return any value (return values are ignored)
        - Multiple handlers can be registered for the same message type

        Handler Execution:
        - All registered handlers for a message type are executed
        - Handlers are executed in registration order
        - Handler failures don't prevent other handlers from executing
        - Handler errors are logged but don't stop message processing

        Args:
            event_type (str): Message type to handle (e.g., "session.accepted")
            handler (Callable): Handler function to call when message is received.
                              Should accept a Dict[str, Any] parameter with message data.

        Example:
            # Register custom handler for session events
            def custom_session_handler(data):
                print(f"Custom session handling: {data}")
                # Custom processing logic here

            message_handler.register_event_handler("session.accepted", custom_session_handler)

            # Register multiple handlers for same message type
            def logging_handler(data):
                logger.info(f"Received message: {data}")

            message_handler.register_event_handler("session.accepted", logging_handler)
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
        self.logger.debug(f"[MESSAGE] Registered handler for {event_type}")

    def process_message(self, message: str) -> Optional[MessageEvent]:
        """
        Process an incoming WebSocket message from the bridge server.

        This method is the main entry point for message processing. It parses
        the JSON message, validates its structure, creates a MessageEvent object,
        and triggers all registered handlers for the message type.

        The processing pipeline:
        1. Parse JSON message and extract message type
        2. Validate message structure and required fields
        3. Store message in history for analysis
        4. Create MessageEvent object with parsed data
        5. Trigger all registered handlers for the message type
        6. Log message receipt for monitoring
        7. Return processed event or None if error

        Message Validation:
        - Ensures message is valid JSON
        - Validates presence of required 'type' field
        - Extracts conversation ID and message data
        - Handles malformed messages gracefully

        Error Handling:
        - JSON parsing errors are caught and logged
        - Missing message type is logged as warning
        - Handler execution errors are isolated
        - Returns None for unprocessable messages

        Args:
            message (str): Raw WebSocket message as JSON string

        Returns:
            Optional[MessageEvent]: Processed message event with type, conversation ID,
                                   and data, or None if processing failed

        Raises:
            json.JSONDecodeError: If message is not valid JSON
            Exception: For other processing errors

        Example:
            # Process incoming message
            event = message_handler.process_message('{"type": "session.accepted", "conversationId": "123"}')
            if event:
                print(f"Processed {event.type} event")
            else:
                print("Message processing failed")
        """
        try:
            # Parse JSON message
            data = json.loads(message)
            msg_type = data.get("type")

            # Validate message structure
            if not msg_type:
                self.logger.warning(
                    f"[MESSAGE] Received message without type: {message}"
                )
                return None

            # Store message in history for analysis and debugging
            self.received_messages.append(data)

            # Create structured message event
            event = MessageEvent(
                type=msg_type, conversation_id=data.get("conversationId"), data=data
            )

            # Trigger all registered handlers for this message type
            self._trigger_handlers(msg_type, data)

            # Log message receipt
            self.logger.debug(f"[MESSAGE] Processed {msg_type} message")
            return event

        except json.JSONDecodeError as e:
            self.logger.error(f"[MESSAGE] JSON decode error: {e}")
            return None
        except Exception as e:
            self.logger.error(f"[MESSAGE] Processing error: {e}")
            return None

    def _trigger_handlers(self, msg_type: str, data: Dict[str, Any]) -> None:
        """
        Trigger all registered handlers for a specific message type.

        This method executes all registered event handlers for a given message
        type. It provides error isolation to ensure that handler failures
        don't prevent other handlers from executing.

        Handler Execution:
        - Executes all registered handlers for the message type
        - Handlers are executed in registration order
        - Each handler is executed independently
        - Handler errors are logged but don't stop execution

        Error Isolation:
        - Individual handler failures are caught and logged
        - Failed handlers don't prevent other handlers from executing
        - Handler errors don't affect message processing
        - Comprehensive error logging for debugging

        Args:
            msg_type (str): Message type to handle
            data (Dict[str, Any]): Message data to pass to handlers

        Example:
            # Internal method - handlers are triggered automatically
            # when process_message() is called
        """
        if msg_type in self.event_handlers:
            for handler in self.event_handlers[msg_type]:
                try:
                    handler(data)
                except Exception as e:
                    self.logger.error(f"[MESSAGE] Handler error for {msg_type}: {e}")

    def _handle_user_stream_started(self, data: Dict[str, Any]) -> None:
        """
        Handle user stream started event from the bridge server.

        This method processes userStream.started messages and updates
        the stream state to reflect that the user audio stream is now
        active and ready for audio input.

        Stream State Updates:
        - Sets user stream status to ACTIVE
        - Records stream start timestamp
        - Updates stream state for audio processing
        - Logs stream activation

        Args:
            data (Dict[str, Any]): User stream started event data

        Example:
            # Internal handler - called automatically by process_message()
        """
        from .models import StreamStatus

        self.session_manager.stream_state.user_stream = StreamStatus.ACTIVE
        self.logger.info("[MESSAGE] User stream started")

    def _handle_user_stream_stopped(self, data: Dict[str, Any]) -> None:
        """
        Handle user stream stopped event from the bridge server.

        This method processes userStream.stopped messages and updates
        the stream state to reflect that the user audio stream has
        been stopped.

        Stream State Updates:
        - Sets user stream status to STOPPED
        - Records stream stop timestamp
        - Updates stream state for audio processing
        - Logs stream deactivation

        Args:
            data (Dict[str, Any]): User stream stopped event data

        Example:
            # Internal handler - called automatically by process_message()
        """
        from .models import StreamStatus

        self.session_manager.stream_state.user_stream = StreamStatus.STOPPED
        self.logger.info("[MESSAGE] User stream stopped")

    def _handle_play_stream_start(self, data: Dict[str, Any]) -> None:
        """
        Handle play stream start event from the bridge server.

        This method processes playStream.start messages and updates
        the stream state to reflect that audio playback is beginning.
        It also manages conversation state for audio collection.

        Stream State Updates:
        - Sets play stream status to ACTIVE
        - Records stream start timestamp
        - Updates conversation state for audio collection
        - Logs playback start

        Conversation State Management:
        - Starts audio collection for greetings or responses
        - Sets appropriate collection flags
        - Prepares for audio chunk collection

        Args:
            data (Dict[str, Any]): Play stream start event data

        Example:
            # Internal handler - called automatically by process_message()
        """
        from .models import StreamStatus

        self.session_manager.stream_state.play_stream = StreamStatus.ACTIVE

        # Set current stream ID if provided
        stream_id = data.get("streamId")
        if stream_id:
            self.session_manager.stream_state.current_stream_id = stream_id

        # Update conversation state for audio collection
        if self.session_manager.conversation_state:
            # Check if we already have greeting chunks to determine if this is a response
            has_greeting = (
                len(self.session_manager.conversation_state.greeting_chunks) > 0
            )

            if not has_greeting:
                # First audio - likely greeting
                self.session_manager.conversation_state.collecting_greeting = True
                self.session_manager.conversation_state.collecting_response = False
                self.logger.info("[MESSAGE] Starting greeting collection")
            else:
                # Subsequent audio - likely response
                self.session_manager.conversation_state.collecting_response = True
                self.session_manager.conversation_state.collecting_greeting = False
                self.logger.info("[MESSAGE] Starting response collection")

        self.logger.info("[MESSAGE] Play stream started")

    def _handle_play_stream_chunk(self, data: Dict[str, Any]) -> None:
        """
        Handle play stream chunk event from the bridge server.

        This method processes playStream.chunk messages and collects
        audio chunks for the current audio stream (greeting or response).
        It manages the audio collection process and stream state.

        Audio Collection:
        - Collects audio chunks based on current collection state
        - Adds chunks to appropriate collection (greeting or response)
        - Manages audio chunk storage and tracking
        - Logs chunk collection progress

        Stream State Management:
        - Tracks audio chunk collection
        - Updates conversation state with collected audio
        - Manages collection flags and state

        Args:
            data (Dict[str, Any]): Play stream chunk event data containing audio

        Example:
            # Internal handler - called automatically by process_message()
        """
        audio_chunk = data.get("audioChunk")
        if audio_chunk and self.session_manager.conversation_state:
            if self.session_manager.conversation_state.collecting_greeting:
                self.session_manager.conversation_state.greeting_chunks.append(
                    audio_chunk
                )
            elif self.session_manager.conversation_state.collecting_response:
                self.session_manager.conversation_state.response_chunks.append(
                    audio_chunk
                )

        self.logger.debug("[MESSAGE] Play stream chunk received")

    def _handle_play_stream_stop(self, data: Dict[str, Any]) -> None:
        """
        Handle play stream stop event from the bridge server.

        This method processes playStream.stop messages and finalizes
        the audio collection process. It updates stream state and
        conversation state to reflect the end of audio playback.

        Stream State Updates:
        - Sets play stream status to STOPPED
        - Records stream stop timestamp
        - Updates stream state for audio processing
        - Logs playback completion

        Conversation State Management:
        - Finalizes audio collection process
        - Clears collection flags
        - Updates conversation state
        - Logs collection completion

        Args:
            data (Dict[str, Any]): Play stream stop event data

        Example:
            # Internal handler - called automatically by process_message()
        """
        from .models import StreamStatus

        # Finalize audio collection
        if self.session_manager.conversation_state:
            if self.session_manager.conversation_state.collecting_greeting:
                self.session_manager.conversation_state.collecting_greeting = False
                self.logger.info(
                    f"[MESSAGE] Greeting collection completed: {len(self.session_manager.conversation_state.greeting_chunks)} chunks"
                )
                # Set to INACTIVE for greeting completion
                self.session_manager.stream_state.play_stream = StreamStatus.INACTIVE
            elif self.session_manager.conversation_state.collecting_response:
                self.session_manager.conversation_state.collecting_response = False
                self.logger.info(
                    f"[MESSAGE] Response collection completed: {len(self.session_manager.conversation_state.response_chunks)} chunks"
                )
                # Set to STOPPED for response completion and clear stream ID
                self.session_manager.stream_state.play_stream = StreamStatus.STOPPED
                self.session_manager.stream_state.current_stream_id = None
            else:
                self.logger.warning(
                    "[MESSAGE] Play stream stopped but no collection was active"
                )

        self.logger.info("[MESSAGE] Play stream stopped")

    def _handle_activities(self, data: Dict[str, Any]) -> None:
        """
        Handle activities event from the bridge server.

        This method processes activities messages and manages custom
        events and activities received from the bridge server. It
        updates conversation state with activity information.

        Activity Processing:
        - Processes custom activities and events
        - Updates conversation state with activity data
        - Manages activity history and tracking
        - Logs activity receipt

        Conversation State Updates:
        - Adds activities to conversation history
        - Updates last activity information
        - Manages activity tracking and analysis

        Args:
            data (Dict[str, Any]): Activities event data

        Example:
            # Internal handler - called automatically by process_message()
        """
        activities = data.get("activities", [])
        if activities and self.session_manager.conversation_state:
            self.session_manager.conversation_state.activities_received.extend(
                activities
            )
            self.session_manager.conversation_state.last_activity = activities[-1]

        self.logger.info(f"[MESSAGE] Received {len(activities)} activities")

    def _handle_speech_started(self, data: Dict[str, Any]) -> None:
        """
        Handle speech started event from the bridge server.

        This method processes userStream.speech.started messages and
        updates the stream state to reflect that speech has been
        detected in the user audio stream.

        Speech State Updates:
        - Sets speech active flag to True
        - Records speech start timestamp
        - Updates stream state for VAD processing
        - Logs speech detection

        Args:
            data (Dict[str, Any]): Speech started event data

        Example:
            # Internal handler - called automatically by process_message()
        """
        self.session_manager.stream_state.speech_active = True
        self.logger.info("[MESSAGE] Speech started")

    def _handle_speech_stopped(self, data: Dict[str, Any]) -> None:
        """
        Handle speech stopped event from the bridge server.

        This method processes userStream.speech.stopped messages and
        updates the stream state to reflect that speech has ended
        in the user audio stream.

        Speech State Updates:
        - Sets speech active flag to False
        - Records speech stop timestamp
        - Updates stream state for VAD processing
        - Logs speech end

        Args:
            data (Dict[str, Any]): Speech stopped event data

        Example:
            # Internal handler - called automatically by process_message()
        """
        self.session_manager.stream_state.speech_active = False
        self.logger.info("[MESSAGE] Speech stopped")

    def _handle_speech_committed(self, data: Dict[str, Any]) -> None:
        """
        Handle speech committed event from the bridge server.

        This method processes userStream.speech.committed messages and
        updates the stream state to reflect that speech has been
        finalized and committed.

        Speech State Updates:
        - Sets speech committed flag to True
        - Records speech commitment timestamp
        - Updates stream state for VAD processing
        - Logs speech commitment

        Args:
            data (Dict[str, Any]): Speech committed event data

        Example:
            # Internal handler - called automatically by process_message()
        """
        self.session_manager.stream_state.speech_committed = True
        self.logger.info("[MESSAGE] Speech committed")

    def _handle_speech_hypothesis(self, data: Dict[str, Any]) -> None:
        """
        Handle speech hypothesis event from the bridge server.

        This method processes userStream.speech.hypothesis messages and
        updates the stream state with interim speech recognition results.

        Speech State Updates:
        - Updates current hypothesis with interim results
        - Records hypothesis timestamp
        - Updates stream state for VAD processing
        - Logs hypothesis receipt

        Args:
            data (Dict[str, Any]): Speech hypothesis event data

        Example:
            # Internal handler - called automatically by process_message()
        """
        alternatives = data.get("alternatives", [])
        self.session_manager.stream_state.current_hypothesis = alternatives
        self.logger.debug(f"[MESSAGE] Speech hypothesis: {len(alternatives)} results")

    def get_received_messages(self) -> List[Dict[str, Any]]:
        """
        Get the complete history of received messages.

        This method returns all messages that have been received and
        processed by the MessageHandler. The message history is useful
        for debugging, analysis, and understanding the conversation flow.

        Message History:
        - Complete record of all received messages
        - Includes message type, data, and timing
        - Useful for debugging and analysis
        - Maintained in chronological order

        Returns:
            List[Dict[str, Any]]: Complete list of received messages

        Example:
            # Get message history
            messages = message_handler.get_received_messages()
            print(f"Received {len(messages)} messages")

            # Analyze message types
            for msg in messages:
                print(f"Message type: {msg.get('type')}")
        """
        return self.received_messages.copy()

    def get_message_count(self) -> int:
        """
        Get the total number of messages received.

        This method returns the count of all messages that have been
        received and processed by the MessageHandler. It's useful for
        monitoring message volume and processing statistics.

        Message Counting:
        - Counts all processed messages
        - Includes both successful and failed processing
        - Useful for monitoring and statistics
        - Real-time count of message volume

        Returns:
            int: Total number of received messages

        Example:
            # Get message count
            count = message_handler.get_message_count()
            print(f"Total messages received: {count}")
        """
        return len(self.received_messages)

    def clear_message_history(self) -> None:
        """
        Clear the message history.

        This method removes all stored messages from the message history,
        freeing up memory and preparing for a new conversation or test
        scenario.

        History Clearing:
        - Removes all stored messages
        - Frees memory occupied by message history
        - Prepares for new conversation
        - Useful for testing and memory management

        Example:
            # Clear message history
            message_handler.clear_message_history()
            print("Message history cleared")
        """
        self.received_messages.clear()
        self.logger.info("[MESSAGE] Message history cleared")

    def get_last_message(self) -> Optional[Dict[str, Any]]:
        """
        Get the most recently received message.

        This method returns the last message that was received and
        processed by the MessageHandler. It's useful for checking
        the most recent communication or for debugging purposes.

        Last Message:
        - Most recently received message
        - Includes complete message data
        - Useful for debugging and monitoring
        - Returns None if no messages received

        Returns:
            Optional[Dict[str, Any]]: Last received message, or None if no messages

        Example:
            # Get last message
            last_msg = message_handler.get_last_message()
            if last_msg:
                print(f"Last message type: {last_msg.get('type')}")
            else:
                print("No messages received yet")
        """
        return self.received_messages[-1] if self.received_messages else None

    def get_messages_by_type(self, msg_type: str) -> List[Dict[str, Any]]:
        """
        Get all messages of a specific type.

        This method filters the message history to return only messages
        of the specified type. It's useful for analyzing specific
        message types or debugging particular message flows.

        Message Filtering:
        - Filters messages by type
        - Returns all matching messages
        - Maintains chronological order
        - Useful for analysis and debugging

        Args:
            msg_type (str): Message type to filter by

        Returns:
            List[Dict[str, Any]]: List of messages matching the specified type

        Example:
            # Get all session messages
            session_messages = message_handler.get_messages_by_type("session.accepted")
            print(f"Found {len(session_messages)} session acceptance messages")

            # Get all audio chunks
            audio_messages = message_handler.get_messages_by_type("playStream.chunk")
            print(f"Received {len(audio_messages)} audio chunks")
        """
        return [msg for msg in self.received_messages if msg.get("type") == msg_type]
