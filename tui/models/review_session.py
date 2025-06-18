"""
Review session data model for the Call Review Interface.

This module provides the ReviewSession class which manages all data
for reviewing completed calls including audio, transcripts, logs,
function calls, and state machine transitions.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

# Optional audio processing imports
try:
    import numpy as np  # type: ignore
    HAS_NUMPY = True
except ImportError:
    np = None
    HAS_NUMPY = False

logger = logging.getLogger(__name__)

@dataclass
class CallMetadata:
    """Call metadata information."""
    call_id: str
    caller_number: str = "Unknown"
    scenario: str = "Unknown"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    result: str = "Unknown"
    sentiment: str = "Neutral"
    agent_name: str = "OpusAgent"
    
    def get_duration_str(self) -> str:
        """Get formatted duration string."""
        if self.duration_seconds:
            minutes = int(self.duration_seconds // 60)
            seconds = int(self.duration_seconds % 60)
            return f"{minutes}:{seconds:02d}"
        return "0:00"

@dataclass 
class TranscriptEntry:
    """Single transcript entry."""
    timestamp: float
    speaker: str  # "user", "bot", "system"
    text: str
    confidence: float = 1.0
    
    def get_time_str(self) -> str:
        """Get formatted timestamp string."""
        minutes = int(self.timestamp // 60)
        seconds = int(self.timestamp % 60)
        return f"{minutes}:{seconds:02d}"

@dataclass
class LogEntry:
    """Single log entry."""
    timestamp: float
    level: str  # "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
    module: str
    message: str
    data: Optional[Dict[str, Any]] = None
    
    def get_time_str(self) -> str:
        """Get formatted timestamp string."""
        minutes = int(self.timestamp // 60)
        seconds = int(self.timestamp % 60)
        return f"{minutes}:{seconds:02d}"

@dataclass
class FunctionCall:
    """Function call entry."""
    timestamp: float
    function_name: str
    arguments: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    duration_ms: Optional[float] = None
    
    def get_time_str(self) -> str:
        """Get formatted timestamp string."""
        minutes = int(self.timestamp // 60)
        seconds = int(self.timestamp % 60)
        return f"{minutes}:{seconds:02d}"
    
    def get_args_str(self) -> str:
        """Get formatted arguments string."""
        if not self.arguments:
            return ""
        return ", ".join([f"{k}={v}" for k, v in self.arguments.items()])

@dataclass
class StateTransition:
    """State machine transition entry."""
    timestamp: float
    from_state: str
    to_state: str
    trigger: str
    duration_seconds: float = 0.0
    
    def get_time_str(self) -> str:
        """Get formatted timestamp string."""
        minutes = int(self.timestamp // 60)
        seconds = int(self.timestamp % 60)
        return f"{minutes}:{seconds:02d}"

class ReviewSession:
    """
    Central review session model that manages all call review data.
    
    Provides synchronized access to audio, transcripts, logs, function calls,
    and state transitions with timestamp-based navigation.
    """
    
    def __init__(self, call_id: str):
        self.call_id = call_id
        
        # Core data
        self.metadata: Optional[CallMetadata] = None
        self.audio_file: Optional[str] = None
        self.audio_data: Optional[Any] = None  # numpy array if available
        self.sample_rate: int = 16000
        self.channels: int = 2  # Stereo for bot/user separation
        
        # Timeline data (sorted by timestamp)
        self.transcript: List[TranscriptEntry] = []
        self.logs: List[LogEntry] = []
        self.function_calls: List[FunctionCall] = []
        self.state_transitions: List[StateTransition] = []
        
        # Current playback position
        self.current_timestamp: float = 0.0
        
        # Filter state
        self.filter_query: str = ""
        self.filtered_transcript: List[TranscriptEntry] = []
        self.filtered_logs: List[LogEntry] = []
        self.filtered_function_calls: List[FunctionCall] = []
        
        # Subscribers for sync events
        self._seek_listeners: List[callable] = []
        self._filter_listeners: List[callable] = []
    
    def load_from_directory(self, data_dir: Path) -> bool:
        """
        Load review session data from a directory.
        
        Expected structure:
        - call_metadata.json
        - transcript.json  
        - session_events.json
        - final_stereo_recording.wav
        - [call_id].log (optional)
        
        Args:
            data_dir: Directory containing call review data
            
        Returns:
            True if successfully loaded
        """
        try:
            data_dir = Path(data_dir)
            
            # Load metadata
            metadata_file = data_dir / "call_metadata.json"
            if metadata_file.exists():
                self._load_metadata(metadata_file)
            
            # Load audio
            audio_file = data_dir / "final_stereo_recording.wav"
            if audio_file.exists():
                self._load_audio(audio_file)
            
            # Load transcript
            transcript_file = data_dir / "transcript.json"
            if transcript_file.exists():
                self._load_transcript(transcript_file)
            
            # Load events (logs, function calls, state transitions)
            events_file = data_dir / "session_events.json"
            if events_file.exists():
                self._load_events(events_file)
            
            # Load log file if exists
            log_file = data_dir / f"{self.call_id}.log"
            if not log_file.exists():
                # Try common log file names
                for log_name in ["opusagent.log", "debug.log", "app.log"]:
                    log_file = data_dir / log_name
                    if log_file.exists():
                        break
            
            if log_file.exists():
                self._load_log_file(log_file)
            
            # Sort all timeline data by timestamp
            self._sort_timeline_data()
            
            # Initialize filters
            self._apply_filter("")
            
            logger.info(f"Review session loaded: {self.call_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load review session: {e}")
            return False
    
    def _load_metadata(self, metadata_file: Path) -> None:
        """Load call metadata from JSON file."""
        with open(metadata_file, 'r') as f:
            data = json.load(f)
        
        # Parse timestamps if present
        start_time = None
        end_time = None
        if data.get("start_time"):
            start_time = datetime.fromisoformat(data["start_time"])
        if data.get("end_time"):
            end_time = datetime.fromisoformat(data["end_time"])
        
        self.metadata = CallMetadata(
            call_id=self.call_id,
            caller_number=data.get("caller_number", "Unknown"),
            scenario=data.get("scenario", "Unknown"),
            start_time=start_time,
            end_time=end_time,
            duration_seconds=data.get("duration_seconds", 0.0),
            result=data.get("result", "Unknown"),
            sentiment=data.get("sentiment", "Neutral"),
            agent_name=data.get("agent_name", "OpusAgent")
        )
    
    def _load_audio(self, audio_file: Path) -> None:
        """Load audio file using soundfile if available."""
        try:
            import soundfile as sf
            self.audio_data, self.sample_rate = sf.read(str(audio_file))
            self.audio_file = str(audio_file)
            
            # Handle mono vs stereo
            if HAS_NUMPY and self.audio_data is not None:
                if len(self.audio_data.shape) == 1:
                    self.channels = 1
                else:
                    self.channels = self.audio_data.shape[1]
                    
                logger.debug(f"Loaded audio: {self.sample_rate}Hz, {self.channels}ch, {len(self.audio_data)} samples")
            else:
                self.channels = 2  # Default to stereo
                
        except ImportError:
            logger.warning("soundfile not available, audio playback may be limited")
            self.audio_file = str(audio_file)
            # Set reasonable defaults
            self.sample_rate = 16000
            self.channels = 2
        except Exception as e:
            logger.error(f"Failed to load audio file: {e}")
    
    def _load_transcript(self, transcript_file: Path) -> None:
        """Load transcript from JSON file."""
        with open(transcript_file, 'r') as f:
            data = json.load(f)
        
        # Handle different transcript formats
        if isinstance(data, list):
            entries = data
        elif isinstance(data, dict) and "transcript" in data:
            entries = data["transcript"]
        else:
            entries = []
        
        for entry in entries:
            transcript_entry = TranscriptEntry(
                timestamp=entry.get("timestamp", 0.0),
                speaker=entry.get("speaker", "unknown"),
                text=entry.get("text", ""),
                confidence=entry.get("confidence", 1.0)
            )
            self.transcript.append(transcript_entry)
    
    def _load_events(self, events_file: Path) -> None:
        """Load events (function calls, state transitions) from JSON file."""
        with open(events_file, 'r') as f:
            data = json.load(f)
        
        events = data.get("events", []) if isinstance(data, dict) else data
        
        for event in events:
            event_type = event.get("type", "")
            timestamp = event.get("timestamp", 0.0)
            
            if event_type == "function_call":
                func_call = FunctionCall(
                    timestamp=timestamp,
                    function_name=event.get("function_name", ""),
                    arguments=event.get("arguments", {}),
                    result=event.get("result"),
                    duration_ms=event.get("duration_ms")
                )
                self.function_calls.append(func_call)
            
            elif event_type == "state_transition":
                transition = StateTransition(
                    timestamp=timestamp,
                    from_state=event.get("from_state", ""),
                    to_state=event.get("to_state", ""),
                    trigger=event.get("trigger", ""),
                    duration_seconds=event.get("duration_seconds", 0.0)
                )
                self.state_transitions.append(transition)
    
    def _load_log_file(self, log_file: Path) -> None:
        """Load log entries from log file."""
        try:
            with open(log_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Parse log line (basic format)
                    # Expected: TIMESTAMP - MODULE - LEVEL - MESSAGE
                    parts = line.split(' - ', 3)
                    if len(parts) >= 4:
                        timestamp_str, module, level, message = parts
                        
                        # Parse timestamp
                        try:
                            # Assume logs use ISO format
                            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                            # Convert to seconds since call start
                            if self.metadata and self.metadata.start_time:
                                timestamp = (dt - self.metadata.start_time).total_seconds()
                            else:
                                timestamp = 0.0
                        except:
                            timestamp = 0.0
                        
                        log_entry = LogEntry(
                            timestamp=timestamp,
                            level=level.upper(),
                            module=module,
                            message=message
                        )
                        self.logs.append(log_entry)
                        
        except Exception as e:
            logger.warning(f"Could not parse log file: {e}")
    
    def _sort_timeline_data(self) -> None:
        """Sort all timeline data by timestamp."""
        self.transcript.sort(key=lambda x: x.timestamp)
        self.logs.sort(key=lambda x: x.timestamp)
        self.function_calls.sort(key=lambda x: x.timestamp)
        self.state_transitions.sort(key=lambda x: x.timestamp)
    
    def seek_to_timestamp(self, timestamp: float) -> None:
        """
        Seek to a specific timestamp and notify all listeners.
        
        Args:
            timestamp: Target timestamp in seconds
        """
        self.current_timestamp = max(0.0, timestamp)
        
        # Notify all seek listeners
        for listener in self._seek_listeners:
            try:
                listener(self.current_timestamp)
            except Exception as e:
                logger.error(f"Error in seek listener: {e}")
    
    def apply_filter(self, query: str) -> None:
        """
        Apply filter query and update filtered data.
        
        Args:
            query: Filter query string
        """
        self.filter_query = query.lower()
        self._apply_filter(self.filter_query)
        
        # Notify filter listeners
        for listener in self._filter_listeners:
            try:
                listener(self.filter_query)
            except Exception as e:
                logger.error(f"Error in filter listener: {e}")
    
    def _apply_filter(self, query: str) -> None:
        """Apply filter to all data types."""
        if not query:
            # No filter - show all data
            self.filtered_transcript = self.transcript.copy()
            self.filtered_logs = self.logs.copy()
            self.filtered_function_calls = self.function_calls.copy()
        else:
            # Apply text filter
            self.filtered_transcript = [
                entry for entry in self.transcript
                if query in entry.text.lower() or query in entry.speaker.lower()
            ]
            
            self.filtered_logs = [
                entry for entry in self.logs
                if query in entry.message.lower() or query in entry.module.lower()
            ]
            
            self.filtered_function_calls = [
                call for call in self.function_calls
                if query in call.function_name.lower() or
                   query in str(call.arguments).lower()
            ]
    
    def get_entry_at_timestamp(self, entries: List, timestamp: float) -> Optional[Any]:
        """Get the entry closest to the given timestamp."""
        if not entries:
            return None
        
        # Binary search for closest entry
        left, right = 0, len(entries) - 1
        closest = entries[0]
        min_diff = abs(entries[0].timestamp - timestamp)
        
        while left <= right:
            mid = (left + right) // 2
            diff = abs(entries[mid].timestamp - timestamp)
            
            if diff < min_diff:
                min_diff = diff
                closest = entries[mid]
            
            if entries[mid].timestamp < timestamp:
                left = mid + 1
            else:
                right = mid - 1
        
        return closest
    
    def get_duration(self) -> float:
        """Get total duration in seconds."""
        if self.metadata:
            return self.metadata.duration_seconds
        elif self.audio_data is not None and HAS_NUMPY:
            return len(self.audio_data) / self.sample_rate
        else:
            return 0.0
    
    def add_seek_listener(self, listener: callable) -> None:
        """Add a listener for seek events."""
        self._seek_listeners.append(listener)
    
    def add_filter_listener(self, listener: callable) -> None:
        """Add a listener for filter events."""
        self._filter_listeners.append(listener)
    
    def remove_seek_listener(self, listener: callable) -> None:
        """Remove a seek listener."""
        if listener in self._seek_listeners:
            self._seek_listeners.remove(listener)
    
    def remove_filter_listener(self, listener: callable) -> None:
        """Remove a filter listener."""
        if listener in self._filter_listeners:
            self._filter_listeners.remove(listener)