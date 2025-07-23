"""
PocketSphinx-based transcription backend for the transcription module.

This module provides:
- PocketSphinxTranscriber: A lightweight, offline transcription backend using PocketSphinx, optimized for real-time and resource-constrained environments.
- Implements audio resampling, preprocessing, and chunked streaming for best performance.

Usage:
    from opusagent.mock.transcription.backends.pocketsphinx import PocketSphinxTranscriber
    transcriber = PocketSphinxTranscriber(config)
"""

import logging
import numpy as np
from typing import Optional, Dict, Any

from ..base import BaseTranscriber
from ..models import TranscriptionConfig, TranscriptionResult

class PocketSphinxTranscriber(BaseTranscriber):
    """PocketSphinx-based transcription for lightweight, offline processing."""

    def __init__(self, config: TranscriptionConfig):
        super().__init__(config)
        self._decoder = None
        self._accumulated_text = ""
        if self.config.sample_rate != 16000:
            self.logger.warning(
                f"PocketSphinx works best with 16kHz audio. "
                f"Current sample rate: {self.config.sample_rate}Hz. "
                f"Auto-resampling is {'enabled' if self.config.pocketsphinx_auto_resample else 'disabled'}."
            )
        self.logger.info(
            f"PocketSphinx optimization settings: "
            f"preprocessing={self.config.pocketsphinx_audio_preprocessing}, "
            f"vad_settings={self.config.pocketsphinx_vad_settings}, "
            f"auto_resample={self.config.pocketsphinx_auto_resample}"
        )

    async def initialize(self) -> bool:
        try:
            import pocketsphinx
            config_dict = {
                "verbose": False,
                "samprate": self.config.sample_rate,
            }
            try:
                import os
                if os.name == "nt":
                    try:
                        config_dict["logfn"] = "NUL"
                    except Exception:
                        pass
                else:
                    config_dict["logfn"] = "/dev/null"
            except Exception:
                pass
            if self.config.pocketsphinx_hmm:
                config_dict["hmm"] = self.config.pocketsphinx_hmm
            if self.config.pocketsphinx_lm:
                config_dict["lm"] = self.config.pocketsphinx_lm
            if self.config.pocketsphinx_dict:
                config_dict["dict"] = self.config.pocketsphinx_dict
            ps_config = pocketsphinx.Decoder.default_config()
            for key, value in config_dict.items():
                try:
                    ps_config.set_string(key, str(value))
                except Exception as e:
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
        if not self._initialized or not self._decoder:
            return TranscriptionResult(text="", error="Transcriber not initialized")
        import time
        start_time = time.time()
        try:
            if self.config.pocketsphinx_auto_resample and self.config.pocketsphinx_input_sample_rate != 16000:
                audio_data = self._resample_audio_for_pocketsphinx(
                    audio_data, 
                    self.config.pocketsphinx_input_sample_rate, 
                    16000
                )
                self.logger.debug("Applied audio resampling for PocketSphinx optimization")
            audio_array = self._convert_audio_for_processing(audio_data)
            if len(audio_array) == 0:
                return TranscriptionResult(text="", error="Invalid audio data")
            audio_array = self._apply_audio_preprocessing(
                audio_array, 
                self.config.pocketsphinx_audio_preprocessing
            )
            self._audio_buffer.extend(audio_array)
            chunk_samples = int(16000 * self.config.chunk_duration)
            if len(self._audio_buffer) >= chunk_samples:
                chunk_data = np.array(self._audio_buffer[:chunk_samples])
                self._audio_buffer = self._audio_buffer[chunk_samples:]
                chunk_int16 = (chunk_data * 32767).astype(np.int16)
                self._decoder.process_raw(chunk_int16.tobytes(), False, False)
                hyp = self._decoder.hyp()
                current_text = hyp.hypstr if hyp else ""
                delta_text = ""
                if current_text and current_text != self._accumulated_text:
                    if current_text.startswith(self._accumulated_text):
                        delta_text = current_text[len(self._accumulated_text):].strip()
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
            return TranscriptionResult(
                text="", processing_time=time.time() - start_time
            )
        except Exception as e:
            self.logger.error(f"Error in PocketSphinx transcription: {e}")
            return TranscriptionResult(
                text="", error=str(e), processing_time=time.time() - start_time
            )

    async def finalize(self) -> TranscriptionResult:
        if not self._initialized or not self._decoder:
            return TranscriptionResult(text="", error="Transcriber not initialized")
        import time
        start_time = time.time()
        try:
            if self._audio_buffer:
                remaining_audio = np.array(self._audio_buffer)
                remaining_audio = self._apply_audio_preprocessing(
                    remaining_audio, 
                    self.config.pocketsphinx_audio_preprocessing
                )
                chunk_int16 = (remaining_audio * 32767).astype(np.int16)
                self._decoder.process_raw(chunk_int16.tobytes(), False, True)
            hyp = self._decoder.hyp()
            final_text = hyp.hypstr if hyp else self._accumulated_text
            processing_time = time.time() - start_time
            result = TranscriptionResult(
                text=final_text,
                confidence=hyp.prob if hyp else 0.0,
                is_final=True,
                processing_time=processing_time,
            )
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
        super().start_session()
        if self._decoder:
            try:
                self._decoder.start_utt()
            except Exception as e:
                self.logger.debug(f"Could not start utterance: {e}")

    def end_session(self) -> None:
        if self._decoder:
            try:
                self._decoder.end_utt()
            except Exception as e:
                self.logger.debug(f"Could not end utterance: {e}")
        super().end_session()

    async def cleanup(self) -> None:
        if self._decoder:
            try:
                self._decoder.end_utt()
            except:
                pass
        self._decoder = None
        self._initialized = False
        self.logger.debug("PocketSphinx transcriber cleaned up")

    def reset_session(self) -> None:
        self._audio_buffer.clear()
        self._accumulated_text = ""
        self._session_active = False
        if self._decoder:
            try:
                self._decoder.end_utt()
            except:
                pass
        self.logger.debug("PocketSphinx session reset") 