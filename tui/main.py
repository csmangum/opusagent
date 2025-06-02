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
from tui.utils.config import TUIConfig


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
        min-height: 5;
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
        Binding("s", "start_call", "Start Call"),
        Binding("e", "end_call", "End Call"),
        Binding("h", "help", "Help"),
        ("ctrl+r", "restart", "Restart"),
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
                
                # Debug console (takes remaining space)
                yield Container(classes="debug-section")
            
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
        if self.connection_panel:
            self.connection_panel.parent_app = self
        if self.controls_panel:
            self.controls_panel.parent_app = self
        if self.audio_panel:
            self.audio_panel.parent_app = self
        if self.events_panel:
            self.events_panel.parent_app = self
        if self.transcript_panel:
            self.transcript_panel.parent_app = self
        if self.status_bar:
            self.status_bar.parent_app = self

    def action_connect(self) -> None:
        """Handle connect action."""
        if self.connection_panel:
            self.connection_panel.initiate_connection()

    def action_disconnect(self) -> None:
        """Handle disconnect action."""
        if self.connection_panel:
            self.connection_panel.disconnect()

    def action_start_call(self) -> None:
        """Handle start call action."""
        if self.controls_panel:
            self.controls_panel.start_call()

    def action_end_call(self) -> None:
        """Handle end call action."""
        if self.controls_panel:
            self.controls_panel.end_call()

    def action_help(self) -> None:
        """Show help dialog."""
        # TODO: Implement help dialog
        self.bell()

    def action_restart(self) -> None:
        """Restart the application."""
        self.exit(return_code=2)  # Use code 2 to indicate restart needed


def main():
    """Main entry point."""
    app = InteractiveTUIValidator()
    app.run()


if __name__ == "__main__":
    main() 