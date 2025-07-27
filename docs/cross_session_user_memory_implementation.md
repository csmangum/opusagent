# Cross-Session User Memory Implementation

Cross-session user memory enables OpusAgent to maintain persistent context across multiple calls or sessions for the same user, allowing personalized experiences based on historical interactions. This feature builds on the existing session management system to aggregate and summarize data from past sessions, which can be injected into new sessions as initial context.

## Overview

Cross-session memory provides:
- **Persistent Context**: Recall summaries of previous conversations, preferences, and key facts.
- **Personalization**: Tailor responses based on user history (e.g., greet by name, reference past issues).
- **User Identification**: Integrate with caller ID or voice fingerprinting for accurate matching.
- **Efficiency**: Store concise summaries to avoid data bloat while enabling long-term recall.

This ties into the roadmap's voice fingerprinting feature (see [voiceprint_implementation.md](voiceprint_implementation.md)) for robust identification beyond caller ID.

## Architecture

### Core Components

```
opusagent/
├── user_memory/
│   ├── __init__.py
│   ├── manager.py             # Main user memory management
│   ├── storage.py             # User profile storage backends
│   ├── models.py              # Pydantic models for user profiles
│   ├── summarizer.py          # Session summarization logic
│   ├── config.py              # Configuration settings
│   └── utils.py               # Helper utilities
```

### Integration Points

- **Session Manager**: Extend to handle user profiles on session start/end.
- **Bridges**: Inject user context during conversation initialization.
- **Agents**: Use loaded memory for personalized responses.
- **Voice Fingerprinting**: Reference for advanced user ID matching.

## Implementation

### User Memory Manager

The core manager handles profile creation, updates, and retrieval:

```python
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import openai  # For summarization
from datetime import datetime

class UserProfile(BaseModel):
    user_id: str
    summaries: List[Dict[str, Any]] = []  # List of session summaries
    preferences: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}
    last_updated: Optional[str] = None

class UserMemoryManager:
    def __init__(self, storage_backend=None):
        self.storage = storage_backend or RedisStorage()
        self.config = UserMemoryConfig()
    
    async def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """Retrieve user profile by ID."""
        return await self.storage.retrieve(user_id)
    
    async def update_profile(self, user_id: str, session_summary: Dict[str, Any], preferences: Optional[Dict[str, Any]] = None):
        """Update profile with new session summary."""
        profile = await self.get_profile(user_id) or UserProfile(user_id=user_id)
        profile.summaries.append(session_summary)
        if preferences:
            profile.preferences.update(preferences)
        profile.last_updated = datetime.now().isoformat()
        await self.storage.store(profile)
    
    async def summarize_session(self, conversation_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate concise summary using OpenAI."""
        prompt = f"Summarize this conversation for future reference: {conversation_history}"
        response = await openai.ChatCompletion.acreate(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}])
        return {"summary": response.choices[0].message.content, "timestamp": datetime.now().isoformat()}
```

### Storage Backends

Extend existing session storage for user profiles:

#### Redis Storage Extension
```python
from opusagent.session_storage.redis_storage import RedisSessionStorage

class UserRedisStorage(RedisSessionStorage):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_prefix = "user_profile:"
    
    async def store(self, profile: UserProfile):
        key = f"{self.user_prefix}{profile.user_id}"
        await self.redis_client.set(key, profile.json(), ex=self.default_ttl)
    
    async def retrieve(self, user_id: str) -> Optional[UserProfile]:
        key = f"{self.user_prefix}{user_id}"
        data = await self.redis_client.get(key)
        return UserProfile.parse_raw(data) if data else None
```

(Implement similar extensions for Memory and other backends.)

## Integration with OpusAgent

### Session Management Integration

Extend `SessionManagerService`:

```python
# In opusagent/services/session_manager_service.py
class SessionManagerService:
    def __init__(self, storage, user_memory_manager=None):
        self.user_memory = user_memory_manager or UserMemoryManager()
    
    async def create_session(self, conversation_id: str, caller: str, **kwargs):
        session = super().create_session(conversation_id, **kwargs)
        profile = await self.user_memory.get_profile(caller)
        if profile:
            session.conversation_history.insert(0, {"role": "system", "content": f"User context: {profile.summaries[-1]['summary']}"})
        return session
    
    async def end_session(self, conversation_id: str, reason: str):
        session = await self.get_session(conversation_id)
        summary = await self.user_memory.summarize_session(session.conversation_history)
        await self.user_memory.update_profile(session.caller, summary)
        super().end_session(conversation_id, reason)
```

### Bridge Integration

In `base_bridge.py`:

```python
class BaseRealtimeBridge:
    async def initialize_conversation(self, conversation_id: Optional[str] = None, caller: str = "unknown"):
        # ... existing code ...
        if self.session_manager:
            await self.session_manager.create_session(conversation_id, caller=caller)
```

## Configuration

### Environment Variables

```bash
USER_MEMORY_ENABLED=true
USER_MEMORY_TTL=2592000  # 30 days
USER_MEMORY_STORAGE=redis
USER_SUMMARY_MODEL=gpt-4o-mini
USER_MAX_SUMMARIES=10  # Per user
```

### Configuration Class

```python
class UserMemoryConfig(BaseModel):
    enabled: bool = True
    ttl: int = 2592000
    storage: str = "redis"
    summary_model: str = "gpt-4o-mini"
    max_summaries: int = 10
```

## Usage Examples

### Basic Usage

```python
async def handle_session_end(session_id: str):
    session = await session_manager.get_session(session_id)
    await user_memory_manager.update_profile(session.caller, await user_memory_manager.summarize_session(session.conversation_history))
```

### Personalized Agent Response

```python
class CustomerServiceAgent:
    async def generate_response(self, input_text: str, session):
        if session.conversation_history[0]["role"] == "system":
            print(f"Using user context: {session.conversation_history[0]['content']}")
        # Generate response with context
```

## Privacy and Security Considerations

- **Consent**: Always obtain user consent before storing profiles.
- **Data Minimization**: Store only summaries, not full transcripts.
- **Encryption**: Encrypt profiles in storage.
- **Deletion**: Provide APIs for users to delete their data.
- **Compliance**: Adhere to GDPR/CCPA; integrate with voice fingerprinting for secure ID.

## Testing

### Unit Tests

Test profile retrieval, updates, and summarization.

### Integration Tests

Simulate multi-session flows and verify context persistence.

## Performance Considerations

- **Scalability**: Use Redis for high-traffic scenarios.
- **Optimization**: Limit summary count; cache frequent users.

## Future Enhancements

- **AI-Driven Insights**: Analyze profiles for trends.
- **Integration with Voice Fingerprinting**: Use for ID if caller ID unavailable.
- **Multi-User Support**: Handle shared devices.

## Dependencies

- openai
- pydantic

## Troubleshooting

- **No Profile Found**: Check caller ID consistency.
- **Summary Errors**: Verify OpenAI API key.

## Conclusion

This implementation enables seamless cross-session persistence, enhancing user experience while building on existing systems. Integrate with voice fingerprinting for advanced features.