# FastAgent API Documentation

## Overview

FastAgent provides a comprehensive API for building low-latency, stateful voice agents using Agentic Finite State Machines (AFSM). This document covers the core components, endpoints, and integration patterns for developers working with the FastAgent framework.

## Core Components

### 1. WebSocket API

FastAgent exposes its primary functionality through WebSocket endpoints for real-time bidirectional communication.

#### Connection Endpoint

```
ws://{server-address}/agent/ws
```

This WebSocket endpoint handles:
- Initial connection establishment
- Session management
- Audio streaming
- State transitions
- Event notifications

#### Authentication

```python
# Connection with authentication headers
websocket = await websockets.connect(
    "ws://localhost:8000/agent/ws",
    extra_headers={
        "Authorization": f"Bearer {API_KEY}",
        "X-Session-ID": session_id
    }
)
```

#### Message Format

All WebSocket messages follow a standard JSON format:

```json
{
  "type": "message_type",
  "payload": {
    // Message-specific data
  },
  "session_id": "unique_session_identifier",
  "timestamp": 1624282543
}
```

### 2. HTTP REST API

In addition to WebSockets, FastAgent provides HTTP endpoints for configuration and management.

#### Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "latency_metrics": {
    "avg_ms": 120,
    "min_ms": 80,
    "max_ms": 250,
    "p95_ms": 180,
    "p99_ms": 220
  },
  "active_connections": 5,
  "uptime_seconds": 3600
}
```

#### Agent Configuration

```
POST /agents/{agent_id}/config
```

Request body:
```json
{
  "states": [
    {
      "name": "greeting",
      "description": "Initial greeting state",
      "allowed_transitions": ["collect_info", "handle_query"],
      "prompt_template": "You are a helpful voice assistant greeting a customer."
    },
    {
      "name": "collect_info",
      "description": "Collecting user information",
      "allowed_transitions": ["process_info", "greeting"],
      "prompt_template": "Collect the user's name and reason for calling."
    }
  ],
  "initial_state": "greeting",
  "scratchpad_enabled": true,
  "llm_config": {
    "model": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 150
  }
}
```

#### Session Management

```
GET /sessions
```

Response:
```json
{
  "active_sessions": [
    {
      "session_id": "sess_123456",
      "start_time": "2023-06-20T15:30:45Z",
      "current_state": "collect_info",
      "duration_seconds": 120,
      "turn_count": 5
    },
    // More sessions...
  ],
  "total_count": 5
}
```

```
DELETE /sessions/{session_id}
```

Response:
```json
{
  "success": true,
  "message": "Session terminated successfully"
}
```

## Message Types

### Client to Server

| Message Type | Description | Payload Example |
|--------------|-------------|-----------------|
| `start_session` | Initiates a new conversation | `{"agent_id": "retail_agent", "metadata": {"caller_id": "+1234567890"}}` |
| `audio_data` | Sends audio chunk for processing | `{"format": "audio/x-wav", "encoding": "base64", "data": "base64_audio_data", "chunk_id": 42}` |
| `dtmf` | Sends DTMF tones | `{"digits": "1234"}` |
| `end_session` | Terminates the session | `{"reason": "user_hangup"}` |

### Server to Client

| Message Type | Description | Payload Example |
|--------------|-------------|-----------------|
| `session_started` | Confirms session creation | `{"session_id": "sess_123456", "initial_state": "greeting"}` |
| `audio_response` | Returns synthesized speech | `{"format": "audio/x-wav", "encoding": "base64", "data": "base64_audio_data", "final": false}` |
| `state_transition` | Notifies of state change | `{"from_state": "greeting", "to_state": "collect_info", "reason": "user_provided_info"}` |
| `session_ended` | Confirms session termination | `{"reason": "completed", "duration_seconds": 145}` |

## AFSM State API

### Defining Custom States

States are defined by extending the base `AFSMState` class:

```python
from fastagent.afsm import AFSMState

class GreetingState(AFSMState):
    """Initial greeting state that welcomes callers."""
    
    def __init__(self):
        super().__init__(
            name="greeting",
            description="Welcomes the user and identifies their needs",
            allowed_transitions=["collect_info", "handle_query"]
        )
    
    async def process(self, input_text, context):
        """Process user input in this state."""
        # Access scratchpad for reasoning
        self.scratchpad = f"User said: {input_text}\nI should greet them and identify their needs."
        
        # Generate response using the state-specific logic
        response = await self._generate_response(input_text, context)
        
        # Determine next state
        next_state = self._determine_next_state(input_text, response)
        
        return {
            "response": response,
            "next_state": next_state,
            "confidence": 0.95
        }
    
    def _determine_next_state(self, input_text, response):
        """Determine the next state based on input and response."""
        if "help" in input_text.lower() or "question" in input_text.lower():
            return "handle_query"
        else:
            return "collect_info"
```

### Context Management

Context is managed through the `ConversationContext` class:

```python
from fastagent.context import ConversationContext

# Initialize a new context
context = ConversationContext(max_history=10)

# Update context with new information
context.update_context(
    user_utterance="I need to check my account balance",
    agent_response="I can help you check your account balance. Can you please verify your identity?",
    state="identity_verification"
)

# Add a salient fact
context.add_salient_fact("account_type", "checking")

# Update user profile
context.update_user_profile({
    "authentication_status": "pending",
    "last_interaction": "2023-06-20T15:45:30Z"
})
```

## Telephony Integration

### Integrating with AudioCodes

FastAgent provides built-in support for AudioCodes VoiceAI Connect:

```python
from fastagent.telephony import AudiocodesConnector

# Initialize connector
audiocodes = AudiocodesConnector(
    webhook_url="https://your-server.com/audiocodes/webhook",
    api_key="your_audiocodes_api_key"
)

# Register agent with connector
await audiocodes.register_agent(
    agent_id="retail_agent",
    phone_number="+18005551234"
)

# Start listening for calls
await audiocodes.start()
```

### Integrating with Twilio

```python
from fastagent.telephony import TwilioConnector

# Initialize connector
twilio = TwilioConnector(
    account_sid="your_twilio_account_sid",
    auth_token="your_twilio_auth_token",
    webhook_url="https://your-server.com/twilio/webhook"
)

# Register agent with connector
await twilio.register_agent(
    agent_id="support_agent",
    phone_number="+18005551235"
)

# Start listening for calls
await twilio.start()
```

## Deployment

### Docker Container

FastAgent can be deployed as a Docker container:

```bash
# Build the Docker image
docker build -t fastagent:latest .

# Run the container
docker run -d -p 8000:8000 \
  -e OPENAI_API_KEY=your_openai_api_key \
  -e LOG_LEVEL=INFO \
  fastagent:latest
```

### Docker Compose

For more complex deployments with additional services:

```yaml
# docker-compose.yml
version: '3'
services:
  fastagent:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=your_openai_api_key
      - LOG_LEVEL=INFO
    restart: always
    depends_on:
      - redis
  
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: always

volumes:
  redis_data:
```

## Monitoring and Logging

### Prometheus Metrics

FastAgent exposes Prometheus metrics at `/metrics`:

```
# HELP fastagent_active_sessions Current number of active voice sessions
# TYPE fastagent_active_sessions gauge
fastagent_active_sessions 5

# HELP fastagent_session_duration_seconds Session duration in seconds
# TYPE fastagent_session_duration_seconds histogram
fastagent_session_duration_seconds_bucket{le="10.0"} 2
fastagent_session_duration_seconds_bucket{le="30.0"} 8
fastagent_session_duration_seconds_bucket{le="60.0"} 15
fastagent_session_duration_seconds_bucket{le="120.0"} 25
fastagent_session_duration_seconds_bucket{le="300.0"} 35
fastagent_session_duration_seconds_bucket{le="+Inf"} 42
fastagent_session_duration_seconds_sum 4285.5
fastagent_session_duration_seconds_count 42

# HELP fastagent_latency_milliseconds Response latency in milliseconds
# TYPE fastagent_latency_milliseconds histogram
fastagent_latency_milliseconds_bucket{le="50.0"} 120
fastagent_latency_milliseconds_bucket{le="100.0"} 450
fastagent_latency_milliseconds_bucket{le="200.0"} 780
fastagent_latency_milliseconds_bucket{le="500.0"} 950
fastagent_latency_milliseconds_bucket{le="+Inf"} 1000
fastagent_latency_milliseconds_sum 124500.0
fastagent_latency_milliseconds_count 1000
```

### Logging

FastAgent uses structured logging:

```json
{
  "timestamp": "2023-06-20T15:45:30.123Z",
  "level": "INFO",
  "message": "Session started",
  "session_id": "sess_123456",
  "agent_id": "retail_agent",
  "caller_id": "+1234567890",
  "initial_state": "greeting"
}
```

## Error Handling

### WebSocket Error Responses

When errors occur, the server sends error messages:

```json
{
  "type": "error",
  "payload": {
    "code": "invalid_audio_format",
    "message": "Unsupported audio format: audio/mp3",
    "details": "Only audio/x-wav is supported"
  },
  "session_id": "sess_123456",
  "timestamp": 1624282543
}
```

### Common Error Codes

| Error Code | Description |
|------------|-------------|
| `invalid_request` | The request format is invalid |
| `authentication_failed` | Authentication failed |
| `session_not_found` | The requested session does not exist |
| `invalid_state` | The requested state transition is not allowed |
| `audio_processing_failed` | Failed to process audio data |
| `llm_error` | Error from the language model |
| `internal_error` | Internal server error |

## Advanced Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Port to run the server on | `8000` |
| `HOST` | Host to bind the server to | `0.0.0.0` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `MAX_SESSIONS` | Maximum concurrent sessions | `100` |
| `DEFAULT_TIMEOUT_SECONDS` | Default timeout for requests | `30` |
| `WEBSOCKET_PING_INTERVAL` | WebSocket ping interval in seconds | `5` |
| `REDIS_URL` | Redis connection URL for session storage | `redis://localhost:6379/0` |

## Examples

### Complete Integration Example

```python
from fastagent import FastAgent, AFSMState, ConversationContext

# Define custom states
class GreetingState(AFSMState):
    # State implementation...

class CollectInfoState(AFSMState):
    # State implementation...

class ProcessInfoState(AFSMState):
    # State implementation...

# Initialize FastAgent
agent = FastAgent(
    agent_id="customer_service",
    states=[
        GreetingState(),
        CollectInfoState(),
        ProcessInfoState()
    ],
    initial_state="greeting",
    llm_config={
        "model": "gpt-4",
        "temperature": 0.7
    }
)

# Start the agent
await agent.start()
```

## Conclusion

This documentation provides an overview of the FastAgent API. For more detailed information, code examples, and best practices, refer to the [GitHub repository](https://github.com/yourusername/fastagent) and the extensive documentation in the `/docs` directory. 