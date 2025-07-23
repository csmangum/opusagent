#!/usr/bin/env python3
"""
Main entry point for the Interactive TUI Validator.

Usage:
    python -m tui.main
    python tui/main.py
"""

import asyncio
import os
import sys
import logging
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Footer, Header

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from tui.components.connection_panel import ConnectionPanel
from tui.components.audio_panel import AudioPanel
from tui.components.events_panel import EventsPanel
from tui.components.transcript_panel import TranscriptPanel
from tui.components.controls_panel import ControlsPanel
from tui.components.status_bar import StatusBar
from tui.components.soundboard_panel import SoundboardPanel
from tui.utils.config import TUIConfig
from tui.models.event_logger import EventLogger, LogEvent

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class InteractiveTUIValidator(App):
    """
    Interactive TUI Validator for TelephonyRealtimeBridge Call Flow Testing.
    
    Provides a comprehensive interface for testing AudioCodes VoiceAI Connect
    Enterprise (VAIC) integration with OpenAI Realtime API.
    """
    
    TITLE = "TelephonyRealtimeBridge Interactive Validator"
    SUB_TITLE = "AudioCodes VAIC ↔ OpenAI Realtime API Testing"
    
    CSS = """
    Screen {
        layout: vertical;
    }
    
    .main-container {
        layout: horizontal;
        height: 1fr;
    }
    
    .left-panel {
        width: 70%;
        layout: vertical;
    }
    
    .right-panel {
        width: 30%;
        layout: vertical;
    }
    
    .connection-section {
        height: auto;
        min-height: {MIN_HEIGHT_CONNECTION_SECTION};
    }
    
    .controls-section {
        height: auto;
        min-height: 3;
    }
    
    .audio-section {
        height: auto;
        min-height: 8;
    }
    
    .debug-section {
        height: 1fr;
    }
    
    .events-section {
        height: 40%;
    }
    
    .transcript-section {
        height: 30%;
    }
    
    .message-log-section {
        height: 30%;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("c", "connect", "Connect"),
        Binding("d", "disconnect", "Disconnect"),
        Binding("s", "start_session", "Start Session"),
        Binding("e", "end_session", "End Session"),
        Binding("r", "start_recording", "Start Recording"),
        Binding("t", "stop_recording", "Stop Recording"),
        Binding("h", "help", "Help"),
        # Soundboard shortcuts
        Binding("1", "send_phrase_1", "Hello"),
                Binding("2", "send_phrase_2", "Policy Info"),
        Binding("3", "send_phrase_3", "File Claim"),
        Binding("4", "send_phrase_4", "Coverage"),
        # System shortcuts
        ("ctrl+r", "restart", "Restart"),
        ("ctrl+l", "clear_logs", "Clear Logs"),
        ("ctrl+e", "export_logs", "Export Logs"),
    ]

    def __init__(self):
        super().__init__()
        self.config = TUIConfig()
        
        # Component references
        self.connection_panel = None
        self.audio_panel = None
        self.events_panel = None
        self.transcript_panel = None
        self.controls_panel = None
        self.status_bar = None
        self.soundboard_panel = None
        
        # Central event logger for the application
        self.event_logger = None

    def compose(self) -> ComposeResult:
        """Create the UI layout."""
        yield Header()
        
        with Container(classes="main-container"):
            # Left panel (70% width)
            with Vertical(classes="left-panel"):
                # Connection status and controls
                self.connection_panel = ConnectionPanel(classes="connection-section")
                yield self.connection_panel
                
                # Call flow controls
                self.controls_panel = ControlsPanel(classes="controls-section")
                yield self.controls_panel
                
                # Audio visualization and controls
                self.audio_panel = AudioPanel(classes="audio-section")
                yield self.audio_panel
                
                # Soundboard for quick phrase testing
                self.soundboard_panel = SoundboardPanel(classes="audio-section")
                yield self.soundboard_panel
            
            # Right panel (30% width)
            with Vertical(classes="right-panel"):
                # Session events
                self.events_panel = EventsPanel(classes="events-section")
                yield self.events_panel
                
                # Live transcript
                self.transcript_panel = TranscriptPanel(classes="transcript-section")
                yield self.transcript_panel
                
                # Message log (takes remaining space)
                yield Container(classes="message-log-section")
        
        # Status bar at bottom
        self.status_bar = StatusBar()
        yield self.status_bar
        
        yield Footer()

    async def on_mount(self) -> None:
        """Initialize the application after mounting."""
        self.title = self.TITLE
        self.sub_title = self.SUB_TITLE
        
        # Set up component references and event handlers
        await self._setup_components()
        
        # Log application startup
        if self.event_logger:
            self.event_logger.log_event(
                "app_startup",
                "TUI Validator started successfully",
                data={"config": self.config.to_dict()}
            )
            
        logger.info("TUI Validator initialized successfully")

    async def _setup_components(self) -> None:
        """Setup and connect all components."""
        # Set parent app reference for all components
        components = [
            self.connection_panel,
            self.controls_panel, 
            self.audio_panel,
            self.events_panel,
            self.transcript_panel,
            self.status_bar,
            self.soundboard_panel
        ]
        
        for component in components:
            if component:
                component.parent_app = self
        
        # Get the central event logger from connection panel
        if self.connection_panel:
            self.event_logger = self.connection_panel.get_event_logger()
            
            # Connect event logger to events panel
            if self.events_panel and self.event_logger:
                self.event_logger.add_event_handler(self._on_event_logged)
        
        # Setup component interconnections
        await self._setup_component_connections()
    
    async def _setup_component_connections(self) -> None:
        """Setup connections between components."""
        if not self.connection_panel:
            return
            
        # Get session state and message handler from connection panel
        session_state = self.connection_panel.get_session_state()
        message_handler = self.connection_panel.message_handler
        
        # Connect session events to transcript panel
        if self.transcript_panel and message_handler:
            message_handler.add_general_handler(self._on_message_for_transcript)
        
        # Connect session state changes to status bar updates
        if self.status_bar and session_state:
            session_state.add_status_change_callback(self._on_session_status_for_status_bar)
            session_state.add_metrics_update_callback(self._on_metrics_update_for_status_bar)
    
    def _on_event_logged(self, event: LogEvent) -> None:
        """Handle events logged to the central event logger."""
        if self.events_panel:
            # Convert LogEvent to events panel format
            status_map = {
                "debug": "info",
                "info": "info", 
                "warning": "warning",
                "error": "error",
                "critical": "error"
            }
            
            status = status_map.get(event.level.value, "info")
            details = event.message
            
            # Add additional context if available
            if event.data:
                context_info = []
                if "conversation_id" in event.data:
                    conv_id = event.data["conversation_id"]
                    if len(conv_id) > 8:
                        conv_id = conv_id[:8] + "..."
                    context_info.append(f"Conv: {conv_id}")
                
                if context_info:
                    details = f"{details} ({', '.join(context_info)})"
            
            self.events_panel.add_event(event.event_type, status=status, details=details)
    
    async def _on_message_for_transcript(self, message: dict) -> None:
        """Handle messages for transcript display."""
        if not self.transcript_panel:
            return
            
        message_type = message.get("type", "")
        
        # Handle transcript-related messages
        if message_type == "conversation.item.input_audio_transcription.completed":
            transcript = message.get("transcript", "")
            if transcript:
                self.transcript_panel.add_user_message(transcript)
                
        elif message_type.startswith("response.") and "content" in message:
            # Handle bot responses
            content = message.get("content", [])
            for item in content:
                if item.get("type") == "text":
                    text = item.get("text", "")
                    if text:
                        self.transcript_panel.add_bot_message(text)
    
    def _on_session_status_for_status_bar(self, old_status, new_status) -> None:
        """Handle session status changes for status bar."""
        if self.status_bar:
            audio_status = "Idle"
            if new_status.value == "active":
                audio_status = "Session Active"
            elif new_status.value == "initiating":
                audio_status = "Starting Session"
            elif new_status.value == "ending":
                audio_status = "Ending Session"
            
            self.status_bar.update_audio_status(audio_status)
    
    def _on_metrics_update_for_status_bar(self, metrics) -> None:
        """Handle metrics updates for status bar."""
        if self.status_bar and metrics.latency_ms:
            self.status_bar.update_latency(metrics.latency_ms)

    def action_connect(self) -> None:
        """Handle connect action."""
        if self.connection_panel:
            asyncio.create_task(self.connection_panel._async_connect())

    def action_disconnect(self) -> None:
        """Handle disconnect action.""" 
        if self.connection_panel:
            asyncio.create_task(self.connection_panel._async_disconnect())
    
    def action_start_session(self) -> None:
        """Handle start session action."""
        if self.connection_panel:
            asyncio.create_task(self.connection_panel._async_start_session())
    
    def action_end_session(self) -> None:
        """Handle end session action."""
        if self.connection_panel:
            asyncio.create_task(self.connection_panel._async_end_session())

    def action_start_recording(self) -> None:
        """Handle start recording action."""
        if self.audio_panel:
            self.audio_panel.start_stream()

    def action_stop_recording(self) -> None:
        """Handle stop recording action."""
        if self.audio_panel:
            self.audio_panel.stop_stream()

    def action_send_phrase_1(self) -> None:
        """Send phrase 1 (Hello)."""
        if self.soundboard_panel and self.soundboard_panel.session_active:
            asyncio.create_task(self.soundboard_panel._send_phrase("Hello"))

    def action_send_phrase_2(self) -> None:
        """Send phrase 2 (Bank Info)."""
        if self.soundboard_panel and self.soundboard_panel.session_active:
            asyncio.create_task(self.soundboard_panel._send_phrase("Bank Info"))

    def action_send_phrase_3(self) -> None:
        """Send phrase 3 (Card Lost)."""
        if self.soundboard_panel and self.soundboard_panel.session_active:
            asyncio.create_task(self.soundboard_panel._send_phrase("Card Lost"))

    def action_send_phrase_4(self) -> None:
        """Send phrase 4 (Balance)."""
        if self.soundboard_panel and self.soundboard_panel.session_active:
            asyncio.create_task(self.soundboard_panel._send_phrase("Balance"))

    def action_clear_logs(self) -> None:
        """Clear all logs and events."""
        if self.events_panel:
            self.events_panel.clear_events()
        if self.transcript_panel:
            self.transcript_panel.clear_transcript()
        if self.event_logger:
            self.event_logger.clear_events()
        if self.status_bar:
            self.status_bar.reset_counters()
            
        self.bell()  # Audio feedback

    def action_export_logs(self) -> None:
        """Export logs to file."""
        if self.event_logger:
            # Create export filename with timestamp
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"tui_validator_logs_{timestamp}.json"
            filepath = self.config.get_audio_file_path(filename)
            
            asyncio.create_task(self._async_export_logs(str(filepath)))

    async def _async_export_logs(self, filepath: str) -> None:
        """Async export logs to file."""
        try:
            success = await self.event_logger.export_logs(filepath, "json")
            if success:
                if self.events_panel:
                    self.events_panel.add_event(
                        "export_success", 
                        status="success", 
                        details=f"Logs exported to {filepath}"
                    )
                self.bell()  # Success feedback
            else:
                if self.events_panel:
                    self.events_panel.add_event(
                        "export_failed", 
                        status="error", 
                        details="Failed to export logs"
                    )
        except Exception as e:
            logger.error(f"Error exporting logs: {e}")
            if self.events_panel:
                self.events_panel.add_event(
                    "export_error", 
                    status="error", 
                    details=f"Export error: {e}"
                )

    def action_help(self) -> None:
        """Show help dialog."""
        help_text = """
TelephonyRealtimeBridge Interactive Validator

Keyboard Shortcuts:
  c - Connect to server
  d - Disconnect from server  
  s - Start session
  e - End session
  r - Start audio recording
  t - Stop audio recording
  
Soundboard (during active session):
  1 - Send "Hello" phrase
          2 - Send "Policy Info" phrase
        3 - Send "File Claim" phrase
        4 - Send "Coverage" phrase
  
System:
  Ctrl+L - Clear all logs
  Ctrl+E - Export logs
  Ctrl+R - Restart application
  q - Quit application
  h - Show this help

Getting Started:
1. Use 'c' to connect to the TelephonyRealtimeBridge server
2. Use 's' to start a session with the bot
3. Click soundboard buttons or use number keys to send phrases
4. Listen to bot responses through your speakers
5. Monitor function calls and conversation flow in real-time
"""
        
        if self.transcript_panel:
            self.transcript_panel.add_system_message(help_text)
        self.bell()

    def action_restart(self) -> None:
        """Restart the application."""
        self.exit(return_code=2)  # Use code 2 to indicate restart needed

    async def on_unmount(self) -> None:
        """Cleanup when app is shutting down."""
        # Disconnect gracefully
        if self.connection_panel:
            await self.connection_panel._async_disconnect()
        
        # Log shutdown
        if self.event_logger:
            self.event_logger.log_event(
                "app_shutdown",
                "TUI Validator shutting down",
            )
        
        logger.info("TUI Validator shutdown complete")


def main():
    """Main entry point."""
    app = InteractiveTUIValidator()
    app.run()


if __name__ == "__main__":
    main() 