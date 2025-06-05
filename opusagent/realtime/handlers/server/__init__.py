"""
Server event handlers for the OpenAI Realtime API.

This module contains handlers for processing events received from the OpenAI Realtime API WebSocket server.
Each handler is responsible for managing specific event types.
"""

from opusagent.realtime.handlers.server.conversation_handler import ConversationHandler
from opusagent.realtime.handlers.server.conversation_item_handler import (
    ConversationItemHandler,
)
from opusagent.realtime.handlers.server.error_handler import ErrorHandler
from opusagent.realtime.handlers.server.input_audio_buffer_handler import (
    InputAudioBufferHandler,
)
from opusagent.realtime.handlers.server.output_audio_buffer_handler import (
    OutputAudioBufferHandler,
)
from opusagent.realtime.handlers.server.rate_limits_handler import RateLimitsHandler
from opusagent.realtime.handlers.server.response_handler import ResponseHandler
from opusagent.realtime.handlers.server.session_handler import SessionHandler
from opusagent.realtime.handlers.server.transcription_session_handler import (
    TranscriptionSessionHandler,
)

# Registry for mapping event types to their handlers
registry = {
    "error": ErrorHandler,
    "session.created": SessionHandler,
    "session.updated": SessionHandler,
    "conversation.created": ConversationHandler,
    "conversation.item.created": ConversationItemHandler,
    "conversation.item.retrieved": ConversationItemHandler,
    "conversation.item.input_audio_transcription.completed": ConversationItemHandler,
    "conversation.item.input_audio_transcription.delta": ConversationItemHandler,
    "conversation.item.input_audio_transcription.failed": ConversationItemHandler,
    "conversation.item.truncated": ConversationItemHandler,
    "conversation.item.deleted": ConversationItemHandler,
    "input_audio_buffer.committed": InputAudioBufferHandler,
    "input_audio_buffer.cleared": InputAudioBufferHandler,
    "input_audio_buffer.speech_started": InputAudioBufferHandler,
    "input_audio_buffer.speech_stopped": InputAudioBufferHandler,
    "response.created": ResponseHandler,
    "response.done": ResponseHandler,
    "response.output_item.added": ResponseHandler,
    "response.output_item.done": ResponseHandler,
    "response.content_part.added": ResponseHandler,
    "response.content_part.done": ResponseHandler,
    "response.text.delta": ResponseHandler,
    "response.text.done": ResponseHandler,
    "response.audio_transcript.delta": ResponseHandler,
    "response.audio_transcript.done": ResponseHandler,
    "response.audio.delta": ResponseHandler,
    "response.audio.done": ResponseHandler,
    "response.function_call_arguments.delta": ResponseHandler,
    "response.function_call_arguments.done": ResponseHandler,
    "transcription_session.updated": TranscriptionSessionHandler,
    "rate_limits.updated": RateLimitsHandler,
    "output_audio_buffer.started": OutputAudioBufferHandler,
    "output_audio_buffer.stopped": OutputAudioBufferHandler,
    "output_audio_buffer.cleared": OutputAudioBufferHandler,
}

__all__ = [
    "SessionHandler",
    "ConversationHandler",
    "ConversationItemHandler",
    "InputAudioBufferHandler",
    "ResponseHandler",
    "TranscriptionSessionHandler",
    "RateLimitsHandler",
    "OutputAudioBufferHandler",
    "ErrorHandler",
    "registry",
]
