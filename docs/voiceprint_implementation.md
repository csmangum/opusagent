# Voiceprint Implementation

Voiceprint enables OpusAgent to identify returning callers and provide personalized experiences based on their voice characteristics. This feature uses speaker recognition technology to create unique voice embeddings and match them against stored profiles.

## Overview

Voiceprint provides:
- **Caller Identification**: Automatically recognize returning callers
- **Personalization**: Load caller-specific context and preferences
- **Cross-Session Memory**: Maintain conversation history across multiple calls
- **Enhanced UX**: Greet callers by name and reference previous interactions

## Architecture

### Core Components

```
opusagent/
├── voiceprint/
│   ├── __init__.py
│   ├── recognizer.py          # Main voice recognition engine
│   ├── storage.py             # Voiceprint storage backends
│   ├── models.py              # Pydantic models for voiceprints
│   ├── config.py              # Configuration settings
│   └── utils.py               # Audio processing utilities
```

### Integration Points

- **Call Start Handler**: Match caller voice on incoming calls
- **Memory System**: Load caller-specific context when match found
- **Session Management**: Associate sessions with caller IDs
- **Audio Pipeline**: Process audio streams for voice analysis

## Implementation

### Voice Recognition Engine

The core voice recognition uses Resemblyzer for lightweight, accurate speaker recognition:

```python
import numpy as np
from resemblyzer import VoiceEncoder, preprocess_wav
from scipy.spatial.distance import cosine

class OpusAgentVoiceRecognizer:
    def __init__(self, storage_backend=None):
        self.encoder = VoiceEncoder()
        self.storage = storage_backend or JSONStorage()
        self.config = VoiceFingerprintConfig()
    
    def get_embedding(self, audio_buffer):
        """Generate voice embedding from audio buffer."""
        wav = preprocess_wav(audio_buffer)
        embedding = self.encoder.embed_utterance(wav)
        return embedding
    
    def match_caller(self, audio_buffer):
        """Match incoming voice to stored voiceprints."""
        new_embedding = self.get_embedding(audio_buffer)
        
        matches = []
        for voiceprint in self.storage.get_all():
            similarity = 1 - cosine(new_embedding, voiceprint.embedding)
            if similarity > self.config.similarity_threshold:
                matches.append((voiceprint.caller_id, similarity, voiceprint.metadata))
        
        if matches:
            matches.sort(key=lambda x: x[1], reverse=True)
            return matches[0]  # (caller_id, similarity, metadata)
        return None
    
    def enroll_caller(self, caller_id, audio_buffer, metadata=None):
        """Enroll a new caller by storing their voiceprint."""
        embedding = self.get_embedding(audio_buffer)
        voiceprint = Voiceprint(
            caller_id=caller_id,
            embedding=embedding,
            metadata=metadata or {}
        )
        self.storage.save(voiceprint)
        return voiceprint
```

### Storage Backends

Multiple storage options for different deployment scenarios:

#### JSON Storage (Development)
```python
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
```

#### Redis Storage (Production)
```python
class RedisStorage:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def save(self, voiceprint):
        key = f"voiceprint:{voiceprint.caller_id}"
        self.redis.set(key, voiceprint.json())
    
    def get_all(self):
        keys = self.redis.keys("voiceprint:*")
        return [Voiceprint.parse_raw(self.redis.get(key)) for key in keys]
```

#### SQLite Storage (Embedded)
```python
class SQLiteStorage:
    def __init__(self, db_path='voiceprints.db'):
        self.db_path = db_path
        self._init_db()
    
    def save(self, voiceprint):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO voiceprints 
                (caller_id, embedding, metadata) VALUES (?, ?, ?)
            """, (voiceprint.caller_id, voiceprint.embedding.tobytes(), 
                  json.dumps(voiceprint.metadata)))
```

### Pydantic Models

```python
from pydantic import BaseModel
from typing import Dict, Any, Optional
import numpy as np

class Voiceprint(BaseModel):
    caller_id: str
    embedding: np.ndarray
    metadata: Dict[str, Any] = {}
    created_at: Optional[str] = None
    last_seen: Optional[str] = None
    
    class Config:
        arbitrary_types_allowed = True

class VoiceFingerprintConfig(BaseModel):
    similarity_threshold: float = 0.75
    enrollment_duration: float = 5.0  # seconds
    min_audio_quality: float = 0.6
    max_voiceprints_per_caller: int = 3
```

## Integration with OpusAgent

### Call Start Handler

Integrate voice fingerprinting into the call flow:

```python
# In opusagent/bridges/base_bridge.py
class BaseBridge:
    def __init__(self):
        self.voice_recognizer = OpusAgentVoiceRecognizer()
    
    async def handle_call_start(self, audio_stream):
        # Attempt to match caller voice
        match = self.voice_recognizer.match_caller(audio_stream)
        
        if match:
            caller_id, similarity, metadata = match
            # Load caller-specific context
            await self.load_caller_context(caller_id)
            return f"Welcome back, {metadata.get('name', 'caller')}!"
        else:
            # New caller - prompt for enrollment
            return "Hello! I don't recognize your voice. Would you like me to remember you for future calls?"
    
    async def load_caller_context(self, caller_id):
        """Load caller-specific memory and preferences."""
        # Load from session storage
        context = await self.session_manager.get_caller_context(caller_id)
        if context:
            self.agent.load_memory(context)
```

### Session Management Integration

```python
# In opusagent/session_manager.py
class SessionManager:
    def __init__(self):
        self.voice_recognizer = OpusAgentVoiceRecognizer()
    
    async def create_session(self, session_id, audio_stream=None):
        session = Session(session_id=session_id)
        
        if audio_stream:
            # Try to identify caller
            match = self.voice_recognizer.match_caller(audio_stream)
            if match:
                caller_id, similarity, metadata = match
                session.caller_id = caller_id
                session.caller_metadata = metadata
                # Load historical context
                await self.load_caller_history(caller_id, session)
        
        return session
    
    async def load_caller_history(self, caller_id, session):
        """Load caller's conversation history and preferences."""
        history = await self.storage.get_caller_history(caller_id)
        if history:
            session.context.update(history)
```

### Memory System Integration

```python
# In opusagent/text_audio_agent.py
class TextAudioAgent:
    def __init__(self):
        self.voice_recognizer = OpusAgentVoiceRecognizer()
        self.caller_memory = {}
    
    async def handle_audio_input(self, audio_buffer, session):
        # Voiceprint
        if not session.caller_id:
            match = self.voice_recognizer.match_caller(audio_buffer)
            if match:
                caller_id, similarity, metadata = match
                session.caller_id = caller_id
                session.caller_metadata = metadata
                await self.load_caller_memory(caller_id)
        
        # Continue with normal processing
        return await super().handle_audio_input(audio_buffer, session)
    
    async def load_caller_memory(self, caller_id):
        """Load caller-specific memory and preferences."""
        if caller_id not in self.caller_memory:
            # Load from persistent storage
            memory = await self.memory_storage.get_caller_memory(caller_id)
            self.caller_memory[caller_id] = memory
        
        # Apply caller-specific context
        self.apply_caller_context(self.caller_memory[caller_id])
```

## Configuration

### Environment Variables

```bash
# Voiceprint Configuration
VOICE_FINGERPRINTING_ENABLED=true
VOICE_SIMILARITY_THRESHOLD=0.75
VOICE_ENROLLMENT_DURATION=5.0
VOICE_STORAGE_BACKEND=json  # json, redis, sqlite
VOICE_STORAGE_PATH=voiceprints.json
VOICE_MIN_AUDIO_QUALITY=0.6
VOICE_MAX_VOICEPRINTS_PER_CALLER=3
```

### Configuration Class

```python
# In opusagent/voiceprint/config.py
class VoiceFingerprintConfig:
    def __init__(self):
        self.enabled = os.getenv('VOICE_FINGERPRINTING_ENABLED', 'true').lower() == 'true'
        self.similarity_threshold = float(os.getenv('VOICE_SIMILARITY_THRESHOLD', '0.75'))
        self.enrollment_duration = float(os.getenv('VOICE_ENROLLMENT_DURATION', '5.0'))
        self.storage_backend = os.getenv('VOICE_STORAGE_BACKEND', 'json')
        self.storage_path = os.getenv('VOICE_STORAGE_PATH', 'voiceprints.json')
        self.min_audio_quality = float(os.getenv('VOICE_MIN_AUDIO_QUALITY', '0.6'))
        self.max_voiceprints_per_caller = int(os.getenv('VOICE_MAX_VOICEPRINTS_PER_CALLER', '3'))
```

## Usage Examples

### Basic Integration

```python
# In opusagent/main.py
from opusagent.voiceprint import OpusAgentVoiceRecognizer

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    app.state.voice_recognizer = OpusAgentVoiceRecognizer()

@app.websocket("/ws/{bridge_type}")
async def websocket_endpoint(websocket: WebSocket, bridge_type: str):
    await websocket.accept()
    
    # Initialize bridge with voice recognition
    bridge = create_bridge(bridge_type, voice_recognizer=app.state.voice_recognizer)
    
    async for message in websocket.iter_text():
        await bridge.handle_message(message)
```

### Enrollment Flow

```python
# Example enrollment in a customer service scenario
async def handle_enrollment_request(session, audio_stream):
    """Handle caller requesting voice enrollment."""
    
    # Collect caller information
    caller_name = await get_caller_name(audio_stream)
    caller_id = generate_caller_id(caller_name)
    
    # Enroll the voiceprint
    voiceprint = voice_recognizer.enroll_caller(
        caller_id=caller_id,
        audio_buffer=audio_stream,
        metadata={'name': caller_name, 'enrolled_at': datetime.now().isoformat()}
    )
    
    # Store caller preferences
    await session_manager.store_caller_preferences(caller_id, {
        'preferred_greeting': 'formal',
        'language': 'en',
        'call_history': []
    })
    
    return f"Great! I'll remember your voice, {caller_name}. You can now call anytime and I'll recognize you."
```

### Personalized Responses

```python
# In opusagent/customer_service_agent.py
class CustomerServiceAgent:
    async def generate_greeting(self, session):
        """Generate personalized greeting based on caller identity."""
        if session.caller_id and session.caller_metadata:
            name = session.caller_metadata.get('name', 'there')
            last_call = session.caller_metadata.get('last_seen')
            
            if last_call:
                days_since = (datetime.now() - parse_datetime(last_call)).days
                if days_since == 0:
                    return f"Welcome back, {name}! How can I help you today?"
                elif days_since == 1:
                    return f"Good to hear from you again, {name}! What can I assist you with?"
                else:
                    return f"Welcome back, {name}! It's been {days_since} days since your last call. How can I help?"
            else:
                return f"Hello {name}! How can I assist you today?"
        else:
            return "Hello! How can I help you today?"
```

## Privacy and Security Considerations

### Data Protection

- **No Raw Audio Storage**: Only voice embeddings are stored, never raw audio
- **Encryption**: Voiceprint data should be encrypted at rest
- **Consent**: Always obtain explicit consent before enrollment
- **Deletion**: Provide easy way for users to delete their voiceprint
- **Compliance**: Follow GDPR, CCPA, and other privacy regulations

### Implementation

```python
class SecureVoiceRecognizer(OpusAgentVoiceRecognizer):
    def __init__(self, encryption_key=None):
        super().__init__()
        self.encryption_key = encryption_key or os.getenv('VOICE_ENCRYPTION_KEY')
    
    def _encrypt_embedding(self, embedding):
        """Encrypt voice embedding before storage."""
        if self.encryption_key:
            # Use Fernet or similar for encryption
            cipher = Fernet(self.encryption_key)
            return cipher.encrypt(embedding.tobytes())
        return embedding
    
    def _decrypt_embedding(self, encrypted_embedding):
        """Decrypt voice embedding for comparison."""
        if self.encryption_key:
            cipher = Fernet(self.encryption_key)
            decrypted = cipher.decrypt(encrypted_embedding)
            return np.frombuffer(decrypted, dtype=np.float32)
        return encrypted_embedding
```

## Testing

### Unit Tests

```python
# tests/opusagent/voiceprint/test_recognizer.py
import pytest
import numpy as np
from opusagent.voiceprint import OpusAgentVoiceRecognizer

class TestVoiceRecognizer:
    def test_enrollment_and_matching(self):
        recognizer = OpusAgentVoiceRecognizer()
        
        # Create test audio (simulated)
        test_audio = np.random.randn(16000 * 5)  # 5 seconds at 16kHz
        
        # Enroll caller
        voiceprint = recognizer.enroll_caller('test_user', test_audio)
        assert voiceprint.caller_id == 'test_user'
        
        # Match caller
        match = recognizer.match_caller(test_audio)
        assert match is not None
        assert match[0] == 'test_user'
        assert match[1] > 0.75  # Similarity threshold
    
    def test_no_match_for_different_voices(self):
        recognizer = OpusAgentVoiceRecognizer()
        
        # Enroll one voice
        voice1 = np.random.randn(16000 * 5)
        recognizer.enroll_caller('user1', voice1)
        
        # Try to match different voice
        voice2 = np.random.randn(16000 * 5)
        match = recognizer.match_caller(voice2)
        assert match is None
```

### Integration Tests

```python
# tests/opusagent/test_voiceprint_integration.py
class TestVoiceprintIntegration:
    async def test_call_with_voice_recognition(self):
        """Test full call flow with voiceprint."""
        agent = CustomerServiceAgent()
        session = Session(session_id='test_session')
        
        # Simulate incoming call with known caller
        audio_stream = create_test_audio_stream()
        response = await agent.handle_call_start(audio_stream, session)
        
        assert "Welcome back" in response
        assert session.caller_id is not None
```

## Performance Considerations

### Optimization Strategies

1. **Caching**: Cache frequently accessed voiceprints in memory
2. **Batch Processing**: Process multiple voiceprints in parallel
3. **Indexing**: Use FAISS for fast similarity search with large datasets
4. **Compression**: Compress embeddings for storage efficiency

### FAISS Integration

```python
import faiss

class FAISSVoiceStorage:
    def __init__(self):
        self.index = faiss.IndexFlatIP(256)  # 256-dim embeddings
        self.caller_ids = []
    
    def add_voiceprint(self, caller_id, embedding):
        self.index.add(embedding.reshape(1, -1))
        self.caller_ids.append(caller_id)
    
    def search_similar(self, query_embedding, k=5):
        similarities, indices = self.index.search(query_embedding.reshape(1, -1), k)
        return [(self.caller_ids[i], similarities[0][j]) 
                for j, i in enumerate(indices[0])]
```

## Future Enhancements

### Planned Features

1. **Multi-Voice Enrollment**: Store multiple voice samples per caller for better accuracy
2. **Voice Drift Adaptation**: Update voiceprints over time to handle aging
3. **Emotion Detection**: Combine voiceprint with emotion analysis
4. **Language-Specific Models**: Use language-specific voice recognition models
5. **Real-time Adaptation**: Continuously improve voiceprint accuracy during calls

### Advanced Use Cases

1. **Family Voice Recognition**: Identify family members calling from same number
2. **Voice Cloning Detection**: Detect and flag potential voice cloning attempts
3. **Health Monitoring**: Detect voice changes that might indicate health issues
4. **Access Control**: Use voiceprint for secure access to sensitive information

## Dependencies

### Required Packages

```bash
pip install resemblyzer scipy numpy pydantic
```

### Optional Dependencies

```bash
# For Redis storage
pip install redis

# For FAISS (high-performance similarity search)
pip install faiss-cpu  # or faiss-gpu for GPU acceleration

# For encryption
pip install cryptography
```

## Troubleshooting

### Common Issues

1. **Low Accuracy**: Adjust similarity threshold or use longer enrollment audio
2. **Memory Usage**: Use FAISS for large voiceprint databases
3. **Audio Quality**: Implement audio quality checks before processing
4. **False Positives**: Implement additional verification steps

### Debug Mode

```python
# Enable debug logging
import logging
logging.getLogger('opusagent.voiceprint').setLevel(logging.DEBUG)

# Test voiceprint quality
recognizer = OpusAgentVoiceRecognizer(debug=True)
```

## Conclusion

Voiceprint significantly enhances OpusAgent's personalization capabilities by enabling caller identification and context preservation across sessions. The implementation provides a solid foundation for building more sophisticated voice-based user experiences while maintaining privacy and security standards.

For production deployments, consider:
- Using Redis or database storage for scalability
- Implementing proper encryption and access controls
- Adding comprehensive logging and monitoring
- Regular testing with diverse voice samples
- Compliance with relevant privacy regulations 