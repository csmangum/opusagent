# MockTwilioClient - Testing Guide

This document explains how to use the `MockTwilioClient` to test your Twilio Media Streams bridge without needing actual phone calls.

## Overview

The `MockTwilioClient` simulates how Twilio Media Streams WebSocket protocol works, allowing you to test your `TwilioRealtimeBridge` implementation locally. It:

- Connects to your bridge server via WebSocket
- Sends properly formatted Twilio Media Streams messages
- Handles audio conversion (PCM16 ↔ mulaw)
- Collects and saves AI responses for analysis
- Supports multi-turn conversations

## Quick Start

### Basic Usage

```python
import asyncio
from mock_twilio_client import MockTwilioClient

async def test_basic_call():
    bridge_url = "ws://localhost:6060/twilio-ws"
    
    async with MockTwilioClient(bridge_url) as client:
        # Initiate Twilio call flow
        await client.initiate_call_flow()
        
        # Wait for AI greeting
        greeting = await client.wait_for_ai_greeting()
        
        # Send user audio
        await client.send_user_audio("test_audio.wav")
        
        # Wait for AI response
        response = await client.wait_for_ai_response()
        
        # End call
        await client.send_stop()
        
        # Save collected audio
        client.save_collected_audio()

asyncio.run(test_basic_call())
```

### Multi-turn Conversation

```python
async def test_conversation():
    bridge_url = "ws://localhost:6060/twilio-ws"
    audio_files = ["hello.wav", "question1.wav", "followup.wav"]
    
    async with MockTwilioClient(bridge_url) as client:
        result = await client.multi_turn_conversation(audio_files)
        
        if result["success"]:
            print(f"Completed {result['completed_turns']} turns")
        
        client.save_collected_audio()
```

## Twilio Protocol Flow

The MockTwilioClient follows the standard Twilio Media Streams protocol:

1. **Connected** - Initial connection established
2. **Start** - Stream metadata and configuration
3. **Media** - Audio chunks (base64-encoded mulaw)
4. **Stop** - End of stream
5. **DTMF** - Touch-tone digits (optional)
6. **Mark** - Audio playback completion markers

### Message Examples

**Connected Message:**
```json
{
  "event": "connected",
  "protocol": "Call",
  "version": "1.0.0"
}
```

**Start Message:**
```json
{
  "event": "start",
  "sequenceNumber": "1",
  "streamSid": "MZ...",
  "start": {
    "streamSid": "MZ...",
    "accountSid": "AC...",
    "callSid": "CA...",
    "tracks": ["inbound", "outbound"],
    "mediaFormat": {
      "encoding": "audio/x-mulaw",
      "sampleRate": 8000,
      "channels": 1
    }
  }
}
```

## Audio Format Requirements

### Input Audio (to Bridge)
- **Format**: mulaw, 8kHz, mono
- **Encoding**: Base64
- **Chunk Size**: 20ms (160 bytes)

### Output Audio (from Bridge)
- **Format**: mulaw, 8kHz, mono
- **Encoding**: Base64
- **Saved as**: PCM16 WAV files for analysis

## Testing Features

### 1. Protocol Compliance Testing
Tests that messages follow Twilio format:
```bash
python test_twilio_mock.py protocol
```

### 2. Single Turn Testing
Tests basic request-response flow:
```bash
python test_twilio_mock.py single
```

### 3. Multi-turn Conversations
Tests complex conversations:
```bash
python test_twilio_mock.py multi
```

### 4. DTMF and Marks
Tests touch-tone and audio markers:
```bash
python test_twilio_mock.py dtmf
```

### 5. Run All Tests
```bash
python test_twilio_mock.py
```

## Configuration Options

### Client Initialization
```python
client = MockTwilioClient(
    bridge_url="ws://localhost:6060/twilio-ws",
    stream_sid="MZ...",        # Auto-generated if not provided
    account_sid="AC...",       # Auto-generated if not provided  
    call_sid="CA...",          # Auto-generated if not provided
    logger=custom_logger       # Optional custom logger
)
```

### Conversation Parameters
```python
result = await client.multi_turn_conversation(
    audio_files=["file1.wav", "file2.wav"],
    wait_for_greeting=True,    # Wait for initial AI greeting
    turn_delay=2.0,           # Delay between turns (seconds)
    chunk_delay=0.02          # Delay between audio chunks (seconds)
)
```

## Audio File Requirements

### Supported Formats
- WAV files (PCM16)
- Mono or stereo (converted to mono)
- Any sample rate (resampled to 8kHz for Twilio)

### Example Audio Structure
```
demo/user_audio/
├── hello.wav          # "Hello, how are you?"
├── question1.wav      # "I need help with my account"
├── question2.wav      # "What's my balance?"
└── goodbye.wav        # "Thank you, goodbye"
```

## Output Files

The client saves collected audio to `validation_output/`:

```
validation_output/
├── twilio_greeting_MZ123456.wav     # AI greeting
├── twilio_response_MZ123456.wav     # Latest AI response
├── twilio_turn_01_response_MZ123456.wav  # Turn 1 response
├── twilio_turn_02_response_MZ123456.wav  # Turn 2 response
└── ...
```

## Common Issues

### 1. Connection Refused
```
Error: Connection refused to ws://localhost:6060/twilio-ws
```
**Solution**: Ensure your bridge server is running and the URL is correct.

### 2. No Audio Response
```
Error: No AI response received
```
**Solutions**:
- Check OpenAI API key configuration
- Verify bridge is connected to OpenAI Realtime API
- Check audio format compatibility

### 3. Audio Format Errors
```
Error: Invalid base64 encoded audio data
```
**Solutions**:
- Ensure WAV files are properly formatted
- Check file permissions
- Verify audio file isn't corrupted

## Advanced Usage

### Custom Audio Processing
```python
# Load and process audio manually
chunks = client._load_audio_as_mulaw_chunks("custom.wav", chunk_duration=0.02)

# Send chunks with custom timing
for chunk in chunks:
    await client.send_media_chunk(chunk)
    await asyncio.sleep(0.02)
```

### Monitoring Messages
```python
# Access all received messages
for msg in client.received_messages:
    print(f"Received: {msg.get('event')} - {msg}")

# Check received marks
print(f"Audio completion marks: {client.received_marks}")
```

### Custom Identifiers
```python
# Use specific Twilio identifiers for testing
client = MockTwilioClient(
    bridge_url="ws://localhost:6060/twilio-ws",
    stream_sid="MZtest123456789012345678901234567890",
    account_sid="ACtest123456789012345678901234567890",
    call_sid="CAtest123456789012345678901234567890"
)
```

## Integration with Testing Frameworks

### Pytest Integration
```python
import pytest
from mock_twilio_client import MockTwilioClient

@pytest.mark.asyncio
async def test_twilio_bridge():
    async with MockTwilioClient("ws://localhost:6060/twilio-ws") as client:
        success = await client.simple_conversation_test(["test.wav"])
        assert success
```

### Unit Testing
```python
import unittest
from unittest.mock import patch

class TestTwilioBridge(unittest.TestCase):
    def test_audio_conversion(self):
        client = MockTwilioClient("ws://test")
        # Test audio conversion methods
        pcm_data = b"\x00\x01" * 100
        mulaw_data = client._convert_pcm16_to_mulaw(pcm_data)
        self.assertIsInstance(mulaw_data, bytes)
```

This MockTwilioClient provides comprehensive testing capabilities for your Twilio Media Streams bridge, allowing you to verify functionality without needing real phone calls or Twilio infrastructure. 