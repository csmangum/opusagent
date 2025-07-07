#!/usr/bin/env python3
"""
Test script for Audio Quality Monitoring functionality.

This script demonstrates the audio quality monitoring features including:
- SNR calculation
- THD measurement
- Clipping detection
- Quality scoring
- Real-time alerts
"""

import numpy as np
import time
from opusagent.audio_quality_monitor import (
    AudioQualityMonitor, 
    QualityThresholds, 
    QualityLevel
)


def generate_test_audio(duration_seconds: float = 1.0, sample_rate: int = 16000, 
                       signal_type: str = "clean") -> bytes:
    """Generate test audio data for quality analysis.
    
    Args:
        duration_seconds: Duration of audio in seconds
        sample_rate: Sample rate in Hz
        signal_type: Type of signal to generate ("clean", "noisy", "clipped", "distorted", "silence", "speech", "lowlevel")
        
    Returns:
        Audio data as bytes (16-bit PCM)
    """
    num_samples = int(duration_seconds * sample_rate)
    t = np.linspace(0, duration_seconds, num_samples)
    
    if signal_type == "clean":
        # Clean sine wave
        signal = 0.5 * np.sin(2 * np.pi * 440 * t)  # 440 Hz tone
    elif signal_type == "noisy":
        # Noisy signal
        signal = 0.3 * np.sin(2 * np.pi * 440 * t) + 0.1 * np.random.randn(num_samples)
    elif signal_type == "clipped":
        # Clipped signal - create actual clipping above 95%
        signal = 1.2 * np.sin(2 * np.pi * 440 * t)  # Amplitude > 1.0 to ensure clipping
        signal = np.clip(signal, -1.0, 1.0)  # Hard clip at ±1.0
    elif signal_type == "distorted":
        # Distorted signal with harmonics
        signal = 0.4 * np.sin(2 * np.pi * 440 * t) + 0.1 * np.sin(2 * np.pi * 880 * t)
        signal += 0.05 * np.sin(2 * np.pi * 1320 * t)  # Add harmonics
    elif signal_type == "silence":
        # Silence
        signal = np.zeros(num_samples)
    elif signal_type == "speech":
        # Speech-like: sum of several formant-like sine waves
        signal = 0.2 * np.sin(2 * np.pi * 220 * t) + 0.15 * np.sin(2 * np.pi * 660 * t)
        signal += 0.1 * np.sin(2 * np.pi * 1100 * t) + 0.05 * np.sin(2 * np.pi * 1760 * t)
        signal += 0.02 * np.random.randn(num_samples)  # Add a little noise
    elif signal_type == "lowlevel":
        # Low-level clean sine wave
        signal = 0.05 * np.sin(2 * np.pi * 440 * t)
    else:
        signal = 0.5 * np.sin(2 * np.pi * 440 * t)
    
    # Convert to 16-bit PCM
    audio_int16 = (signal * 32767).astype(np.int16)
    return audio_int16.tobytes()


def test_quality_monitoring():
    """Test the audio quality monitoring functionality."""
    print("=== Audio Quality Monitoring Test ===\n")
    
    # Configure quality thresholds
    thresholds = QualityThresholds(
        min_snr_db=15.0,  # Lowered for telephony realism
        max_thd_percent=1.0,
        max_clipping_percent=0.1,
        min_quality_score=60.0,
    )
    
    # Initialize quality monitor
    monitor = AudioQualityMonitor(
        sample_rate=16000,
        chunk_size=1024,
        thresholds=thresholds,
        history_size=50
    )
    
    # Set up alert callback
    def on_quality_alert(alert):
        print(f"🚨 ALERT: {alert.severity.upper()} - {alert.message}")
    
    monitor.on_quality_alert = on_quality_alert
    
    # Test different audio types (add more realistic scenarios)
    test_signals = [
        ("clean", "Clean sine wave"),
        ("noisy", "Noisy signal"),
        ("clipped", "Clipped signal"),
        ("distorted", "Distorted signal with harmonics"),
        ("silence", "Silence (noise floor test)"),
        ("speech", "Speech-like synthetic signal"),
        ("lowlevel", "Low-level clean sine wave"),
    ]
    
    for signal_type, description in test_signals:
        print(f"\n--- Testing {description} ---")
        
        # Generate test audio
        audio_data = generate_test_audio(duration_seconds=0.5, signal_type=signal_type)
        
        # Analyze quality
        metrics = monitor.analyze_audio_chunk(audio_data)
        
        # Display results
        print(f"SNR: {metrics.snr_db:.1f} dB")
        print(f"THD: {metrics.thd_percent:.2f}%")
        print(f"Clipping: {metrics.clipping_percent:.2f}%")
        print(f"RMS Level: {metrics.rms_level:.3f}")
        print(f"Peak Level: {metrics.peak_level:.3f}")
        print(f"Quality Score: {metrics.quality_score:.1f}/100")
        print(f"Quality Level: {metrics.quality_level.value}")
        
        time.sleep(0.1)  # Small delay between tests
    
    # Display summary
    print(f"\n=== Quality Monitoring Summary ===")
    summary = monitor.get_quality_summary()
    print(f"Total chunks analyzed: {summary['total_chunks']}")
    print(f"Average quality score: {summary['average_quality_score']:.1f}")
    print(f"Average SNR: {summary['average_snr_db']:.1f} dB")
    print(f"Average THD: {summary['average_thd_percent']:.2f}%")
    print(f"Average clipping: {summary['average_clipping_percent']:.2f}%")
    print(f"Alerts triggered: {summary['alerts_triggered']}")
    print(f"Session duration: {summary['session_duration']:.1f} seconds")
    
    # Quality distribution
    print(f"\nQuality Distribution:")
    for level, count in summary['quality_distribution'].items():
        print(f"  {level}: {count} chunks")
    
    # Recent alerts
    recent_alerts = monitor.get_recent_alerts(5)
    if recent_alerts:
        print(f"\nRecent Alerts:")
        for alert in recent_alerts:
            print(f"  [{alert.severity.upper()}] {alert.message}")
    else:
        print(f"\nNo alerts triggered during testing.")


def test_threshold_configuration():
    """Test different threshold configurations."""
    print(f"\n=== Threshold Configuration Test ===\n")
    
    # Test with strict thresholds
    strict_thresholds = QualityThresholds(
        min_snr_db=30.0,      # Higher SNR requirement
        max_thd_percent=0.5,  # Lower THD tolerance
        max_clipping_percent=0.05,  # Lower clipping tolerance
        min_quality_score=80.0,     # Higher quality score requirement
    )
    
    monitor = AudioQualityMonitor(
        sample_rate=16000,
        chunk_size=1024,
        thresholds=strict_thresholds,
        history_size=10
    )
    
    def on_alert(alert):
        print(f"🔴 STRICT THRESHOLD ALERT: {alert.message}")
    
    monitor.on_quality_alert = on_alert
    
    # Test with noisy signal (should trigger alerts with strict thresholds)
    audio_data = generate_test_audio(duration_seconds=0.5, signal_type="noisy")
    metrics = monitor.analyze_audio_chunk(audio_data)
    
    print(f"Testing noisy signal with strict thresholds:")
    print(f"SNR: {metrics.snr_db:.1f} dB (threshold: {strict_thresholds.min_snr_db} dB)")
    print(f"THD: {metrics.thd_percent:.2f}% (threshold: {strict_thresholds.max_thd_percent}%)")
    print(f"Clipping: {metrics.clipping_percent:.2f}% (threshold: {strict_thresholds.max_clipping_percent}%)")
    print(f"Quality Score: {metrics.quality_score:.1f} (threshold: {strict_thresholds.min_quality_score})")


if __name__ == "__main__":
    test_quality_monitoring()
    test_threshold_configuration()
    print(f"\n✅ Audio Quality Monitoring test completed!") 