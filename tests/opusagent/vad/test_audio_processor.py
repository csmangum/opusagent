#!/usr/bin/env python3
"""
Unit tests for audio_processor module.
"""

import pytest
import numpy as np
import struct
from unittest.mock import patch

from opusagent.vad.audio_processor import to_float32_mono


class TestAudioProcessor:
    """Test cases for audio_processor module."""

    def test_to_float32_mono_int16_mono(self):
        """Test conversion of int16 mono audio data."""
        # Create test int16 mono audio data (sine wave)
        sample_rate = 16000
        duration = 0.1  # 100ms
        frequency = 440  # A4 note
        
        samples = []
        for i in range(int(sample_rate * duration)):
            t = i / sample_rate
            sample = int(32767 * 0.5 * np.sin(2 * np.pi * frequency * t))
            samples.append(sample)
        
        # Pack as int16 bytes
        audio_data = struct.pack(f'<{len(samples)}h', *samples)
        
        # Convert to float32
        result = to_float32_mono(audio_data, sample_width=2, channels=1)
        
        # Verify result
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.float32
        assert len(result) == len(samples)
        assert np.all(result >= -1.0) and np.all(result <= 1.0)
        
        # Verify conversion accuracy (should be close to original)
        expected = np.array(samples, dtype=np.float32) / 32768.0
        np.testing.assert_array_almost_equal(result, expected, decimal=5)

    def test_to_float32_mono_int16_stereo_raises_error(self):
        """Test that stereo audio raises NotImplementedError."""
        # Create test stereo audio data
        audio_data = struct.pack('<4h', 1000, -1000, 2000, -2000)  # 2 stereo samples
        
        with pytest.raises(NotImplementedError) as exc_info:
            to_float32_mono(audio_data, sample_width=2, channels=2)
        
        assert "Audio conversion for this format is not implemented" in str(exc_info.value)

    def test_to_float32_mono_int24_raises_error(self):
        """Test that 24-bit audio raises NotImplementedError."""
        audio_data = b'\x00\x00\x00\x00\x00\x00'  # 2 samples of 24-bit audio
        
        with pytest.raises(NotImplementedError) as exc_info:
            to_float32_mono(audio_data, sample_width=3, channels=1)
        
        assert "Audio conversion for this format is not implemented" in str(exc_info.value)

    def test_to_float32_mono_int32_raises_error(self):
        """Test that 32-bit audio raises NotImplementedError."""
        audio_data = struct.pack('<2i', 1000000, -1000000)  # 2 samples of 32-bit audio
        
        with pytest.raises(NotImplementedError) as exc_info:
            to_float32_mono(audio_data, sample_width=4, channels=1)
        
        assert "Audio conversion for this format is not implemented" in str(exc_info.value)

    def test_to_float32_mono_empty_data(self):
        """Test handling of empty audio data."""
        audio_data = b''
        
        result = to_float32_mono(audio_data, sample_width=2, channels=1)
        
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.float32
        assert len(result) == 0

    def test_to_float32_mono_silence(self):
        """Test conversion of silence (all zeros)."""
        # Create silent audio data
        audio_data = struct.pack('<4h', 0, 0, 0, 0)  # 4 samples of silence
        
        result = to_float32_mono(audio_data, sample_width=2, channels=1)
        
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.float32
        assert len(result) == 4
        assert np.all(result == 0.0)

    def test_to_float32_mono_max_values(self):
        """Test conversion of maximum/minimum int16 values."""
        # Test maximum positive and negative values
        audio_data = struct.pack('<2h', 32767, -32768)  # Max positive and negative
        
        result = to_float32_mono(audio_data, sample_width=2, channels=1)
        
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.float32
        assert len(result) == 2
        # Use more appropriate tolerance for float32 precision
        assert result[0] == pytest.approx(32767.0 / 32768.0, abs=1e-7)  # 32767 / 32768
        assert result[1] == pytest.approx(-32768.0 / 32768.0, abs=1e-7)  # -32768 / 32768

    def test_to_float32_mono_odd_length(self):
        """Test handling of odd-length audio data."""
        # Create audio data with odd number of bytes (incomplete sample)
        audio_data = struct.pack('<3h', 1000, -1000, 500)  # 3 samples = 6 bytes
        
        result = to_float32_mono(audio_data, sample_width=2, channels=1)
        
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.float32
        assert len(result) == 3

    def test_to_float32_mono_invalid_sample_width(self):
        """Test handling of invalid sample width."""
        audio_data = b'\x00\x00\x00\x00'
        
        with pytest.raises(NotImplementedError) as exc_info:
            to_float32_mono(audio_data, sample_width=1, channels=1)
        
        assert "Audio conversion for this format is not implemented" in str(exc_info.value)

    def test_to_float32_mono_invalid_channels(self):
        """Test handling of invalid channel count."""
        audio_data = b'\x00\x00\x00\x00'
        
        with pytest.raises(NotImplementedError) as exc_info:
            to_float32_mono(audio_data, sample_width=2, channels=0)
        
        assert "Audio conversion for this format is not implemented" in str(exc_info.value)

    def test_to_float32_mono_large_data(self):
        """Test conversion of large audio data."""
        # Create 1 second of 16kHz audio
        sample_rate = 16000
        samples = [i % 1000 for i in range(sample_rate)]  # Simple pattern
        
        audio_data = struct.pack(f'<{len(samples)}h', *samples)
        
        result = to_float32_mono(audio_data, sample_width=2, channels=1)
        
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.float32
        assert len(result) == sample_rate
        assert np.all(result >= -1.0) and np.all(result <= 1.0)

    def test_to_float32_mono_conversion_formula(self):
        """Test that the conversion formula is mathematically correct."""
        # Test with known values
        test_samples = [0, 16384, 32767, -16384, -32768]  # Various int16 values
        audio_data = struct.pack(f'<{len(test_samples)}h', *test_samples)
        
        result = to_float32_mono(audio_data, sample_width=2, channels=1)
        
        # Verify the conversion formula: int16_value / 32768.0
        expected = np.array([0.0, 16384.0/32768.0, 32767.0/32768.0, -16384.0/32768.0, -32768.0/32768.0], dtype=np.float32)
        
        np.testing.assert_array_almost_equal(result, expected, decimal=7)
        
        # Verify specific values
        assert result[0] == 0.0  # 0 / 32768.0 = 0.0
        assert result[1] == pytest.approx(0.5, abs=1e-7)  # 16384 / 32768.0 = 0.5
        assert result[2] == pytest.approx(32767.0/32768.0, abs=1e-7)  # 32767 / 32768.0
        assert result[3] == pytest.approx(-0.5, abs=1e-7)  # -16384 / 32768.0 = -0.5
        assert result[4] == pytest.approx(-1.0, abs=1e-7)  # -32768 / 32768.0 = -1.0 