"""
Adaptive quality management for audio processing.

This module provides dynamic quality adjustment based on performance metrics,
error rates, and latency to optimize system performance under varying conditions.
"""

import logging
import time
from collections import deque
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class QualityLevel:
    """Quality level configuration."""
    
    def __init__(
        self, 
        name: str, 
        error_rate_threshold: float, 
        latency_threshold_ms: float,
        sample_rate: int,
        bit_depth: int,
        compression_ratio: float = 1.0
    ):
        self.name = name
        self.error_rate_threshold = error_rate_threshold
        self.latency_threshold_ms = latency_threshold_ms
        self.sample_rate = sample_rate
        self.bit_depth = bit_depth
        self.compression_ratio = compression_ratio


class AdaptiveQualityManager:
    """Manages adaptive quality adjustment based on performance metrics."""
    
    def __init__(self, initial_quality: str = 'high'):
        """
        Initialize adaptive quality manager.
        
        Args:
            initial_quality: Starting quality level
        """
        # Define quality levels - more aggressive thresholds for better adaptation
        self.quality_levels = {
            'high': QualityLevel('high', 0.15, 150, 24000, 16, 1.0),
            'medium': QualityLevel('medium', 0.25, 300, 16000, 16, 0.8),
            'low': QualityLevel('low', 0.40, 800, 8000, 16, 0.6)
        }
        
        self.current_quality = initial_quality
        if self.current_quality not in self.quality_levels:
            logger.warning(f"Invalid initial quality '{initial_quality}', using 'high'")
            self.current_quality = 'high'
        
        # Performance tracking
        self.error_count = 0
        self.success_count = 0
        self.latency_samples = deque(maxlen=100)
        self.quality_changes = []
        
        # Timing
        self.last_adjustment_time = time.time()
        self.min_adjustment_interval = 10.0  # Reduced from 30s to 10s for faster adaptation
        
        # Statistics
        self.total_requests = 0
        self.quality_downgrades = 0
        self.quality_upgrades = 0
        
        logger.info(f"Adaptive quality manager initialized with '{self.current_quality}' quality")
    
    def record_success(self, latency_ms: float) -> None:
        """
        Record a successful operation.
        
        Args:
            latency_ms: Operation latency in milliseconds
        """
        self.success_count += 1
        self.total_requests += 1
        self.latency_samples.append(latency_ms)
        
        logger.debug(f"Recorded success: latency={latency_ms:.1f}ms, quality={self.current_quality}")
    
    def record_error(self, latency_ms: float) -> None:
        """
        Record a failed operation.
        
        Args:
            latency_ms: Operation latency in milliseconds
        """
        self.error_count += 1
        self.total_requests += 1
        self.latency_samples.append(latency_ms)
        
        logger.warning(f"Recorded error: latency={latency_ms:.1f}ms, quality={self.current_quality}")
    
    def should_adjust_quality(self) -> bool:
        """
        Check if quality should be adjusted based on current metrics.
        
        Returns:
            True if quality adjustment is recommended
        """
        # Check minimum interval
        if time.time() - self.last_adjustment_time < self.min_adjustment_interval:
            logger.debug(f"Quality adjustment blocked: minimum interval not met ({time.time() - self.last_adjustment_time:.1f}s < {self.min_adjustment_interval}s)")
            return False
        
        # Need minimum sample size
        if self.total_requests < 10:
            logger.debug(f"Quality adjustment blocked: insufficient samples ({self.total_requests} < 10)")
            return False
        
        current_level = self.quality_levels[self.current_quality]
        error_rate = self.error_count / self.total_requests
        avg_latency = self._calculate_average_latency()
        
        logger.debug(f"Quality check - Error rate: {error_rate:.3f} (threshold: {current_level.error_rate_threshold}), "
                    f"Latency: {avg_latency:.1f}ms (threshold: {current_level.latency_threshold_ms}ms)")
        
        # Check if current performance exceeds thresholds
        if (error_rate > current_level.error_rate_threshold or 
            avg_latency > current_level.latency_threshold_ms):
            logger.debug(f"Quality adjustment triggered: performance exceeds thresholds")
            return True
        
        # Check if we can upgrade quality (performance is good)
        quality_order = ['high', 'medium', 'low']
        current_index = quality_order.index(self.current_quality)
        if current_index > 0:
            next_quality = quality_order[current_index - 1]
            next_level = self.quality_levels[next_quality]
            if (error_rate < next_level.error_rate_threshold * 0.5 and
                avg_latency < next_level.latency_threshold_ms * 0.5):
                logger.debug(f"Quality adjustment triggered: conditions allow upgrade")
                return True
        
        logger.debug("Quality adjustment not needed")
        return False
    
    def adjust_quality(self) -> Optional[str]:
        """
        Adjust quality level based on current performance metrics.
        
        Returns:
            New quality level name, or None if no change
        """
        if not self.should_adjust_quality():
            return None
        
        current_level = self.quality_levels[self.current_quality]
        error_rate = self.error_count / self.total_requests
        avg_latency = self._calculate_average_latency()
        
        old_quality = self.current_quality
        
        # Determine new quality level
        if (error_rate > current_level.error_rate_threshold or 
            avg_latency > current_level.latency_threshold_ms):
            # Performance is poor - degrade quality
            new_quality = self._degrade_quality()
            if new_quality != old_quality:
                self.quality_downgrades += 1
                logger.warning(
                    f"Degrading quality from '{old_quality}' to '{new_quality}' "
                    f"(error_rate: {error_rate:.3f}, latency: {avg_latency:.1f}ms)"
                )
        else:
            # Performance is good - try to improve quality
            new_quality = self._improve_quality(error_rate, avg_latency)
            if new_quality != old_quality:
                self.quality_upgrades += 1
                logger.info(
                    f"Upgrading quality from '{old_quality}' to '{new_quality}' "
                    f"(error_rate: {error_rate:.3f}, latency: {avg_latency:.1f}ms)"
                )
        
        if new_quality != old_quality:
            self.current_quality = new_quality
            self.last_adjustment_time = time.time()
            self.quality_changes.append({
                'timestamp': time.time(),
                'from_quality': old_quality,
                'to_quality': new_quality,
                'error_rate': error_rate,
                'avg_latency': avg_latency,
                'reason': 'performance_adjustment'
            })
            
            # Reset counters for new quality level
            self.error_count = 0
            self.success_count = 0
        
        return new_quality if new_quality != old_quality else None
    
    def _degrade_quality(self) -> str:
        """Degrade to next lower quality level."""
        quality_order = ['high', 'medium', 'low']
        current_index = quality_order.index(self.current_quality)
        
        if current_index < len(quality_order) - 1:
            return quality_order[current_index + 1]
        return self.current_quality  # Already at lowest
    
    def _improve_quality(self, error_rate: float, avg_latency: float) -> str:
        """Improve to next higher quality level if conditions allow."""
        quality_order = ['high', 'medium', 'low']
        current_index = quality_order.index(self.current_quality)
        
        if current_index > 0:
            # Check if next higher level would be sustainable
            next_quality = quality_order[current_index - 1]
            next_level = self.quality_levels[next_quality]
            
            # Only upgrade if we're well below thresholds
            if (error_rate < next_level.error_rate_threshold * 0.5 and
                avg_latency < next_level.latency_threshold_ms * 0.5):
                return next_quality
        
        return self.current_quality
    
    def _calculate_average_latency(self) -> float:
        """Calculate average latency from recent samples."""
        if not self.latency_samples:
            return 0.0
        return sum(self.latency_samples) / len(self.latency_samples)
    
    def get_current_quality_config(self) -> QualityLevel:
        """Get current quality level configuration."""
        return self.quality_levels[self.current_quality]
    
    def get_statistics(self) -> Dict:
        """
        Get quality management statistics.
        
        Returns:
            Dictionary with quality management statistics
        """
        current_level = self.quality_levels[self.current_quality]
        error_rate = self.error_count / self.total_requests if self.total_requests > 0 else 0.0
        avg_latency = self._calculate_average_latency()
        
        return {
            'current_quality': self.current_quality,
            'total_requests': self.total_requests,
            'error_count': self.error_count,
            'success_count': self.success_count,
            'error_rate': error_rate,
            'average_latency_ms': avg_latency,
            'quality_downgrades': self.quality_downgrades,
            'quality_upgrades': self.quality_upgrades,
            'quality_changes': len(self.quality_changes),
            'current_thresholds': {
                'error_rate': current_level.error_rate_threshold,
                'latency_ms': current_level.latency_threshold_ms
            },
            'current_config': {
                'sample_rate': current_level.sample_rate,
                'bit_depth': current_level.bit_depth,
                'compression_ratio': current_level.compression_ratio
            },
            'recent_changes': self.quality_changes[-5:] if self.quality_changes else []
        }
    
    def force_quality_level(self, quality: str) -> bool:
        """
        Force a specific quality level.
        
        Args:
            quality: Quality level to force
            
        Returns:
            True if quality was changed, False if invalid
        """
        if quality not in self.quality_levels:
            logger.error(f"Invalid quality level: {quality}")
            return False
        
        if quality != self.current_quality:
            old_quality = self.current_quality
            self.current_quality = quality
            self.last_adjustment_time = time.time()
            
            self.quality_changes.append({
                'timestamp': time.time(),
                'from_quality': old_quality,
                'to_quality': quality,
                'error_rate': self.error_count / self.total_requests if self.total_requests > 0 else 0.0,
                'avg_latency': self._calculate_average_latency(),
                'reason': 'manual_override'
            })
            
            logger.info(f"Forced quality change from '{old_quality}' to '{quality}'")
            return True
        
        return False
    
    def reset_statistics(self) -> None:
        """Reset all statistics and counters."""
        self.error_count = 0
        self.success_count = 0
        self.total_requests = 0
        self.latency_samples.clear()
        self.quality_changes.clear()
        self.quality_downgrades = 0
        self.quality_upgrades = 0
        self.last_adjustment_time = time.time()
        
        logger.info("Quality management statistics reset")
    
    def get_available_quality_levels(self) -> List[str]:
        """Get list of available quality levels."""
        return list(self.quality_levels.keys())
    
    def get_quality_level_config(self, quality: str) -> Optional[QualityLevel]:
        """Get configuration for a specific quality level."""
        return self.quality_levels.get(quality) 