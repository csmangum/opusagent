import json
import sqlite3
from typing import List
from .models import Voiceprint
import numpy as np

class JSONStorage:
    def __init__(self, file_path='voiceprints.json'):
        self.file_path = file_path
    
    def save(self, voiceprint):
        voiceprints = self._load_all()
        # Convert numpy array to list for JSON serialization
        voiceprint_dict = voiceprint.model_dump()
        voiceprint_dict['embedding'] = voiceprint_dict['embedding'].tolist()
        voiceprints[voiceprint.caller_id] = voiceprint_dict
        self._save_all(voiceprints)
    
    def get_all(self):
        voiceprints = self._load_all()
        result = []
        for vp in voiceprints.values():
            try:
                # Convert list back to numpy array
                vp['embedding'] = np.array(vp['embedding'], dtype=np.float32)
                result.append(Voiceprint(**vp))
            except (KeyError, ValueError, TypeError):
                continue
        return result

    def _load_all(self):
        try:
            with open(self.file_path, 'r') as f:
                content = f.read().strip()
                if not content:
                    return {}
                return json.loads(content)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_all(self, voiceprints):
        with open(self.file_path, 'w') as f:
            json.dump(voiceprints, f)

class RedisStorage:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def save(self, voiceprint):
        key = f"voiceprint:{voiceprint.caller_id}"
        # Convert numpy array to list for JSON serialization
        voiceprint_dict = voiceprint.model_dump()
        voiceprint_dict['embedding'] = voiceprint_dict['embedding'].tolist()
        self.redis.set(key, json.dumps(voiceprint_dict))
    
    def get_all(self):
        keys = self.redis.keys("voiceprint:*")
        voiceprints = []
        for key in keys:
            try:
                data = json.loads(self.redis.get(key))
                # Convert list back to numpy array
                data['embedding'] = np.array(data['embedding'], dtype=np.float32)
                voiceprints.append(Voiceprint(**data))
            except KeyError:
                continue
            except json.JSONDecodeError:
                # Re-raise JSON decode errors to indicate data corruption
                raise
        return voiceprints

class SQLiteStorage:
    def __init__(self, db_path='voiceprints.db'):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS voiceprints (
                    caller_id TEXT PRIMARY KEY,
                    embedding BLOB,
                    metadata TEXT,
                    created_at TEXT,
                    last_seen TEXT
                )
            """)
    
    def save(self, voiceprint):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO voiceprints 
                (caller_id, embedding, metadata, created_at, last_seen) VALUES (?, ?, ?, ?, ?)
            """, (
                voiceprint.caller_id, 
                voiceprint.embedding.tobytes(), 
                json.dumps(voiceprint.metadata),
                voiceprint.created_at,
                voiceprint.last_seen
            ))
    
    def get_all(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM voiceprints")
            voiceprints = []
            for row in cursor.fetchall():
                try:
                    voiceprints.append(Voiceprint(
                        caller_id=row[0],
                        embedding=np.frombuffer(row[1], dtype=np.float32),
                        metadata=json.loads(row[2]) if row[2] else {},
                        created_at=row[3],
                        last_seen=row[4]
                    ))
                except (json.JSONDecodeError, ValueError):
                    continue
            return voiceprints
    
    def close(self):
        """Close the database connection and ensure file handle is released."""
        # Force a connection to ensure any pending writes are flushed
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA wal_checkpoint(FULL)")
            conn.execute("PRAGMA optimize")
            conn.commit()
            # Close all connections to this database
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            conn.commit() 