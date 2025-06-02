"""
Shared audio validation utilities for validation scripts.

This module provides:
- AudioRecorder: class for recording and saving audio streams
- load_audio_chunks: function to load and chunk audio files for streaming
"""

import base64
import wave
import numpy as np
from pathlib import Path
from datetime import datetime
from scipy import signal

class AudioRecorder:
    """Handles recording of audio streams in multiple formats."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.output_dir = Path("validation_output")
        self.output_dir.mkdir(exist_ok=True)

        # Create timestamp for all files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # File paths
        self.bot_audio_file = (
            self.output_dir / f"bot_audio_{session_id}_{timestamp}.wav"
        )
        self.user_audio_file = (
            self.output_dir / f"user_audio_{session_id}_{timestamp}.wav"
        )
        self.session_recording_file = (
            self.output_dir / f"session_recording_{session_id}_{timestamp}.wav"
        )

        # WAV file objects
        self.bot_wav = None
        self.user_wav = None
        self.session_wav = None

        # Audio buffers for creating combined recording
        self.bot_audio_buffer = []
        self.user_audio_buffer = []

        # Audio parameters
        self.sample_rate = 16000
        self.channels = 1
        self.sample_width = 2  # 16-bit

        self._init_wav_files()

    def _init_wav_files(self):
        """Initialize WAV files for recording."""
        # Bot audio (incoming)
        self.bot_wav = wave.open(str(self.bot_audio_file), "wb")
        self.bot_wav.setnchannels(self.channels)
        self.bot_wav.setsampwidth(self.sample_width)
        self.bot_wav.setframerate(self.sample_rate)

        # User audio (outgoing)
        self.user_wav = wave.open(str(self.user_audio_file), "wb")
        self.user_wav.setnchannels(self.channels)
        self.user_wav.setsampwidth(self.sample_width)
        self.user_wav.setframerate(self.sample_rate)

        # Session recording (stereo: left=user, right=bot)
        self.session_wav = wave.open(str(self.session_recording_file), "wb")
        self.session_wav.setnchannels(2)  # Stereo
        self.session_wav.setsampwidth(self.sample_width)
        self.session_wav.setframerate(self.sample_rate)

        print(f"✅ Audio recording initialized:")
        print(f"   Bot audio: {self.bot_audio_file}")
        print(f"   User audio: {self.user_audio_file}")
        print(f"   Session recording: {self.session_recording_file}")

    def record_bot_audio(self, audio_chunk_b64: str):
        """Record incoming bot audio."""
        try:
            decoded_chunk = base64.b64decode(audio_chunk_b64)

            # Write to bot-only file
            if self.bot_wav:
                self.bot_wav.writeframes(decoded_chunk)

            # Store in buffer for combined recording
            self.bot_audio_buffer.append(decoded_chunk)

        except Exception as e:
            print(f"❌ Error recording bot audio: {e}")

    def record_user_audio(self, audio_chunk_b64: str):
        """Record outgoing user audio."""
        try:
            decoded_chunk = base64.b64decode(audio_chunk_b64)

            # Write to user-only file
            if self.user_wav:
                self.user_wav.writeframes(decoded_chunk)

            # Store in buffer for combined recording
            self.user_audio_buffer.append(decoded_chunk)

        except Exception as e:
            print(f"❌ Error recording user audio: {e}")

    def create_combined_recording(self):
        """Create a stereo recording with user on left channel, bot on right channel."""
        try:
            # Convert buffers to numpy arrays
            if self.user_audio_buffer:
                user_audio = np.concatenate(
                    [
                        np.frombuffer(chunk, dtype=np.int16)
                        for chunk in self.user_audio_buffer
                    ]
                )
            else:
                user_audio = np.array([], dtype=np.int16)

            if self.bot_audio_buffer:
                bot_audio = np.concatenate(
                    [
                        np.frombuffer(chunk, dtype=np.int16)
                        for chunk in self.bot_audio_buffer
                    ]
                )
            else:
                bot_audio = np.array([], dtype=np.int16)

            # Make both arrays the same length by padding with silence
            max_length = max(len(user_audio), len(bot_audio))
            if max_length == 0:
                return

            if len(user_audio) < max_length:
                user_audio = np.pad(
                    user_audio, (0, max_length - len(user_audio)), "constant"
                )
            if len(bot_audio) < max_length:
                bot_audio = np.pad(
                    bot_audio, (0, max_length - len(bot_audio)), "constant"
                )

            # Create stereo audio (interleave left and right channels)
            stereo_audio = np.empty((max_length * 2,), dtype=np.int16)
            stereo_audio[0::2] = user_audio  # Left channel (user)
            stereo_audio[1::2] = bot_audio  # Right channel (bot)

            # Write to stereo file
            if self.session_wav:
                self.session_wav.writeframes(stereo_audio.tobytes())

        except Exception as e:
            print(f"❌ Error creating combined recording: {e}")

    def close(self):
        """Close all WAV files and create final combined recording."""
        try:
            # Create the combined recording before closing
            self.create_combined_recording()

            # Close all files
            if self.bot_wav:
                self.bot_wav.close()
                self.bot_wav = None

            if self.user_wav:
                self.user_wav.close()
                self.user_wav = None

            if self.session_wav:
                self.session_wav.close()
                self.session_wav = None

            print(f"✅ Audio recording completed:")
            print(f"   Bot audio: {self.bot_audio_file}")
            print(f"   User audio: {self.user_audio_file}")
            print(
                f"   Session recording: {self.session_recording_file} (stereo: left=user, right=bot)"
            )

        except Exception as e:
            print(f"❌ Error closing audio files: {e}")

def load_audio_chunks(file_path, chunk_size=32000):
    """Load and chunk audio file into base64 encoded strings.

    Args:
        file_path: Path to WAV file
        chunk_size: Size of each chunk in bytes

    Returns:
        List of base64 encoded audio chunks
    """
    try:
        with wave.open(str(file_path), "rb") as wav_file:
            # Get file properties
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            frame_rate = wav_file.getframerate()

            print(f"Loading audio: {file_path}")
            print(f"  Format: {channels} channels, {sample_width * 8}-bit, {frame_rate}Hz")

            # Read all frames
            audio_data = wav_file.readframes(wav_file.getnframes())

            # Convert to numpy array for resampling
            audio_array = np.frombuffer(audio_data, dtype=np.int16)

            # Resample to 16kHz if needed
            if frame_rate != 16000:
                print(f"  Resampling from {frame_rate}Hz to 16000Hz...")
                number_of_samples = round(len(audio_array) * 16000 / frame_rate)
                audio_array = signal.resample(audio_array, number_of_samples)
                audio_array = audio_array.astype(np.int16)
                frame_rate = 16000
                print(f"  Resampled to {frame_rate}Hz")

            # Convert back to bytes
            audio_data = audio_array.tobytes()

            # Calculate minimum chunk size for 100ms of audio
            min_chunk_size = int(0.1 * frame_rate * sample_width)  # 100ms of audio
            print(f"  Minimum chunk size for 100ms: {min_chunk_size} bytes")

            # Ensure we have enough audio data
            if len(audio_data) < min_chunk_size:
                print(f"  ⚠️ Warning: Audio file is too short, padding with silence")
                # Pad with silence to reach minimum size
                audio_data += b"\x00" * (min_chunk_size - len(audio_data))

            # Ensure chunk_size is at least the minimum required
            if chunk_size < min_chunk_size:
                print(f"  ⚠️ Warning: Chunk size too small, increasing to {min_chunk_size} bytes")
                chunk_size = min_chunk_size

            # Chunk the audio data
            chunks = []
            for i in range(0, len(audio_data), chunk_size):
                chunk = audio_data[i : i + chunk_size]
                # Ensure each chunk is at least min_chunk_size
                if len(chunk) < min_chunk_size and i + chunk_size > len(audio_data):
                    # Pad the last chunk if it's too small
                    chunk += b"\x00" * (min_chunk_size - len(chunk))
                encoded_chunk = base64.b64encode(chunk).decode("utf-8")
                chunks.append(encoded_chunk)

            print(f"  Split into {len(chunks)} chunks")
            print(f"  Average chunk size: {len(audio_data) // len(chunks)} bytes")
            print(f"  Total audio duration: {len(audio_data) / (frame_rate * sample_width):.2f} seconds")

            # Ensure we don't have empty chunks
            chunks = [c for c in chunks if len(c) > 0]

            return chunks
    except Exception as e:
        print(f"❌ Error loading audio file: {e}")
        return None 