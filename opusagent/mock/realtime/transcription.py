"""
Transcription module for the LocalRealtime mock client.

This module provides local audio transcription capabilities using PocketSphinx
and Whisper models. It's designed to mimic the OpenAI Realtime API's transcription
behavior by processing audio chunks and emitting transcription delta events.

Key Features:
- Real-time transcription with chunked audio processing
- Support for PocketSphinx (lightweight, offline) and Whisper (high accuracy)
- Configurable backends via factory pattern
- Async/await support for non-blocking transcription
- Integration with VAD for speech segment detection
- Confidence scoring and error handling

Usage:
    transcriber = TranscriptionFactory.create_transcriber({"backend": "whisper"})
    await transcriber.initialize()

    # Process audio chunks
    for chunk in audio_chunks:
        result = await transcriber.transcribe_chunk(chunk)
        if result.text:
            print(f"Delta: {result.text}")

    # Finalize transcription
    final_result = await transcriber.finalize()
    print(f"Final: {final_result.text}")
"""

import asyncio
import base64
import io
import logging
import os
import tempfile
import time
import wave
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    """Result of a transcription operation."""

    text: str
    confidence: float = 0.0
    is_final: bool = False
    segments: Optional[List[Dict[str, Any]]] = None
    processing_time: float = 0.0
    error: Optional[str] = None


@dataclass
class TranscriptionConfig:
    """Configuration for transcription backends."""

    backend: str = "pocketsphinx"  # "pocketsphinx" or "whisper"
    language: str = "en"
    model_size: str = "base"  # For Whisper: tiny, base, small, medium, large
    chunk_duration: float = 1.0  # Duration in seconds for processing chunks
    confidence_threshold: float = 0.5
    sample_rate: int = 16000
    enable_vad: bool = True
    device: str = "cpu"  # "cpu" or "cuda" for Whisper

    # PocketSphinx specific
    pocketsphinx_hmm: Optional[str] = None
    pocketsphinx_lm: Optional[str] = None
    pocketsphinx_dict: Optional[str] = None

    # Whisper specific
    whisper_model_dir: Optional[str] = None
    whisper_temperature: float = 0.0


class BaseTranscriber(ABC):
    """Abstract base class for audio transcription."""

    def __init__(self, config: TranscriptionConfig):
        """Initialize the transcriber with configuration.

        Args:
            config: Transcription configuration
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._initialized = False
        self._audio_buffer = []
        self._session_active = False

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the transcription backend.

        Returns:
            True if initialization successful, False otherwise
        """
        pass

    @abstractmethod
    async def transcribe_chunk(self, audio_data: bytes) -> TranscriptionResult:
        """Transcribe a chunk of audio data.

        Args:
            audio_data: Raw audio data (16-bit PCM)

        Returns:
            TranscriptionResult with partial or complete text
        """
        pass

    @abstractmethod
    async def finalize(self) -> TranscriptionResult:
        """Finalize transcription and return complete result.

        Returns:
            TranscriptionResult with final transcription
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up transcription resources."""
        pass

    def start_session(self) -> None:
        """Start a new transcription session."""
        self._audio_buffer.clear()
        self._session_active = True
        self.logger.debug("Transcription session started")

    def end_session(self) -> None:
        """End the current transcription session."""
        self._session_active = False
        self.logger.debug("Transcription session ended")

    def reset_session(self) -> None:
        """Reset session state without destroying the transcriber.

        This method clears session-specific state (audio buffer, accumulated text)
        without destroying the underlying transcriber resources. Use this when
        you want to process multiple audio files with the same transcriber instance.
        """
        self._audio_buffer.clear()
        self._session_active = False
        self.logger.debug("Transcription session reset")

    def _convert_audio_for_processing(self, audio_data: bytes) -> np.ndarray:
        """Convert raw audio bytes to numpy array for processing.

        Args:
            audio_data: Raw audio bytes (16-bit PCM)

        Returns:
            Float32 numpy array normalized to [-1, 1]
        """
        try:
            # Convert bytes to int16 array
            audio_int16 = np.frombuffer(audio_data, dtype=np.int16)

            # Convert to float32 and normalize
            audio_float32 = audio_int16.astype(np.float32) / 32768.0

            return audio_float32
        except Exception as e:
            self.logger.error(f"Error converting audio data: {e}")
            return np.array([], dtype=np.float32)


class PocketSphinxTranscriber(BaseTranscriber):
    """PocketSphinx-based transcription for lightweight, offline processing."""

    def __init__(self, config: TranscriptionConfig):
        super().__init__(config)
        self._decoder = None
        self._accumulated_text = ""

    async def initialize(self) -> bool:
        """Initialize PocketSphinx decoder."""
        try:
            import os
            import tempfile

            import pocketsphinx

            # Configure PocketSphinx with cross-platform log suppression
            config_dict = {
                "verbose": False,
                "samprate": self.config.sample_rate,
            }

            # Handle log redirection cross-platform
            try:
                if os.name == "nt":  # Windows
                    # On Windows, try NUL device first, then skip if it fails
                    try:
                        config_dict["logfn"] = "NUL"
                    except Exception:
                        # Skip log redirection on Windows if it fails
                        pass
                else:  # Unix-like systems
                    config_dict["logfn"] = "/dev/null"
            except Exception:
                # If log redirection fails, just skip it entirely
                pass

            # Add custom models if specified
            if self.config.pocketsphinx_hmm:
                config_dict["hmm"] = self.config.pocketsphinx_hmm
            if self.config.pocketsphinx_lm:
                config_dict["lm"] = self.config.pocketsphinx_lm
            if self.config.pocketsphinx_dict:
                config_dict["dict"] = self.config.pocketsphinx_dict

            # Create decoder
            ps_config = pocketsphinx.Decoder.default_config()
            for key, value in config_dict.items():
                try:
                    ps_config.set_string(key, str(value))
                except Exception as e:
                    # Skip problematic configuration options
                    self.logger.debug(f"Skipping config option {key}: {e}")
                    continue

            self._decoder = pocketsphinx.Decoder(ps_config)
            self._initialized = True

            self.logger.info("PocketSphinx transcriber initialized successfully")
            return True

        except ImportError:
            self.logger.error(
                "PocketSphinx not available. Install with: pip install pocketsphinx"
            )
            return False
        except Exception as e:
            self.logger.error(f"Failed to initialize PocketSphinx: {e}")
            return False

    async def transcribe_chunk(self, audio_data: bytes) -> TranscriptionResult:
        """Transcribe audio chunk using PocketSphinx."""
        if not self._initialized or not self._decoder:
            return TranscriptionResult(text="", error="Transcriber not initialized")

        start_time = time.time()

        try:
            # Convert audio data
            audio_array = self._convert_audio_for_processing(audio_data)
            if len(audio_array) == 0:
                return TranscriptionResult(text="", error="Invalid audio data")

            # Add to buffer for continuous processing
            self._audio_buffer.extend(audio_array)

            # Process in chunks to simulate real-time transcription
            chunk_samples = int(self.config.sample_rate * self.config.chunk_duration)

            if len(self._audio_buffer) >= chunk_samples:
                # Extract chunk for processing
                chunk_data = np.array(self._audio_buffer[:chunk_samples])
                self._audio_buffer = self._audio_buffer[chunk_samples:]

                # Convert to int16 for PocketSphinx
                chunk_int16 = (chunk_data * 32767).astype(np.int16)

                # Process audio without starting/stopping utterance for each chunk
                # This allows for continuous processing
                self._decoder.process_raw(chunk_int16.tobytes(), False, False)

                # Get hypothesis
                hyp = self._decoder.hyp()
                current_text = hyp.hypstr if hyp else ""

                # Calculate delta (new text since last chunk)
                delta_text = ""
                if current_text and current_text != self._accumulated_text:
                    if current_text.startswith(self._accumulated_text):
                        delta_text = current_text[len(self._accumulated_text) :].strip()
                    else:
                        delta_text = current_text
                    self._accumulated_text = current_text

                processing_time = time.time() - start_time

                return TranscriptionResult(
                    text=delta_text,
                    confidence=hyp.prob if hyp else 0.0,
                    is_final=False,
                    processing_time=processing_time,
                )

            # Not enough data yet
            return TranscriptionResult(
                text="", processing_time=time.time() - start_time
            )

        except Exception as e:
            self.logger.error(f"Error in PocketSphinx transcription: {e}")
            return TranscriptionResult(
                text="", error=str(e), processing_time=time.time() - start_time
            )

    async def finalize(self) -> TranscriptionResult:
        """Finalize PocketSphinx transcription."""
        if not self._initialized or not self._decoder:
            return TranscriptionResult(text="", error="Transcriber not initialized")

        start_time = time.time()

        try:
            # Process any remaining audio
            if self._audio_buffer:
                remaining_audio = np.array(self._audio_buffer)
                chunk_int16 = (remaining_audio * 32767).astype(np.int16)
                self._decoder.process_raw(chunk_int16.tobytes(), False, True)

            # Get final hypothesis before ending utterance
            hyp = self._decoder.hyp()
            final_text = hyp.hypstr if hyp else self._accumulated_text

            processing_time = time.time() - start_time

            result = TranscriptionResult(
                text=final_text,
                confidence=hyp.prob if hyp else 0.0,
                is_final=True,
                processing_time=processing_time,
            )

            # Reset for next session
            self._accumulated_text = ""
            self._audio_buffer.clear()

            return result

        except Exception as e:
            self.logger.error(f"Error in PocketSphinx finalization: {e}")
            return TranscriptionResult(
                text=self._accumulated_text,
                error=str(e),
                is_final=True,
                processing_time=time.time() - start_time,
            )

    def start_session(self) -> None:
        """Start a new transcription session with utterance management."""
        super().start_session()
        # Start utterance for PocketSphinx
        if self._decoder:
            try:
                self._decoder.start_utt()
            except Exception as e:
                self.logger.debug(f"Could not start utterance: {e}")

    def end_session(self) -> None:
        """End the current transcription session with utterance management."""
        # End utterance for PocketSphinx
        if self._decoder:
            try:
                self._decoder.end_utt()
            except Exception as e:
                self.logger.debug(f"Could not end utterance: {e}")
        super().end_session()

    async def cleanup(self) -> None:
        """Clean up PocketSphinx resources."""
        if self._decoder:
            try:
                self._decoder.end_utt()
            except:
                pass
        self._decoder = None
        self._initialized = False
        self.logger.debug("PocketSphinx transcriber cleaned up")

    def reset_session(self) -> None:
        """Reset session state without destroying the transcriber."""
        self._audio_buffer.clear()
        self._accumulated_text = ""
        self._session_active = False
        # End any active utterance
        if self._decoder:
            try:
                self._decoder.end_utt()
            except:
                pass
        self.logger.debug("PocketSphinx session reset")


class WhisperTranscriber(BaseTranscriber):
    """Whisper-based transcription for high accuracy."""

    def __init__(self, config: TranscriptionConfig):
        super().__init__(config)
        self._model = None
        self._temp_dir = None
        self._accumulated_text = ""
        self._last_segment_end = 0.0

    async def initialize(self) -> bool:
        """Initialize Whisper model."""
        try:
            # Try to import whisper with error handling
            whisper = None
            try:
                # Try openai-whisper first
                import openai_whisper as whisper  # type: ignore
            except ImportError:
                try:
                    # Try regular whisper import
                    import whisper  # type: ignore
                except ImportError as e:
                    self.logger.error(f"Whisper not available: {e}")
                    return False

            if whisper is None:
                self.logger.error("Failed to import whisper module")
                return False

            # Load model
            model_name = self.config.model_size
            if self.config.whisper_model_dir:
                # Load from custom directory
                model_path = Path(self.config.whisper_model_dir) / f"{model_name}.pt"
                if model_path.exists():
                    self._model = whisper.load_model(str(model_path), device=self.config.device)  # type: ignore
                else:
                    self.logger.warning(
                        f"Custom model not found at {model_path}, using default"
                    )
                    self._model = whisper.load_model(model_name, device=self.config.device)  # type: ignore
            else:
                self._model = whisper.load_model(model_name, device=self.config.device)  # type: ignore

            # Create temporary directory for audio files
            self._temp_dir = tempfile.mkdtemp(prefix="whisper_transcription_")

            self._initialized = True
            self.logger.info(
                f"Whisper transcriber initialized with {model_name} model on {self.config.device}"
            )
            return True

        except ImportError:
            self.logger.error(
                "Whisper not available. Install with: pip install openai-whisper"
            )
            return False
        except Exception as e:
            self.logger.error(f"Failed to initialize Whisper: {e}")
            return False

    async def transcribe_chunk(self, audio_data: bytes) -> TranscriptionResult:
        """Transcribe audio chunk using Whisper."""
        if not self._initialized or not self._model:
            return TranscriptionResult(text="", error="Transcriber not initialized")

        start_time = time.time()

        try:
            # Convert audio data
            audio_array = self._convert_audio_for_processing(audio_data)
            if len(audio_array) == 0:
                return TranscriptionResult(text="", error="Invalid audio data")

            # Add to buffer
            self._audio_buffer.extend(audio_array)

            # Process in larger chunks for Whisper (it works better with more context)
            chunk_samples = int(
                self.config.sample_rate * self.config.chunk_duration * 2
            )  # 2x chunk duration

            if len(self._audio_buffer) >= chunk_samples:
                # Extract chunk for processing
                chunk_data = np.array(self._audio_buffer[:chunk_samples])

                # Keep some overlap for better transcription continuity
                overlap_samples = int(chunk_samples * 0.1)  # 10% overlap
                self._audio_buffer = self._audio_buffer[
                    chunk_samples - overlap_samples :
                ]

                # Run transcription in thread pool to avoid blocking
                result = await asyncio.get_event_loop().run_in_executor(
                    None, self._transcribe_with_whisper, chunk_data
                )

                processing_time = time.time() - start_time
                result.processing_time = processing_time

                return result

            # Not enough data yet
            return TranscriptionResult(
                text="", processing_time=time.time() - start_time
            )

        except Exception as e:
            self.logger.error(f"Error in Whisper transcription: {e}")
            return TranscriptionResult(
                text="", error=str(e), processing_time=time.time() - start_time
            )

    def _transcribe_with_whisper(self, audio_data: np.ndarray) -> TranscriptionResult:
        """Transcribe audio using Whisper model (runs in thread pool)."""
        try:
            # Whisper expects audio to be padded/trimmed to 30 seconds max
            target_length = self.config.sample_rate * 30  # 30 seconds
            if len(audio_data) > target_length:
                audio_data = audio_data[:target_length]
            elif len(audio_data) < target_length:
                # Pad with zeros
                padding = target_length - len(audio_data)
                audio_data = np.pad(audio_data, (0, padding), mode="constant")

            # Transcribe
            result = self._model.transcribe(  # type: ignore
                audio_data,
                language=self.config.language if self.config.language != "en" else None,
                temperature=self.config.whisper_temperature,
                word_timestamps=True,
                verbose=False,
            )

            # Extract text and segments
            text = result.get("text", "")
            if isinstance(text, str):
                text = text.strip()
            else:
                text = ""
            segments = result.get("segments", [])

            # Calculate delta (new text since last transcription)
            delta_text = ""
            if text and text != self._accumulated_text:
                if text.startswith(self._accumulated_text):
                    delta_text = text[len(self._accumulated_text) :].strip()
                else:
                    # Handle case where Whisper gives completely different result
                    delta_text = text
                self._accumulated_text = text

            # Calculate average confidence from segments
            confidence = 0.0
            if segments and isinstance(segments, list):
                valid_segments = [s for s in segments if isinstance(s, dict)]
                if valid_segments:
                    confidence = sum(
                        s.get("avg_logprob", 0.0) for s in valid_segments
                    ) / len(valid_segments)
                    # Convert log probability to a more intuitive confidence score
                    confidence = max(0.0, min(1.0, (confidence + 1.0) / 2.0))

            return TranscriptionResult(
                text=delta_text,
                confidence=confidence,
                is_final=False,
                segments=segments if isinstance(segments, list) else None,
            )

        except Exception as e:
            self.logger.error(f"Whisper transcription error: {e}")
            return TranscriptionResult(text="", error=str(e))

    async def finalize(self) -> TranscriptionResult:
        """Finalize Whisper transcription."""
        if not self._initialized or not self._model:
            return TranscriptionResult(text="", error="Transcriber not initialized")

        start_time = time.time()

        try:
            # Process any remaining audio
            if self._audio_buffer:
                remaining_audio = np.array(self._audio_buffer)
                result = await asyncio.get_event_loop().run_in_executor(
                    None, self._transcribe_with_whisper, remaining_audio
                )

                # Update accumulated text with final result
                if result.text:
                    self._accumulated_text = result.text

            processing_time = time.time() - start_time

            final_result = TranscriptionResult(
                text=self._accumulated_text,
                confidence=1.0,  # Final result is considered fully confident
                is_final=True,
                processing_time=processing_time,
            )

            # Reset for next session
            self._accumulated_text = ""
            self._audio_buffer.clear()

            return final_result

        except Exception as e:
            self.logger.error(f"Error in Whisper finalization: {e}")
            return TranscriptionResult(
                text=self._accumulated_text,
                error=str(e),
                is_final=True,
                processing_time=time.time() - start_time,
            )

    async def cleanup(self) -> None:
        """Clean up Whisper resources."""
        # Clean up temporary directory
        if self._temp_dir and Path(self._temp_dir).exists():
            import shutil

            try:
                shutil.rmtree(self._temp_dir)
            except Exception as e:
                self.logger.warning(f"Failed to clean up temp directory: {e}")

        self._model = None
        self._initialized = False
        self.logger.debug("Whisper transcriber cleaned up")

    def reset_session(self) -> None:
        """Reset session state without destroying the transcriber."""
        self._audio_buffer.clear()
        self._accumulated_text = ""
        self._session_active = False
        self.logger.debug("Whisper session reset")


class TranscriptionFactory:
    """Factory for creating transcription backends."""

    @staticmethod
    def create_transcriber(
        config: Union[Dict[str, Any], TranscriptionConfig],
    ) -> BaseTranscriber:
        """Create a transcriber based on configuration.

        Args:
            config: Configuration dictionary or TranscriptionConfig object

        Returns:
            Configured transcriber instance

        Raises:
            ValueError: If backend is not supported
        """
        if isinstance(config, dict):
            config = TranscriptionConfig(**config)

        backend = config.backend.lower()

        if backend == "pocketsphinx":
            return PocketSphinxTranscriber(config)
        elif backend == "whisper":
            return WhisperTranscriber(config)
        else:
            raise ValueError(f"Unsupported transcription backend: {backend}")

    @staticmethod
    def get_available_backends() -> List[str]:
        """Get list of available transcription backends.

        Returns:
            List of backend names that can be used
        """
        available = []

        try:
            import pocketsphinx

            available.append("pocketsphinx")
        except ImportError:
            pass

        # Skip whisper check to avoid conflicts with system whisper.py
        # Whisper availability will be checked when actually needed
        available.append("whisper")

        return available


def load_transcription_config() -> TranscriptionConfig:
    """Load transcription configuration from environment variables.

    Returns:
        TranscriptionConfig with values from environment or defaults
    """
    from opusagent.config.constants import (
        DEFAULT_SAMPLE_RATE,
        DEFAULT_TRANSCRIPTION_BACKEND,
        DEFAULT_TRANSCRIPTION_CHUNK_DURATION,
        DEFAULT_TRANSCRIPTION_CONFIDENCE_THRESHOLD,
        DEFAULT_TRANSCRIPTION_LANGUAGE,
        DEFAULT_WHISPER_MODEL_SIZE,
    )

    return TranscriptionConfig(
        backend=os.getenv("TRANSCRIPTION_BACKEND", DEFAULT_TRANSCRIPTION_BACKEND),
        language=os.getenv("TRANSCRIPTION_LANGUAGE", DEFAULT_TRANSCRIPTION_LANGUAGE),
        model_size=os.getenv("WHISPER_MODEL_SIZE", DEFAULT_WHISPER_MODEL_SIZE),
        chunk_duration=float(
            os.getenv(
                "TRANSCRIPTION_CHUNK_DURATION",
                str(DEFAULT_TRANSCRIPTION_CHUNK_DURATION),
            )
        ),
        confidence_threshold=float(
            os.getenv(
                "TRANSCRIPTION_CONFIDENCE_THRESHOLD",
                str(DEFAULT_TRANSCRIPTION_CONFIDENCE_THRESHOLD),
            )
        ),
        sample_rate=int(
            os.getenv("TRANSCRIPTION_SAMPLE_RATE", str(DEFAULT_SAMPLE_RATE))
        ),
        enable_vad=os.getenv("TRANSCRIPTION_ENABLE_VAD", "true").lower() == "true",
        device=os.getenv("WHISPER_DEVICE", "cpu"),
        pocketsphinx_hmm=os.getenv("POCKETSPHINX_HMM"),
        pocketsphinx_lm=os.getenv("POCKETSPHINX_LM"),
        pocketsphinx_dict=os.getenv("POCKETSPHINX_DICT"),
        whisper_model_dir=os.getenv("WHISPER_MODEL_DIR"),
        whisper_temperature=float(os.getenv("WHISPER_TEMPERATURE", "0.0")),
    )
