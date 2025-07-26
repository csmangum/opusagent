"""Audio Quality Monitoring Module.

This module provides real-time audio quality analysis including:
- Signal-to-Noise Ratio (SNR) calculation
- Total Harmonic Distortion (THD) measurement
- Clipping detection
- Overall quality scoring
- Real-time alerts and logging
"""

import logging
import numpy as np
from typing import Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import time
from collections import deque

logger = logging.getLogger(__name__)


class QualityLevel(Enum):
    """Audio quality levels."""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    UNACCEPTABLE = "unacceptable"


@dataclass
class QualityThresholds:
    """Configurable quality thresholds."""
    min_snr_db: float = 15.0  # Lowered from 20.0 to be more realistic for telephony
    max_thd_percent: float = 1.0
    max_clipping_percent: float = 0.1
    min_quality_score: float = 60.0
    min_audio_level: float = 0.01  # Minimum RMS level to consider audio active


@dataclass
class QualityMetrics:
    """Audio quality metrics for a chunk."""
    snr_db: float
    thd_percent: float
    clipping_percent: float
    rms_level: float
    peak_level: float
    quality_score: float
    quality_level: QualityLevel
    timestamp: float


@dataclass
class QualityAlert:
    """Quality alert information."""
    alert_type: str
    severity: str
    message: str
    metrics: QualityMetrics
    timestamp: float


class AudioQualityMonitor:
    """Real-time audio quality monitoring and analysis."""

    def __init__(
        self,
        sample_rate: int = 16000,
        chunk_size: int = 1024,
        thresholds: Optional[QualityThresholds] = None,
        history_size: int = 100,
    ):
        """Initialize the audio quality monitor.

        Args:
            sample_rate: Audio sample rate in Hz
            chunk_size: Number of samples per chunk
            thresholds: Quality thresholds configuration
            history_size: Number of recent metrics to keep in history
        """
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.thresholds = thresholds or QualityThresholds()
        self.history_size = history_size

        # Quality history
        self.quality_history: deque = deque(maxlen=history_size)
        self.alert_history: deque = deque(maxlen=history_size)

        # Statistics
        self.total_chunks_analyzed = 0
        self.alerts_triggered = 0
        self.start_time = time.time()

        # Callbacks
        self.on_quality_alert: Optional[Callable[[QualityAlert], None]] = None
        self.on_metrics_update: Optional[Callable[[QualityMetrics], None]] = None

        logger.info(f"AudioQualityMonitor initialized: sample_rate={sample_rate}, chunk_size={chunk_size}")

    def analyze_audio_chunk(self, audio_bytes: bytes) -> QualityMetrics:
        """Analyze audio quality for a single chunk.

        Args:
            audio_bytes: Raw audio data as bytes (16-bit PCM)

        Returns:
            QualityMetrics object with analysis results
        """
        try:
            # Convert bytes to numpy array
            audio_array = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0

            # Calculate basic metrics
            rms_level = np.sqrt(np.mean(audio_array ** 2))
            peak_level = np.max(np.abs(audio_array))

            # Skip analysis if audio is too quiet
            if rms_level < self.thresholds.min_audio_level:
                return QualityMetrics(
                    snr_db=0.0,
                    thd_percent=0.0,
                    clipping_percent=0.0,
                    rms_level=float(rms_level),
                    peak_level=float(peak_level),
                    quality_score=0.0,
                    quality_level=QualityLevel.UNACCEPTABLE,
                    timestamp=time.time()
                )

            # Calculate SNR
            snr_db = self._calculate_snr(audio_array)

            # Calculate THD
            thd_percent = self._calculate_thd(audio_array)

            # Calculate clipping percentage
            clipping_percent = self._calculate_clipping(audio_array)

            # Calculate overall quality score
            quality_score = self._calculate_quality_score(snr_db, thd_percent, clipping_percent, rms_level)

            # Determine quality level
            quality_level = self._determine_quality_level(quality_score)

            # Create metrics object
            metrics = QualityMetrics(
                snr_db=float(snr_db),
                thd_percent=float(thd_percent),
                clipping_percent=float(clipping_percent),
                rms_level=float(rms_level),
                peak_level=float(peak_level),
                quality_score=float(quality_score),
                quality_level=quality_level,
                timestamp=time.time()
            )

            # Store in history
            self.quality_history.append(metrics)
            self.total_chunks_analyzed += 1

            # Check for quality alerts
            self._check_quality_alerts(metrics)

            # Trigger callback if set
            if self.on_metrics_update:
                self.on_metrics_update(metrics)

            return metrics

        except Exception as e:
            logger.error(f"Error analyzing audio chunk: {e}")
            return QualityMetrics(
                snr_db=0.0,
                thd_percent=0.0,
                clipping_percent=0.0,
                rms_level=0.0,
                peak_level=0.0,
                quality_score=0.0,
                quality_level=QualityLevel.UNACCEPTABLE,
                timestamp=time.time()
            )

    def _calculate_snr(self, audio_array: np.ndarray) -> float:
        """Calculate Signal-to-Noise Ratio in dB using spectral analysis.

        Args:
            audio_array: Normalized audio samples

        Returns:
            SNR in dB
        """
        try:
            # Calculate FFT
            fft = np.fft.fft(audio_array)
            magnitude = np.abs(fft)
            
            # Find the fundamental frequency (strongest component)
            fundamental_idx = np.argmax(magnitude[1:len(magnitude)//2]) + 1
            
            if fundamental_idx == 0:
                return 0.0
            
            # Calculate signal power around fundamental frequency
            signal_bandwidth = 50  # Hz
            freq_resolution = self.sample_rate / len(audio_array)  # Hz per bin
            bandwidth_bins = max(1, int(signal_bandwidth / freq_resolution))
            
            start_bin = max(0, fundamental_idx - bandwidth_bins)
            end_bin = min(len(magnitude)//2, fundamental_idx + bandwidth_bins)
            
            signal_power = np.sum(magnitude[start_bin:end_bin] ** 2)
            
            # Calculate noise power from remaining frequency bins
            noise_bins = np.concatenate([
                magnitude[1:start_bin],
                magnitude[end_bin:len(magnitude)//2]
            ])
            
            if len(noise_bins) > 0:
                noise_power = np.mean(noise_bins ** 2)
            else:
                # Fallback to fixed noise floor for very clean signals
                noise_power = 1e-8
            
            if noise_power > 0:
                snr_db = 10 * np.log10(signal_power / noise_power)
                return float(max(0.0, snr_db))
            else:
                return 0.0
                
        except Exception as e:
            logger.debug(f"Error calculating SNR: {e}")
            return 0.0

    def _calculate_thd(self, audio_array: np.ndarray) -> float:
        """Calculate Total Harmonic Distortion percentage.

        Args:
            audio_array: Normalized audio samples

        Returns:
            THD percentage
        """
        try:
            # Simplified THD calculation using FFT
            fft = np.fft.fft(audio_array)
            magnitude = np.abs(fft)
            
            # Find fundamental frequency (strongest component)
            fundamental_idx = np.argmax(magnitude[1:len(magnitude)//2]) + 1
            
            if fundamental_idx == 0:
                return 0.0
            
            fundamental_magnitude = magnitude[fundamental_idx]
            
            # Calculate harmonics (2nd, 3rd, 4th, 5th)
            harmonic_magnitudes = []
            for i in range(2, 6):
                harmonic_idx = fundamental_idx * i
                if harmonic_idx < len(magnitude) // 2:
                    harmonic_magnitudes.append(magnitude[harmonic_idx])
            
            if not harmonic_magnitudes:
                return 0.0
            
            # Calculate THD
            harmonic_rms = np.sqrt(np.mean(np.array(harmonic_magnitudes) ** 2))
            thd_percent = (harmonic_rms / fundamental_magnitude) * 100
            
            return min(100.0, thd_percent)
        except Exception as e:
            logger.debug(f"Error calculating THD: {e}")
            return 0.0

    def _calculate_clipping(self, audio_array: np.ndarray) -> float:
        """Calculate clipping percentage.

        Args:
            audio_array: Normalized audio samples

        Returns:
            Clipping percentage
        """
        try:
            # Count samples that are at or near maximum amplitude
            clipping_threshold = 0.95  # 95% of max amplitude
            clipped_samples = np.sum(np.abs(audio_array) >= clipping_threshold)
            clipping_percent = (clipped_samples / len(audio_array)) * 100
            
            return float(clipping_percent)
        except Exception as e:
            logger.debug(f"Error calculating clipping: {e}")
            return 0.0

    def _calculate_quality_score(self, snr_db: float, thd_percent: float, 
                               clipping_percent: float, rms_level: float) -> float:
        """Calculate overall quality score (0-100).

        Args:
            snr_db: Signal-to-noise ratio in dB
            thd_percent: Total harmonic distortion percentage
            clipping_percent: Clipping percentage
            rms_level: RMS audio level

        Returns:
            Quality score from 0 to 100
        """
        try:
            # SNR score (0-40 points)
            snr_score = min(40.0, max(0.0, snr_db / 2.0))
            
            # THD score (0-30 points)
            thd_score = max(0.0, 30.0 - (thd_percent * 3.0))
            
            # Clipping score (0-20 points)
            clipping_score = max(0.0, 20.0 - (clipping_percent * 20.0))
            
            # Level score (0-10 points) - penalize very low levels
            level_score = min(10.0, rms_level * 100.0)
            
            total_score = snr_score + thd_score + clipping_score + level_score
            
            return max(0.0, min(100.0, total_score))
        except Exception as e:
            logger.debug(f"Error calculating quality score: {e}")
            return 0.0

    def _determine_quality_level(self, quality_score: float) -> QualityLevel:
        """Determine quality level based on score.

        Args:
            quality_score: Overall quality score (0-100)

        Returns:
            QualityLevel enum
        """
        if quality_score >= 90:
            return QualityLevel.EXCELLENT
        elif quality_score >= 75:
            return QualityLevel.GOOD
        elif quality_score >= 60:
            return QualityLevel.FAIR
        elif quality_score >= 40:
            return QualityLevel.POOR
        else:
            return QualityLevel.UNACCEPTABLE

    def _check_quality_alerts(self, metrics: QualityMetrics) -> None:
        """Check for quality alerts and trigger callbacks.

        Args:
            metrics: Quality metrics to check
        """
        alerts = []

        # Check SNR
        if metrics.snr_db < self.thresholds.min_snr_db:
            alerts.append(QualityAlert(
                alert_type="low_snr",
                severity="warning" if metrics.snr_db > 10 else "error",
                message=f"Low SNR detected: {metrics.snr_db:.1f} dB (threshold: {self.thresholds.min_snr_db} dB)",
                metrics=metrics,
                timestamp=time.time()
            ))

        # Check THD
        if metrics.thd_percent > self.thresholds.max_thd_percent:
            alerts.append(QualityAlert(
                alert_type="high_thd",
                severity="warning" if metrics.thd_percent < 5 else "error",
                message=f"High THD detected: {metrics.thd_percent:.2f}% (threshold: {self.thresholds.max_thd_percent}%)",
                metrics=metrics,
                timestamp=time.time()
            ))

        # Check clipping
        if metrics.clipping_percent > self.thresholds.max_clipping_percent:
            alerts.append(QualityAlert(
                alert_type="clipping",
                severity="warning" if metrics.clipping_percent < 5 else "error",
                message=f"Audio clipping detected: {metrics.clipping_percent:.2f}% (threshold: {self.thresholds.max_clipping_percent}%)",
                metrics=metrics,
                timestamp=time.time()
            ))

        # Check overall quality score
        if metrics.quality_score < self.thresholds.min_quality_score:
            alerts.append(QualityAlert(
                alert_type="low_quality",
                severity="warning" if metrics.quality_score > 30 else "error",
                message=f"Low quality score: {metrics.quality_score:.1f} (threshold: {self.thresholds.min_quality_score})",
                metrics=metrics,
                timestamp=time.time()
            ))

        # Log and trigger alerts
        for alert in alerts:
            self.alert_history.append(alert)
            self.alerts_triggered += 1
            
            log_level = logging.ERROR if alert.severity == "error" else logging.WARNING
            logger.log(log_level, f"Quality Alert: {alert.message}")
            
            if self.on_quality_alert:
                self.on_quality_alert(alert)

    def get_quality_summary(self) -> Dict:
        """Get summary of quality metrics.

        Returns:
            Dictionary with quality summary statistics
        """
        if not self.quality_history:
            return {
                "total_chunks": 0,
                "average_quality_score": 0.0,
                "average_snr_db": 0.0,
                "average_thd_percent": 0.0,
                "average_clipping_percent": 0.0,
                "alerts_triggered": 0,
                "quality_distribution": {},
                "session_duration": 0.0
            }

        # Calculate averages
        avg_quality = np.mean([m.quality_score for m in self.quality_history])
        avg_snr = np.mean([m.snr_db for m in self.quality_history])
        avg_thd = np.mean([m.thd_percent for m in self.quality_history])
        avg_clipping = np.mean([m.clipping_percent for m in self.quality_history])

        # Quality level distribution
        quality_dist = {}
        for level in QualityLevel:
            count = sum(1 for m in self.quality_history if m.quality_level == level)
            quality_dist[level.value] = count

        return {
            "total_chunks": self.total_chunks_analyzed,
            "average_quality_score": avg_quality,
            "average_snr_db": avg_snr,
            "average_thd_percent": avg_thd,
            "average_clipping_percent": avg_clipping,
            "alerts_triggered": self.alerts_triggered,
            "quality_distribution": quality_dist,
            "session_duration": time.time() - self.start_time
        }

    def get_recent_metrics(self, count: int = 10) -> List[QualityMetrics]:
        """Get recent quality metrics.

        Args:
            count: Number of recent metrics to return

        Returns:
            List of recent QualityMetrics objects
        """
        return list(self.quality_history)[-count:]

    def get_recent_alerts(self, count: int = 10) -> List[QualityAlert]:
        """Get recent quality alerts.

        Args:
            count: Number of recent alerts to return

        Returns:
            List of recent QualityAlert objects
        """
        return list(self.alert_history)[-count:]

    def reset(self) -> None:
        """Reset the quality monitor state."""
        self.quality_history.clear()
        self.alert_history.clear()
        self.total_chunks_analyzed = 0
        self.alerts_triggered = 0
        self.start_time = time.time()
        logger.info("AudioQualityMonitor reset") 