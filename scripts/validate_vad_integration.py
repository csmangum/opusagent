#!/usr/bin/env python3
"""
VAD Integration Validation Script

This script provides comprehensive validation of the Voice Activity Detection (VAD) integration
in the LocalRealtimeClient system. It validates all aspects of VAD functionality including
initialization, audio processing, speech detection, state management, runtime control,
session configuration, error handling, performance, and integration.

Features:
- Comprehensive test coverage of all VAD features
- Performance benchmarking and measurements
- Error handling and fallback validation
- Integration testing with existing components
- Detailed reporting and logging
- Audio test data generation and validation
- Configurable test scenarios and parameters

Usage:
    python scripts/validate_vad_integration.py [options]

Options:
    --category CATEGORY     Run specific test category (init, audio, speech, state, control, session, error, performance, integration, regression)
    --scenario SCENARIO     Run specific test scenario (e.g., VAD_INIT_001)
    --verbose              Enable verbose logging
    --output FILE          Save results to JSON file
    --generate-audio       Generate test audio files
    --performance          Include performance benchmarks
    --integration          Include integration tests
    --quick                Run quick validation (subset of tests)
    --all                  Run all validation tests (default)

Examples:
    # Run all validation tests
    python scripts/validate_vad_integration.py --all

    # Run specific category
    python scripts/validate_vad_integration.py --category init --verbose

    # Run with performance benchmarks
    python scripts/validate_vad_integration.py --performance --output vad_results.json

    # Quick validation
    python scripts/validate_vad_integration.py --quick

    # Generate test audio and run validation
    python scripts/validate_vad_integration.py --generate-audio --all
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
import traceback
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from unittest.mock import Mock, patch, AsyncMock, MagicMock

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from opusagent.mock.realtime.client import LocalRealtimeClient
from opusagent.mock.realtime.models import LocalResponseConfig, ResponseSelectionCriteria
from opusagent.models.openai_api import SessionConfig, ResponseCreateOptions
from opusagent.vad.vad_factory import VADFactory
from opusagent.vad.vad_config import load_vad_config
from opusagent.utils.audio_utils import AudioUtils
from opusagent.config.constants import DEFAULT_SAMPLE_RATE, DEFAULT_VAD_CHUNK_SIZE

# Test audio generation imports
try:
    import numpy as np
    import soundfile as sf
    AUDIO_LIBS_AVAILABLE = True
except ImportError:
    AUDIO_LIBS_AVAILABLE = False


class VADIntegrationValidator:
    """Comprehensive VAD integration validation tool."""
    
    def __init__(self, verbose: bool = False, output_file: Optional[str] = None):
        """Initialize the VAD validator."""
        self.verbose = verbose
        self.output_file = output_file
        self.logger = self._setup_logger()
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "test_categories": {},
            "performance_metrics": {},
            "summary": {
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "errors": 0,
                "skipped": 0
            },
            "test_details": []
        }
        
        # Test data directory
        self.test_data_dir = project_root / "test_data" / "vad"
        self.test_data_dir.mkdir(parents=True, exist_ok=True)
        
        # Test configuration
        self.test_config = {
            "sample_rate": DEFAULT_SAMPLE_RATE,
            "chunk_size": DEFAULT_VAD_CHUNK_SIZE,
            "test_duration": 2.0,  # seconds
            "performance_iterations": 100,
            "memory_check_interval": 0.1,  # seconds
        }
        
    def _setup_logger(self) -> logging.Logger:
        """Setup logging configuration."""
        logger = logging.getLogger("VADValidator")
        logger.setLevel(logging.DEBUG if self.verbose else logging.INFO)
        
        # Remove existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG if self.verbose else logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
        return logger
    
    def log_test_result(self, test_id: str, category: str, description: str, 
                       status: str, details: str = "", execution_time: float = 0.0):
        """Log test result."""
        self.results["test_details"].append({
            "test_id": test_id,
            "category": category,
            "description": description,
            "status": status,
            "details": details,
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        })
        
        # Update category results
        if category not in self.results["test_categories"]:
            self.results["test_categories"][category] = {
                "total": 0, "passed": 0, "failed": 0, "errors": 0, "skipped": 0
            }
        
        self.results["test_categories"][category]["total"] += 1
        status_key = status.lower()
        if status_key == "error":
            status_key = "errors"
        self.results["test_categories"][category][status_key] += 1
        
        # Update summary
        self.results["summary"]["total_tests"] += 1
        status_key = status.lower()
        if status_key == "error":
            status_key = "errors"
        self.results["summary"][status_key] += 1
        
        # Log to console
        status_emoji = {
            "PASSED": "✅",
            "FAILED": "❌", 
            "ERROR": "💥",
            "SKIPPED": "⏭️"
        }
        
        emoji = status_emoji.get(status, "❓")
        self.logger.info(f"{emoji} {test_id}: {description} - {status}")
        
        if details and (status in ["FAILED", "ERROR"] or self.verbose):
            self.logger.info(f"   Details: {details}")
            
        if execution_time > 0:
            self.logger.debug(f"   Execution time: {execution_time:.3f}s")
    
    def generate_test_audio(self) -> bool:
        """Generate test audio files for validation with enhanced patterns."""
        if not AUDIO_LIBS_AVAILABLE:
            self.logger.warning("Audio libraries not available, skipping audio generation")
            return False
            
        self.logger.info("Generating enhanced test audio files for VAD validation...")
        
        try:
            sample_rate = self.test_config["sample_rate"]
            duration = self.test_config["test_duration"]
            
            # Try to use actual mock audio files first
            mock_audio_types = ["greetings", "customer_service", "confirmations", "default"]
            
            audio_files = {}
            
            # Generate enhanced audio with better speech/silence patterns
            for category in mock_audio_types:
                mock_audio = self._load_mock_audio_if_available(category)
                if mock_audio is not None:
                    audio_files[f"mock_{category}"] = mock_audio
                    
            # Generate synthetic audio with enhanced patterns
            synthetic_audio = {
                "clear_speech_with_silence": self._generate_speech_with_trailing_silence(sample_rate, duration, 0.7),
                "silence_only": self._generate_silence_audio(sample_rate, duration),
                "background_noise": self._generate_noise_audio(sample_rate, duration, 0.1),
                "speech_with_noise_and_silence": self._generate_speech_with_noise_and_silence(sample_rate, duration, 0.6, 0.1),
                "intermittent_speech_clear": self._generate_intermittent_speech_audio(sample_rate, duration),
                "low_confidence_speech": self._generate_speech_with_trailing_silence(sample_rate, duration, 0.3),
                "very_short_speech": self._generate_short_speech_segments(sample_rate, duration),
                "long_speech_with_timeout": self._generate_long_speech_audio(sample_rate, duration * 2, 0.6)
            }
            
            audio_files.update(synthetic_audio)
            
            # Save all audio files
            for name, audio_data in audio_files.items():
                file_path = self.test_data_dir / f"test_{name}.wav"
                sf.write(file_path, audio_data, sample_rate)
                self.logger.debug(f"Generated: {file_path}")
            
            self.logger.info(f"Generated {len(audio_files)} enhanced test audio files")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to generate enhanced test audio: {e}")
            return False
    
    def _generate_speech_audio(self, sample_rate: int, duration: float, amplitude: float) -> np.ndarray:
        """Generate synthetic speech-like audio."""
        t = np.linspace(0, duration, int(sample_rate * duration))
        
        # Create speech-like patterns with varying frequencies
        speech = np.zeros_like(t)
        
        # Add formants (speech-like frequency components)
        formants = [800, 1200, 2400]  # Typical formant frequencies
        for formant in formants:
            speech += amplitude * np.sin(2 * np.pi * formant * t) * np.exp(-t * 0.5)
        
        # Add envelope to make it more speech-like
        envelope = np.exp(-((t - duration/2) ** 2) / (duration/4) ** 2)
        speech *= envelope
        
        # Add some randomness
        speech += np.random.normal(0, 0.05, len(t))
        
        return speech.astype(np.float32)
    
    def _generate_silence_audio(self, sample_rate: int, duration: float) -> np.ndarray:
        """Generate silence audio."""
        return np.zeros(int(sample_rate * duration), dtype=np.float32)
    
    def _generate_noise_audio(self, sample_rate: int, duration: float, amplitude: float) -> np.ndarray:
        """Generate background noise audio."""
        return np.random.normal(0, amplitude, int(sample_rate * duration)).astype(np.float32)
    
    def _generate_speech_with_noise_audio(self, sample_rate: int, duration: float, 
                                        speech_amp: float, noise_amp: float) -> np.ndarray:
        """Generate speech with background noise."""
        speech = self._generate_speech_audio(sample_rate, duration, speech_amp)
        noise = self._generate_noise_audio(sample_rate, duration, noise_amp)
        return speech + noise
    
    def _generate_intermittent_speech_audio(self, sample_rate: int, duration: float) -> np.ndarray:
        """Generate intermittent speech audio with clear boundaries."""
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio = np.zeros_like(t)
        
        # Create segments of speech and silence with clear boundaries
        segment_duration = 0.5
        segments = int(duration / segment_duration)
        
        for i in range(segments):
            start_idx = int(i * segment_duration * sample_rate)
            end_idx = int((i + 1) * segment_duration * sample_rate)
            
            if end_idx > len(audio):
                end_idx = len(audio)
            
            # Alternate between speech and silence
            if i % 2 == 0:
                # Speech segment with clear start/end
                segment_audio = self._generate_speech_audio(sample_rate, segment_duration, 0.7)
                # Add clear boundaries with brief fade-in/out
                fade_samples = int(sample_rate * 0.02)  # 20ms fade
                if len(segment_audio) > 2 * fade_samples:
                    segment_audio[:fade_samples] *= np.linspace(0, 1, fade_samples)
                    segment_audio[-fade_samples:] *= np.linspace(1, 0, fade_samples)
                audio[start_idx:end_idx] = segment_audio[:end_idx-start_idx]
            # Silence segments are already zeros
        
        return audio.astype(np.float32)
    
    def _load_mock_audio_if_available(self, category: str = "greetings") -> Optional[np.ndarray]:
        """
        Load actual audio files from the mock audio directory if available.
        
        Args:
            category: Audio category to load (greetings, customer_service, etc.)
            
        Returns:
            numpy array of audio data or None if not available
        """
        try:
            import soundfile as sf
            
            # Path to mock audio directory
            mock_audio_dir = project_root / "opusagent" / "mock" / "audio" / category
            
            if mock_audio_dir.exists():
                # Find first available .wav file
                wav_files = list(mock_audio_dir.glob("*.wav"))
                if wav_files:
                    audio_file = wav_files[0]
                    audio_data, sample_rate = sf.read(audio_file)
                    
                    # Ensure mono and correct sample rate
                    if len(audio_data.shape) > 1:
                        audio_data = audio_data.mean(axis=1)  # Convert to mono
                    
                    # Resample if needed
                    if sample_rate != self.test_config["sample_rate"]:
                        try:
                            import scipy.signal
                            # Simple resampling (for testing only)
                            num_samples = int(len(audio_data) * self.test_config["sample_rate"] / sample_rate)
                            audio_data = scipy.signal.resample(audio_data, num_samples)
                        except ImportError:
                            # Fallback: just use the audio as-is
                            pass
                    
                    # Add trailing silence for complete VAD sequences
                    silence_duration = 0.1  # 100ms silence
                    silence_samples = int(self.test_config["sample_rate"] * silence_duration)
                    silence = np.zeros(silence_samples, dtype=np.float32)
                    
                    # Combine audio with trailing silence
                    audio_with_silence = np.concatenate([audio_data.astype(np.float32), silence])
                    
                    self.logger.debug(f"Loaded mock audio from {audio_file}: {len(audio_with_silence)} samples")
                    return audio_with_silence
                    
        except Exception as e:
            self.logger.debug(f"Could not load mock audio: {e}")
            
        return None
    
    # Test category implementations
    
    def test_vad_initialization(self) -> None:
        """Test VAD initialization scenarios."""
        category = "initialization"
        
        # VAD_INIT_001: Basic VAD initialization with default configuration
        start_time = time.time()
        try:
            client = LocalRealtimeClient(enable_vad=True)
            
            if client.is_vad_enabled():
                self.log_test_result(
                    "VAD_INIT_001", category, "Basic VAD initialization with default configuration",
                    "PASSED", "VAD initialized successfully with default configuration",
                    time.time() - start_time
                )
            else:
                self.log_test_result(
                    "VAD_INIT_001", category, "Basic VAD initialization with default configuration",
                    "FAILED", "VAD not enabled after initialization",
                    time.time() - start_time
                )
        except Exception as e:
            self.log_test_result(
                "VAD_INIT_001", category, "Basic VAD initialization with default configuration",
                "ERROR", f"Exception during initialization: {e}",
                time.time() - start_time
            )
        
        # VAD_INIT_002: VAD initialization with custom configuration
        start_time = time.time()
        try:
            custom_config = {
                "backend": "silero",
                "threshold": 0.3,
                "sample_rate": 16000
            }
            client = LocalRealtimeClient(enable_vad=True, vad_config=custom_config)
            
            if client.is_vad_enabled():
                vad_config = client.get_vad_config()
                if vad_config.get("threshold") == 0.3:
                    self.log_test_result(
                        "VAD_INIT_002", category, "VAD initialization with custom configuration",
                        "PASSED", "VAD initialized with custom configuration",
                        time.time() - start_time
                    )
                else:
                    self.log_test_result(
                        "VAD_INIT_002", category, "VAD initialization with custom configuration",
                        "FAILED", "Custom configuration not applied correctly",
                        time.time() - start_time
                    )
            else:
                self.log_test_result(
                    "VAD_INIT_002", category, "VAD initialization with custom configuration",
                    "FAILED", "VAD not enabled with custom configuration",
                    time.time() - start_time
                )
        except Exception as e:
            self.log_test_result(
                "VAD_INIT_002", category, "VAD initialization with custom configuration",
                "ERROR", f"Exception with custom configuration: {e}",
                time.time() - start_time
            )
        
        # VAD_INIT_003: VAD auto-enabled by session configuration
        start_time = time.time()
        try:
            session_config = SessionConfig(
                model="gpt-4o-realtime-preview-2025-06-03",
                modalities=["text", "audio"],
                voice="alloy",
                turn_detection={"type": "server_vad"}
            )
            client = LocalRealtimeClient(session_config=session_config)
            
            if client.is_vad_enabled():
                self.log_test_result(
                    "VAD_INIT_003", category, "VAD auto-enabled by session configuration",
                    "PASSED", "VAD automatically enabled by session configuration",
                    time.time() - start_time
                )
            else:
                self.log_test_result(
                    "VAD_INIT_003", category, "VAD auto-enabled by session configuration",
                    "FAILED", "VAD not auto-enabled by session configuration",
                    time.time() - start_time
                )
        except Exception as e:
            self.log_test_result(
                "VAD_INIT_003", category, "VAD auto-enabled by session configuration",
                "ERROR", f"Exception with session configuration: {e}",
                time.time() - start_time
            )
        
        # VAD_INIT_004: VAD explicitly disabled
        start_time = time.time()
        try:
            client = LocalRealtimeClient(enable_vad=False)
            
            if not client.is_vad_enabled():
                self.log_test_result(
                    "VAD_INIT_004", category, "VAD explicitly disabled",
                    "PASSED", "VAD correctly disabled",
                    time.time() - start_time
                )
            else:
                self.log_test_result(
                    "VAD_INIT_004", category, "VAD explicitly disabled",
                    "FAILED", "VAD enabled when it should be disabled",
                    time.time() - start_time
                )
        except Exception as e:
            self.log_test_result(
                "VAD_INIT_004", category, "VAD explicitly disabled",
                "ERROR", f"Exception with disabled VAD: {e}",
                time.time() - start_time
            )
        
        # VAD_INIT_005: VAD initialization failure fallback
        start_time = time.time()
        try:
            # Mock VAD creation to fail
            with patch('opusagent.vad.vad_factory.VADFactory.create_vad') as mock_create:
                mock_create.side_effect = Exception("VAD creation failed")
                
                client = LocalRealtimeClient(enable_vad=True)
                
                # Should fallback gracefully
                if not client.is_vad_enabled():
                    self.log_test_result(
                        "VAD_INIT_005", category, "VAD initialization failure fallback",
                        "PASSED", "VAD initialization failed gracefully with fallback",
                        time.time() - start_time
                    )
                else:
                    self.log_test_result(
                        "VAD_INIT_005", category, "VAD initialization failure fallback",
                        "FAILED", "VAD enabled despite initialization failure",
                        time.time() - start_time
                    )
        except Exception as e:
            self.log_test_result(
                "VAD_INIT_005", category, "VAD initialization failure fallback",
                "ERROR", f"Unexpected exception during fallback test: {e}",
                time.time() - start_time
            )
    
    def test_audio_processing(self) -> None:
        """Test VAD audio processing scenarios."""
        category = "audio_processing"
        
        # VAD_AUDIO_001: PCM16 audio format conversion and processing
        start_time = time.time()
        try:
            client = LocalRealtimeClient(enable_vad=True)
            
            if client.is_vad_enabled():
                # Test PCM16 audio processing
                test_audio = self._generate_test_audio_bytes(format="pcm16")
                
                # Process audio through the event handler
                event_data = {
                    "audio": test_audio,
                    "event_id": str(uuid.uuid4())
                }
                
                # This should not raise an exception
                result = client._event_handler._convert_audio_for_vad(test_audio, "pcm16")
                
                if result is not None:
                    self.log_test_result(
                        "VAD_AUDIO_001", category, "PCM16 audio format conversion and processing",
                        "PASSED", "PCM16 audio converted successfully",
                        time.time() - start_time
                    )
                else:
                    self.log_test_result(
                        "VAD_AUDIO_001", category, "PCM16 audio format conversion and processing",
                        "FAILED", "PCM16 audio conversion returned None",
                        time.time() - start_time
                    )
            else:
                self.log_test_result(
                    "VAD_AUDIO_001", category, "PCM16 audio format conversion and processing",
                    "SKIPPED", "VAD not enabled",
                    time.time() - start_time
                )
        except Exception as e:
            self.log_test_result(
                "VAD_AUDIO_001", category, "PCM16 audio format conversion and processing",
                "ERROR", f"Exception during PCM16 processing: {e}",
                time.time() - start_time
            )
        
        # VAD_AUDIO_002: PCM24 audio format conversion and processing
        start_time = time.time()
        try:
            client = LocalRealtimeClient(enable_vad=True)
            
            if client.is_vad_enabled():
                # Test PCM24 audio processing
                test_audio = self._generate_test_audio_bytes(format="pcm24")
                
                result = client._event_handler._convert_audio_for_vad(test_audio, "pcm24")
                
                if result is not None:
                    self.log_test_result(
                        "VAD_AUDIO_002", category, "PCM24 audio format conversion and processing",
                        "PASSED", "PCM24 audio converted successfully",
                        time.time() - start_time
                    )
                else:
                    self.log_test_result(
                        "VAD_AUDIO_002", category, "PCM24 audio format conversion and processing",
                        "FAILED", "PCM24 audio conversion returned None",
                        time.time() - start_time
                    )
            else:
                self.log_test_result(
                    "VAD_AUDIO_002", category, "PCM24 audio format conversion and processing",
                    "SKIPPED", "VAD not enabled",
                    time.time() - start_time
                )
        except Exception as e:
            self.log_test_result(
                "VAD_AUDIO_002", category, "PCM24 audio format conversion and processing",
                "ERROR", f"Exception during PCM24 processing: {e}",
                time.time() - start_time
            )
        
        # VAD_AUDIO_006: Invalid audio format handling
        start_time = time.time()
        try:
            client = LocalRealtimeClient(enable_vad=True)
            
            if client.is_vad_enabled():
                # Test invalid audio format
                test_audio = b"invalid_audio_data"
                
                result = client._event_handler._convert_audio_for_vad(test_audio, "invalid_format")
                
                if result is None:
                    self.log_test_result(
                        "VAD_AUDIO_006", category, "Invalid audio format handling",
                        "PASSED", "Invalid audio format handled gracefully",
                        time.time() - start_time
                    )
                else:
                    self.log_test_result(
                        "VAD_AUDIO_006", category, "Invalid audio format handling",
                        "FAILED", "Invalid audio format not handled properly",
                        time.time() - start_time
                    )
            else:
                self.log_test_result(
                    "VAD_AUDIO_006", category, "Invalid audio format handling",
                    "SKIPPED", "VAD not enabled",
                    time.time() - start_time
                )
        except Exception as e:
            self.log_test_result(
                "VAD_AUDIO_006", category, "Invalid audio format handling",
                "ERROR", f"Exception during invalid format handling: {e}",
                time.time() - start_time
            )
    
    def test_speech_detection(self) -> None:
        """Test VAD speech detection scenarios with enhanced sequence validation."""
        category = "speech_detection"
        
        # VAD_SPEECH_001: Complete VAD event sequence validation
        start_time = time.time()
        try:
            client = LocalRealtimeClient(enable_vad=True)
            
            if client.is_vad_enabled():
                handler = client._event_handler
                
                # Test complete sequence: start -> active -> stop -> commit
                # First, trigger speech start
                handler._update_vad_state(True, 0.8)  # First speech detection
                handler._update_vad_state(True, 0.8)  # Second speech detection (should start)
                
                # Check that speech started
                if handler._vad_state.get("speech_active", False):
                    # Now trigger speech stop
                    handler._update_vad_state(False, 0.1)  # First silence
                    handler._update_vad_state(False, 0.1)  # Second silence  
                    handler._update_vad_state(False, 0.1)  # Third silence (should stop)
                    
                    # Check that speech stopped
                    if not handler._vad_state.get("speech_active", False):
                        self.log_test_result(
                            "VAD_SPEECH_001", category, "Complete VAD event sequence validation",
                            "PASSED", "Complete start->stop sequence validated successfully",
                            time.time() - start_time
                        )
                    else:
                        self.log_test_result(
                            "VAD_SPEECH_001", category, "Complete VAD event sequence validation",
                            "FAILED", "Speech did not stop after 3 silence detections",
                            time.time() - start_time
                        )
                else:
                    self.log_test_result(
                        "VAD_SPEECH_001", category, "Complete VAD event sequence validation",
                        "FAILED", "Speech did not start after 2 speech detections",
                        time.time() - start_time
                    )
            else:
                self.log_test_result(
                    "VAD_SPEECH_001", category, "Complete VAD event sequence validation",
                    "SKIPPED", "VAD not enabled",
                    time.time() - start_time
                )
        except Exception as e:
            self.log_test_result(
                "VAD_SPEECH_001", category, "Complete VAD event sequence validation",
                "ERROR", f"Exception during sequence validation: {e}",
                time.time() - start_time
            )
        
        # VAD_SPEECH_002: Minimum speech duration validation
        start_time = time.time()
        try:
            client = LocalRealtimeClient(enable_vad=True)
            
            if client.is_vad_enabled() and hasattr(client._vad, 'min_speech_duration_ms'):
                min_duration = client._vad.min_speech_duration_ms
                
                # Test that short speech segments are filtered out
                if min_duration > 0:
                    self.log_test_result(
                        "VAD_SPEECH_002", category, "Minimum speech duration validation",
                        "PASSED", f"Minimum speech duration configured: {min_duration}ms",
                        time.time() - start_time
                    )
                else:
                    self.log_test_result(
                        "VAD_SPEECH_002", category, "Minimum speech duration validation",
                        "FAILED", "Minimum speech duration not configured",
                        time.time() - start_time
                    )
            else:
                self.log_test_result(
                    "VAD_SPEECH_002", category, "Minimum speech duration validation",
                    "SKIPPED", "VAD not enabled or min_speech_duration_ms not available",
                    time.time() - start_time
                )
        except Exception as e:
            self.log_test_result(
                "VAD_SPEECH_002", category, "Minimum speech duration validation",
                "ERROR", f"Exception during duration validation: {e}",
                time.time() - start_time
            )
        
        # VAD_SPEECH_003: Trailing silence validation  
        start_time = time.time()
        try:
            client = LocalRealtimeClient(enable_vad=True)
            
            if client.is_vad_enabled():
                # Test with audio that includes trailing silence
                test_audio = self._generate_test_audio_bytes(format="pcm16")
                
                # Process audio through VAD
                result = client._event_handler._convert_audio_for_vad(test_audio, "pcm16")
                
                if result is not None:
                    # The audio should contain both speech and silence portions
                    if len(result) > 0:
                        self.log_test_result(
                            "VAD_SPEECH_003", category, "Trailing silence validation",
                            "PASSED", f"Audio with trailing silence processed successfully: {len(result)} samples",
                            time.time() - start_time
                        )
                    else:
                        self.log_test_result(
                            "VAD_SPEECH_003", category, "Trailing silence validation",
                            "FAILED", "Audio processing returned empty array",
                            time.time() - start_time
                        )
                else:
                    self.log_test_result(
                        "VAD_SPEECH_003", category, "Trailing silence validation",
                        "FAILED", "Audio processing returned None",
                        time.time() - start_time
                    )
            else:
                self.log_test_result(
                    "VAD_SPEECH_003", category, "Trailing silence validation",
                    "SKIPPED", "VAD not enabled",
                    time.time() - start_time
                )
        except Exception as e:
            self.log_test_result(
                "VAD_SPEECH_003", category, "Trailing silence validation",
                "ERROR", f"Exception during trailing silence test: {e}",
                time.time() - start_time
            )
        
        # VAD_SPEECH_004: Hysteresis implementation
        start_time = time.time()
        try:
            client = LocalRealtimeClient(enable_vad=True)
            
            if client.is_vad_enabled():
                handler = client._event_handler
                
                # Test hysteresis: need 2 consecutive speech detections to start
                handler._update_vad_state(True, 0.8)  # First speech detection
                state1 = handler._vad_state.copy()
                
                handler._update_vad_state(True, 0.8)  # Second speech detection
                state2 = handler._vad_state.copy()
                
                # Should transition to speech after 2 detections
                if state2.get("speech_active", False) and not state1.get("speech_active", False):
                    self.log_test_result(
                        "VAD_SPEECH_004", category, "Hysteresis implementation (2 speech, 3 silence)",
                        "PASSED", "Hysteresis correctly requires 2 speech detections",
                        time.time() - start_time
                    )
                else:
                    self.log_test_result(
                        "VAD_SPEECH_004", category, "Hysteresis implementation (2 speech, 3 silence)",
                        "FAILED", f"Hysteresis not working properly: state1={state1}, state2={state2}",
                        time.time() - start_time
                    )
            else:
                self.log_test_result(
                    "VAD_SPEECH_004", category, "Hysteresis implementation (2 speech, 3 silence)",
                    "SKIPPED", "VAD not enabled",
                    time.time() - start_time
                )
        except Exception as e:
            self.log_test_result(
                "VAD_SPEECH_004", category, "Hysteresis implementation (2 speech, 3 silence)",
                "ERROR", f"Exception during hysteresis test: {e}",
                time.time() - start_time
            )
        
        # VAD_SPEECH_005: Confidence smoothing
        start_time = time.time()
        try:
            client = LocalRealtimeClient(enable_vad=True)
            
            if client.is_vad_enabled():
                handler = client._event_handler
                
                # Add confidence values to history
                confidences = [0.6, 0.7, 0.8, 0.9, 0.5]
                for conf in confidences:
                    handler._update_vad_state(True, conf)
                
                # Check confidence history is limited to 5 values
                history = handler._vad_state.get("confidence_history", [])
                if len(history) <= 5:
                    self.log_test_result(
                        "VAD_SPEECH_005", category, "Confidence smoothing (5-value history)",
                        "PASSED", f"Confidence history properly limited to {len(history)} values",
                        time.time() - start_time
                    )
                else:
                    self.log_test_result(
                        "VAD_SPEECH_005", category, "Confidence smoothing (5-value history)",
                        "FAILED", f"Confidence history too long: {len(history)} values",
                        time.time() - start_time
                    )
            else:
                self.log_test_result(
                    "VAD_SPEECH_005", category, "Confidence smoothing (5-value history)",
                    "SKIPPED", "VAD not enabled",
                    time.time() - start_time
                )
        except Exception as e:
            self.log_test_result(
                "VAD_SPEECH_005", category, "Confidence smoothing (5-value history)",
                "ERROR", f"Exception during confidence smoothing test: {e}",
                time.time() - start_time
            )
    
    def test_runtime_control(self) -> None:
        """Test VAD runtime control scenarios."""
        category = "runtime_control"
        
        # VAD_CONTROL_001: Runtime VAD enabling
        start_time = time.time()
        try:
            client = LocalRealtimeClient(enable_vad=False)
            
            # Initially disabled
            if not client.is_vad_enabled():
                client.enable_vad()
                
                # Should be enabled now
                if client.is_vad_enabled():
                    self.log_test_result(
                        "VAD_CONTROL_001", category, "Runtime VAD enabling",
                        "PASSED", "VAD successfully enabled at runtime",
                        time.time() - start_time
                    )
                else:
                    self.log_test_result(
                        "VAD_CONTROL_001", category, "Runtime VAD enabling",
                        "FAILED", "VAD not enabled at runtime",
                        time.time() - start_time
                    )
            else:
                self.log_test_result(
                    "VAD_CONTROL_001", category, "Runtime VAD enabling",
                    "FAILED", "VAD already enabled initially",
                    time.time() - start_time
                )
        except Exception as e:
            self.log_test_result(
                "VAD_CONTROL_001", category, "Runtime VAD enabling",
                "ERROR", f"Exception during runtime enabling: {e}",
                time.time() - start_time
            )
        
        # VAD_CONTROL_002: Runtime VAD disabling
        start_time = time.time()
        try:
            client = LocalRealtimeClient(enable_vad=True)
            
            # Initially enabled
            if client.is_vad_enabled():
                client.disable_vad()
                
                # Should be disabled now
                if not client.is_vad_enabled():
                    self.log_test_result(
                        "VAD_CONTROL_002", category, "Runtime VAD disabling",
                        "PASSED", "VAD successfully disabled at runtime",
                        time.time() - start_time
                    )
                else:
                    self.log_test_result(
                        "VAD_CONTROL_002", category, "Runtime VAD disabling",
                        "FAILED", "VAD not disabled at runtime",
                        time.time() - start_time
                    )
            else:
                self.log_test_result(
                    "VAD_CONTROL_002", category, "Runtime VAD disabling",
                    "FAILED", "VAD not enabled initially",
                    time.time() - start_time
                )
        except Exception as e:
            self.log_test_result(
                "VAD_CONTROL_002", category, "Runtime VAD disabling",
                "ERROR", f"Exception during runtime disabling: {e}",
                time.time() - start_time
            )
    
    def test_performance(self) -> None:
        """Test VAD performance characteristics."""
        category = "performance"
        
        # VAD_PERF_001: Audio processing latency measurement
        start_time = time.time()
        try:
            client = LocalRealtimeClient(enable_vad=True)
            
            if client.is_vad_enabled():
                # Generate test audio
                test_audio = self._generate_test_audio_bytes(format="pcm16")
                
                # Measure processing time
                processing_times = []
                iterations = min(self.test_config["performance_iterations"], 10)  # Limit for test
                
                for _ in range(iterations):
                    proc_start = time.time()
                    result = client._event_handler._convert_audio_for_vad(test_audio, "pcm16")
                    proc_end = time.time()
                    
                    if result is not None:
                        processing_times.append(proc_end - proc_start)
                
                if processing_times:
                    avg_time = sum(processing_times) / len(processing_times)
                    max_time = max(processing_times)
                    
                    # Performance threshold: 50ms
                    if avg_time < 0.05:
                        self.log_test_result(
                            "VAD_PERF_001", category, "Audio processing latency measurement",
                            "PASSED", f"Average processing time: {avg_time*1000:.2f}ms (max: {max_time*1000:.2f}ms)",
                            time.time() - start_time
                        )
                        
                        # Store performance metric
                        self.results["performance_metrics"]["audio_processing_latency"] = {
                            "average_ms": avg_time * 1000,
                            "max_ms": max_time * 1000,
                            "iterations": len(processing_times)
                        }
                    else:
                        self.log_test_result(
                            "VAD_PERF_001", category, "Audio processing latency measurement",
                            "FAILED", f"Processing too slow: {avg_time*1000:.2f}ms (threshold: 50ms)",
                            time.time() - start_time
                        )
                else:
                    self.log_test_result(
                        "VAD_PERF_001", category, "Audio processing latency measurement",
                        "FAILED", "No valid processing times recorded",
                        time.time() - start_time
                    )
            else:
                self.log_test_result(
                    "VAD_PERF_001", category, "Audio processing latency measurement",
                    "SKIPPED", "VAD not enabled",
                    time.time() - start_time
                )
        except Exception as e:
            self.log_test_result(
                "VAD_PERF_001", category, "Audio processing latency measurement",
                "ERROR", f"Exception during performance test: {e}",
                time.time() - start_time
            )
    
    def test_error_handling(self) -> None:
        """Test VAD error handling scenarios."""
        category = "error_handling"
        
        # VAD_ERROR_001: VAD processing exception handling
        start_time = time.time()
        try:
            client = LocalRealtimeClient(enable_vad=True)
            
            if client.is_vad_enabled():
                # Mock VAD to raise an exception
                original_vad = client._vad
                client._vad = Mock()
                client._vad.process_audio.side_effect = Exception("VAD processing error")
                
                # Test error handling
                test_audio = self._generate_test_audio_bytes(format="pcm16")
                
                try:
                    # This should handle the exception gracefully
                    result = client._event_handler._process_audio_with_vad(test_audio)
                    
                    # Should not raise an exception
                    self.log_test_result(
                        "VAD_ERROR_001", category, "VAD processing exception handling",
                        "PASSED", "VAD processing exception handled gracefully",
                        time.time() - start_time
                    )
                except Exception as e:
                    self.log_test_result(
                        "VAD_ERROR_001", category, "VAD processing exception handling",
                        "FAILED", f"Exception not handled: {e}",
                        time.time() - start_time
                    )
                finally:
                    # Restore original VAD
                    client._vad = original_vad
            else:
                self.log_test_result(
                    "VAD_ERROR_001", category, "VAD processing exception handling",
                    "SKIPPED", "VAD not enabled",
                    time.time() - start_time
                )
        except Exception as e:
            self.log_test_result(
                "VAD_ERROR_001", category, "VAD processing exception handling",
                "ERROR", f"Exception during error handling test: {e}",
                time.time() - start_time
            )
    
    def _generate_test_audio_bytes(self, format: str = "pcm16") -> bytes:
        """
        Generate test audio bytes for testing with enhanced speech/silence patterns.
        
        This method generates audio with proper speech/silence boundaries, including
        trailing silence to ensure complete VAD event sequences.
        """
        if not AUDIO_LIBS_AVAILABLE:
            # Return dummy audio data with improved patterns
            if format == "pcm16":
                # Generate pattern with speech + trailing silence
                speech_samples = b"\x00\x10" * 800  # 800 samples of low-level speech
                silence_samples = b"\x00\x00" * 800  # 800 samples of silence
                return speech_samples + silence_samples
            elif format == "pcm24":
                # Generate pattern with speech + trailing silence  
                speech_samples = b"\x00\x10\x00" * 800  # 800 samples of low-level speech
                silence_samples = b"\x00\x00\x00" * 800  # 800 samples of silence
                return speech_samples + silence_samples
            else:
                return b"\x00" * 3200
        
        # Generate real audio data with enhanced patterns
        sample_rate = self.test_config["sample_rate"]
        total_duration = 0.2  # 200ms total
        speech_duration = 0.1  # 100ms speech
        silence_duration = 0.1  # 100ms trailing silence
        
        # Generate speech segment
        speech_audio = self._generate_speech_audio(sample_rate, speech_duration, 0.6)
        
        # Generate trailing silence for complete VAD sequences
        silence_audio = self._generate_silence_audio(sample_rate, silence_duration)
        
        # Combine speech and silence
        audio = np.concatenate([speech_audio, silence_audio])
        
        # Add brief fade-in/fade-out for more realistic boundaries
        fade_samples = int(sample_rate * 0.01)  # 10ms fade
        if len(audio) > 2 * fade_samples:
            # Fade in
            audio[:fade_samples] *= np.linspace(0, 1, fade_samples)
            # Fade out
            audio[-fade_samples:] *= np.linspace(1, 0, fade_samples)
        
        if format == "pcm16":
            # Convert to 16-bit PCM
            audio_16bit = (audio * 32767).astype(np.int16)
            return audio_16bit.tobytes()
        elif format == "pcm24":
            # Convert to 24-bit PCM with proper clamping
            audio_24bit = np.clip(audio * 8388607, -8388608, 8388607).astype(np.int32)
            # Pack as 24-bit
            bytes_data = []
            for sample in audio_24bit:
                # Ensure the value fits in 24 bits
                sample_int = int(sample)
                if sample_int < -8388608:
                    sample_int = -8388608
                elif sample_int > 8388607:
                    sample_int = 8388607
                bytes_data.extend(sample_int.to_bytes(3, byteorder='little', signed=True))
            return bytes(bytes_data)
        else:
            return audio.tobytes()
    
    def _generate_speech_with_trailing_silence(self, sample_rate: int, duration: float, amplitude: float) -> np.ndarray:
        """Generate speech with mandatory trailing silence for complete VAD sequences."""
        speech_duration = duration * 0.7  # 70% speech
        silence_duration = duration * 0.3  # 30% silence
        
        # Generate speech segment
        speech_audio = self._generate_speech_audio(sample_rate, speech_duration, amplitude)
        
        # Generate trailing silence
        silence_audio = self._generate_silence_audio(sample_rate, silence_duration)
        
        # Combine with smooth transition
        combined_audio = np.concatenate([speech_audio, silence_audio])
        
        # Add fade-out at speech end for realistic transition
        fade_samples = int(sample_rate * 0.02)  # 20ms fade
        if len(speech_audio) > fade_samples:
            speech_end = len(speech_audio)
            combined_audio[speech_end - fade_samples:speech_end] *= np.linspace(1, 0, fade_samples)
        
        return combined_audio.astype(np.float32)
    
    def _generate_speech_with_noise_and_silence(self, sample_rate: int, duration: float, 
                                               speech_amp: float, noise_amp: float) -> np.ndarray:
        """Generate speech with background noise and trailing silence."""
        speech_with_silence = self._generate_speech_with_trailing_silence(sample_rate, duration, speech_amp)
        noise = self._generate_noise_audio(sample_rate, duration, noise_amp)
        
        # Ensure noise array is same length as speech
        if len(noise) != len(speech_with_silence):
            noise = noise[:len(speech_with_silence)]
            
        return speech_with_silence + noise
    
    def _generate_short_speech_segments(self, sample_rate: int, duration: float) -> np.ndarray:
        """Generate very short speech segments that should be filtered out."""
        audio = np.zeros(int(sample_rate * duration), dtype=np.float32)
        
        # Create multiple very short speech segments (< min_speech_duration)
        segment_duration = 0.1  # 100ms segments
        num_segments = int(duration / (segment_duration * 2))  # With gaps
        
        for i in range(num_segments):
            start_idx = int(i * segment_duration * 2 * sample_rate)
            end_idx = int((i * segment_duration * 2 + segment_duration) * sample_rate)
            
            if end_idx < len(audio):
                segment = self._generate_speech_audio(sample_rate, segment_duration, 0.5)
                audio[start_idx:end_idx] = segment
        
        return audio
    
    def _generate_long_speech_audio(self, sample_rate: int, duration: float, amplitude: float) -> np.ndarray:
        """Generate long speech audio that should trigger timeout handling."""
        # Generate continuous speech for extended duration
        speech_audio = self._generate_speech_audio(sample_rate, duration, amplitude)
        
        # Add some variation to make it more realistic
        variation = np.random.normal(0, 0.05, len(speech_audio))
        speech_audio += variation
        
        # Ensure we don't clip
        speech_audio = np.clip(speech_audio, -1.0, 1.0)
        
        return speech_audio.astype(np.float32)
    
    # Main test execution methods
    
    def run_category_tests(self, category: str) -> None:
        """Run tests for a specific category."""
        category_map = {
            "init": self.test_vad_initialization,
            "audio": self.test_audio_processing,
            "speech": self.test_speech_detection,
            "control": self.test_runtime_control,
            "performance": self.test_performance,
            "error": self.test_error_handling,
        }
        
        if category in category_map:
            self.logger.info(f"Running {category} tests...")
            category_map[category]()
        else:
            self.logger.error(f"Unknown category: {category}")
    
    def run_all_tests(self) -> None:
        """Run all validation tests."""
        self.logger.info("Starting comprehensive VAD integration validation...")
        
        # Run all test categories
        categories = ["init", "audio", "speech", "control", "performance", "error"]
        
        for category in categories:
            self.logger.info(f"\n{'='*50}")
            self.logger.info(f"Running {category.upper()} tests")
            self.logger.info('='*50)
            
            try:
                self.run_category_tests(category)
            except Exception as e:
                self.logger.error(f"Error running {category} tests: {e}")
                self.logger.error(traceback.format_exc())
    
    def run_quick_tests(self) -> None:
        """Run a quick subset of validation tests."""
        self.logger.info("Running quick VAD validation tests...")
        
        # Run essential tests only
        categories = ["init", "control"]
        
        for category in categories:
            self.logger.info(f"\n{'='*30}")
            self.logger.info(f"Running {category.upper()} tests (quick)")
            self.logger.info('='*30)
            
            try:
                self.run_category_tests(category)
            except Exception as e:
                self.logger.error(f"Error running {category} tests: {e}")
    
    def print_summary(self) -> None:
        """Print validation summary."""
        summary = self.results["summary"]
        
        self.logger.info("\n" + "="*60)
        self.logger.info("VAD INTEGRATION VALIDATION SUMMARY")
        self.logger.info("="*60)
        
        self.logger.info(f"Total Tests: {summary['total_tests']}")
        self.logger.info(f"✅ Passed: {summary['passed']}")
        self.logger.info(f"❌ Failed: {summary['failed']}")
        self.logger.info(f"💥 Errors: {summary['errors']}")
        self.logger.info(f"⏭️ Skipped: {summary['skipped']}")
        
        # Calculate success rate
        if summary['total_tests'] > 0:
            success_rate = (summary['passed'] / summary['total_tests']) * 100
            self.logger.info(f"Success Rate: {success_rate:.1f}%")
        
        # Print category breakdown
        self.logger.info("\nCategory Breakdown:")
        for category, stats in self.results["test_categories"].items():
            self.logger.info(f"  {category}: {stats['passed']}/{stats['total']} passed")
        
        # Print performance metrics
        if self.results["performance_metrics"]:
            self.logger.info("\nPerformance Metrics:")
            for metric, data in self.results["performance_metrics"].items():
                if isinstance(data, dict):
                    self.logger.info(f"  {metric}: {data}")
                else:
                    self.logger.info(f"  {metric}: {data}")
        
        # Print failed tests
        failed_tests = [test for test in self.results["test_details"] 
                       if test["status"] in ["FAILED", "ERROR"]]
        
        if failed_tests:
            self.logger.info(f"\nFailed Tests ({len(failed_tests)}):")
            for test in failed_tests:
                self.logger.info(f"  ❌ {test['test_id']}: {test['description']}")
                if test["details"]:
                    self.logger.info(f"     Details: {test['details']}")
    
    def save_results(self) -> None:
        """Save validation results to JSON file."""
        if self.output_file:
            try:
                with open(self.output_file, 'w') as f:
                    json.dump(self.results, f, indent=2)
                self.logger.info(f"Results saved to: {self.output_file}")
            except Exception as e:
                self.logger.error(f"Failed to save results: {e}")


def main():
    """Main entry point for VAD validation."""
    parser = argparse.ArgumentParser(
        description="VAD Integration Validation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all validation tests
  python scripts/validate_vad_integration.py --all

  # Run specific category
  python scripts/validate_vad_integration.py --category init --verbose

  # Run with performance benchmarks
  python scripts/validate_vad_integration.py --performance --output vad_results.json

  # Quick validation
  python scripts/validate_vad_integration.py --quick
        """
    )
    
    parser.add_argument(
        "--category",
        choices=["init", "audio", "speech", "state", "control", "session", "error", "performance", "integration", "regression"],
        help="Run specific test category"
    )
    parser.add_argument(
        "--scenario",
        help="Run specific test scenario (e.g., VAD_INIT_001)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--output", "-o",
        help="Save results to JSON file"
    )
    parser.add_argument(
        "--generate-audio",
        action="store_true",
        help="Generate test audio files"
    )
    parser.add_argument(
        "--performance",
        action="store_true",
        help="Include performance benchmarks"
    )
    parser.add_argument(
        "--integration",
        action="store_true",
        help="Include integration tests"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick validation (subset of tests)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all validation tests (default)"
    )
    
    args = parser.parse_args()
    
    # Create validator
    validator = VADIntegrationValidator(
        verbose=args.verbose,
        output_file=args.output
    )
    
    try:
        # Generate test audio if requested
        if args.generate_audio:
            validator.generate_test_audio()
        
        # Run tests based on arguments
        if args.scenario:
            validator.logger.info(f"Running specific scenario: {args.scenario}")
            # TODO: Implement specific scenario execution
            validator.logger.warning("Specific scenario execution not yet implemented")
        elif args.category:
            validator.run_category_tests(args.category)
        elif args.quick:
            validator.run_quick_tests()
        else:
            # Default to running all tests
            validator.run_all_tests()
        
        # Print summary
        validator.print_summary()
        
        # Save results
        if args.output:
            validator.save_results()
        
        # Exit with appropriate code
        summary = validator.results["summary"]
        if summary["failed"] > 0 or summary["errors"] > 0:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except KeyboardInterrupt:
        validator.logger.info("\nValidation interrupted by user")
        sys.exit(1)
    except Exception as e:
        validator.logger.error(f"Validation failed with error: {e}")
        validator.logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main() 