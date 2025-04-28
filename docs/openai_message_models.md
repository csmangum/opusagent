# OpenAI Realtime API Message Models

This document provides an overview of the message models used in the OpenAI Realtime API, including examples of how they're structured in JSON format.

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

## Conversation Items

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

## Client Events

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

### Audio Message Event

Creating a message with audio content:

```json
{
  "type": "conversation.item.create",
  "item": {
    "type": "message",
    "role": "user",
    "content": [
      {
        "type": "input_audio",
        "audio": "base64EncodedAudioDataHere..."
      }
    ]
  }
}
```

## Server Events

### ConversationItemCreatedEvent

Sent by the server when an item is created:

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
  }
}
```

### ResponseTextDeltaEvent

Sent by the server while generating text:

```json
{
  "type": "response.text.delta",
  "delta": "The"
}
```

### ResponseDoneEvent

Sent when the response is complete:

```json
{
  "type": "response.done"
}
```

## Function Calling

### Function Call Example

When the model wants to call a function:

```json
{
  "type": "response.done",
  "event_id": "event_AeqLA8iR6FK20L4XZs2P6",
  "response": {
    "object": "realtime.response",
    "id": "resp_AeqL8XwMUOri9OhcQJIu9",
    "status": "completed",
    "output": [
      {
        "object": "realtime.item",
        "id": "item_AeqL8gmRWDn9bIsUM2T35",
        "type": "function_call",
        "status": "completed",
        "name": "generate_horoscope",
        "call_id": "call_sHlR7iaFwQ2YQOqm",
        "arguments": "{\"sign\":\"Aquarius\"}"
      }
    ]
  }
}
```

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

## Legacy/Compatibility Models

### RealtimeTranscriptMessage

Used for speech transcription:

```json
{
  "type": "transcript",
  "text": "Hello, world!",
  "is_final": true,
  "confidence": 0.97
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