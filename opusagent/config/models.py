"""
Configuration models for the OpusAgent application.

This module defines dataclasses for different configuration domains,
providing type safety and validation for all application settings.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from opusagent.config.constants import (
    DEFAULT_AUDIO_CHUNK_SIZE,
    DEFAULT_AUDIO_CHUNK_SIZE_LARGE,
    DEFAULT_BITS_PER_SAMPLE,
    DEFAULT_CHANNELS,
    DEFAULT_INTERNAL_SAMPLE_RATE,
    DEFAULT_MIN_AUDIO_BYTES,
    DEFAULT_OPENAI_SAMPLE_RATE,
    DEFAULT_SAMPLE_RATE,
    DEFAULT_TRANSCRIPTION_BACKEND,
    DEFAULT_TRANSCRIPTION_CHUNK_DURATION,
    DEFAULT_TRANSCRIPTION_CONFIDENCE_THRESHOLD,
    DEFAULT_TRANSCRIPTION_LANGUAGE,
    DEFAULT_VAD_CHUNK_SIZE,
    DEFAULT_WHISPER_MODEL_SIZE,
    SPEECH_START_THRESHOLD,
    SPEECH_STOP_THRESHOLD,
)


class Environment(Enum):
    """Application environment types."""

    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class LogLevel(Enum):
    """Logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class ServerConfig:
    """Server configuration settings."""

    host: str = "0.0.0.0"
    port: int = 8000
    environment: Environment = Environment.PRODUCTION
    debug: bool = False
    reload: bool = False
    workers: int = 1
    timeout_keep_alive: int = 5

    # HTTP/WebSocket server settings
    http_protocol: str = "h11"  # HTTP/1.1 for lower overhead
    access_log: bool = False
    ws_ping_interval: int = 5
    ws_ping_timeout: int = 10
    ws_max_size: int = 16 * 1024 * 1024  # 16MB


@dataclass
class OpenAIConfig:
    """OpenAI API configuration."""

    api_key: Optional[str] = None
    model: str = "gpt-4o-realtime-preview-2024-12-17"
    base_url: str = "wss://api.openai.com"
    timeout: int = 30
    max_retries: int = 3

    def get_websocket_url(self) -> str:
        """Get the OpenAI Realtime API WebSocket URL."""
        return f"{self.base_url}/v1/realtime?model={self.model}"

    def get_headers(self) -> Dict[str, str]:
        """Get headers for OpenAI API authentication."""
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "OpenAI-Beta": "realtime=v1",
        }


@dataclass
class AudioConfig:
    """Audio processing configuration."""

    sample_rate: int = DEFAULT_SAMPLE_RATE
    channels: int = DEFAULT_CHANNELS
    bits_per_sample: int = DEFAULT_BITS_PER_SAMPLE
    chunk_size: int = DEFAULT_AUDIO_CHUNK_SIZE
    chunk_size_large: int = DEFAULT_AUDIO_CHUNK_SIZE_LARGE
    format: str = "raw/lpcm16"
    supported_formats: List[str] = field(
        default_factory=lambda: ["raw/lpcm16", "g711/ulaw", "g711/alaw"]
    )


@dataclass
class VADConfig:
    """Voice Activity Detection configuration."""

    enabled: bool = True
    backend: str = "silero"
    confidence_threshold: float = 0.5
    silence_threshold: float = 0.6
    min_speech_duration_ms: int = 500
    speech_start_threshold: int = SPEECH_START_THRESHOLD
    speech_stop_threshold: int = SPEECH_STOP_THRESHOLD
    device: str = "cpu"
    chunk_size: int = DEFAULT_VAD_CHUNK_SIZE
    confidence_history_size: int = 5
    force_stop_timeout_ms: int = 2000
    sample_rate: int = DEFAULT_SAMPLE_RATE


@dataclass
class TranscriptionConfig:
    """Transcription configuration."""

    enabled: bool = True
    backend: str = DEFAULT_TRANSCRIPTION_BACKEND
    language: str = DEFAULT_TRANSCRIPTION_LANGUAGE
    model_size: str = DEFAULT_WHISPER_MODEL_SIZE
    chunk_duration: float = DEFAULT_TRANSCRIPTION_CHUNK_DURATION
    confidence_threshold: float = DEFAULT_TRANSCRIPTION_CONFIDENCE_THRESHOLD
    sample_rate: int = DEFAULT_SAMPLE_RATE
    enable_vad: bool = True
    device: str = "cpu"

    # Pocketsphinx specific
    pocketsphinx_hmm: Optional[str] = None
    pocketsphinx_lm: Optional[str] = None
    pocketsphinx_dict: Optional[str] = None
    pocketsphinx_audio_preprocessing: str = "normalize"
    pocketsphinx_vad_settings: str = "conservative"
    pocketsphinx_auto_resample: bool = True
    pocketsphinx_input_sample_rate: int = 24000

    # Whisper specific
    whisper_model_dir: Optional[str] = None
    whisper_temperature: float = 0.0


@dataclass
class WebSocketConfig:
    """WebSocket connection configuration."""

    max_connections: int = 10
    max_connection_age: float = 3600.0  # 1 hour
    max_idle_time: float = 300.0  # 5 minutes
    health_check_interval: float = 30.0  # 30 seconds
    max_sessions_per_connection: int = 10
    ping_interval: int = 20
    ping_timeout: int = 30
    close_timeout: int = 10


@dataclass
class QualityMonitoringConfig:
    """Audio quality monitoring configuration."""

    enabled: bool = True
    min_snr_db: float = 15.0
    max_thd_percent: float = 1.0
    max_clipping_percent: float = 0.1
    min_quality_score: float = 60.0
    min_audio_level: float = 0.01
    sample_rate: int = DEFAULT_SAMPLE_RATE
    chunk_size: int = 1024
    history_size: int = 100
    enable_alerts: bool = True
    alert_log_level: str = "WARNING"
    enable_realtime_logging: bool = True
    enable_summary_reports: bool = True
    summary_interval_seconds: int = 60


@dataclass
class AudioStreamHandlerConfig:
    """Audio Stream Handler configuration."""

    internal_sample_rate: int = DEFAULT_INTERNAL_SAMPLE_RATE
    min_audio_bytes: int = DEFAULT_MIN_AUDIO_BYTES
    openai_sample_rate: int = DEFAULT_OPENAI_SAMPLE_RATE
    enable_quality_monitoring: bool = False
    vad_enabled: bool = True
    bridge_type: str = "unknown"


@dataclass
class LoggingConfig:
    """Logging configuration settings."""

    level: LogLevel = LogLevel.INFO
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_dir: Path = field(default_factory=lambda: Path("logs"))
    log_filename: str = "opusagent.log"
    max_log_size: int = 10 * 1024 * 1024  # 10 MB
    backup_count: int = 5
    console_output: bool = True
    file_output: bool = True


@dataclass
class MockConfig:
    """Mock/testing configuration."""

    enabled: bool = False
    server_url: str = "ws://localhost:8080"
    use_local_realtime: bool = False
    enable_transcription: bool = True
    setup_smart_responses: bool = True


@dataclass
class TUIConfig:
    """TUI application configuration."""

    host: str = "localhost"
    port: int = 8000
    ws_path: str = "/voice-bot"
    timeout_seconds: int = 15
    ping_interval: int = 5
    ping_timeout: int = 20
    reconnect_attempts: int = 3
    reconnect_delay: int = 2
    bot_name: str = "voice-bot"
    caller_id: str = "tui-validator"
    session_timeout: int = 300
    auto_reconnect: bool = True

    # VAD settings
    vad_enabled: bool = True
    show_vad_events: bool = True

    # Recording settings
    enable_audio_recording: bool = True
    recordings_dir: str = "test_logs"
    max_recording_duration: int = 300

    # UI settings
    refresh_rate: int = 60
    log_max_lines: int = 1000
    transcript_max_lines: int = 500
    events_max_lines: int = 200

    # Message filtering
    show_audio_chunks: bool = False
    show_debug_messages: bool = True
    filter_heartbeat_messages: bool = True

    # Event logging
    max_events: int = 1000
    log_level: str = "INFO"
    export_format: str = "json"
    auto_export_on_session_end: bool = False

    # Appearance
    theme: str = "dark"
    show_timestamps: bool = True
    show_latency: bool = True


@dataclass
class StaticDataConfig:
    """Static data file configuration."""

    scenarios_file: Path = field(default_factory=lambda: Path("scenarios.json"))
    phrases_mapping_file: Path = field(
        default_factory=lambda: Path("opusagent/local/audio/phrases_mapping.yml")
    )
    audio_directory: Path = field(default_factory=lambda: Path("opusagent/local/audio"))


@dataclass
class SecurityConfig:
    """Security-related configuration."""

    api_key_validation: bool = True
    rate_limiting_enabled: bool = True
    max_requests_per_minute: int = 100
    require_ssl: bool = False
    allowed_origins: List[str] = field(default_factory=lambda: ["*"])


@dataclass
class ApplicationConfig:
    """Master application configuration containing all domain configs."""

    server: ServerConfig = field(default_factory=ServerConfig)
    openai: OpenAIConfig = field(default_factory=OpenAIConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    vad: VADConfig = field(default_factory=VADConfig)
    transcription: TranscriptionConfig = field(default_factory=TranscriptionConfig)
    websocket: WebSocketConfig = field(default_factory=WebSocketConfig)
    quality: QualityMonitoringConfig = field(default_factory=QualityMonitoringConfig)
    audio_stream_handler: AudioStreamHandlerConfig = field(
        default_factory=AudioStreamHandlerConfig
    )
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    mock: MockConfig = field(default_factory=MockConfig)
    tui: TUIConfig = field(default_factory=TUIConfig)
    static_data: StaticDataConfig = field(default_factory=StaticDataConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)

    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []

        # Validate OpenAI config if not in mock mode
        if not self.mock.enabled and not self.openai.api_key:
            errors.append(
                "OpenAI API key is required when not in mock mode. Please set the OPENAI_API_KEY environment variable or enable mock mode by setting OPUSAGENT_USE_MOCK=true"
            )

        # Validate server config
        if self.server.port <= 0 or self.server.port > 65535:
            errors.append("Server port must be between 1 and 65535")

        # Validate audio config
        if self.audio.sample_rate <= 0:
            errors.append("Audio sample rate must be positive")

        # Validate VAD config
        if self.vad.confidence_threshold < 0 or self.vad.confidence_threshold > 1:
            errors.append("VAD confidence threshold must be between 0 and 1")

        # Validate transcription config
        if (
            self.transcription.confidence_threshold < 0
            or self.transcription.confidence_threshold > 1
        ):
            errors.append("Transcription confidence threshold must be between 0 and 1")

        return errors

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.server.environment == Environment.DEVELOPMENT

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.server.environment == Environment.PRODUCTION
