# Resilience Implementation Guide

## Overview

This guide explains how to implement and use the enhanced error handling and resilience features in the FastAgent system. These features provide robust handling of real-world failure scenarios including network jitter, audio corruption, and service degradation.

## Quick Start

### 1. Basic Usage

To enable resilience features in your audio stream handler:

```python
from opusagent.enhanced_audio_stream_handler import EnhancedAudioStreamHandler

# Create enhanced handler with resilience enabled
handler = EnhancedAudioStreamHandler(
    platform_websocket=platform_ws,
    realtime_websocket=openai_ws,
    enable_resilience=True  # Enable all resilience features
)
```

### 2. Individual Components

You can also use resilience components individually:

```python
from opusagent.resilience import (
    AudioDataValidator,
    AudioChunkRecovery,
    CircuitBreaker,
    AdaptiveQualityManager
)

# Audio validation
audio_bytes = AudioDataValidator.validate_and_decode_audio(audio_b64)

# Chunk recovery
recovery = AudioChunkRecovery()
result = await recovery.process_chunk_with_recovery(audio_b64)

# Circuit breaker
cb = CircuitBreaker(failure_threshold=5)
result = await cb.call(external_service_function)

# Quality management
qm = AdaptiveQualityManager()
qm.record_success(latency_ms)
new_quality = qm.adjust_quality()
```

## Component Details

### AudioDataValidator

Handles base64 decoding and audio validation with comprehensive error recovery.

**Key Features:**
- Validates base64 format and padding
- Detects corrupted audio data
- Provides silence fallback for failed validation
- Audio quality analysis

**Usage:**
```python
# Basic validation
audio_bytes = AudioDataValidator.validate_and_decode_audio(audio_b64)

# With size constraints
audio_bytes = AudioDataValidator.validate_and_decode_audio(
    audio_b64,
    expected_size_range=(1000, 10000),
    fallback_silence_ms=100
)

# Quality analysis
quality = AudioDataValidator.validate_audio_quality(audio_bytes)
if quality['issues']:
    print(f"Audio issues: {quality['issues']}")
```

### AudioChunkRecovery

Handles network jitter and timing issues in audio processing.

**Key Features:**
- Detects delayed audio chunks
- Inserts silence to maintain timing
- Tracks recovery statistics
- Adaptive parameter adjustment

**Usage:**
```python
recovery = AudioChunkRecovery(
    max_chunk_delay_ms=500,  # Maximum acceptable delay
    buffer_size=10           # Number of chunks to buffer
)

# Process chunk with recovery
result = await recovery.process_chunk_with_recovery(
    audio_b64,
    timestamp=time.time(),
    chunk_sequence=123
)

# Check recovery statistics
stats = recovery.get_recovery_statistics()
print(f"Recovery rate: {stats['recovery_rate']:.2%}")
```

### CircuitBreaker

Protects against cascading failures in external service calls.

**Key Features:**
- Automatic circuit opening on failures
- Configurable failure thresholds
- Recovery timeout and half-open state
- Comprehensive statistics

**Usage:**
```python
# Create circuit breaker
cb = CircuitBreaker(
    failure_threshold=5,      # Failures before opening
    recovery_timeout=60.0,    # Seconds to wait before recovery
    name="openai_api"         # Name for monitoring
)

# Use with external service
try:
    result = await cb.call(openai_api_function, *args, **kwargs)
except Exception as e:
    print(f"Circuit breaker protected call failed: {e}")

# Check statistics
stats = cb.get_statistics()
print(f"Success rate: {stats['success_rate']:.2%}")
```

### AdaptiveQualityManager

Dynamically adjusts quality settings based on performance metrics.

**Key Features:**
- Three quality levels: high, medium, low
- Automatic degradation/improvement
- Performance-based thresholds
- Quality change tracking

**Usage:**
```python
qm = AdaptiveQualityManager(initial_quality='high')

# Record performance
qm.record_success(latency_ms=50)   # Good performance
qm.record_error(latency_ms=300)    # Poor performance

# Check if adjustment needed
if qm.should_adjust_quality():
    new_quality = qm.adjust_quality()
    print(f"Quality adjusted to: {new_quality}")

# Get current configuration
config = qm.get_current_quality_config()
print(f"Sample rate: {config.sample_rate}Hz")
```

## Integration Examples

### 1. Enhanced Audio Stream Handler

The `EnhancedAudioStreamHandler` integrates all resilience components:

```python
from opusagent.enhanced_audio_stream_handler import EnhancedAudioStreamHandler

# Create enhanced handler
handler = EnhancedAudioStreamHandler(
    platform_websocket=platform_ws,
    realtime_websocket=openai_ws,
    enable_resilience=True,
    bridge_type='twilio'
)

# Use normally - resilience is automatic
await handler.handle_incoming_audio(audio_data)

# Get resilience statistics
stats = handler.get_resilience_statistics()
print(f"Recovery events: {stats['performance_metrics']['recovery_events']}")
```

### 2. Custom Integration

For custom implementations:

```python
class CustomAudioProcessor:
    def __init__(self):
        self.audio_validator = AudioDataValidator()
        self.chunk_recovery = AudioChunkRecovery()
        self.openai_cb = CircuitBreaker(name="openai")
        self.quality_manager = AdaptiveQualityManager()
    
    async def process_audio(self, audio_b64: str):
        # Validate audio
        audio_bytes = self.audio_validator.validate_and_decode_audio(audio_b64)
        
        # Handle timing recovery
        recovery_result = await self.chunk_recovery.process_chunk_with_recovery(audio_b64)
        
        # Process with circuit breaker protection
        result = await self.openai_cb.call(self.send_to_openai, audio_bytes)
        
        # Update quality metrics
        self.quality_manager.record_success(processing_time_ms)
        
        return result
```

## Testing and Validation

### 1. Run Resilience Tests

```bash
# Run comprehensive resilience tests
python scripts/test_resilience.py

# Run demonstration
python scripts/demo_resilience.py
```

### 2. Test Individual Components

```python
# Test audio validation
async def test_audio_validation():
    test_cases = [
        ("valid", b"normal_audio_data"),
        ("truncated", b"truncated_data"),
        ("corrupted", "invalid_base64"),
        ("empty", b"")
    ]
    
    for test_name, audio_data in test_cases:
        result = AudioDataValidator.validate_and_decode_audio(audio_data)
        print(f"{test_name}: {'✓' if result else '✗'}")

# Test circuit breaker
async def test_circuit_breaker():
    cb = CircuitBreaker(failure_threshold=3)
    
    def failing_service():
        raise Exception("Service down")
    
    # Should open circuit after 3 failures
    for i in range(5):
        try:
            await cb.call(failing_service)
        except Exception:
            pass
    
    assert cb.state.value == 'OPEN'
```

## Monitoring and Metrics

### 1. Performance Metrics

All resilience components provide comprehensive statistics:

```python
# Audio validation metrics
validation_stats = {
    'total_validations': 1000,
    'successful_validations': 950,
    'validation_error_rate': 0.05
}

# Chunk recovery metrics
recovery_stats = chunk_recovery.get_recovery_statistics()
# {
#     'total_chunks': 1000,
#     'chunks_with_delay': 50,
#     'silence_insertions': 25,
#     'recovery_rate': 0.075
# }

# Circuit breaker metrics
cb_stats = circuit_breaker.get_statistics()
# {
#     'total_requests': 500,
#     'success_rate': 0.85,
#     'circuit_opens': 2,
#     'average_response_time': 0.15
# }

# Quality management metrics
qm_stats = quality_manager.get_statistics()
# {
#     'current_quality': 'medium',
#     'quality_downgrades': 1,
#     'quality_upgrades': 0,
#     'error_rate': 0.12
# }
```

### 2. Alerting and Logging

Set up monitoring for critical metrics:

```python
# Monitor circuit breaker state changes
def circuit_breaker_monitor(name, old_state, new_state):
    if new_state.value == 'OPEN':
        logger.error(f"Circuit breaker {name} opened!")
        # Send alert to monitoring system
    
    if new_state.value == 'CLOSED':
        logger.info(f"Circuit breaker {name} recovered")

cb = CircuitBreaker(monitor_callback=circuit_breaker_monitor)

# Monitor quality degradation
if qm.should_adjust_quality():
    new_quality = qm.adjust_quality()
    if new_quality != qm.current_quality:
        logger.warning(f"Quality degraded to {new_quality}")
        # Send alert if quality drops significantly
```

## Best Practices

### 1. Configuration

- **Start conservative**: Use lower failure thresholds initially
- **Monitor and adjust**: Tune parameters based on real-world performance
- **Set appropriate timeouts**: Balance responsiveness with stability

### 2. Error Handling

- **Always provide fallbacks**: Ensure graceful degradation
- **Log comprehensively**: Include context for debugging
- **Monitor error patterns**: Identify systemic issues

### 3. Performance

- **Measure impact**: Track performance overhead of resilience features
- **Optimize hot paths**: Ensure critical paths remain fast
- **Cache when possible**: Reduce redundant operations

### 4. Testing

- **Test failure scenarios**: Simulate various failure conditions
- **Load test**: Verify behavior under high load
- **Chaos engineering**: Randomly inject failures in production-like environments

## Troubleshooting

### Common Issues

1. **High recovery rates**: May indicate network issues or misconfigured thresholds
2. **Circuit breaker opening frequently**: Check external service health and failure thresholds
3. **Quality degrading too quickly**: Adjust quality thresholds or investigate performance issues
4. **Memory usage**: Monitor buffer sizes and clear old statistics periodically

### Debugging

```python
# Enable debug logging
logging.getLogger('opusagent.resilience').setLevel(logging.DEBUG)

# Check component states
print(f"Circuit breaker state: {cb.state.value}")
print(f"Quality level: {qm.current_quality}")
print(f"Recovery buffer size: {len(chunk_recovery.chunk_buffer)}")

# Reset components if needed
cb.reset()
qm.reset_statistics()
chunk_recovery.reset_statistics()
```

## Conclusion

The resilience features provide robust error handling and recovery mechanisms for the FastAgent system. By implementing these features, you can significantly improve system reliability and user experience in real-world conditions with network issues, service failures, and audio corruption.

Start with the enhanced audio stream handler for automatic resilience, or integrate individual components for custom solutions. Monitor performance metrics and adjust configurations based on your specific requirements and failure patterns. 