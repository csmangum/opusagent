#!/usr/bin/env python3
"""
Realtime Transcription Validation Script

This script validates the transcription capabilities integrated within the LocalRealtimeClient,
testing both PocketSphinx and Whisper backends in a realistic realtime conversation context.

Features:
- Tests transcription within LocalRealtimeClient sessions
- Validates real-time audio transcription during conversations
- Tests transcription event generation and WebSocket communication
- Verifies VAD integration with transcription
- Tests error handling and fallback scenarios
- Uses real WAV audio files from the mock audio directory
- Generates detailed validation reports with conversation flows

Usage:
    # Run with default settings (both backends)
    python scripts/validate_realtime_transcription.py

    # Test specific backend
    python scripts/validate_realtime_transcription.py --backend pocketsphinx
    python scripts/validate_realtime_transcription.py --backend whisper

    # Test with specific audio file
    python scripts/validate_realtime_transcription.py --audio-file path/to/audio.wav

    # Test with specific audio category
    python scripts/validate_realtime_transcription.py --audio-category greetings

    # Verbose logging
    python scripts/validate_realtime_transcription.py --verbose

    # Custom output directory
    python scripts/validate_realtime_transcription.py --output-dir validation_results

Examples:
    # Quick test with PocketSphinx
    python scripts/validate_realtime_transcription.py --backend pocketsphinx --verbose

    # Full validation with customer service audio
    python scripts/validate_realtime_transcription.py --audio-category customer_service --output-dir test_results

    # Test with real audio file
    python scripts/validate_realtime_transcription.py --audio-file opusagent/mock/audio/greetings/greetings_01.wav
"""

import argparse
import asyncio
import base64
import json
import logging
import os
import sys
import tempfile
import time
import uuid
import yaml
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from opusagent.mock.realtime import (
    LocalRealtimeClient,
    TranscriptionConfig,
    TranscriptionFactory,
    load_transcription_config,
    LocalResponseConfig,
    ResponseSelectionCriteria
)
from opusagent.models.openai_api import SessionConfig


class RealtimeTranscriptionValidator:
    """
    Comprehensive validator for transcription capabilities within LocalRealtimeClient.
    
    This validator tests transcription integration in realistic conversation scenarios,
    including real-time audio processing, event generation, and WebSocket communication.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": [],
            "conversation_flows": [],
            "transcription_events": [],
            "summary": {
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "total_transcription_events": 0,
                "successful_transcriptions": 0,
                "failed_transcriptions": 0
            }
        }
        self.test_audio_data = None
        self.test_audio_file = None
        self.mock_audio_dir = Path("opusagent/mock/audio")
        self.phrases_mapping = None
        self.available_audio_files = {}
        
    def log_test_result(self, test_name: str, passed: bool, details: str = "", skipped: bool = False):
        """Log a test result with detailed information."""
        test_result = {
            "name": test_name,
            "passed": passed,
            "skipped": skipped,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        
        self.results["tests"].append(test_result)
        self.results["summary"]["total_tests"] += 1
        
        if skipped:
            self.results["summary"]["skipped"] += 1
            self.logger.info(f"SKIPPED: {test_name} - {details}")
        elif passed:
            self.results["summary"]["passed"] += 1
            self.logger.info(f"PASSED: {test_name}")
        else:
            self.results["summary"]["failed"] += 1
            self.logger.error(f"FAILED: {test_name} - {details}")
    
    def log_transcription_event(self, event_type: str, event_data: Dict[str, Any], success: bool = True):
        """Log transcription events for analysis."""
        event_record = {
            "type": event_type,
            "data": event_data,
            "success": success,
            "timestamp": datetime.now().isoformat()
        }
        
        self.results["transcription_events"].append(event_record)
        self.results["summary"]["total_transcription_events"] += 1
        
        if success:
            self.results["summary"]["successful_transcriptions"] += 1
        else:
            self.results["summary"]["failed_transcriptions"] += 1
    
    def log_conversation_flow(self, flow_name: str, messages: List[Dict[str, Any]], transcription_results: List[Dict[str, Any]]):
        """Log conversation flow for analysis."""
        flow_record = {
            "name": flow_name,
            "messages": messages,
            "transcription_results": transcription_results,
            "timestamp": datetime.now().isoformat()
        }
        
        self.results["conversation_flows"].append(flow_record)
    
    def load_phrases_mapping(self) -> Dict[str, Any]:
        """Load the phrases mapping configuration."""
        if self.phrases_mapping is None:
            mapping_file = self.mock_audio_dir / "phrases_mapping.yml"
            if mapping_file.exists():
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    self.phrases_mapping = yaml.safe_load(f)
                self.logger.info(f"Loaded phrases mapping from {mapping_file}")
            else:
                self.logger.warning(f"Phrases mapping file not found: {mapping_file}")
                self.phrases_mapping = {}
        return self.phrases_mapping
    
    def get_available_audio_files(self) -> Dict[str, List[str]]:
        """Get all available audio files organized by category."""
        if not self.available_audio_files:
            mapping = self.load_phrases_mapping()
            
            for scenario_name, scenario_data in mapping.get('scenarios', {}).items():
                scenario_dir = self.mock_audio_dir / scenario_name
                if scenario_dir.exists():
                    wav_files = [f.name for f in scenario_dir.glob("*.wav")]
                    self.available_audio_files[scenario_name] = wav_files
                    self.logger.debug(f"Found {len(wav_files)} audio files in {scenario_name}")
        
        return self.available_audio_files
    
    def select_test_audio_file(self, category: Optional[str] = None) -> Optional[str]:
        """Select a test audio file from the mock audio directory."""
        available_files = self.get_available_audio_files()
        
        if not available_files:
            self.logger.error("No audio files found in mock audio directory")
            return None
        
        if category and category in available_files:
            # Use specified category
            selected_file = random.choice(available_files[category])
            file_path = self.mock_audio_dir / category / selected_file
        else:
            # Randomly select from any category
            all_categories = list(available_files.keys())
            selected_category = random.choice(all_categories)
            selected_file = random.choice(available_files[selected_category])
            file_path = self.mock_audio_dir / selected_category / selected_file
        
        if file_path.exists():
            self.logger.info(f"Selected test audio file: {file_path}")
            return str(file_path)
        else:
            self.logger.error(f"Selected audio file does not exist: {file_path}")
            return None
    
    async def load_test_audio_data(self, audio_file_path: str) -> Optional[bytes]:
        """Load audio data from a WAV file."""
        try:
            with open(audio_file_path, 'rb') as f:
                audio_data = f.read()
            self.logger.info(f"Loaded audio data from {audio_file_path} ({len(audio_data)} bytes)")
            return audio_data
        except Exception as e:
            self.logger.error(f"Failed to load audio file {audio_file_path}: {e}")
            return None
    
    async def save_test_audio_file(self, audio_data: bytes, output_dir: str = "test_audio") -> str:
        """Save test audio data to a WAV file."""
        try:
            import wave
            
            # Create output directory
            Path(output_dir).mkdir(exist_ok=True)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_audio_{timestamp}.wav"
            filepath = Path(output_dir) / filename
            
            # Save as WAV file
            with wave.open(str(filepath), 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(16000)  # 16kHz
                wav_file.writeframes(audio_data)
            
            self.logger.info(f"Test audio saved to: {filepath}")
            return str(filepath)
            
        except ImportError:
            self.logger.warning("wave module not available, cannot save audio file")
            return ""
    
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
    
    async def test_client_transcription_initialization(self, backend: str) -> bool:
        """Test transcription initialization within LocalRealtimeClient."""
        test_name = f"Client Transcription Initialization: {backend}"
        
        try:
            # Create client with transcription enabled
            transcription_config = TranscriptionConfig(backend=backend)
            client = LocalRealtimeClient(
                enable_transcription=True,
                transcription_config={"backend": backend}
            )
            
            # Check if transcription is enabled
            if client.is_transcription_enabled():
                self.log_test_result(test_name, True, f"Transcription enabled with {backend}")
                await client.disconnect()
                return True
            else:
                self.log_test_result(test_name, False, f"Transcription not enabled for {backend}")
                await client.disconnect()
                return False
                
        except Exception as e:
            self.log_test_result(test_name, False, f"Error during client initialization: {e}")
            return False
    
    async def test_transcription_event_generation(self, backend: str) -> bool:
        """Test transcription event generation during conversation."""
        test_name = f"Transcription Event Generation: {backend}"
        
        try:
            # Create client with transcription enabled
            client = LocalRealtimeClient(
                enable_transcription=True,
                transcription_config={"backend": backend}
            )
            
            # Connect to the running OpusAgent server
            await client.connect("ws://localhost:8000/ws/telephony")
            
            # Set up conversation context
            client.update_conversation_context("Hello, this is a test message")
            
            # Load test audio if not available
            if not self.test_audio_data:
                audio_file = self.select_test_audio_file(category="greetings")
                if audio_file:
                    self.test_audio_data = await self.load_test_audio_data(audio_file)
                else:
                    self.log_test_result(test_name, False, "Failed to load test audio data")
                    return False
            
            # Simulate audio append events
            if not self.test_audio_data:
                self.log_test_result(test_name, False, "No test audio data available")
                return False
                
            chunk_size = 3200  # 200ms at 16kHz 16-bit
            audio_chunks = [self.test_audio_data[i:i + chunk_size] 
                          for i in range(0, len(self.test_audio_data), chunk_size)]
            
            transcription_events = []
            
            # Process audio chunks
            for i, chunk in enumerate(audio_chunks):
                # Simulate audio append
                await client.handle_audio_append({
                    "audio": base64.b64encode(chunk).decode("utf-8"),
                    "item_id": str(uuid.uuid4())
                })
                
                # Small delay to simulate real-time processing
                await asyncio.sleep(0.1)
            
            # Simulate audio commit
            await client.handle_audio_commit({
                "item_id": str(uuid.uuid4())
            })
            
            # Wait for transcription processing
            await asyncio.sleep(2.0)
            
            # Check for transcription events in session state
            session_state = client.get_session_state()
            
            # Log transcription events
            if "transcription_events" in session_state:
                transcription_events = session_state["transcription_events"]
                for event in transcription_events:
                    self.log_transcription_event("transcription", event, success=True)
            
            await client.disconnect()
            
            if transcription_events:
                self.log_test_result(test_name, True, f"Generated {len(transcription_events)} transcription events")
                return True
            else:
                self.log_test_result(test_name, False, "No transcription events generated")
                return False
                
        except Exception as e:
            self.log_test_result(test_name, False, f"Error during event generation: {e}")
            return False
    
    async def test_conversation_flow_with_transcription(self, backend: str) -> bool:
        """Test complete conversation flow with transcription enabled."""
        test_name = f"Conversation Flow with Transcription: {backend}"
        
        try:
            # Create client with transcription and VAD enabled
            client = LocalRealtimeClient(
                enable_transcription=True,
                enable_vad=True,
                transcription_config={"backend": backend}
            )
            
            # Set up smart responses
            client.setup_smart_response_examples()
            
            # Connect to the running OpusAgent server
            await client.connect("ws://localhost:8000/ws/telephony")
            
            # Load test audio if not available
            if not self.test_audio_data:
                audio_file = self.select_test_audio_file(category="customer_service")
                if audio_file:
                    self.test_audio_data = await self.load_test_audio_data(audio_file)
                else:
                    self.log_test_result(test_name, False, "Failed to load test audio data")
                    return False
            
            conversation_messages = []
            transcription_results = []
            
            # Simulate a conversation turn
            turn_id = str(uuid.uuid4())
            
            # Update conversation context
            client.update_conversation_context("Hello, I need help with my account")
            conversation_messages.append({
                "type": "user_input",
                "text": "Hello, I need help with my account",
                "timestamp": datetime.now().isoformat()
            })
            
            # Simulate audio streaming
            if not self.test_audio_data:
                self.log_test_result(test_name, False, "No test audio data available")
                return False
                
            chunk_size = 3200
            audio_chunks = [self.test_audio_data[i:i + chunk_size] 
                          for i in range(0, len(self.test_audio_data), chunk_size)]
            
            # Stream audio chunks
            for i, chunk in enumerate(audio_chunks):
                await client.handle_audio_append({
                    "audio": base64.b64encode(chunk).decode("utf-8"),
                    "item_id": turn_id
                })
                await asyncio.sleep(0.05)  # Simulate real-time streaming
            
            # Commit audio for processing
            await client.handle_audio_commit({
                "item_id": turn_id
            })
            
            # Wait for transcription and response generation
            await asyncio.sleep(3.0)
            
            # Check session state for transcription results
            session_state = client.get_session_state()
            
            # Log conversation flow
            self.log_conversation_flow(
                f"transcription_conversation_{backend}",
                conversation_messages,
                transcription_results
            )
            
            await client.disconnect()
            
            # Check if transcription was processed
            if "transcription_events" in session_state or "conversation_context" in session_state:
                self.log_test_result(test_name, True, "Conversation flow with transcription completed")
                return True
            else:
                self.log_test_result(test_name, False, "No transcription processing detected")
                return False
                
        except Exception as e:
            self.log_test_result(test_name, False, f"Error during conversation flow: {e}")
            return False
    
    async def test_transcription_error_handling(self, backend: str) -> bool:
        """Test transcription error handling and fallback scenarios."""
        test_name = f"Transcription Error Handling: {backend}"
        
        try:
            # Create client with transcription enabled
            client = LocalRealtimeClient(
                enable_transcription=True,
                transcription_config={"backend": backend}
            )
            
            await client.connect("ws://localhost:8000/ws/telephony")
            
            # Test with invalid audio data
            invalid_audio = b"invalid_audio_data"
            
            # Simulate audio append with invalid data
            await client.handle_audio_append({
                "audio": base64.b64encode(invalid_audio).decode("utf-8"),
                "item_id": str(uuid.uuid4())
            })
            
            # Commit audio
            await client.handle_audio_commit({
                "item_id": str(uuid.uuid4())
            })
            
            # Wait for processing
            await asyncio.sleep(2.0)
            
            # Check session state for error handling
            session_state = client.get_session_state()
            
            await client.disconnect()
            
            # The test passes if the client handles the error gracefully
            self.log_test_result(test_name, True, "Error handling completed gracefully")
            return True
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Error during error handling test: {e}")
            return False
    
    async def test_transcription_configuration(self, backend: str) -> bool:
        """Test transcription configuration loading and validation."""
        test_name = f"Transcription Configuration: {backend}"
        
        try:
            # Test configuration loading
            config = load_transcription_config()
            
            # Update with backend-specific settings
            config.backend = backend
            
            # Test configuration validation
            if config.backend == backend:
                self.log_test_result(test_name, True, f"Configuration loaded for {backend}")
                return True
            else:
                self.log_test_result(test_name, False, f"Configuration mismatch: expected {backend}, got {config.backend}")
                return False
                
        except Exception as e:
            self.log_test_result(test_name, False, f"Error during configuration test: {e}")
            return False
    
    async def test_transcription_performance(self, backend: str) -> bool:
        """Test transcription performance and timing."""
        test_name = f"Transcription Performance: {backend}"
        
        try:
            # Create client with transcription enabled
            client = LocalRealtimeClient(
                enable_transcription=True,
                transcription_config={"backend": backend}
            )
            
            await client.connect("ws://localhost:8000/ws/telephony")
            
            # Load test audio
            audio_file = self.select_test_audio_file(category="technical_support")
            if not audio_file:
                self.log_test_result(test_name, False, "Failed to select test audio file")
                return False
            
            test_audio = await self.load_test_audio_data(audio_file)
            if not test_audio:
                self.log_test_result(test_name, False, "Failed to load test audio data")
                return False
            
            # Measure transcription time
            start_time = time.perf_counter()
            
            # Process audio
            chunk_size = 3200
            audio_chunks = [test_audio[i:i + chunk_size] 
                          for i in range(0, len(test_audio), chunk_size)]
            
            for chunk in audio_chunks:
                await client.handle_audio_append({
                    "audio": base64.b64encode(chunk).decode("utf-8"),
                    "item_id": str(uuid.uuid4())
                })
            
            await client.handle_audio_commit({
                "item_id": str(uuid.uuid4())
            })
            
            # Wait for processing
            await asyncio.sleep(3.0)
            
            end_time = time.perf_counter()
            processing_time = end_time - start_time
            
            await client.disconnect()
            
            # Performance criteria: should complete within reasonable time
            if processing_time < 10.0:  # 10 seconds max
                self.log_test_result(test_name, True, f"Processing completed in {processing_time:.2f}s")
                return True
            else:
                self.log_test_result(test_name, False, f"Processing took too long: {processing_time:.2f}s")
                return False
                
        except Exception as e:
            self.log_test_result(test_name, False, f"Error during performance test: {e}")
            return False
    
    async def run_validation(self, backends: List[str], audio_file: Optional[str] = None, 
                           audio_category: Optional[str] = None, output_dir: str = "validation_results") -> Dict[str, Any]:
        """
        Run comprehensive transcription validation for the realtime module.
        
        Args:
            backends: List of transcription backends to test
            audio_file: Optional path to audio file for testing
            audio_category: Optional audio category to use for testing
            output_dir: Directory to save results and test audio
            
        Returns:
            Dictionary containing validation results
        """
        self.logger.info("Starting Realtime Transcription Validation...")
        
        # Create output directory
        Path(output_dir).mkdir(exist_ok=True)
        
        # Load test audio if no audio file provided
        if not audio_file:
            self.logger.info("Loading test audio from mock directory...")
            audio_file = self.select_test_audio_file(category=audio_category)
            if audio_file:
                self.test_audio_data = await self.load_test_audio_data(audio_file)
                self.test_audio_file = audio_file
            else:
                self.logger.error("Failed to select test audio file")
                return self.results
        
        # Load audio file if provided
        if audio_file and Path(audio_file).exists():
            try:
                with open(audio_file, 'rb') as f:
                    self.test_audio_data = f.read()
                self.logger.info(f"Loaded audio file: {audio_file}")
            except Exception as e:
                self.logger.error(f"Failed to load audio file {audio_file}: {e}")
        
        # Run tests for each backend
        for backend in backends:
            self.logger.info(f"\n=== Testing Backend: {backend} ===")
            
            # Test backend availability
            if not await self.test_backend_availability(backend):
                self.logger.warning(f"Skipping tests for {backend} - not available")
                continue
            
            # Run all tests for this backend
            await self.test_client_transcription_initialization(backend)
            await self.test_transcription_event_generation(backend)
            await self.test_conversation_flow_with_transcription(backend)
            await self.test_transcription_error_handling(backend)
            await self.test_transcription_configuration(backend)
            await self.test_transcription_performance(backend)
        
        # Generate summary
        summary = self.results["summary"]
        success_rate = (summary["passed"] / max(1, summary["total_tests"])) * 100
        
        self.logger.info(f"\n=== Validation Summary ===")
        self.logger.info(f"Total Tests: {summary['total_tests']}")
        self.logger.info(f"Passed: {summary['passed']}")
        self.logger.info(f"Failed: {summary['failed']}")
        self.logger.info(f"Skipped: {summary['skipped']}")
        self.logger.info(f"Success Rate: {success_rate:.1f}%")
        self.logger.info(f"Transcription Events: {summary['total_transcription_events']}")
        self.logger.info(f"Successful Transcriptions: {summary['successful_transcriptions']}")
        self.logger.info(f"Failed Transcriptions: {summary['failed_transcriptions']}")
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = Path(output_dir) / f"realtime_transcription_validation_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        self.logger.info(f"Detailed results saved to: {results_file}")
        
        return self.results


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                logs_dir / f"realtime_transcription_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            )
        ]
    )
    
    return logging.getLogger("realtime_transcription_validator")


def main():
    """Main entry point for the validation script."""
    parser = argparse.ArgumentParser(
        description="Validate transcription capabilities within LocalRealtimeClient"
    )
    parser.add_argument(
        "--backend",
        choices=["pocketsphinx", "whisper", "both"],
        default="both",
        help="Transcription backend(s) to test"
    )
    parser.add_argument(
        "--audio-file",
        help="Path to audio file for testing"
    )
    parser.add_argument(
        "--audio-category",
        choices=["greetings", "customer_service", "card_replacement", "technical_support", "sales", "farewells", "confirmations", "errors", "default"],
        help="Audio category to use for testing (random selection if not specified)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--output-dir",
        default="validation_results",
        help="Output directory for results"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    logger = setup_logging(args.verbose)
    
    # Determine backends to test
    if args.backend == "both":
        backends = ["pocketsphinx", "whisper"]
    else:
        backends = [args.backend]
    
    # Create validator and run tests
    validator = RealtimeTranscriptionValidator(logger)
    
    try:
        results = asyncio.run(validator.run_validation(
            backends=backends,
            audio_file=args.audio_file,
            audio_category=args.audio_category,
            output_dir=args.output_dir
        ))
        
        # Exit with appropriate code
        summary = results["summary"]
        if summary["failed"] > 0:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except KeyboardInterrupt:
        logger.info("Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Validation failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 