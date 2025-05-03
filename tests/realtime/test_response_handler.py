"""Unit tests for the ResponseHandler class."""

import asyncio
from typing import Dict, Any, List
import pytest
from fastagent.realtime.handlers.client.response_handler import ResponseHandler
from fastagent.models.openai_api import ResponseCreateOptions

class MockSendEvent:
    """Mock class for testing event sending."""
    
    def __init__(self):
        self.sent_events: List[Dict[str, Any]] = []
        
    async def __call__(self, event: Dict[str, Any]) -> None:
        self.sent_events.append(event)

@pytest.fixture
def mock_send_event():
    """Fixture providing a mock send event callback."""
    return MockSendEvent()

@pytest.fixture
def response_handler(mock_send_event):
    """Fixture providing a ResponseHandler instance."""
    return ResponseHandler(mock_send_event)

@pytest.mark.asyncio
async def test_handle_create_basic(response_handler, mock_send_event):
    """Test basic response creation."""
    event = {
        "type": "response.create",
        "event_id": "test_event_1",
        "response": {
            "modalities": ["text"],
            "instructions": "Test instructions",
            "temperature": 0.7
        }
    }
    
    await response_handler.handle_create(event)
    
    # Check that response.created was sent
    assert len(mock_send_event.sent_events) >= 1
    created_event = mock_send_event.sent_events[0]
    assert created_event["type"] == "response.created"
    assert created_event["event_id"] == "test_event_1"
    assert "response" in created_event
    assert created_event["response"]["status"] == "in_progress"
    assert created_event["response"]["modalities"] == ["text"]
    assert created_event["response"]["instructions"] == "Test instructions"
    assert created_event["response"]["temperature"] == 0.7

@pytest.mark.asyncio
async def test_handle_create_with_audio(response_handler, mock_send_event):
    """Test response creation with audio modality."""
    event = {
        "type": "response.create",
        "event_id": "test_event_2",
        "response": {
            "modalities": ["text", "audio"],
            "voice": "sage",
            "output_audio_format": "pcm16"
        }
    }
    
    await response_handler.handle_create(event)
    
    # Check that response.created was sent
    assert len(mock_send_event.sent_events) >= 1
    created_event = mock_send_event.sent_events[0]
    assert created_event["type"] == "response.created"
    assert created_event["response"]["modalities"] == ["text", "audio"]
    assert created_event["response"]["voice"] == "sage"
    assert created_event["response"]["output_audio_format"] == "pcm16"

@pytest.mark.asyncio
async def test_handle_create_with_tools(response_handler, mock_send_event):
    """Test response creation with tools."""
    event = {
        "type": "response.create",
        "event_id": "test_event_3",
        "response": {
            "modalities": ["text"],
            "tools": [
                {
                    "type": "function",
                    "name": "test_function",
                    "description": "A test function",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "param1": {"type": "string"}
                        }
                    }
                }
            ],
            "tool_choice": "auto"
        }
    }
    
    await response_handler.handle_create(event)
    
    # Check that response.created was sent
    assert len(mock_send_event.sent_events) >= 1
    created_event = mock_send_event.sent_events[0]
    assert created_event["type"] == "response.created"
    assert created_event["response"]["tools"] == event["response"]["tools"]
    assert created_event["response"]["tool_choice"] == "auto"

@pytest.mark.asyncio
async def test_handle_cancel_with_id(response_handler, mock_send_event):
    """Test canceling a specific response."""
    # First create a response
    create_event = {
        "type": "response.create",
        "event_id": "test_event_4",
        "response": {"modalities": ["text"]}
    }
    await response_handler.handle_create(create_event)
    
    # Get the response ID from the created event
    response_id = mock_send_event.sent_events[0]["response"]["id"]
    
    # Now cancel it
    cancel_event = {
        "type": "response.cancel",
        "event_id": "test_event_5",
        "response_id": response_id
    }
    await response_handler.handle_cancel(cancel_event)
    
    # Check that response.cancelled was sent
    assert len(mock_send_event.sent_events) >= 2
    cancelled_event = mock_send_event.sent_events[-1]
    assert cancelled_event["type"] == "response.cancelled"
    assert cancelled_event["event_id"] == "test_event_5"
    assert cancelled_event["response_id"] == response_id

@pytest.mark.asyncio
async def test_handle_cancel_without_id(response_handler, mock_send_event):
    """Test canceling the most recent response."""
    # First create a response
    create_event = {
        "type": "response.create",
        "event_id": "test_event_6",
        "response": {"modalities": ["text"]}
    }
    await response_handler.handle_create(create_event)
    
    # Now cancel it without specifying response_id
    cancel_event = {
        "type": "response.cancel",
        "event_id": "test_event_7"
    }
    await response_handler.handle_cancel(cancel_event)
    
    # Check that response.cancelled was sent
    assert len(mock_send_event.sent_events) >= 2
    cancelled_event = mock_send_event.sent_events[-1]
    assert cancelled_event["type"] == "response.cancelled"
    assert cancelled_event["event_id"] == "test_event_7"

@pytest.mark.asyncio
async def test_handle_cancel_nonexistent(response_handler, mock_send_event):
    """Test canceling a nonexistent response."""
    cancel_event = {
        "type": "response.cancel",
        "event_id": "test_event_8",
        "response_id": "nonexistent"
    }
    await response_handler.handle_cancel(cancel_event)
    
    # Check that error was sent
    assert len(mock_send_event.sent_events) == 1
    error_event = mock_send_event.sent_events[0]
    assert error_event["type"] == "error"
    assert error_event["event_id"] == "test_event_8"
    assert "Response nonexistent not found" in error_event["message"]

@pytest.mark.asyncio
async def test_handle_cancel_no_active_responses(response_handler, mock_send_event):
    """Test canceling when no active responses exist."""
    cancel_event = {
        "type": "response.cancel",
        "event_id": "test_event_9"
    }
    await response_handler.handle_cancel(cancel_event)
    
    # Check that error was sent
    assert len(mock_send_event.sent_events) == 1
    error_event = mock_send_event.sent_events[0]
    assert error_event["type"] == "error"
    assert error_event["event_id"] == "test_event_9"
    assert "No active responses to cancel" in error_event["message"]

@pytest.mark.asyncio
async def test_response_generation_flow(response_handler, mock_send_event):
    """Test the complete response generation flow."""
    event = {
        "type": "response.create",
        "event_id": "test_event_10",
        "response": {
            "modalities": ["text", "audio"],
            "tools": [{"type": "function", "name": "test_function"}]
        }
    }
    
    await response_handler.handle_create(event)
    
    # Get the response ID and task
    response_id = mock_send_event.sent_events[0]["response"]["id"]
    task = response_handler._response_tasks[response_id]
    
    # Wait for the task to complete
    try:
        await asyncio.wait_for(task, timeout=1.0)
    except asyncio.TimeoutError:
        task.cancel()
        raise AssertionError("Response generation task did not complete in time")
    
    # Check the sequence of events
    events = mock_send_event.sent_events
    assert len(events) >= 5  # created + text deltas + audio deltas + function call + done
    
    # Check response.created
    assert events[0]["type"] == "response.created"
    
    # Check text deltas
    text_deltas = [e for e in events if e["type"] == "response.text.delta"]
    assert len(text_deltas) > 0
    
    # Check audio deltas
    audio_deltas = [e for e in events if e["type"] == "response.audio.delta"]
    assert len(audio_deltas) > 0
    
    # Check function call
    function_call = [e for e in events if e["type"] == "response.content_part.added"]
    assert len(function_call) == 1
    
    # Check response.done
    assert events[-1]["type"] == "response.done"

@pytest.mark.asyncio
async def test_response_cancellation_during_generation(response_handler, mock_send_event):
    """Test canceling a response during generation."""
    event = {
        "type": "response.create",
        "event_id": "test_event_11",
        "response": {"modalities": ["text"]}
    }
    
    # Start response generation
    await response_handler.handle_create(event)
    
    # Get the response ID
    response_id = mock_send_event.sent_events[0]["response"]["id"]
    
    # Cancel the response
    cancel_event = {
        "type": "response.cancel",
        "event_id": "test_event_12",
        "response_id": response_id
    }
    await response_handler.handle_cancel(cancel_event)
    
    # Check that response.cancelled was sent
    assert len(mock_send_event.sent_events) >= 2
    cancelled_event = mock_send_event.sent_events[-1]
    assert cancelled_event["type"] == "response.cancelled"
    assert cancelled_event["response_id"] == response_id 