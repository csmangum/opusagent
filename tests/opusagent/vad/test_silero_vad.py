#!/usr/bin/env python3
"""
Unit tests for silero_vad module.
"""

import pytest
import numpy as np
import torch
from unittest.mock import Mock, patch, MagicMock

from opusagent.vad.silero_vad import SileroVAD


class TestSileroVAD:
    """Test cases for SileroVAD implementation."""

    def test_silero_vad_initialization_defaults(self):
        """Test SileroVAD initialization with default values."""
        vad = SileroVAD()
        
        assert vad.model is None
        assert vad.sample_rate == 16000
        assert vad.threshold == 0.5
        assert vad.device == 'cpu'
        assert vad.chunk_size == 512

    def test_silero_vad_initialization_with_config(self):
        """Test SileroVAD initialization with custom config."""
        vad = SileroVAD()
        config = {
            'sample_rate': 8000,
            'threshold': 0.3,
            'device': 'cuda',
            'chunk_size': 256
        }
        
        with patch('silero_vad.load_silero_vad') as mock_load:
            mock_model = Mock()
            mock_load.return_value = mock_model
            
            vad.initialize(config)
            
            assert vad.sample_rate == 8000
            assert vad.threshold == 0.3
            assert vad.device == 'cuda'
            assert vad.chunk_size == 256
            assert vad.model == mock_model
            mock_load.assert_called_once()

    def test_silero_vad_initialization_chunk_size_validation(self):
        """Test that chunk size is validated and corrected for sample rate."""
        vad = SileroVAD()
        
        # Test 16kHz with wrong chunk size
        config = {'sample_rate': 16000, 'chunk_size': 1024}
        with patch('silero_vad.load_silero_vad') as mock_load:
            mock_load.return_value = Mock()
            vad.initialize(config)
            assert vad.chunk_size == 512  # Should be corrected
        
        # Test 8kHz with wrong chunk size
        vad2 = SileroVAD()
        config2 = {'sample_rate': 8000, 'chunk_size': 512}
        with patch('silero_vad.load_silero_vad') as mock_load:
            mock_load.return_value = Mock()
            vad2.initialize(config2)
            assert vad2.chunk_size == 256  # Should be corrected

    def test_silero_vad_initialization_missing_silero(self):
        """Test initialization when silero-vad is not installed."""
        vad = SileroVAD()
        config = {'sample_rate': 16000}
        
        with patch('silero_vad.load_silero_vad', side_effect=ImportError):
            with pytest.raises(RuntimeError) as exc_info:
                vad.initialize(config)
            
            assert "silero-vad not installed" in str(exc_info.value)

    def test_silero_vad_process_audio_not_initialized(self):
        """Test that processing audio without initialization raises error."""
        vad = SileroVAD()
        audio_data = np.random.randn(512).astype(np.float32)
        
        with pytest.raises(RuntimeError) as exc_info:
            vad.process_audio(audio_data)
        
        assert "Silero VAD model not initialized" in str(exc_info.value)

    def test_silero_vad_process_audio_correct_chunk_size(self):
        """Test processing audio with correct chunk size."""
        vad = SileroVAD()
        config = {'sample_rate': 16000, 'threshold': 0.5}
        
        with patch('silero_vad.load_silero_vad') as mock_load:
            mock_model = Mock()
            mock_model.return_value.item.return_value = 0.8
            mock_load.return_value = mock_model
            
            vad.initialize(config)
            
            # Test with correct chunk size
            audio_data = np.random.randn(512).astype(np.float32)
            result = vad.process_audio(audio_data)
            
            assert isinstance(result, dict)
            assert 'speech_prob' in result
            assert 'is_speech' in result
            assert result['speech_prob'] == 0.8
            assert result['is_speech'] is True  # 0.8 > 0.5 threshold
            
            # Verify model was called correctly
            mock_model.assert_called_once()
            call_args = mock_model.call_args
            assert isinstance(call_args[0][0], torch.Tensor)
            assert call_args[0][1] == 16000

    def test_silero_vad_process_audio_wrong_chunk_size(self):
        """Test processing audio with wrong chunk size (should be chunked)."""
        vad = SileroVAD()
        config = {'sample_rate': 16000, 'threshold': 0.5}
        
        with patch('silero_vad.load_silero_vad') as mock_load:
            mock_model = Mock()
            # Return different probabilities for different chunks
            mock_model.return_value.item.side_effect = [0.3, 0.9, 0.2]
            mock_load.return_value = mock_model
            
            vad.initialize(config)
            
            # Test with wrong chunk size (should be split into 512-sample chunks)
            audio_data = np.random.randn(1024).astype(np.float32)
            result = vad.process_audio(audio_data)
            
            assert isinstance(result, dict)
            assert 'speech_prob' in result
            assert 'is_speech' in result
            assert result['speech_prob'] == 0.9  # Should be max of [0.3, 0.9, 0.2]
            assert result['is_speech'] is True   # 0.9 > 0.5 threshold
            
            # Verify model was called for each chunk
            assert mock_model.call_count == 2  # 1024 samples / 512 = 2 chunks

    def test_silero_vad_process_audio_short_audio(self):
        """Test processing audio shorter than chunk size (should be padded)."""
        vad = SileroVAD()
        config = {'sample_rate': 16000, 'threshold': 0.5}
        
        with patch('silero_vad.load_silero_vad') as mock_load:
            mock_model = Mock()
            mock_model.return_value.item.return_value = 0.4
            mock_load.return_value = mock_model
            
            vad.initialize(config)
            
            # Test with short audio (should be padded to 512 samples)
            audio_data = np.random.randn(256).astype(np.float32)
            result = vad.process_audio(audio_data)
            
            assert isinstance(result, dict)
            assert 'speech_prob' in result
            assert 'is_speech' in result
            assert result['speech_prob'] == 0.4
            assert result['is_speech'] is False  # 0.4 < 0.5 threshold
            
            # Verify model was called with padded audio
            mock_model.assert_called_once()
            call_args = mock_model.call_args
            assert call_args[0][0].shape[0] == 512  # Should be padded to chunk size

    def test_silero_vad_process_audio_empty_audio(self):
        """Test processing empty audio data."""
        vad = SileroVAD()
        config = {'sample_rate': 16000, 'threshold': 0.5}
        
        with patch('silero_vad.load_silero_vad') as mock_load:
            mock_model = Mock()
            mock_model.return_value.item.return_value = 0.0
            mock_load.return_value = mock_model
            
            vad.initialize(config)
            
            # Test with empty audio
            audio_data = np.array([], dtype=np.float32)
            result = vad.process_audio(audio_data)
            
            assert isinstance(result, dict)
            assert 'speech_prob' in result
            assert 'is_speech' in result
            assert result['speech_prob'] == 0.0
            assert result['is_speech'] is False  # 0.0 < 0.5 threshold

    def test_silero_vad_process_audio_threshold_behavior(self):
        """Test VAD behavior with different thresholds."""
        vad = SileroVAD()
        
        with patch('silero_vad.load_silero_vad') as mock_load:
            mock_model = Mock()
            mock_model.return_value.item.return_value = 0.6
            mock_load.return_value = mock_model
            
            # Test with high threshold
            config_high = {'sample_rate': 16000, 'threshold': 0.8}
            vad.initialize(config_high)
            audio_data = np.random.randn(512).astype(np.float32)
            result_high = vad.process_audio(audio_data)
            assert result_high['is_speech'] is False  # 0.6 < 0.8
            
            # Test with low threshold
            config_low = {'sample_rate': 16000, 'threshold': 0.3}
            vad.initialize(config_low)
            result_low = vad.process_audio(audio_data)
            assert result_low['is_speech'] is True   # 0.6 > 0.3

    def test_silero_vad_reset(self):
        """Test VAD reset functionality."""
        vad = SileroVAD()
        config = {'sample_rate': 16000, 'threshold': 0.5}
        
        with patch('silero_vad.load_silero_vad') as mock_load:
            mock_load.return_value = Mock()
            vad.initialize(config)
            
            # Reset should not affect the model
            vad.reset()
            assert vad.model is not None
            assert vad.sample_rate == 16000
            assert vad.threshold == 0.5

    def test_silero_vad_cleanup(self):
        """Test VAD cleanup functionality."""
        vad = SileroVAD()
        config = {'sample_rate': 16000, 'threshold': 0.5}
        
        with patch('silero_vad.load_silero_vad') as mock_load:
            mock_load.return_value = Mock()
            vad.initialize(config)
            
            assert vad.model is not None
            
            vad.cleanup()
            assert vad.model is None

    def test_silero_vad_8khz_sample_rate(self):
        """Test VAD with 8kHz sample rate."""
        vad = SileroVAD()
        config = {'sample_rate': 8000, 'threshold': 0.5}
        
        with patch('silero_vad.load_silero_vad') as mock_load:
            mock_model = Mock()
            mock_model.return_value.item.return_value = 0.7
            mock_load.return_value = mock_model
            
            vad.initialize(config)
            
            assert vad.sample_rate == 8000
            assert vad.chunk_size == 256  # Should be adjusted for 8kHz
            
            audio_data = np.random.randn(256).astype(np.float32)
            result = vad.process_audio(audio_data)
            
            assert result['speech_prob'] == 0.7
            assert result['is_speech'] is True
            
            # Verify model was called with correct sample rate
            mock_model.assert_called_once()
            call_args = mock_model.call_args
            assert call_args[0][1] == 8000

    def test_silero_vad_tensor_conversion(self):
        """Test that audio data is properly converted to torch tensor."""
        vad = SileroVAD()
        config = {'sample_rate': 16000, 'threshold': 0.5}
        
        with patch('silero_vad.load_silero_vad') as mock_load:
            mock_model = Mock()
            mock_model.return_value.item.return_value = 0.5
            mock_load.return_value = mock_model
            
            vad.initialize(config)
            
            # Create test audio data that matches chunk size
            audio_data = np.random.randn(512).astype(np.float32)
            
            result = vad.process_audio(audio_data)
            
            # Verify tensor conversion
            mock_model.assert_called_once()
            call_args = mock_model.call_args
            tensor = call_args[0][0]
            
            assert isinstance(tensor, torch.Tensor)
            assert tensor.dtype == torch.float32
            assert tensor.shape[0] == 512
            np.testing.assert_array_almost_equal(tensor.numpy(), audio_data)

    def test_silero_vad_multiple_process_calls(self):
        """Test multiple consecutive process_audio calls."""
        vad = SileroVAD()
        config = {'sample_rate': 16000, 'threshold': 0.5}
        
        with patch('silero_vad.load_silero_vad') as mock_load:
            mock_model = Mock()
            # Return different probabilities for each call
            mock_model.return_value.item.side_effect = [0.3, 0.8, 0.2, 0.9]
            mock_load.return_value = mock_model
            
            vad.initialize(config)
            
            audio_data = np.random.randn(512).astype(np.float32)
            
            # Multiple calls
            results = []
            for i in range(4):
                result = vad.process_audio(audio_data)
                results.append(result)
            
            # Verify results
            expected_probs = [0.3, 0.8, 0.2, 0.9]
            expected_speech = [False, True, False, True]
            
            for i, (result, exp_prob, exp_speech) in enumerate(zip(results, expected_probs, expected_speech)):
                assert result['speech_prob'] == exp_prob
                assert result['is_speech'] == exp_speech
            
            # Verify model was called 4 times
            assert mock_model.call_count == 4 