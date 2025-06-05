"""
Unit tests for the Twilio API message schemas.

These tests validate that the Pydantic models correctly validate message data
and that the validation rules work as expected for Twilio Media Streams WebSocket protocol.
"""

import base64
import pytest
from pydantic import ValidationError

from opusagent.models.twilio_api import (
    TwilioEventType,
    BaseTwilioMessage,
    TwilioMessageWithSequence,
    TwilioMessageWithStreamSid,
    ConnectedMessage,
    MediaFormat,
    StartMetadata,
    StartMessage,
    MediaPayload,
    MediaMessage,
    StopMetadata,
    StopMessage,
    DTMFPayload,
    DTMFMessage,
    MarkPayload,
    MarkMessage,
    OutgoingMediaPayload,
    OutgoingMediaMessage,
    OutgoingMarkMessage,
    ClearMessage,
    IncomingMessage,
    OutgoingMessage,
    TwilioMessage,
    SID_PATTERN,
    DTMF_PATTERN,
    SUPPORTED_ENCODINGS,
    SUPPORTED_SAMPLE_RATES,
    SUPPORTED_CHANNELS,
)

# Test SIDs - Using clearly fake test values
TEST_ACCOUNT_SID = "ACtest1234567890abcdef1234567890abcdef"
TEST_CALL_SID = "CAtest1234567890abcdef1234567890abcdef"
TEST_STREAM_SID = "MStest1234567890abcdef1234567890abcdef"

class TestTwilioEventType:
    """Tests for the TwilioEventType enum."""

    def test_enum_values(self):
        """Test that all enum values are correct."""
        assert TwilioEventType.CONNECTED == "connected"
        assert TwilioEventType.START == "start"
        assert TwilioEventType.MEDIA == "media"
        assert TwilioEventType.STOP == "stop"
        assert TwilioEventType.DTMF == "dtmf"
        assert TwilioEventType.MARK == "mark"
        assert TwilioEventType.CLEAR == "clear"


class TestConstants:
    """Tests for validation constants."""

    def test_sid_pattern(self):
        """Test that SID pattern validation works correctly."""
        # Valid SIDs
        valid_sids = [
            TEST_STREAM_SID,  # Stream SID
            TEST_ACCOUNT_SID,  # Account SID
            TEST_CALL_SID,  # Call SID
        ]
        for sid in valid_sids:
            assert SID_PATTERN.match(sid) is not None

        # Invalid SIDs
        invalid_sids = [
            "invalid",
            "MS1234567890ABCDEF1234567890abcdef",  # Uppercase in hex part
            "MS1234567890abcdef1234567890abcde",   # Too short
            "MS1234567890abcdef1234567890abcdeff", # Too long
            "ms1234567890abcdef1234567890abcdef",  # Lowercase prefix
        ]
        for sid in invalid_sids:
            assert SID_PATTERN.match(sid) is None

    def test_dtmf_pattern(self):
        """Test that DTMF pattern validation works correctly."""
        # Valid DTMF digits
        valid_dtmf = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "*", "#", "A", "B", "C", "D"]
        for digit in valid_dtmf:
            assert DTMF_PATTERN.match(digit) is not None

        # Invalid DTMF
        invalid_dtmf = ["E", "Z", "abc", "10", "", " "]
        for digit in invalid_dtmf:
            assert DTMF_PATTERN.match(digit) is None

    def test_supported_formats(self):
        """Test that supported format constants are correct."""
        assert "audio/x-mulaw" in SUPPORTED_ENCODINGS
        assert 8000 in SUPPORTED_SAMPLE_RATES
        assert 1 in SUPPORTED_CHANNELS


class TestBaseTwilioMessage:
    """Tests for the BaseTwilioMessage class."""

    def test_valid_base_message(self):
        """Test that a valid base message can be created."""
        message = BaseTwilioMessage(event="test.event")
        assert message.event == "test.event"

    def test_missing_event(self):
        """Test that a message without an event raises a validation error."""
        with pytest.raises(ValidationError):
            BaseTwilioMessage()


class TestTwilioMessageWithSequence:
    """Tests for the TwilioMessageWithSequence class."""

    def test_valid_sequence_message(self):
        """Test that a valid sequence message can be created."""
        message = TwilioMessageWithSequence(event="test.event", sequenceNumber="123")
        assert message.event == "test.event"
        assert message.sequenceNumber == "123"

    def test_missing_sequence_number(self):
        """Test that a message without a sequence number raises a validation error."""
        with pytest.raises(ValidationError):
            TwilioMessageWithSequence(event="test.event")


class TestTwilioMessageWithStreamSid:
    """Tests for the TwilioMessageWithStreamSid class."""

    def test_valid_stream_sid_message(self):
        """Test that a valid stream SID message can be created."""
        message = TwilioMessageWithStreamSid(
            event="test.event",
            streamSid=TEST_STREAM_SID
        )
        assert message.event == "test.event"
        assert message.streamSid == TEST_STREAM_SID

    def test_invalid_stream_sid_format(self):
        """Test that an invalid stream SID format logs a warning but doesn't fail."""
        # This should not raise an exception but will log a warning
        message = TwilioMessageWithStreamSid(
            event="test.event",
            streamSid="invalid-sid"
        )
        assert message.streamSid == "invalid-sid"

    def test_missing_stream_sid(self):
        """Test that a message without a stream SID raises a validation error."""
        with pytest.raises(ValidationError):
            TwilioMessageWithStreamSid(event="test.event")


class TestConnectedMessage:
    """Tests for the ConnectedMessage class."""

    def test_valid_connected_message(self):
        """Test that a valid connected message can be created."""
        message = ConnectedMessage(
            event="connected",
            protocol="Call",
            version="1.0.0"
        )
        assert message.event == "connected"
        assert message.protocol == "Call"
        assert message.version == "1.0.0"

    def test_invalid_protocol(self):
        """Test that an invalid protocol logs a warning but doesn't fail."""
        message = ConnectedMessage(
            event="connected",
            protocol="InvalidProtocol",
            version="1.0.0"
        )
        assert message.protocol == "InvalidProtocol"

    def test_missing_required_fields(self):
        """Test that missing required fields raise validation errors."""
        with pytest.raises(ValidationError):
            ConnectedMessage(event="connected")


class TestMediaFormat:
    """Tests for the MediaFormat class."""

    def test_valid_media_format(self):
        """Test that a valid media format can be created."""
        format = MediaFormat(
            encoding="audio/x-mulaw",
            sampleRate=8000,
            channels=1
        )
        assert format.encoding == "audio/x-mulaw"
        assert format.sampleRate == 8000
        assert format.channels == 1

    def test_invalid_encoding(self):
        """Test that an invalid encoding raises a validation error."""
        with pytest.raises(ValidationError):
            MediaFormat(
                encoding="invalid/encoding",
                sampleRate=8000,
                channels=1
            )

    def test_invalid_sample_rate(self):
        """Test that an invalid sample rate raises a validation error."""
        with pytest.raises(ValidationError):
            MediaFormat(
                encoding="audio/x-mulaw",
                sampleRate=44100,
                channels=1
            )

    def test_invalid_channels(self):
        """Test that an invalid channel count raises a validation error."""
        with pytest.raises(ValidationError):
            MediaFormat(
                encoding="audio/x-mulaw",
                sampleRate=8000,
                channels=2
            )


class TestStartMetadata:
    """Tests for the StartMetadata class."""

    def test_valid_start_metadata(self):
        """Test that valid start metadata can be created."""
        metadata = StartMetadata(
            streamSid=TEST_STREAM_SID,
            accountSid=TEST_ACCOUNT_SID,
            callSid=TEST_CALL_SID,
            tracks=["inbound", "outbound"],
            customParameters={"param1": "value1"},
            mediaFormat=MediaFormat(
                encoding="audio/x-mulaw",
                sampleRate=8000,
                channels=1
            )
        )
        assert "inbound" in metadata.tracks
        assert "outbound" in metadata.tracks
        assert metadata.customParameters["param1"] == "value1"

    def test_invalid_tracks(self):
        """Test that invalid tracks raise a validation error."""
        with pytest.raises(ValidationError):
            StartMetadata(
                streamSid=TEST_STREAM_SID,
                accountSid=TEST_ACCOUNT_SID,
                callSid=TEST_CALL_SID,
                tracks=["invalid_track"],
                mediaFormat=MediaFormat(
                    encoding="audio/x-mulaw",
                    sampleRate=8000,
                    channels=1
                )
            )

    def test_empty_custom_parameters(self):
        """Test that empty custom parameters use default factory."""
        metadata = StartMetadata(
            streamSid=TEST_STREAM_SID,
            accountSid=TEST_ACCOUNT_SID,
            callSid=TEST_CALL_SID,
            tracks=["inbound"],
            mediaFormat=MediaFormat(
                encoding="audio/x-mulaw",
                sampleRate=8000,
                channels=1
            )
        )
        assert metadata.customParameters == {}


class TestStartMessage:
    """Tests for the StartMessage class."""

    def test_valid_start_message(self):
        """Test that a valid start message can be created."""
        message = StartMessage(
            event="start",
            sequenceNumber="1",
            streamSid=TEST_STREAM_SID,
            start=StartMetadata(
                streamSid=TEST_STREAM_SID,
                accountSid=TEST_ACCOUNT_SID,
                callSid=TEST_CALL_SID,
                tracks=["inbound"],
                mediaFormat=MediaFormat(
                    encoding="audio/x-mulaw",
                    sampleRate=8000,
                    channels=1
                )
            )
        )
        assert message.event == "start"
        assert message.sequenceNumber == "1"
        assert message.start.streamSid == TEST_STREAM_SID


class TestMediaPayload:
    """Tests for the MediaPayload class."""

    def test_valid_media_payload(self):
        """Test that a valid media payload can be created."""
        audio_data = base64.b64encode(b"test audio data").decode("utf-8")
        payload = MediaPayload(
            track="inbound",
            chunk="1",
            timestamp="1000",
            payload=audio_data
        )
        assert payload.track == "inbound"
        assert payload.chunk == "1"
        assert payload.timestamp == "1000"
        assert payload.payload == audio_data

    def test_invalid_track(self):
        """Test that an invalid track raises a validation error."""
        audio_data = base64.b64encode(b"test audio data").decode("utf-8")
        with pytest.raises(ValidationError):
            MediaPayload(
                track="invalid_track",
                chunk="1",
                timestamp="1000",
                payload=audio_data
            )

    def test_empty_payload(self):
        """Test that an empty payload raises a validation error."""
        with pytest.raises(ValidationError):
            MediaPayload(
                track="inbound",
                chunk="1",
                timestamp="1000",
                payload=""
            )

    def test_invalid_base64_payload(self):
        """Test that an invalid base64 payload raises a validation error."""
        with pytest.raises(ValidationError):
            MediaPayload(
                track="inbound",
                chunk="1",
                timestamp="1000",
                payload="not valid base64!"
            )


class TestMediaMessage:
    """Tests for the MediaMessage class."""

    def test_valid_media_message(self):
        """Test that a valid media message can be created."""
        audio_data = base64.b64encode(b"test audio data").decode("utf-8")
        message = MediaMessage(
            event="media",
            sequenceNumber="2",
            streamSid=TEST_STREAM_SID,
            media=MediaPayload(
                track="inbound",
                chunk="1",
                timestamp="1000",
                payload=audio_data
            )
        )
        assert message.event == "media"
        assert message.media.track == "inbound"


class TestStopMessage:
    """Tests for the StopMessage class."""

    def test_valid_stop_message(self):
        """Test that a valid stop message can be created."""
        message = StopMessage(
            event="stop",
            sequenceNumber="5",
            streamSid=TEST_STREAM_SID,
            stop=StopMetadata(
                accountSid=TEST_ACCOUNT_SID,
                callSid=TEST_CALL_SID
            )
        )
        assert message.event == "stop"
        assert message.stop.accountSid == TEST_ACCOUNT_SID


class TestDTMFPayload:
    """Tests for the DTMFPayload class."""

    def test_valid_dtmf_payload(self):
        """Test that a valid DTMF payload can be created."""
        payload = DTMFPayload(track="inbound_track", digit="1")
        assert payload.track == "inbound_track"
        assert payload.digit == "1"

    def test_invalid_dtmf_digit(self):
        """Test that an invalid DTMF digit raises a validation error."""
        with pytest.raises(ValidationError):
            DTMFPayload(track="inbound_track", digit="Z")

    def test_invalid_track_warning(self):
        """Test that an invalid track logs a warning but doesn't fail."""
        payload = DTMFPayload(track="invalid_track", digit="1")
        assert payload.track == "invalid_track"


class TestDTMFMessage:
    """Tests for the DTMFMessage class."""

    def test_valid_dtmf_message(self):
        """Test that a valid DTMF message can be created."""
        message = DTMFMessage(
            event="dtmf",
            sequenceNumber="3",
            streamSid=TEST_STREAM_SID,
            dtmf=DTMFPayload(track="inbound_track", digit="5")
        )
        assert message.event == "dtmf"
        assert message.dtmf.digit == "5"


class TestMarkPayload:
    """Tests for the MarkPayload class."""

    def test_valid_mark_payload(self):
        """Test that a valid mark payload can be created."""
        payload = MarkPayload(name="my_label")
        assert payload.name == "my_label"


class TestMarkMessage:
    """Tests for the MarkMessage class."""

    def test_valid_mark_message(self):
        """Test that a valid mark message can be created."""
        message = MarkMessage(
            event="mark",
            sequenceNumber="4",
            streamSid=TEST_STREAM_SID,
            mark=MarkPayload(name="test_mark")
        )
        assert message.event == "mark"
        assert message.mark.name == "test_mark"


class TestOutgoingMediaPayload:
    """Tests for the OutgoingMediaPayload class."""

    def test_valid_outgoing_media_payload(self):
        """Test that a valid outgoing media payload can be created."""
        audio_data = base64.b64encode(b"test audio data").decode("utf-8")
        payload = OutgoingMediaPayload(payload=audio_data)
        assert payload.payload == audio_data

    def test_empty_outgoing_payload(self):
        """Test that an empty outgoing payload raises a validation error."""
        with pytest.raises(ValidationError):
            OutgoingMediaPayload(payload="")

    def test_invalid_base64_outgoing_payload(self):
        """Test that an invalid base64 outgoing payload raises a validation error."""
        with pytest.raises(ValidationError):
            OutgoingMediaPayload(payload="not valid base64!")


class TestOutgoingMediaMessage:
    """Tests for the OutgoingMediaMessage class."""

    def test_valid_outgoing_media_message(self):
        """Test that a valid outgoing media message can be created."""
        audio_data = base64.b64encode(b"test audio data").decode("utf-8")
        message = OutgoingMediaMessage(
            event="media",
            streamSid=TEST_STREAM_SID,
            media=OutgoingMediaPayload(payload=audio_data)
        )
        assert message.event == "media"
        assert message.media.payload == audio_data


class TestOutgoingMarkMessage:
    """Tests for the OutgoingMarkMessage class."""

    def test_valid_outgoing_mark_message(self):
        """Test that a valid outgoing mark message can be created."""
        message = OutgoingMarkMessage(
            event="mark",
            streamSid=TEST_STREAM_SID,
            mark=MarkPayload(name="my_mark")
        )
        assert message.event == "mark"
        assert message.mark.name == "my_mark"


class TestClearMessage:
    """Tests for the ClearMessage class."""

    def test_valid_clear_message(self):
        """Test that a valid clear message can be created."""
        message = ClearMessage(
            event="clear",
            streamSid=TEST_STREAM_SID
        )
        assert message.event == "clear"
        assert message.streamSid == TEST_STREAM_SID


class TestUnionTypes:
    """Tests for union type validation."""

    def test_incoming_message_union(self):
        """Test that incoming message union works correctly."""
        # Test ConnectedMessage
        connected = ConnectedMessage(
            event="connected",
            protocol="Call",
            version="1.0.0"
        )
        # Should be valid as IncomingMessage
        incoming: IncomingMessage = connected
        assert isinstance(incoming, ConnectedMessage)

        # Test MediaMessage
        audio_data = base64.b64encode(b"test audio data").decode("utf-8")
        media = MediaMessage(
            event="media",
            sequenceNumber="2",
            streamSid=TEST_STREAM_SID,
            media=MediaPayload(
                track="inbound",
                chunk="1",
                timestamp="1000",
                payload=audio_data
            )
        )
        incoming = media
        assert isinstance(incoming, MediaMessage)

    def test_outgoing_message_union(self):
        """Test that outgoing message union works correctly."""
        # Test OutgoingMediaMessage
        audio_data = base64.b64encode(b"test audio data").decode("utf-8")
        outgoing_media = OutgoingMediaMessage(
            event="media",
            streamSid=TEST_STREAM_SID,
            media=OutgoingMediaPayload(payload=audio_data)
        )
        outgoing: OutgoingMessage = outgoing_media
        assert isinstance(outgoing, OutgoingMediaMessage)

        # Test ClearMessage
        clear = ClearMessage(
            event="clear",
            streamSid=TEST_STREAM_SID
        )
        outgoing = clear
        assert isinstance(outgoing, ClearMessage)

    def test_twilio_message_union(self):
        """Test that TwilioMessage union includes both incoming and outgoing."""
        # Test with incoming message
        connected = ConnectedMessage(
            event="connected",
            protocol="Call",
            version="1.0.0"
        )
        twilio_msg: TwilioMessage = connected
        assert isinstance(twilio_msg, ConnectedMessage)

        # Test with outgoing message
        clear = ClearMessage(
            event="clear",
            streamSid=TEST_STREAM_SID
        )
        twilio_msg = clear
        assert isinstance(twilio_msg, ClearMessage)


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_special_dtmf_characters(self):
        """Test that all special DTMF characters are accepted."""
        special_chars = ["*", "#", "A", "B", "C", "D"]
        for char in special_chars:
            payload = DTMFPayload(track="inbound_track", digit=char)
            assert payload.digit == char

    def test_boundary_values(self):
        """Test boundary values for various fields."""
        # Test minimum valid chunk number
        audio_data = base64.b64encode(b"test").decode("utf-8")
        payload = MediaPayload(
            track="inbound",
            chunk="0",
            timestamp="0",
            payload=audio_data
        )
        assert payload.chunk == "0"

    def test_unicode_in_mark_name(self):
        """Test that unicode characters work in mark names."""
        payload = MarkPayload(name="test_mark_🎵")
        assert payload.name == "test_mark_🎵"

    def test_large_base64_payload(self):
        """Test that large base64 payloads are handled correctly."""
        large_data = b"x" * 10000  # 10KB of data
        audio_data = base64.b64encode(large_data).decode("utf-8")
        payload = OutgoingMediaPayload(payload=audio_data)
        assert len(payload.payload) > 10000 