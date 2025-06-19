#!/usr/bin/env python3
"""
Main entry point for the Call Review Interface.

Usage:
    python -m tui.review_main
    python tui/review_main.py [--demo] [--session-dir <path>]
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Static

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from tui.components.audio_panel import AudioPanel
from tui.components.events_panel import EventsPanel
from tui.components.function_calls_panel import FunctionCallsPanel
from tui.components.metadata_panel import MetadataPanel
from tui.components.search_filter_box import SearchFilterBox
from tui.components.state_timeline_panel import StateTimelinePanel
from tui.components.status_bar import StatusBar
from tui.components.transcript_panel import TranscriptPanel
from tui.models.review_session import ReviewSession
from tui.models.review_session_loader import ReviewSessionLoader

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CallReviewInterface(App):
    """
    Call Review Interface for analyzing completed calls.

    Provides a comprehensive interface for reviewing call recordings,
    transcripts, logs, function calls, and state machine transitions
    with synchronized navigation and filtering.
    """

    TITLE = "Call Review Interface"
    SUB_TITLE = "Comprehensive Call Analysis Tool"

    CSS = """
    Screen {
        layout: vertical;
    }
    
    .top-section {
        height: auto;
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
    
    .metadata-section {
        height: auto;
        min-height: 3;
        max-height: 3;
    }
    
    .search-section {
        height: auto;
        min-height: 3;
        max-height: 3;
    }
    
    .timeline-section {
        height: auto;
        min-height: 8;
        max-height: 12;
    }
    
    .transcript-section {
        height: 1fr;
        min-height: 10;
    }
    
    .audio-section {
        height: auto;
        min-height: 8;
        max-height: 12;
    }
    
    .events-section {
        height: 40%;
    }
    
    .functions-section {
        height: 30%;
    }
    
    .status-section {
        height: 30%;
    }
    
    .session-selector {
        background: $surface;
        border: solid $primary;
        height: auto;
        min-height: 5;
        layout: vertical;
        padding: 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("l", "load_session", "Load Session"),
        Binding("d", "demo_session", "Demo Session"),
        Binding("f", "focus_filter", "Filter", key_display="/"),
        Binding("h", "help", "Help"),
        # Playback controls
        Binding("space", "toggle_playback", "Play/Pause"),
        Binding("left", "seek_backward", "◀ 5s"),
        Binding("right", "seek_forward", "▶ 5s"),
        Binding("shift+left", "seek_backward_long", "◀ 30s"),
        Binding("shift+right", "seek_forward_long", "▶ 30s"),
        Binding("home", "seek_start", "⏮ Start"),
        Binding("end", "seek_end", "⏭ End"),
        # Navigation
        Binding("ctrl+t", "focus_transcript", "Transcript"),
        Binding("ctrl+e", "focus_events", "Events"),
        Binding("ctrl+f", "focus_functions", "Functions"),
        Binding("ctrl+s", "focus_timeline", "Timeline"),
        # System
        ("ctrl+r", "reload_session", "Reload"),
        ("ctrl+c", "clear_all", "Clear"),
    ]

    def __init__(self, session_dir: Optional[str] = None, demo_mode: bool = False):
        super().__init__()

        # Configuration
        self.session_dir = session_dir
        self.demo_mode = demo_mode

        # Core components
        self.review_session: Optional[ReviewSession] = None
        self.session_loader = ReviewSessionLoader()

        # Component references
        self.metadata_panel: Optional[MetadataPanel] = None
        self.search_box: Optional[SearchFilterBox] = None
        self.timeline_panel: Optional[StateTimelinePanel] = None
        self.transcript_panel: Optional[TranscriptPanel] = None
        self.audio_panel: Optional[AudioPanel] = None
        self.events_panel: Optional[EventsPanel] = None
        self.functions_panel: Optional[FunctionCallsPanel] = None
        self.status_bar: Optional[StatusBar] = None

        # Session selector
        self.session_selector: Optional[Static] = None
        self.available_sessions = []
        self.selected_session_index = 0

        # Current state
        self.showing_session_selector = True

    def compose(self) -> ComposeResult:
        """Create the UI layout."""
        yield Header()

        # Session selector (shown initially)
        self.session_selector = Static(classes="session-selector")
        yield self.session_selector

        # Main interface (hidden initially)
        with Container(classes="main-interface", id="main-interface"):
            # Top section with metadata and search
            with Vertical(classes="top-section"):
                self.metadata_panel = MetadataPanel(classes="metadata-section")
                yield self.metadata_panel

                self.search_box = SearchFilterBox(classes="search-section")
                yield self.search_box

            # Main content area
            with Horizontal(classes="main-container"):
                # Left panel (70% width)
                with Vertical(classes="left-panel"):
                    # State timeline
                    self.timeline_panel = StateTimelinePanel(classes="timeline-section")
                    yield self.timeline_panel

                    # Transcript (expandable)
                    self.transcript_panel = TranscriptPanel(
                        classes="transcript-section"
                    )
                    yield self.transcript_panel

                    # Audio controls
                    self.audio_panel = AudioPanel(classes="audio-section")
                    yield self.audio_panel

                # Right panel (30% width)
                with Vertical(classes="right-panel"):
                    # Events log
                    self.events_panel = EventsPanel(classes="events-section")
                    yield self.events_panel

                    # Function calls
                    self.functions_panel = FunctionCallsPanel(
                        classes="functions-section"
                    )
                    yield self.functions_panel

        # Status bar at bottom
        self.status_bar = StatusBar()
        yield self.status_bar

        yield Footer()

    async def on_mount(self) -> None:
        """Initialize the application after mounting."""
        self.title = self.TITLE
        self.sub_title = self.SUB_TITLE

        # Hide main interface initially
        main_interface = self.query_one("#main-interface")
        main_interface.display = False

        # Setup component connections
        await self._setup_components()

        # Load initial session
        if self.demo_mode:
            await self._load_demo_session()
        elif self.session_dir:
            await self._load_session_from_directory(self.session_dir)
        else:
            await self._show_session_selector()

        logger.info("Call Review Interface initialized")

    async def _setup_components(self) -> None:
        """Setup component connections and callbacks."""
        # Set up seek callbacks
        if self.timeline_panel:
            self.timeline_panel.set_seek_callback(self._on_seek_request)

        # Set up filter callbacks
        if self.search_box:
            self.search_box.set_filter_callback(self._on_filter_applied)

        # Set up transcript click-to-seek (enhanced existing component)
        if self.transcript_panel:
            # This would require enhancing the existing transcript panel
            pass

        # Set up function calls click-to-seek
        if self.functions_panel:
            # This would require enhancing the existing function calls panel
            pass

    async def _show_session_selector(self) -> None:
        """Show the session selector interface."""
        self.showing_session_selector = True

        # Find available sessions
        self.available_sessions = self.session_loader.find_available_sessions()

        # Update session selector display
        await self._update_session_selector()

    async def _update_session_selector(self) -> None:
        """Update the session selector display."""
        if not self.session_selector:
            return

        if not self.available_sessions:
            content = """
[bold cyan]Call Review Interface[/bold cyan]

[yellow]No call sessions found.[/yellow]

Options:
[green]d[/green] - Load demo session
[green]q[/green] - Quit

Searched directories:
- demo/
- demo/no_hang_up/
- validation_output/
"""
        else:
            content = f"""
[bold cyan]Call Review Interface[/bold cyan]

[green]Available Sessions ({len(self.available_sessions)}):[/green]

"""
            for i, session in enumerate(self.available_sessions):
                marker = ">" if i == self.selected_session_index else " "
                summary = self.session_loader.get_session_summary(session)
                content += f"{marker} {i+1:2d}. {summary}\n"

            content += """
Navigation:
[green]↑/↓[/green] - Select session
[green]Enter[/green] - Load selected session
[green]d[/green] - Load demo session
[green]q[/green] - Quit
"""

        self.session_selector.update(content)

    async def _load_demo_session(self) -> None:
        """Load a demo session for testing."""
        demo_session = self.session_loader.create_demo_session()
        if demo_session:
            await self._set_review_session(demo_session)
        else:
            if self.status_bar:
                self.status_bar.update_status("Failed to create demo session")

    async def _load_session_from_directory(self, session_dir: str) -> None:
        """Load a session from a specific directory."""
        session_path = Path(session_dir)
        if not session_path.exists():
            logger.error(f"Session directory not found: {session_dir}")
            return

        # Create session info manually
        session_info = {
            "call_id": session_path.name,
            "path": str(session_path),
            "has_audio": True,  # Assume true for manual loading
            "has_transcript": True,
            "has_metadata": True,
            "has_events": True,
            "directory_name": session_path.name,
        }

        session = self.session_loader.load_session(session_info)
        if session:
            await self._set_review_session(session)
        else:
            logger.error(f"Failed to load session from: {session_dir}")

    async def _set_review_session(self, session: ReviewSession) -> None:
        """Set the current review session and update all components."""
        self.review_session = session

        # Hide session selector and show main interface
        if self.showing_session_selector:
            self.session_selector.display = False
            main_interface = self.query_one("#main-interface")
            main_interface.display = True
            self.showing_session_selector = False

        # Update all components with the new session
        if self.metadata_panel:
            self.metadata_panel.set_review_session(session)

        if self.search_box:
            self.search_box.set_review_session(session)

        if self.timeline_panel:
            self.timeline_panel.set_review_session(session)

        if self.transcript_panel:
            await self._update_transcript_panel(session)

        if self.events_panel:
            await self._update_events_panel(session)

        if self.functions_panel:
            await self._update_functions_panel(session)

        # Update status
        if self.status_bar:
            self.status_bar.update_status(f"Loaded: {session.call_id}")
            if session.metadata:
                self.status_bar.update_audio_status(
                    f"Duration: {session.metadata.get_duration_str()}"
                )

        logger.info(f"Review session loaded: {session.call_id}")

    async def _update_transcript_panel(self, session: ReviewSession) -> None:
        """Update transcript panel with session data."""
        if not self.transcript_panel:
            return

        # Clear existing transcript
        self.transcript_panel.clear_transcript()

        # Add transcript entries
        for entry in session.filtered_transcript:
            if entry.speaker == "user":
                self.transcript_panel.add_user_message(entry.text, entry.get_time_str())
            elif entry.speaker == "bot":
                self.transcript_panel.add_bot_message(entry.text, entry.get_time_str())
            else:
                self.transcript_panel.add_system_message(
                    entry.text, entry.get_time_str()
                )

    async def _update_events_panel(self, session: ReviewSession) -> None:
        """Update events panel with session data."""
        if not self.events_panel:
            return

        # Clear existing events
        self.events_panel.clear_events()

        # Add log entries
        for entry in session.filtered_logs:
            status = "error" if entry.level in ["ERROR", "CRITICAL"] else "info"
            event_type = f"{entry.module}.{entry.level.lower()}"
            details = f"[{entry.get_time_str()}] {entry.message}"
            self.events_panel.add_event(event_type, status=status, details=details)

    async def _update_functions_panel(self, session: ReviewSession) -> None:
        """Update function calls panel with session data."""
        if not self.functions_panel:
            return

        # Add function calls
        for call in session.filtered_function_calls:
            self.functions_panel.add_function_call(
                call.function_name, call.arguments, call.get_time_str()
            )

            if call.result:
                self.functions_panel.add_function_result(
                    call.function_name, call.result, call.get_time_str()
                )

    def _on_seek_request(self, timestamp: float) -> None:
        """Handle seek requests from components."""
        if self.review_session:
            self.review_session.seek_to_timestamp(timestamp)

        # Update audio panel if available
        if self.audio_panel:
            # This would require enhancing the audio panel for review mode
            pass

        # Update status
        if self.status_bar:
            minutes = int(timestamp // 60)
            seconds = int(timestamp % 60)
            self.status_bar.update_status(f"Position: {minutes}:{seconds:02d}")

    def _on_filter_applied(self, query: str) -> None:
        """Handle filter application across all panels."""
        if not self.review_session:
            return

        # Update all panels with filtered data
        asyncio.create_task(self._update_transcript_panel(self.review_session))
        asyncio.create_task(self._update_events_panel(self.review_session))
        asyncio.create_task(self._update_functions_panel(self.review_session))

    # Action handlers
    def action_load_session(self) -> None:
        """Load a new session."""
        if self.showing_session_selector and self.available_sessions:
            selected = self.available_sessions[self.selected_session_index]
            session = self.session_loader.load_session(selected)
            if session:
                asyncio.create_task(self._set_review_session(session))
        else:
            asyncio.create_task(self._show_session_selector())

    def action_demo_session(self) -> None:
        """Load demo session."""
        asyncio.create_task(self._load_demo_session())

    def action_focus_filter(self) -> None:
        """Focus the search/filter box."""
        if self.search_box:
            self.search_box.focus_search()

    def action_toggle_playback(self) -> None:
        """Toggle audio playback."""
        # This would require enhancing audio panel for review mode
        pass

    def action_seek_backward(self) -> None:
        """Seek backward 5 seconds."""
        if self.review_session:
            new_time = max(0.0, self.review_session.current_timestamp - 5.0)
            self._on_seek_request(new_time)

    def action_seek_forward(self) -> None:
        """Seek forward 5 seconds."""
        if self.review_session:
            max_time = self.review_session.get_duration()
            new_time = min(max_time, self.review_session.current_timestamp + 5.0)
            self._on_seek_request(new_time)

    def action_seek_backward_long(self) -> None:
        """Seek backward 30 seconds."""
        if self.review_session:
            new_time = max(0.0, self.review_session.current_timestamp - 30.0)
            self._on_seek_request(new_time)

    def action_seek_forward_long(self) -> None:
        """Seek forward 30 seconds."""
        if self.review_session:
            max_time = self.review_session.get_duration()
            new_time = min(max_time, self.review_session.current_timestamp + 30.0)
            self._on_seek_request(new_time)

    def action_seek_start(self) -> None:
        """Seek to beginning."""
        self._on_seek_request(0.0)

    def action_seek_end(self) -> None:
        """Seek to end."""
        if self.review_session:
            self._on_seek_request(self.review_session.get_duration())

    def action_reload_session(self) -> None:
        """Reload current session."""
        if self.review_session:
            # Re-apply current filter to refresh display
            current_filter = self.review_session.filter_query
            self.review_session.apply_filter(current_filter)
            self._on_filter_applied(current_filter)

    def action_clear_all(self) -> None:
        """Clear all filters and reset view."""
        if self.search_box:
            self.search_box.clear_all()

    def action_help(self) -> None:
        """Show help information."""
        help_text = """
Call Review Interface Help

Navigation:
  ↑/↓ - Navigate sessions (in selector)
  Enter - Load selected session
  Space - Toggle playback
  ←/→ - Seek ±5s
  Shift+←/→ - Seek ±30s
  Home/End - Seek to start/end

Filtering:
  / - Focus filter box
  Type to filter across all panels
  Esc - Clear filter

Panels:
  Ctrl+T - Focus transcript
  Ctrl+E - Focus events
  Ctrl+F - Focus functions
  Ctrl+S - Focus timeline

Actions:
  l - Load session
  d - Demo session
  Ctrl+R - Reload
  Ctrl+C - Clear filters
  q - Quit

Click on timeline states or transcript entries to seek.
"""
        if self.transcript_panel:
            self.transcript_panel.add_system_message(help_text)


def main():
    """Main entry point with command line arguments."""
    parser = argparse.ArgumentParser(description="Call Review Interface")
    parser.add_argument("--demo", action="store_true", help="Load demo session")
    parser.add_argument("--session-dir", type=str, help="Path to session directory")

    args = parser.parse_args()

    app = CallReviewInterface(session_dir=args.session_dir, demo_mode=args.demo)
    app.run()


if __name__ == "__main__":
    main()
