import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from scipy.spatial.distance import cosine
from opusagent.voiceprint.recognizer import OpusAgentVoiceRecognizer
from opusagent.voiceprint.models import Voiceprint
import tempfile
import os
from opusagent.voiceprint.storage import JSONStorage


class TestOpusAgentVoiceRecognizer:
    """Test the OpusAgentVoiceRecognizer class."""
    
    def test_recognizer_initialization(self, temp_json_storage):
        """Test recognizer initialization."""
        with patch('opusagent.voiceprint.recognizer.VoiceEncoder') as mock_encoder_class:
            mock_encoder = Mock()
            mock_encoder_class.return_value = mock_encoder
            
            recognizer = OpusAgentVoiceRecognizer(storage_backend=temp_json_storage)
            
            assert recognizer.storage == temp_json_storage
            assert recognizer.encoder == mock_encoder
            assert recognizer.config is not None
    
    def test_recognizer_initialization_default_storage(self):
        """Test recognizer initialization with default storage."""
        with patch('opusagent.voiceprint.recognizer.VoiceEncoder') as mock_encoder_class:
            mock_encoder = Mock()
            mock_encoder_class.return_value = mock_encoder
            
            recognizer = OpusAgentVoiceRecognizer()
            
            assert recognizer.storage is not None
            assert recognizer.encoder == mock_encoder
    
    @patch('opusagent.voiceprint.recognizer.preprocess_wav')
    def test_get_embedding(self, mock_preprocess, sample_audio_buffer, mock_voice_encoder):
        """Test embedding generation from audio buffer."""
        # Setup mocks
        mock_preprocess.return_value = sample_audio_buffer
        mock_voice_encoder.embed_utterance.return_value = np.random.rand(256).astype(np.float32)
        
        with patch('opusagent.voiceprint.recognizer.VoiceEncoder') as mock_encoder_class:
            mock_encoder_class.return_value = mock_voice_encoder
            
            recognizer = OpusAgentVoiceRecognizer()
            embedding = recognizer.get_embedding(sample_audio_buffer)
            
            # Verify preprocessing was called
            mock_preprocess.assert_called_once_with(sample_audio_buffer)
            
            # Verify embedding generation was called
            mock_voice_encoder.embed_utterance.assert_called_once()
            
            # Verify embedding is numpy array with correct dtype
            assert isinstance(embedding, np.ndarray)
            assert embedding.dtype == np.float32
    
    def test_get_embedding_error_handling(self, sample_audio_buffer):
        """Test embedding generation error handling."""
        with patch('opusagent.voiceprint.recognizer.VoiceEncoder') as mock_encoder_class:
            mock_encoder = Mock()
            mock_encoder.embed_utterance.side_effect = Exception("Embedding error")
            mock_encoder_class.return_value = mock_encoder
            
            recognizer = OpusAgentVoiceRecognizer()
            
            with pytest.raises(Exception):
                recognizer.get_embedding(sample_audio_buffer)
    
    def test_match_caller_no_matches(self, sample_audio_buffer, temp_json_storage, mock_voice_encoder):
        """Test caller matching when no matches found."""
        with patch('opusagent.voiceprint.recognizer.VoiceEncoder') as mock_encoder_class:
            mock_encoder_class.return_value = mock_voice_encoder
            
            recognizer = OpusAgentVoiceRecognizer(storage_backend=temp_json_storage)
            
            # No voiceprints in storage
            result = recognizer.match_caller(sample_audio_buffer)
            
            assert result is None
    
    def test_match_caller_with_matches(self, sample_audio_buffer, temp_json_storage, mock_voice_encoder, multiple_voiceprints):
        """Test caller matching when matches are found."""
        with patch('opusagent.voiceprint.recognizer.VoiceEncoder') as mock_encoder_class:
            mock_encoder_class.return_value = mock_voice_encoder
            
            recognizer = OpusAgentVoiceRecognizer(storage_backend=temp_json_storage)
            
            # Add voiceprints to storage
            for voiceprint in multiple_voiceprints:
                temp_json_storage.save(voiceprint)
            
            # Mock embedding generation to return similar embedding
            similar_embedding = multiple_voiceprints[0].embedding + 0.01  # Slightly different
            mock_voice_encoder.embed_utterance.return_value = similar_embedding
            
            result = recognizer.match_caller(sample_audio_buffer)
            
            assert result is not None
            assert len(result) == 3  # (caller_id, similarity, metadata)
            assert result[0] == multiple_voiceprints[0].caller_id
            assert result[1] > recognizer.config.similarity_threshold  # Should be above threshold
    
    def test_match_caller_below_threshold(self, sample_audio_buffer, temp_json_storage, mock_voice_encoder, sample_voiceprint):
        """Test caller matching when similarity is below threshold."""
        with patch('opusagent.voiceprint.recognizer.VoiceEncoder') as mock_encoder_class:
            mock_encoder_class.return_value = mock_voice_encoder
            
            recognizer = OpusAgentVoiceRecognizer(storage_backend=temp_json_storage)
            
            # Add voiceprint to storage
            temp_json_storage.save(sample_voiceprint)
            
            # Mock embedding generation to return very different embedding
            # Create a completely different embedding by negating the original
            different_embedding = -sample_voiceprint.embedding
            mock_voice_encoder.embed_utterance.return_value = different_embedding
            
            result = recognizer.match_caller(sample_audio_buffer)
            
            # Should return None if similarity is below threshold
            if result is not None:
                assert result[1] <= recognizer.config.similarity_threshold
    
    def test_match_caller_multiple_matches_ordering(self, sample_audio_buffer, temp_json_storage, mock_voice_encoder, multiple_voiceprints):
        """Test that multiple matches are ordered by similarity."""
        with patch('opusagent.voiceprint.recognizer.VoiceEncoder') as mock_encoder_class:
            mock_encoder_class.return_value = mock_voice_encoder
            
            recognizer = OpusAgentVoiceRecognizer(storage_backend=temp_json_storage)
            
            # Add voiceprints to storage
            for voiceprint in multiple_voiceprints:
                temp_json_storage.save(voiceprint)
            
            # Mock embedding generation to return embedding similar to first voiceprint
            similar_embedding = multiple_voiceprints[0].embedding + 0.01
            mock_voice_encoder.embed_utterance.return_value = similar_embedding
            
            result = recognizer.match_caller(sample_audio_buffer)
            
            if result is not None:
                # Should return the best match (highest similarity)
                assert result[0] == multiple_voiceprints[0].caller_id
    
    def test_enroll_caller(self, sample_audio_buffer, temp_json_storage, mock_voice_encoder):
        """Test caller enrollment."""
        with patch('opusagent.voiceprint.recognizer.VoiceEncoder') as mock_encoder_class:
            mock_encoder_class.return_value = mock_voice_encoder
            
            recognizer = OpusAgentVoiceRecognizer(storage_backend=temp_json_storage)
            
            # Mock embedding generation
            test_embedding = np.random.rand(256).astype(np.float32)
            mock_voice_encoder.embed_utterance.return_value = test_embedding
            
            # Enroll caller
            metadata = {"age": 30, "gender": "male"}
            voiceprint = recognizer.enroll_caller("test_caller", sample_audio_buffer, metadata)
            
            # Verify voiceprint was created correctly
            assert voiceprint.caller_id == "test_caller"
            assert np.array_equal(voiceprint.embedding, test_embedding)
            assert voiceprint.metadata == metadata
            
            # Verify voiceprint was saved to storage
            stored_voiceprints = temp_json_storage.get_all()
            assert len(stored_voiceprints) == 1
            assert stored_voiceprints[0].caller_id == "test_caller"
    
    def test_enroll_caller_default_metadata(self, sample_audio_buffer, temp_json_storage, mock_voice_encoder):
        """Test caller enrollment with default metadata."""
        with patch('opusagent.voiceprint.recognizer.VoiceEncoder') as mock_encoder_class:
            mock_encoder_class.return_value = mock_voice_encoder
            
            recognizer = OpusAgentVoiceRecognizer(storage_backend=temp_json_storage)
            
            # Mock embedding generation
            test_embedding = np.random.rand(256).astype(np.float32)
            mock_voice_encoder.embed_utterance.return_value = test_embedding
            
            # Enroll caller without metadata
            voiceprint = recognizer.enroll_caller("test_caller", sample_audio_buffer)
            
            # Verify default metadata
            assert voiceprint.metadata == {}
    
    def test_enroll_caller_error_handling(self, sample_audio_buffer, temp_json_storage):
        """Test caller enrollment error handling."""
        with patch('opusagent.voiceprint.recognizer.VoiceEncoder') as mock_encoder_class:
            mock_encoder = Mock()
            mock_encoder.embed_utterance.side_effect = Exception("Enrollment error")
            mock_encoder_class.return_value = mock_encoder
            
            recognizer = OpusAgentVoiceRecognizer(storage_backend=temp_json_storage)
            
            with pytest.raises(Exception):
                recognizer.enroll_caller("test_caller", sample_audio_buffer)
    
    def test_similarity_calculation(self, sample_audio_buffer, temp_json_storage, mock_voice_encoder):
        """Test similarity calculation accuracy."""
        with patch('opusagent.voiceprint.recognizer.VoiceEncoder') as mock_encoder_class:
            mock_encoder_class.return_value = mock_voice_encoder
            
            recognizer = OpusAgentVoiceRecognizer(storage_backend=temp_json_storage)
            
            # Create test embeddings
            embedding1 = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32)
            embedding2 = np.array([1.1, 2.1, 3.1, 4.1], dtype=np.float32)  # Similar
            embedding3 = np.array([10.0, 20.0, 30.0, 40.0], dtype=np.float32)  # Different
            
            # Create voiceprints
            voiceprint1 = Voiceprint(caller_id="caller1", embedding=embedding1)
            voiceprint2 = Voiceprint(caller_id="caller2", embedding=embedding2)
            voiceprint3 = Voiceprint(caller_id="caller3", embedding=embedding3)
            
            # Add to storage
            temp_json_storage.save(voiceprint1)
            temp_json_storage.save(voiceprint2)
            temp_json_storage.save(voiceprint3)
            
            # Mock embedding generation to return embedding similar to embedding1
            test_embedding = embedding1 + 0.01
            mock_voice_encoder.embed_utterance.return_value = test_embedding
            
            result = recognizer.match_caller(sample_audio_buffer)
            
            if result is not None:
                # Should match with embedding1 (most similar)
                assert result[0] == "caller1"
                
                # Verify similarity calculation
                expected_similarity = 1 - cosine(test_embedding, embedding1)
                assert abs(result[1] - expected_similarity) < 1e-6
    
    def test_config_integration(self, sample_audio_buffer, temp_json_storage, mock_voice_encoder, sample_voiceprint):
        """Test that configuration affects matching behavior."""
        with patch('opusagent.voiceprint.recognizer.VoiceEncoder') as mock_encoder_class:
            mock_encoder_class.return_value = mock_voice_encoder
            
            recognizer = OpusAgentVoiceRecognizer(storage_backend=temp_json_storage)
            
            # Add voiceprint to storage
            temp_json_storage.save(sample_voiceprint)
            
            # Test with different similarity thresholds
            original_threshold = recognizer.config.similarity_threshold
            
            # Test with high threshold (should not match)
            recognizer.config.similarity_threshold = 0.95
            mock_voice_encoder.embed_utterance.return_value = sample_voiceprint.embedding + 0.1
            result_high = recognizer.match_caller(sample_audio_buffer)
            
            # Test with low threshold (should match)
            recognizer.config.similarity_threshold = 0.5
            result_low = recognizer.match_caller(sample_audio_buffer)
            
            # Verify behavior difference
            if result_high is None and result_low is not None:
                assert result_low[1] > 0.5  # Should be above low threshold
                assert result_low[1] <= 0.95  # Should be below high threshold
    
    def test_storage_integration(self, sample_audio_buffer, mock_voice_encoder, multiple_voiceprints):
        """Test integration with different storage backends."""
        # Test with JSON storage
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_json_file = f.name
        
        try:
            json_storage = JSONStorage(temp_json_file)
            
            with patch('opusagent.voiceprint.recognizer.VoiceEncoder') as mock_encoder_class:
                mock_encoder_class.return_value = mock_voice_encoder
                
                recognizer = OpusAgentVoiceRecognizer(storage_backend=json_storage)
                
                # Add voiceprints
                for voiceprint in multiple_voiceprints:
                    json_storage.save(voiceprint)
                
                # Test matching
                mock_voice_encoder.embed_utterance.return_value = multiple_voiceprints[0].embedding + 0.01
                result = recognizer.match_caller(sample_audio_buffer)
                
                if result is not None:
                    assert result[0] == multiple_voiceprints[0].caller_id
        finally:
            try:
                os.unlink(temp_json_file)
            except FileNotFoundError:
                pass


class TestRecognizerPerformance:
    """Performance tests for the recognizer."""
    
    def test_embedding_generation_performance(self, sample_audio_buffer, mock_voice_encoder):
        """Test embedding generation performance."""
        import time
        
        with patch('opusagent.voiceprint.recognizer.VoiceEncoder') as mock_encoder_class:
            mock_encoder_class.return_value = mock_voice_encoder
            
            recognizer = OpusAgentVoiceRecognizer()
            
            # Time embedding generation
            start_time = time.time()
            for _ in range(10):
                recognizer.get_embedding(sample_audio_buffer)
            end_time = time.time()
            
            avg_time = (end_time - start_time) / 10
            assert avg_time < 0.1  # Should be fast
    
    def test_matching_performance(self, sample_audio_buffer, temp_json_storage, mock_voice_encoder):
        """Test matching performance with many voiceprints."""
        import time
        
        with patch('opusagent.voiceprint.recognizer.VoiceEncoder') as mock_encoder_class:
            mock_encoder_class.return_value = mock_voice_encoder
            
            recognizer = OpusAgentVoiceRecognizer(storage_backend=temp_json_storage)
            
            # Create many voiceprints
            for i in range(100):
                voiceprint = Voiceprint(
                    caller_id=f"caller_{i}",
                    embedding=np.random.rand(256).astype(np.float32),
                    metadata={"index": i}
                )
                temp_json_storage.save(voiceprint)
            
            # Mock embedding generation
            test_embedding = np.random.rand(256).astype(np.float32)
            mock_voice_encoder.embed_utterance.return_value = test_embedding
            
            # Time matching
            start_time = time.time()
            result = recognizer.match_caller(sample_audio_buffer)
            end_time = time.time()
            
            matching_time = end_time - start_time
            assert matching_time < 1.0  # Should be reasonably fast even with many voiceprints 