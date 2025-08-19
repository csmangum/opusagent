"""
Unit tests for the models module.

This module tests the configuration models defined in opusagent.config.models to ensure
they have the expected structure, validation, and behavior.
"""

import pytest
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Any

from opusagent.config.models import (
    Environment,
    LogLevel,
    ServerConfig,
    OpenAIConfig,
    AudioConfig,
    VADConfig,
    TranscriptionConfig,
    WebSocketConfig,
    QualityMonitoringConfig,
    AudioStreamHandlerConfig,
    LoggingConfig,
    MockConfig,
    TUIConfig,
    StaticDataConfig,
    SecurityConfig,
    ApplicationConfig,
)


class TestEnvironment:
    """Test Environment enum."""

    def test_environment_values(self):
        """Test that Environment enum has the expected values."""
        assert Environment.DEVELOPMENT.value == "development"
        assert Environment.PRODUCTION.value == "production"
        assert Environment.TESTING.value == "testing"

    def test_environment_enumeration(self):
        """Test that Environment enum can be enumerated."""
        environments = list(Environment)
        assert len(environments) == 3
        assert Environment.DEVELOPMENT in environments
        assert Environment.PRODUCTION in environments
        assert Environment.TESTING in environments

    def test_environment_string_representation(self):
        """Test that Environment enum values are strings."""
        for env in Environment:
            assert isinstance(env.value, str)
            assert len(env.value) > 0


class TestLogLevel:
    """Test LogLevel enum."""

    def test_log_level_values(self):
        """Test that LogLevel enum has the expected values."""
        assert LogLevel.DEBUG.value == "DEBUG"
        assert LogLevel.INFO.value == "INFO"
        assert LogLevel.WARNING.value == "WARNING"
        assert LogLevel.ERROR.value == "ERROR"
        assert LogLevel.CRITICAL.value == "CRITICAL"

    def test_log_level_enumeration(self):
        """Test that LogLevel enum can be enumerated."""
        log_levels = list(LogLevel)
        assert len(log_levels) == 5
        assert LogLevel.DEBUG in log_levels
        assert LogLevel.INFO in log_levels
        assert LogLevel.WARNING in log_levels
        assert LogLevel.ERROR in log_levels
        assert LogLevel.CRITICAL in log_levels

    def test_log_level_string_representation(self):
        """Test that LogLevel enum values are strings."""
        for level in LogLevel:
            assert isinstance(level.value, str)
            assert len(level.value) > 0


class TestServerConfig:
    """Test ServerConfig dataclass."""

    def test_server_config_defaults(self):
        """Test that ServerConfig has the expected default values."""
        config = ServerConfig()
        
        assert config.host == "0.0.0.0"
        assert config.port == 8080
        assert config.environment == Environment.PRODUCTION
        assert config.debug is False
        assert config.reload is False
        assert config.workers == 1
        assert config.timeout_keep_alive == 5
        assert config.http_protocol == "h11"
        assert config.access_log is False
        assert config.ws_ping_interval == 5
        assert config.ws_ping_timeout == 10
        assert config.ws_max_size == 16 * 1024 * 1024

    def test_server_config_custom_values(self):
        """Test that ServerConfig can be created with custom values."""
        config = ServerConfig(
            host="localhost",
            port=9000,
            environment=Environment.DEVELOPMENT,
            debug=True,
            reload=True,
            workers=4,
            timeout_keep_alive=10,
            http_protocol="h2",
            access_log=True,
            ws_ping_interval=10,
            ws_ping_timeout=20,
            ws_max_size=32 * 1024 * 1024
        )
        
        assert config.host == "localhost"
        assert config.port == 9000
        assert config.environment == Environment.DEVELOPMENT
        assert config.debug is True
        assert config.reload is True
        assert config.workers == 4
        assert config.timeout_keep_alive == 10
        assert config.http_protocol == "h2"
        assert config.access_log is True
        assert config.ws_ping_interval == 10
        assert config.ws_ping_timeout == 20
        assert config.ws_max_size == 32 * 1024 * 1024

    def test_server_config_validation(self):
        """Test that ServerConfig validates its values."""
        # Valid port range
        config = ServerConfig(port=1)
        assert config.port == 1
        
        config = ServerConfig(port=65535)
        assert config.port == 65535
        
        # Valid environment
        config = ServerConfig(environment=Environment.DEVELOPMENT)
        assert config.environment == Environment.DEVELOPMENT


class TestOpenAIConfig:
    """Test OpenAIConfig dataclass."""

    def test_openai_config_defaults(self):
        """Test that OpenAIConfig has the expected default values."""
        config = OpenAIConfig()
        
        assert config.api_key is None
        assert config.model == "gpt-4o-realtime-preview-2024-12-17"
        assert config.base_url == "wss://api.openai.com"
        assert config.timeout == 30
        assert config.max_retries == 3

    def test_openai_config_custom_values(self):
        """Test that OpenAIConfig can be created with custom values."""
        config = OpenAIConfig(
            api_key="test-key",
            model="gpt-4",
            base_url="https://api.openai.com",
            timeout=60,
            max_retries=5
        )
        
        assert config.api_key == "test-key"
        assert config.model == "gpt-4"
        assert config.base_url == "https://api.openai.com"
        assert config.timeout == 60
        assert config.max_retries == 5

    def test_get_websocket_url(self):
        """Test that get_websocket_url returns the expected URL."""
        config = OpenAIConfig(
            base_url="wss://api.openai.com",
            model="gpt-4o-realtime-preview-2024-12-17"
        )
        
        expected_url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17"
        assert config.get_websocket_url() == expected_url

    def test_get_headers_with_api_key(self):
        """Test that get_headers returns the expected headers with API key."""
        config = OpenAIConfig(api_key="test-key")
        
        headers = config.get_headers()
        assert headers["Authorization"] == "Bearer test-key"
        assert headers["OpenAI-Beta"] == "realtime=v1"

    def test_get_headers_without_api_key(self):
        """Test that get_headers raises ValueError without API key."""
        config = OpenAIConfig(api_key=None)
        
        with pytest.raises(ValueError, match="OpenAI API key is required"):
            config.get_headers()

    def test_get_headers_with_empty_api_key(self):
        """Test that get_headers raises ValueError with empty API key."""
        config = OpenAIConfig(api_key="")
        
        with pytest.raises(ValueError, match="OpenAI API key is required"):
            config.get_headers()


class TestAudioConfig:
    """Test AudioConfig dataclass."""

    def test_audio_config_defaults(self):
        """Test that AudioConfig has the expected default values."""
        config = AudioConfig()
        
        assert config.sample_rate == 24000
        assert config.channels == 1
        assert config.bits_per_sample == 16
        assert config.chunk_size == 4800
        assert config.chunk_size_large == 48000
        assert config.format == "raw/lpcm16"
        assert "raw/lpcm16" in config.supported_formats
        assert "g711/ulaw" in config.supported_formats
        assert "g711/alaw" in config.supported_formats

    def test_audio_config_custom_values(self):
        """Test that AudioConfig can be created with custom values."""
        config = AudioConfig(
            sample_rate=16000,
            channels=2,
            bits_per_sample=24,
            chunk_size=3200,
            chunk_size_large=32000,
            format="g711/ulaw",
            supported_formats=["g711/ulaw", "g711/alaw"]
        )
        
        assert config.sample_rate == 16000
        assert config.channels == 2
        assert config.bits_per_sample == 24
        assert config.chunk_size == 3200
        assert config.chunk_size_large == 32000
        assert config.format == "g711/ulaw"
        assert config.supported_formats == ["g711/ulaw", "g711/alaw"]

    def test_supported_formats_default(self):
        """Test that supported_formats has the expected default values."""
        config = AudioConfig()
        expected_formats = ["raw/lpcm16", "g711/ulaw", "g711/alaw"]
        
        for fmt in expected_formats:
            assert fmt in config.supported_formats


class TestVADConfig:
    """Test VADConfig dataclass."""

    def test_vad_config_defaults(self):
        """Test that VADConfig has the expected default values."""
        config = VADConfig()
        
        assert config.enabled is True
        assert config.backend == "silero"
        assert config.confidence_threshold == 0.5
        assert config.silence_threshold == 0.6
        assert config.min_speech_duration_ms == 500
        assert config.speech_start_threshold == 2
        assert config.speech_stop_threshold == 3
        assert config.device == "cpu"
        assert config.chunk_size == 768
        assert config.confidence_history_size == 5
        assert config.force_stop_timeout_ms == 2000
        assert config.sample_rate == 24000

    def test_vad_config_custom_values(self):
        """Test that VADConfig can be created with custom values."""
        config = VADConfig(
            enabled=False,
            backend="whisper",
            confidence_threshold=0.7,
            silence_threshold=0.8,
            min_speech_duration_ms=1000,
            speech_start_threshold=3,
            speech_stop_threshold=5,
            device="cuda",
            chunk_size=1024,
            confidence_history_size=10,
            force_stop_timeout_ms=3000,
            sample_rate=16000
        )
        
        assert config.enabled is False
        assert config.backend == "whisper"
        assert config.confidence_threshold == 0.7
        assert config.silence_threshold == 0.8
        assert config.min_speech_duration_ms == 1000
        assert config.speech_start_threshold == 3
        assert config.speech_stop_threshold == 5
        assert config.device == "cuda"
        assert config.chunk_size == 1024
        assert config.confidence_history_size == 10
        assert config.force_stop_timeout_ms == 3000
        assert config.sample_rate == 16000


class TestTranscriptionConfig:
    """Test TranscriptionConfig dataclass."""

    def test_transcription_config_defaults(self):
        """Test that TranscriptionConfig has the expected default values."""
        config = TranscriptionConfig()
        
        assert config.enabled is True
        assert config.backend == "pocketsphinx"
        assert config.language == "en"
        assert config.model_size == "base"
        assert config.chunk_duration == 1.0
        assert config.confidence_threshold == 0.5
        assert config.sample_rate == 24000
        assert config.enable_vad is True
        assert config.device == "cpu"
        assert config.pocketsphinx_hmm is None
        assert config.pocketsphinx_lm is None
        assert config.pocketsphinx_dict is None
        assert config.pocketsphinx_audio_preprocessing == "normalize"
        assert config.pocketsphinx_vad_settings == "conservative"
        assert config.pocketsphinx_auto_resample is True
        assert config.pocketsphinx_input_sample_rate == 24000
        assert config.whisper_model_dir is None
        assert config.whisper_temperature == 0.0

    def test_transcription_config_custom_values(self):
        """Test that TranscriptionConfig can be created with custom values."""
        config = TranscriptionConfig(
            enabled=False,
            backend="whisper",
            language="es",
            model_size="large",
            chunk_duration=2.0,
            confidence_threshold=0.8,
            sample_rate=16000,
            enable_vad=False,
            device="cuda",
            pocketsphinx_hmm="/path/to/hmm",
            pocketsphinx_lm="/path/to/lm",
            pocketsphinx_dict="/path/to/dict",
            pocketsphinx_audio_preprocessing="amplify",
            pocketsphinx_vad_settings="aggressive",
            pocketsphinx_auto_resample=False,
            pocketsphinx_input_sample_rate=16000,
            whisper_model_dir="/path/to/models",
            whisper_temperature=0.3
        )
        
        assert config.enabled is False
        assert config.backend == "whisper"
        assert config.language == "es"
        assert config.model_size == "large"
        assert config.chunk_duration == 2.0
        assert config.confidence_threshold == 0.8
        assert config.sample_rate == 16000
        assert config.enable_vad is False
        assert config.device == "cuda"
        assert config.pocketsphinx_hmm == "/path/to/hmm"
        assert config.pocketsphinx_lm == "/path/to/lm"
        assert config.pocketsphinx_dict == "/path/to/dict"
        assert config.pocketsphinx_audio_preprocessing == "amplify"
        assert config.pocketsphinx_vad_settings == "aggressive"
        assert config.pocketsphinx_auto_resample is False
        assert config.pocketsphinx_input_sample_rate == 16000
        assert config.whisper_model_dir == "/path/to/models"
        assert config.whisper_temperature == 0.3


class TestWebSocketConfig:
    """Test WebSocketConfig dataclass."""

    def test_websocket_config_defaults(self):
        """Test that WebSocketConfig has the expected default values."""
        config = WebSocketConfig()
        
        assert config.max_connections == 10
        assert config.max_connection_age == 3600.0
        assert config.max_idle_time == 300.0
        assert config.health_check_interval == 30.0
        assert config.max_sessions_per_connection == 10
        assert config.ping_interval == 20
        assert config.ping_timeout == 30
        assert config.close_timeout == 10

    def test_websocket_config_custom_values(self):
        """Test that WebSocketConfig can be created with custom values."""
        config = WebSocketConfig(
            max_connections=20,
            max_connection_age=7200.0,
            max_idle_time=600.0,
            health_check_interval=60.0,
            max_sessions_per_connection=20,
            ping_interval=30,
            ping_timeout=45,
            close_timeout=15
        )
        
        assert config.max_connections == 20
        assert config.max_connection_age == 7200.0
        assert config.max_idle_time == 600.0
        assert config.health_check_interval == 60.0
        assert config.max_sessions_per_connection == 20
        assert config.ping_interval == 30
        assert config.ping_timeout == 45
        assert config.close_timeout == 15


class TestQualityMonitoringConfig:
    """Test QualityMonitoringConfig dataclass."""

    def test_quality_monitoring_config_defaults(self):
        """Test that QualityMonitoringConfig has the expected default values."""
        config = QualityMonitoringConfig()
        
        assert config.enabled is True
        assert config.min_snr_db == 15.0
        assert config.max_thd_percent == 1.0
        assert config.max_clipping_percent == 0.1
        assert config.min_quality_score == 60.0
        assert config.min_audio_level == 0.01
        assert config.sample_rate == 24000
        assert config.chunk_size == 1024
        assert config.history_size == 100
        assert config.enable_alerts is True
        assert config.alert_log_level == "WARNING"
        assert config.enable_realtime_logging is True
        assert config.enable_summary_reports is True
        assert config.summary_interval_seconds == 60

    def test_quality_monitoring_config_custom_values(self):
        """Test that QualityMonitoringConfig can be created with custom values."""
        config = QualityMonitoringConfig(
            enabled=False,
            min_snr_db=20.0,
            max_thd_percent=2.0,
            max_clipping_percent=0.2,
            min_quality_score=70.0,
            min_audio_level=0.02,
            sample_rate=16000,
            chunk_size=2048,
            history_size=200,
            enable_alerts=False,
            alert_log_level="ERROR",
            enable_realtime_logging=False,
            enable_summary_reports=False,
            summary_interval_seconds=120
        )
        
        assert config.enabled is False
        assert config.min_snr_db == 20.0
        assert config.max_thd_percent == 2.0
        assert config.max_clipping_percent == 0.2
        assert config.min_quality_score == 70.0
        assert config.min_audio_level == 0.02
        assert config.sample_rate == 16000
        assert config.chunk_size == 2048
        assert config.history_size == 200
        assert config.enable_alerts is False
        assert config.alert_log_level == "ERROR"
        assert config.enable_realtime_logging is False
        assert config.enable_summary_reports is False
        assert config.summary_interval_seconds == 120


class TestAudioStreamHandlerConfig:
    """Test AudioStreamHandlerConfig dataclass."""

    def test_audio_stream_handler_config_defaults(self):
        """Test that AudioStreamHandlerConfig has the expected default values."""
        config = AudioStreamHandlerConfig()
        
        assert config.internal_sample_rate == 24000
        assert config.min_audio_bytes == 4800
        assert config.openai_sample_rate == 24000
        assert config.enable_quality_monitoring is False
        assert config.vad_enabled is True
        assert config.bridge_type == "unknown"

    def test_audio_stream_handler_config_custom_values(self):
        """Test that AudioStreamHandlerConfig can be created with custom values."""
        config = AudioStreamHandlerConfig(
            internal_sample_rate=16000,
            min_audio_bytes=3200,
            openai_sample_rate=16000,
            enable_quality_monitoring=True,
            vad_enabled=False,
            bridge_type="twilio"
        )
        
        assert config.internal_sample_rate == 16000
        assert config.min_audio_bytes == 3200
        assert config.openai_sample_rate == 16000
        assert config.enable_quality_monitoring is True
        assert config.vad_enabled is False
        assert config.bridge_type == "twilio"


class TestLoggingConfig:
    """Test LoggingConfig dataclass."""

    def test_logging_config_defaults(self):
        """Test that LoggingConfig has the expected default values."""
        config = LoggingConfig()
        
        assert config.level == LogLevel.INFO
        assert config.format == "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        assert config.log_dir == Path("logs")
        assert config.log_filename == "opusagent.log"
        assert config.max_log_size == 10 * 1024 * 1024
        assert config.backup_count == 5
        assert config.console_output is True
        assert config.file_output is True

    def test_logging_config_custom_values(self):
        """Test that LoggingConfig can be created with custom values."""
        config = LoggingConfig(
            level=LogLevel.DEBUG,
            format="%(levelname)s: %(message)s",
            log_dir=Path("/custom/logs"),
            log_filename="custom.log",
            max_log_size=20 * 1024 * 1024,
            backup_count=10,
            console_output=False,
            file_output=True
        )
        
        assert config.level == LogLevel.DEBUG
        assert config.format == "%(levelname)s: %(message)s"
        assert config.log_dir == Path("/custom/logs")
        assert config.log_filename == "custom.log"
        assert config.max_log_size == 20 * 1024 * 1024
        assert config.backup_count == 10
        assert config.console_output is False
        assert config.file_output is True


class TestMockConfig:
    """Test MockConfig dataclass."""

    def test_mock_config_defaults(self):
        """Test that MockConfig has the expected default values."""
        config = MockConfig()
        
        assert config.enabled is False
        assert config.server_url == "ws://localhost:8080"
        assert config.use_local_realtime is False
        assert config.enable_transcription is True
        assert config.setup_smart_responses is True

    def test_mock_config_custom_values(self):
        """Test that MockConfig can be created with custom values."""
        config = MockConfig(
            enabled=True,
            server_url="ws://localhost:9000",
            use_local_realtime=True,
            enable_transcription=False,
            setup_smart_responses=False
        )
        
        assert config.enabled is True
        assert config.server_url == "ws://localhost:9000"
        assert config.use_local_realtime is True
        assert config.enable_transcription is False
        assert config.setup_smart_responses is False


class TestTUIConfig:
    """Test TUIConfig dataclass."""

    def test_tui_config_defaults(self):
        """Test that TUIConfig has the expected default values."""
        config = TUIConfig()
        
        assert config.host == "localhost"
        assert config.port == 8080
        assert config.ws_path == "/voice-bot"
        assert config.timeout_seconds == 15
        assert config.ping_interval == 5
        assert config.ping_timeout == 20
        assert config.reconnect_attempts == 3
        assert config.reconnect_delay == 2
        assert config.bot_name == "voice-bot"
        assert config.caller_id == "tui-validator"
        assert config.session_timeout == 300
        assert config.auto_reconnect is True
        assert config.vad_enabled is True
        assert config.show_vad_events is True
        assert config.enable_audio_recording is True
        assert config.recordings_dir == "test_logs"
        assert config.max_recording_duration == 300
        assert config.refresh_rate == 60
        assert config.log_max_lines == 1000
        assert config.transcript_max_lines == 500
        assert config.events_max_lines == 200
        assert config.show_audio_chunks is False
        assert config.show_debug_messages is True
        assert config.filter_heartbeat_messages is True
        assert config.max_events == 1000
        assert config.log_level == "INFO"
        assert config.export_format == "json"
        assert config.auto_export_on_session_end is False
        assert config.theme == "dark"
        assert config.show_timestamps is True
        assert config.show_latency is True

    def test_tui_config_custom_values(self):
        """Test that TUIConfig can be created with custom values."""
        config = TUIConfig(
            host="127.0.0.1",
            port=9000,
            ws_path="/custom-bot",
            timeout_seconds=30,
            ping_interval=10,
            ping_timeout=30,
            reconnect_attempts=5,
            reconnect_delay=5,
            bot_name="custom-bot",
            caller_id="custom-validator",
            session_timeout=600,
            auto_reconnect=False,
            vad_enabled=False,
            show_vad_events=False,
            enable_audio_recording=False,
            recordings_dir="/custom/recordings",
            max_recording_duration=600,
            refresh_rate=30,
            log_max_lines=500,
            transcript_max_lines=250,
            events_max_lines=100,
            show_audio_chunks=True,
            show_debug_messages=False,
            filter_heartbeat_messages=False,
            max_events=500,
            log_level="DEBUG",
            export_format="csv",
            auto_export_on_session_end=True,
            theme="light",
            show_timestamps=False,
            show_latency=False
        )
        
        assert config.host == "127.0.0.1"
        assert config.port == 9000
        assert config.ws_path == "/custom-bot"
        assert config.timeout_seconds == 30
        assert config.ping_interval == 10
        assert config.ping_timeout == 30
        assert config.reconnect_attempts == 5
        assert config.reconnect_delay == 5
        assert config.bot_name == "custom-bot"
        assert config.caller_id == "custom-validator"
        assert config.session_timeout == 600
        assert config.auto_reconnect is False
        assert config.vad_enabled is False
        assert config.show_vad_events is False
        assert config.enable_audio_recording is False
        assert config.recordings_dir == "/custom/recordings"
        assert config.max_recording_duration == 600
        assert config.refresh_rate == 30
        assert config.log_max_lines == 500
        assert config.transcript_max_lines == 250
        assert config.events_max_lines == 100
        assert config.show_audio_chunks is True
        assert config.show_debug_messages is False
        assert config.filter_heartbeat_messages is False
        assert config.max_events == 500
        assert config.log_level == "DEBUG"
        assert config.export_format == "csv"
        assert config.auto_export_on_session_end is True
        assert config.theme == "light"
        assert config.show_timestamps is False
        assert config.show_latency is False


class TestStaticDataConfig:
    """Test StaticDataConfig dataclass."""

    def test_static_data_config_defaults(self):
        """Test that StaticDataConfig has the expected default values."""
        config = StaticDataConfig()
        
        assert config.scenarios_file == Path("scenarios.json")
        assert config.phrases_mapping_file == Path("opusagent/local/audio/phrases_mapping.yml")
        assert config.audio_directory == Path("opusagent/local/audio")

    def test_static_data_config_custom_values(self):
        """Test that StaticDataConfig can be created with custom values."""
        config = StaticDataConfig(
            scenarios_file=Path("/custom/scenarios.json"),
            phrases_mapping_file=Path("/custom/phrases.yml"),
            audio_directory=Path("/custom/audio")
        )
        
        assert config.scenarios_file == Path("/custom/scenarios.json")
        assert config.phrases_mapping_file == Path("/custom/phrases.yml")
        assert config.audio_directory == Path("/custom/audio")


class TestSecurityConfig:
    """Test SecurityConfig dataclass."""

    def test_security_config_defaults(self):
        """Test that SecurityConfig has the expected default values."""
        config = SecurityConfig()
        
        assert config.api_key_validation is True
        assert config.rate_limiting_enabled is True
        assert config.max_requests_per_minute == 100
        assert config.require_ssl is False
        assert config.allowed_origins == ["*"]

    def test_security_config_custom_values(self):
        """Test that SecurityConfig can be created with custom values."""
        config = SecurityConfig(
            api_key_validation=False,
            rate_limiting_enabled=False,
            max_requests_per_minute=200,
            require_ssl=True,
            allowed_origins=["https://example.com", "https://test.com"]
        )
        
        assert config.api_key_validation is False
        assert config.rate_limiting_enabled is False
        assert config.max_requests_per_minute == 200
        assert config.require_ssl is True
        assert config.allowed_origins == ["https://example.com", "https://test.com"]


class TestApplicationConfig:
    """Test ApplicationConfig dataclass."""

    def test_application_config_defaults(self):
        """Test that ApplicationConfig has the expected default values."""
        config = ApplicationConfig()
        
        assert isinstance(config.server, ServerConfig)
        assert isinstance(config.openai, OpenAIConfig)
        assert isinstance(config.audio, AudioConfig)
        assert isinstance(config.vad, VADConfig)
        assert isinstance(config.transcription, TranscriptionConfig)
        assert isinstance(config.websocket, WebSocketConfig)
        assert isinstance(config.quality, QualityMonitoringConfig)
        assert isinstance(config.audio_stream_handler, AudioStreamHandlerConfig)
        assert isinstance(config.logging, LoggingConfig)
        assert isinstance(config.mock, MockConfig)
        assert isinstance(config.tui, TUIConfig)
        assert isinstance(config.static_data, StaticDataConfig)
        assert isinstance(config.security, SecurityConfig)

    def test_application_config_custom_values(self):
        """Test that ApplicationConfig can be created with custom values."""
        custom_server = ServerConfig(host="localhost", port=9000)
        custom_openai = OpenAIConfig(api_key="test-key")
        
        config = ApplicationConfig(
            server=custom_server,
            openai=custom_openai
        )
        
        assert config.server == custom_server
        assert config.openai == custom_openai
        # Other configs should still have defaults
        assert isinstance(config.audio, AudioConfig)
        assert isinstance(config.vad, VADConfig)

    def test_validate_with_valid_config(self):
        """Test that validate returns empty list for valid config."""
        config = ApplicationConfig()
        config.openai.api_key = "test-key"
        
        errors = config.validate()
        assert isinstance(errors, list)
        assert len(errors) == 0

    def test_validate_without_openai_key(self):
        """Test that validate returns error without OpenAI API key."""
        config = ApplicationConfig()
        config.openai.api_key = None
        config.mock.enabled = False
        
        errors = config.validate()
        assert isinstance(errors, list)
        assert len(errors) == 1
        assert "OpenAI API key is required" in errors[0]

    def test_validate_with_mock_enabled(self):
        """Test that validate passes when mock mode is enabled."""
        config = ApplicationConfig()
        config.openai.api_key = None
        config.mock.enabled = True
        
        errors = config.validate()
        assert isinstance(errors, list)
        assert len(errors) == 0

    def test_validate_invalid_port(self):
        """Test that validate returns error for invalid port."""
        config = ApplicationConfig()
        config.openai.api_key = "test-key"
        config.server.port = 0  # Invalid port
        
        errors = config.validate()
        assert isinstance(errors, list)
        assert len(errors) == 1
        assert "Server port must be between 1 and 65535" in errors[0]

    def test_validate_invalid_sample_rate(self):
        """Test that validate returns error for invalid sample rate."""
        config = ApplicationConfig()
        config.openai.api_key = "test-key"
        config.audio.sample_rate = 0  # Invalid sample rate
        
        errors = config.validate()
        assert isinstance(errors, list)
        assert len(errors) == 1
        assert "Audio sample rate must be positive" in errors[0]

    def test_validate_invalid_vad_threshold(self):
        """Test that validate returns error for invalid VAD threshold."""
        config = ApplicationConfig()
        config.openai.api_key = "test-key"
        config.vad.confidence_threshold = 1.5  # Invalid threshold
        
        errors = config.validate()
        assert isinstance(errors, list)
        assert len(errors) == 1
        assert "VAD confidence threshold must be between 0 and 1" in errors[0]

    def test_validate_invalid_transcription_threshold(self):
        """Test that validate returns error for invalid transcription threshold."""
        config = ApplicationConfig()
        config.openai.api_key = "test-key"
        config.transcription.confidence_threshold = -0.1  # Invalid threshold
        
        errors = config.validate()
        assert isinstance(errors, list)
        assert len(errors) == 1
        assert "Transcription confidence threshold must be between 0 and 1" in errors[0]

    def test_validate_multiple_errors(self):
        """Test that validate returns multiple errors."""
        config = ApplicationConfig()
        config.openai.api_key = None
        config.mock.enabled = False
        config.server.port = 0
        config.audio.sample_rate = 0
        
        errors = config.validate()
        assert isinstance(errors, list)
        assert len(errors) == 3
        assert any("OpenAI API key is required" in error for error in errors)
        assert any("Server port must be between 1 and 65535" in error for error in errors)
        assert any("Audio sample rate must be positive" in error for error in errors)

    def test_is_development(self):
        """Test that is_development returns correct value."""
        config = ApplicationConfig()
        
        config.server.environment = Environment.DEVELOPMENT
        assert config.is_development() is True
        
        config.server.environment = Environment.PRODUCTION
        assert config.is_development() is False

    def test_is_production(self):
        """Test that is_production returns correct value."""
        config = ApplicationConfig()
        
        config.server.environment = Environment.PRODUCTION
        assert config.is_production() is True
        
        config.server.environment = Environment.DEVELOPMENT
        assert config.is_production() is False


class TestModelsIntegration:
    """Integration tests for configuration models."""

    def test_all_configs_are_dataclasses(self):
        """Test that all config classes are dataclasses."""
        config_classes = [
            ServerConfig, OpenAIConfig, AudioConfig, VADConfig,
            TranscriptionConfig, WebSocketConfig, QualityMonitoringConfig,
            AudioStreamHandlerConfig, LoggingConfig, MockConfig,
            TUIConfig, StaticDataConfig, SecurityConfig, ApplicationConfig
        ]
        
        for config_class in config_classes:
            # Check if it's a dataclass by looking for __dataclass_fields__
            assert hasattr(config_class, '__dataclass_fields__')

    def test_config_serialization(self):
        """Test that configs can be serialized to dictionaries."""
        config = ApplicationConfig()
        config.openai.api_key = "test-key"
        
        config_dict = asdict(config)
        assert isinstance(config_dict, dict)
        assert "server" in config_dict
        assert "openai" in config_dict
        assert "audio" in config_dict
        assert config_dict["openai"]["api_key"] == "test-key"

    def test_config_equality(self):
        """Test that configs can be compared for equality."""
        config1 = ApplicationConfig()
        config1.openai.api_key = "test-key"
        
        config2 = ApplicationConfig()
        config2.openai.api_key = "test-key"
        
        assert config1 == config2
        
        config2.openai.api_key = "different-key"
        assert config1 != config2

    def test_config_immutability(self):
        """Test that config fields can be modified."""
        config = ApplicationConfig()
        original_port = config.server.port
        
        # Should be able to modify nested configs
        config.server.port = 9000
        assert config.server.port == 9000
        assert config.server.port != original_port

    def test_config_defaults_consistency(self):
        """Test that config defaults are consistent across the application."""
        config = ApplicationConfig()
        
        # Audio sample rates should be consistent
        assert config.audio.sample_rate == 24000
        assert config.vad.sample_rate == 24000
        assert config.transcription.sample_rate == 24000
        assert config.audio_stream_handler.internal_sample_rate == 24000
        assert config.audio_stream_handler.openai_sample_rate == 24000
        
        # VAD should be enabled by default
        assert config.vad.enabled is True
        assert config.audio_stream_handler.vad_enabled is True
        
        # Transcription should be enabled by default
        assert config.transcription.enabled is True
