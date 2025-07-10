# MockTwilioClient - Twilio Bridge Validation

This document explains how to use the MockTwilioClient to validate the Twilio bridge and endpoint.

## Overview

The MockTwilioClient simulates a Twilio Media Streams WebSocket connection to test the integration between your Twilio bridge and the OpenAI Realtime API. It implements the complete Twilio Media Streams protocol and can conduct realistic conversation tests using both pre-recorded audio files and live microphone input.

## Features

- ✅ **Complete Twilio Protocol**: Implements all Twilio Media Streams message types
- ✅ **Audio Processing**: Handles μ-law audio conversion and streaming
- ✅ **Multi-turn Conversations**: Supports complex conversation flows
- ✅ **Live Microphone Input**: Real-time conversation using your microphone
- ✅ **Audio Collection**: Saves AI responses for analysis
- ✅ **DTMF Support**: Tests touch-tone input handling
- ✅ **Protocol Compliance**: Validates message formatting and timing

## Quick Start

### 1. Start the Server

First, start the OpusAgent server with your OpenAI API key:

```bash
# Set your OpenAI API key
export OPENAI_API_KEY="your-api-key-here"

# Start the server
python -m opusagent.main
```

The server will start on `http://localhost:8000` with the Twilio endpoint at `/twilio-agent`.

### 2. Live Conversation Test (NEW!)

For the most realistic testing experience, use the live conversation test:

```bash
# Test live conversation with your microphone
python scripts/test_live_conversation.py

# With verbose logging
python scripts/test_live_conversation.py --verbose
```

This will:
1. Connect to the bridge
2. Wait for the AI to greet you
3. Let you speak into your microphone
4. Send your voice to the AI and play back the response
5. Continue the conversation interactively

### 3. Run Validation Tests

Use the validation script for comprehensive testing:

```bash
# Run all validation tests (including live conversation)
python scripts/validate_twilio_bridge.py

# Run just the live conversation test
python scripts/validate_twilio_bridge.py --test live

# Run specific test
python scripts/validate_twilio_bridge.py --test single

# Run with verbose logging
python scripts/validate_twilio_bridge.py --verbose
```

### 4. Run Unit Tests

Use the pytest-based unit tests for file-based testing:

```bash
# Run all Twilio mock tests
python -m pytest tests/opusagent/test_twilio_mock.py -v

# Run specific test
python tests/opusagent/test_twilio_mock.py single
```

## Live Conversation Usage

The MockTwilioClient now supports real-time conversation using your microphone:

```python
import asyncio
from opusagent.mock.mock_twilio_client import MockTwilioClient

async def live_conversation_example():
    bridge_url = "ws://localhost:8000/twilio-agent"
    
    async with MockTwilioClient(bridge_url) as client:
        # Start live conversation
        result = await client.live_conversation()
        
        # Or use the simple wrapper
        success = await client.simple_live_conversation_test()
        
        # Save all collected audio
        client.save_collected_audio("conversation_recordings")

# Run the conversation
asyncio.run(live_conversation_example())
```

### Microphone Features

- **Real-time Streaming**: Audio is streamed directly from your microphone
- **Proper Format Conversion**: Automatically converts from 16kHz PCM to 8kHz μ-law
- **Interactive Control**: Press Enter to start/stop recording
- **Audio Quality**: Uses sounddevice for high-quality audio capture
- **Error Handling**: Graceful handling of microphone access issues

## Manual Testing

You can also use the MockTwilioClient directly in your code:

```python
import asyncio
from opusagent.mock.mock_twilio_client import MockTwilioClient

async def test_conversation():
    bridge_url = "ws://localhost:8000/twilio-agent"
    
    async with MockTwilioClient(bridge_url) as client:
        # Option 1: Use file-based audio
        await client.initiate_call_flow()
        greeting = await client.wait_for_ai_greeting()
        await client.send_user_audio("path/to/audio.wav")
        response = await client.wait_for_ai_response()
        
        # Option 2: Use live microphone
        await client.initiate_call_flow()
        greeting = await client.wait_for_ai_greeting()
        await client.stream_microphone_audio(duration=5.0)  # Record for 5 seconds
        response = await client.wait_for_ai_response()
        
        # Option 3: Full interactive conversation
        result = await client.live_conversation()
        
        # Save audio for analysis
        client.save_collected_audio("output_dir")

# Run the test
asyncio.run(test_conversation())
```

## Test Audio Files

The mock client can use the pre-generated audio files in `opusagent/mock/audio/`:

- `greetings/` - Various greeting audio files
- `customer_service/` - Customer service requests
- `card_replacement/` - Card replacement requests
- `confirmations/` - Confirmation responses
- `farewells/` - Goodbye messages

## Validation Results

The validation script will output:

- ✅ **Protocol Compliance**: Validates message format and flow
- ✅ **Single Turn**: Tests basic conversation with files
- ✅ **Multi Turn**: Tests complex conversations with files
- ✅ **Live Conversation**: Tests real-time microphone conversation
- 📊 **Audio Analysis**: Saves AI responses for quality analysis
- 📝 **Detailed Logs**: Comprehensive logging for debugging

## Troubleshooting

### Common Issues

1. **Connection Failed**: 
   - Ensure the server is running on the correct port
   - Check the bridge URL is correct (`ws://localhost:8000/twilio-agent`)

2. **No Audio Response**:
   - Verify your OpenAI API key is set and valid
   - Check that the OpenAI Realtime API is accessible
   - Ensure audio files exist and are in the correct format

3. **Microphone Issues**:
   - Check that your microphone is working and not muted
   - Ensure no other applications are using the microphone
   - Try running with `--verbose` to see detailed audio logs
   - Check microphone permissions in your OS

4. **Import Errors**:
   - Install required dependencies: `pip install -r requirements.txt`
   - Ensure you're running from the project root directory

### Debug Mode

Run with verbose logging to see detailed message flow:

```bash
python scripts/test_live_conversation.py --verbose
```

This will show:
- WebSocket connection details
- Message exchange logs
- Audio processing information
- Microphone recording status
- Timing and performance metrics

## Configuration

### Custom Bridge URL

```bash
python scripts/test_live_conversation.py --bridge-url ws://your-server:port/twilio-agent
```

### Custom Audio Settings

```python
# Use custom microphone settings
async with MockTwilioClient(bridge_url) as client:
    client.sample_rate = 44100  # Change sample rate
    
    # Stream for specific duration
    await client.stream_microphone_audio(duration=10.0)
    
    # Custom live conversation settings
    result = await client.live_conversation(
        wait_for_greeting=True,
        auto_detect_silence=True,
        silence_threshold=2.0
    )
```

## Integration with CI/CD

The validation script returns appropriate exit codes for CI/CD integration:

```bash
# In your CI/CD pipeline
python scripts/validate_twilio_bridge.py --test protocol
if [ $? -eq 0 ]; then
    echo "✅ Twilio bridge validation passed"
else
    echo "❌ Twilio bridge validation failed"
    exit 1
fi
```

Note: Live conversation tests are typically not suitable for CI/CD as they require interactive input.

## API Reference

### MockTwilioClient Methods

#### File-based Methods
- `initiate_call_flow()` - Start the Twilio call protocol
- `send_user_audio(file_path)` - Send audio file to the bridge
- `wait_for_ai_greeting(timeout)` - Wait for initial AI greeting
- `wait_for_ai_response(timeout)` - Wait for AI response to user input
- `multi_turn_conversation(audio_files)` - Conduct multi-turn conversation
- `save_collected_audio(output_dir)` - Save collected audio for analysis

#### Live Microphone Methods (NEW!)
- `start_microphone_recording()` - Start recording from microphone
- `stop_microphone_recording()` - Stop recording from microphone
- `stream_microphone_audio(duration)` - Stream microphone audio for specified duration
- `live_conversation()` - Full interactive conversation with microphone
- `simple_live_conversation_test()` - Simple wrapper for live conversation

#### Other Methods
- `send_dtmf(digit)` - Send DTMF tone

### Configuration Options

- `bridge_url` - WebSocket URL of the bridge
- `stream_sid` - Custom Twilio stream ID (optional)
- `account_sid` - Custom Twilio account ID (optional)  
- `call_sid` - Custom Twilio call ID (optional)
- `logger` - Custom logger instance (optional)
- `sample_rate` - Microphone sample rate (default: 16000)

## Next Steps

Once validation passes, your Twilio bridge is ready for production use with real Twilio Media Streams connections. The live conversation feature provides the most realistic testing experience and closely mimics how users will interact with your system in production. 

# 🎙️ Real-time Audio Streaming

## Overview

The MockTwilioClient now supports **real-time audio streaming** for natural conversations without recording. This feature streams microphone audio continuously in chunks directly to the bridge, creating a seamless conversation experience.

### Key Features

- **Continuous Streaming**: Audio is sent in real-time as 20ms chunks
- **Voice Activity Detection**: Automatically detects when user is speaking
- **No Recording**: Audio is streamed directly without saving to disk
- **Natural Flow**: Conversation feels like a real phone call
- **Configurable**: Adjustable voice threshold and silence timeout

## Real-time vs Interactive Methods

### 1. Real-time Streaming (Recommended)
- **Method**: `live_realtime_conversation()` or `simple_realtime_conversation_test()`
- **Audio Flow**: Microphone → Real-time chunks → Bridge
- **User Experience**: Natural conversation, microphone always live
- **Best For**: Production-like testing, natural conversation flow

### 2. Interactive Recording (Legacy)
- **Method**: `live_conversation()` or `simple_live_conversation_test()`
- **Audio Flow**: Microphone → Record → Send on Enter press
- **User Experience**: Press Enter to record, press Enter to send
- **Best For**: Controlled testing, debugging specific phrases

## Usage Examples

### Real-time Streaming

```python
import asyncio
from opusagent.mock.mock_twilio_client import MockTwilioClient

async def test_realtime():
    bridge_url = "ws://localhost:8000/twilio-agent"
    
    async with MockTwilioClient(bridge_url) as client:
        # Start real-time conversation
        result = await client.live_realtime_conversation(
            wait_for_greeting=True,
            voice_activation_threshold=0.01,  # Adjust sensitivity
            silence_timeout=2.0  # Seconds of silence before considering speech ended
        )
        
        if result["success"]:
            print(f"Conversation lasted {result.get('total_duration', 0):.1f} seconds")
            print(f"Sent {result.get('total_audio_chunks_sent', 0)} audio chunks")

# Run the test
asyncio.run(test_realtime())
```

### Simple Real-time Test

```python
async def simple_test():
    bridge_url = "ws://localhost:8000/twilio-agent"
    
    async with MockTwilioClient(bridge_url) as client:
        # One-line real-time conversation test
        success = await client.simple_realtime_conversation_test()
        print(f"Test {'passed' if success else 'failed'}")

asyncio.run(simple_test())
```

## Scripts

### Real-time Streaming Test

```bash
# Basic real-time streaming test
python scripts/test_realtime_streaming.py

# With custom settings
python scripts/test_realtime_streaming.py --voice-threshold 0.005 --silence-timeout 1.5

# Verbose logging
python scripts/test_realtime_streaming.py --verbose

# Skip instructions and start immediately
python scripts/test_realtime_streaming.py --no-instructions
```

### Validation Script

```bash
# Test real-time streaming specifically
python scripts/validate_twilio_bridge.py --test realtime

# Test interactive recording
python scripts/validate_twilio_bridge.py --test live

# Test both (part of full validation)
python scripts/validate_twilio_bridge.py --test all
```

## Audio Settings

### Voice Threshold
Controls sensitivity for voice activity detection:
- **0.001-0.005**: Very sensitive (quiet environments)
- **0.01**: Default (normal environments)
- **0.02-0.05**: Less sensitive (noisy environments)

### Silence Timeout
How long to wait before considering speech ended:
- **1.0-1.5s**: Fast response (may cut off speech)
- **2.0s**: Default (good balance)
- **3.0-5.0s**: Longer pauses (allows for thinking)

## Technical Details

### Audio Processing Pipeline

1. **Microphone Input**: 16kHz PCM audio from sounddevice
2. **Real-time Processing**: Audio processed in 20ms chunks
3. **Resampling**: 16kHz → 8kHz for Twilio compatibility
4. **Format Conversion**: PCM16 → μ-law encoding
5. **Streaming**: 160-byte chunks sent via WebSocket

### Voice Activity Detection

```python
def _calculate_audio_level(self, audio_bytes: bytes) -> float:
    """Calculate RMS audio level for voice detection."""
    audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
    rms = np.sqrt(np.mean(audio_array.astype(float) ** 2))
    return rms / 32767.0  # Normalize to 0-1
```

### Continuous Streaming Loop

```python
async def _continuous_audio_streaming(self):
    """Stream audio continuously in real-time."""
    while True:
        # Get audio from microphone queue
        audio_bytes = self.audio_queue.get_nowait()
        
        # Process and send
        resampled_audio = self._resample_pcm16(audio_bytes, 16000, 8000)
        mulaw_data = self._convert_pcm16_to_mulaw(resampled_audio)
        
        # Send as 20ms chunks
        for chunk in chunks(mulaw_data, 160):
            encoded_chunk = base64.b64encode(chunk).decode()
            await self.send_media_chunk(encoded_chunk)
```

## Troubleshooting

### Common Issues

1. **No audio detected**:
   - Check microphone permissions
   - Lower voice threshold: `--voice-threshold 0.005`
   - Verify microphone is not muted

2. **Audio cutting off**:
   - Increase silence timeout: `--silence-timeout 3.0`
   - Speak more continuously

3. **Poor audio quality**:
   - Ensure quiet environment
   - Check microphone quality
   - Verify no other apps using microphone

4. **AI not responding**:
   - Check bridge server is running
   - Verify OpenAI API key is valid
   - Look for errors in bridge logs

### Debug Mode

```bash
# Enable verbose logging for debugging
python scripts/test_realtime_streaming.py --verbose

# Check log files
tail -f realtime_test.log
```

## API Reference

### Real-time Methods

#### `live_realtime_conversation()`
```python
async def live_realtime_conversation(
    self,
    wait_for_greeting: bool = True,
    voice_activation_threshold: float = 0.01,
    silence_timeout: float = 2.0
) -> Dict[str, Any]
```

**Parameters**:
- `wait_for_greeting`: Wait for AI greeting before starting
- `voice_activation_threshold`: Voice detection sensitivity (0.001-0.1)
- `silence_timeout`: Silence duration before considering speech ended

**Returns**: Dictionary with conversation results and statistics

#### `simple_realtime_conversation_test()`
```python
async def simple_realtime_conversation_test(self) -> bool
```

**Returns**: True if conversation was successful, False otherwise

### Interactive Methods (Legacy)

#### `live_conversation()`
```python
async def live_conversation(
    self,
    wait_for_greeting: bool = True,
    auto_detect_silence: bool = True,
    silence_threshold: float = 2.0
) -> Dict[str, Any]
```

**Parameters**:
- `wait_for_greeting`: Wait for AI greeting
- `auto_detect_silence`: Enable automatic silence detection
- `silence_threshold`: Silence threshold for auto-detection

#### `simple_live_conversation_test()`
```python
async def simple_live_conversation_test(self) -> bool
```

**Returns**: True if conversation was successful

## Performance Metrics

Typical performance for real-time streaming:
- **Latency**: ~20-40ms (audio chunk processing)
- **Throughput**: ~50 chunks/second (1000 bytes/second)
- **CPU Usage**: Low (efficient numpy processing)
- **Memory**: Minimal (streaming, no buffering)

## Best Practices

1. **Environment**: Test in quiet environment for best results
2. **Hardware**: Use quality microphone for clear audio
3. **Settings**: Start with defaults, adjust based on testing
4. **Testing**: Use real-time streaming for production-like testing
5. **Debugging**: Use interactive recording for controlled testing 