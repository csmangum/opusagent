"""
Voiceprint Storage Module

This module provides multiple storage implementations for voiceprint data, allowing
flexible persistence of voiceprint embeddings and metadata across different storage
backends.

The module includes three storage implementations:

1. JSONStorage: File-based storage using JSON format
   - Simple and portable
   - Good for development and small datasets
   - Embeds numpy arrays as lists for JSON serialization

2. RedisStorage: Redis-backed storage for high-performance applications
   - Fast in-memory storage with persistence
   - Suitable for production environments
   - Stores voiceprints as JSON strings in Redis

3. SQLiteStorage: SQLite database storage for structured data
   - ACID-compliant storage with transaction support
   - Efficient BLOB storage for embeddings
   - Includes database maintenance and optimization features

All storage implementations provide a consistent interface:
- save(voiceprint): Store a voiceprint
- get_all(): Retrieve all stored voiceprints

Usage Example:
    from opusagent.voiceprint.storage import JSONStorage
    from opusagent.voiceprint.models import Voiceprint

    storage = JSONStorage("my_voiceprints.json")
    voiceprint = Voiceprint(caller_id="user123", embedding=np.array([...]))
    storage.save(voiceprint)
    all_voiceprints = storage.get_all()
"""

import json
import sqlite3
from typing import Any, Dict, List, Optional

import numpy as np

from .models import Voiceprint


class JSONStorage:
    """
    JSON-based storage implementation for voiceprint data.

    This class provides a simple file-based storage solution using JSON format.
    Voiceprint embeddings are stored as lists and converted to/from numpy arrays
    for serialization compatibility.
    """

    def __init__(self, file_path: str = "voiceprints.json") -> None:
        """
        Initialize JSON storage with the specified file path.

        Args:
            file_path: Path to the JSON file where voiceprints will be stored.
                      Defaults to 'voiceprints.json'.
        """
        self.file_path = file_path

    def save(self, voiceprint: Voiceprint) -> None:
        """
        Save a voiceprint to JSON storage.

        Args:
            voiceprint: The Voiceprint object to save.

        Note:
            The embedding numpy array is converted to a list for JSON serialization.
        """
        voiceprints = self._load_all()
        # Convert numpy array to list for JSON serialization
        voiceprint_dict = voiceprint.model_dump()
        voiceprint_dict["embedding"] = voiceprint_dict["embedding"].tolist()
        voiceprints[voiceprint.caller_id] = voiceprint_dict
        self._save_all(voiceprints)

    def get_all(self) -> List[Voiceprint]:
        """
        Retrieve all voiceprints from JSON storage.

        Returns:
            List of Voiceprint objects loaded from storage.

        Note:
            Invalid voiceprint entries are silently skipped.
        """
        voiceprints = self._load_all()
        result = []
        for vp in voiceprints.values():
            try:
                # Convert list back to numpy array
                vp["embedding"] = np.array(vp["embedding"], dtype=np.float32)
                result.append(Voiceprint(**vp))
            except (KeyError, ValueError, TypeError):
                continue
        return result

    def _load_all(self) -> Dict[str, Dict[str, Any]]:
        """
        Load all voiceprint data from the JSON file.

        Returns:
            Dictionary mapping caller_id to voiceprint data.

        Note:
            Returns empty dictionary if file doesn't exist or is invalid.
        """
        try:
            with open(self.file_path, "r") as f:
                content = f.read().strip()
                if not content:
                    return {}
                return json.loads(content)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_all(self, voiceprints: Dict[str, Dict[str, Any]]) -> None:
        """
        Save all voiceprint data to the JSON file.

        Args:
            voiceprints: Dictionary mapping caller_id to voiceprint data.
        """
        with open(self.file_path, "w") as f:
            json.dump(voiceprints, f)


class RedisStorage:
    """
    Redis-based storage implementation for voiceprint data.

    This class provides a Redis-backed storage solution for voiceprints.
    Voiceprint embeddings are stored as JSON strings and converted to/from
    numpy arrays for serialization compatibility.
    """

    def __init__(self, redis_client) -> None:
        """
        Initialize Redis storage with the provided Redis client.

        Args:
            redis_client: Redis client instance for database operations.
        """
        self.redis = redis_client

    def save(self, voiceprint: Voiceprint) -> None:
        """
        Save a voiceprint to Redis storage.

        Args:
            voiceprint: The Voiceprint object to save.

        Note:
            The embedding numpy array is converted to a list for JSON serialization.
        """
        key = f"voiceprint:{voiceprint.caller_id}"
        # Convert numpy array to list for JSON serialization
        voiceprint_dict = voiceprint.model_dump()
        voiceprint_dict["embedding"] = voiceprint_dict["embedding"].tolist()
        self.redis.set(key, json.dumps(voiceprint_dict))

    def get_all(self) -> List[Voiceprint]:
        """
        Retrieve all voiceprints from Redis storage.

        Returns:
            List of Voiceprint objects loaded from storage.

        Raises:
            json.JSONDecodeError: If stored data is corrupted and cannot be parsed.

        Note:
            Invalid voiceprint entries are silently skipped, except for JSON decode errors.
        """
        keys = self.redis.keys("voiceprint:*")
        voiceprints = []
        for key in keys:
            try:
                data = json.loads(self.redis.get(key))
                # Convert list back to numpy array
                data["embedding"] = np.array(data["embedding"], dtype=np.float32)
                voiceprints.append(Voiceprint(**data))
            except KeyError:
                continue
            except json.JSONDecodeError:
                # Re-raise JSON decode errors to indicate data corruption
                raise
        return voiceprints


class SQLiteStorage:
    """
    SQLite-based storage implementation for voiceprint data.

    This class provides a SQLite database storage solution for voiceprints.
    Voiceprint embeddings are stored as BLOB data for efficient storage and retrieval.
    """

    def __init__(self, db_path: str = "voiceprints.db") -> None:
        """
        Initialize SQLite storage with the specified database path.

        Args:
            db_path: Path to the SQLite database file. Defaults to 'voiceprints.db'.
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """
        Initialize the SQLite database with the required table structure.

        Creates the voiceprints table if it doesn't exist with the following schema:
        - caller_id: TEXT PRIMARY KEY
        - embedding: BLOB (numpy array as bytes)
        - metadata: TEXT (JSON string)
        - created_at: TEXT
        - last_seen: TEXT
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS voiceprints (
                    caller_id TEXT PRIMARY KEY,
                    embedding BLOB,
                    metadata TEXT,
                    created_at TEXT,
                    last_seen TEXT
                )
            """
            )

    def save(self, voiceprint: Voiceprint) -> None:
        """
        Save a voiceprint to SQLite storage.

        Args:
            voiceprint: The Voiceprint object to save.

        Note:
            The embedding is stored as BLOB data for efficient storage.
            Metadata is stored as a JSON string.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO voiceprints 
                (caller_id, embedding, metadata, created_at, last_seen) VALUES (?, ?, ?, ?, ?)
            """,
                (
                    voiceprint.caller_id,
                    voiceprint.embedding.tobytes(),
                    json.dumps(voiceprint.metadata),
                    voiceprint.created_at,
                    voiceprint.last_seen,
                ),
            )

    def get_all(self) -> List[Voiceprint]:
        """
        Retrieve all voiceprints from SQLite storage.

        Returns:
            List of Voiceprint objects loaded from storage.

        Note:
            Invalid voiceprint entries are silently skipped.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM voiceprints")
            voiceprints = []
            for row in cursor.fetchall():
                try:
                    voiceprints.append(
                        Voiceprint(
                            caller_id=row[0],
                            embedding=np.frombuffer(row[1], dtype=np.float32),
                            metadata=json.loads(row[2]) if row[2] else {},
                            created_at=row[3],
                            last_seen=row[4],
                        )
                    )
                except (json.JSONDecodeError, ValueError):
                    continue
            return voiceprints

    def close(self) -> None:
        """
        Close the database connection and ensure file handle is released.

        This method performs database maintenance operations:
        - Forces a WAL checkpoint to ensure all data is written to disk
        - Optimizes the database for better performance
        - Truncates the WAL file to free up disk space

        Note:
            This should be called when the storage instance is no longer needed
            to ensure proper cleanup of database resources.
        """
        # Force a connection to ensure any pending writes are flushed
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA wal_checkpoint(FULL)")
            conn.execute("PRAGMA optimize")
            conn.commit()
            # Close all connections to this database
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            conn.commit()
