"""
Call Recording Manager for TelephonyRealtimeBridge.

This module provides comprehensive recording functionality for telephony calls,
including bidirectional audio recording, transcript logging, and call metadata.
"""

import asyncio
import base64
import json
import wave
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum

from opusagent.config.logging_config import configure_logging

logger = configure_logging("call_recorder")


class AudioChannel(Enum):
    """Audio channel enumeration."""
    CALLER = "caller"
    BOT = "bot"


class TranscriptType(Enum):
    """Transcript type enumeration."""
    INPUT = "input"  # Caller speech (input to AI)
    OUTPUT = "output"  # Bot speech (output from AI)


@dataclass
class TranscriptEntry:
    """A single transcript entry with metadata."""
    timestamp: datetime
    channel: AudioChannel
    type: TranscriptType
    text: str
    confidence: Optional[float] = None
    duration_ms: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "channel": self.channel.value,
            "type": self.type.value,
            "text": self.text,
            "confidence": self.confidence,
            "duration_ms": self.duration_ms
        }


@dataclass
class CallMetadata:
    """Call metadata and statistics."""
    conversation_id: str
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    caller_audio_chunks: int = 0
    bot_audio_chunks: int = 0
    caller_audio_bytes: int = 0
    bot_audio_bytes: int = 0
    transcript_entries: int = 0
    function_calls: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate call duration in seconds."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def caller_audio_duration_seconds(self) -> float:
        """Estimate caller audio duration in seconds (assuming 16kHz 16-bit)."""
        return self.caller_audio_bytes / (16000 * 2)
    
    @property
    def bot_audio_duration_seconds(self) -> float:
        """Estimate bot audio duration in seconds (assuming 24kHz 16-bit, resampled to 16kHz)."""
        # Bot audio is originally 24kHz but we resample to 16kHz for consistency
        return self.bot_audio_bytes / (16000 * 2)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "conversation_id": self.conversation_id,
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "caller_audio_chunks": self.caller_audio_chunks,
            "bot_audio_chunks": self.bot_audio_chunks,
            "caller_audio_bytes": self.caller_audio_bytes,
            "bot_audio_bytes": self.bot_audio_bytes,
            "caller_audio_duration_seconds": self.caller_audio_duration_seconds,
            "bot_audio_duration_seconds": self.bot_audio_duration_seconds,
            "transcript_entries": self.transcript_entries,
            "function_calls": self.function_calls
        }


class CallRecorder:
    """
    Comprehensive call recording manager.
    
    Handles:
    - Bidirectional audio recording (separate and combined stereo)
    - Transcript logging with timestamps
    - Call metadata and statistics
    - File management and cleanup
    - Audio resampling for different sample rates (caller: 16kHz, bot: 24kHz)
    """
    
    def __init__(
        self,
        conversation_id: str,
        session_id: Optional[str] = None,
        base_output_dir: str = "call_recordings",
        bot_sample_rate: int = 24000  # Allow overriding the bot sample rate
    ):
        """
        Initialize the call recorder.
        
        Args:
            conversation_id: Unique conversation identifier
            session_id: Optional session identifier
            base_output_dir: Base directory for recordings
            bot_sample_rate: Sample rate for bot audio (default 24000 for OpenAI Realtime API)
        """
        self.conversation_id = conversation_id
        self.session_id = session_id or conversation_id
        self.base_output_dir = Path(base_output_dir)
        
        # Create recording session directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.recording_dir = self.base_output_dir / f"{self.session_id}_{timestamp}"
        self.recording_dir.mkdir(parents=True, exist_ok=True)
        
        # Audio recording setup - different sample rates for different sources
        self.caller_sample_rate = 16000  # Telephony is typically 16kHz
        self.bot_sample_rate = bot_sample_rate     # OpenAI Realtime API (configurable)
        self.target_sample_rate = 16000  # Target rate for final recordings (for consistency)
        self.channels = 1
        self.sample_width = 2  # 16-bit
        
        # File paths
        self.caller_audio_file = self.recording_dir / "caller_audio.wav"
        self.bot_audio_file = self.recording_dir / "bot_audio.wav"
        self.stereo_audio_file = self.recording_dir / "stereo_recording.wav"
        self.transcript_file = self.recording_dir / "transcript.json"
        self.metadata_file = self.recording_dir / "call_metadata.json"
        self.session_log_file = self.recording_dir / "session_events.json"
        
        # WAV file handles
        self.caller_wav: Optional[wave.Wave_write] = None
        self.bot_wav: Optional[wave.Wave_write] = None
        self.stereo_wav: Optional[wave.Wave_write] = None
        
        # Audio buffers for stereo creation
        self.caller_audio_buffer: List[bytes] = []
        self.bot_audio_buffer: List[bytes] = []
        
        # Transcript and metadata
        self.transcripts: List[TranscriptEntry] = []
        self.metadata = CallMetadata(
            conversation_id=conversation_id,
            session_id=self.session_id,
            start_time=datetime.now(timezone.utc)
        )
        self.session_events: List[Dict[str, Any]] = []
        
        # State
        self.recording_active = False
        self.finalized = False
        
        logger.info(f"CallRecorder initialized for conversation {conversation_id}")
        logger.info(f"Recording directory: {self.recording_dir}")
        logger.info(f"Audio settings - Caller: {self.caller_sample_rate}Hz, Bot: {self.bot_sample_rate}Hz, Target: {self.target_sample_rate}Hz")
    
    def _resample_audio(self, audio_bytes: bytes, from_rate: int, to_rate: int) -> bytes:
        """
        Resample audio from one sample rate to another using high-quality interpolation.
        
        Args:
            audio_bytes: Raw audio bytes (16-bit PCM)
            from_rate: Source sample rate
            to_rate: Target sample rate
            
        Returns:
            Resampled audio bytes
        """
        if from_rate == to_rate:
            return audio_bytes
            
        try:
            # Convert bytes to numpy array
            audio_array = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float64)
            
            # Calculate resampling parameters
            ratio = to_rate / from_rate
            original_length = len(audio_array)
            new_length = int(original_length * ratio)
            
            # Use sinc interpolation for better quality resampling
            # This is a simplified version of what scipy.signal.resample would do
            if ratio > 1:
                # Upsampling - use linear interpolation with anti-aliasing
                old_indices = np.linspace(0, original_length - 1, new_length)
                resampled_audio = np.interp(old_indices, np.arange(original_length), audio_array)
            else:
                # Downsampling - apply low-pass filter first to prevent aliasing
                # Simple moving average as low-pass filter
                filter_size = max(1, int(1 / ratio))
                if filter_size > 1:
                    # Apply simple moving average filter
                    filtered_audio = np.convolve(audio_array, np.ones(filter_size)/filter_size, mode='same')
                else:
                    filtered_audio = audio_array
                
                # Then downsample
                old_indices = np.linspace(0, original_length - 1, new_length)
                resampled_audio = np.interp(old_indices, np.arange(original_length), filtered_audio)
            
            # Convert back to int16 with proper clipping
            resampled_audio = np.clip(resampled_audio, -32768, 32767).astype(np.int16)
            
            # Log resampling details for debugging
            original_duration_ms = (original_length / from_rate) * 1000
            resampled_duration_ms = (new_length / to_rate) * 1000
            logger.debug(
                f"Audio resampling: {from_rate}Hz -> {to_rate}Hz, "
                f"{original_length} -> {new_length} samples, "
                f"{original_duration_ms:.1f}ms -> {resampled_duration_ms:.1f}ms"
            )
            
            return resampled_audio.tobytes()
            
        except Exception as e:
            logger.error(f"Error resampling audio from {from_rate}Hz to {to_rate}Hz: {e}")
            return audio_bytes  # Return original on error
    
    async def start_recording(self) -> bool:
        """
        Start the recording session.
        
        Returns:
            True if recording started successfully, False otherwise
        """
        if self.recording_active:
            logger.warning("Recording already active")
            return True
        
        try:
            # Initialize WAV files
            self._init_wav_files()
            self.recording_active = True
            
            # Log session start event
            await self._log_session_event("recording_started", {
                "conversation_id": self.conversation_id,
                "recording_dir": str(self.recording_dir),
                "caller_sample_rate": self.caller_sample_rate,
                "bot_sample_rate": self.bot_sample_rate,
                "target_sample_rate": self.target_sample_rate
            })
            
            logger.info(f"Recording started for conversation {self.conversation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            return False
    
    def _init_wav_files(self):
        """Initialize WAV files for recording."""
        # Caller audio (16kHz)
        self.caller_wav = wave.open(str(self.caller_audio_file), "wb")
        self.caller_wav.setnchannels(self.channels)
        self.caller_wav.setsampwidth(self.sample_width)
        self.caller_wav.setframerate(self.target_sample_rate)  # Use target rate for consistency
        
        # Bot audio (resampled to 16kHz for consistency)
        self.bot_wav = wave.open(str(self.bot_audio_file), "wb")
        self.bot_wav.setnchannels(self.channels)
        self.bot_wav.setsampwidth(self.sample_width)
        self.bot_wav.setframerate(self.target_sample_rate)  # Use target rate for consistency
        
        # Stereo recording (both channels at 16kHz)
        self.stereo_wav = wave.open(str(self.stereo_audio_file), "wb")
        self.stereo_wav.setnchannels(2)  # Stereo
        self.stereo_wav.setsampwidth(self.sample_width)
        self.stereo_wav.setframerate(self.target_sample_rate)  # Use target rate for consistency
        
        logger.info("WAV files initialized for recording")
    
    async def record_caller_audio(self, audio_chunk_b64: str) -> bool:
        """
        Record audio from the caller.
        
        Args:
            audio_chunk_b64: Base64 encoded audio chunk (assumed 16kHz)
            
        Returns:
            True if recorded successfully, False otherwise
        """
        if not self.recording_active:
            return False
        
        try:
            decoded_chunk = base64.b64decode(audio_chunk_b64)
            
            # Caller audio is typically already 16kHz, so no resampling needed usually
            processed_chunk = decoded_chunk
            if self.caller_sample_rate != self.target_sample_rate:
                processed_chunk = self._resample_audio(
                    decoded_chunk, self.caller_sample_rate, self.target_sample_rate
                )
            
            # Write to caller-only file
            if self.caller_wav:
                self.caller_wav.writeframes(processed_chunk)
            
            # Store in buffer for stereo creation
            self.caller_audio_buffer.append(processed_chunk)
            
            # Update metadata (use processed chunk size for consistency)
            self.metadata.caller_audio_chunks += 1
            self.metadata.caller_audio_bytes += len(processed_chunk)
            
            # Write to stereo file (left channel)
            if self.stereo_wav:
                await self._write_stereo_chunk(processed_chunk, AudioChannel.CALLER)
            
            return True
            
        except Exception as e:
            logger.error(f"Error recording caller audio: {e}")
            return False
    
    async def record_bot_audio(self, audio_chunk_b64: str) -> bool:
        """
        Record audio from the bot.
        
        Args:
            audio_chunk_b64: Base64 encoded audio chunk (assumed to be at bot_sample_rate from OpenAI)
            
        Returns:
            True if recorded successfully, False otherwise
        """
        if not self.recording_active:
            return False
        
        try:
            decoded_chunk = base64.b64decode(audio_chunk_b64)
            
            # Validate chunk size (should be reasonable for audio data)
            if len(decoded_chunk) < 2:  # Need at least one 16-bit sample
                logger.warning(f"Bot audio chunk too small: {len(decoded_chunk)} bytes")
                return False
            
            # Ensure even number of bytes (16-bit samples)
            if len(decoded_chunk) % 2 != 0:
                logger.warning(f"Bot audio chunk has odd number of bytes: {len(decoded_chunk)}")
                decoded_chunk = decoded_chunk[:-1]  # Remove last byte
            
            # Calculate original duration for logging
            original_samples = len(decoded_chunk) // 2  # 16-bit = 2 bytes per sample
            original_duration_ms = (original_samples / self.bot_sample_rate) * 1000
            
            # Resample bot audio from bot_sample_rate to target_sample_rate for consistency
            processed_chunk = self._resample_audio(
                decoded_chunk, self.bot_sample_rate, self.target_sample_rate
            )
            
            # Calculate resampled duration for verification
            resampled_samples = len(processed_chunk) // 2
            resampled_duration_ms = (resampled_samples / self.target_sample_rate) * 1000
            
            # Write to bot-only file
            if self.bot_wav:
                self.bot_wav.writeframes(processed_chunk)
            
            # Store in buffer for stereo creation
            self.bot_audio_buffer.append(processed_chunk)
            
            # Update metadata (use processed chunk size for consistency)
            self.metadata.bot_audio_chunks += 1
            self.metadata.bot_audio_bytes += len(processed_chunk)
            
            # Write to stereo file (right channel)
            if self.stereo_wav:
                await self._write_stereo_chunk(processed_chunk, AudioChannel.BOT)
            
            # Log resampling info occasionally for debugging
            if self.metadata.bot_audio_chunks % 100 == 1:  # Log every 100th chunk
                logger.info(
                    f"Bot audio chunk #{self.metadata.bot_audio_chunks}: "
                    f"Original: {len(decoded_chunk)} bytes ({original_duration_ms:.1f}ms @ {self.bot_sample_rate}Hz), "
                    f"Resampled: {len(processed_chunk)} bytes ({resampled_duration_ms:.1f}ms @ {self.target_sample_rate}Hz)"
                )
                
                # Validate duration consistency
                duration_ratio = resampled_duration_ms / original_duration_ms
                expected_ratio = self.target_sample_rate / self.bot_sample_rate
                if abs(duration_ratio - expected_ratio) > 0.01:  # Allow 1% tolerance
                    logger.warning(
                        f"Duration ratio mismatch: got {duration_ratio:.3f}, expected {expected_ratio:.3f}. "
                        f"This may indicate incorrect sample rate assumptions."
                    )
            
            return True
            
        except Exception as e:
            logger.error(f"Error recording bot audio: {e}")
            return False
    
    async def _write_stereo_chunk(self, audio_chunk: bytes, channel: AudioChannel):
        """Write audio chunk to stereo file with proper channel assignment."""
        try:
            # Convert to numpy array (audio_chunk is already at target sample rate)
            mono_audio = np.frombuffer(audio_chunk, dtype=np.int16)
            
            # Create stereo frame (left=caller, right=bot)
            stereo_frames = np.zeros((len(mono_audio), 2), dtype=np.int16)
            
            if channel == AudioChannel.CALLER:
                stereo_frames[:, 0] = mono_audio  # Left channel
            else:  # BOT
                stereo_frames[:, 1] = mono_audio  # Right channel
            
            # Write to stereo file
            if self.stereo_wav:
                self.stereo_wav.writeframes(stereo_frames.tobytes())
            
        except Exception as e:
            logger.error(f"Error writing stereo chunk: {e}")
    
    async def add_transcript(
        self,
        text: str,
        channel: AudioChannel,
        transcript_type: TranscriptType,
        confidence: Optional[float] = None,
        duration_ms: Optional[float] = None
    ) -> bool:
        """
        Add a transcript entry.
        
        Args:
            text: The transcript text
            channel: Audio channel (caller or bot)
            transcript_type: Type of transcript (input or output)
            confidence: Optional confidence score
            duration_ms: Optional duration in milliseconds
            
        Returns:
            True if added successfully, False otherwise
        """
        try:
            entry = TranscriptEntry(
                timestamp=datetime.now(timezone.utc),
                channel=channel,
                type=transcript_type,
                text=text,
                confidence=confidence,
                duration_ms=duration_ms
            )
            
            self.transcripts.append(entry)
            self.metadata.transcript_entries += 1
            
            logger.info(f"Transcript added: [{channel.value}] {text[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Error adding transcript: {e}")
            return False
    
    async def log_function_call(
        self,
        function_name: str,
        arguments: Dict[str, Any],
        result: Optional[Dict[str, Any]] = None,
        call_id: Optional[str] = None
    ):
        """Log a function call event."""
        function_call = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "function_name": function_name,
            "arguments": arguments,
            "result": result,
            "call_id": call_id
        }
        
        self.metadata.function_calls.append(function_call)
        
        await self._log_session_event("function_call", function_call)
        logger.info(f"Function call logged: {function_name}")
    
    async def _log_session_event(self, event_type: str, data: Dict[str, Any]):
        """Log a session event."""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "data": data
        }
        
        self.session_events.append(event)
    
    async def stop_recording(self) -> bool:
        """
        Stop the recording session and save all data.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        if not self.recording_active:
            logger.warning("Recording not active")
            return True
        
        try:
            self.recording_active = False
            self.metadata.end_time = datetime.now(timezone.utc)
            
            # Close WAV files
            if self.caller_wav:
                self.caller_wav.close()
                self.caller_wav = None
            
            if self.bot_wav:
                self.bot_wav.close()
                self.bot_wav = None
            
            if self.stereo_wav:
                self.stereo_wav.close()
                self.stereo_wav = None
            
            # Save transcript and metadata
            await self._save_transcript()
            await self._save_metadata()
            await self._save_session_events()
            
            # Create final stereo recording (if needed)
            await self._create_final_stereo_recording()
            
            await self._log_session_event("recording_stopped", {
                "conversation_id": self.conversation_id,
                "duration_seconds": self.metadata.duration_seconds,
                "total_audio_chunks": self.metadata.caller_audio_chunks + self.metadata.bot_audio_chunks
            })
            
            self.finalized = True
            logger.info(f"Recording stopped and finalized for conversation {self.conversation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            return False
    
    async def _save_transcript(self):
        """Save transcript to JSON file."""
        try:
            transcript_data = {
                "conversation_id": self.conversation_id,
                "session_id": self.session_id,
                "start_time": self.metadata.start_time.isoformat(),
                "end_time": self.metadata.end_time.isoformat() if self.metadata.end_time else None,
                "entries": [entry.to_dict() for entry in self.transcripts]
            }
            
            with open(self.transcript_file, 'w', encoding='utf-8') as f:
                json.dump(transcript_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Transcript saved: {self.transcript_file}")
            
        except Exception as e:
            logger.error(f"Error saving transcript: {e}")
    
    async def _save_metadata(self):
        """Save call metadata to JSON file."""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata.to_dict(), f, indent=2)
            
            logger.info(f"Metadata saved: {self.metadata_file}")
            
        except Exception as e:
            logger.error(f"Error saving metadata: {e}")
    
    async def _save_session_events(self):
        """Save session events to JSON file."""
        try:
            events_data = {
                "conversation_id": self.conversation_id,
                "session_id": self.session_id,
                "events": self.session_events
            }
            
            with open(self.session_log_file, 'w', encoding='utf-8') as f:
                json.dump(events_data, f, indent=2)
            
            logger.info(f"Session events saved: {self.session_log_file}")
            
        except Exception as e:
            logger.error(f"Error saving session events: {e}")
    
    async def _create_final_stereo_recording(self):
        """Create a final stereo recording by combining caller and bot audio buffers."""
        try:
            if not self.caller_audio_buffer and not self.bot_audio_buffer:
                logger.warning("No audio buffers to combine")
                return
            
            # Convert buffers to numpy arrays
            caller_audio = np.array([], dtype=np.int16)
            bot_audio = np.array([], dtype=np.int16)
            
            if self.caller_audio_buffer:
                caller_audio = np.concatenate([
                    np.frombuffer(chunk, dtype=np.int16) 
                    for chunk in self.caller_audio_buffer
                ])
            
            if self.bot_audio_buffer:
                bot_audio = np.concatenate([
                    np.frombuffer(chunk, dtype=np.int16) 
                    for chunk in self.bot_audio_buffer
                ])
            
            # Make both arrays the same length by padding with silence
            # Both audio sources are now at the same sample rate (target_sample_rate)
            max_length = max(len(caller_audio), len(bot_audio))
            if max_length == 0:
                logger.warning("No audio data to combine")
                return
            
            if len(caller_audio) < max_length:
                caller_audio = np.pad(
                    caller_audio, (0, max_length - len(caller_audio)), 'constant'
                )
            
            if len(bot_audio) < max_length:
                bot_audio = np.pad(
                    bot_audio, (0, max_length - len(bot_audio)), 'constant'
                )
            
            # Create stereo array (left=caller, right=bot)
            stereo_audio = np.column_stack((caller_audio, bot_audio))
            
            # Save as final stereo recording
            final_stereo_file = self.recording_dir / "final_stereo_recording.wav"
            with wave.open(str(final_stereo_file), 'wb') as wav_file:
                wav_file.setnchannels(2)
                wav_file.setsampwidth(self.sample_width)
                wav_file.setframerate(self.target_sample_rate)
                wav_file.writeframes(stereo_audio.tobytes())
            
            duration = len(stereo_audio) / self.target_sample_rate
            logger.info(f"Final stereo recording created: {final_stereo_file} ({duration:.2f}s)")
            logger.info(f"Audio resampling applied - Bot audio resampled from {self.bot_sample_rate}Hz to {self.target_sample_rate}Hz")
            
        except Exception as e:
            logger.error(f"Error creating final stereo recording: {e}")
    
    def get_recording_summary(self) -> Dict[str, Any]:
        """Get a summary of the recording session."""
        return {
            "conversation_id": self.conversation_id,
            "session_id": self.session_id,
            "recording_dir": str(self.recording_dir),
            "recording_active": self.recording_active,
            "finalized": self.finalized,
            "files": {
                "caller_audio": str(self.caller_audio_file),
                "bot_audio": str(self.bot_audio_file),
                "stereo_audio": str(self.stereo_audio_file),
                "transcript": str(self.transcript_file),
                "metadata": str(self.metadata_file),
                "session_events": str(self.session_log_file)
            },
            "stats": self.metadata.to_dict()
        }
    
    async def cleanup(self):
        """Clean up resources and close any open files."""
        try:
            if self.recording_active:
                await self.stop_recording()
            
            # Ensure all files are closed
            for wav_file in [self.caller_wav, self.bot_wav, self.stereo_wav]:
                if wav_file:
                    wav_file.close()
            
            logger.info(f"CallRecorder cleanup completed for {self.conversation_id}")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    @classmethod
    def test_sample_rate_detection(cls, audio_chunk_b64: str, test_rates: Optional[List[int]] = None) -> dict:
        """
        Test different sample rates to help detect the correct one.
        This is a debugging helper method.
        
        Args:
            audio_chunk_b64: Base64 encoded audio chunk
            test_rates: List of sample rates to test (default: [16000, 22050, 24000, 44100, 48000])
            
        Returns:
            Dictionary with sample rate analysis results
        """
        if test_rates is None:
            test_rates = [16000, 22050, 24000, 44100, 48000]
        
        results = {}
        
        try:
            decoded_chunk = base64.b64decode(audio_chunk_b64)
            samples = len(decoded_chunk) // 2  # 16-bit samples
            
            for rate in test_rates:
                duration_ms = (samples / rate) * 1000
                results[rate] = {
                    'duration_ms': duration_ms,
                    'samples': samples,
                    'bytes': len(decoded_chunk),
                    'reasonable': 10 <= duration_ms <= 500  # Typical chunk should be 10-500ms
                }
            
            # Find most reasonable sample rates
            reasonable_rates = [rate for rate, info in results.items() if info['reasonable']]
            
            return {
                'chunk_info': {
                    'bytes': len(decoded_chunk),
                    'samples': samples
                },
                'sample_rate_analysis': results,
                'recommended_rates': reasonable_rates
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def set_bot_sample_rate(self, new_rate: int):
        """
        Update the bot sample rate during recording.
        Useful for dynamic adjustment if the initial rate was incorrect.
        
        Args:
            new_rate: New sample rate for bot audio
        """
        old_rate = self.bot_sample_rate
        self.bot_sample_rate = new_rate
        logger.info(f"Bot sample rate changed from {old_rate}Hz to {new_rate}Hz")
        
        # Log current session event
        if hasattr(self, 'session_events'):
            asyncio.create_task(self._log_session_event("sample_rate_changed", {
                "old_rate": old_rate,
                "new_rate": new_rate,
                "chunk_count": self.metadata.bot_audio_chunks
            }))