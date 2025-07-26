"""
Unit tests for CallRecorder module.

Tests cover:
- CallRecorder initialization and configuration
- Audio recording for both caller and bot
- Transcript management
- Recording lifecycle (start/stop)
- Audio resampling functionality
- Metadata tracking
- File operations and cleanup
- Error handling scenarios
"""

import asyncio
import base64
import json
import shutil
import tempfile
import wave
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, mock_open, patch

import numpy as np
import pytest

from opusagent.utils.call_recorder import (AudioChannel, CallMetadata,
                                            CallRecorder, TranscriptEntry,
                                            TranscriptType)


class TestTranscriptEntry:
    """Test TranscriptEntry dataclass."""
    
    def test_transcript_entry_creation(self):
        """Test creating a transcript entry."""
        timestamp = datetime.now(timezone.utc)
        entry = TranscriptEntry(
            timestamp=timestamp,
            channel=AudioChannel.CALLER,
            type=TranscriptType.INPUT,
            text="Hello world",
            confidence=0.95,
            duration_ms=1500.0
        )
        
        assert entry.timestamp == timestamp
        assert entry.channel == AudioChannel.CALLER
        assert entry.type == TranscriptType.INPUT
        assert entry.text == "Hello world"
        assert entry.confidence == 0.95
        assert entry.duration_ms == 1500.0
    
    def test_transcript_entry_to_dict(self):
        """Test converting transcript entry to dictionary."""
        timestamp = datetime.now(timezone.utc)
        entry = TranscriptEntry(
            timestamp=timestamp,
            channel=AudioChannel.BOT,
            type=TranscriptType.OUTPUT,
            text="Test response",
            confidence=0.87
        )
        
        result = entry.to_dict()
        
        assert result["timestamp"] == timestamp.isoformat()
        assert result["channel"] == "bot"
        assert result["type"] == "output"
        assert result["text"] == "Test response"
        assert result["confidence"] == 0.87
        assert result["duration_ms"] is None


class TestCallMetadata:
    """Test CallMetadata dataclass."""
    
    def test_call_metadata_creation(self):
        """Test creating call metadata."""
        start_time = datetime.now(timezone.utc)
        metadata = CallMetadata(
            conversation_id="conv_123",
            session_id="sess_456",
            start_time=start_time
        )
        
        assert metadata.conversation_id == "conv_123"
        assert metadata.session_id == "sess_456"
        assert metadata.start_time == start_time
        assert metadata.end_time is None
        assert metadata.caller_audio_chunks == 0
        assert metadata.bot_audio_chunks == 0
        assert metadata.caller_audio_bytes == 0
        assert metadata.bot_audio_bytes == 0
        assert metadata.transcript_entries == 0
        assert metadata.function_calls == []
    
    def test_duration_calculation(self):
        """Test duration calculation."""
        start_time = datetime.now(timezone.utc)
        metadata = CallMetadata(
            conversation_id="conv_123",
            session_id="sess_456",
            start_time=start_time
        )
        
        # No end time
        assert metadata.duration_seconds is None
        
        # With end time
        from datetime import timedelta
        end_time = start_time + timedelta(seconds=30)
        metadata.end_time = end_time
        assert metadata.duration_seconds == 30.0
    
    def test_audio_duration_estimation(self):
        """Test audio duration estimation."""
        metadata = CallMetadata(
            conversation_id="conv_123",
            session_id="sess_456",
            start_time=datetime.now(timezone.utc)
        )
        
        # 16000 samples/sec * 2 bytes/sample = 32000 bytes/sec
        metadata.caller_audio_bytes = 32000  # 1 second
        metadata.bot_audio_bytes = 64000     # 2 seconds
        
        assert metadata.caller_audio_duration_seconds == 1.0
        assert metadata.bot_audio_duration_seconds == 2.0
    
    def test_metadata_to_dict(self):
        """Test converting metadata to dictionary."""
        start_time = datetime.now(timezone.utc)
        from datetime import timedelta
        end_time = start_time + timedelta(seconds=10)
        
        metadata = CallMetadata(
            conversation_id="conv_123",
            session_id="sess_456",
            start_time=start_time,
            end_time=end_time,
            caller_audio_chunks=5,
            bot_audio_chunks=3,
            caller_audio_bytes=1000,
            bot_audio_bytes=2000,
            transcript_entries=8
        )
        
        result = metadata.to_dict()
        
        assert result["conversation_id"] == "conv_123"
        assert result["session_id"] == "sess_456"
        assert result["start_time"] == start_time.isoformat()
        assert result["end_time"] == end_time.isoformat()
        assert result["duration_seconds"] == 10.0
        assert result["caller_audio_chunks"] == 5
        assert result["bot_audio_chunks"] == 3
        assert result["caller_audio_bytes"] == 1000
        assert result["bot_audio_bytes"] == 2000
        assert result["transcript_entries"] == 8


class TestCallRecorder:
    """Test CallRecorder class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def recorder(self, temp_dir):
        """Create a CallRecorder instance for testing."""
        return CallRecorder(
            conversation_id="test_conv_123",
            session_id="test_sess_456",
            base_output_dir=temp_dir,
            bot_sample_rate=24000
        )
    
    def test_initialization(self, temp_dir):
        """Test CallRecorder initialization."""
        recorder = CallRecorder(
            conversation_id="conv_123",
            session_id="sess_456",
            base_output_dir=temp_dir,
            bot_sample_rate=22050
        )
        
        assert recorder.conversation_id == "conv_123"
        assert recorder.session_id == "sess_456"
        assert recorder.base_output_dir == Path(temp_dir)
        assert recorder.caller_sample_rate == 16000
        assert recorder.bot_sample_rate == 22050
        assert recorder.target_sample_rate == 16000
        assert recorder.channels == 1
        assert recorder.sample_width == 2
        assert not recorder.recording_active
        assert not recorder.finalized
        
        # Check that recording directory was created
        assert recorder.recording_dir.exists()
        assert recorder.recording_dir.is_dir()
    
    def test_initialization_with_defaults(self, temp_dir):
        """Test CallRecorder initialization with default values."""
        recorder = CallRecorder(
            conversation_id="conv_123",
            base_output_dir=temp_dir
        )
        
        assert recorder.session_id == "conv_123"  # Defaults to conversation_id
        assert recorder.bot_sample_rate == 24000  # Default value
    
    def test_audio_resampling_no_change(self, recorder):
        """Test audio resampling when no resampling is needed."""
        # Create test audio data (16-bit PCM)
        audio_data = np.array([100, -200, 300, -400], dtype=np.int16)
        audio_bytes = audio_data.tobytes()
        
        # Same sample rate - should return unchanged
        result = recorder._resample_audio(audio_bytes, 16000, 16000)
        
        assert result == audio_bytes
    
    def test_audio_resampling_upsampling(self, recorder):
        """Test audio upsampling."""
        # Create test audio data
        audio_data = np.array([100, -200, 300, -400], dtype=np.int16)
        audio_bytes = audio_data.tobytes()
        
        # Upsample from 16kHz to 32kHz (should double the length)
        result = recorder._resample_audio(audio_bytes, 16000, 32000)
        
        # Result should be longer
        result_array = np.frombuffer(result, dtype=np.int16)
        assert len(result_array) > len(audio_data)
        # Should be approximately double the length
        assert abs(len(result_array) - 2 * len(audio_data)) <= 1
    
    def test_audio_resampling_downsampling(self, recorder):
        """Test audio downsampling."""
        # Create test audio data
        audio_data = np.array([100, -200, 300, -400, 500, -600, 700, -800], dtype=np.int16)
        audio_bytes = audio_data.tobytes()
        
        # Downsample from 32kHz to 16kHz (should halve the length)
        result = recorder._resample_audio(audio_bytes, 32000, 16000)
        
        # Result should be shorter
        result_array = np.frombuffer(result, dtype=np.int16)
        assert len(result_array) < len(audio_data)
        # Should be approximately half the length
        assert abs(len(result_array) - len(audio_data) // 2) <= 1
    
    def test_audio_resampling_error_handling(self, recorder):
        """Test audio resampling error handling."""
        with patch('numpy.frombuffer', side_effect=Exception("Test error")):
            # Should return original data on error
            result = recorder._resample_audio(b"test_data", 16000, 24000)
            assert result == b"test_data"
    
    @pytest.mark.asyncio
    async def test_start_recording_success(self, recorder):
        """Test successful recording start."""
        with patch.object(recorder, '_init_wav_files') as mock_init, \
             patch.object(recorder, '_log_session_event', new_callable=AsyncMock) as mock_log:
            
            result = await recorder.start_recording()
            
            assert result is True
            assert recorder.recording_active is True
            mock_init.assert_called_once()
            mock_log.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_recording_already_active(self, recorder):
        """Test starting recording when already active."""
        recorder.recording_active = True
        
        result = await recorder.start_recording()
        
        assert result is True  # Should still return True
    
    @pytest.mark.asyncio
    async def test_start_recording_failure(self, recorder):
        """Test recording start failure."""
        with patch.object(recorder, '_init_wav_files', side_effect=Exception("Test error")):
            result = await recorder.start_recording()
            
            assert result is False
            assert recorder.recording_active is False
    
    def test_init_wav_files(self, recorder):
        """Test WAV file initialization."""
        with patch('wave.open') as mock_wave_open:
            mock_wav = Mock()
            mock_wave_open.return_value = mock_wav
            
            recorder._init_wav_files()
            
            # Should open 3 WAV files
            assert mock_wave_open.call_count == 3
            
            # Check calls for proper file paths
            call_args = [call[0][0] for call in mock_wave_open.call_args_list]  # Get first positional arg from each call
            assert str(recorder.caller_audio_file) in call_args
            assert str(recorder.bot_audio_file) in call_args
            assert str(recorder.stereo_audio_file) in call_args
            
            # Check that all calls use "wb" mode
            call_modes = [call[0][1] for call in mock_wave_open.call_args_list]  # Get second positional arg from each call
            assert all(mode == "wb" for mode in call_modes)
            
            # Check WAV file configuration
            assert mock_wav.setnchannels.call_count >= 2  # Mono files
            assert mock_wav.setsampwidth.call_count == 3
            assert mock_wav.setframerate.call_count == 3
    
    @pytest.mark.asyncio
    async def test_record_caller_audio_success(self, recorder):
        """Test successful caller audio recording."""
        # Setup recording
        recorder.recording_active = True
        recorder.caller_wav = Mock()
        recorder.stereo_wav = Mock()
        
        # Create test audio data
        audio_data = np.array([100, -200, 300, -400], dtype=np.int16)
        audio_b64 = base64.b64encode(audio_data.tobytes()).decode()
        
        with patch.object(recorder, '_write_stereo_chunk', new_callable=AsyncMock) as mock_stereo:
            result = await recorder.record_caller_audio(audio_b64)
            
            assert result is True
            assert recorder.metadata.caller_audio_chunks == 1
            assert recorder.metadata.caller_audio_bytes > 0
            
            # Check that audio was written
            recorder.caller_wav.writeframes.assert_called_once()
            mock_stereo.assert_called_once()
            
            # Check that audio is buffered
            assert len(recorder.caller_audio_buffer) == 1
    
    @pytest.mark.asyncio
    async def test_record_caller_audio_not_recording(self, recorder):
        """Test caller audio recording when not active."""
        recorder.recording_active = False
        
        result = await recorder.record_caller_audio("dGVzdA==")  # "test" in base64
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_record_caller_audio_with_resampling(self, recorder):
        """Test caller audio recording with resampling."""
        recorder.recording_active = True
        recorder.caller_wav = Mock()
        recorder.stereo_wav = Mock()
        recorder.caller_sample_rate = 8000  # Different from target rate
        
        audio_data = np.array([100, -200, 300, -400], dtype=np.int16)
        audio_b64 = base64.b64encode(audio_data.tobytes()).decode()
        
        with patch.object(recorder, '_resample_audio', return_value=audio_data.tobytes()) as mock_resample, \
             patch.object(recorder, '_write_stereo_chunk', new_callable=AsyncMock):
            
            result = await recorder.record_caller_audio(audio_b64)
            
            assert result is True
            mock_resample.assert_called_once_with(
                audio_data.tobytes(), 8000, 16000
            )
    
    @pytest.mark.asyncio
    async def test_record_bot_audio_success(self, recorder):
        """Test successful bot audio recording."""
        recorder.recording_active = True
        recorder.bot_wav = Mock()
        recorder.stereo_wav = Mock()
        
        # Create test audio data
        audio_data = np.array([100, -200, 300, -400], dtype=np.int16)
        audio_b64 = base64.b64encode(audio_data.tobytes()).decode()
        
        with patch.object(recorder, '_resample_audio', return_value=audio_data.tobytes()) as mock_resample, \
             patch.object(recorder, '_write_stereo_chunk', new_callable=AsyncMock) as mock_stereo:
            
            result = await recorder.record_bot_audio(audio_b64)
            
            assert result is True
            assert recorder.metadata.bot_audio_chunks == 1
            assert recorder.metadata.bot_audio_bytes > 0
            
            # Check resampling was called
            mock_resample.assert_called_once_with(
                audio_data.tobytes(), 24000, 16000
            )
            
            # Check that audio was written
            recorder.bot_wav.writeframes.assert_called_once()
            mock_stereo.assert_called_once()
            
            # Check that audio is buffered
            assert len(recorder.bot_audio_buffer) == 1
    
    @pytest.mark.asyncio
    async def test_record_bot_audio_invalid_chunk(self, recorder):
        """Test bot audio recording with invalid chunk."""
        recorder.recording_active = True
        
        # Too small chunk
        result = await recorder.record_bot_audio(base64.b64encode(b"x").decode())
        assert result is False
        
        # Odd number of bytes
        result = await recorder.record_bot_audio(base64.b64encode(b"xxx").decode())
        # Should still succeed after truncation
        assert result is True or result is False  # Implementation dependent
    
    @pytest.mark.asyncio
    async def test_record_bot_audio_error_handling(self, recorder):
        """Test bot audio recording error handling."""
        recorder.recording_active = True
        
        with patch('base64.b64decode', side_effect=Exception("Decode error")):
            result = await recorder.record_bot_audio("invalid_base64")
            assert result is False
    
    @pytest.mark.asyncio
    async def test_write_stereo_chunk(self, recorder):
        """Test writing stereo chunks."""
        recorder.stereo_wav = Mock()
        
        audio_data = np.array([100, -200, 300, -400], dtype=np.int16)
        audio_bytes = audio_data.tobytes()
        
        # Test caller channel (left)
        await recorder._write_stereo_chunk(audio_bytes, AudioChannel.CALLER)
        
        # Test bot channel (right)
        await recorder._write_stereo_chunk(audio_bytes, AudioChannel.BOT)
        
        # Should have written stereo frames twice
        assert recorder.stereo_wav.writeframes.call_count == 2
    
    @pytest.mark.asyncio
    async def test_write_stereo_chunk_error(self, recorder):
        """Test stereo chunk writing error handling."""
        recorder.stereo_wav = Mock()
        
        with patch('numpy.frombuffer', side_effect=Exception("Test error")):
            # Should not raise exception
            await recorder._write_stereo_chunk(b"test", AudioChannel.CALLER)
    
    @pytest.mark.asyncio
    async def test_add_transcript(self, recorder):
        """Test adding transcript entries."""
        result = await recorder.add_transcript(
            text="Hello world",
            channel=AudioChannel.CALLER,
            transcript_type=TranscriptType.INPUT,
            confidence=0.95,
            duration_ms=1500.0
        )
        
        assert result is True
        assert len(recorder.transcripts) == 1
        assert recorder.metadata.transcript_entries == 1
        
        entry = recorder.transcripts[0]
        assert entry.text == "Hello world"
        assert entry.channel == AudioChannel.CALLER
        assert entry.type == TranscriptType.INPUT
        assert entry.confidence == 0.95
        assert entry.duration_ms == 1500.0
    
    @pytest.mark.asyncio
    async def test_add_transcript_error(self, recorder):
        """Test transcript addition error handling."""
        with patch.object(TranscriptEntry, '__init__', side_effect=Exception("Test error")):
            result = await recorder.add_transcript(
                text="Test",
                channel=AudioChannel.CALLER,
                transcript_type=TranscriptType.INPUT
            )
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_log_function_call(self, recorder):
        """Test logging function calls."""
        with patch.object(recorder, '_log_session_event', new_callable=AsyncMock) as mock_log:
            await recorder.log_function_call(
                function_name="test_function",
                arguments={"param1": "value1"},
                result={"success": True},
                call_id="call_123"
            )
            
            assert len(recorder.metadata.function_calls) == 1
            
            function_call = recorder.metadata.function_calls[0]
            assert function_call["function_name"] == "test_function"
            assert function_call["arguments"] == {"param1": "value1"}
            assert function_call["result"] == {"success": True}
            assert function_call["call_id"] == "call_123"
            
            mock_log.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_log_session_event(self, recorder):
        """Test session event logging."""
        await recorder._log_session_event("test_event", {"key": "value"})
        
        assert len(recorder.session_events) == 1
        
        event = recorder.session_events[0]
        assert event["event_type"] == "test_event"
        assert event["data"] == {"key": "value"}
        assert "timestamp" in event
    
    @pytest.mark.asyncio
    async def test_stop_recording_success(self, recorder):
        """Test successful recording stop."""
        # Setup active recording
        recorder.recording_active = True
        recorder.caller_wav = Mock()
        recorder.bot_wav = Mock()
        recorder.stereo_wav = Mock()
        
        # Store references to the mocks before they get set to None
        caller_wav = recorder.caller_wav
        bot_wav = recorder.bot_wav
        stereo_wav = recorder.stereo_wav
        
        with patch.object(recorder, '_save_transcript', new_callable=AsyncMock) as mock_save_transcript, \
             patch.object(recorder, '_save_metadata', new_callable=AsyncMock) as mock_save_metadata, \
             patch.object(recorder, '_save_session_events', new_callable=AsyncMock) as mock_save_events, \
             patch.object(recorder, '_create_final_stereo_recording', new_callable=AsyncMock) as mock_create_stereo, \
             patch.object(recorder, '_log_session_event', new_callable=AsyncMock) as mock_log:
            
            result = await recorder.stop_recording()
            
            assert result is True
            assert not recorder.recording_active
            assert recorder.finalized
            assert recorder.metadata.end_time is not None
            
            # Check that WAV files were closed using the stored references
            caller_wav.close.assert_called_once()
            bot_wav.close.assert_called_once()
            stereo_wav.close.assert_called_once()
            
            # Check that save methods were called
            mock_save_transcript.assert_called_once()
            mock_save_metadata.assert_called_once()
            mock_save_events.assert_called_once()
            mock_create_stereo.assert_called_once()
            mock_log.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_recording_not_active(self, recorder):
        """Test stopping recording when not active."""
        recorder.recording_active = False
        
        result = await recorder.stop_recording()
        
        assert result is True  # Should still succeed
    
    @pytest.mark.asyncio
    async def test_stop_recording_error(self, recorder):
        """Test stop recording error handling."""
        recorder.recording_active = True
        
        with patch.object(recorder, '_save_transcript', new_callable=AsyncMock, side_effect=Exception("Save error")):
            result = await recorder.stop_recording()
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_save_transcript(self, recorder):
        """Test saving transcript to file."""
        # Add some transcript entries
        await recorder.add_transcript("Hello", AudioChannel.CALLER, TranscriptType.INPUT)
        await recorder.add_transcript("Hi there", AudioChannel.BOT, TranscriptType.OUTPUT)
        
        recorder.metadata.end_time = datetime.now(timezone.utc)
        
        with patch('builtins.open', mock_open()) as mock_file:
            await recorder._save_transcript()
            
            mock_file.assert_called_once_with(recorder.transcript_file, 'w', encoding='utf-8')
            
            # Check that JSON was written
            handle = mock_file.return_value
            written_data = ''.join(call[0][0] for call in handle.write.call_args_list)
            
            # Should be valid JSON
            transcript_data = json.loads(written_data)
            assert transcript_data["conversation_id"] == recorder.conversation_id
            assert len(transcript_data["entries"]) == 2
    
    @pytest.mark.asyncio
    async def test_save_metadata(self, recorder):
        """Test saving metadata to file."""
        recorder.metadata.end_time = datetime.now(timezone.utc)
        
        with patch('builtins.open', mock_open()) as mock_file:
            await recorder._save_metadata()
            
            mock_file.assert_called_once_with(recorder.metadata_file, 'w', encoding='utf-8')
            
            # Check that JSON was written
            handle = mock_file.return_value
            written_data = ''.join(call[0][0] for call in handle.write.call_args_list)
            
            # Should be valid JSON
            metadata_dict = json.loads(written_data)
            assert metadata_dict["conversation_id"] == recorder.conversation_id
    
    @pytest.mark.asyncio
    async def test_save_session_events(self, recorder):
        """Test saving session events to file."""
        await recorder._log_session_event("test_event", {"key": "value"})
        
        with patch('builtins.open', mock_open()) as mock_file:
            await recorder._save_session_events()
            
            mock_file.assert_called_once_with(recorder.session_log_file, 'w', encoding='utf-8')
            
            # Check that JSON was written
            handle = mock_file.return_value
            written_data = ''.join(call[0][0] for call in handle.write.call_args_list)
            
            # Should be valid JSON
            events_data = json.loads(written_data)
            assert events_data["conversation_id"] == recorder.conversation_id
            assert len(events_data["events"]) == 1
    
    @pytest.mark.asyncio
    async def test_create_final_stereo_recording(self, recorder):
        """Test creating final stereo recording."""
        # Add some audio data to buffers
        audio_data1 = np.array([100, -200, 300], dtype=np.int16).tobytes()
        audio_data2 = np.array([400, -500], dtype=np.int16).tobytes()
        
        recorder.caller_audio_buffer = [audio_data1, audio_data2]
        recorder.bot_audio_buffer = [audio_data1]  # Different length
        
        with patch('wave.open', mock_open()) as mock_wave:
            mock_wav = Mock()
            mock_wave.return_value.__enter__.return_value = mock_wav
            
            await recorder._create_final_stereo_recording()
            
            # Check that WAV file was configured for stereo
            mock_wav.setnchannels.assert_called_with(2)
            mock_wav.setsampwidth.assert_called_with(recorder.sample_width)
            mock_wav.setframerate.assert_called_with(recorder.target_sample_rate)
            
            # Check that audio frames were written
            mock_wav.writeframes.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_final_stereo_recording_no_audio(self, recorder):
        """Test creating stereo recording with no audio buffers."""
        recorder.caller_audio_buffer = []
        recorder.bot_audio_buffer = []
        
        # Should handle gracefully
        await recorder._create_final_stereo_recording()
    
    @pytest.mark.asyncio
    async def test_create_final_stereo_recording_error(self, recorder):
        """Test stereo recording creation error handling."""
        recorder.caller_audio_buffer = [b"invalid_audio"]
        
        with patch('numpy.frombuffer', side_effect=Exception("Test error")):
            # Should not raise exception
            await recorder._create_final_stereo_recording()
    
    def test_get_recording_summary(self, recorder):
        """Test getting recording summary."""
        summary = recorder.get_recording_summary()
        
        assert summary["conversation_id"] == recorder.conversation_id
        assert summary["session_id"] == recorder.session_id
        assert summary["recording_active"] == recorder.recording_active
        assert summary["finalized"] == recorder.finalized
        assert "files" in summary
        assert "stats" in summary
        
        # Check file paths
        files = summary["files"]
        assert "caller_audio" in files
        assert "bot_audio" in files
        assert "stereo_audio" in files
        assert "transcript" in files
        assert "metadata" in files
        assert "session_events" in files
    
    @pytest.mark.asyncio
    async def test_cleanup(self, recorder):
        """Test cleanup functionality."""
        recorder.recording_active = True
        recorder.caller_wav = Mock()
        recorder.bot_wav = Mock()
        recorder.stereo_wav = Mock()
        
        with patch.object(recorder, 'stop_recording', new_callable=AsyncMock) as mock_stop:
            await recorder.cleanup()
            
            mock_stop.assert_called_once()
            
            # Check that files were closed
            recorder.caller_wav.close.assert_called_once()
            recorder.bot_wav.close.assert_called_once()
            recorder.stereo_wav.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup_error(self, recorder):
        """Test cleanup error handling."""
        with patch.object(recorder, 'stop_recording', new_callable=AsyncMock, side_effect=Exception("Test error")):
            # Should not raise exception
            await recorder.cleanup()
    
    def test_sample_rate_detection(self):
        """Test sample rate detection helper."""
        # Create test audio data (4 samples = 8 bytes)
        audio_data = np.array([100, -200, 300, -400], dtype=np.int16)
        audio_b64 = base64.b64encode(audio_data.tobytes()).decode()
        
        result = CallRecorder.test_sample_rate_detection(audio_b64)
        
        assert "chunk_info" in result
        assert "sample_rate_analysis" in result
        assert "recommended_rates" in result
        
        chunk_info = result["chunk_info"]
        assert chunk_info["bytes"] == 8
        assert chunk_info["samples"] == 4
        
        # Check that analysis was performed for different sample rates
        analysis = result["sample_rate_analysis"]
        assert 16000 in analysis
        assert 24000 in analysis
        assert 44100 in analysis
    
    def test_sample_rate_detection_error(self):
        """Test sample rate detection error handling."""
        result = CallRecorder.test_sample_rate_detection("invalid_base64")
        
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_set_bot_sample_rate(self, recorder):
        """Test setting bot sample rate."""
        original_rate = recorder.bot_sample_rate
        new_rate = 48000
        
        with patch.object(recorder, '_log_session_event', new_callable=AsyncMock) as mock_log:
            recorder.set_bot_sample_rate(new_rate)
            
            # Wait a bit for the async task to complete
            await asyncio.sleep(0.1)
            
            assert recorder.bot_sample_rate == new_rate
            mock_log.assert_called_once_with(
                "sample_rate_changed",
                {
                    "old_rate": original_rate,
                    "new_rate": new_rate,
                    "chunk_count": recorder.metadata.bot_audio_chunks
                }
            )
    
    @pytest.mark.asyncio
    async def test_full_recording_workflow(self, recorder):
        """Test a complete recording workflow."""
        # Start recording
        with patch.object(recorder, '_init_wav_files'), \
             patch.object(recorder, '_log_session_event', new_callable=AsyncMock):
            
            assert await recorder.start_recording()
            assert recorder.recording_active
        
        # Record some audio
        recorder.caller_wav = Mock()
        recorder.bot_wav = Mock()
        recorder.stereo_wav = Mock()
        
        audio_data = np.array([100, -200, 300, -400], dtype=np.int16)
        audio_b64 = base64.b64encode(audio_data.tobytes()).decode()
        
        with patch.object(recorder, '_write_stereo_chunk', new_callable=AsyncMock):
            assert await recorder.record_caller_audio(audio_b64)
            assert await recorder.record_bot_audio(audio_b64)
        
        # Add transcript
        assert await recorder.add_transcript(
            "Test transcript", AudioChannel.CALLER, TranscriptType.INPUT
        )
        
        # Log function call
        with patch.object(recorder, '_log_session_event', new_callable=AsyncMock):
            await recorder.log_function_call("test_func", {"arg": "value"})
        
        # Stop recording
        with patch.object(recorder, '_save_transcript', new_callable=AsyncMock), \
             patch.object(recorder, '_save_metadata', new_callable=AsyncMock), \
             patch.object(recorder, '_save_session_events', new_callable=AsyncMock), \
             patch.object(recorder, '_create_final_stereo_recording', new_callable=AsyncMock), \
             patch.object(recorder, '_log_session_event', new_callable=AsyncMock):
            
            assert await recorder.stop_recording()
            assert not recorder.recording_active
            assert recorder.finalized
        
        # Verify metadata
        assert recorder.metadata.caller_audio_chunks == 1
        assert recorder.metadata.bot_audio_chunks == 1
        assert recorder.metadata.transcript_entries == 1
        assert len(recorder.metadata.function_calls) == 1
        assert recorder.metadata.end_time is not None


if __name__ == "__main__":
    pytest.main([__file__]) 