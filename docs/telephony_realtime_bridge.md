# TelephonyRealtimeBridge

The `TelephonyRealtimeBridge` is a critical component in the FastAgent framework that enables real-time, bidirectional audio communication between telephony systems (using AudioCodes or similar telephony providers) and OpenAI's Realtime API. It serves as a communication pipeline that handles audio streaming, session management, speech detection, and event processing in both directions.

This bridge is designed for low-latency voice agent applications, allowing seamless transmission of audio between end-users (via telephony) and AI agents (via OpenAI), enabling natural, real-time conversations with voice-enabled AI assistants.

## Key Features

- **Bidirectional Audio Streaming**: Streams audio in real-time between telephony systems and OpenAI Realtime API
- **Session Management**: Handles the full lifecycle of a voice conversation, from initialization to termination
- **Event Processing**: Routes and processes events from both telephony and OpenAI systems
- **Speech Detection**: Monitors and reacts to speech start/stop events
- **Low Latency**: Designed for minimal processing overhead to maintain natural conversation flow
- **Stateful Communications**: Maintains conversation state throughout the session

## Architecture

The bridge connects two WebSocket endpoints:
1. **Telephony WebSocket** (typically AudioCodes VAIC): Handles the connection with the telephone/voice system
2. **OpenAI Realtime WebSocket**: Connects to OpenAI's Realtime API for AI-powered responses

```
Telephone User ⟷ Telephony System ⟷ TelephonyRealtimeBridge ⟷ OpenAI Realtime API ⟷ AI Model
```

## Message Models

The bridge uses strictly typed Pydantic models to ensure reliable message parsing and generation. These models represent the various message types exchanged with both the telephony system and OpenAI.

### AudioCodes API Models
Located in `fastagent/models/audiocodes_api.py`, these models represent the telephony protocol:

- **Session Management**:
  - `SessionInitiateMessage`: Initial request to start a conversation
  - `SessionAcceptedResponse`: Confirmation of session acceptance
  - `SessionEndMessage`: Request to terminate a session

- **Audio Streaming**:
  - `UserStreamStartMessage`: Signal to start receiving user audio
  - `UserStreamStartedResponse`: Confirmation of stream start
  - `UserStreamChunkMessage`: Audio data from the user
  - `UserStreamStopMessage`: Signal to stop receiving user audio
  - `UserStreamStoppedResponse`: Confirmation of stream stop
  
- **Playback**:
  - `PlayStreamStartMessage`: Start playing audio to the user
  - `PlayStreamChunkMessage`: Audio data sent to the user
  - `PlayStreamStopMessage`: Stop playing audio to the user

### OpenAI Realtime API Models
Located in `fastagent/models/openai_api.py`, these models represent the OpenAI Realtime protocol:

- **Session Management**:
  - `SessionConfig`: Configuration for the OpenAI session
  - `SessionUpdateEvent`: Update session settings
  - `SessionCreatedEvent`: Confirmation of session creation

- **Audio Input/Output**:
  - `InputAudioBufferAppendEvent`: Add audio to the input buffer
  - `InputAudioBufferCommitEvent`: Signal end of audio input
  - `ResponseAudioDeltaEvent`: Audio chunk from OpenAI's response

- **Response Management**:
  - `ResponseCreateEvent`: Start generating a response
  - `ResponseCreateOptions`: Configuration for response generation
  - `ResponseTextDeltaEvent`: Text chunk from OpenAI's response
  - `ResponseDoneEvent`: Signal completion of response

## Messaging Protocol

### Telephony Messages (AudioCodes API)
- `session.initiate`: Starts a new conversation session
- `userStream.start/chunk/stop`: Manages audio streaming from user
- `playStream.start/chunk/stop`: Manages audio streaming to user
- `session.end`: Terminates the conversation session

### OpenAI Realtime Messages
- `session.update/created`: Handles session configuration
- `input_audio_buffer.append/commit`: Manages incoming audio
- `response.audio.delta`: Streams AI-generated audio
- `response.text.delta`: Provides text transcripts
- `response.done`: Signals completion of AI response

## Usage

The bridge is typically instantiated and used within a FastAPI endpoint that handles WebSocket connections:

```python
# Example usage in a FastAPI application
from fastapi import FastAPI, WebSocket
import asyncio
import websockets
from fastagent.telephony_realtime_bridge import TelephonyRealtimeBridge

app = FastAPI()

@app.websocket("/voice-bot")
async def handle_call(telephony_websocket: WebSocket):
    """Handle WebSocket connections between telephony provider and OpenAI."""
    await telephony_websocket.accept()
    
    # Connect to OpenAI Realtime API
    async with websockets.connect(
        "wss://api.openai.com/v1/audio/realtime",
        extra_headers={"Authorization": f"Bearer {OPENAI_API_KEY}"}
    ) as realtime_websocket:
        # Create the bridge
        bridge = TelephonyRealtimeBridge(
            telephony_websocket=telephony_websocket,
            realtime_websocket=realtime_websocket
        )
        
        # Run both receive tasks concurrently
        try:
            await asyncio.gather(
                bridge.receive_from_telephony(),
                bridge.receive_from_realtime()
            )
        finally:
            # Always ensure proper cleanup
            await bridge.close()
```

## Call Flow

1. **Session Initialization**:
   - Telephony system sends `session.initiate` with conversation ID and media format
   - Bridge connects to OpenAI and initializes the session with configuration
   - OpenAI responds with `session.created`
   - Bridge confirms with `session.accepted` to telephony system

2. **User Speech**:
   - Telephony sends `userStream.start`
   - Audio chunks flow from telephony to OpenAI via the bridge
   - Telephony signals stream end with `userStream.stop`
   - Bridge commits the audio buffer to OpenAI

3. **AI Response**:
   - OpenAI processes the input and begins generating a response
   - Bridge receives text and audio deltas from OpenAI
   - Bridge streams audio back to telephony via `playStream` messages
   - OpenAI signals completion with `response.done`

4. **Session Termination**:
   - Telephony signals session end with `session.end`
   - Bridge closes connections to both systems

## Implementation Details

### Event Handlers

The bridge implements dedicated handlers for various events:

**Telephony Event Handlers:**
- `handle_session_initiate`: Processes new session requests
- `handle_user_stream_start/chunk/stop`: Manages incoming audio
- `handle_session_end`: Handles session termination

**OpenAI Event Handlers:**
- `handle_session_update`: Processes session configuration events
- `handle_speech_detection`: Manages speech detection events
- `handle_audio_response_delta`: Processes incoming audio from AI
- `handle_text_and_transcript`: Handles text responses and transcripts
- `handle_response_completion`: Manages response completion

### Error Handling

The bridge implements robust error handling for various failure scenarios:
- WebSocket disconnections
- Audio processing errors
- Session configuration issues
- Invalid message formats

### Performance Considerations

- **Minimal Processing**: The bridge performs minimal processing on audio data to maintain low latency
- **Efficient Event Routing**: Uses direct event handler mapping to minimize overhead
- **Graceful Shutdown**: Implements proper connection cleanup to prevent resource leaks

## Integration

This bridge component integrates with:
- FastAPI for HTTP/WebSocket routing
- Telephony systems implementing AudioCodes-compatible API
- OpenAI Realtime API for AI-powered conversations

## Requirements

- Python 3.9+
- FastAPI
- WebSockets support
- OpenAI API key with Realtime API access
- Telephony provider with WebSocket support (e.g., AudioCodes)

## Future Enhancements

- Multi-modal support (voice + image/video)
- Enhanced error recovery mechanisms
- Support for additional telephony providers
- Performance optimizations for high-volume deployments 