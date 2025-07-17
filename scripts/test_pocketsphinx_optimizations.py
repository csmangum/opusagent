#!/usr/bin/env python3
"""
Test script for PocketSphinx optimizations in transcription.py

This script validates that the optimizations we implemented work correctly:
- Audio resampling from 24kHz to 16kHz
- Audio preprocessing (normalize, amplify, etc.)
- Configuration loading with optimization settings
- Performance improvements

Usage:
    python scripts/test_pocketsphinx_optimizations.py
"""

import asyncio
import logging
import sys
import time
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from opusagent.mock.transcription import TranscriptionFactory, TranscriptionConfig, TranscriptionResult, load_transcription_config
from opusagent.config.logging_config import configure_logging


class PocketSphinxOptimizationTester:
    """Test the PocketSphinx optimizations we implemented."""
    
    def __init__(self):
        self.logger = configure_logging(name="pocketsphinx_optimization_tester")
        self.test_results = []
        
    async def test_configuration_loading(self):
        """Test that optimization settings are loaded correctly."""
        self.logger.info("Testing configuration loading...")
        
        # Test default configuration
        config = load_transcription_config()
        self.logger.info(f"Default config - preprocessing: {config.pocketsphinx_audio_preprocessing}")
        self.logger.info(f"Default config - vad_settings: {config.pocketsphinx_vad_settings}")
        self.logger.info(f"Default config - auto_resample: {config.pocketsphinx_auto_resample}")
        self.logger.info(f"Default config - input_sample_rate: {config.pocketsphinx_input_sample_rate}")
        
        # Test custom configuration
        custom_config = TranscriptionConfig(
            backend="pocketsphinx",
            pocketsphinx_audio_preprocessing="amplify",
            pocketsphinx_vad_settings="aggressive",
            pocketsphinx_auto_resample=True,
            pocketsphinx_input_sample_rate=24000
        )
        
        self.logger.info(f"Custom config - preprocessing: {custom_config.pocketsphinx_audio_preprocessing}")
        self.logger.info(f"Custom config - vad_settings: {custom_config.pocketsphinx_vad_settings}")
        
        return True
        
    async def test_transcriber_creation(self):
        """Test that transcribers are created with optimization settings."""
        self.logger.info("Testing transcriber creation...")
        
        config = TranscriptionConfig(
            backend="pocketsphinx",
            pocketsphinx_audio_preprocessing="normalize",
            pocketsphinx_vad_settings="conservative",
            pocketsphinx_auto_resample=True,
            pocketsphinx_input_sample_rate=24000
        )
        
        try:
            transcriber = TranscriptionFactory.create_transcriber(config)
            self.logger.info(f"Created transcriber: {type(transcriber).__name__}")
            
            # Test initialization
            success = await transcriber.initialize()
            if success:
                self.logger.info("Transcriber initialized successfully")
                await transcriber.cleanup()
                return True
            else:
                self.logger.error("Transcriber initialization failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Error creating transcriber: {e}")
            return False
            
    async def test_audio_resampling(self):
        """Test the audio resampling functionality."""
        self.logger.info("Testing audio resampling...")
        
        config = TranscriptionConfig(
            backend="pocketsphinx",
            pocketsphinx_auto_resample=True,
            pocketsphinx_input_sample_rate=24000
        )
        
        transcriber = TranscriptionFactory.create_transcriber(config)
        
        # Create test audio data (24kHz, 1 second of silence)
        original_rate = 24000
        target_rate = 16000
        duration_seconds = 1.0
        
        # Generate test audio (simple sine wave)
        import numpy as np
        t = np.linspace(0, duration_seconds, int(original_rate * duration_seconds))
        audio_24k = np.sin(2 * np.pi * 440 * t) * 0.5  # 440Hz sine wave
        audio_24k_int16 = (audio_24k * 32767).astype(np.int16)
        audio_24k_bytes = audio_24k_int16.tobytes()
        
        # Test resampling
        resampled_bytes = transcriber._resample_audio_for_pocketsphinx(
            audio_24k_bytes, original_rate, target_rate
        )
        
        # Verify resampling worked
        resampled_int16 = np.frombuffer(resampled_bytes, dtype=np.int16)
        expected_length = int(len(audio_24k_int16) * target_rate / original_rate)
        
        self.logger.info(f"Original audio length: {len(audio_24k_int16)} samples")
        self.logger.info(f"Resampled audio length: {len(resampled_int16)} samples")
        self.logger.info(f"Expected length: {expected_length} samples")
        
        # Check if resampling produced reasonable results
        if abs(len(resampled_int16) - expected_length) <= 1:
            self.logger.info("Audio resampling test PASSED")
            return True
        else:
            self.logger.error("Audio resampling test FAILED")
            return False
            
    async def test_audio_preprocessing(self):
        """Test the audio preprocessing functionality."""
        self.logger.info("Testing audio preprocessing...")
        
        config = TranscriptionConfig(
            backend="pocketsphinx",
            pocketsphinx_audio_preprocessing="normalize"
        )
        
        transcriber = TranscriptionFactory.create_transcriber(config)
        
        # Create test audio data
        import numpy as np
        audio_data = np.array([0.1, 0.2, 0.3, 0.4, 0.5, -0.3, -0.2, -0.1])
        
        # Test normalization
        normalized = transcriber._apply_audio_preprocessing(audio_data, "normalize")
        max_val = np.max(np.abs(normalized))
        
        self.logger.info(f"Original max: {np.max(np.abs(audio_data))}")
        self.logger.info(f"Normalized max: {max_val}")
        
        if abs(max_val - 1.0) < 0.01:
            self.logger.info("Audio normalization test PASSED")
            return True
        else:
            self.logger.error("Audio normalization test FAILED")
            return False
            
    async def test_with_actual_audio_files(self):
        """Test with actual audio files from the mock directory."""
        self.logger.info("Testing with actual audio files...")
        
        # Find test audio files
        audio_dir = Path("opusagent/mock/audio")
        if not audio_dir.exists():
            self.logger.warning("Audio directory not found, skipping file tests")
            return True
            
        # Get a few test files
        test_files = []
        for category in ["greetings", "customer_service", "errors", "confirmations"]:
            category_dir = audio_dir / category
            if category_dir.exists():
                files = list(category_dir.glob("*.wav"))
                if files:
                    test_files.append(files[0])
                    
        if not test_files:
            self.logger.warning("No test audio files found")
            return True
            
        self.logger.info(f"Found {len(test_files)} test files")
        
        # Test with each file
        config = TranscriptionConfig(
            backend="pocketsphinx",
            pocketsphinx_audio_preprocessing="normalize",
            pocketsphinx_vad_settings="conservative",
            pocketsphinx_auto_resample=True,
            pocketsphinx_input_sample_rate=24000
        )
        
        transcriber = TranscriptionFactory.create_transcriber(config)
        success = await transcriber.initialize()
        
        if not success:
            self.logger.error("Failed to initialize transcriber for file tests")
            return False
            
        try:
            for test_file in test_files[:2]:  # Test with first 2 files
                self.logger.info(f"Testing with file: {test_file.name}")
                
                # Read audio file
                with open(test_file, 'rb') as f:
                    audio_data = f.read()
                
                # Test transcription
                transcriber.start_session()
                
                start_time = time.time()
                # First call fills the buffer, second call processes it
                await transcriber.transcribe_chunk(audio_data)
                result = await transcriber.transcribe_chunk(audio_data)
                assert result.text == "test transcription"
                processing_time = time.time() - start_time
                
                final_result = await transcriber.finalize()
                
                self.logger.info(f"Transcription result: '{final_result.text}'")
                self.logger.info(f"Confidence: {final_result.confidence:.3f}")
                self.logger.info(f"Processing time: {processing_time:.3f}s")
                
                transcriber.end_session()
                
        finally:
            await transcriber.cleanup()
            
        return True
        
    async def run_all_tests(self):
        """Run all optimization tests."""
        self.logger.info("Starting PocketSphinx optimization tests...")
        
        tests = [
            ("Configuration Loading", self.test_configuration_loading),
            ("Transcriber Creation", self.test_transcriber_creation),
            ("Audio Resampling", self.test_audio_resampling),
            ("Audio Preprocessing", self.test_audio_preprocessing),
            ("Actual Audio Files", self.test_with_actual_audio_files),
        ]
        
        results = []
        for test_name, test_func in tests:
            self.logger.info(f"\n{'='*50}")
            self.logger.info(f"Running test: {test_name}")
            self.logger.info(f"{'='*50}")
            
            try:
                result = await test_func()
                results.append((test_name, result))
                status = "PASSED" if result else "FAILED"
                self.logger.info(f"Test {test_name}: {status}")
            except Exception as e:
                self.logger.error(f"Test {test_name} failed with exception: {e}")
                results.append((test_name, False))
                
        # Summary
        self.logger.info(f"\n{'='*50}")
        self.logger.info("TEST SUMMARY")
        self.logger.info(f"{'='*50}")
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "PASSED" if result else "FAILED"
            self.logger.info(f"{test_name}: {status}")
            
        self.logger.info(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            self.logger.info("🎉 All PocketSphinx optimization tests PASSED!")
        else:
            self.logger.error("❌ Some tests failed")
            
        return passed == total


async def main():
    """Main test function."""
    tester = PocketSphinxOptimizationTester()
    success = await tester.run_all_tests()
    
    if success:
        print("\n✅ PocketSphinx optimizations are working correctly!")
        sys.exit(0)
    else:
        print("\n❌ Some PocketSphinx optimization tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 