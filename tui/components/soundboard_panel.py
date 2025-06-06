"""
Soundboard Panel component for the Interactive TUI Validator.

This panel provides quick access to predefined audio phrases and files
for rapid call flow testing with pre-recorded caller responses.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, Grid
from textual.widgets import Static, Button, Label, Select
from textual.widget import Widget

logger = logging.getLogger(__name__)

class SoundboardPanel(Widget):
    """Panel for soundboard controls and predefined phrases."""
    
    CSS = """
    SoundboardPanel {
        background: $surface;
        border: solid $primary;
        height: auto;
        min-height: 15;
    }
    
    .soundboard-header {
        background: $primary;
        color: $primary-background;
        text-align: center;
        height: 1;
    }
    
    .soundboard-grid {
        layout: grid;
        grid-size: 3 4;
        grid-gutter: 1;
        height: 10;
        padding: 1;
    }
    
    .phrase-btn {
        height: 2;
        min-width: 15;
    }
    
    .controls-row {
        layout: horizontal;
        height: 2;
        align: center middle;
        padding: 1;
    }
    
    .status-row {
        height: 1;
        text-align: center;
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.parent_app = None
        
        # Soundboard configuration
        self.phrases = self._get_default_phrases()
        self.audio_files = self._get_audio_files()
        self.current_playing = None
        
        # State
        self.connected = False
        self.session_active = False
        self.current_conversation_id = None
        
    def compose(self) -> ComposeResult:
        """Create the soundboard panel layout."""
        with Vertical():
            # Header
            yield Static("🎵 Caller Soundboard", classes="soundboard-header")
            
            # Phrase buttons grid
            with Grid(classes="soundboard-grid"):
                for i, (label, _) in enumerate(self.phrases.items()):
                    yield Button(
                        label, 
                        id=f"phrase-{i}",
                        classes="phrase-btn",
                        disabled=True
                    )
            
            # Controls
            with Horizontal(classes="controls-row"):
                yield Label("Audio File:")
                yield Select(
                    [(Path(f).stem, f) for f in self.audio_files],
                    prompt="Select audio file...",
                    id="audio-file-select",
                    disabled=True
                )
                yield Button("▶️ Play File", id="play-file-btn", disabled=True)
                yield Button("⏹ Stop", id="stop-btn", disabled=True)
            
            # Status
            yield Static(
                "⚫ Disconnected - Connect and start session to use soundboard",
                id="soundboard-status",
                classes="status-row"
            )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id and event.button.id.startswith("phrase-"):
            # Extract phrase index
            phrase_idx = int(event.button.id.split("-")[1])
            phrase_keys = list(self.phrases.keys())
            if phrase_idx < len(phrase_keys):
                phrase_key = phrase_keys[phrase_idx]
                asyncio.create_task(self._send_phrase(phrase_key))
        
        elif event.button.id == "play-file-btn":
            asyncio.create_task(self._play_selected_file())
        
        elif event.button.id == "stop-btn":
            asyncio.create_task(self._stop_audio())
    
    async def _send_phrase(self, phrase_key: str) -> None:
        """Send a predefined phrase as audio."""
        if not self.session_active:
            logger.warning("Cannot send phrase: No active session")
            return
        
        phrase_data = self.phrases.get(phrase_key)
        if not phrase_data:
            logger.error(f"Phrase not found: {phrase_key}")
            return
        
        try:
            # Update status
            self._update_status(f"🎤 Sending: {phrase_key}")
            
            # Get audio file path
            audio_file = phrase_data.get("file")
            if audio_file and Path(audio_file).exists():
                # Send file audio
                await self._send_audio_file(audio_file, phrase_key)
            else:
                # Send text-to-speech (fallback)
                text = phrase_data.get("text", phrase_key)
                await self._send_text_as_speech(text, phrase_key)
            
            # Log to events
            if self.parent_app and hasattr(self.parent_app, "events_panel"):
                self.parent_app.events_panel.add_event(
                    "soundboard_phrase", status="info",
                    details=f"Sent phrase: {phrase_key}"
                )
                
        except Exception as e:
            logger.error(f"Error sending phrase {phrase_key}: {e}")
            self._update_status("❌ Error sending phrase")
    
    async def _send_audio_file(self, audio_file: str, phrase_name: str) -> None:
        """Send an audio file as user input."""
        if not self.parent_app or not hasattr(self.parent_app, "connection_panel"):
            return
        
        connection_panel = self.parent_app.connection_panel
        if not connection_panel.websocket_client.connected:
            return
        
        try:
            # Load and chunk the audio file
            from tui.utils.audio_utils import AudioUtils
            
            audio_data, sample_rate, channels = AudioUtils.load_audio_file(audio_file, target_sample_rate=16000)
            if not audio_data:
                logger.error(f"Failed to load audio file: {audio_file}")
                return
            
            # Chunk audio for streaming (1 second chunks)
            audio_chunks = AudioUtils.chunk_audio_by_duration(
                audio_data, sample_rate, 1000, channels
            )
            
            # Get session state
            session_state = connection_panel.get_session_state()
            if not session_state.conversation_id:
                logger.error("No active conversation")
                return
            
            # Send userStream.start
            from tui.websocket.message_handler import SessionMessageBuilder
            start_message = SessionMessageBuilder.create_user_stream_start(
                session_state.conversation_id
            )
            await connection_panel.websocket_client.send_message(start_message)
            
            # Send audio chunks
            total_chunks = len(audio_chunks)
            for i, chunk in enumerate(audio_chunks):
                # Convert to base64
                chunk_b64 = AudioUtils.convert_to_base64(chunk)
                
                # Send chunk
                chunk_message = SessionMessageBuilder.create_user_stream_chunk(
                    session_state.conversation_id, chunk_b64
                )
                await connection_panel.websocket_client.send_message(chunk_message)
                
                # Update progress
                progress = int((i + 1) / total_chunks * 100)
                self._update_status(f"🎤 Sending {phrase_name}: {progress}%")
                
                # Small delay between chunks (simulate real-time)
                await asyncio.sleep(0.95)  # Slightly less than 1 second for smoother playback
            
            # Send userStream.stop
            stop_message = SessionMessageBuilder.create_user_stream_stop(
                session_state.conversation_id
            )
            await connection_panel.websocket_client.send_message(stop_message)
            
            self._update_status(f"✅ Sent: {phrase_name}")
            await asyncio.sleep(2)  # Show success for 2 seconds
            self._update_status_connected()
            
        except Exception as e:
            logger.error(f"Error sending audio file: {e}")
            self._update_status("❌ Error sending audio")
    
    async def _send_text_as_speech(self, text: str, phrase_name: str) -> None:
        """Send text as speech (placeholder for TTS)."""
        # For now, just log that we would send this as TTS
        logger.info(f"Would convert to speech: {text}")
        self._update_status(f"📝 Text-to-speech not implemented: {phrase_name}")
        await asyncio.sleep(2)
        self._update_status_connected()
    
    async def _play_selected_file(self) -> None:
        """Play the selected audio file."""
        file_select = self.query_one("#audio-file-select", Select)
        if file_select.value == Select.BLANK:
            return
        
        audio_file = file_select.value
        if not Path(audio_file).exists():
            logger.error(f"Audio file not found: {audio_file}")
            return
        
        # Send the selected file
        phrase_name = Path(audio_file).stem
        await self._send_audio_file(audio_file, phrase_name)
    
    async def _stop_audio(self) -> None:
        """Stop current audio playback."""
        self.current_playing = None
        self._update_status_connected()
        
        if self.parent_app and hasattr(self.parent_app, "events_panel"):
            self.parent_app.events_panel.add_event(
                "soundboard_stop", status="info",
                details="Audio playback stopped"
            )
    
    def set_connection_state(self, connected: bool) -> None:
        """Update controls based on connection state."""
        self.connected = connected
        self._update_button_states()
        
        if connected:
            self._update_status("🟢 Connected - Start session to use soundboard")
        else:
            self._update_status("⚫ Disconnected")
    
    def set_session_state(self, active: bool, conversation_id: str = None) -> None:
        """Update controls based on session state."""
        self.session_active = active
        if conversation_id:
            self.current_conversation_id = conversation_id
        self._update_button_states()
        
        if active:
            self._update_status_connected()
        else:
            self._update_status("🟡 Session inactive")
    
    def _update_button_states(self) -> None:
        """Update button enabled/disabled states."""
        can_send = self.connected and self.session_active
        
        # Update phrase buttons
        for i in range(len(self.phrases)):
            try:
                btn = self.query_one(f"#phrase-{i}", Button)
                btn.disabled = not can_send
            except:
                pass
        
        # Update controls
        try:
            file_select = self.query_one("#audio-file-select", Select)
            play_btn = self.query_one("#play-file-btn", Button)
            stop_btn = self.query_one("#stop-btn", Button)
            
            file_select.disabled = not can_send
            play_btn.disabled = not can_send
            stop_btn.disabled = not can_send
        except:
            pass
    
    def _update_status(self, message: str) -> None:
        """Update status display."""
        try:
            status_widget = self.query_one("#soundboard-status", Static)
            status_widget.update(message)
        except:
            pass
    
    def _update_status_connected(self) -> None:
        """Update status for connected and active session."""
        if self.session_active:
            self._update_status("🟢 Ready - Click phrases to send as caller audio")
        elif self.connected:
            self._update_status("🟡 Connected - Start session to use soundboard")
        else:
            self._update_status("⚫ Disconnected")
    
    def _get_default_phrases(self) -> Dict[str, Dict]:
        """Get default phrase configuration."""
        return {
            "Hello": {
                "text": "Hello, how are you doing today?",
                "file": "static/hello.wav"
            },
            "Bank Info": {
                "text": "Can you tell me about your bank services?",
                "file": "static/tell_me_about_your_bank.wav"
            },
            "Card Lost": {
                "text": "I need to report a lost credit card",
                "file": "static/card_lost.wav"
            },
            "Balance": {
                "text": "What is my account balance?",
                "file": "static/balance_inquiry.wav"
            },
            "Transfer": {
                "text": "I want to transfer money to another account",
                "file": "static/transfer_request.wav"
            },
            "Loan": {
                "text": "I'm interested in applying for a loan",
                "file": "static/loan_inquiry.wav"
            },
            "Thank You": {
                "text": "Thank you for your help today",
                "file": "static/thank_you.wav"
            },
            "Goodbye": {
                "text": "Goodbye, have a great day",
                "file": "static/goodbye.wav"
            },
            "Yes": {
                "text": "Yes, that's correct",
                "file": "static/yes.wav"
            },
            "No": {
                "text": "No, that's not right",
                "file": "static/no.wav"
            },
            "Help": {
                "text": "I need help with my account",
                "file": "static/help.wav"
            },
            "Repeat": {
                "text": "Could you please repeat that?",
                "file": "static/repeat.wav"
            }
        }
    
    def _get_audio_files(self) -> List[str]:
        """Get list of available audio files."""
        audio_extensions = {".wav", ".mp3", ".flac", ".ogg"}
        audio_dirs = ["static", "test_audio", "audio_samples"]
        
        audio_files = []
        
        for audio_dir in audio_dirs:
            dir_path = Path(audio_dir)
            if dir_path.exists():
                for file_path in dir_path.iterdir():
                    if file_path.suffix.lower() in audio_extensions:
                        audio_files.append(str(file_path))
        
        return sorted(audio_files) 