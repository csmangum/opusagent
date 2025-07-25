"""
Session management for the AudioCodes mock client.

This module provides comprehensive session state management and lifecycle
handling for the AudioCodes mock client. It tracks session status, manages
conversation state, and provides methods for all session operations.

The SessionManager handles:
- Session lifecycle (initiate, resume, validate, end)
- State tracking and status management
- WebSocket message preparation
- Event handling and state updates
- Session configuration management
- Error handling and recovery

The session manager maintains the complete state of the AudioCodes session
and provides a clean interface for session operations while ensuring
proper state transitions and validation.

Session Lifecycle:
The session manager orchestrates the complete lifecycle of AudioCodes sessions:

1. Session Creation: Initialize session with configuration
2. Session Initiation: Establish connection with bridge server
3. Session Validation: Verify connection health and capabilities
4. Session Management: Handle ongoing communication and state updates
5. Session Resumption: Reconnect to existing sessions if needed
6. Session Termination: Clean shutdown and resource cleanup

State Management:
The session manager maintains three key state objects:
- SessionState: Tracks session status and metadata
- StreamState: Manages audio stream status and speech detection
- ConversationState: Handles multi-turn conversation tracking
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from .models import (
    ConversationResult,
    ConversationState,
    SessionConfig,
    SessionState,
    SessionStatus,
    StreamState,
    StreamStatus,
)


class SessionManager:
    """
    Session state manager for the AudioCodes mock client.

    This class manages the complete lifecycle of AudioCodes sessions, including
    session creation, state tracking, message preparation, and event handling.
    It serves as the central coordinator for all session-related operations.

    The SessionManager provides:
    - Session lifecycle management (initiate, resume, validate, end)
    - Real-time state tracking and status updates
    - WebSocket message preparation for all session operations
    - Event handling and state synchronization
    - Comprehensive error handling and recovery
    - Session configuration and parameter management

    State Management:
    The SessionManager maintains three primary state objects:
    - session_state: Tracks session status, conversation ID, and metadata
    - stream_state: Manages audio stream status and speech detection
    - conversation_state: Handles multi-turn conversation tracking

    Message Preparation:
    The SessionManager prepares all WebSocket messages for session operations,
    ensuring proper formatting and including all required parameters for
    successful communication with the bridge server.

    Error Handling:
    Comprehensive error handling ensures graceful degradation and proper
    state recovery when session operations fail or encounter errors.

    Attributes:
        logger (logging.Logger): Logger instance for debugging and monitoring
        config (SessionConfig): Session configuration parameters
        session_state (SessionState): Current session state and status
        stream_state (StreamState): Audio stream state management
        conversation_state (Optional[ConversationState]): Multi-turn conversation state
    """

    def __init__(self, config: SessionConfig, logger: Optional[logging.Logger] = None):
        """
        Initialize the SessionManager with configuration and logging.

        Args:
            config (SessionConfig): Session configuration containing all parameters
                                  for session establishment and management
            logger (Optional[logging.Logger]): Logger instance for debugging and monitoring.
                                             If None, creates a default logger for this module.

        Example:
            # Create SessionManager with configuration
            config = SessionConfig(
                bridge_url="ws://localhost:8080",
                bot_name="TestBot",
                caller="+15551234567"
            )
            session_manager = SessionManager(config)
        """
        self.logger = logger or logging.getLogger(__name__)
        self.config = config
        self.session_state = SessionState()
        self.stream_state = StreamState()
        self.conversation_state: Optional[ConversationState] = None

    def create_session(self, conversation_id: Optional[str] = None) -> str:
        """
        Create a new session with optional conversation ID.

        This method initializes a new session, either with a provided conversation ID
        or by generating a new one. It sets up the initial session state and prepares
        for session establishment with the bridge server.

        The session creation process:
        1. Generate or use provided conversation ID
        2. Initialize session state with default values
        3. Set session status to CONNECTED
        4. Record creation timestamp
        5. Log session creation details

        Session Initialization:
        - Creates unique conversation identifier if not provided
        - Initializes all state objects with default values
        - Sets up conversation state for multi-turn tracking
        - Prepares session for connection establishment

        Args:
            conversation_id (Optional[str]): Pre-existing conversation ID to use.
                                           If None, generates a new UUID-based ID.

        Returns:
            str: The conversation ID for the new session

        Example:
            # Create new session with auto-generated ID
            conv_id = session_manager.create_session()
            print(f"Created session with ID: {conv_id}")

            # Create session with existing ID
            conv_id = session_manager.create_session("conv_existing_123")
        """
        # Generate conversation ID if not provided
        if conversation_id is None:
            conversation_id = f"conv_{str(uuid.uuid4())}"

        # Initialize session state
        self.session_state.conversation_id = conversation_id
        self.session_state.status = SessionStatus.CONNECTED
        self.session_state.created_at = datetime.now()

        # Initialize conversation state
        self.conversation_state = ConversationState(conversation_id=conversation_id)

        self.logger.info(f"[SESSION] Created session: {conversation_id}")
        return conversation_id

    def initiate_session(self) -> Dict[str, Any]:
        """
        Prepare session initiation message for the bridge server.

        This method creates the WebSocket message required to initiate a new
        session with the bridge server. It includes all necessary configuration
        parameters and sets the session status to INITIATING.

        The initiation message includes:
        - Session type and conversation ID
        - Bot configuration and caller information
        - Supported media formats
        - Audio message expectations

        Message Structure:
        The initiation message follows the AudioCodes protocol format:
        - type: "session.initiate"
        - conversationId: Unique session identifier
        - botName: Bot name identifier
        - caller: Caller phone number
        - expectAudioMessages: Audio message handling flag
        - supportedMediaFormats: List of supported audio formats

        State Transition:
        - Updates session status to INITIATING
        - Records initiation timestamp
        - Prepares for session acceptance

        Returns:
            Dict[str, Any]: WebSocket message for session initiation

        Example:
            # Initiate session
            message = session_manager.initiate_session()
            await websocket.send(json.dumps(message))

            # Check session status
            if session_manager.session_state.status == SessionStatus.INITIATING:
                print("Session initiation in progress")
        """
        # Auto-create session if needed
        if self.session_state.conversation_id is None:
            self.create_session()

        # Update session status to initiating
        self.session_state.status = SessionStatus.INITIATING
        self.session_state.last_activity = datetime.now()

        # Prepare initiation message
        message = {
            "type": "session.initiate",
            "conversationId": self.session_state.conversation_id,
            "botName": self.config.bot_name,
            "caller": self.config.caller,
            "expectAudioMessages": self.config.expect_audio_messages,
            "supportedMediaFormats": self.config.supported_media_formats,
        }

        self.logger.info(
            f"[SESSION] Prepared session initiation for: {self.session_state.conversation_id}"
        )
        return message

    def resume_session(self, conversation_id: str) -> Dict[str, Any]:
        """
        Prepare session resumption message for the bridge server.

        This method creates the WebSocket message required to resume an existing
        session with the bridge server. It's used when reconnecting to a previous
        conversation that was interrupted.

        The resumption process:
        1. Update session status to RESUMING
        2. Set the conversation ID for resumption
        3. Prepare resumption message with session details
        4. Log resumption attempt

        Session Resumption:
        - Used when reconnecting to existing sessions
        - Maintains conversation continuity
        - Preserves conversation state and history
        - Handles interrupted connections gracefully

        Message Structure:
        The resumption message includes:
        - type: "session.resume"
        - conversationId: Existing conversation identifier
        - botName: Bot name identifier
        - caller: Caller phone number

        Args:
            conversation_id (str): Conversation ID of the session to resume

        Returns:
            Dict[str, Any]: WebSocket message for session resumption

        Example:
            # Resume existing session
            message = session_manager.resume_session("conv_12345")
            await websocket.send(json.dumps(message))
        """
        # Update session state for resumption
        self.session_state.status = SessionStatus.RESUMING
        self.session_state.conversation_id = conversation_id
        self.session_state.last_activity = datetime.now()

        # Prepare resumption message
        message = {
            "type": "session.resume",
            "conversationId": conversation_id,
            "botName": self.config.bot_name,
            "caller": self.config.caller,
        }

        self.logger.info(
            f"[SESSION] Prepared session resumption for: {conversation_id}"
        )
        return message

    def validate_connection(self) -> Dict[str, Any]:
        """
        Prepare connection validation message for the bridge server.

        This method creates the WebSocket message required to validate the
        connection with the bridge server. It's used to verify that the
        connection is healthy and ready for session operations.

        Connection Validation:
        - Verifies WebSocket connection health
        - Confirms bridge server availability
        - Validates connection parameters
        - Ensures readiness for session operations

        Message Structure:
        The validation message includes:
        - type: "connection.validate"
        - conversationId: Current conversation identifier

        State Management:
        - Sets validation_pending flag
        - Records validation timestamp
        - Prepares for validation response

        Returns:
            Dict[str, Any]: WebSocket message for connection validation

        Raises:
            ValueError: If no conversation ID is available

        Example:
            # Validate connection
            message = session_manager.validate_connection()
            await websocket.send(json.dumps(message))
        """
        # Check for conversation ID
        if self.session_state.conversation_id is None:
            raise ValueError("No conversation ID available")

        # Update session state for validation
        self.session_state.validation_pending = True
        self.session_state.last_activity = datetime.now()

        # Prepare validation message
        message = {
            "type": "connection.validate",
            "conversationId": self.session_state.conversation_id,
        }

        self.logger.info(
            f"[SESSION] Prepared connection validation for: {self.session_state.conversation_id}"
        )
        return message

    def end_session(self, reason: str = "Session ended") -> Dict[str, Any]:
        """
        Prepare session termination message for the bridge server.

        This method creates the WebSocket message required to properly end
        the session with the bridge server. It ensures clean session
        termination and resource cleanup.

        Session Termination:
        - Sends proper termination message to bridge
        - Ensures clean resource cleanup
        - Records termination reason
        - Updates session state accordingly

        Message Structure:
        The termination message includes:
        - type: "session.end"
        - conversationId: Current conversation identifier
        - reasonCode: Termination reason code (default: "normal")
        - reason: Termination reason for logging

        State Cleanup:
        - Updates session status to ENDED
        - Records termination timestamp
        - Logs termination details

        Args:
            reason (str): Reason for session termination (default: "Session ended")

        Returns:
            Dict[str, Any]: WebSocket message for session termination

        Raises:
            ValueError: If no conversation ID is available

        Example:
            # End session normally
            message = session_manager.end_session("Test completed")
            await websocket.send(json.dumps(message))

            # End session with error
            message = session_manager.end_session("Connection lost")
        """
        # Check for conversation ID
        if self.session_state.conversation_id is None:
            raise ValueError("No conversation ID available")

        # Update session state for termination
        self.session_state.status = SessionStatus.ENDED
        self.session_state.last_activity = datetime.now()

        # Prepare termination message
        message = {
            "type": "session.end",
            "conversationId": self.session_state.conversation_id,
            "reasonCode": "normal",
            "reason": reason,
        }

        self.logger.info(
            f"[SESSION] Prepared session termination for: {self.session_state.conversation_id} - {reason}"
        )
        return message

    def handle_session_accepted(self, data: Dict[str, Any]) -> None:
        """
        Handle session acceptance response from the bridge server.

        This method processes the session acceptance message from the bridge
        server and updates the session state accordingly. It's called by
        the MessageHandler when a session.accepted message is received.

        Session Acceptance:
        - Confirms session establishment with bridge
        - Updates session status to ACTIVE
        - Records acceptance timestamp
        - Logs successful session establishment

        State Updates:
        - Sets session status to ACTIVE
        - Marks session as accepted
        - Updates last activity timestamp
        - Records session metadata from response

        Args:
            data (Dict[str, Any]): Session acceptance data from bridge server

        Example:
            # Handle session acceptance
            session_manager.handle_session_accepted({
                "sessionId": "sess_12345",
                "mediaFormat": "raw/lpcm16"
            })
        """
        # Update session state for acceptance
        self.session_state.status = SessionStatus.ACTIVE
        self.session_state.accepted = True
        self.session_state.last_activity = datetime.now()

        # Extract session metadata if provided
        if "mediaFormat" in data:
            self.session_state.media_format = data["mediaFormat"]

        self.logger.info(
            f"[SESSION] Session accepted: {self.session_state.conversation_id}"
        )

    def handle_session_resumed(self, data: Dict[str, Any]) -> None:
        """
        Handle session resumption response from the bridge server.

        This method processes the session resumption message from the bridge
        server and updates the session state accordingly. It's called by
        the MessageHandler when a session.resumed message is received.

        Session Resumption:
        - Confirms successful session resumption
        - Updates session status to ACTIVE
        - Records resumption timestamp
        - Logs successful session resumption

        State Updates:
        - Sets session status to ACTIVE
        - Marks session as resumed
        - Updates last activity timestamp
        - Records session metadata from response

        Args:
            data (Dict[str, Any]): Session resumption data from bridge server

        Example:
            # Handle session resumption
            session_manager.handle_session_resumed({
                "sessionId": "sess_12345",
                "resumed": True
            })
        """
        # Update session state for resumption
        self.session_state.status = SessionStatus.ACTIVE
        self.session_state.resumed = True
        self.session_state.last_activity = datetime.now()

        # Extract session metadata if provided
        if "mediaFormat" in data:
            self.session_state.media_format = data["mediaFormat"]

        self.logger.info(
            f"[SESSION] Session resumed: {self.session_state.conversation_id}"
        )

    def handle_session_error(self, data: Dict[str, Any]) -> None:
        """
        Handle session error response from the bridge server.

        This method processes session error messages from the bridge server
        and updates the session state accordingly. It's called by the
        MessageHandler when a session.error message is received.

        Session Error Handling:
        - Updates session status to ERROR
        - Records error details and reason
        - Logs error information
        - Prepares for error recovery

        State Updates:
        - Sets session status to ERROR
        - Marks session as having error
        - Records error reason and details
        - Updates last activity timestamp

        Args:
            data (Dict[str, Any]): Session error data from bridge server

        Example:
            # Handle session error
            session_manager.handle_session_error({
                "error": "Invalid session configuration",
                "reason": "Unsupported media format"
            })
        """
        # Update session state for error
        self.session_state.status = SessionStatus.ERROR
        self.session_state.error = True
        self.session_state.last_activity = datetime.now()

        # Extract error information
        self.session_state.error_reason = data.get("reason", "Unknown error")

        self.logger.error(
            f"[SESSION] Session error: {self.session_state.conversation_id} - {self.session_state.error_reason}"
        )

    def handle_connection_validated(self, data: Dict[str, Any]) -> None:
        """
        Handle connection validation response from the bridge server.

        This method processes connection validation messages from the bridge
        server and updates the session state accordingly. It's called by
        the MessageHandler when a connection.validated message is received.

        Connection Validation:
        - Confirms connection health and readiness
        - Updates validation status
        - Records validation timestamp
        - Logs successful validation

        State Updates:
        - Marks connection as validated
        - Clears validation pending flag
        - Updates last activity timestamp
        - Records validation metadata

        Args:
            data (Dict[str, Any]): Connection validation data from bridge server

        Example:
            # Handle connection validation
            session_manager.handle_connection_validated({
                "validated": True,
                "capabilities": ["audio", "vad"]
            })
        """
        # Update session state for validation
        self.session_state.connection_validated = True
        self.session_state.validation_pending = False
        self.session_state.last_activity = datetime.now()

        self.logger.info(
            f"[SESSION] Connection validated: {self.session_state.conversation_id}"
        )

    def send_dtmf_event(self, digit: str) -> Dict[str, Any]:
        """
        Prepare DTMF event message for the bridge server.

        This method creates a DTMF (Dual-Tone Multi-Frequency) event message
        for sending digit tones to the bridge server. DTMF events are used
        for interactive voice response systems and menu navigation.

        DTMF Events:
        - Send digit tones (0-9, *, #, A-D)
        - Used for menu navigation and input
        - Simulates phone keypad interactions
        - Supports interactive voice response systems

        Message Structure:
        The DTMF event message includes:
        - type: "activities"
        - conversationId: Current conversation identifier
        - activities: Array containing DTMF event data

        Args:
            digit (str): DTMF digit to send (0-9, *, #, A-D)

        Returns:
            Dict[str, Any]: WebSocket message for DTMF event

        Raises:
            ValueError: If no conversation ID is available

        Example:
            # Send DTMF digit
            message = session_manager.send_dtmf_event("1")
            await websocket.send(json.dumps(message))

            # Send multiple digits
            for digit in "123":
                message = session_manager.send_dtmf_event(digit)
                await websocket.send(json.dumps(message))
        """
        # Check for conversation ID
        if self.session_state.conversation_id is None:
            raise ValueError("No conversation ID available")

        # Prepare DTMF event message
        message = {
            "type": "activities",
            "conversationId": self.session_state.conversation_id,
            "activities": [
                {
                    "type": "event",
                    "name": "dtmf",
                    "value": digit,
                }
            ],
        }

        self.logger.info(
            f"[SESSION] Prepared DTMF event: {digit} for {self.session_state.conversation_id}"
        )
        return message

    def send_hangup_event(self) -> Dict[str, Any]:
        """
        Prepare hangup event message for the bridge server.

        This method creates a hangup event message for simulating a call
        termination event. Hangup events are used to signal that the
        call has been ended by the user or system.

        Hangup Events:
        - Simulates call termination
        - Signals end of conversation
        - Triggers session cleanup
        - Used for call flow testing

        Message Structure:
        The hangup event message includes:
        - type: "activities"
        - conversationId: Current conversation identifier
        - activities: Array containing hangup event data

        Returns:
            Dict[str, Any]: WebSocket message for hangup event

        Raises:
            ValueError: If no conversation ID is available

        Example:
            # Send hangup event
            message = session_manager.send_hangup_event()
            await websocket.send(json.dumps(message))
        """
        # Check for conversation ID
        if self.session_state.conversation_id is None:
            raise ValueError("No conversation ID available")

        # Prepare hangup event message
        message = {
            "type": "activities",
            "conversationId": self.session_state.conversation_id,
            "activities": [
                {
                    "type": "event",
                    "name": "hangup",
                }
            ],
        }

        self.logger.info(
            f"[SESSION] Prepared hangup event for {self.session_state.conversation_id}"
        )
        return message

    def send_custom_activity(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare custom activity message for the bridge server.

        This method creates a custom activity message for sending arbitrary
        events to the bridge server. Custom activities can be used for
        testing specific scenarios or extending the mock client functionality.

        Custom Activities:
        - Send arbitrary event data
        - Support custom testing scenarios
        - Extend mock client functionality
        - Enable protocol-specific testing

        Message Structure:
        The custom activity message includes:
        - type: "activities"
        - conversationId: Current conversation identifier
        - activities: Array containing custom activity data

        Args:
            activity (Dict[str, Any]): Custom activity data to send

        Returns:
            Dict[str, Any]: WebSocket message for custom activity

        Raises:
            ValueError: If no conversation ID is available

        Example:
            # Send custom activity
            custom_activity = {
                "type": "custom_event",
                "data": {"key": "value"},
                "timestamp": datetime.now().isoformat()
            }
            message = session_manager.send_custom_activity(custom_activity)
            await websocket.send(json.dumps(message))
        """
        # Check for conversation ID
        if self.session_state.conversation_id is None:
            raise ValueError("No conversation ID available")

        # Prepare custom activity message
        message = {
            "type": "activities",
            "conversationId": self.session_state.conversation_id,
            "activities": [activity],
        }

        self.logger.info(
            f"[SESSION] Prepared custom activity for {self.session_state.conversation_id}"
        )
        return message

    def reset_session_state(self) -> None:
        """
        Reset all session state to initial values.

        This method resets all session state objects to their initial
        values, effectively clearing the session and preparing for a
        new session. It's useful for testing scenarios or session recovery.

        State Reset:
        - Resets session state to DISCONNECTED
        - Clears conversation state
        - Resets stream state
        - Clears all flags and timestamps

        Usage:
        - Testing scenarios requiring clean state
        - Session recovery after errors
        - Preparing for new session establishment
        - Clearing accumulated state data

        Example:
            # Reset session state for new test
            session_manager.reset_session_state()
            print("Session state reset")
        """
        # Reset session state
        self.session_state = SessionState()

        # Reset stream state
        self.stream_state = StreamState()

        # Clear conversation state
        self.conversation_state = None

        self.logger.info("[SESSION] Session state reset")

    def get_session_status(self) -> Dict[str, Any]:
        """
        Get comprehensive session status information.

        This method provides a complete overview of the current session
        state, including status, metadata, and timing information.
        It's useful for monitoring, debugging, and status reporting.

        Status Information:
        - Session status and flags
        - Conversation metadata
        - Timing information
        - Stream state details
        - Error information if applicable

        Returns:
            Dict[str, Any]: Complete session status dictionary

        Example:
            # Get session status
            status = session_manager.get_session_status()
            print(f"Session status: {status['status']}")
            print(f"Conversation ID: {status['conversation_id']}")
            print(f"Active: {status['is_active']}")
        """
        return {
            "conversation_id": self.session_state.conversation_id,
            "status": self.session_state.status.value,
            "accepted": self.session_state.accepted,
            "resumed": self.session_state.resumed,
            "error": self.session_state.error,
            "error_reason": self.session_state.error_reason,
            "media_format": self.session_state.media_format,
            "connection_validated": self.session_state.connection_validated,
            "validation_pending": self.session_state.validation_pending,
            "created_at": (
                self.session_state.created_at.isoformat()
                if self.session_state.created_at
                else None
            ),
            "last_activity": (
                self.session_state.last_activity.isoformat()
                if self.session_state.last_activity
                else None
            ),
            "is_active": self.is_session_active(),
            "is_connected": self.is_connected(),
            "user_stream_active": self.stream_state.user_stream == StreamStatus.ACTIVE,
            "play_stream_active": self.stream_state.play_stream == StreamStatus.ACTIVE,
            "speech_active": self.stream_state.speech_active,
            "conversation_turn_count": (
                self.conversation_state.turn_count if self.conversation_state else 0
            ),
            "activities_count": (
                len(self.conversation_state.activities_received)
                if self.conversation_state
                else 0
            ),
            "stream_state": {
                "user_stream": self.stream_state.user_stream.value,
                "play_stream": self.stream_state.play_stream.value,
                "speech_active": self.stream_state.speech_active,
                "speech_committed": self.stream_state.speech_committed,
            },
            "conversation_state": (
                {
                    "turn_count": (
                        self.conversation_state.turn_count
                        if self.conversation_state
                        else 0
                    ),
                    "started_at": (
                        self.conversation_state.started_at.isoformat()
                        if self.conversation_state
                        else None
                    ),
                }
                if self.conversation_state
                else None
            ),
        }

    def is_session_active(self) -> bool:
        """
        Check if the session is currently active and ready for communication.

        This method checks whether the session is in an active state and
        ready for audio communication. An active session has been accepted
        by the bridge server and is ready for bidirectional communication.

        Active Session Criteria:
        - Session status is ACTIVE
        - Session has been accepted by bridge
        - No errors are present
        - Connection is validated

        Returns:
            bool: True if session is active, False otherwise

        Example:
            # Check if session is ready for communication
            if session_manager.is_session_active():
                print("Session is ready for audio communication")
            else:
                print("Session is not ready")
        """
        return (
            self.session_state.status == SessionStatus.ACTIVE
            and self.session_state.accepted
            and not self.session_state.error
        )

    def is_connected(self) -> bool:
        """
        Check if the WebSocket connection is established.

        This method checks whether the WebSocket connection to the bridge
        server is established. It's a lower-level check than session
        activity and only verifies connection status.

        Connection Status:
        - WebSocket connection is established
        - Connection may not be fully initialized
        - Session may not be active yet
        - Used for connection-level checks

        Returns:
            bool: True if connected, False otherwise

        Example:
            # Check connection status
            if session_manager.is_connected():
                print("WebSocket connection is established")
            else:
                print("WebSocket connection is not established")
        """
        return self.session_state.status in [
            SessionStatus.CONNECTED,
            SessionStatus.INITIATING,
            SessionStatus.ACTIVE,
            SessionStatus.RESUMING,
        ]

    def get_conversation_id(self) -> Optional[str]:
        """
        Get the current conversation ID.

        This method returns the conversation ID for the current session.
        The conversation ID is a unique identifier assigned to the session
        and is used throughout the session lifecycle.

        Conversation ID:
        - Unique identifier for the session
        - Used in all WebSocket messages
        - Assigned during session creation
        - Maintained throughout session lifecycle

        Returns:
            Optional[str]: Current conversation ID, or None if not set

        Example:
            # Get conversation ID
            conv_id = session_manager.get_conversation_id()
            if conv_id:
                print(f"Current conversation: {conv_id}")
            else:
                print("No conversation ID set")
        """
        return self.session_state.conversation_id
