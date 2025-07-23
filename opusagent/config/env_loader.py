"""
Environment variable loader for OpusAgent configuration.

This module handles loading configuration from environment variables,
with type conversion, validation, and fallback to defaults.

Environment variables must be explicitly loaded using load_env_file() before
accessing any configuration functions.
"""

import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, cast, get_origin
from dotenv import load_dotenv

from .models import (
    ApplicationConfig,
    ServerConfig,
    OpenAIConfig,
    AudioConfig,
    VADConfig,
    TranscriptionConfig,
    WebSocketConfig,
    QualityMonitoringConfig,
    LoggingConfig,
    MockConfig,
    TUIConfig,
    StaticDataConfig,
    SecurityConfig,
    Environment,
    LogLevel,
)


# Track if environment variables have been loaded
_env_loaded = False


def load_env_file(env_file: Optional[str] = None) -> None:
    """Load environment variables from a .env file.
    
    This function must be called before accessing any configuration functions.
    
    Args:
        env_file: Path to the .env file. If None, uses default behavior.
    """
    global _env_loaded
    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv()
    _env_loaded = True


def _check_env_loaded() -> None:
    """Check if environment variables have been loaded, raise error if not."""
    if not _env_loaded:
        raise RuntimeError(
            "Environment variables not loaded. Call load_env_file() before accessing configuration."
        )


T = TypeVar("T")


def safe_convert(value: Optional[str], target_type: Type[T], default: T) -> T:
    """Safely convert environment variable string to target type."""
    if value is None:
        return default

    try:
        if target_type == bool:
            return cast(T, value.lower() == "true")
        elif target_type == int:
            return cast(T, int(value))
        elif target_type == float:
            return cast(T, float(value))
        elif target_type == str:
            return cast(T, value)
        elif target_type == Path:
            return cast(T, Path(value))
        elif get_origin(target_type) == list:
            # Handle List[str] type
            return cast(
                T,
                (
                    [item.strip() for item in value.split(",") if item.strip()]
                    if value
                    else default
                ),
            )
        elif callable(target_type):
            return cast(T, target_type(value))  # type: ignore
        else:
            return default
    except (ValueError, TypeError):
        return default


def safe_string_or_none(value: Optional[str]) -> Optional[str]:
    """Convert environment variable to string or None if empty."""
    if value is None or value.strip() == "":
        return None
    return value.strip()


def load_server_config() -> ServerConfig:
    """Load server configuration from environment variables."""
    _check_env_loaded()
    
    env_str = os.getenv("ENV", "production").lower()
    environment = (
        Environment.DEVELOPMENT if env_str == "development" else Environment.PRODUCTION
    )
    if env_str == "testing":
        environment = Environment.TESTING

    return ServerConfig(
        host=os.getenv("HOST", "0.0.0.0"),
        port=safe_convert(os.getenv("PORT"), int, 8000),
        environment=environment,
        debug=safe_convert(os.getenv("DEBUG"), bool, False),
        reload=safe_convert(os.getenv("RELOAD"), bool, False),
        workers=safe_convert(os.getenv("WORKERS"), int, 1),
        timeout_keep_alive=safe_convert(os.getenv("TIMEOUT_KEEP_ALIVE"), int, 5),
        http_protocol=os.getenv("HTTP_PROTOCOL", "h11"),
        access_log=safe_convert(os.getenv("ACCESS_LOG"), bool, False),
        ws_ping_interval=safe_convert(os.getenv("WS_PING_INTERVAL"), int, 5),
        ws_ping_timeout=safe_convert(os.getenv("WS_PING_TIMEOUT"), int, 10),
        ws_max_size=safe_convert(os.getenv("WS_MAX_SIZE"), int, 16 * 1024 * 1024),
    )


def load_openai_config() -> OpenAIConfig:
    """Load OpenAI configuration from environment variables."""
    _check_env_loaded()
    
    return OpenAIConfig(
        api_key=os.getenv("OPENAI_API_KEY"),
        model=os.getenv("OPENAI_MODEL", "gpt-4o-realtime-preview-2024-12-17"),
        base_url=os.getenv("OPENAI_API_BASE_URL", "wss://api.openai.com"),
        timeout=safe_convert(os.getenv("OPENAI_TIMEOUT"), int, 30),
        max_retries=safe_convert(os.getenv("OPENAI_MAX_RETRIES"), int, 3),
    )


def load_audio_config() -> AudioConfig:
    """Load audio configuration from environment variables."""
    _check_env_loaded()
    
    return AudioConfig(
        sample_rate=safe_convert(os.getenv("AUDIO_SAMPLE_RATE"), int, 16000),
        channels=safe_convert(os.getenv("AUDIO_CHANNELS"), int, 1),
        bits_per_sample=safe_convert(os.getenv("AUDIO_BITS_PER_SAMPLE"), int, 16),
        chunk_size=safe_convert(os.getenv("AUDIO_CHUNK_SIZE"), int, 3200),
        chunk_size_large=safe_convert(os.getenv("AUDIO_CHUNK_SIZE_LARGE"), int, 32000),
        format=os.getenv("AUDIO_FORMAT", "raw/lpcm16"),
        supported_formats=safe_convert(
            os.getenv("AUDIO_SUPPORTED_FORMATS"),
            List[str],
            ["raw/lpcm16", "g711/ulaw", "g711/alaw"],
        ),
    )


def load_vad_config() -> VADConfig:
    """Load VAD configuration from environment variables."""
    _check_env_loaded()
    
    return VADConfig(
        enabled=safe_convert(os.getenv("VAD_ENABLED"), bool, True),
        backend=os.getenv("VAD_BACKEND", "silero"),
        confidence_threshold=safe_convert(
            os.getenv("VAD_CONFIDENCE_THRESHOLD"), float, 0.5
        ),
        silence_threshold=safe_convert(os.getenv("VAD_SILENCE_THRESHOLD"), float, 0.6),
        min_speech_duration_ms=safe_convert(
            os.getenv("VAD_MIN_SPEECH_DURATION_MS"), int, 500
        ),
        speech_start_threshold=safe_convert(
            os.getenv("VAD_SPEECH_START_THRESHOLD"), int, 2
        ),
        speech_stop_threshold=safe_convert(
            os.getenv("VAD_SPEECH_STOP_THRESHOLD"), int, 3
        ),
        device=os.getenv("VAD_DEVICE", "cpu"),
        chunk_size=safe_convert(os.getenv("VAD_CHUNK_SIZE"), int, 512),
        confidence_history_size=safe_convert(
            os.getenv("VAD_CONFIDENCE_HISTORY_SIZE"), int, 5
        ),
        force_stop_timeout_ms=safe_convert(
            os.getenv("VAD_FORCE_STOP_TIMEOUT_MS"), int, 2000
        ),
        sample_rate=safe_convert(os.getenv("VAD_SAMPLE_RATE"), int, 16000),
    )


def load_transcription_config() -> TranscriptionConfig:
    """Load transcription configuration from environment variables."""
    _check_env_loaded()
    
    return TranscriptionConfig(
        enabled=safe_convert(os.getenv("TRANSCRIPTION_ENABLED"), bool, True),
        backend=os.getenv("TRANSCRIPTION_BACKEND", "pocketsphinx"),
        language=os.getenv("TRANSCRIPTION_LANGUAGE", "en"),
        model_size=os.getenv("WHISPER_MODEL_SIZE", "base"),
        chunk_duration=safe_convert(
            os.getenv("TRANSCRIPTION_CHUNK_DURATION"), float, 1.0
        ),
        confidence_threshold=safe_convert(
            os.getenv("TRANSCRIPTION_CONFIDENCE_THRESHOLD"), float, 0.5
        ),
        sample_rate=safe_convert(os.getenv("TRANSCRIPTION_SAMPLE_RATE"), int, 16000),
        enable_vad=safe_convert(os.getenv("TRANSCRIPTION_ENABLE_VAD"), bool, True),
        device=os.getenv("WHISPER_DEVICE", "cpu"),
        pocketsphinx_hmm=safe_string_or_none(os.getenv("POCKETSPHINX_HMM")),
        pocketsphinx_lm=safe_string_or_none(os.getenv("POCKETSPHINX_LM")),
        pocketsphinx_dict=safe_string_or_none(os.getenv("POCKETSPHINX_DICT")),
        pocketsphinx_audio_preprocessing=os.getenv(
            "POCKETSPHINX_AUDIO_PREPROCESSING", "normalize"
        ),
        pocketsphinx_vad_settings=os.getenv(
            "POCKETSPHINX_VAD_SETTINGS", "conservative"
        ),
        pocketsphinx_auto_resample=safe_convert(
            os.getenv("POCKETSPHINX_AUTO_RESAMPLE"), bool, True
        ),
        pocketsphinx_input_sample_rate=safe_convert(
            os.getenv("POCKETSPHINX_INPUT_SAMPLE_RATE"), int, 24000
        ),
        whisper_model_dir=safe_string_or_none(os.getenv("WHISPER_MODEL_DIR")),
        whisper_temperature=safe_convert(os.getenv("WHISPER_TEMPERATURE"), float, 0.0),
    )


def load_websocket_config() -> WebSocketConfig:
    """Load WebSocket configuration from environment variables."""
    _check_env_loaded()
    
    return WebSocketConfig(
        max_connections=safe_convert(os.getenv("WEBSOCKET_MAX_CONNECTIONS"), int, 10),
        max_connection_age=safe_convert(
            os.getenv("WEBSOCKET_MAX_CONNECTION_AGE"), float, 3600.0
        ),
        max_idle_time=safe_convert(os.getenv("WEBSOCKET_MAX_IDLE_TIME"), float, 300.0),
        health_check_interval=safe_convert(
            os.getenv("WEBSOCKET_HEALTH_CHECK_INTERVAL"), float, 30.0
        ),
        max_sessions_per_connection=safe_convert(
            os.getenv("WEBSOCKET_MAX_SESSIONS_PER_CONNECTION"), int, 10
        ),
        ping_interval=safe_convert(os.getenv("WEBSOCKET_PING_INTERVAL"), int, 20),
        ping_timeout=safe_convert(os.getenv("WEBSOCKET_PING_TIMEOUT"), int, 30),
        close_timeout=safe_convert(os.getenv("WEBSOCKET_CLOSE_TIMEOUT"), int, 10),
    )


def load_quality_config() -> QualityMonitoringConfig:
    """Load quality monitoring configuration from environment variables."""
    _check_env_loaded()
    
    return QualityMonitoringConfig(
        enabled=safe_convert(os.getenv("QUALITY_MONITORING_ENABLED"), bool, True),
        min_snr_db=safe_convert(os.getenv("QUALITY_MIN_SNR_DB"), float, 15.0),
        max_thd_percent=safe_convert(os.getenv("QUALITY_MAX_THD_PERCENT"), float, 1.0),
        max_clipping_percent=safe_convert(
            os.getenv("QUALITY_MAX_CLIPPING_PERCENT"), float, 0.1
        ),
        min_quality_score=safe_convert(os.getenv("QUALITY_MIN_SCORE"), float, 60.0),
        min_audio_level=safe_convert(os.getenv("QUALITY_MIN_AUDIO_LEVEL"), float, 0.01),
        sample_rate=safe_convert(os.getenv("QUALITY_SAMPLE_RATE"), int, 16000),
        chunk_size=safe_convert(os.getenv("QUALITY_CHUNK_SIZE"), int, 1024),
        history_size=safe_convert(os.getenv("QUALITY_HISTORY_SIZE"), int, 100),
        enable_alerts=safe_convert(os.getenv("QUALITY_ENABLE_ALERTS"), bool, True),
        alert_log_level=os.getenv("QUALITY_ALERT_LOG_LEVEL", "WARNING"),
        enable_realtime_logging=safe_convert(
            os.getenv("QUALITY_ENABLE_REALTIME_LOGGING"), bool, True
        ),
        enable_summary_reports=safe_convert(
            os.getenv("QUALITY_ENABLE_SUMMARY_REPORTS"), bool, True
        ),
        summary_interval_seconds=safe_convert(
            os.getenv("QUALITY_SUMMARY_INTERVAL"), int, 60
        ),
    )


def load_logging_config() -> LoggingConfig:
    """Load logging configuration from environment variables."""
    _check_env_loaded()
    
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = LogLevel.INFO
    try:
        log_level = LogLevel(log_level_str)
    except ValueError:
        pass

    return LoggingConfig(
        level=log_level,
        format=os.getenv(
            "LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ),
        log_dir=Path(os.getenv("LOG_DIR", "logs")),
        log_filename=os.getenv("LOG_FILENAME", "opusagent.log"),
        max_log_size=safe_convert(os.getenv("LOG_MAX_SIZE"), int, 10 * 1024 * 1024),
        backup_count=safe_convert(os.getenv("LOG_BACKUP_COUNT"), int, 5),
        console_output=safe_convert(os.getenv("LOG_CONSOLE_OUTPUT"), bool, True),
        file_output=safe_convert(os.getenv("LOG_FILE_OUTPUT"), bool, True),
    )


def load_mock_config() -> MockConfig:
    """Load mock/testing configuration from environment variables."""
    _check_env_loaded()
    
    return MockConfig(
        enabled=safe_convert(os.getenv("OPUSAGENT_USE_MOCK"), bool, False),
        server_url=os.getenv("OPUSAGENT_MOCK_SERVER_URL", "ws://localhost:8080"),
        use_local_realtime=safe_convert(os.getenv("USE_LOCAL_REALTIME"), bool, False),
        enable_transcription=safe_convert(
            os.getenv("LOCAL_REALTIME_ENABLE_TRANSCRIPTION"), bool, True
        ),
        setup_smart_responses=safe_convert(
            os.getenv("LOCAL_REALTIME_SETUP_SMART_RESPONSES"), bool, True
        ),
    )


def load_tui_config() -> TUIConfig:
    """Load TUI configuration from environment variables."""
    _check_env_loaded()
    
    return TUIConfig(
        host=os.getenv("TUI_HOST", "localhost"),
        port=safe_convert(os.getenv("TUI_PORT"), int, 8000),
        ws_path=os.getenv("TUI_WS_PATH", "/voice-bot"),
        timeout_seconds=safe_convert(os.getenv("TUI_TIMEOUT"), int, 15),
        ping_interval=safe_convert(os.getenv("TUI_PING_INTERVAL"), int, 5),
        ping_timeout=safe_convert(os.getenv("TUI_PING_TIMEOUT"), int, 20),
        reconnect_attempts=safe_convert(os.getenv("TUI_RECONNECT_ATTEMPTS"), int, 3),
        reconnect_delay=safe_convert(os.getenv("TUI_RECONNECT_DELAY"), int, 2),
        bot_name=os.getenv("TUI_BOT_NAME", "voice-bot"),
        caller_id=os.getenv("TUI_CALLER_ID", "tui-validator"),
        session_timeout=safe_convert(os.getenv("TUI_SESSION_TIMEOUT"), int, 300),
        auto_reconnect=safe_convert(os.getenv("TUI_AUTO_RECONNECT"), bool, True),
        vad_enabled=safe_convert(os.getenv("TUI_VAD_ENABLED"), bool, True),
        show_vad_events=safe_convert(os.getenv("TUI_SHOW_VAD_EVENTS"), bool, True),
        enable_audio_recording=safe_convert(
            os.getenv("TUI_ENABLE_RECORDING"), bool, True
        ),
        recordings_dir=os.getenv("TUI_RECORDINGS_DIR", "test_logs"),
        max_recording_duration=safe_convert(
            os.getenv("TUI_MAX_RECORDING_DURATION"), int, 300
        ),
        refresh_rate=safe_convert(os.getenv("TUI_REFRESH_RATE"), int, 60),
        log_max_lines=safe_convert(os.getenv("TUI_LOG_MAX_LINES"), int, 1000),
        transcript_max_lines=safe_convert(
            os.getenv("TUI_TRANSCRIPT_MAX_LINES"), int, 500
        ),
        events_max_lines=safe_convert(os.getenv("TUI_EVENTS_MAX_LINES"), int, 200),
        show_audio_chunks=safe_convert(os.getenv("TUI_SHOW_AUDIO_CHUNKS"), bool, False),
        show_debug_messages=safe_convert(os.getenv("TUI_SHOW_DEBUG"), bool, True),
        filter_heartbeat_messages=safe_convert(
            os.getenv("TUI_FILTER_HEARTBEAT"), bool, True
        ),
        max_events=safe_convert(os.getenv("TUI_MAX_EVENTS"), int, 1000),
        log_level=os.getenv("TUI_LOG_LEVEL", "INFO"),
        export_format=os.getenv("TUI_EXPORT_FORMAT", "json"),
        auto_export_on_session_end=safe_convert(
            os.getenv("TUI_AUTO_EXPORT"), bool, False
        ),
        theme=os.getenv("TUI_THEME", "dark"),
        show_timestamps=safe_convert(os.getenv("TUI_SHOW_TIMESTAMPS"), bool, True),
        show_latency=safe_convert(os.getenv("TUI_SHOW_LATENCY"), bool, True),
    )


def load_static_data_config() -> StaticDataConfig:
    """Load static data configuration from environment variables."""
    _check_env_loaded()
    
    return StaticDataConfig(
        scenarios_file=Path(os.getenv("SCENARIOS_FILE", "scenarios.json")),
        phrases_mapping_file=Path(
            os.getenv(
                "PHRASES_MAPPING_FILE", "opusagent/local/audio/phrases_mapping.yml"
            )
        ),
        audio_directory=Path(os.getenv("AUDIO_DIRECTORY", "opusagent/local/audio")),
    )


def load_security_config() -> SecurityConfig:
    """Load security configuration from environment variables."""
    _check_env_loaded()
    
    allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")
    origins_list = [origin.strip() for origin in allowed_origins.split(",")]

    return SecurityConfig(
        api_key_validation=safe_convert(os.getenv("API_KEY_VALIDATION"), bool, True),
        rate_limiting_enabled=safe_convert(
            os.getenv("RATE_LIMITING_ENABLED"), bool, True
        ),
        max_requests_per_minute=safe_convert(
            os.getenv("MAX_REQUESTS_PER_MINUTE"), int, 100
        ),
        require_ssl=safe_convert(os.getenv("REQUIRE_SSL"), bool, False),
        allowed_origins=origins_list,
    )


def load_application_config() -> ApplicationConfig:
    """Load complete application configuration from environment variables."""
    _check_env_loaded()
    
    config = ApplicationConfig(
        server=load_server_config(),
        openai=load_openai_config(),
        audio=load_audio_config(),
        vad=load_vad_config(),
        transcription=load_transcription_config(),
        websocket=load_websocket_config(),
        quality=load_quality_config(),
        logging=load_logging_config(),
        mock=load_mock_config(),
        tui=load_tui_config(),
        static_data=load_static_data_config(),
        security=load_security_config(),
    )
    
    # Validate configuration and raise exceptions for critical errors
    validation_errors = config.validate()
    if validation_errors:
        # Format error message
        error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in validation_errors)
        raise ValueError(error_msg)
    
    return config


def get_environment_info() -> Dict[str, Any]:
    """Get information about current environment variables for debugging."""
    _check_env_loaded()
    
    return {
        "environment_variables_loaded": len(
            [
                k
                for k in os.environ.keys()
                if k.startswith(("OPENAI_", "VAD_", "TUI_", "WEBSOCKET_", "LOG_"))
            ]
        ),
        "dotenv_loaded": Path(".env").exists(),
        "current_environment": os.getenv("ENV", "production"),
        "mock_mode": safe_convert(os.getenv("OPUSAGENT_USE_MOCK"), bool, False),
        "openai_api_key_set": bool(os.getenv("OPENAI_API_KEY")),
    }
