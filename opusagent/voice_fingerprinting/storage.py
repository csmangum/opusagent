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
        voiceprints[voiceprint.caller_id] = voiceprint.dict()
        self._save_all(voiceprints)
    
    def get_all(self):
        voiceprints = self._load_all()
        return [Voiceprint(**vp) for vp in voiceprints.values()]

    def _load_all(self):
        try:
            with open(self.file_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def _save_all(self, voiceprints):
        with open(self.file_path, 'w') as f:
            json.dump(voiceprints, f)

class RedisStorage:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def save(self, voiceprint):
        key = f"voiceprint:{voiceprint.caller_id}"
        self.redis.set(key, voiceprint.json())
    
    def get_all(self):
        keys = self.redis.keys("voiceprint:*")
        return [Voiceprint.parse_raw(self.redis.get(key)) for key in keys]

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
                    metadata TEXT
                )
            """)
    
    def save(self, voiceprint):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO voiceprints 
                (caller_id, embedding, metadata) VALUES (?, ?, ?)
            """, (voiceprint.caller_id, voiceprint.embedding.tobytes(), 
                  json.dumps(voiceprint.metadata)))
    
    def get_all(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM voiceprints")
            return [Voiceprint(
                caller_id=row[0],
                embedding=np.frombuffer(row[1], dtype=np.float32),
                metadata=json.loads(row[2])
            ) for row in cursor.fetchall()] 