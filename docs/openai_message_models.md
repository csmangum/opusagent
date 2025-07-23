# OpenAI Realtime API Message Models

This document provides a comprehensive overview of the message models used in the OpenAI Realtime API, including examples of how they're structured in JSON format. This documentation is based on the actual implementation in `opusagent/models/openai_api.py`.

## Table of Contents

1. [Basic Message Models](#basic-message-models)
2. [Session Configuration](#session-configuration)
3. [Conversation Items](#conversation-items)
4. [Function Calling Models](#function-calling-models)
5. [Client Events](#client-events)
6. [Server Events](#server-events)
7. [Audio and Transcription Events](#audio-and-transcription-events)
8. [Legacy/Compatibility Models](#legacycompatibility-models)

## Basic Message Models

### OpenAIMessage

The base model for OpenAI messages:

```json
{
  "role": "user",
  "content": "Hello, how are you today?"
}
```

Valid roles include: `system`, `user`, `assistant`, and `function`.

### MessageRole Enum

```python
class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"
```

## Session Configuration

### SessionConfig

Configuration for a Realtime API Session:

```json
{
  "modalities": ["text", "audio"],
  "model": "gpt-4o",
  "instructions": "You are a helpful assistant.",
  "voice": "alloy",
  "input_audio_format": "pcm16",
  "output_audio_format": "pcm16",
  "turn_detection": {"type": "server_vad"},
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "Get weather information",
        "parameters": {
          "type": "object",
          "properties": {
            "location": {"type": "string"}
          }
        }
      }
    }
  ],
  "tool_choice": "auto",
  "temperature": 0.7,
  "max_response_output_tokens": 4096,
  "input_audio_transcription": {
    "model": "whisper-1"
  },
  "input_audio_noise_reduction": {
    "enabled": true
  }
}
```

### ResponseCreateOptions

Options for creating a response (more restrictive than SessionConfig):

```json
{
  "modalities": ["text", "audio"],
  "voice": "alloy",
  "instructions": "You are a helpful assistant.",
  "output_audio_format": "pcm16",
  "tools": [...],
  "tool_choice": "auto",
  "temperature": 0.7,
  "max_output_tokens": 4096,
  "metadata": {
    "custom_field": "value"
  }
}
```

## Conversation Items

### ConversationItemType Enum

```python
class ConversationItemType(str, Enum):
    MESSAGE = "message"
    FUNCTION_CALL = "function_call"
    FUNCTION_CALL_OUTPUT = "function_call_output"
```

### ConversationItemStatus Enum

```python
class ConversationItemStatus(str, Enum):
    COMPLETED = "completed"
    IN_PROGRESS = "in_progress"
    INTERRUPTED = "interrupted"
```

### ConversationItemContentParam

Parameter for creating content in a conversation item:

```json
{
  "type": "input_text",
  "text": "What is my horoscope? I am an aquarius."
}
```

Or for audio:

```json
{
  "type": "input_audio",
  "audio": "base64EncodedAudioDataHere..."
}
```

### ConversationItemParam

Used when creating a new conversation item:

```json
{
  "type": "message",
  "role": "user",
  "content": [
    {
      "type": "input_text",
      "text": "What is my horoscope? I am an aquarius."
    }
  ]
}
```

### ConversationItem

Represents an item in the conversation:

```json
{
  "id": "item_AeqL8gmRWDn9bIsUM2T35",
  "object": "realtime.item",
  "type": "message",
  "status": "completed",
  "role": "user",
  "content": [
    {
      "type": "input_text",
      "text": "What is my horoscope? I am an aquarius."
    }
  ],
  "created_at": 1683901234
}
```

## Function Calling Models

### RealtimeFunctionCall

Function call structure in OpenAI Realtime API:

```json
{
  "name": "get_weather",
  "arguments": "{\"location\": \"New York\", \"unit\": \"celsius\"}"
}
```

### RealtimeFunctionCallOutput

Output from a function call:

```json
{
  "name": "get_weather",
  "output": "{\"temperature\": 22, \"condition\": \"sunny\"}"
}
```

## Client Events

### SessionUpdateEvent

Used to update session configuration:

```json
{
  "type": "session.update",
  "session": {
    "modalities": ["text", "audio"],
    "model": "gpt-4o",
    "voice": "alloy"
  }
}
```

### GetSessionConfigEvent

Used to retrieve current session configuration:

```json
{
  "type": "session.get_config"
}
```

### InputAudioBufferAppendEvent

Used to append audio to the input buffer:

```json
{
  "type": "input_audio_buffer.append",
  "audio": "base64EncodedAudioDataHere..."
}
```

### InputAudioBufferCommitEvent

Used to commit the audio buffer to the conversation:

```json
{
  "type": "input_audio_buffer.commit"
}
```

### InputAudioBufferClearEvent

Used to clear the audio buffer:

```json
{
  "type": "input_audio_buffer.clear"
}
```

### ConversationItemCreateEvent

Used to add a new message to the conversation:

```json
{
  "type": "conversation.item.create",
  "item": {
    "type": "message",
    "role": "user",
    "content": [
      {
        "type": "input_text",
        "text": "What is my horoscope? I am an aquarius."
      }
    ]
  }
}
```

### ConversationItemRetrieveEvent

Used to retrieve a conversation item:

```json
{
  "type": "conversation.item.retrieve",
  "item_id": "item_ABC123"
}
```

### ConversationItemTruncateEvent

Used to truncate a conversation item's content:

```json
{
  "type": "conversation.item.truncate",
  "item_id": "item_ABC123",
  "content_index": 0,
  "audio_end_ms": 5000
}
```

### ConversationItemDeleteEvent

Used to delete a conversation item:

```json
{
  "type": "conversation.item.delete",
  "item_id": "item_ABC123"
}
```

### ResponseCreateEvent

Used to create a model response:

```json
{
  "type": "response.create",
  "response": {
    "modalities": ["text", "audio"],
    "output_audio_format": "pcm16",
    "temperature": 0.7,
    "max_output_tokens": 4096,
    "voice": "alloy"
  }
}
```

### ResponseCancelEvent

Used to cancel an active model response:

```json
{
  "type": "response.cancel",
  "response_id": "resp_ABC123"
}
```

### TranscriptionSessionUpdateEvent

Used to update transcription session settings:

```json
{
  "type": "transcription_session.update",
  "session": {
    "model": "whisper-1"
  }
}
```

## Server Events

### ErrorEvent

Error message from OpenAI Realtime API:

```json
{
  "type": "error",
  "code": "invalid_value",
  "message": "Invalid parameter",
  "details": {
    "param": "voice"
  },
  "error": {
    "additional_info": "value"
  }
}
```

### SessionCreatedEvent

Sent when a session is created:

```json
{
  "type": "session.created",
  "session": {
    "modalities": ["text", "audio"],
    "model": "gpt-4o",
    "voice": "alloy"
  }
}
```

### SessionUpdatedEvent

Sent when session configuration is updated:

```json
{
  "type": "session.updated",
  "session": {
    "modalities": ["text", "audio"],
    "model": "gpt-4o"
  }
}
```

### SessionConfigEvent

Sent in response to session.get_config:

```json
{
  "type": "session.config",
  "session": {
    "modalities": ["text", "audio"],
    "model": "gpt-4o"
  }
}
```

### ConversationCreatedEvent

Sent when a conversation is created:

```json
{
  "type": "conversation.created",
  "conversation": {
    "id": "conv_ABC123"
  }
}
```

### ConversationItemCreatedEvent

Sent when an item is created:

```json
{
  "type": "conversation.item.created",
  "item": {
    "id": "item_ABC123",
    "object": "realtime.item",
    "type": "message",
    "status": "completed",
    "role": "user",
    "content": [
      {
        "type": "input_text",
        "text": "What's the weather like?"
      }
    ],
    "created_at": 1683901234
  },
  "previous_item_id": "item_PREV123"
}
```

### ConversationItemRetrievedEvent

Sent in response to conversation.item.retrieve:

```json
{
  "type": "conversation.item.retrieved",
  "item": {
    "id": "item_ABC123",
    "object": "realtime.item",
    "type": "message",
    "status": "completed",
    "role": "user",
    "content": [...],
    "created_at": 1683901234
  }
}
```

### ConversationItemTruncatedEvent

Sent when an item is truncated:

```json
{
  "type": "conversation.item.truncated",
  "item_id": "item_ABC123",
  "content_index": 0,
  "audio_end_ms": 5000
}
```

### ConversationItemDeletedEvent

Sent when an item is deleted:

```json
{
  "type": "conversation.item.deleted",
  "item_id": "item_ABC123"
}
```

### InputAudioBufferCommittedEvent

Sent when audio buffer is committed:

```json
{
  "type": "input_audio_buffer.committed",
  "item_id": "item_ABC123",
  "previous_item_id": "item_PREV123"
}
```

### InputAudioBufferClearedEvent

Sent when audio buffer is cleared:

```json
{
  "type": "input_audio_buffer.cleared"
}
```

### InputAudioBufferSpeechStartedEvent

Sent when speech is detected:

```json
{
  "type": "input_audio_buffer.speech_started",
  "audio_start_ms": 1000,
  "item_id": "item_ABC123"
}
```

### InputAudioBufferSpeechStoppedEvent

Sent when speech stops:

```json
{
  "type": "input_audio_buffer.speech_stopped",
  "audio_end_ms": 5000,
  "item_id": "item_ABC123"
}
```

### ResponseCreatedEvent

Sent when a response is created:

```json
{
  "type": "response.created",
  "response": {
    "id": "resp_ABC123",
    "status": "in_progress"
  }
}
```

### ResponseDoneEvent

Sent when response is complete:

```json
{
  "type": "response.done",
  "response": {
    "id": "resp_ABC123",
    "status": "completed"
  }
}
```

### ResponseCancelledEvent

Sent when response is cancelled:

```json
{
  "type": "response.cancelled",
  "response_id": "resp_ABC123"
}
```

### ResponseTextDeltaEvent

Sent during text generation:

```json
{
  "type": "response.text.delta",
  "response_id": "resp_ABC123",
  "item_id": "item_ABC123",
  "output_index": 0,
  "content_index": 0,
  "delta": "The"
}
```

### ResponseTextDoneEvent

Sent when text generation is complete:

```json
{
  "type": "response.text.done",
  "response_id": "resp_ABC123",
  "item_id": "item_ABC123",
  "output_index": 0,
  "content_index": 0,
  "text": "The weather is sunny today."
}
```

### ResponseFunctionCallArgumentsDeltaEvent

Sent during function call generation:

```json
{
  "type": "response.function_call_arguments.delta",
  "response_id": "resp_ABC123",
  "item_id": "item_ABC123",
  "output_index": 0,
  "call_id": "call_ABC123",
  "delta": "{\"location\":"
}
```

### ResponseFunctionCallArgumentsDoneEvent

Sent when function call arguments are complete:

```json
{
  "type": "response.function_call_arguments.done",
  "response_id": "resp_ABC123",
  "item_id": "item_ABC123",
  "output_index": 0,
  "call_id": "call_ABC123",
  "arguments": "{\"location\": \"New York\", \"unit\": \"celsius\"}"
}
```

### RateLimitsUpdatedEvent

Sent when rate limits are updated:

```json
{
  "type": "rate_limits.updated",
  "rate_limits": [
    {
      "type": "requests",
      "limit": 100,
      "remaining": 95,
      "reset": 1683901234
    }
  ]
}
```

### ResponseOutputItemAddedEvent

Sent when a new output item is added:

```json
{
  "type": "response.output_item.added",
  "response_id": "resp_ABC123",
  "output_index": 0,
  "item": {
    "id": "item_ABC123",
    "type": "function_call",
    "status": "in_progress"
  }
}
```

### ResponseOutputItemDoneEvent

Sent when an output item is complete:

```json
{
  "type": "response.output_item.done",
  "response_id": "resp_ABC123",
  "output_index": 0,
  "item": {
    "id": "item_ABC123",
    "type": "function_call",
    "status": "completed"
  }
}
```

### ResponseContentPartDoneEvent

Sent when a content part is completed:

```json
{
  "type": "response.content_part.done",
  "response_id": "resp_ABC123",
  "item_id": "item_ABC123",
  "output_index": 0,
  "content_index": 0,
  "part_id": "part_ABC123",
  "status": "completed",
  "part": {
    "type": "text",
    "text": "The weather is sunny."
  }
}
```

### ResponseContentPartAddedEvent

Sent when a new content part is added:

```json
{
  "type": "response.content_part.added",
  "response_id": "resp_ABC123",
  "item_id": "item_ABC123",
  "output_index": 0,
  "content_index": 0,
  "part": {
    "type": "text",
    "text": "The weather is sunny."
  }
}
```

## Audio and Transcription Events

### ResponseAudioDeltaEvent

Sent during audio generation:

```json
{
  "type": "response.audio.delta",
  "response_id": "resp_ABC123",
  "item_id": "item_ABC123",
  "output_index": 0,
  "content_index": 0,
  "delta": "base64EncodedAudioChunk..."
}
```

### ResponseAudioDoneEvent

Sent when audio generation is complete:

```json
{
  "type": "response.audio.done",
  "response_id": "resp_ABC123",
  "item_id": "item_ABC123",
  "output_index": 0,
  "content_index": 0
}
```

### ResponseAudioTranscriptDeltaEvent

Sent during audio transcript generation:

```json
{
  "type": "response.audio_transcript.delta",
  "response_id": "resp_ABC123",
  "item_id": "item_ABC123",
  "output_index": 0,
  "content_index": 0,
  "delta": "The weather"
}
```

### ResponseAudioTranscriptDoneEvent

Sent when audio transcript is complete:

```json
{
  "type": "response.audio_transcript.done",
  "response_id": "resp_ABC123",
  "item_id": "item_ABC123",
  "output_index": 0,
  "content_index": 0,
  "transcript": "The weather is sunny today."
}
```

### ConversationItemInputAudioTranscriptionCompletedEvent

Sent when input audio transcription is complete:

```json
{
  "type": "conversation.item.input_audio_transcription.completed",
  "item_id": "item_ABC123",
  "content_index": 0,
  "transcript": "What's the weather like?",
  "logprobs": [
    {
      "token": "What",
      "logprob": -0.1
    }
  ]
}
```

### ConversationItemInputAudioTranscriptionDeltaEvent

Sent during input audio transcription:

```json
{
  "type": "conversation.item.input_audio_transcription.delta",
  "item_id": "item_ABC123",
  "content_index": 0,
  "delta": "What's",
  "logprobs": [
    {
      "token": "What",
      "logprob": -0.1
    }
  ]
}
```

### ConversationItemInputAudioTranscriptionFailedEvent

Sent when input audio transcription fails:

```json
{
  "type": "conversation.item.input_audio_transcription.failed",
  "item_id": "item_ABC123",
  "content_index": 0,
  "error": {
    "code": "transcription_failed",
    "message": "Audio quality too poor"
  }
}
```

### TranscriptionSessionUpdatedEvent

Sent when transcription session is updated:

```json
{
  "type": "transcription_session.updated",
  "session": {
    "model": "whisper-1",
    "language": "en"
  }
}
```

## Function Calling Examples

### Function Call Output

Sending function output back to the model:

```json
{
  "type": "conversation.item.create",
  "item": {
    "type": "function_call_output",
    "call_id": "call_sHlR7iaFwQ2YQOqm",
    "output": "{\"horoscope\": \"You will soon meet a new friend.\"}"
  }
}
```

### Function Call in Response

When the model wants to call a function, it appears in the response output:

```json
{
  "type": "response.output_item.added",
  "response_id": "resp_ABC123",
  "output_index": 0,
  "item": {
    "id": "item_ABC123",
    "type": "function_call",
    "status": "in_progress",
    "name": "generate_horoscope",
    "call_id": "call_sHlR7iaFwQ2YQOqm"
  }
}
```

## Legacy/Compatibility Models

### RealtimeTranscriptMessage

Used for speech transcription:

```json
{
  "type": "transcript",
  "text": "Hello, world!",
  "final": true,
  "created_at": 1683901234
}
```

### RealtimeErrorMessage

Used to indicate errors:

```json
{
  "type": "error",
  "code": "invalid_value",
  "message": "Invalid parameter",
  "details": {
    "param": "voice"
  }
}
```

### RealtimeTurnMessage

Used for turn detection:

```json
{
  "type": "turn",
  "action": "start",
  "created_at": 1683901234
}
```

### RealtimeMessage

Message model for OpenAI Realtime API:

```json
{
  "type": "message",
  "role": "user",
  "content": "Hello, how are you?",
  "name": null,
  "function_call": null,
  "created_at": 1683901234
}
```

### RealtimeStreamMessage

Stream message from OpenAI Realtime API:

```json
{
  "type": "stream",
  "content": "Hello, how are you?",
  "role": "assistant",
  "end": false,
  "created_at": 1683901234
}
```

### RealtimeFunctionMessage

Function message for OpenAI Realtime API:

```json
{
  "type": "function",
  "function": {
    "name": "get_weather",
    "arguments": "{\"location\": \"New York\"}"
  },
  "created_at": 1683901234
}
```

### WebSocketErrorResponse

Error response for WebSocket errors:

```json
{
  "error": "connection_failed",
  "message": "Failed to establish WebSocket connection"
}
```

## Event Type Enums

### ClientEventType

```python
class ClientEventType(str, Enum):
    SESSION_UPDATE = "session.update"
    GET_SESSION_CONFIG = "session.get_config"
    INPUT_AUDIO_BUFFER_APPEND = "input_audio_buffer.append"
    INPUT_AUDIO_BUFFER_COMMIT = "input_audio_buffer.commit"
    INPUT_AUDIO_BUFFER_CLEAR = "input_audio_buffer.clear"
    CONVERSATION_ITEM_CREATE = "conversation.item.create"
    CONVERSATION_ITEM_RETRIEVE = "conversation.item.retrieve"
    CONVERSATION_ITEM_TRUNCATE = "conversation.item.truncate"
    CONVERSATION_ITEM_DELETE = "conversation.item.delete"
    RESPONSE_CREATE = "response.create"
    RESPONSE_CANCEL = "response.cancel"
    TRANSCRIPTION_SESSION_UPDATE = "transcription_session.update"
```

### ServerEventType

```python
class ServerEventType(str, Enum):
    ERROR = "error"
    SESSION_CREATED = "session.created"
    SESSION_UPDATED = "session.updated"
    SESSION_CONFIG = "session.config"
    CONVERSATION_CREATED = "conversation.created"
    CONVERSATION_ITEM_CREATED = "conversation.item.created"
    CONVERSATION_ITEM_RETRIEVED = "conversation.item.retrieved"
    CONVERSATION_ITEM_TRUNCATED = "conversation.item.truncated"
    CONVERSATION_ITEM_DELETED = "conversation.item.deleted"
    INPUT_AUDIO_BUFFER_COMMITTED = "input_audio_buffer.committed"
    INPUT_AUDIO_BUFFER_CLEARED = "input_audio_buffer.cleared"
    INPUT_AUDIO_BUFFER_SPEECH_STARTED = "input_audio_buffer.speech_started"
    INPUT_AUDIO_BUFFER_SPEECH_STOPPED = "input_audio_buffer.speech_stopped"
    RESPONSE_CREATED = "response.created"
    RESPONSE_DONE = "response.done"
    RESPONSE_CANCELLED = "response.cancelled"
    RESPONSE_TEXT_DELTA = "response.text.delta"
    RESPONSE_TEXT_DONE = "response.text.done"
    RESPONSE_AUDIO_DELTA = "response.audio.delta"
    RESPONSE_AUDIO_DONE = "response.audio.done"
    RESPONSE_AUDIO_TRANSCRIPT_DELTA = "response.audio_transcript.delta"
    RESPONSE_AUDIO_TRANSCRIPT_DONE = "response.audio_transcript.done"
    RESPONSE_FUNCTION_CALL_ARGUMENTS_DELTA = "response.function_call_arguments.delta"
    RESPONSE_FUNCTION_CALL_ARGUMENTS_DONE = "response.function_call_arguments.done"
    RATE_LIMITS_UPDATED = "rate_limits.updated"
    RESPONSE_OUTPUT_ITEM_ADDED = "response.output_item.added"
    RESPONSE_OUTPUT_ITEM_DONE = "response.output_item.done"
    RESPONSE_CONTENT_PART_DONE = "response.content_part.done"
    RESPONSE_CONTENT_PART_ADDED = "response.content_part.added"
    CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_COMPLETED = "conversation.item.input_audio_transcription.completed"
    CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_DELTA = "conversation.item.input_audio_transcription.delta"
    CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_FAILED = "conversation.item.input_audio_transcription.failed"
    TRANSCRIPTION_SESSION_UPDATED = "transcription_session.updated"
```

## Usage Notes

1. **Base64 Audio**: All audio data should be base64 encoded
2. **Timestamps**: All timestamps are Unix timestamps in seconds
3. **Event IDs**: Optional event IDs can be included for correlation
4. **Error Handling**: Most errors are recoverable and the session stays open
5. **Streaming**: Text, audio, and function calls are streamed via delta events
6. **VAD**: Voice Activity Detection can be client-side or server-side
7. **Transcription**: Input audio transcription runs asynchronously with response generation

This documentation reflects the actual implementation in the codebase and should be kept up to date with any changes to the models. 