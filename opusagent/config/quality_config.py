"""Audio Quality Monitoring Configuration.

This module provides configuration settings for audio quality monitoring,
including thresholds, alert levels, and monitoring parameters.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from opusagent.config.constants import DEFAULT_SAMPLE_RATE
from opusagent.utils.audio_quality_monitor import QualityThresholds

# Sentinel value to distinguish between "not provided" and "explicitly None"
_UNSET = object()


@dataclass
class QualityMonitoringConfig:
    """Configuration for audio quality monitoring."""

    # Enable/disable quality monitoring
    enabled: bool = True

    # Quality thresholds - use private field to handle sentinel value
    _thresholds: Any = field(default=_UNSET, repr=False)

    # Monitoring parameters
    sample_rate: int = DEFAULT_SAMPLE_RATE
    chunk_size: int = 1024
    history_size: int = 100

    # Alert configuration
    enable_alerts: bool = True
    alert_log_level: str = "WARNING"  # DEBUG, INFO, WARNING, ERROR

    # Reporting configuration
    enable_realtime_logging: bool = True
    enable_summary_reports: bool = True
    summary_interval_seconds: int = 60  # Generate summary every minute

    def __post_init__(self):
        """Initialize default thresholds if not provided."""
        # Only create default thresholds if enabled and thresholds was not provided
        if self.enabled and self._thresholds is _UNSET:
            self._thresholds = QualityThresholds(
                min_snr_db=15.0,  # Minimum signal-to-noise ratio (lowered for telephony)
                max_thd_percent=1.0,  # Maximum total harmonic distortion
                max_clipping_percent=0.1,  # Maximum acceptable clipping
                min_quality_score=60.0,  # Minimum overall quality score
                min_audio_level=0.01,  # Minimum RMS level to consider audio active
            )
        elif self._thresholds is _UNSET:
            # If not enabled and thresholds not provided, set to None
            self._thresholds = None

    @property
    def thresholds(self) -> Optional[QualityThresholds]:
        """Get the quality thresholds."""
        return self._thresholds if self._thresholds is not _UNSET else None

    @thresholds.setter
    def thresholds(self, value: Optional[QualityThresholds]) -> None:
        """Set the quality thresholds."""
        self._thresholds = value


# Predefined quality configurations for different environments
QUALITY_CONFIGS = {
    "development": QualityMonitoringConfig(
        enabled=True,
        alert_log_level="INFO",
        enable_realtime_logging=True,
    ),
    "production": QualityMonitoringConfig(
        enabled=True,
        alert_log_level="WARNING",
        enable_realtime_logging=True,
        enable_summary_reports=True,
        summary_interval_seconds=30,
    ),
    "testing": QualityMonitoringConfig(
        enabled=True,
        alert_log_level="DEBUG",
        enable_realtime_logging=False,
        enable_summary_reports=True,
    ),
    "disabled": QualityMonitoringConfig(
        enabled=False,
    ),
}

# Set custom thresholds for predefined configs after creation
QUALITY_CONFIGS["development"].thresholds = QualityThresholds(
    min_snr_db=15.0,  # More lenient for development
    max_thd_percent=2.0,
    max_clipping_percent=0.5,
    min_quality_score=50.0,
)

QUALITY_CONFIGS["production"].thresholds = QualityThresholds(
    min_snr_db=25.0,  # Stricter for production
    max_thd_percent=0.5,
    max_clipping_percent=0.05,
    min_quality_score=75.0,
)

QUALITY_CONFIGS["testing"].thresholds = QualityThresholds(
    min_snr_db=10.0,  # Very lenient for testing
    max_thd_percent=5.0,
    max_clipping_percent=1.0,
    min_quality_score=30.0,
)

QUALITY_CONFIGS["disabled"].thresholds = None


def get_quality_config(environment: str = "development") -> QualityMonitoringConfig:
    """Get quality monitoring configuration for the specified environment.

    Args:
        environment: Environment name ("development", "production", "testing", "disabled")

    Returns:
        QualityMonitoringConfig for the specified environment
    """
    return QUALITY_CONFIGS.get(environment, QUALITY_CONFIGS["development"])


def create_custom_quality_config(
    enabled: bool = True,
    min_snr_db: float = 20.0,
    max_thd_percent: float = 1.0,
    max_clipping_percent: float = 0.1,
    min_quality_score: float = 60.0,
    **kwargs
) -> QualityMonitoringConfig:
    """Create a custom quality monitoring configuration.

    Args:
        enabled: Enable quality monitoring
        min_snr_db: Minimum signal-to-noise ratio in dB
        max_thd_percent: Maximum total harmonic distortion percentage
        max_clipping_percent: Maximum acceptable clipping percentage
        min_quality_score: Minimum overall quality score
        **kwargs: Additional configuration parameters

    Returns:
        Custom QualityMonitoringConfig
    """
    thresholds = QualityThresholds(
        min_snr_db=min_snr_db,
        max_thd_percent=max_thd_percent,
        max_clipping_percent=max_clipping_percent,
        min_quality_score=min_quality_score,
    )

    config = QualityMonitoringConfig(enabled=enabled, **kwargs)
    config.thresholds = thresholds

    return config


def validate_quality_config(config: QualityMonitoringConfig) -> Dict[str, Any]:
    """Validate a quality monitoring configuration.

    Args:
        config: QualityMonitoringConfig to validate

    Returns:
        Dictionary with validation results
    """
    validation_results = {"valid": True, "warnings": [], "errors": []}

    if not config.enabled:
        return validation_results

    # Validate thresholds
    thresholds = config.thresholds

    if thresholds is None:
        validation_results["errors"].append(
            "thresholds must be provided when monitoring is enabled"
        )
        validation_results["valid"] = False
        return validation_results

    if thresholds.min_snr_db < 0:
        validation_results["errors"].append("min_snr_db must be non-negative")
        validation_results["valid"] = False

    if thresholds.max_thd_percent < 0 or thresholds.max_thd_percent > 100:
        validation_results["errors"].append("max_thd_percent must be between 0 and 100")
        validation_results["valid"] = False

    if thresholds.max_clipping_percent < 0 or thresholds.max_clipping_percent > 100:
        validation_results["errors"].append(
            "max_clipping_percent must be between 0 and 100"
        )
        validation_results["valid"] = False

    if thresholds.min_quality_score < 0 or thresholds.min_quality_score > 100:
        validation_results["errors"].append(
            "min_quality_score must be between 0 and 100"
        )
        validation_results["valid"] = False

    # Validate monitoring parameters
    if config.sample_rate <= 0:
        validation_results["errors"].append("sample_rate must be positive")
        validation_results["valid"] = False

    if config.chunk_size <= 0:
        validation_results["errors"].append("chunk_size must be positive")
        validation_results["valid"] = False

    if config.history_size <= 0:
        validation_results["errors"].append("history_size must be positive")
        validation_results["valid"] = False

    # Warnings for potentially problematic settings
    if thresholds.min_snr_db < 10:
        validation_results["warnings"].append(
            "Very low SNR threshold may generate many alerts"
        )

    if thresholds.max_thd_percent > 5:
        validation_results["warnings"].append(
            "High THD threshold may miss quality issues"
        )

    if thresholds.max_clipping_percent > 1:
        validation_results["warnings"].append(
            "High clipping threshold may miss distortion issues"
        )

    if config.history_size > 1000:
        validation_results["warnings"].append(
            "Large history size may consume significant memory"
        )

    return validation_results
