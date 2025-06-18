"""
Review session loader utilities for the Call Review Interface.

This module provides utilities for loading call review data from various
sources including demo directories, saved sessions, and export formats.
"""

import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

from .review_session import ReviewSession

logger = logging.getLogger(__name__)

class ReviewSessionLoader:
    """Utility class for loading review sessions from various sources."""
    
    def __init__(self):
        self.demo_directories = [
            Path("demo"),
            Path("demo/no_hang_up"),
            Path("validation_output"),
        ]
    
    def find_available_sessions(self) -> List[Dict[str, Any]]:
        """
        Find all available review sessions.
        
        Returns:
            List of session info dictionaries with keys:
            - call_id: Session identifier
            - path: Path to session data
            - has_audio: Whether audio file exists
            - has_transcript: Whether transcript exists
            - has_metadata: Whether metadata exists
        """
        sessions = []
        
        # Check demo directories
        for demo_dir in self.demo_directories:
            if demo_dir.exists():
                sessions.extend(self._scan_directory_for_sessions(demo_dir))
        
        # Check for individual call directories in demo
        demo_path = Path("demo")
        if demo_path.exists():
            for item in demo_path.iterdir():
                if item.is_dir() and item.name not in ["audio", "data"]:
                    sessions.extend(self._scan_directory_for_sessions(item))
        
        return sessions
    
    def _scan_directory_for_sessions(self, directory: Path) -> List[Dict[str, Any]]:
        """Scan a directory for session data files."""
        sessions = []
        
        # Look for audio files as session indicators
        audio_files = list(directory.glob("*.wav"))
        
        for audio_file in audio_files:
            session_info = self._analyze_session_directory(directory, audio_file)
            if session_info:
                sessions.append(session_info)
        
        # If no audio files, check if this looks like a session directory
        if not audio_files:
            session_info = self._analyze_session_directory(directory)
            if session_info:
                sessions.append(session_info)
        
        return sessions
    
    def _analyze_session_directory(self, directory: Path, audio_file: Optional[Path] = None) -> Optional[Dict[str, Any]]:
        """Analyze a directory to determine if it contains session data."""
        
        # Check for key files
        has_metadata = (directory / "call_metadata.json").exists()
        has_transcript = (directory / "transcript.json").exists()
        has_events = (directory / "session_events.json").exists()
        
        # Look for audio files if not provided
        if not audio_file:
            audio_candidates = [
                directory / "final_stereo_recording.wav",
                directory / "stereo_recording.wav",
                directory / "bot_audio.wav",
                directory / "caller_audio.wav",
            ]
            audio_file = next((f for f in audio_candidates if f.exists()), None)
        
        has_audio = audio_file is not None
        
        # Require at least audio or transcript to consider it a session
        if not (has_audio or has_transcript):
            return None
        
        # Generate call ID from directory name or audio file
        if audio_file:
            call_id = audio_file.stem
        else:
            call_id = directory.name
        
        return {
            "call_id": call_id,
            "path": str(directory),
            "audio_file": str(audio_file) if audio_file else None,
            "has_audio": has_audio,
            "has_transcript": has_transcript,
            "has_metadata": has_metadata,
            "has_events": has_events,
            "directory_name": directory.name,
        }
    
    def load_session(self, session_info: Dict[str, Any]) -> Optional[ReviewSession]:
        """
        Load a review session from session info.
        
        Args:
            session_info: Session info dictionary from find_available_sessions()
            
        Returns:
            Loaded ReviewSession or None if failed
        """
        try:
            call_id = session_info["call_id"]
            directory = Path(session_info["path"])
            
            session = ReviewSession(call_id)
            
            if session.load_from_directory(directory):
                return session
            else:
                logger.error(f"Failed to load session data from {directory}")
                return None
                
        except Exception as e:
            logger.error(f"Error loading session: {e}")
            return None
    
    def create_demo_session(self) -> Optional[ReviewSession]:
        """
        Create a demo session with sample data for testing.
        
        Returns:
            Demo ReviewSession or None if creation failed
        """
        try:
            from datetime import datetime, timedelta
            from .review_session import CallMetadata, TranscriptEntry, LogEntry, FunctionCall, StateTransition
            
            # Create demo session
            session = ReviewSession("demo_call_001")
            
            # Create demo metadata
            start_time = datetime.now() - timedelta(minutes=10)
            end_time = start_time + timedelta(minutes=8, seconds=30)
            
            session.metadata = CallMetadata(
                call_id="demo_call_001",
                caller_number="+1-555-0123",
                scenario="Card Replacement",
                start_time=start_time,
                end_time=end_time,
                duration_seconds=510.0,
                result="Success",
                sentiment="Positive",
                agent_name="OpusAgent"
            )
            
            # Create demo transcript
            session.transcript = [
                TranscriptEntry(0.0, "bot", "Hello! Thank you for calling Bank of Peril. How can I help you today?"),
                TranscriptEntry(3.2, "user", "Hi, I need to report my credit card as lost"),
                TranscriptEntry(7.8, "bot", "I'm sorry to hear that. I can help you with that right away."),
                TranscriptEntry(10.5, "bot", "Can you please provide me with your account number?"),
                TranscriptEntry(15.2, "user", "Yes, it's 1234-5678-9012-3456"),
                TranscriptEntry(22.1, "bot", "Thank you. Let me look up your account."),
                TranscriptEntry(25.0, "bot", "I found your account. I'll cancel your current card and order a replacement."),
                TranscriptEntry(30.5, "user", "How long will it take to receive the new card?"),
                TranscriptEntry(35.2, "bot", "Your new card will arrive within 3-5 business days."),
                TranscriptEntry(40.0, "user", "Great, thank you for your help!"),
                TranscriptEntry(43.5, "bot", "You're welcome! Is there anything else I can help you with today?"),
                TranscriptEntry(47.2, "user", "No, that's all. Thank you!"),
                TranscriptEntry(50.0, "bot", "Have a wonderful day! Goodbye."),
            ]
            
            # Create demo function calls
            session.function_calls = [
                FunctionCall(
                    timestamp=22.1,
                    function_name="lookup_account",
                    arguments={"account_number": "1234-5678-9012-3456"},
                    result={"status": "success", "account_found": True},
                    duration_ms=850.0
                ),
                FunctionCall(
                    timestamp=25.0,
                    function_name="cancel_card",
                    arguments={"card_number": "1234-5678-9012-3456", "reason": "lost"},
                    result={"status": "success", "card_cancelled": True},
                    duration_ms=1200.0
                ),
                FunctionCall(
                    timestamp=27.5,
                    function_name="order_replacement_card",
                    arguments={"account_number": "1234-5678-9012-3456", "expedited": False},
                    result={"status": "success", "order_id": "ORD789012", "delivery_days": 5},
                    duration_ms=950.0
                ),
            ]
            
            # Create demo logs
            session.logs = [
                LogEntry(0.0, "INFO", "session", "Session initiated"),
                LogEntry(3.2, "INFO", "transcript", "User speech detected"),
                LogEntry(7.8, "INFO", "tts", "Bot response generated"),
                LogEntry(22.1, "INFO", "function", "Executing lookup_account"),
                LogEntry(23.0, "INFO", "function", "Account lookup successful"),
                LogEntry(25.0, "INFO", "function", "Executing cancel_card"),
                LogEntry(26.2, "INFO", "function", "Card cancellation successful"),
                LogEntry(27.5, "INFO", "function", "Executing order_replacement_card"),
                LogEntry(28.5, "INFO", "function", "Replacement card ordered"),
                LogEntry(50.0, "INFO", "session", "Session completed"),
            ]
            
            # Create demo state transitions
            session.state_transitions = [
                StateTransition(0.0, "idle", "greeting", "session_start", 3.2),
                StateTransition(3.2, "greeting", "listening", "user_speech", 4.6),
                StateTransition(7.8, "listening", "processing", "intent_detected", 2.7),
                StateTransition(10.5, "processing", "account_lookup", "function_call", 11.6),
                StateTransition(22.1, "account_lookup", "card_management", "account_found", 8.4),
                StateTransition(30.5, "card_management", "confirmation", "task_complete", 16.7),
                StateTransition(47.2, "confirmation", "closing", "user_satisfied", 2.8),
                StateTransition(50.0, "closing", "idle", "session_end", 0.0),
            ]
            
            # Sort timeline data
            session._sort_timeline_data()
            session._apply_filter("")
            
            logger.info("Demo session created successfully")
            return session
            
        except Exception as e:
            logger.error(f"Failed to create demo session: {e}")
            return None
    
    def get_session_summary(self, session_info: Dict[str, Any]) -> str:
        """Get a summary string for a session."""
        call_id = session_info["call_id"]
        directory = session_info["directory_name"]
        
        features = []
        if session_info["has_audio"]:
            features.append("Audio")
        if session_info["has_transcript"]:
            features.append("Transcript")
        if session_info["has_metadata"]:
            features.append("Metadata")
        if session_info["has_events"]:
            features.append("Events")
        
        feature_str = ", ".join(features) if features else "No data"
        
        return f"{call_id} ({directory}) - {feature_str}"