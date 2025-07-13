#!/usr/bin/env python3
"""
Simple Transcription Test Script

This script provides a simple way to test the transcription capabilities
of the LocalRealtimeClient without complex WebSocket server setup.

Features:
- Tests transcription backends directly
- Validates audio processing
- Tests transcription configuration
- Simple command-line interface

Usage:
    python scripts/simple_transcription_test.py [options]

Options:
    --backend pocketsphinx|whisper    Test specific backend
    --audio-file path/to/audio.wav    Use specific audio file
    --generate-test-audio             Generate test audio
    --verbose                         Enable verbose logging
"""

import asyncio
import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from opusagent.mock.realtime import (
    LocalRealtimeClient,
    TranscriptionConfig,
    TranscriptionFactory,
    load_transcription_config
)
from opusagent.models.openai_api import SessionConfig


class SimpleTranscriptionTester:
    """Simple tester for transcription functionality."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": [],
            "summary": {
                "total_tests": 0,
                "passed": 0,
                "failed": 0
            }
        }
    
    def log_test_result(self, test_name: str, passed: bool, details: str = ""):
        """Log a test result."""
        test_result = {
            "name": test_name,
            "passed": passed,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        
        self.results["tests"].append(test_result)
        self.results["summary"]["total_tests"] += 1
        
        if passed:
            self.results["summary"]["passed"] += 1
            self.logger.info(f"PASSED: {test_name} - {details}")
        else:
            self.results["summary"]["failed"] += 1
            self.logger.error(f"FAILED: {test_name} - {details}")
    
    async def test_backend_availability(self, backend: str) -> bool:
        """Test if a transcription backend is available."""
        test_name = f"Backend Availability: {backend}"
        
        try:
            available_backends = TranscriptionFactory.get_available_backends()
            if backend in available_backends:
                self.log_test_result(test_name, True, f"Backend {backend} is available")
                return True
            else:
                self.log_test_result(test_name, False, f"Backend {backend} is not available")
                return False
        except Exception as e:
            self.log_test_result(test_name, False, f"Error checking backend availability: {e}")
            return False
    
    async def test_transcriber_initialization(self, backend: str) -> bool:
        """Test transcriber initialization."""
        test_name = f"Transcriber Initialization: {backend}"
        
        try:
            config = TranscriptionConfig(backend=backend)
            transcriber = TranscriptionFactory.create_transcriber(config)
            
            # Test initialization
            initialized = await transcriber.initialize()
            if initialized:
                await transcriber.cleanup()
                self.log_test_result(test_name, True, f"Successfully initialized {backend} transcriber")
                return True
            else:
                self.log_test_result(test_name, False, f"Failed to initialize {backend} transcriber")
                return False
                
        except Exception as e:
            self.log_test_result(test_name, False, f"Error during initialization: {e}")
            return False
    
    async def test_audio_conversion(self, backend: str) -> bool:
        """Test audio format conversion."""
        test_name = f"Audio Conversion: {backend}"
        
        try:
            config = TranscriptionConfig(backend=backend)
            transcriber = TranscriptionFactory.create_transcriber(config)
            
            # Generate test audio data (1 second of 16kHz 16-bit PCM)
            test_audio = bytes([0] * 32000)  # 1 second of silence
            
            # Test conversion
            audio_array = transcriber._convert_audio_for_processing(test_audio)
            
            if audio_array is not None and len(audio_array) > 0:
                self.log_test_result(test_name, True, f"Converted {len(audio_array)} samples")
                return True
            else:
                self.log_test_result(test_name, False, "Audio conversion returned empty result")
                return False
                
        except Exception as e:
            self.log_test_result(test_name, False, f"Error during audio conversion: {e}")
            return False
    
    async def test_chunk_transcription(self, backend: str) -> bool:
        """Test chunk-based transcription."""
        test_name = f"Chunk Transcription: {backend}"
        
        try:
            config = TranscriptionConfig(backend=backend)
            transcriber = TranscriptionFactory.create_transcriber(config)
            
            # Initialize transcriber
            if not await transcriber.initialize():
                self.log_test_result(test_name, False, "Failed to initialize transcriber")
                return False
            
            # Generate test audio chunks
            chunk_size = 3200  # 200ms at 16kHz 16-bit
            test_chunks = [bytes([0] * chunk_size) for _ in range(5)]
            
            # Start session
            transcriber.start_session()
            
            # Process chunks
            results = []
            for i, chunk in enumerate(test_chunks):
                result = await transcriber.transcribe_chunk(chunk)
                results.append(result)
                self.logger.debug(f"Chunk {i+1}: {result.text} (confidence: {result.confidence:.3f})")
            
            # Finalize
            final_result = await transcriber.finalize()
            transcriber.end_session()
            await transcriber.cleanup()
            
            # Check results
            if final_result.error:
                self.log_test_result(test_name, False, f"Transcription error: {final_result.error}")
                return False
            
            self.log_test_result(test_name, True, f"Final text: '{final_result.text}' (confidence: {final_result.confidence:.3f})")
            return True
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Error during chunk transcription: {e}")
            return False
    
    async def test_client_integration(self, backend: str) -> bool:
        """Test transcription integration with LocalRealtimeClient."""
        test_name = f"Client Integration: {backend}"
        
        try:
            # Create client with transcription enabled
            transcription_config = {
                "backend": backend,
                "language": "en",
                "chunk_duration": 1.0
            }
            
            session_config = SessionConfig(
                model="gpt-4o-realtime-preview-2025-06-03",
                modalities=["text", "audio"],
                voice="alloy",
                input_audio_transcription={"model": "local"}
            )
            
            client = LocalRealtimeClient(
                session_config=session_config,
                enable_transcription=True,
                transcription_config=transcription_config
            )
            
            # Test transcription state
            transcription_state = client.get_transcription_state()
            
            if transcription_state["enabled"] and transcription_state["initialized"]:
                self.log_test_result(test_name, True, f"Transcription enabled with {backend}")
                return True
            else:
                self.log_test_result(test_name, False, f"Transcription not properly initialized: {transcription_state}")
                return False
                
        except Exception as e:
            self.log_test_result(test_name, False, f"Error during client integration: {e}")
            return False
    
    async def test_audio_file_transcription(self, backend: str, audio_file: Optional[str] = None) -> bool:
        """Test transcription with actual audio file."""
        test_name = f"Audio File Transcription: {backend}"
        
        if not audio_file:
            self.log_test_result(test_name, True, "No audio file provided, skipping")
            return True
        
        if not os.path.exists(audio_file):
            self.log_test_result(test_name, False, f"Audio file not found: {audio_file}")
            return False
        
        try:
            config = TranscriptionConfig(backend=backend)
            transcriber = TranscriptionFactory.create_transcriber(config)
            
            if not await transcriber.initialize():
                self.log_test_result(test_name, False, "Failed to initialize transcriber")
                return False
            
            # Read audio file
            with open(audio_file, 'rb') as f:
                audio_data = f.read()
            
            # Process in chunks
            chunk_size = 3200
            chunks = [audio_data[i:i + chunk_size] for i in range(0, len(audio_data), chunk_size)]
            
            transcriber.start_session()
            
            for chunk in chunks:
                result = await transcriber.transcribe_chunk(chunk)
                if result.error:
                    self.log_test_result(test_name, False, f"Chunk transcription error: {result.error}")
                    return False
            
            final_result = await transcriber.finalize()
            transcriber.end_session()
            await transcriber.cleanup()
            
            if final_result.error:
                self.log_test_result(test_name, False, f"Final transcription error: {final_result.error}")
                return False
            
            self.log_test_result(test_name, True, f"Transcribed: '{final_result.text}' (confidence: {final_result.confidence:.3f})")
            return True
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Error during audio file transcription: {e}")
            return False
    
    async def test_configuration_loading(self) -> bool:
        """Test configuration loading from environment."""
        test_name = "Configuration Loading"
        
        try:
            config = load_transcription_config()
            
            # Verify config has required fields
            required_fields = ["backend", "language", "sample_rate"]
            for field in required_fields:
                if not hasattr(config, field):
                    self.log_test_result(test_name, False, f"Missing required field: {field}")
                    return False
            
            self.log_test_result(test_name, True, f"Loaded config: {config.backend}, {config.language}, {config.sample_rate}Hz")
            return True
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Error loading configuration: {e}")
            return False
    
    async def generate_test_audio(self, output_dir: str) -> str:
        """Generate test audio file for validation."""
        try:
            import numpy as np
            import wave
            
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate test audio (1 second of 440Hz sine wave)
            sample_rate = 16000
            duration = 1.0
            frequency = 440.0
            
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            audio_data = np.sin(2 * np.pi * frequency * t)
            
            # Convert to 16-bit PCM
            audio_int16 = (audio_data * 32767).astype(np.int16)
            
            # Save as WAV file
            output_file = os.path.join(output_dir, "test_audio_440hz.wav")
            with wave.open(output_file, 'w') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_int16.tobytes())
            
            self.logger.info(f"Generated test audio: {output_file}")
            return output_file
            
        except Exception as e:
            self.logger.error(f"Error generating test audio: {e}")
            return ""
    
    async def run_tests(self, backend: str, audio_file: Optional[str] = None, 
                       generate_test_audio: bool = False) -> Dict[str, Any]:
        """Run comprehensive transcription tests."""
        self.logger.info(f"Starting transcription tests for {backend} backend...")
        
        # Generate test audio if requested
        if generate_test_audio:
            test_audio_file = await self.generate_test_audio("test_audio")
            if test_audio_file and not audio_file:
                audio_file = test_audio_file
        
        # Test configuration loading
        await self.test_configuration_loading()
        
        # Test backend availability
        if not await self.test_backend_availability(backend):
            return self.results
        
        # Test transcriber initialization
        if not await self.test_transcriber_initialization(backend):
            return self.results
        
        # Test audio conversion
        await self.test_audio_conversion(backend)
        
        # Test chunk transcription
        await self.test_chunk_transcription(backend)
        
        # Test client integration
        await self.test_client_integration(backend)
        
        # Test audio file transcription
        await self.test_audio_file_transcription(backend, audio_file)
        
        # Save results
        results_file = f"transcription_test_results_{backend}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        self.logger.info(f"\n=== Test Results ===")
        self.logger.info(f"Results saved to: {results_file}")
        self.logger.info(f"Summary: {self.results['summary']['passed']}/{self.results['summary']['total_tests']} tests passed")
        
        return self.results


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


async def main():
    """Main entry point for the transcription test."""
    parser = argparse.ArgumentParser(description="Simple transcription test for LocalRealtimeClient")
    parser.add_argument("--backend", choices=["pocketsphinx", "whisper"], 
                       default="pocketsphinx", help="Test specific backend")
    parser.add_argument("--audio-file", help="Path to audio file for testing")
    parser.add_argument("--generate-test-audio", action="store_true", 
                       help="Generate test audio files")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging(args.verbose)
    
    # Create tester and run tests
    tester = SimpleTranscriptionTester(logger)
    
    try:
        results = await tester.run_tests(
            backend=args.backend,
            audio_file=args.audio_file,
            generate_test_audio=args.generate_test_audio
        )
        
        # Print final summary
        logger.info("\n=== Final Summary ===")
        for test in results["tests"]:
            status = "PASSED" if test["passed"] else "FAILED"
            logger.info(f"{status}: {test['name']}")
        
        success_rate = results["summary"]["passed"] / results["summary"]["total_tests"] if results["summary"]["total_tests"] > 0 else 0
        logger.info(f"\nSuccess Rate: {success_rate:.1%}")
        
        # Exit with appropriate code
        if results["summary"]["failed"] > 0:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 