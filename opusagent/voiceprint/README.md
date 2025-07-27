# Voiceprint Module

A comprehensive voice recognition and caller identification system for OpusAgent that uses voice fingerprinting to identify callers based on their unique vocal characteristics.

## Overview

The voiceprint module provides speaker identification capabilities through voice fingerprinting technology. It uses the Resemblyzer library to generate voice embeddings that capture the unique characteristics of a caller's voice, enabling automatic caller identification and personalized interactions.

## Key Features

- **Speaker Identification**: Identify callers based on voice characteristics
- **Voice Enrollment**: Register new callers with voice samples
- **Multiple Storage Backends**: JSON, Redis, and SQLite storage options
- **Configurable Thresholds**: Adjustable similarity matching parameters
- **Audio Quality Control**: Minimum quality requirements for voiceprint processing
- **Metadata Storage**: Associate additional caller information with voiceprints
- **Production Ready**: Robust error handling and performance optimization

## Installation

### Dependencies

The module requires the following Python packages:

```bash
pip install resemblyzer numpy scipy pydantic redis
```

For SQLite storage (default Python installation includes sqlite3).

### Optional Dependencies

- **Redis**: Required only if using RedisStorage backend
- **SQLite**: Included with Python standard library

## Quick Start

### Basic Usage

```python
from opusagent.voiceprint import OpusAgentVoiceRecognizer
import numpy as np

# Initialize the voice recognizer
recognizer = OpusAgentVoiceRecognizer()

# Enroll a new caller
audio_data = np.array([...])  # Your audio data as numpy array
voiceprint = recognizer.enroll_caller(
    caller_id="john_doe",
    audio_buffer=audio_data,
    metadata={"name": "John Doe", "phone": "555-1234"}
)

# Identify an incoming caller
incoming_audio = np.array([...])  # New audio sample
result = recognizer.match_caller(incoming_audio)

if result:
    caller_id, similarity, metadata = result
    print(f"Caller identified: {caller_id} (similarity: {similarity:.2f})")
    print(f"Metadata: {metadata}")
else:
    print("Unknown caller")
```

### Using Different Storage Backends

```python
from opusagent.voiceprint import OpusAgentVoiceRecognizer
from opusagent.voiceprint.storage import RedisStorage, SQLiteStorage
import redis

# JSON Storage (default)
recognizer = OpusAgentVoiceRecognizer()

# Redis Storage
redis_client = redis.Redis(host='localhost', port=6379, db=0)
redis_storage = RedisStorage(redis_client)
recognizer = OpusAgentVoiceRecognizer(storage_backend=redis_storage)

# SQLite Storage
sqlite_storage = SQLiteStorage("voiceprints.db")
recognizer = OpusAgentVoiceRecognizer(storage_backend=sqlite_storage)
```

## Configuration

The module can be configured through environment variables or by modifying the `VoiceFingerprintConfig` class:

### Environment Variables

```bash
# Enable/disable voice fingerprinting
VOICE_FINGERPRINTING_ENABLED=true

# Similarity threshold for caller matching (0.0-1.0)
VOICE_SIMILARITY_THRESHOLD=0.75

# Required audio duration for enrollment (seconds)
VOICE_ENROLLMENT_DURATION=5.0

# Storage backend: 'json', 'redis', or 'sqlite'
VOICE_STORAGE_BACKEND=json

# Storage file path (for JSON/SQLite)
VOICE_STORAGE_PATH=voiceprints.json

# Minimum audio quality score (0.0-1.0)
VOICE_MIN_AUDIO_QUALITY=0.6

# Maximum voiceprints per caller
VOICE_MAX_VOICEPRINTS_PER_CALLER=3
```

### Programmatic Configuration

```python
from opusagent.voiceprint.config import VoiceFingerprintConfig

config = VoiceFingerprintConfig()
config.similarity_threshold = 0.8
config.enrollment_duration = 10.0
config.min_audio_quality = 0.7
```

## API Reference

### OpusAgentVoiceRecognizer

The main class for voice recognition operations.

#### Methods

##### `__init__(storage_backend=None)`
Initialize the voice recognizer with optional storage backend.

##### `enroll_caller(caller_id, audio_buffer, metadata=None)`
Enroll a new caller with their voiceprint.

**Parameters:**
- `caller_id` (str): Unique identifier for the caller
- `audio_buffer` (np.ndarray): Raw audio data
- `metadata` (dict, optional): Additional caller information

**Returns:** `Voiceprint` object

##### `match_caller(audio_buffer)`
Match incoming voice against stored voiceprints.

**Parameters:**
- `audio_buffer` (np.ndarray): Raw audio data from incoming call

**Returns:** `(caller_id, similarity, metadata)` tuple or `None` if no match

##### `get_embedding(audio_buffer)`
Generate voice embedding from audio buffer.

**Parameters:**
- `audio_buffer` (np.ndarray): Raw audio data

**Returns:** `np.ndarray` voice embedding

### Storage Classes

#### JSONStorage
File-based storage using JSON format.

```python
from opusagent.voiceprint.storage import JSONStorage

storage = JSONStorage("my_voiceprints.json")
```

#### RedisStorage
Redis-backed storage for high-performance applications.

```python
from opusagent.voiceprint.storage import RedisStorage
import redis

redis_client = redis.Redis(host='localhost', port=6379, db=0)
storage = RedisStorage(redis_client)
```

#### SQLiteStorage
SQLite database storage with ACID compliance.

```python
from opusagent.voiceprint.storage import SQLiteStorage

storage = SQLiteStorage("voiceprints.db")
```

### Data Models

#### Voiceprint
Represents a single voiceprint with caller identification data.

**Attributes:**
- `caller_id` (str): Unique caller identifier
- `embedding` (np.ndarray): Voice characteristics as numerical vector
- `metadata` (dict): Additional caller information
- `created_at` (str, optional): Creation timestamp
- `last_seen` (str, optional): Last usage timestamp

#### VoiceFingerprintConfig
Configuration settings for voice recognition.

**Attributes:**
- `similarity_threshold` (float): Minimum similarity for matching (default: 0.75)
- `enrollment_duration` (float): Required audio duration in seconds (default: 5.0)
- `min_audio_quality` (float): Minimum audio quality score (default: 0.6)
- `max_voiceprints_per_caller` (int): Maximum voiceprints per caller (default: 3)

## Storage Backends

### JSON Storage
- **Use Case**: Development, small datasets, portable storage
- **Pros**: Simple, human-readable, no external dependencies
- **Cons**: Not suitable for high-volume production use

### Redis Storage
- **Use Case**: High-performance production applications
- **Pros**: Fast in-memory access, persistence, clustering support
- **Cons**: Requires Redis server, additional infrastructure

### SQLite Storage
- **Use Case**: Medium-scale applications, ACID compliance needed
- **Pros**: Zero-configuration, ACID transactions, efficient queries
- **Cons**: Single-writer limitation, not suitable for high-concurrency

## Audio Requirements

### Supported Formats
- Raw audio as numpy arrays
- Sample rate: 16kHz recommended
- Bit depth: 16-bit or higher
- Channels: Mono preferred

### Quality Guidelines
- Minimum duration: 3-5 seconds for enrollment
- Clean audio with minimal background noise
- Consistent recording conditions for best results
- Avoid heavily processed or compressed audio

## Error Handling

The module includes comprehensive error handling for common scenarios:

- **Invalid audio data**: Validates input format and quality
- **Storage errors**: Graceful handling of storage backend failures
- **Matching failures**: Proper handling of no-match scenarios
- **Configuration errors**: Validation of configuration parameters

## Performance Considerations

### Memory Usage
- Voice embeddings are compact (typically 256 dimensions)
- In-memory storage scales linearly with number of enrolled callers
- Consider Redis for large-scale deployments

### Processing Speed
- Embedding generation: ~100ms per 5-second audio sample
- Matching speed: Linear with number of stored voiceprints
- Use appropriate similarity thresholds to balance accuracy vs. speed

## Security Notes

- Voiceprint embeddings are one-way transformations (cannot reconstruct original audio)
- Store sensitive metadata separately if required
- Consider encryption for stored voiceprint data in production
- Implement access controls for voiceprint enrollment/management

## Troubleshooting

### Common Issues

**Low matching accuracy:**
- Increase audio quality requirements
- Ensure consistent recording conditions
- Adjust similarity threshold
- Use longer enrollment samples

**Storage errors:**
- Check file permissions for JSON/SQLite storage
- Verify Redis connectivity for Redis storage
- Monitor disk space for file-based storage

**Performance issues:**
- Consider Redis storage for large datasets
- Implement voiceprint pruning for old/unused entries
- Use appropriate similarity thresholds

## Examples

### Advanced Usage

```python
# Custom configuration
from opusagent.voiceprint import OpusAgentVoiceRecognizer, VoiceFingerprintConfig
from opusagent.voiceprint.storage import SQLiteStorage

# Configure for high-security application
config = VoiceFingerprintConfig(
    similarity_threshold=0.85,  # Higher threshold for better security
    enrollment_duration=10.0,   # Longer enrollment for better accuracy
    min_audio_quality=0.8       # Higher quality requirements
)

# Use SQLite for ACID compliance
storage = SQLiteStorage("secure_voiceprints.db")
recognizer = OpusAgentVoiceRecognizer(storage_backend=storage)

# Enroll with detailed metadata
voiceprint = recognizer.enroll_caller(
    caller_id="customer_12345",
    audio_buffer=enrollment_audio,
    metadata={
        "name": "Jane Smith",
        "phone": "+1-555-0123",
        "account_type": "premium",
        "security_level": "high",
        "enrollment_date": "2024-01-15"
    }
)

# Batch processing for multiple callers
def process_enrollment_batch(enrollments):
    results = []
    for caller_id, audio_data, metadata in enrollments:
        try:
            voiceprint = recognizer.enroll_caller(caller_id, audio_data, metadata)
            results.append(("success", caller_id, voiceprint))
        except Exception as e:
            results.append(("error", caller_id, str(e)))
    return results
```

## Contributing

When contributing to the voiceprint module:

1. Ensure all new features include comprehensive docstrings
2. Add unit tests for new functionality
3. Update this README for significant changes
4. Follow the existing code style and patterns
5. Consider backward compatibility for API changes

## License

This module is part of the OpusAgent project. See the main project LICENSE file for details. 