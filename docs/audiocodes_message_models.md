# AudioCodes VoiceAI Connect Enterprise Message Models

This document provides an overview of the message models used in the AudioCodes Bot API WebSocket protocol, including examples of how they're structured in JSON format.

## Base Message Structure

All messages share a common base structure:

```json
{
  "type": "message_type",
  "conversationId": "12345678-1234-1234-1234-123456789012"
}
```

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
  "conversationId": "12345678-1234-1234-1234-123456789012"
}
```

### UserStreamChunkMessage

Sent by AudioCodes with chunks of audio data:

```json
{
  "type": "userStream.chunk",
  "conversationId": "12345678-1234-1234-1234-123456789012",
  "audioChunk": "base64EncodedAudioDataHere..."
}
```

### UserStreamStopMessage

Sent by AudioCodes to indicate the end of user audio:

```json
{
  "type": "userStream.stop",
  "conversationId": "12345678-1234-1234-1234-123456789012"
}
```

### UserStreamStartedResponse

Sent to AudioCodes to acknowledge the start of user audio:

```json
{
  "type": "userStream.started",
  "conversationId": "12345678-1234-1234-1234-123456789012"
}
```

### UserStreamStoppedResponse

Sent to AudioCodes to acknowledge the end of user audio:

```json
{
  "type": "userStream.stopped",
  "conversationId": "12345678-1234-1234-1234-123456789012"
}
```

### UserStreamHypothesisResponse

Sent to AudioCodes with speech recognition hypotheses:

```json
{
  "type": "userStream.speech.hypothesis",
  "conversationId": "12345678-1234-1234-1234-123456789012",
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

## Play Stream Messages

### PlayStreamStartMessage

Sent to AudioCodes to start audio playback:

```json
{
  "type": "playStream.start",
  "conversationId": "12345678-1234-1234-1234-123456789012",
  "streamId": "stream_1234567890",
  "mediaFormat": "raw/lpcm16"
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
      "value": "5"
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
      "name": "hangup"
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