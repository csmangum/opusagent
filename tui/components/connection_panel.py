"""
Connection Panel component for the Interactive TUI Validator.

This panel manages WebSocket connection status and controls for connecting
to the TelephonyRealtimeBridge server with enhanced error handling and session management.
"""

import uuid
import asyncio
import logging
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static, Button, Input, Label
from textual.widget import Widget

from tui.websocket.client import WebSocketClient
from tui.websocket.message_handler import MessageHandler, SessionMessageBuilder
from tui.models.session_state import SessionState, SessionStatus
from tui.models.event_logger import EventLogger, EventLevel, EventCategory

logger = logging.getLogger(__name__)


class ConnectionPanel(Widget):
    """Panel for managing WebSocket connection and displaying status."""
    
    CSS = """
    ConnectionPanel {
        background: $surface;
        border: solid $primary;
        height: auto;
        min-height: 6;
    }
    
    .connection-status {
        background: $surface;
        color: $text;
        text-align: center;
        height: 1;
    }
    
    .connection-controls {
        layout: horizontal;
        height: 2;
        align: center middle;
    }
    
    .session-info {
        background: $surface;
        color: $text;
        text-align: center;
        height: 1;
    }
    
    .status-connected {
        color: $success;
    }
    
    .status-disconnected {
        color: $error;
    }
    
    .status-connecting {
        color: $warning;
    }
    
    .status-error {
        color: $error;
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.parent_app = None
        
        # Initialize components
        self.websocket_client = WebSocketClient(
            max_reconnect_attempts=5,
            reconnect_delay=2.0,
            ping_interval=20.0,
            connection_timeout=15.0
        )
        self.message_handler = MessageHandler()
        self.session_state = SessionState()
        self.event_logger = EventLogger()
        
        # Connection state
        self.connection_status = "Disconnected"
        self.is_connecting = False
        self.last_error = None
        
        # Setup message and event handlers
        self._setup_handlers()
        
    def compose(self) -> ComposeResult:
        """Create the connection panel layout."""
        with Vertical():
            # Connection status display
            yield Static(
                "🔴 Disconnected from ws://localhost:8000/voice-bot",
                id="connection-status",
                classes="connection-status status-disconnected"
            )
            
            # Connection controls
            with Horizontal(classes="connection-controls"):
                yield Button("Connect", id="connect-btn", variant="success")
                yield Button("Disconnect", id="disconnect-btn", variant="error", disabled=True)
                yield Button("Reconnect", id="reconnect-btn", disabled=True)
                yield Button("Start Session", id="start-session-btn", disabled=True)
                yield Button("End Session", id="end-session-btn", disabled=True)
            
            # Session info
            yield Static(
                "Session: Not established | Conv: N/A | Status: Idle",
                id="session-info",
                classes="session-info"
            )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "connect-btn":
            asyncio.create_task(self._async_connect())
        elif event.button.id == "disconnect-btn":
            asyncio.create_task(self._async_disconnect())
        elif event.button.id == "reconnect-btn":
            asyncio.create_task(self._async_reconnect())
        elif event.button.id == "start-session-btn":
            asyncio.create_task(self._async_start_session())
        elif event.button.id == "end-session-btn":
            asyncio.create_task(self._async_end_session())
    
    async def _async_connect(self) -> None:
        """Initiate WebSocket connection."""
        if self.is_connecting or self.websocket_client.connected:
            return
            
        self.is_connecting = True
        self._update_status("Connecting...")
        
        try:
            url = self.parent_app.config.ws_url if self.parent_app else "ws://localhost:8000/voice-bot"
            
            self.event_logger.log_connection_event(
                "connection_attempt", 
                f"Attempting to connect to {url}",
                EventLevel.INFO
            )
            
            success = await self.websocket_client.connect(url)
            
            if success:
                self._update_status("Connected")
                self.last_error = None
                
                self.event_logger.log_connection_event(
                    "connected", 
                    f"Successfully connected to {url}",
                    EventLevel.INFO
                )
                
                # Notify parent app components
                if self.parent_app:
                    if hasattr(self.parent_app, "events_panel"):
                        self.parent_app.events_panel.add_event(
                            "connected", status="success", details=f"Connected to {url}"
                        )
                    if hasattr(self.parent_app, "status_bar"):
                        self.parent_app.status_bar.update_connection_status("Connected")
                    
                    # Update other components
                    self._notify_connection_state_change(True)
            else:
                self._update_status("Disconnected")
                self.event_logger.log_connection_event(
                    "connection_failed", 
                    f"Failed to connect to {url}",
                    EventLevel.ERROR
                )
                
                if self.parent_app and hasattr(self.parent_app, "events_panel"):
                    self.parent_app.events_panel.add_event(
                        "error", status="error", details=f"Failed to connect to {url}"
                    )
                    
        except Exception as e:
            self._update_status("Disconnected")
            self.last_error = str(e)
            
            self.event_logger.log_error_event(
                "connection_error",
                f"Connection error: {e}",
                {"error": str(e), "error_type": type(e).__name__}
            )
            
            logger.error(f"Connection error: {e}")
            
            if self.parent_app and hasattr(self.parent_app, "events_panel"):
                self.parent_app.events_panel.add_event(
                    "error", status="error", details=f"Connection error: {e}"
                )
        finally:
            self.is_connecting = False
    
    async def _async_disconnect(self) -> None:
        """Disconnect from WebSocket."""
        try:
            # End session first if active
            if self.session_state.is_active:
                await self._async_end_session()
            
            await self.websocket_client.disconnect()
            self._update_status("Disconnected")
            
            self.event_logger.log_connection_event(
                "disconnected", 
                "Manually disconnected from server",
                EventLevel.INFO
            )
            
            if self.parent_app:
                if hasattr(self.parent_app, "events_panel"):
                    self.parent_app.events_panel.add_event(
                        "disconnected", status="info", details="Disconnected from server"
                    )
                if hasattr(self.parent_app, "status_bar"):
                    self.parent_app.status_bar.update_connection_status("Disconnected")
                
                # Update other components
                self._notify_connection_state_change(False)
                
        except Exception as e:
            logger.error(f"Disconnect error: {e}")
            self.event_logger.log_error_event(
                "disconnect_error",
                f"Error during disconnect: {e}"
            )
    
    async def _async_reconnect(self) -> None:
        """Reconnect to WebSocket."""
        await self._async_disconnect()
        await asyncio.sleep(1.0)  # Brief pause
        await self._async_connect()
    
    async def _async_start_session(self) -> None:
        """Start a new session."""
        if not self.websocket_client.connected:
            logger.warning("Cannot start session: Not connected")
            return
            
        if self.session_state.status != SessionStatus.IDLE:
            logger.warning(f"Cannot start session: Current status is {self.session_state.status}")
            return
        
        try:
            # Generate new session
            conversation_id = self.session_state.initiate_session()
            
            # Create session initiate message
            message = SessionMessageBuilder.create_session_initiate(
                conversation_id=conversation_id,
                bot_name=self.parent_app.config.bot_name if self.parent_app else "voice-bot",
                caller="tui-validator",
                media_formats=["raw/lpcm16"]
            )
            
            # Send session initiate
            success = await self.websocket_client.send_message(message)
            
            if success:
                self.event_logger.log_session_event(
                    "session.initiate",
                    f"Session initiated: {conversation_id}",
                    EventLevel.INFO,
                    data={"conversation_id": conversation_id}
                )
                
                if self.parent_app and hasattr(self.parent_app, "events_panel"):
                    self.parent_app.events_panel.add_event(
                        "session.initiate", status="info", 
                        details=f"Session initiated: {conversation_id[:8]}..."
                    )
                    
                self._update_session_info()
            else:
                logger.error("Failed to send session initiate message")
                self.session_state.reset()
                
        except Exception as e:
            logger.error(f"Error starting session: {e}")
            self.session_state.reset()
            self.event_logger.log_error_event(
                "session_start_error",
                f"Error starting session: {e}"
            )
    
    async def _async_end_session(self) -> None:
        """End the current session."""
        if not self.session_state.is_active:
            logger.warning("No active session to end")
            return
        
        try:
            # Create session end message
            message = SessionMessageBuilder.create_session_end(
                conversation_id=self.session_state.conversation_id
            )
            
            # Send session end
            success = await self.websocket_client.send_message(message)
            
            if success:
                self.event_logger.log_session_event(
                    "session.end",
                    f"Session end requested: {self.session_state.conversation_id}",
                    EventLevel.INFO
                )
                
                if self.parent_app and hasattr(self.parent_app, "events_panel"):
                    self.parent_app.events_panel.add_event(
                        "session.end", status="info", 
                        details=f"Session end requested"
                    )
            
            # End session locally
            self.session_state.end_session()
            self._update_session_info()
            
        except Exception as e:
            logger.error(f"Error ending session: {e}")
            self.event_logger.log_error_event(
                "session_end_error",
                f"Error ending session: {e}"
            )
    
    def _update_status(self, status: str) -> None:
        """Update the connection status display."""
        self.connection_status = status
        
        # Update UI elements
        status_widget = self.query_one("#connection-status", Static)
        
        ws_url = self.parent_app.config.ws_url if self.parent_app and hasattr(self.parent_app, "config") else "ws://localhost:8000/voice-bot"
        
        if status == "Connected":
            status_widget.update(f"🟢 Connected to {ws_url}")
            status_widget.set_class(False, "status-disconnected", "status-connecting", "status-error")
            status_widget.set_class(True, "status-connected")
            
        elif status == "Connecting...":
            status_widget.update(f"🟡 Connecting to {ws_url}")
            status_widget.set_class(False, "status-disconnected", "status-connected", "status-error")
            status_widget.set_class(True, "status-connecting")
            
        elif status == "Error":
            error_msg = f" ({self.last_error})" if self.last_error else ""
            status_widget.update(f"🔴 Error connecting to {ws_url}{error_msg}")
            status_widget.set_class(False, "status-disconnected", "status-connected", "status-connecting")
            status_widget.set_class(True, "status-error")
            
        else:  # Disconnected
            status_widget.update(f"🔴 Disconnected from {ws_url}")
            status_widget.set_class(False, "status-connected", "status-connecting", "status-error")
            status_widget.set_class(True, "status-disconnected")
        
        # Update button states
        self._update_button_states()
    
    def _update_session_info(self) -> None:
        """Update session information display."""
        session_widget = self.query_one("#session-info", Static)
        
        session_str, conv_str = self.session_state.get_connection_display_info()
        status_str = self.session_state.status.value.title()
        
        session_widget.update(f"Session: {session_str} | Conv: {conv_str} | Status: {status_str}")
        
        # Update button states
        self._update_button_states()
    
    def _update_button_states(self) -> None:
        """Update button enabled/disabled states."""
        connect_btn = self.query_one("#connect-btn", Button)
        disconnect_btn = self.query_one("#disconnect-btn", Button)
        reconnect_btn = self.query_one("#reconnect-btn", Button)
        start_session_btn = self.query_one("#start-session-btn", Button)
        end_session_btn = self.query_one("#end-session-btn", Button)
        
        is_connected = self.websocket_client.connected and not self.is_connecting
        is_session_active = self.session_state.is_active
        
        # Connection buttons
        connect_btn.disabled = is_connected or self.is_connecting
        disconnect_btn.disabled = not is_connected
        reconnect_btn.disabled = not is_connected
        
        # Session buttons
        start_session_btn.disabled = not is_connected or is_session_active
        end_session_btn.disabled = not is_connected or not is_session_active
    
    def _setup_handlers(self) -> None:
        """Setup WebSocket and message handlers."""
        # WebSocket event handlers
        self.websocket_client.on_connect = self._on_websocket_connect
        self.websocket_client.on_disconnect = self._on_websocket_disconnect
        self.websocket_client.on_message = self._on_websocket_message
        self.websocket_client.on_error = self._on_websocket_error
        
        # Message handlers
        self.message_handler.add_session_handler(self._on_session_message)
        self.message_handler.add_audio_handler(self._on_audio_message)
        self.message_handler.add_error_handler(self._on_error_message)
        self.message_handler.add_general_handler(self._on_general_message)
        
        # Session state change handler
        self.session_state.add_status_change_callback(self._on_session_status_change)
    
    async def _on_websocket_connect(self) -> None:
        """Handle WebSocket connection event."""
        logger.info("WebSocket connected")
        
    async def _on_websocket_disconnect(self) -> None:
        """Handle WebSocket disconnection event."""
        logger.info("WebSocket disconnected")
        self._update_status("Disconnected")
        
        # Reset session if active
        if self.session_state.is_active:
            self.session_state.reset()
            self._update_session_info()
    
    async def _on_websocket_message(self, message: dict) -> None:
        """Handle incoming WebSocket message."""
        try:
            # Route through message handler
            await self.message_handler.handle_message(message)
            
            # Update statistics
            if self.parent_app and hasattr(self.parent_app, "status_bar"):
                self.parent_app.status_bar.increment_message_count()
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            self.event_logger.log_error_event(
                "message_processing_error",
                f"Error processing message: {e}",
                {"message": message}
            )
    
    async def _on_websocket_error(self, error: Exception) -> None:
        """Handle WebSocket error event."""
        logger.error(f"WebSocket error: {error}")
        self.last_error = str(error)
        self._update_status("Error")
        
        self.event_logger.log_error_event(
            "websocket_error",
            f"WebSocket error: {error}",
            {"error": str(error), "error_type": type(error).__name__}
        )
        
        if self.parent_app and hasattr(self.parent_app, "status_bar"):
            self.parent_app.status_bar.increment_error_count()
    
    async def _on_session_message(self, message_type: str, message: dict) -> None:
        """Handle session-related messages."""
        if message_type == "session.accepted":
            session_id = message.get("sessionId")
            self.session_state.accept_session(session_id)
            self._update_session_info()
            
            self.event_logger.log_session_event(
                "session.accepted",
                f"Session accepted: {session_id}",
                EventLevel.INFO,
                data=message
            )
            
        elif message_type == "session.end":
            self.session_state.end_session()
            self._update_session_info()
            
            self.event_logger.log_session_event(
                "session.end",
                "Session ended by server",
                EventLevel.INFO,
                data=message
            )
    
    async def _on_audio_message(self, message_type: str, message: dict) -> None:
        """Handle audio-related messages."""
        # Update session state based on audio events
        if message_type == "userStream.started":
            self.session_state.user_stream_started()
        elif message_type == "userStream.stopped":
            self.session_state.user_stream_stopped()
        elif message_type == "playStream.start":
            self.session_state.handle_bot_audio_start()
        elif message_type == "playStream.stop":
            self.session_state.handle_bot_audio_stop()
        elif message_type == "playStream.chunk":
            chunk_data = message.get("audioChunk", "")
            self.session_state.handle_bot_audio_chunk(chunk_data)
        
        self.event_logger.log_audio_event(
            message_type,
            f"Audio event: {message_type}",
            EventLevel.DEBUG,
            data={"conversation_id": message.get("conversationId")}
        )
    
    async def _on_error_message(self, message: dict) -> None:
        """Handle error messages from server."""
        self.session_state.handle_error(message)
        
        error_code = message.get("error", {}).get("code", "unknown")
        error_message = message.get("error", {}).get("message", "Unknown error")
        
        self.event_logger.log_error_event(
            "server_error",
            f"Server error: {error_code} - {error_message}",
            message
        )
        
        if self.parent_app and hasattr(self.parent_app, "status_bar"):
            self.parent_app.status_bar.increment_error_count()
    
    async def _on_general_message(self, message: dict) -> None:
        """Handle general messages."""
        message_type = message.get("type", "unknown")
        
        self.event_logger.log_message_event(
            message_type,
            f"Received message: {message_type}",
            EventLevel.DEBUG,
            data=message
        )
    
    def _on_session_status_change(self, old_status, new_status) -> None:
        """Handle session status changes."""
        self._update_session_info()
        
        if self.parent_app and hasattr(self.parent_app, "events_panel"):
            self.parent_app.events_panel.add_event(
                f"session_status_change", 
                status="info", 
                details=f"Session status: {old_status.value} → {new_status.value}"
            )
    
    def _notify_connection_state_change(self, connected: bool) -> None:
        """Notify other components of connection state change."""
        if self.parent_app:
            # Notify audio panel
            if hasattr(self.parent_app, "audio_panel"):
                self.parent_app.audio_panel.set_connection_state(connected)
            
            # Notify controls panel
            if hasattr(self.parent_app, "controls_panel"):
                self.parent_app.controls_panel.set_connection_state(connected)
    
    def get_session_state(self) -> SessionState:
        """Get the current session state."""
        return self.session_state
    
    def get_event_logger(self) -> EventLogger:
        """Get the event logger."""
        return self.event_logger
    
    def get_connection_stats(self) -> dict:
        """Get connection statistics."""
        ws_stats = self.websocket_client.get_connection_stats()
        session_summary = self.session_state.get_session_summary()
        
        return {
            "websocket": ws_stats,
            "session": session_summary,
            "events": self.event_logger.get_statistics()
        } 