# AudioCodes VoiceAI Connect Enterprise Message Models

This document provides an overview of the message models used in the AudioCodes Bot API WebSocket protocol, including examples of how they're structured in JSON format.

## Base Message Structure

All messages share a common base structure:

```json
{
  "type": "message_type",
  "conversationId": "12345678-1234-1234-1234-123456789012",
  "participant": "caller"
}
```

**Note:** The `participant` field is optional and used in Agent Assist mode to indicate which participant (e.g., "caller") the message refers to.

## Session Messages

### SessionInitiateMessage

Sent by AudioCodes to initiate a new session:

```json
{
  "type": "session.initiate",
  "conversationId": "12345678-1234-1234-1234-123456789012",
  "expectAudioMessages": true,
  "botName": "CustomerService",
  "caller": "+12025550123",
  "supportedMediaFormats": ["raw/lpcm16", "audio/wav"]
}
```

### SessionResumeMessage

Sent by AudioCodes to resume a previously paused session:

```json
{
  "type": "session.resume",
  "conversationId": "12345678-1234-1234-1234-123456789012"
}
```

### SessionResumedMessage

Sent by AudioCodes to confirm session resumption:

```json
{
  "type": "session.resumed",
  "conversationId": "12345678-1234-1234-1234-123456789012"
}
```

### SessionEndMessage

Sent by AudioCodes to end a session:

```json
{
  "type": "session.end",
  "conversationId": "12345678-1234-1234-1234-123456789012",
  "reasonCode": "user_hangup",
  "reason": "User ended the call"
}
```

### SessionAcceptedResponse

Sent to AudioCodes to accept a session:

```json
{
  "type": "session.accepted",
  "conversationId": "12345678-1234-1234-1234-123456789012",
  "mediaFormat": "raw/lpcm16"
}
```

### SessionErrorResponse

Sent to AudioCodes to reject a session:

```json
{
  "type": "session.error",
  "conversationId": "12345678-1234-1234-1234-123456789012",
  "reason": "Service unavailable"
}
```

## User Stream Messages

### UserStreamStartMessage

Sent by AudioCodes to indicate the start of user audio:

```json
{
  "type": "userStream.start",
  "conversationId": "12345678-1234-1234-1234-123456789012",
  "participant": "caller"
}
```

### UserStreamChunkMessage

Sent by AudioCodes with chunks of audio data:

```json
{
  "type": "userStream.chunk",
  "conversationId": "12345678-1234-1234-1234-123456789012",
  "participant": "caller",
  "audioChunk": "base64EncodedAudioDataHere..."
}
```

### UserStreamStopMessage

Sent by AudioCodes to indicate the end of user audio:

```json
{
  "type": "userStream.stop",
  "conversationId": "12345678-1234-1234-1234-123456789012",
  "participant": "caller"
}
```

### UserStreamStartedResponse

Sent to AudioCodes to acknowledge the start of user audio:

```json
{
  "type": "userStream.started",
  "conversationId": "12345678-1234-1234-1234-123456789012",
  "participant": "caller"
}
```

### UserStreamStoppedResponse

Sent to AudioCodes to acknowledge the end of user audio:

```json
{
  "type": "userStream.stopped",
  "conversationId": "12345678-1234-1234-1234-123456789012",
  "participant": "caller"
}
```

## Speech Recognition Messages

### UserStreamHypothesisResponse

Sent to AudioCodes with speech recognition hypotheses (interim results):

```json
{
  "type": "userStream.speech.hypothesis",
  "conversationId": "12345678-1234-1234-1234-123456789012",
  "participant": "caller",
  "alternatives": [
    {
      "text": "I'd like to check my account balance",
      "confidence": "0.95"
    },
    {
      "text": "I'd like to check my current balance",
      "confidence": "0.87"
    }
  ]
}
```

### UserStreamRecognitionResponse

Sent to AudioCodes with final speech recognition results:

```json
{
  "type": "userStream.speech.recognition",
  "conversationId": "12345678-1234-1234-1234-123456789012",
  "participant": "caller",
  "alternatives": [
    {
      "text": "I'd like to check my account balance",
      "confidence": 0.95
    }
  ]
}
```

## Voice Activity Detection (VAD) Messages

### UserStreamSpeechStartedResponse

Sent to AudioCodes to indicate speech detection started:

```json
{
  "type": "userStream.speech.started",
  "conversationId": "12345678-1234-1234-1234-123456789012",
  "participantId": "caller"
}
```

### UserStreamSpeechStoppedResponse

Sent to AudioCodes to indicate speech detection stopped:

```json
{
  "type": "userStream.speech.stopped",
  "conversationId": "12345678-1234-1234-1234-123456789012",
  "participantId": "caller"
}
```

### UserStreamSpeechCommittedResponse

Sent to AudioCodes to indicate speech was committed for processing:

```json
{
  "type": "userStream.speech.committed",
  "conversationId": "12345678-1234-1234-1234-123456789012",
  "participantId": "caller"
}
```

## Play Stream Messages

### PlayStreamStartMessage

Sent to AudioCodes to start audio playback:

```json
{
  "type": "playStream.start",
  "conversationId": "12345678-1234-1234-1234-123456789012",
  "streamId": "stream_1234567890",
  "mediaFormat": "raw/lpcm16",
  "altText": "Optional alternative text for logging"
}
```

### PlayStreamChunkMessage

Sent to AudioCodes with chunks of audio data to play:

```json
{
  "type": "playStream.chunk",
  "conversationId": "12345678-1234-1234-1234-123456789012",
  "streamId": "stream_1234567890",
  "audioChunk": "base64EncodedAudioDataHere..."
}
```

### PlayStreamStopMessage

Sent to AudioCodes to stop audio playback:

```json
{
  "type": "playStream.stop",
  "conversationId": "12345678-1234-1234-1234-123456789012",
  "streamId": "stream_1234567890"
}
```

## Activity Messages

### ActivitiesMessage

Used to communicate events like DTMF input or call hangup:

```json
{
  "type": "activities",
  "conversationId": "12345678-1234-1234-1234-123456789012",
  "activities": [
    {
      "type": "event",
      "name": "dtmf",
      "value": "5",
      "id": "582bbc43-0ef7-47e9-97b4-1e6141625b01",
      "timestamp": "2022-07-20T07:15:48.239Z",
      "language": "en-US"
    }
  ]
}
```

Example of hangup activity:

```json
{
  "type": "activities",
  "conversationId": "12345678-1234-1234-1234-123456789012",
  "activities": [
    {
      "type": "event",
      "name": "hangup",
      "id": "582bbc43-0ef7-47e9-97b4-1e6141625b01",
      "timestamp": "2022-07-20T07:15:48.239Z"
    }
  ]
}
```

Example of call start activity:

```json
{
  "type": "activities",
  "conversationId": "12345678-1234-1234-1234-123456789012",
  "activities": [
    {
      "type": "event",
      "name": "start",
      "id": "582bbc43-0ef7-47e9-97b4-1e6141625b01",
      "timestamp": "2022-07-20T07:15:48.239Z",
      "language": "en-US",
      "parameters": {
        "locale": "en-US",
        "caller": "caller-id",
        "callee": "my_bot_name"
      }
    }
  ]
}
```

## Connection Messages

### ConnectionValidateMessage

Sent by AudioCodes to validate the connection:

```json
{
  "type": "connection.validate",
  "conversationId": "12345678-1234-1234-1234-123456789012"
}
```

### ConnectionValidatedResponse

Sent to AudioCodes to confirm validation:

```json
{
  "type": "connection.validated",
  "conversationId": "12345678-1234-1234-1234-123456789012",
  "success": true
}
```

## Supported Media Formats

The AudioCodes VoiceAI Connect Enterprise supports the following media formats:

- `raw/mulaw` - Mu-Law encoded (8 bit, 8 kHz) without a header
- `wav/mulaw` - Mu-Law encoded (8 bit, 8 kHz) with a WAV header
- `raw/lpcm16` - Linear PCM (16 bit, 16 kHz) without a header
- `wav/lpcm16` - Linear PCM (16 bit, 16 kHz) with a WAV header
- `raw/lpcm16_8` - Linear PCM (16 bit, 8 kHz) without a header
- `wav/lpcm16_8` - Linear PCM (16 bit, 8 kHz) with a WAV header
- `raw/lpcm16_24` - Linear PCM (16 bit, 24 kHz) without a header (VAIC-E-3.24.1+)
- `wav/lpcm16_24` - Linear PCM (16 bit, 24 kHz) with a WAV header (VAIC-E-3.24.1+)

## Message Flow

### Typical Session Flow

1. **Connection Validation** (optional)
   - `connection.validate` → `connection.validated`

2. **Session Initiation**
   - `session.initiate` → `session.accepted` or `session.error`

3. **Audio Streaming**
   - `userStream.start` → `userStream.started`
   - `userStream.chunk` (multiple)
   - `userStream.stop` → `userStream.stopped`

4. **Speech Recognition** (optional)
   - `userStream.speech.hypothesis` (interim results)
   - `userStream.speech.recognition` (final results)

5. **Voice Activity Detection** (optional)
   - `userStream.speech.started`
   - `userStream.speech.stopped`
   - `userStream.speech.committed`

6. **Audio Playback**
   - `playStream.start` → `playStream.chunk` (multiple) → `playStream.stop`

7. **Session End**
   - `session.end`

### Session Resume Flow

1. **Session Resume**
   - `session.resume` → `session.accepted` → `session.resumed`

### Activity Events

Activities can occur at any time during the session:
- DTMF input: `activities` with `name: "dtmf"`
- Call hangup: `activities` with `name: "hangup"`
- Call start: `activities` with `name: "start"` 