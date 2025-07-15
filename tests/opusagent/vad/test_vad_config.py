#!/usr/bin/env python3
"""
Unit tests for vad_config module.
"""

import pytest
import os
from unittest.mock import patch

from opusagent.vad.vad_config import load_vad_config


class TestVADConfig:
    """Test cases for VAD configuration loading."""

    def test_load_vad_config_defaults(self):
        """Test loading VAD config with default values when no env vars are set."""
        with patch.dict(os.environ, {}, clear=True):
            config = load_vad_config()
            
            assert isinstance(config, dict)
            assert config['backend'] == 'silero'
            assert config['sample_rate'] == 16000
            assert config['threshold'] == 0.5
            assert config['device'] == 'cpu'
            assert config['chunk_size'] == 512

    def test_load_vad_config_from_environment(self):
        """Test loading VAD config from environment variables."""
        env_vars = {
            'VAD_BACKEND': 'custom_backend',
            'VAD_SAMPLE_RATE': '8000',
            'VAD_CONFIDENCE_THRESHOLD': '0.3',
            'VAD_DEVICE': 'cuda',
            'VAD_CHUNK_SIZE': '256'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = load_vad_config()
            
            assert config['backend'] == 'custom_backend'
            assert config['sample_rate'] == 8000
            assert config['threshold'] == 0.3
            assert config['device'] == 'cuda'
            assert config['chunk_size'] == 256

    def test_load_vad_config_partial_environment(self):
        """Test loading VAD config with some environment variables set."""
        env_vars = {
            'VAD_BACKEND': 'silero',
            'VAD_CONFIDENCE_THRESHOLD': '0.7'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = load_vad_config()
            
            # Set values should be used
            assert config['backend'] == 'silero'
            assert config['threshold'] == 0.7
            
            # Unset values should use defaults
            assert config['sample_rate'] == 16000
            assert config['device'] == 'cpu'
            assert config['chunk_size'] == 512

    def test_load_vad_config_numeric_conversion(self):
        """Test that numeric environment variables are properly converted."""
        env_vars = {
            'VAD_SAMPLE_RATE': '22050',
            'VAD_CONFIDENCE_THRESHOLD': '0.123',
            'VAD_CHUNK_SIZE': '1024'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = load_vad_config()
            
            assert isinstance(config['sample_rate'], int)
            assert config['sample_rate'] == 22050
            
            assert isinstance(config['threshold'], float)
            assert config['threshold'] == 0.123
            
            assert isinstance(config['chunk_size'], int)
            assert config['chunk_size'] == 1024

    def test_load_vad_config_invalid_numeric_values(self):
        """Test handling of invalid numeric environment variables."""
        env_vars = {
            'VAD_SAMPLE_RATE': 'invalid',
            'VAD_CONFIDENCE_THRESHOLD': 'not_a_number',
            'VAD_CHUNK_SIZE': 'abc'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValueError):
                load_vad_config()

    def test_load_vad_config_edge_case_values(self):
        """Test edge case values for VAD configuration."""
        env_vars = {
            'VAD_SAMPLE_RATE': '0',
            'VAD_CONFIDENCE_THRESHOLD': '0.0',
            'VAD_CHUNK_SIZE': '1'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = load_vad_config()
            
            assert config['sample_rate'] == 0
            assert config['threshold'] == 0.0
            assert config['chunk_size'] == 1

    def test_load_vad_config_negative_values(self):
        """Test handling of negative values."""
        env_vars = {
            'VAD_SAMPLE_RATE': '-16000',
            'VAD_CONFIDENCE_THRESHOLD': '-0.5',
            'VAD_CHUNK_SIZE': '-512'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = load_vad_config()
            
            assert config['sample_rate'] == -16000
            assert config['threshold'] == -0.5
            assert config['chunk_size'] == -512

    def test_load_vad_config_float_threshold(self):
        """Test that threshold can handle various float values."""
        test_cases = [
            '0.0', '0.1', '0.5', '0.9', '1.0',
            '0.123456789', '0.999999999'
        ]
        
        for threshold_str in test_cases:
            env_vars = {'VAD_CONFIDENCE_THRESHOLD': threshold_str}
            
            with patch.dict(os.environ, env_vars, clear=True):
                config = load_vad_config()
                expected_threshold = float(threshold_str)
                assert config['threshold'] == expected_threshold

    def test_load_vad_config_large_values(self):
        """Test handling of large numeric values."""
        env_vars = {
            'VAD_SAMPLE_RATE': '48000',
            'VAD_CHUNK_SIZE': '8192'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = load_vad_config()
            
            assert config['sample_rate'] == 48000
            assert config['chunk_size'] == 8192

    def test_load_vad_config_string_values(self):
        """Test that string values are handled correctly."""
        env_vars = {
            'VAD_BACKEND': 'my_custom_vad',
            'VAD_DEVICE': 'gpu:0'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = load_vad_config()
            
            assert config['backend'] == 'my_custom_vad'
            assert config['device'] == 'gpu:0'

    def test_load_vad_config_empty_strings(self):
        """Test handling of empty string environment variables."""
        env_vars = {
            'VAD_BACKEND': '',
            'VAD_DEVICE': ''
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = load_vad_config()
            
            # Empty strings should be used as-is for string values
            assert config['backend'] == ''
            assert config['device'] == ''
            
            # Numeric values should still use defaults
            assert config['sample_rate'] == 16000
            assert config['threshold'] == 0.5
            assert config['chunk_size'] == 512

    def test_load_vad_config_whitespace_handling(self):
        """Test handling of whitespace in environment variables."""
        env_vars = {
            'VAD_BACKEND': '  silero  ',
            'VAD_DEVICE': '  cpu  ',
            'VAD_SAMPLE_RATE': '  16000  ',
            'VAD_CONFIDENCE_THRESHOLD': '  0.5  ',
            'VAD_CHUNK_SIZE': '  512  '
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = load_vad_config()
            
            # String values should preserve whitespace
            assert config['backend'] == '  silero  '
            assert config['device'] == '  cpu  '
            
            # Numeric values should be stripped and converted
            assert config['sample_rate'] == 16000
            assert config['threshold'] == 0.5
            assert config['chunk_size'] == 512

    def test_load_vad_config_return_type(self):
        """Test that load_vad_config returns a dictionary with expected keys."""
        config = load_vad_config()
        
        assert isinstance(config, dict)
        expected_keys = {
            'backend', 'sample_rate', 'threshold', 'silence_threshold',
            'min_speech_duration_ms', 'speech_start_threshold', 'speech_stop_threshold',
            'device', 'chunk_size', 'confidence_history_size', 'force_stop_timeout_ms'
        }
        assert set(config.keys()) == expected_keys

    def test_load_vad_config_immutability(self):
        """Test that modifying the returned config doesn't affect subsequent calls."""
        config1 = load_vad_config()
        config1['backend'] = 'modified'
        
        config2 = load_vad_config()
        assert config2['backend'] == 'silero'  # Should still be default

    def test_load_vad_config_environment_persistence(self):
        """Test that environment variables persist across multiple calls."""
        env_vars = {
            'VAD_BACKEND': 'test_backend',
            'VAD_SAMPLE_RATE': '44100'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config1 = load_vad_config()
            config2 = load_vad_config()
            
            assert config1 == config2
            assert config1['backend'] == 'test_backend'
            assert config1['sample_rate'] == 44100

    def test_load_vad_config_new_parameters_defaults(self):
        """Test that new VAD parameters have correct default values."""
        with patch.dict(os.environ, {}, clear=True):
            config = load_vad_config()
            
            assert config['silence_threshold'] == 0.6
            assert config['min_speech_duration_ms'] == 500
            assert config['speech_start_threshold'] == 2
            assert config['speech_stop_threshold'] == 3
            assert config['confidence_history_size'] == 5
            assert config['force_stop_timeout_ms'] == 2000

    def test_load_vad_config_new_parameters_from_environment(self):
        """Test loading new VAD parameters from environment variables."""
        env_vars = {
            'VAD_SILENCE_THRESHOLD': '0.3',
            'VAD_MIN_SPEECH_DURATION_MS': '1000',
            'VAD_SPEECH_START_THRESHOLD': '5',
            'VAD_SPEECH_STOP_THRESHOLD': '7',
            'VAD_CONFIDENCE_HISTORY_SIZE': '10',
            'VAD_FORCE_STOP_TIMEOUT_MS': '5000'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = load_vad_config()
            
            assert config['silence_threshold'] == 0.3
            assert config['min_speech_duration_ms'] == 1000
            assert config['speech_start_threshold'] == 5
            assert config['speech_stop_threshold'] == 7
            assert config['confidence_history_size'] == 10
            assert config['force_stop_timeout_ms'] == 5000

    def test_load_vad_config_new_parameters_numeric_conversion(self):
        """Test that new numeric parameters are properly converted."""
        env_vars = {
            'VAD_SILENCE_THRESHOLD': '0.789',
            'VAD_MIN_SPEECH_DURATION_MS': '750',
            'VAD_SPEECH_START_THRESHOLD': '1',
            'VAD_SPEECH_STOP_THRESHOLD': '4',
            'VAD_CONFIDENCE_HISTORY_SIZE': '8',
            'VAD_FORCE_STOP_TIMEOUT_MS': '3000'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = load_vad_config()
            
            assert isinstance(config['silence_threshold'], float)
            assert config['silence_threshold'] == 0.789
            
            assert isinstance(config['min_speech_duration_ms'], int)
            assert config['min_speech_duration_ms'] == 750
            
            assert isinstance(config['speech_start_threshold'], int)
            assert config['speech_start_threshold'] == 1
            
            assert isinstance(config['speech_stop_threshold'], int)
            assert config['speech_stop_threshold'] == 4
            
            assert isinstance(config['confidence_history_size'], int)
            assert config['confidence_history_size'] == 8
            
            assert isinstance(config['force_stop_timeout_ms'], int)
            assert config['force_stop_timeout_ms'] == 3000

    def test_load_vad_config_new_parameters_invalid_values(self):
        """Test handling of invalid numeric values for new parameters."""
        env_vars = {
            'VAD_SILENCE_THRESHOLD': 'invalid',
            'VAD_MIN_SPEECH_DURATION_MS': 'not_a_number',
            'VAD_SPEECH_START_THRESHOLD': 'abc',
            'VAD_SPEECH_STOP_THRESHOLD': 'xyz',
            'VAD_CONFIDENCE_HISTORY_SIZE': 'def',
            'VAD_FORCE_STOP_TIMEOUT_MS': 'ghi'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValueError):
                load_vad_config()

    def test_load_vad_config_new_parameters_edge_cases(self):
        """Test edge case values for new VAD parameters."""
        env_vars = {
            'VAD_SILENCE_THRESHOLD': '0.0',
            'VAD_MIN_SPEECH_DURATION_MS': '0',
            'VAD_SPEECH_START_THRESHOLD': '1',
            'VAD_SPEECH_STOP_THRESHOLD': '1',
            'VAD_CONFIDENCE_HISTORY_SIZE': '1',
            'VAD_FORCE_STOP_TIMEOUT_MS': '0'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = load_vad_config()
            
            assert config['silence_threshold'] == 0.0
            assert config['min_speech_duration_ms'] == 0
            assert config['speech_start_threshold'] == 1
            assert config['speech_stop_threshold'] == 1
            assert config['confidence_history_size'] == 1
            assert config['force_stop_timeout_ms'] == 0 