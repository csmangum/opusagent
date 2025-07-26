"""Unit tests for the TranscriptManager class."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from opusagent.utils.call_recorder import AudioChannel, CallRecorder, TranscriptType
from opusagent.handlers.transcript_manager import TranscriptManager


@pytest.fixture
def mock_call_recorder():
    """Create a mock CallRecorder instance."""
    recorder = MagicMock(spec=CallRecorder)
    recorder.add_transcript = AsyncMock()
    return recorder


@pytest.fixture
def transcript_manager(mock_call_recorder):
    """Create a TranscriptManager instance with a mock CallRecorder."""
    manager = TranscriptManager(mock_call_recorder)
    return manager


@pytest.fixture
def transcript_manager_no_recorder():
    """Create a TranscriptManager instance without a CallRecorder."""
    return TranscriptManager()


@pytest.mark.asyncio
async def test_handle_input_transcript_delta(transcript_manager):
    """Test handling input transcript delta."""
    # Test with non-empty delta
    await transcript_manager.handle_input_transcript_delta("Hello")
    assert transcript_manager.input_transcript_buffer == ["Hello"]

    # Test with empty delta
    await transcript_manager.handle_input_transcript_delta("")
    assert transcript_manager.input_transcript_buffer == ["Hello"]

    # Test with another non-empty delta
    await transcript_manager.handle_input_transcript_delta(" world")
    assert transcript_manager.input_transcript_buffer == ["Hello", " world"]


@pytest.mark.asyncio
async def test_handle_output_transcript_delta(transcript_manager):
    """Test handling output transcript delta."""
    # Test with non-empty delta
    await transcript_manager.handle_output_transcript_delta("Hi there")
    assert transcript_manager.output_transcript_buffer == ["Hi there"]

    # Test with empty delta
    await transcript_manager.handle_output_transcript_delta("")
    assert transcript_manager.output_transcript_buffer == ["Hi there"]

    # Test with another non-empty delta
    await transcript_manager.handle_output_transcript_delta("!")
    assert transcript_manager.output_transcript_buffer == ["Hi there", "!"]


@pytest.mark.asyncio
async def test_handle_input_transcript_completed(
    transcript_manager, mock_call_recorder
):
    """Test handling input transcript completion."""
    # Add some transcript deltas
    await transcript_manager.handle_input_transcript_delta("Hello")
    await transcript_manager.handle_input_transcript_delta(" world")

    # Complete the transcript
    await transcript_manager.handle_input_transcript_completed()

    # Verify the transcript was recorded
    mock_call_recorder.add_transcript.assert_called_once_with(
        text="Hello world",
        channel=AudioChannel.CALLER,
        transcript_type=TranscriptType.INPUT,
    )

    # Verify buffer was cleared
    assert transcript_manager.input_transcript_buffer == []


@pytest.mark.asyncio
async def test_handle_output_transcript_completed(
    transcript_manager, mock_call_recorder
):
    """Test handling output transcript completion."""
    # Add some transcript deltas
    await transcript_manager.handle_output_transcript_delta("Hi")
    await transcript_manager.handle_output_transcript_delta(" there")

    # Complete the transcript
    await transcript_manager.handle_output_transcript_completed()

    # Verify the transcript was recorded
    mock_call_recorder.add_transcript.assert_called_once_with(
        text="Hi there",
        channel=AudioChannel.BOT,
        transcript_type=TranscriptType.OUTPUT,
    )

    # Verify buffer was cleared
    assert transcript_manager.output_transcript_buffer == []


@pytest.mark.asyncio
async def test_handle_input_transcript_completed_empty(
    transcript_manager, mock_call_recorder
):
    """Test handling input transcript completion with empty buffer."""
    # Complete empty transcript
    await transcript_manager.handle_input_transcript_completed()

    # Verify no transcript was recorded
    mock_call_recorder.add_transcript.assert_not_called()

    # Verify buffer remains empty
    assert transcript_manager.input_transcript_buffer == []


@pytest.mark.asyncio
async def test_handle_output_transcript_completed_empty(
    transcript_manager, mock_call_recorder
):
    """Test handling output transcript completion with empty buffer."""
    # Complete empty transcript
    await transcript_manager.handle_output_transcript_completed()

    # Verify no transcript was recorded
    mock_call_recorder.add_transcript.assert_not_called()

    # Verify buffer remains empty
    assert transcript_manager.output_transcript_buffer == []


@pytest.mark.asyncio
async def test_handle_input_transcript_completed_no_recorder(
    transcript_manager_no_recorder,
):
    """Test handling input transcript completion without a call recorder."""
    # Add some transcript deltas
    await transcript_manager_no_recorder.handle_input_transcript_delta("Hello")
    await transcript_manager_no_recorder.handle_input_transcript_delta(" world")

    # Complete the transcript
    await transcript_manager_no_recorder.handle_input_transcript_completed()

    # Verify buffer was cleared
    assert transcript_manager_no_recorder.input_transcript_buffer == []


@pytest.mark.asyncio
async def test_handle_output_transcript_completed_no_recorder(
    transcript_manager_no_recorder,
):
    """Test handling output transcript completion without a call recorder."""
    # Add some transcript deltas
    await transcript_manager_no_recorder.handle_output_transcript_delta("Hi")
    await transcript_manager_no_recorder.handle_output_transcript_delta(" there")

    # Complete the transcript
    await transcript_manager_no_recorder.handle_output_transcript_completed()

    # Verify buffer was cleared
    assert transcript_manager_no_recorder.output_transcript_buffer == []


def test_set_call_recorder(transcript_manager_no_recorder, mock_call_recorder):
    """Test setting the call recorder."""
    # Initially no recorder
    assert transcript_manager_no_recorder.call_recorder is None

    # Set the recorder
    transcript_manager_no_recorder.set_call_recorder(mock_call_recorder)

    # Verify recorder was set
    assert transcript_manager_no_recorder.call_recorder == mock_call_recorder


@pytest.mark.asyncio
async def test_handle_input_transcript_completed_whitespace(
    transcript_manager, mock_call_recorder
):
    """Test handling input transcript completion with only whitespace."""
    # Add whitespace-only transcript
    await transcript_manager.handle_input_transcript_delta("   ")
    await transcript_manager.handle_input_transcript_delta("\t\n")

    # Complete the transcript
    await transcript_manager.handle_input_transcript_completed()

    # Verify no transcript was recorded
    mock_call_recorder.add_transcript.assert_not_called()

    # Verify buffer was cleared
    assert transcript_manager.input_transcript_buffer == []


@pytest.mark.asyncio
async def test_handle_output_transcript_completed_whitespace(
    transcript_manager, mock_call_recorder
):
    """Test handling output transcript completion with only whitespace."""
    # Add whitespace-only transcript
    await transcript_manager.handle_output_transcript_delta("   ")
    await transcript_manager.handle_output_transcript_delta("\t\n")

    # Complete the transcript
    await transcript_manager.handle_output_transcript_completed()

    # Verify no transcript was recorded
    mock_call_recorder.add_transcript.assert_not_called()

    # Verify buffer was cleared
    assert transcript_manager.output_transcript_buffer == []
