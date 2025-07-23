#!/usr/bin/env python3
"""
Integration tests for VAD modules.
"""

import pytest
import numpy as np
import struct
from unittest.mock import patch, Mock

from opusagent.vad.audio_processor import to_float32_mono
from opusagent.vad.base_vad import BaseVAD
from opusagent.vad.silero_vad import SileroVAD
from opusagent.vad.vad_config import load_vad_config
from opusagent.vad.vad_factory import VADFactory


class MockVAD(BaseVAD):
    """Mock VAD implementation for integration testing."""
    
    def __init__(self):
        self.initialized = False
        self.config = None
        self.process_count = 0
    
    def initialize(self, config):
        self.initialized = True
        self.config = config
    
    def process_audio(self, audio_data: np.ndarray) -> dict:
        if not self.initialized:
            raise RuntimeError("VAD not initialized")
        
        self.process_count += 1
        
        # Simulate VAD processing based on audio energy
        energy = np.mean(np.abs(audio_data))
        speech_prob = min(energy * 2.0, 1.0)  # Simple energy-based VAD
        threshold = self.config.get('threshold', 0.5) if self.config else 0.5
        is_speech = speech_prob > threshold
        
        return {
            'speech_prob': speech_prob,
            'is_speech': is_speech,
            'timestamp': self.process_count
        }
    
    def reset(self):
        self.process_count = 0
    
    def cleanup(self):
        self.initialized = False


class TestVADIntegration:
    """Integration tests for VAD modules working together."""

    def test_full_vad_pipeline_silero(self):
        """Test complete VAD pipeline with Silero backend."""
        # 1. Load configuration
        config = load_vad_config()
        config['backend'] = 'silero'
        config['threshold'] = 0.5
        
        # 2. Create VAD instance
        with patch('silero_vad.load_silero_vad') as mock_load:
            mock_model = Mock()
            mock_model.return_value.item.return_value = 0.7
            mock_load.return_value = mock_model
            
            vad = VADFactory.create_vad(config)
            
            # 3. Create test audio data
            audio_bytes = struct.pack('<512h', *[1000] * 512)  # 512 samples of constant audio
            
            # 4. Convert audio format
            audio_float = to_float32_mono(audio_bytes, sample_width=2, channels=1)
            
            # 5. Process with VAD
            result = vad.process_audio(audio_float)
            
            # 6. Verify results
            assert isinstance(result, dict)
            assert 'speech_prob' in result
            assert 'is_speech' in result
            assert result['speech_prob'] == 0.7
            assert result['is_speech'] is True

    def test_full_vad_pipeline_mock(self):
        """Test complete VAD pipeline with mock backend."""
        # 1. Load configuration
        config = load_vad_config()
        config['backend'] = 'silero'  # Will be overridden by factory
        config['threshold'] = 0.3
        
        # 2. Create VAD instance with mock
        with patch('opusagent.vad.vad_factory.SileroVAD', MockVAD):
            vad = VADFactory.create_vad(config)
            
            # 3. Create test audio data with varying energy
            # High energy audio (should be detected as speech)
            high_energy_audio = np.random.randn(512).astype(np.float32) * 0.8
            high_energy_bytes = struct.pack('<512f', *high_energy_audio)
            
            # Low energy audio (should not be detected as speech)
            low_energy_audio = np.random.randn(512).astype(np.float32) * 0.1
            low_energy_bytes = struct.pack('<512f', *low_energy_audio)
            
            # 4. Convert and process high energy audio
            high_energy_float = to_float32_mono(high_energy_bytes, sample_width=4, channels=1)
            high_result = vad.process_audio(high_energy_float)
            
            # 5. Convert and process low energy audio
            low_energy_float = to_float32_mono(low_energy_bytes, sample_width=4, channels=1)
            low_result = vad.process_audio(low_energy_float)
            
            # 6. Verify results
            print(f"High energy result: {high_result}")
            print(f"Low energy result: {low_result}")
            assert high_result['speech_prob'] > low_result['speech_prob']
            assert high_result['is_speech'] is True
            assert not low_result['is_speech']

    def test_vad_config_integration(self):
        """Test that VAD configuration integrates properly with all components."""
        # Test different configuration scenarios
        test_configs = [
            {'backend': 'silero', 'sample_rate': 16000, 'threshold': 0.5},
            {'backend': 'silero', 'sample_rate': 8000, 'threshold': 0.3},
            {'backend': 'silero', 'sample_rate': 16000, 'threshold': 0.7},
        ]
        
        for config in test_configs:
            with patch('silero_vad.load_silero_vad') as mock_load:
                mock_model = Mock()
                mock_model.return_value.item.return_value = 0.6
                mock_load.return_value = mock_model
                
                # Create VAD with config
                vad = VADFactory.create_vad(config)
                
                # Verify config was applied
                assert vad.sample_rate == config['sample_rate']
                assert vad.threshold == config['threshold']
                
                # Test processing
                audio_data = np.random.randn(512).astype(np.float32)
                result = vad.process_audio(audio_data)
                
                assert isinstance(result, dict)
                assert 'speech_prob' in result
                assert 'is_speech' in result

    def test_audio_processor_integration(self):
        """Test audio processor integration with VAD pipeline."""
        # Create test audio data in different formats
        test_cases = [
            # (audio_data, sample_width, channels, expected_samples)
            (struct.pack('<256h', *[1000] * 256), 2, 1, 256),  # 16-bit mono
            (struct.pack('<128f', *[0.5] * 128), 4, 1, 128),   # 32-bit float mono
        ]
        
        for audio_bytes, sample_width, channels, expected_samples in test_cases:
            # Convert audio
            audio_float = to_float32_mono(audio_bytes, sample_width, channels)
            
            # Verify conversion
            assert isinstance(audio_float, np.ndarray)
            assert audio_float.dtype == np.float32
            assert len(audio_float) == expected_samples
            
            # Test with VAD (using mock to avoid silero dependency)
            with patch('opusagent.vad.vad_factory.SileroVAD', MockVAD):
                config = {'backend': 'silero', 'threshold': 0.5}
                vad = VADFactory.create_vad(config)
                
                result = vad.process_audio(audio_float)
                
                assert isinstance(result, dict)
                assert 'speech_prob' in result
                assert 'is_speech' in result

    def test_vad_lifecycle_integration(self):
        """Test complete VAD lifecycle with all components."""
        # 1. Load configuration
        config = load_vad_config()
        config['backend'] = 'silero'
        config['threshold'] = 0.5
        
        # 2. Create VAD instance
        with patch('silero_vad.load_silero_vad') as mock_load:
            mock_model = Mock()
            mock_model.return_value.item.return_value = 0.6
            mock_load.return_value = mock_model
            
            vad = VADFactory.create_vad(config)
            
            # 3. Create test audio
            audio_bytes = struct.pack('<512h', *[1000] * 512)
            audio_float = to_float32_mono(audio_bytes, sample_width=2, channels=1)
            
            # 4. Process multiple audio chunks
            results = []
            for i in range(3):
                result = vad.process_audio(audio_float)
                results.append(result)
            
            # 5. Verify processing
            assert len(results) == 3
            for result in results:
                assert result['speech_prob'] == 0.6
                assert result['is_speech'] is True
            
            # 6. Test reset
            vad.reset()
            
            # 7. Process again after reset
            result = vad.process_audio(audio_float)
            assert result['speech_prob'] == 0.6
            assert result['is_speech'] is True
            
            # 8. Test cleanup
            vad.cleanup()
            assert vad.model is None

    def test_error_handling_integration(self):
        """Test error handling across the VAD pipeline."""
        # Test unsupported audio format (sample_width=5 is not supported)
        with pytest.raises(NotImplementedError):
            to_float32_mono(b'invalid', sample_width=5, channels=1)
        
        # Test VAD without initialization
        vad = SileroVAD()
        audio_data = np.random.randn(512).astype(np.float32)
        
        with pytest.raises(RuntimeError) as exc_info:
            vad.process_audio(audio_data)
        assert "Silero VAD model not initialized" in str(exc_info.value)
        
        # Test unsupported backend
        config = {'backend': 'unsupported'}
        with pytest.raises(ValueError) as exc_info:
            VADFactory.create_vad(config)
        assert "Unsupported VAD backend" in str(exc_info.value)

    def test_performance_integration(self):
        """Test performance characteristics of the VAD pipeline."""
        # Create large audio data
        large_audio_bytes = struct.pack('<8192h', *[1000] * 8192)  # 8k samples
        
        # Test conversion performance
        import time
        start_time = time.time()
        audio_float = to_float32_mono(large_audio_bytes, sample_width=2, channels=1)
        conversion_time = time.time() - start_time
        
        # Conversion should be fast (< 1ms for 8k samples)
        assert conversion_time < 0.001
        
        # Test VAD processing performance (with mock)
        with patch('opusagent.vad.vad_factory.SileroVAD', MockVAD):
            config = {'backend': 'silero', 'threshold': 0.5}
            vad = VADFactory.create_vad(config)
            
            start_time = time.time()
            result = vad.process_audio(audio_float)
            processing_time = time.time() - start_time
            
            # Processing should be fast (< 10ms for 8k samples with mock)
            assert processing_time < 0.01
            
            assert isinstance(result, dict)
            assert 'speech_prob' in result

    def test_memory_integration(self):
        """Test memory usage characteristics of the VAD pipeline."""
        import gc
        import sys
        
        # Test memory usage for large audio processing
        large_audio_bytes = struct.pack('<16384h', *[1000] * 16384)  # 16k samples
        
        # Get initial memory usage
        gc.collect()
        initial_memory = sys.getsizeof(large_audio_bytes)
        
        # Process audio
        audio_float = to_float32_mono(large_audio_bytes, sample_width=2, channels=1)
        
        # Memory usage should be reasonable
        float_memory = sys.getsizeof(audio_float)
        assert float_memory > 0
        assert float_memory < initial_memory * 10  # Shouldn't be excessive
        
        # Test with VAD (mock)
        with patch('opusagent.vad.vad_factory.SileroVAD', MockVAD):
            config = {'backend': 'silero', 'threshold': 0.5}
            vad = VADFactory.create_vad(config)
            
            result = vad.process_audio(audio_float)
            
            # Result should be small
            result_memory = sys.getsizeof(result)
            assert result_memory < 1000  # Small dictionary

    def test_concurrent_access_integration(self):
        """Test concurrent access to VAD components."""
        import threading
        import queue
        
        # Test concurrent audio processing
        def process_audio_thread(vad, audio_data, results_queue, thread_id):
            try:
                result = vad.process_audio(audio_data)
                results_queue.put((thread_id, result))
            except Exception as e:
                results_queue.put((thread_id, e))
        
        # Create test audio
        audio_bytes = struct.pack('<512h', *[1000] * 512)
        audio_float = to_float32_mono(audio_bytes, sample_width=2, channels=1)
        
        # Test with mock VAD
        with patch('opusagent.vad.vad_factory.SileroVAD', MockVAD):
            config = {'backend': 'silero', 'threshold': 0.5}
            vad = VADFactory.create_vad(config)
            
            # Create multiple threads
            results_queue = queue.Queue()
            threads = []
            
            for i in range(3):
                thread = threading.Thread(
                    target=process_audio_thread,
                    args=(vad, audio_float, results_queue, i)
                )
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
            
            # Collect results
            results = []
            while not results_queue.empty():
                results.append(results_queue.get())
            
            # Verify all threads completed successfully
            assert len(results) == 3
            for thread_id, result in results:
                assert isinstance(result, dict)
                assert 'speech_prob' in result
                assert 'is_speech' in result 