import pytest
import numpy as np
from unittest.mock import patch, Mock
from opusagent.voice_fingerprinting.utils import preprocess_audio, normalize_embedding


class TestPreprocessAudio:
    """Test the preprocess_audio function."""
    
    def test_preprocess_audio_basic(self, sample_audio_buffer):
        """Test basic audio preprocessing."""
        with patch('opusagent.voice_fingerprinting.utils.preprocess_wav') as mock_preprocess:
            mock_preprocess.return_value = sample_audio_buffer
            
            result = preprocess_audio(sample_audio_buffer)
            
            # Verify preprocessing was called
            mock_preprocess.assert_called_once_with(sample_audio_buffer)
            
            # Verify result
            assert np.array_equal(result, sample_audio_buffer)
    
    def test_preprocess_audio_different_input(self):
        """Test preprocessing with different input types."""
        # Test with different audio buffer
        audio_buffer = np.random.rand(8000).astype(np.float32)
        
        with patch('opusagent.voice_fingerprinting.utils.preprocess_wav') as mock_preprocess:
            mock_preprocess.return_value = audio_buffer
            
            result = preprocess_audio(audio_buffer)
            
            mock_preprocess.assert_called_once_with(audio_buffer)
            assert np.array_equal(result, audio_buffer)
    
    def test_preprocess_audio_error_handling(self, sample_audio_buffer):
        """Test preprocessing error handling."""
        with patch('opusagent.voice_fingerprinting.utils.preprocess_wav') as mock_preprocess:
            mock_preprocess.side_effect = Exception("Preprocessing error")
            
            with pytest.raises(Exception):
                preprocess_audio(sample_audio_buffer)
    
    def test_preprocess_audio_empty_buffer(self):
        """Test preprocessing with empty audio buffer."""
        empty_buffer = np.array([], dtype=np.float32)
        
        with patch('opusagent.voice_fingerprinting.utils.preprocess_wav') as mock_preprocess:
            mock_preprocess.return_value = empty_buffer
            
            result = preprocess_audio(empty_buffer)
            
            mock_preprocess.assert_called_once_with(empty_buffer)
            assert len(result) == 0
    
    def test_preprocess_audio_large_buffer(self):
        """Test preprocessing with large audio buffer."""
        large_buffer = np.random.rand(48000).astype(np.float32)  # 3 seconds at 16kHz
        
        with patch('opusagent.voice_fingerprinting.utils.preprocess_wav') as mock_preprocess:
            mock_preprocess.return_value = large_buffer
            
            result = preprocess_audio(large_buffer)
            
            mock_preprocess.assert_called_once_with(large_buffer)
            assert len(result) == 48000
    
    def test_preprocess_audio_different_dtypes(self):
        """Test preprocessing with different data types."""
        # Test with int16
        int16_buffer = np.random.randint(-32768, 32767, 16000, dtype=np.int16)
        
        with patch('opusagent.voice_fingerprinting.utils.preprocess_wav') as mock_preprocess:
            mock_preprocess.return_value = int16_buffer.astype(np.float32)
            
            result = preprocess_audio(int16_buffer)
            
            mock_preprocess.assert_called_once_with(int16_buffer)
            assert result.dtype == np.float32


class TestNormalizeEmbedding:
    """Test the normalize_embedding function."""
    
    def test_normalize_embedding_basic(self, sample_embedding):
        """Test basic embedding normalization."""
        result = normalize_embedding(sample_embedding)
        
        # Verify result is normalized (unit vector)
        norm = np.linalg.norm(result)
        assert abs(norm - 1.0) < 1e-6
        
        # Verify result is numpy array
        assert isinstance(result, np.ndarray)
    
    def test_normalize_embedding_zero_vector(self):
        """Test normalization of zero vector."""
        zero_embedding = np.zeros(256, dtype=np.float32)
        
        with pytest.raises(ValueError):
            normalize_embedding(zero_embedding)
    
    def test_normalize_embedding_small_vector(self):
        """Test normalization of small vector."""
        small_embedding = np.array([0.001, 0.002, 0.003], dtype=np.float32)
        
        result = normalize_embedding(small_embedding)
        
        norm = np.linalg.norm(result)
        assert abs(norm - 1.0) < 1e-6
    
    def test_normalize_embedding_large_vector(self):
        """Test normalization of large vector."""
        large_embedding = np.random.rand(1024).astype(np.float32) * 1000
        
        result = normalize_embedding(large_embedding)
        
        norm = np.linalg.norm(result)
        assert abs(norm - 1.0) < 1e-6
    
    def test_normalize_embedding_already_normalized(self):
        """Test normalization of already normalized vector."""
        # Create a normalized vector
        original = np.random.rand(256).astype(np.float32)
        normalized = original / np.linalg.norm(original)
        
        result = normalize_embedding(normalized)
        
        # Should remain normalized
        norm = np.linalg.norm(result)
        assert abs(norm - 1.0) < 1e-6
        
        # Should be very close to original normalized vector
        assert np.allclose(result, normalized, atol=1e-6)
    
    def test_normalize_embedding_negative_values(self):
        """Test normalization of vector with negative values."""
        negative_embedding = np.array([-1.0, -2.0, -3.0, -4.0], dtype=np.float32)
        
        result = normalize_embedding(negative_embedding)
        
        norm = np.linalg.norm(result)
        assert abs(norm - 1.0) < 1e-6
    
    def test_normalize_embedding_mixed_values(self):
        """Test normalization of vector with mixed positive and negative values."""
        mixed_embedding = np.array([1.0, -2.0, 3.0, -4.0, 5.0], dtype=np.float32)
        
        result = normalize_embedding(mixed_embedding)
        
        norm = np.linalg.norm(result)
        assert abs(norm - 1.0) < 1e-6
    
    def test_normalize_embedding_preserves_direction(self):
        """Test that normalization preserves the direction of the vector."""
        original = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        
        result = normalize_embedding(original)
        
        # Direction should be preserved (all components should have same sign)
        assert np.all(np.sign(result) == np.sign(original))
        
        # Ratios should be preserved
        original_ratio = original[1] / original[0]
        result_ratio = result[1] / result[0]
        assert abs(original_ratio - result_ratio) < 1e-6
    
    def test_normalize_embedding_different_dtypes(self):
        """Test normalization with different data types."""
        # Test with float64
        float64_embedding = np.random.rand(256).astype(np.float64)
        
        result = normalize_embedding(float64_embedding)
        
        assert result.dtype == np.float64
        norm = np.linalg.norm(result)
        assert abs(norm - 1.0) < 1e-6
    
    def test_normalize_embedding_edge_cases(self):
        """Test normalization with edge cases."""
        # Test with single element vector
        single_element = np.array([5.0], dtype=np.float32)
        result = normalize_embedding(single_element)
        assert abs(np.linalg.norm(result) - 1.0) < 1e-6
        assert abs(result[0] - 1.0) < 1e-6
        
        # Test with very small values
        small_values = np.array([1e-10, 2e-10, 3e-10], dtype=np.float32)
        result = normalize_embedding(small_values)
        assert abs(np.linalg.norm(result) - 1.0) < 1e-6
        
        # Test with very large values
        large_values = np.array([1e10, 2e10, 3e10], dtype=np.float32)
        result = normalize_embedding(large_values)
        assert abs(np.linalg.norm(result) - 1.0) < 1e-6


class TestUtilsIntegration:
    """Integration tests for utility functions."""
    
    def test_preprocess_and_normalize_workflow(self, sample_audio_buffer):
        """Test the complete workflow of preprocessing and normalization."""
        with patch('opusagent.voice_fingerprinting.utils.preprocess_wav') as mock_preprocess:
            # Mock preprocessing to return a realistic embedding
            mock_preprocess.return_value = sample_audio_buffer
            
            # Preprocess audio
            preprocessed = preprocess_audio(sample_audio_buffer)
            
            # Create a mock embedding from the preprocessed audio
            mock_embedding = np.random.rand(256).astype(np.float32)
            
            # Normalize the embedding
            normalized = normalize_embedding(mock_embedding)
            
            # Verify results
            assert len(preprocessed) == len(sample_audio_buffer)
            assert abs(np.linalg.norm(normalized) - 1.0) < 1e-6
    
    def test_utils_with_realistic_data(self):
        """Test utilities with realistic voice embedding data."""
        # Simulate realistic voice embedding (256-dimensional)
        realistic_embedding = np.random.rand(256).astype(np.float32)
        
        # Normalize
        normalized = normalize_embedding(realistic_embedding)
        
        # Verify properties
        assert normalized.shape == (256,)
        assert normalized.dtype == np.float32
        assert abs(np.linalg.norm(normalized) - 1.0) < 1e-6
        
        # Verify that normalization preserves relative relationships
        original_ratios = realistic_embedding[1:] / realistic_embedding[:-1]
        normalized_ratios = normalized[1:] / normalized[:-1]
        
        # Ratios should be preserved (except for numerical precision)
        assert np.allclose(original_ratios, normalized_ratios, atol=1e-6)
    
    def test_utils_error_propagation(self):
        """Test that errors in preprocessing propagate correctly."""
        with patch('opusagent.voice_fingerprinting.utils.preprocess_wav') as mock_preprocess:
            mock_preprocess.side_effect = Exception("Preprocessing failed")
            
            with pytest.raises(Exception):
                preprocess_audio(np.random.rand(16000).astype(np.float32))
    
    def test_utils_performance(self):
        """Test performance of utility functions."""
        import time
        
        # Test normalization performance
        large_embedding = np.random.rand(1024).astype(np.float32)
        
        start_time = time.time()
        for _ in range(1000):
            normalize_embedding(large_embedding)
        end_time = time.time()
        
        avg_time = (end_time - start_time) / 1000
        assert avg_time < 0.001  # Should be very fast
    
    def test_utils_numerical_stability(self):
        """Test numerical stability of utility functions."""
        # Test with very small values
        tiny_embedding = np.array([1e-20, 2e-20, 3e-20], dtype=np.float32)
        
        with pytest.raises(ValueError):
            normalize_embedding(tiny_embedding)
        
        # Test with very large values
        huge_embedding = np.array([1e20, 2e20, 3e20], dtype=np.float32)
        
        result = normalize_embedding(huge_embedding)
        assert abs(np.linalg.norm(result) - 1.0) < 1e-6
    
    def test_utils_memory_efficiency(self):
        """Test memory efficiency of utility functions."""
        import psutil
        import os
        
        # Create large embedding
        large_embedding = np.random.rand(10000).astype(np.float32)
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Perform normalization
        result = normalize_embedding(large_embedding)
        
        # Get final memory usage
        final_memory = process.memory_info().rss
        
        # Memory increase should be reasonable (not more than 10x the embedding size)
        memory_increase = final_memory - initial_memory
        embedding_size_bytes = large_embedding.nbytes
        
        assert memory_increase < embedding_size_bytes * 10 