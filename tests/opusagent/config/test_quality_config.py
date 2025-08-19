"""
Unit tests for the quality_config module.

This module tests the quality monitoring configuration functions defined in opusagent.config.quality_config.
"""

import pytest
from unittest.mock import patch, MagicMock
from typing import Dict, Any

from opusagent.config.quality_config import (
    QualityMonitoringConfig,
    QUALITY_CONFIGS,
    get_quality_config,
    create_custom_quality_config,
    validate_quality_config,
)


class TestQualityMonitoringConfig:
    """Test QualityMonitoringConfig class."""

    def test_quality_monitoring_config_defaults(self):
        """Test QualityMonitoringConfig with default values."""
        config = QualityMonitoringConfig()
        
        assert config.enabled is True
        assert config.thresholds is not None
        assert config.sample_rate > 0
        assert config.chunk_size > 0
        assert config.history_size > 0
        assert config.enable_alerts is True
        assert config.alert_log_level == "WARNING"
        assert config.enable_realtime_logging is True
        assert config.enable_summary_reports is True
        assert config.summary_interval_seconds > 0

    def test_quality_monitoring_config_custom_values(self):
        """Test QualityMonitoringConfig with custom values."""
        config = QualityMonitoringConfig(
            enabled=False,
            sample_rate=48000,
            chunk_size=2048,
            history_size=200,
            enable_alerts=False,
            alert_log_level="ERROR",
            enable_realtime_logging=False,
            enable_summary_reports=False,
            summary_interval_seconds=120
        )
        
        assert config.enabled is False
        assert config.sample_rate == 48000
        assert config.chunk_size == 2048
        assert config.history_size == 200
        assert config.enable_alerts is False
        assert config.alert_log_level == "ERROR"
        assert config.enable_realtime_logging is False
        assert config.enable_summary_reports is False
        assert config.summary_interval_seconds == 120

    def test_quality_monitoring_config_post_init(self):
        """Test that __post_init__ creates default thresholds."""
        config = QualityMonitoringConfig()
        
        assert config.thresholds is not None
        assert hasattr(config.thresholds, 'min_snr_db')
        assert hasattr(config.thresholds, 'max_thd_percent')
        assert hasattr(config.thresholds, 'max_clipping_percent')
        assert hasattr(config.thresholds, 'min_quality_score')
        assert hasattr(config.thresholds, 'min_audio_level')

    def test_quality_monitoring_config_with_custom_thresholds(self):
        """Test QualityMonitoringConfig with custom thresholds."""
        mock_thresholds = MagicMock()
        mock_thresholds.min_snr_db = 25.0
        mock_thresholds.max_thd_percent = 0.5
        mock_thresholds.max_clipping_percent = 0.05
        mock_thresholds.min_quality_score = 75.0
        mock_thresholds.min_audio_level = 0.02
        
        config = QualityMonitoringConfig()
        config.thresholds = mock_thresholds
        
        assert config.thresholds == mock_thresholds
        assert config.thresholds is not None  # Type guard for the linter
        assert config.thresholds.min_snr_db == 25.0
        assert config.thresholds.max_thd_percent == 0.5
        assert config.thresholds.max_clipping_percent == 0.05
        assert config.thresholds.min_quality_score == 75.0
        assert config.thresholds.min_audio_level == 0.02


class TestQualityConfigs:
    """Test predefined quality configurations."""

    def test_quality_configs_contains_expected_environments(self):
        """Test that QUALITY_CONFIGS contains expected environments."""
        expected_environments = ["development", "production", "testing", "disabled"]
        
        for env in expected_environments:
            assert env in QUALITY_CONFIGS
            assert isinstance(QUALITY_CONFIGS[env], QualityMonitoringConfig)

    def test_development_config(self):
        """Test development quality configuration."""
        config = QUALITY_CONFIGS["development"]
        
        assert config.enabled is True
        assert config.thresholds is not None
        thresholds = config.thresholds
        assert thresholds.min_snr_db == 15.0
        assert thresholds.max_thd_percent == 2.0
        assert thresholds.max_clipping_percent == 0.5
        assert thresholds.min_quality_score == 50.0
        assert config.alert_log_level == "INFO"
        assert config.enable_realtime_logging is True

    def test_production_config(self):
        """Test production quality configuration."""
        config = QUALITY_CONFIGS["production"]
        
        assert config.enabled is True
        assert config.thresholds is not None
        thresholds = config.thresholds
        assert thresholds.min_snr_db == 25.0
        assert thresholds.max_thd_percent == 0.5
        assert thresholds.max_clipping_percent == 0.05
        assert thresholds.min_quality_score == 75.0
        assert config.alert_log_level == "WARNING"
        assert config.enable_realtime_logging is True
        assert config.enable_summary_reports is True
        assert config.summary_interval_seconds == 30

    def test_testing_config(self):
        """Test testing quality configuration."""
        config = QUALITY_CONFIGS["testing"]
        
        assert config.enabled is True
        assert config.thresholds is not None
        thresholds = config.thresholds
        assert thresholds.min_snr_db == 10.0
        assert thresholds.max_thd_percent == 5.0
        assert thresholds.max_clipping_percent == 1.0
        assert thresholds.min_quality_score == 30.0
        assert config.alert_log_level == "DEBUG"
        assert config.enable_realtime_logging is False
        assert config.enable_summary_reports is True

    def test_disabled_config(self):
        """Test disabled quality configuration."""
        config = QUALITY_CONFIGS["disabled"]
        
        assert config.enabled is False
        assert config.thresholds is None

    def test_quality_configs_threshold_comparison(self):
        """Test that quality thresholds are properly ordered by environment."""
        # Production should have stricter thresholds than development
        prod_config = QUALITY_CONFIGS["production"]
        dev_config = QUALITY_CONFIGS["development"]
        
        assert prod_config.thresholds is not None
        assert dev_config.thresholds is not None
        assert prod_config.thresholds.min_snr_db > dev_config.thresholds.min_snr_db
        assert prod_config.thresholds.max_thd_percent < dev_config.thresholds.max_thd_percent
        assert prod_config.thresholds.max_clipping_percent < dev_config.thresholds.max_clipping_percent
        assert prod_config.thresholds.min_quality_score > dev_config.thresholds.min_quality_score


class TestGetQualityConfig:
    """Test get_quality_config function."""

    def test_get_quality_config_development(self):
        """Test get_quality_config with development environment."""
        config = get_quality_config("development")
        
        assert isinstance(config, QualityMonitoringConfig)
        assert config.enabled is True
        assert config.thresholds is not None
        assert config.thresholds.min_snr_db == 15.0

    def test_get_quality_config_production(self):
        """Test get_quality_config with production environment."""
        config = get_quality_config("production")
        
        assert isinstance(config, QualityMonitoringConfig)
        assert config.enabled is True
        assert config.thresholds is not None
        assert config.thresholds.min_snr_db == 25.0

    def test_get_quality_config_testing(self):
        """Test get_quality_config with testing environment."""
        config = get_quality_config("testing")
        
        assert isinstance(config, QualityMonitoringConfig)
        assert config.enabled is True
        assert config.thresholds is not None
        assert config.thresholds.min_snr_db == 10.0

    def test_get_quality_config_disabled(self):
        """Test get_quality_config with disabled environment."""
        config = get_quality_config("disabled")
        
        assert isinstance(config, QualityMonitoringConfig)
        assert config.enabled is False

    def test_get_quality_config_unknown_environment(self):
        """Test get_quality_config with unknown environment."""
        config = get_quality_config("unknown")
        
        # Should return development config as default
        assert isinstance(config, QualityMonitoringConfig)
        assert config.enabled is True
        assert config.thresholds is not None
        assert config.thresholds.min_snr_db == 15.0


class TestCreateCustomQualityConfig:
    """Test create_custom_quality_config function."""

    def test_create_custom_quality_config_defaults(self):
        """Test create_custom_quality_config with default parameters."""
        config = create_custom_quality_config()
        
        assert isinstance(config, QualityMonitoringConfig)
        assert config.enabled is True
        assert config.thresholds is not None
        thresholds = config.thresholds
        assert thresholds.min_snr_db == 20.0
        assert thresholds.max_thd_percent == 1.0
        assert thresholds.max_clipping_percent == 0.1
        assert thresholds.min_quality_score == 60.0

    def test_create_custom_quality_config_custom_values(self):
        """Test create_custom_quality_config with custom values."""
        config = create_custom_quality_config(
            enabled=False,
            min_snr_db=30.0,
            max_thd_percent=0.3,
            max_clipping_percent=0.02,
            min_quality_score=80.0,
            sample_rate=48000,
            chunk_size=2048
        )
        
        assert isinstance(config, QualityMonitoringConfig)
        assert config.enabled is False
        assert config.thresholds is not None
        thresholds = config.thresholds
        assert thresholds.min_snr_db == 30.0
        assert thresholds.max_thd_percent == 0.3
        assert thresholds.max_clipping_percent == 0.02
        assert thresholds.min_quality_score == 80.0
        assert config.sample_rate == 48000
        assert config.chunk_size == 2048

    def test_create_custom_quality_config_with_kwargs(self):
        """Test create_custom_quality_config with additional kwargs."""
        config = create_custom_quality_config(
            history_size=500,
            enable_alerts=False,
            alert_log_level="ERROR"
        )
        
        assert config.history_size == 500
        assert config.enable_alerts is False
        assert config.alert_log_level == "ERROR"


class TestValidateQualityConfig:
    """Test validate_quality_config function."""

    def test_validate_quality_config_valid(self):
        """Test validate_quality_config with valid configuration."""
        config = QualityMonitoringConfig()
        result = validate_quality_config(config)
        
        assert isinstance(result, dict)
        assert result["valid"] is True
        assert isinstance(result["warnings"], list)
        assert isinstance(result["errors"], list)

    def test_validate_quality_config_disabled(self):
        """Test validate_quality_config with disabled configuration."""
        config = QualityMonitoringConfig(enabled=False)
        result = validate_quality_config(config)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert len(result["warnings"]) == 0

    def test_validate_quality_config_missing_thresholds(self):
        """Test validate_quality_config with missing thresholds."""
        # Create config and manually set thresholds to None after __post_init__
        config = QualityMonitoringConfig(enabled=True)
        config.thresholds = None
        result = validate_quality_config(config)
        
        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert any("thresholds must be provided" in error for error in result["errors"])

    def test_validate_quality_config_invalid_snr(self):
        """Test validate_quality_config with invalid SNR threshold."""
        config = create_custom_quality_config(min_snr_db=-5.0)
        result = validate_quality_config(config)
        
        assert result["valid"] is False
        assert any("min_snr_db must be non-negative" in error for error in result["errors"])

    def test_validate_quality_config_invalid_thd(self):
        """Test validate_quality_config with invalid THD threshold."""
        config = create_custom_quality_config(max_thd_percent=150.0)
        result = validate_quality_config(config)
        
        assert result["valid"] is False
        assert any("max_thd_percent must be between 0 and 100" in error for error in result["errors"])

    def test_validate_quality_config_invalid_clipping(self):
        """Test validate_quality_config with invalid clipping threshold."""
        config = create_custom_quality_config(max_clipping_percent=-1.0)
        result = validate_quality_config(config)
        
        assert result["valid"] is False
        assert any("max_clipping_percent must be between 0 and 100" in error for error in result["errors"])

    def test_validate_quality_config_invalid_quality_score(self):
        """Test validate_quality_config with invalid quality score."""
        config = create_custom_quality_config(min_quality_score=150.0)
        result = validate_quality_config(config)
        
        assert result["valid"] is False
        assert any("min_quality_score must be between 0 and 100" in error for error in result["errors"])

    def test_validate_quality_config_invalid_sample_rate(self):
        """Test validate_quality_config with invalid sample rate."""
        config = QualityMonitoringConfig(sample_rate=0)
        result = validate_quality_config(config)
        
        assert result["valid"] is False
        assert any("sample_rate must be positive" in error for error in result["errors"])

    def test_validate_quality_config_invalid_chunk_size(self):
        """Test validate_quality_config with invalid chunk size."""
        config = QualityMonitoringConfig(chunk_size=0)
        result = validate_quality_config(config)
        
        assert result["valid"] is False
        assert any("chunk_size must be positive" in error for error in result["errors"])

    def test_validate_quality_config_invalid_history_size(self):
        """Test validate_quality_config with invalid history size."""
        config = QualityMonitoringConfig(history_size=0)
        result = validate_quality_config(config)
        
        assert result["valid"] is False
        assert any("history_size must be positive" in error for error in result["errors"])

    def test_validate_quality_config_warnings(self):
        """Test validate_quality_config generates warnings for problematic settings."""
        config = create_custom_quality_config(
            min_snr_db=5.0,
            max_thd_percent=10.0,
            max_clipping_percent=2.0
        )
        config.history_size = 2000
        
        result = validate_quality_config(config)
        
        assert result["valid"] is True
        assert len(result["warnings"]) > 0
        assert any("Very low SNR threshold" in warning for warning in result["warnings"])
        assert any("High THD threshold" in warning for warning in result["warnings"])
        assert any("High clipping threshold" in warning for warning in result["warnings"])
        assert any("Large history size" in warning for warning in result["warnings"])


class TestQualityConfigIntegration:
    """Integration tests for quality configuration."""

    def test_quality_config_workflow(self):
        """Test complete quality configuration workflow."""
        # Create custom config
        config = create_custom_quality_config(
            min_snr_db=25.0,
            max_thd_percent=0.5,
            max_clipping_percent=0.05,
            min_quality_score=75.0
        )
        
        # Validate config
        validation = validate_quality_config(config)
        
        assert validation["valid"] is True
        assert config.enabled is True
        assert config.thresholds is not None
        assert config.thresholds.min_snr_db == 25.0

    def test_quality_configs_consistency(self):
        """Test that quality configurations are internally consistent."""
        for env, config in QUALITY_CONFIGS.items():
            # All configs should be QualityMonitoringConfig instances
            assert isinstance(config, QualityMonitoringConfig)
            
            # If enabled, should have thresholds
            if config.enabled:
                assert config.thresholds is not None
                assert config.sample_rate > 0
                assert config.chunk_size > 0
                assert config.history_size > 0

    def test_threshold_values_are_reasonable(self):
        """Test that threshold values are within reasonable ranges."""
        for env, config in QUALITY_CONFIGS.items():
            if config.enabled and config.thresholds:
                thresholds = config.thresholds
                
                # SNR should be reasonable
                assert 0 <= thresholds.min_snr_db <= 100
                
                # THD should be reasonable
                assert 0 <= thresholds.max_thd_percent <= 100
                
                # Clipping should be reasonable
                assert 0 <= thresholds.max_clipping_percent <= 100
                
                # Quality score should be reasonable
                assert 0 <= thresholds.min_quality_score <= 100
                
                # Audio level should be reasonable
                assert 0 <= thresholds.min_audio_level <= 1
