#!/usr/bin/env python3
"""
Unit tests for vad_factory module.
"""

import pytest
from unittest.mock import Mock, patch

from opusagent.vad.vad_factory import VADFactory
from opusagent.vad.silero_vad import SileroVAD


class TestVADFactory:
    """Test cases for VADFactory."""

    def test_create_vad_silero_backend(self):
        """Test creating Silero VAD backend."""
        config = {
            'backend': 'silero',
            'sample_rate': 16000,
            'threshold': 0.5,
            'device': 'cpu',
            'chunk_size': 512
        }
        
        vad = VADFactory.create_vad(config)
        
        assert isinstance(vad, SileroVAD)
        assert vad.sample_rate == 16000
        assert vad.threshold == 0.5
        assert vad.device == 'cpu'
        assert vad.chunk_size == 512

    def test_create_vad_silero_backend_default_config(self):
        """Test creating Silero VAD with minimal config."""
        config = {'backend': 'silero'}
        
        vad = VADFactory.create_vad(config)
        
        assert isinstance(vad, SileroVAD)
        # Should use SileroVAD defaults
        assert vad.sample_rate == 16000
        assert vad.threshold == 0.5
        assert vad.device == 'cpu'
        assert vad.chunk_size == 512

    def test_create_vad_silero_backend_custom_config(self):
        """Test creating Silero VAD with custom configuration."""
        config = {
            'backend': 'silero',
            'sample_rate': 8000,
            'threshold': 0.3,
            'device': 'cuda',
            'chunk_size': 256
        }
        
        vad = VADFactory.create_vad(config)
        
        assert isinstance(vad, SileroVAD)
        assert vad.sample_rate == 8000
        assert vad.threshold == 0.3
        assert vad.device == 'cuda'
        assert vad.chunk_size == 256

    def test_create_vad_unsupported_backend(self):
        """Test creating VAD with unsupported backend raises error."""
        config = {'backend': 'unsupported_backend'}
        
        with pytest.raises(ValueError) as exc_info:
            VADFactory.create_vad(config)
        
        assert "Unsupported VAD backend: unsupported_backend" in str(exc_info.value)

    def test_create_vad_no_backend_specified(self):
        """Test creating VAD with no backend specified (should default to silero)."""
        config = {
            'sample_rate': 16000,
            'threshold': 0.5
        }
        
        vad = VADFactory.create_vad(config)
        
        assert isinstance(vad, SileroVAD)
        assert vad.sample_rate == 16000
        assert vad.threshold == 0.5

    def test_create_vad_empty_config(self):
        """Test creating VAD with empty config."""
        config = {}
        
        vad = VADFactory.create_vad(config)
        
        assert isinstance(vad, SileroVAD)
        # Should use SileroVAD defaults
        assert vad.sample_rate == 16000
        assert vad.threshold == 0.5
        assert vad.device == 'cpu'
        assert vad.chunk_size == 512

    def test_create_vad_none_config(self):
        """Test creating VAD with None config."""
        config = None
        
        vad = VADFactory.create_vad(config)
        
        assert isinstance(vad, SileroVAD)
        # Should use SileroVAD defaults
        assert vad.sample_rate == 16000
        assert vad.threshold == 0.5
        assert vad.device == 'cpu'
        assert vad.chunk_size == 512

    def test_create_vad_case_insensitive_backend(self):
        """Test that backend names are case-sensitive."""
        config_upper = {'backend': 'SILERO'}
        config_lower = {'backend': 'silero'}
        
        # Should raise error for uppercase
        with pytest.raises(ValueError) as exc_info:
            VADFactory.create_vad(config_upper)
        assert "Unsupported VAD backend: SILERO" in str(exc_info.value)
        
        # Should work for lowercase
        vad = VADFactory.create_vad(config_lower)
        assert isinstance(vad, SileroVAD)

    def test_create_vad_whitespace_backend(self):
        """Test handling of backend names with whitespace."""
        config = {'backend': '  silero  '}
        
        with pytest.raises(ValueError) as exc_info:
            VADFactory.create_vad(config)
        
        assert "Unsupported VAD backend:   silero  " in str(exc_info.value)

    def test_create_vad_silero_initialization_called(self):
        """Test that SileroVAD.initialize is called with the config."""
        config = {
            'backend': 'silero',
            'sample_rate': 16000,
            'threshold': 0.5
        }
        
        with patch('opusagent.vad.vad_factory.SileroVAD') as mock_silero_class:
            mock_vad = Mock()
            mock_silero_class.return_value = mock_vad
            
            vad = VADFactory.create_vad(config)
            
            # Verify SileroVAD was instantiated
            mock_silero_class.assert_called_once()
            
            # Verify initialize was called with config
            mock_vad.initialize.assert_called_once_with(config)
            
            # Verify the returned VAD is the mock
            assert vad == mock_vad

    def test_create_vad_multiple_instances(self):
        """Test creating multiple VAD instances."""
        config1 = {'backend': 'silero', 'sample_rate': 16000}
        config2 = {'backend': 'silero', 'sample_rate': 8000}
        
        vad1 = VADFactory.create_vad(config1)
        vad2 = VADFactory.create_vad(config2)
        
        assert isinstance(vad1, SileroVAD)
        assert isinstance(vad2, SileroVAD)
        assert vad1 is not vad2  # Should be different instances
        
        assert vad1.sample_rate == 16000
        assert vad2.sample_rate == 8000

    def test_create_vad_backend_validation(self):
        """Test various backend name validations."""
        invalid_backends = [
            '',  # Empty string
            'silero_v2',  # Similar but different
            'Silero',  # Different case
            'SILERO',  # All caps
            ' silero',  # Leading space
            'silero ',  # Trailing space
            'silero\t',  # Tab character
            'silero\n',  # Newline character
        ]
        
        for backend in invalid_backends:
            config = {'backend': backend}
            with pytest.raises(ValueError) as exc_info:
                VADFactory.create_vad(config)
            assert f"Unsupported VAD backend: {backend}" in str(exc_info.value)

    def test_create_vad_config_passed_through(self):
        """Test that all config values are passed through to the VAD."""
        config = {
            'backend': 'silero',
            'sample_rate': 44100,
            'threshold': 0.123,
            'device': 'gpu:1',
            'chunk_size': 1024,
            'extra_param': 'extra_value'  # Extra parameter should be passed through
        }
        
        vad = VADFactory.create_vad(config)
        
        assert isinstance(vad, SileroVAD)
        # Verify all config values are set
        assert vad.sample_rate == 44100
        assert vad.threshold == 0.123
        assert vad.device == 'gpu:1'
        assert vad.chunk_size == 1024

    def test_create_vad_static_method(self):
        """Test that create_vad is a static method."""
        # Should be able to call without instantiating VADFactory
        config = {'backend': 'silero'}
        vad = VADFactory.create_vad(config)
        
        assert isinstance(vad, SileroVAD)

    def test_create_vad_error_propagation(self):
        """Test that errors from VAD initialization are propagated."""
        config = {'backend': 'silero'}
        
        with patch('opusagent.vad.vad_factory.SileroVAD') as mock_silero_class:
            mock_vad = Mock()
            mock_vad.initialize.side_effect = RuntimeError("Initialization failed")
            mock_silero_class.return_value = mock_vad
            
            with pytest.raises(RuntimeError) as exc_info:
                VADFactory.create_vad(config)
            
            assert "Initialization failed" in str(exc_info.value)

    def test_create_vad_factory_methods(self):
        """Test that VADFactory has the expected methods."""
        # Check that create_vad is a static method
        assert hasattr(VADFactory, 'create_vad')
        assert callable(VADFactory.create_vad)
        
        # Should not be able to instantiate VADFactory
        with pytest.raises(TypeError):
            VADFactory() 