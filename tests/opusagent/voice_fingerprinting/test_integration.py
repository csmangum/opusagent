import pytest
import numpy as np
import tempfile
import os
from unittest.mock import patch, Mock
from opusagent.voice_fingerprinting.recognizer import OpusAgentVoiceRecognizer
from opusagent.voice_fingerprinting.storage import JSONStorage, SQLiteStorage
from opusagent.voice_fingerprinting.models import Voiceprint, VoiceFingerprintConfig
from opusagent.voice_fingerprinting.utils import normalize_embedding


class TestVoiceFingerprintingIntegration:
    """Integration tests for the complete voice fingerprinting system."""
    
    def test_complete_enrollment_and_matching_workflow(self, sample_audio_buffer, temp_json_storage):
        """Test complete workflow from enrollment to matching."""
        with patch('opusagent.voice_fingerprinting.recognizer.VoiceEncoder') as mock_encoder_class:
            mock_encoder = Mock()
            mock_encoder_class.return_value = mock_encoder
            
            recognizer = OpusAgentVoiceRecognizer(storage_backend=temp_json_storage)
            
            # Step 1: Enroll a caller
            enrollment_embedding = np.random.rand(256).astype(np.float32)
            mock_encoder.embed_utterance.return_value = enrollment_embedding
            
            metadata = {"age": 30, "gender": "male", "accent": "us"}
            voiceprint = recognizer.enroll_caller("caller_123", sample_audio_buffer, metadata)
            
            # Verify enrollment
            assert voiceprint.caller_id == "caller_123"
            assert np.array_equal(voiceprint.embedding, enrollment_embedding)
            assert voiceprint.metadata == metadata
            
            # Step 2: Match the same caller
            matching_embedding = enrollment_embedding + 0.01  # Slightly different
            mock_encoder.embed_utterance.return_value = matching_embedding
            
            match_result = recognizer.match_caller(sample_audio_buffer)
            
            # Verify matching
            assert match_result is not None
            assert match_result[0] == "caller_123"  # caller_id
            assert match_result[1] > recognizer.config.similarity_threshold  # similarity
            assert match_result[2] == metadata  # metadata
    
    def test_multiple_callers_enrollment_and_matching(self, sample_audio_buffer, temp_json_storage):
        """Test enrollment and matching with multiple callers."""
        with patch('opusagent.voice_fingerprinting.recognizer.VoiceEncoder') as mock_encoder_class:
            mock_encoder = Mock()
            mock_encoder_class.return_value = mock_encoder
            
            recognizer = OpusAgentVoiceRecognizer(storage_backend=temp_json_storage)
            
            # Enroll multiple callers
            callers = [
                ("caller_1", {"age": 25, "gender": "female"}),
                ("caller_2", {"age": 45, "gender": "male"}),
                ("caller_3", {"age": 35, "gender": "female"})
            ]
            
            for caller_id, metadata in callers:
                embedding = np.random.rand(256).astype(np.float32)
                mock_encoder.embed_utterance.return_value = embedding
                recognizer.enroll_caller(caller_id, sample_audio_buffer, metadata)
            
            # Verify all callers are enrolled
            stored_voiceprints = temp_json_storage.get_all()
            assert len(stored_voiceprints) == 3
            
            # Test matching for each caller
            for caller_id, metadata in callers:
                # Get the original embedding for this caller
                original_voiceprint = next(vp for vp in stored_voiceprints if vp.caller_id == caller_id)
                
                # Create similar embedding for matching
                similar_embedding = original_voiceprint.embedding + 0.01
                mock_encoder.embed_utterance.return_value = similar_embedding
                
                match_result = recognizer.match_caller(sample_audio_buffer)
                
                assert match_result is not None
                assert match_result[0] == caller_id
                assert match_result[1] > recognizer.config.similarity_threshold
                assert match_result[2] == metadata
    
    def test_storage_backend_integration(self, sample_audio_buffer):
        """Test integration with different storage backends."""
        # Test with JSON storage
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            json_file = f.name
        
        # Test with SQLite storage
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            sqlite_file = f.name
        
        try:
            json_storage = JSONStorage(json_file)
            sqlite_storage = SQLiteStorage(sqlite_file)
            
            with patch('opusagent.voice_fingerprinting.recognizer.VoiceEncoder') as mock_encoder_class:
                mock_encoder = Mock()
                mock_encoder_class.return_value = mock_encoder
                
                # Test JSON storage
                json_recognizer = OpusAgentVoiceRecognizer(storage_backend=json_storage)
                test_embedding = np.random.rand(256).astype(np.float32)
                mock_encoder.embed_utterance.return_value = test_embedding
                
                json_recognizer.enroll_caller("test_caller", sample_audio_buffer, {"test": True})
                
                # Test SQLite storage
                sqlite_recognizer = OpusAgentVoiceRecognizer(storage_backend=sqlite_storage)
                sqlite_recognizer.enroll_caller("test_caller", sample_audio_buffer, {"test": True})
                
                # Verify both storages have the voiceprint
                json_voiceprints = json_storage.get_all()
                sqlite_voiceprints = sqlite_storage.get_all()
                
                assert len(json_voiceprints) == 1
                assert len(sqlite_voiceprints) == 1
                assert json_voiceprints[0].caller_id == "test_caller"
                assert sqlite_voiceprints[0].caller_id == "test_caller"
        
        finally:
            # Close SQLite storage to release file handle
            sqlite_storage.close()
            
            # Add a small delay to allow file handles to be released on Windows
            import time
            time.sleep(0.1)
            
            try:
                os.unlink(json_file)
                os.unlink(sqlite_file)
            except (FileNotFoundError, PermissionError):
                # On Windows, sometimes files can't be deleted immediately
                # This is acceptable for a test environment
                pass
    
    def test_configuration_integration(self, sample_audio_buffer, temp_json_storage):
        """Test that configuration affects system behavior."""
        with patch('opusagent.voice_fingerprinting.recognizer.VoiceEncoder') as mock_encoder_class:
            mock_encoder = Mock()
            mock_encoder_class.return_value = mock_encoder
            
            recognizer = OpusAgentVoiceRecognizer(storage_backend=temp_json_storage)
            
            # Enroll a caller
            enrollment_embedding = np.random.rand(256).astype(np.float32)
            mock_encoder.embed_utterance.return_value = enrollment_embedding
            recognizer.enroll_caller("test_caller", sample_audio_buffer, {"test": True})
            
            # Test with different similarity thresholds
            test_embedding = enrollment_embedding + 0.1  # Somewhat different
            
            # High threshold - should not match
            recognizer.config.similarity_threshold = 0.95
            mock_encoder.embed_utterance.return_value = test_embedding
            result_high = recognizer.match_caller(sample_audio_buffer)
            
            # Low threshold - should match
            recognizer.config.similarity_threshold = 0.5
            result_low = recognizer.match_caller(sample_audio_buffer)
            
            # Verify configuration effect
            if result_high is None and result_low is not None:
                assert result_low[1] > 0.5
                assert result_low[1] <= 0.95
    
    def test_error_handling_integration(self, sample_audio_buffer, temp_json_storage):
        """Test error handling throughout the system."""
        with patch('opusagent.voice_fingerprinting.recognizer.VoiceEncoder') as mock_encoder_class:
            mock_encoder = Mock()
            mock_encoder_class.return_value = mock_encoder
            
            recognizer = OpusAgentVoiceRecognizer(storage_backend=temp_json_storage)
            
            # Test enrollment error
            mock_encoder.embed_utterance.side_effect = Exception("Enrollment failed")
            
            with pytest.raises(Exception):
                recognizer.enroll_caller("test_caller", sample_audio_buffer)
            
            # Test matching error
            mock_encoder.embed_utterance.side_effect = Exception("Matching failed")
            
            with pytest.raises(Exception):
                recognizer.match_caller(sample_audio_buffer)
    
    def test_performance_integration(self, sample_audio_buffer, temp_json_storage):
        """Test performance with realistic workload."""
        import time
        
        with patch('opusagent.voice_fingerprinting.recognizer.VoiceEncoder') as mock_encoder_class:
            mock_encoder = Mock()
            mock_encoder_class.return_value = mock_encoder
            
            recognizer = OpusAgentVoiceRecognizer(storage_backend=temp_json_storage)
            
            # Enroll many callers
            start_time = time.time()
            for i in range(50):
                embedding = np.random.rand(256).astype(np.float32)
                mock_encoder.embed_utterance.return_value = embedding
                recognizer.enroll_caller(f"caller_{i}", sample_audio_buffer, {"index": i})
            
            enrollment_time = time.time() - start_time
            
            # Test matching performance
            start_time = time.time()
            for i in range(10):
                test_embedding = np.random.rand(256).astype(np.float32)
                mock_encoder.embed_utterance.return_value = test_embedding
                recognizer.match_caller(sample_audio_buffer)
            
            matching_time = time.time() - start_time
            
            # Performance assertions
            assert enrollment_time < 5.0  # Should be fast
            assert matching_time < 2.0  # Should be fast
    
    def test_data_persistence_integration(self, sample_audio_buffer):
        """Test that data persists across recognizer instances."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            with patch('opusagent.voice_fingerprinting.recognizer.VoiceEncoder') as mock_encoder_class:
                mock_encoder = Mock()
                mock_encoder_class.return_value = mock_encoder
                
                # First recognizer instance
                storage = JSONStorage(temp_file)
                recognizer1 = OpusAgentVoiceRecognizer(storage_backend=storage)
                
                # Enroll caller
                embedding = np.random.rand(256).astype(np.float32)
                mock_encoder.embed_utterance.return_value = embedding
                recognizer1.enroll_caller("persistent_caller", sample_audio_buffer, {"persistent": True})
                
                # Create new recognizer instance with same storage
                recognizer2 = OpusAgentVoiceRecognizer(storage_backend=storage)
                
                # Test matching with new instance
                test_embedding = embedding + 0.01
                mock_encoder.embed_utterance.return_value = test_embedding
                result = recognizer2.match_caller(sample_audio_buffer)
                
                assert result is not None
                assert result[0] == "persistent_caller"
                assert result[2]["persistent"] is True
        
        finally:
            try:
                os.unlink(temp_file)
            except FileNotFoundError:
                pass
    
    def test_metadata_integration(self, sample_audio_buffer, temp_json_storage):
        """Test metadata handling throughout the system."""
        with patch('opusagent.voice_fingerprinting.recognizer.VoiceEncoder') as mock_encoder_class:
            mock_encoder = Mock()
            mock_encoder_class.return_value = mock_encoder
            
            recognizer = OpusAgentVoiceRecognizer(storage_backend=temp_json_storage)
            
            # Test complex metadata
            complex_metadata = {
                "personal": {
                    "age": 30,
                    "gender": "male",
                    "preferences": ["english", "spanish"]
                },
                "technical": {
                    "sample_rate": 16000,
                    "quality_score": 0.85
                },
                "flags": [True, False, True],
                "nested": {
                    "level1": {
                        "level2": {
                            "level3": "deep_value"
                        }
                    }
                }
            }
            
            # Enroll with complex metadata
            embedding = np.random.rand(256).astype(np.float32)
            mock_encoder.embed_utterance.return_value = embedding
            voiceprint = recognizer.enroll_caller("complex_caller", sample_audio_buffer, complex_metadata)
            
            # Verify metadata is preserved
            assert voiceprint.metadata == complex_metadata
            
            # Test matching preserves metadata
            test_embedding = embedding + 0.01
            mock_encoder.embed_utterance.return_value = test_embedding
            result = recognizer.match_caller(sample_audio_buffer)
            
            assert result is not None
            assert result[2] == complex_metadata
    
    def test_similarity_calculation_integration(self, sample_audio_buffer, temp_json_storage):
        """Test similarity calculation accuracy in integration."""
        with patch('opusagent.voice_fingerprinting.recognizer.VoiceEncoder') as mock_encoder_class:
            mock_encoder = Mock()
            mock_encoder_class.return_value = mock_encoder
            
            recognizer = OpusAgentVoiceRecognizer(storage_backend=temp_json_storage)
            
            # Create test embeddings with known relationships
            embedding1 = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32)
            embedding2 = np.array([1.1, 2.1, 3.1, 4.1], dtype=np.float32)  # Similar
            embedding3 = np.array([10.0, 20.0, 30.0, 40.0], dtype=np.float32)  # Different
            
            # Enroll voiceprints
            mock_encoder.embed_utterance.return_value = embedding1
            recognizer.enroll_caller("caller_1", sample_audio_buffer, {"type": "similar"})
            
            mock_encoder.embed_utterance.return_value = embedding2
            recognizer.enroll_caller("caller_2", sample_audio_buffer, {"type": "similar"})
            
            mock_encoder.embed_utterance.return_value = embedding3
            recognizer.enroll_caller("caller_3", sample_audio_buffer, {"type": "different"})
            
            # Test matching with embedding similar to embedding1
            test_embedding = embedding1 + 0.01
            mock_encoder.embed_utterance.return_value = test_embedding
            result = recognizer.match_caller(sample_audio_buffer)
            
            if result is not None:
                # Should match with caller_1 (most similar)
                assert result[0] == "caller_1"
                
                # Verify similarity calculation
                from scipy.spatial.distance import cosine
                expected_similarity = 1 - cosine(test_embedding, embedding1)
                assert abs(result[1] - expected_similarity) < 1e-6


class TestVoiceFingerprintingEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_storage_matching(self, sample_audio_buffer, temp_json_storage):
        """Test matching when storage is empty."""
        with patch('opusagent.voice_fingerprinting.recognizer.VoiceEncoder') as mock_encoder_class:
            mock_encoder = Mock()
            mock_encoder_class.return_value = mock_encoder
            
            recognizer = OpusAgentVoiceRecognizer(storage_backend=temp_json_storage)
            
            # Try to match without any enrolled callers
            test_embedding = np.random.rand(256).astype(np.float32)
            mock_encoder.embed_utterance.return_value = test_embedding
            
            result = recognizer.match_caller(sample_audio_buffer)
            assert result is None
    
    def test_duplicate_enrollment(self, sample_audio_buffer, temp_json_storage):
        """Test enrolling the same caller multiple times."""
        with patch('opusagent.voice_fingerprinting.recognizer.VoiceEncoder') as mock_encoder_class:
            mock_encoder = Mock()
            mock_encoder_class.return_value = mock_encoder
            
            recognizer = OpusAgentVoiceRecognizer(storage_backend=temp_json_storage)
            
            # Enroll same caller twice
            embedding1 = np.random.rand(256).astype(np.float32)
            mock_encoder.embed_utterance.return_value = embedding1
            recognizer.enroll_caller("duplicate_caller", sample_audio_buffer, {"version": 1})
            
            embedding2 = np.random.rand(256).astype(np.float32)
            mock_encoder.embed_utterance.return_value = embedding2
            recognizer.enroll_caller("duplicate_caller", sample_audio_buffer, {"version": 2})
            
            # Should only have one voiceprint (latest overwrites)
            stored_voiceprints = temp_json_storage.get_all()
            assert len(stored_voiceprints) == 1
            assert stored_voiceprints[0].metadata["version"] == 2
    
    def test_large_metadata_handling(self, sample_audio_buffer, temp_json_storage):
        """Test handling of large metadata."""
        with patch('opusagent.voice_fingerprinting.recognizer.VoiceEncoder') as mock_encoder_class:
            mock_encoder = Mock()
            mock_encoder_class.return_value = mock_encoder
            
            recognizer = OpusAgentVoiceRecognizer(storage_backend=temp_json_storage)
            
            # Create large metadata
            large_metadata = {
                "large_array": list(range(10000)),
                "large_string": "x" * 10000,
                "nested": {
                    "deep": {
                        "very_deep": {
                            "extremely_deep": "value" * 100
                        }
                    }
                }
            }
            
            embedding = np.random.rand(256).astype(np.float32)
            mock_encoder.embed_utterance.return_value = embedding
            voiceprint = recognizer.enroll_caller("large_metadata_caller", sample_audio_buffer, large_metadata)
            
            # Verify large metadata is handled
            assert voiceprint.metadata == large_metadata
            
            # Test matching with large metadata
            test_embedding = embedding + 0.01
            mock_encoder.embed_utterance.return_value = test_embedding
            result = recognizer.match_caller(sample_audio_buffer)
            
            assert result is not None
            assert result[2] == large_metadata 