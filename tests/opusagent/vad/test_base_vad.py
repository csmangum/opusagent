#!/usr/bin/env python3
"""
Unit tests for base_vad module.
"""

import pytest
import numpy as np
from abc import ABC
from unittest.mock import Mock

from opusagent.vad.base_vad import BaseVAD


class MockVAD(BaseVAD):
    """Mock implementation of BaseVAD for testing."""
    
    def __init__(self):
        self.initialized = False
        self.reset_called = False
        self.cleanup_called = False
        self.process_count = 0
    
    def initialize(self, config):
        """Initialize the VAD system with the given configuration."""
        self.initialized = True
        self.config = config
    
    def process_audio(self, audio_data: np.ndarray) -> dict:
        """Process audio data and return VAD result."""
        if not self.initialized:
            raise RuntimeError("VAD not initialized")
        
        self.process_count += 1
        
        # Mock VAD result
        return {
            'speech_prob': 0.7,
            'is_speech': True,
            'timestamp': self.process_count
        }
    
    def reset(self):
        """Reset VAD state."""
        self.reset_called = True
        self.process_count = 0
    
    def cleanup(self):
        """Cleanup VAD resources."""
        self.cleanup_called = True
        self.initialized = False


class TestBaseVAD:
    """Test cases for BaseVAD abstract base class."""

    def test_base_vad_is_abstract(self):
        """Test that BaseVAD is an abstract base class."""
        assert issubclass(BaseVAD, ABC)
        
        # Should not be able to instantiate directly
        with pytest.raises(TypeError):
            BaseVAD()

    def test_mock_vad_implements_interface(self):
        """Test that MockVAD properly implements the BaseVAD interface."""
        vad = MockVAD()
        
        # Test that all required methods exist
        assert hasattr(vad, 'initialize')
        assert hasattr(vad, 'process_audio')
        assert hasattr(vad, 'reset')
        assert hasattr(vad, 'cleanup')
        
        # Test that methods are callable
        assert callable(vad.initialize)
        assert callable(vad.process_audio)
        assert callable(vad.reset)
        assert callable(vad.cleanup)

    def test_mock_vad_initialize(self):
        """Test VAD initialization."""
        vad = MockVAD()
        config = {'sample_rate': 16000, 'threshold': 0.5}
        
        vad.initialize(config)
        
        assert vad.initialized
        assert vad.config == config

    def test_mock_vad_process_audio_initialized(self):
        """Test audio processing when VAD is initialized."""
        vad = MockVAD()
        config = {'sample_rate': 16000, 'threshold': 0.5}
        vad.initialize(config)
        
        # Create test audio data
        audio_data = np.random.randn(512).astype(np.float32)
        
        result = vad.process_audio(audio_data)
        
        assert isinstance(result, dict)
        assert 'speech_prob' in result
        assert 'is_speech' in result
        assert 'timestamp' in result
        assert result['speech_prob'] == 0.7
        assert result['is_speech'] is True
        assert result['timestamp'] == 1
        assert vad.process_count == 1

    def test_mock_vad_process_audio_not_initialized(self):
        """Test that processing audio without initialization raises error."""
        vad = MockVAD()
        audio_data = np.random.randn(512).astype(np.float32)
        
        with pytest.raises(RuntimeError) as exc_info:
            vad.process_audio(audio_data)
        
        assert "VAD not initialized" in str(exc_info.value)

    def test_mock_vad_reset(self):
        """Test VAD reset functionality."""
        vad = MockVAD()
        config = {'sample_rate': 16000, 'threshold': 0.5}
        vad.initialize(config)
        
        # Process some audio to increment counter
        audio_data = np.random.randn(512).astype(np.float32)
        vad.process_audio(audio_data)
        vad.process_audio(audio_data)
        
        assert vad.process_count == 2
        
        # Reset
        vad.reset()
        
        assert vad.reset_called
        assert vad.process_count == 0

    def test_mock_vad_cleanup(self):
        """Test VAD cleanup functionality."""
        vad = MockVAD()
        config = {'sample_rate': 16000, 'threshold': 0.5}
        vad.initialize(config)
        
        assert vad.initialized
        
        # Cleanup
        vad.cleanup()
        
        assert vad.cleanup_called
        assert not vad.initialized

    def test_mock_vad_lifecycle(self):
        """Test complete VAD lifecycle."""
        vad = MockVAD()
        
        # 1. Initialize
        config = {'sample_rate': 16000, 'threshold': 0.5}
        vad.initialize(config)
        assert vad.initialized
        
        # 2. Process audio multiple times
        audio_data = np.random.randn(512).astype(np.float32)
        for i in range(3):
            result = vad.process_audio(audio_data)
            assert result['timestamp'] == i + 1
        
        assert vad.process_count == 3
        
        # 3. Reset
        vad.reset()
        assert vad.reset_called
        assert vad.process_count == 0
        
        # 4. Process again after reset
        result = vad.process_audio(audio_data)
        assert result['timestamp'] == 1
        assert vad.process_count == 1
        
        # 5. Cleanup
        vad.cleanup()
        assert vad.cleanup_called
        assert not vad.initialized

    def test_mock_vad_process_audio_different_inputs(self):
        """Test VAD processing with different audio input types."""
        vad = MockVAD()
        config = {'sample_rate': 16000, 'threshold': 0.5}
        vad.initialize(config)
        
        # Test with different audio data sizes
        test_cases = [
            np.random.randn(256).astype(np.float32),   # 256 samples
            np.random.randn(512).astype(np.float32),   # 512 samples
            np.random.randn(1024).astype(np.float32),  # 1024 samples
            np.zeros(512, dtype=np.float32),           # Silence
            np.ones(512, dtype=np.float32) * 0.5,      # Constant value
        ]
        
        for i, audio_data in enumerate(test_cases):
            result = vad.process_audio(audio_data)
            
            assert isinstance(result, dict)
            assert 'speech_prob' in result
            assert 'is_speech' in result
            assert 'timestamp' in result
            assert result['timestamp'] == i + 1

    def test_mock_vad_config_persistence(self):
        """Test that configuration persists through operations."""
        vad = MockVAD()
        config = {'sample_rate': 16000, 'threshold': 0.5, 'device': 'cpu'}
        vad.initialize(config)
        
        # Process some audio
        audio_data = np.random.randn(512).astype(np.float32)
        vad.process_audio(audio_data)
        
        # Verify config is still there
        assert vad.config == config
        
        # Reset should not affect config
        vad.reset()
        assert vad.config == config
        
        # Cleanup should not affect config
        vad.cleanup()
        assert vad.config == config

    def test_mock_vad_multiple_initializations(self):
        """Test multiple initializations of the same VAD instance."""
        vad = MockVAD()
        
        # First initialization
        config1 = {'sample_rate': 16000, 'threshold': 0.5}
        vad.initialize(config1)
        assert vad.initialized
        assert vad.config == config1
        
        # Second initialization with different config
        config2 = {'sample_rate': 8000, 'threshold': 0.3}
        vad.initialize(config2)
        assert vad.initialized
        assert vad.config == config2

    def test_mock_vad_process_audio_return_type(self):
        """Test that process_audio returns the expected data types."""
        vad = MockVAD()
        config = {'sample_rate': 16000, 'threshold': 0.5}
        vad.initialize(config)
        
        audio_data = np.random.randn(512).astype(np.float32)
        result = vad.process_audio(audio_data)
        
        # Check data types
        assert isinstance(result['speech_prob'], (int, float))
        assert isinstance(result['is_speech'], bool)
        assert isinstance(result['timestamp'], int)
        
        # Check value ranges
        assert 0.0 <= result['speech_prob'] <= 1.0
        assert result['timestamp'] > 0 