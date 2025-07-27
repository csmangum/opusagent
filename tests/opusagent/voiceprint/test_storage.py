import pytest
import json
import sqlite3
import tempfile
import os
from unittest.mock import Mock, patch
import numpy as np
from opusagent.voiceprint.storage import JSONStorage, RedisStorage, SQLiteStorage
from opusagent.voiceprint.models import Voiceprint


class TestJSONStorage:
    """Test the JSONStorage class."""
    
    def test_json_storage_initialization(self):
        """Test JSON storage initialization."""
        storage = JSONStorage("test_voiceprints.json")
        assert storage.file_path == "test_voiceprints.json"
    
    def test_json_storage_default_path(self):
        """Test JSON storage with default path."""
        storage = JSONStorage()
        assert storage.file_path == "voiceprints.json"
    
    def test_json_storage_save_and_load(self, temp_json_storage, sample_voiceprint):
        """Test saving and loading voiceprints."""
        # Save voiceprint
        temp_json_storage.save(sample_voiceprint)
        
        # Load all voiceprints
        voiceprints = temp_json_storage.get_all()
        
        assert len(voiceprints) == 1
        assert voiceprints[0].caller_id == sample_voiceprint.caller_id
        assert np.array_equal(voiceprints[0].embedding, sample_voiceprint.embedding)
        assert voiceprints[0].metadata == sample_voiceprint.metadata
    
    def test_json_storage_multiple_voiceprints(self, temp_json_storage, multiple_voiceprints):
        """Test saving and loading multiple voiceprints."""
        # Save multiple voiceprints
        for voiceprint in multiple_voiceprints:
            temp_json_storage.save(voiceprint)
        
        # Load all voiceprints
        voiceprints = temp_json_storage.get_all()
        
        assert len(voiceprints) == len(multiple_voiceprints)
        
        # Check that all voiceprints are loaded correctly
        for i, voiceprint in enumerate(voiceprints):
            assert voiceprint.caller_id == multiple_voiceprints[i].caller_id
            assert np.array_equal(voiceprint.embedding, multiple_voiceprints[i].embedding)
    
    def test_json_storage_overwrite(self, temp_json_storage, sample_voiceprint):
        """Test overwriting existing voiceprint."""
        # Save initial voiceprint
        temp_json_storage.save(sample_voiceprint)
        
        # Create modified voiceprint with same caller_id
        modified_voiceprint = Voiceprint(
            caller_id=sample_voiceprint.caller_id,
            embedding=sample_voiceprint.embedding + 0.1,
            metadata={"modified": True}
        )
        
        # Save modified voiceprint (should overwrite)
        temp_json_storage.save(modified_voiceprint)
        
        # Load voiceprints
        voiceprints = temp_json_storage.get_all()
        
        assert len(voiceprints) == 1
        assert voiceprints[0].caller_id == modified_voiceprint.caller_id
        assert np.array_equal(voiceprints[0].embedding, modified_voiceprint.embedding)
        assert voiceprints[0].metadata == modified_voiceprint.metadata
    
    def test_json_storage_empty_file(self, temp_json_storage):
        """Test loading from empty file."""
        voiceprints = temp_json_storage.get_all()
        assert len(voiceprints) == 0
    
    def test_json_storage_file_not_found(self):
        """Test loading from non-existent file."""
        storage = JSONStorage("nonexistent.json")
        voiceprints = storage.get_all()
        assert len(voiceprints) == 0
    
    def test_json_storage_serialization(self, temp_json_storage, sample_voiceprint):
        """Test JSON serialization of voiceprints."""
        temp_json_storage.save(sample_voiceprint)
        
        # Check that file was created and contains valid JSON
        with open(temp_json_storage.file_path, 'r') as f:
            data = json.load(f)
        
        assert sample_voiceprint.caller_id in data
        assert "caller_id" in data[sample_voiceprint.caller_id]
        assert "embedding" in data[sample_voiceprint.caller_id]
        assert "metadata" in data[sample_voiceprint.caller_id]


class TestRedisStorage:
    """Test the RedisStorage class."""
    
    def test_redis_storage_initialization(self, mock_redis_client):
        """Test Redis storage initialization."""
        storage = RedisStorage(mock_redis_client)
        assert storage.redis == mock_redis_client
    
    def test_redis_storage_save(self, mock_redis_client, sample_voiceprint):
        """Test saving voiceprint to Redis."""
        storage = RedisStorage(mock_redis_client)
        storage.save(sample_voiceprint)
        
        # Verify that Redis set was called
        mock_redis_client.set.assert_called_once()
        call_args = mock_redis_client.set.call_args
        assert call_args[0][0] == f"voiceprint:{sample_voiceprint.caller_id}"
    
    def test_redis_storage_get_all(self, mock_redis_client):
        """Test loading all voiceprints from Redis."""
        storage = RedisStorage(mock_redis_client)
        voiceprints = storage.get_all()
        
        # Verify that Redis keys and get were called
        mock_redis_client.keys.assert_called_once_with("voiceprint:*")
        assert mock_redis_client.get.call_count == 2  # Two keys returned
    
    def test_redis_storage_empty(self, mock_redis_client):
        """Test loading from empty Redis."""
        mock_redis_client.keys.return_value = []
        storage = RedisStorage(mock_redis_client)
        voiceprints = storage.get_all()
        
        assert len(voiceprints) == 0
        mock_redis_client.keys.assert_called_once_with("voiceprint:*")
        mock_redis_client.get.assert_not_called()
    
    def test_redis_storage_invalid_json(self, mock_redis_client):
        """Test handling of invalid JSON in Redis."""
        mock_redis_client.keys.return_value = [b"voiceprint:test"]
        mock_redis_client.get.return_value = "invalid json"
        
        storage = RedisStorage(mock_redis_client)
        
        with pytest.raises(Exception):  # Should raise JSON decode error
            storage.get_all()


class TestSQLiteStorage:
    """Test the SQLiteStorage class."""
    
    def test_sqlite_storage_initialization(self, temp_sqlite_storage):
        """Test SQLite storage initialization."""
        assert temp_sqlite_storage.db_path.endswith('.db')
        
        # Check that table was created
        with sqlite3.connect(temp_sqlite_storage.db_path) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='voiceprints'")
            assert cursor.fetchone() is not None
    
    def test_sqlite_storage_save_and_load(self, temp_sqlite_storage, sample_voiceprint):
        """Test saving and loading voiceprints."""
        # Save voiceprint
        temp_sqlite_storage.save(sample_voiceprint)
        
        # Load all voiceprints
        voiceprints = temp_sqlite_storage.get_all()
        
        assert len(voiceprints) == 1
        assert voiceprints[0].caller_id == sample_voiceprint.caller_id
        assert np.array_equal(voiceprints[0].embedding, sample_voiceprint.embedding)
        assert voiceprints[0].metadata == sample_voiceprint.metadata
    
    def test_sqlite_storage_multiple_voiceprints(self, temp_sqlite_storage, multiple_voiceprints):
        """Test saving and loading multiple voiceprints."""
        # Save multiple voiceprints
        for voiceprint in multiple_voiceprints:
            temp_sqlite_storage.save(voiceprint)
        
        # Load all voiceprints
        voiceprints = temp_sqlite_storage.get_all()
        
        assert len(voiceprints) == len(multiple_voiceprints)
        
        # Check that all voiceprints are loaded correctly
        for i, voiceprint in enumerate(voiceprints):
            assert voiceprint.caller_id == multiple_voiceprints[i].caller_id
            assert np.array_equal(voiceprint.embedding, multiple_voiceprints[i].embedding)
    
    def test_sqlite_storage_overwrite(self, temp_sqlite_storage, sample_voiceprint):
        """Test overwriting existing voiceprint."""
        # Save initial voiceprint
        temp_sqlite_storage.save(sample_voiceprint)
        
        # Create modified voiceprint with same caller_id
        modified_voiceprint = Voiceprint(
            caller_id=sample_voiceprint.caller_id,
            embedding=sample_voiceprint.embedding + 0.1,
            metadata={"modified": True}
        )
        
        # Save modified voiceprint (should overwrite)
        temp_sqlite_storage.save(modified_voiceprint)
        
        # Load voiceprints
        voiceprints = temp_sqlite_storage.get_all()
        
        assert len(voiceprints) == 1
        assert voiceprints[0].caller_id == modified_voiceprint.caller_id
        assert np.array_equal(voiceprints[0].embedding, modified_voiceprint.embedding)
        assert voiceprints[0].metadata == modified_voiceprint.metadata
    
    def test_sqlite_storage_empty_database(self, temp_sqlite_storage):
        """Test loading from empty database."""
        voiceprints = temp_sqlite_storage.get_all()
        assert len(voiceprints) == 0
    
    def test_sqlite_storage_table_creation(self):
        """Test that table is created on initialization."""
        import time
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_db = f.name
        
        try:
            storage = SQLiteStorage(temp_db)
            
            # Check that table exists by using the storage's own connection
            # This avoids creating additional connections that might hold the file
            conn = sqlite3.connect(temp_db)
            try:
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='voiceprints'")
                assert cursor.fetchone() is not None
                
                # Check table structure
                cursor = conn.execute("PRAGMA table_info(voiceprints)")
                columns = cursor.fetchall()
                column_names = [col[1] for col in columns]
                
                assert "caller_id" in column_names
                assert "embedding" in column_names
                assert "metadata" in column_names
            finally:
                conn.close()
            
            # Close the storage to release file handles
            storage.close()
            
            # Give the OS time to release the file handle
            time.sleep(0.1)
        finally:
            try:
                os.unlink(temp_db)
            except (FileNotFoundError, PermissionError):
                # On Windows, file might still be locked - this is acceptable
                pass
    
    def test_sqlite_storage_metadata_serialization(self, temp_sqlite_storage, sample_voiceprint):
        """Test metadata JSON serialization."""
        # Add complex metadata
        complex_metadata = {
            "personal": {"age": 30, "gender": "male"},
            "preferences": ["english", "spanish"],
            "flags": [True, False, True],
            "nested": {"level1": {"level2": "value"}}
        }
        
        voiceprint_with_complex_metadata = Voiceprint(
            caller_id="test_caller",
            embedding=sample_voiceprint.embedding,
            metadata=complex_metadata
        )
        
        temp_sqlite_storage.save(voiceprint_with_complex_metadata)
        voiceprints = temp_sqlite_storage.get_all()
        
        assert len(voiceprints) == 1
        assert voiceprints[0].metadata == complex_metadata
    
    def test_sqlite_storage_embedding_precision(self, temp_sqlite_storage, sample_voiceprint):
        """Test that embedding precision is maintained."""
        # Create voiceprint with specific embedding
        test_embedding = np.array([1.23456789, 2.34567890, 3.45678901], dtype=np.float32)
        voiceprint = Voiceprint(
            caller_id="test_caller",
            embedding=test_embedding,
            metadata={"test": True}
        )
        
        temp_sqlite_storage.save(voiceprint)
        voiceprints = temp_sqlite_storage.get_all()
        
        assert len(voiceprints) == 1
        assert np.array_equal(voiceprints[0].embedding, test_embedding)
        assert voiceprints[0].embedding.dtype == np.float32


class TestStorageIntegration:
    """Integration tests for storage systems."""
    
    def test_storage_consistency(self, temp_json_storage, temp_sqlite_storage, sample_voiceprint):
        """Test that different storage backends produce consistent results."""
        # Save to both storages
        temp_json_storage.save(sample_voiceprint)
        temp_sqlite_storage.save(sample_voiceprint)
        
        # Load from both storages
        json_voiceprints = temp_json_storage.get_all()
        sqlite_voiceprints = temp_sqlite_storage.get_all()
        
        assert len(json_voiceprints) == 1
        assert len(sqlite_voiceprints) == 1
        
        # Compare results
        json_vp = json_voiceprints[0]
        sqlite_vp = sqlite_voiceprints[0]
        
        assert json_vp.caller_id == sqlite_vp.caller_id
        assert np.array_equal(json_vp.embedding, sqlite_vp.embedding)
        assert json_vp.metadata == sqlite_vp.metadata
    
    def test_storage_performance(self, temp_json_storage, multiple_voiceprints):
        """Test storage performance with multiple voiceprints."""
        import time
        
        # Time saving multiple voiceprints
        start_time = time.time()
        for voiceprint in multiple_voiceprints:
            temp_json_storage.save(voiceprint)
        save_time = time.time() - start_time
        
        # Time loading multiple voiceprints
        start_time = time.time()
        voiceprints = temp_json_storage.get_all()
        load_time = time.time() - start_time
        
        assert len(voiceprints) == len(multiple_voiceprints)
        assert save_time < 1.0  # Should be fast
        assert load_time < 1.0  # Should be fast 