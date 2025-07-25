"""
Whisper-based transcription backend for the transcription module.

This module provides:
- WhisperTranscriber: A high-accuracy transcription backend using OpenAI Whisper, supporting multiple model sizes and advanced features.
- Implements async processing, segment timing, and confidence scoring for detailed transcription results.

Usage:
    from opusagent.mock.transcription.backends.whisper import WhisperTranscriber
    transcriber = WhisperTranscriber(config)
"""

import logging
from typing import Any, Dict, Optional

import numpy as np

from ..base import BaseTranscriber
from ..models import TranscriptionConfig, TranscriptionResult


class WhisperTranscriber(BaseTranscriber):
    """Whisper-based transcription for high accuracy."""

    def __init__(self, config: TranscriptionConfig):
        super().__init__(config)
        self._model = None
        self._temp_dir = None
        self._accumulated_text = ""
        self._last_segment_end = 0.0

    async def initialize(self) -> bool:
        try:
            whisper = None
            try:
                import openai_whisper as whisper  # type: ignore
            except ImportError:
                try:
                    import whisper  # type: ignore
                except ImportError as e:
                    self.logger.error(f"Whisper not available: {e}")
                    return False
            if whisper is None:
                self.logger.error("Failed to import whisper module")
                return False
            model_name = self.config.model_size
            import tempfile
            from pathlib import Path

            if self.config.whisper_model_dir:
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
        if not self._initialized or not self._model:
            return TranscriptionResult(text="", error="Transcriber not initialized")
        import time

        start_time = time.time()
        try:
            audio_array = self._convert_audio_for_processing(audio_data)
            if len(audio_array) == 0:
                return TranscriptionResult(text="", error="Invalid audio data")
            self._audio_buffer.extend(audio_array)
            chunk_samples = int(
                self.config.sample_rate * self.config.chunk_duration * 2
            )
            if len(self._audio_buffer) >= chunk_samples:
                chunk_data = np.array(self._audio_buffer[:chunk_samples])
                overlap_samples = int(chunk_samples * 0.1)
                self._audio_buffer = self._audio_buffer[
                    chunk_samples - overlap_samples :
                ]
                import asyncio

                result = await asyncio.get_event_loop().run_in_executor(
                    None, self._transcribe_with_whisper, chunk_data
                )
                processing_time = max(
                    time.time() - start_time, 0.001
                )  # Ensure minimum time
                result.processing_time = processing_time
                return result
            processing_time = max(
                time.time() - start_time, 0.001
            )  # Ensure minimum time
            return TranscriptionResult(text="", processing_time=processing_time)
        except Exception as e:
            self.logger.error(f"Error in Whisper transcription: {e}")
            processing_time = max(
                time.time() - start_time, 0.001
            )  # Ensure minimum time
            return TranscriptionResult(
                text="", error=str(e), processing_time=processing_time
            )

    def _transcribe_with_whisper(self, audio_data: np.ndarray) -> TranscriptionResult:
        try:
            target_length = self.config.sample_rate * 30
            if len(audio_data) > target_length:
                audio_data = audio_data[:target_length]
            elif len(audio_data) < target_length:
                padding = target_length - len(audio_data)
                audio_data = np.pad(audio_data, (0, padding), mode="constant")
            result = self._model.transcribe(  # type: ignore
                audio_data,
                language=self.config.language if self.config.language != "en" else None,
                temperature=self.config.whisper_temperature,
                word_timestamps=True,
                verbose=False,
            )
            text = result.get("text", "")
            if isinstance(text, str):
                text = text.strip()
            else:
                text = ""
            segments = result.get("segments", [])
            delta_text = ""
            if text and text != self._accumulated_text:
                if text.startswith(self._accumulated_text):
                    delta_text = text[len(self._accumulated_text) :].strip()
                else:
                    # Handle case where Whisper gives completely different result
                    # Check if the new text contains repetitions or duplications
                    if self._accumulated_text and self._accumulated_text in text:
                        # Find the last occurrence of accumulated text and take everything after it
                        last_pos = text.rfind(self._accumulated_text)
                        if last_pos != -1:
                            delta_text = text[
                                last_pos + len(self._accumulated_text) :
                            ].strip()
                        else:
                            delta_text = text.strip()
                    else:
                        delta_text = text.strip()

                # Update accumulated text only if we have meaningful delta
                if delta_text:
                    self._accumulated_text = text
            confidence = 0.0
            if segments and isinstance(segments, list):
                valid_segments = [s for s in segments if isinstance(s, dict)]
                if valid_segments:
                    confidence = sum(
                        s.get("avg_logprob", 0.0) for s in valid_segments
                    ) / len(valid_segments)
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
        if not self._initialized or not self._model:
            return TranscriptionResult(text="", error="Transcriber not initialized")
        import time

        start_time = time.time()
        try:
            final_text = self._accumulated_text
            if self._audio_buffer:
                remaining_audio = np.array(self._audio_buffer)
                import asyncio

                result = await asyncio.get_event_loop().run_in_executor(
                    None, self._transcribe_with_whisper, remaining_audio
                )
                if result.text:
                    # Only use the delta text from remaining audio, not the full result
                    # This prevents repetition of already transcribed content
                    if result.text.strip() and not final_text.endswith(
                        result.text.strip()
                    ):
                        final_text = (
                            final_text + " " + result.text.strip()
                            if final_text
                            else result.text.strip()
                        )
                    # Remove any leading/trailing whitespace and normalize
                    final_text = final_text.strip()
            processing_time = max(
                time.time() - start_time, 0.001
            )  # Ensure minimum time
            final_result = TranscriptionResult(
                text=final_text,
                confidence=1.0,
                is_final=True,
                processing_time=processing_time,
            )
            self._accumulated_text = ""
            self._audio_buffer.clear()
            return final_result
        except Exception as e:
            self.logger.error(f"Error in Whisper finalization: {e}")
            processing_time = max(
                time.time() - start_time, 0.001
            )  # Ensure minimum time
            return TranscriptionResult(
                text=self._accumulated_text,
                error=str(e),
                is_final=True,
                processing_time=processing_time,
            )

    async def cleanup(self) -> None:
        if self._temp_dir:
            import shutil
            from pathlib import Path

            try:
                shutil.rmtree(self._temp_dir)
            except Exception as e:
                self.logger.warning(f"Failed to clean up temp directory: {e}")
        self._model = None
        self._initialized = False
        self.logger.debug("Whisper transcriber cleaned up")

    def reset_session(self) -> None:
        self._audio_buffer.clear()
        self._accumulated_text = ""
        self._session_active = False
        self.logger.debug("Whisper session reset")
