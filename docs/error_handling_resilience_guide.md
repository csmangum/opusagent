# Error Handling & Resilience Testing Guide

## Overview

This document outlines comprehensive error handling strategies and resilience testing approaches for the FastAgent system, particularly focusing on real-world failure scenarios like network jitter, base64 decoding errors, and audio processing failures.

## Current Error Handling Analysis

### Strengths
- Basic try/except blocks in critical paths
- WebSocket connection state monitoring
- Audio quality monitoring and alerts
- Graceful degradation for missing components

### Areas for Improvement
- Limited fallback strategies for network failures
- No retry mechanisms for transient errors
- Insufficient handling of malformed audio data
- Missing circuit breaker patterns for external services

## Enhanced Error Handling Strategies

### 1. Network Resilience

#### WebSocket Connection Management
```python
class ResilientWebSocketManager:
    def __init__(self, max_retries=3, backoff_factor=2.0, timeout=30.0):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.timeout = timeout
        self.connection_attempts = 0
        self.last_failure_time = None
        
    async def connect_with_retry(self, uri: str) -> WebSocket:
        """Connect with exponential backoff and circuit breaker pattern."""
        for attempt in range(self.max_retries):
            try:
                websocket = await asyncio.wait_for(
                    websockets.connect(uri), 
                    timeout=self.timeout
                )
                self.connection_attempts = 0
                self.last_failure_time = None
                return websocket
            except Exception as e:
                self.connection_attempts += 1
                wait_time = self.backoff_factor ** attempt
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s")
                await asyncio.sleep(wait_time)
        
        raise ConnectionError(f"Failed to connect after {self.max_retries} attempts")
```

#### Message Delivery Reliability
```python
class ReliableMessageSender:
    def __init__(self, max_retries=3, ack_timeout=5.0):
        self.max_retries = max_retries
        self.ack_timeout = ack_timeout
        self.pending_messages = {}
        
    async def send_with_ack(self, websocket: WebSocket, message: dict) -> bool:
        """Send message with acknowledgment and retry logic."""
        message_id = str(uuid.uuid4())
        message['id'] = message_id
        
        for attempt in range(self.max_retries):
            try:
                await websocket.send(json.dumps(message))
                
                # Wait for acknowledgment
                try:
                    ack = await asyncio.wait_for(
                        websocket.recv(), 
                        timeout=self.ack_timeout
                    )
                    ack_data = json.loads(ack)
                    if ack_data.get('type') == 'ack' and ack_data.get('id') == message_id:
                        return True
                except asyncio.TimeoutError:
                    logger.warning(f"Ack timeout for message {message_id}, attempt {attempt + 1}")
                    
            except Exception as e:
                logger.error(f"Send attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(0.1 * (attempt + 1))
                    
        return False
```

### 2. Audio Processing Resilience

#### Base64 Decoding with Validation
```python
class AudioDataValidator:
    @staticmethod
    def validate_and_decode_audio(audio_chunk_b64: str, expected_size_range: tuple = None) -> bytes:
        """Validate and decode base64 audio data with comprehensive error handling."""
        try:
            # Validate base64 format
            if not audio_chunk_b64 or not isinstance(audio_chunk_b64, str):
                raise ValueError("Invalid audio chunk: must be non-empty string")
            
            # Check for valid base64 characters
            import re
            if not re.match(r'^[A-Za-z0-9+/]*={0,2}$', audio_chunk_b64):
                raise ValueError("Invalid base64 format")
            
            # Decode with error handling
            try:
                audio_bytes = base64.b64decode(audio_chunk_b64, validate=True)
            except binascii.Error as e:
                raise ValueError(f"Base64 decoding failed: {e}")
            
            # Validate decoded data
            if not audio_bytes:
                raise ValueError("Decoded audio data is empty")
            
            # Check size constraints if specified
            if expected_size_range:
                min_size, max_size = expected_size_range
                if len(audio_bytes) < min_size or len(audio_bytes) > max_size:
                    raise ValueError(f"Audio size {len(audio_bytes)} outside expected range {expected_size_range}")
            
            return audio_bytes
            
        except Exception as e:
            logger.error(f"Audio validation failed: {e}")
            # Return silence as fallback
            return b"\x00" * 3200  # 100ms of silence at 16kHz
```

#### Audio Chunk Recovery
```python
class AudioChunkRecovery:
    def __init__(self, max_chunk_delay_ms=500, silence_threshold=0.01):
        self.max_chunk_delay_ms = max_chunk_delay_ms
        self.silence_threshold = silence_threshold
        self.last_chunk_time = None
        self.chunk_buffer = []
        
    async def process_chunk_with_recovery(self, audio_chunk_b64: str, timestamp: float = None) -> bytes:
        """Process audio chunk with network jitter recovery."""
        try:
            # Validate and decode
            audio_bytes = AudioDataValidator.validate_and_decode_audio(audio_chunk_b64)
            
            # Handle timing issues
            current_time = timestamp or time.time()
            if self.last_chunk_time:
                delay_ms = (current_time - self.last_chunk_time) * 1000
                if delay_ms > self.max_chunk_delay_ms:
                    logger.warning(f"Large chunk delay detected: {delay_ms:.1f}ms")
                    # Insert silence to maintain timing
                    silence_duration = int(delay_ms / 10)  # 10ms per chunk
                    silence_bytes = b"\x00" * (silence_duration * 32)  # 16kHz, 16-bit
                    self.chunk_buffer.append(silence_bytes)
            
            self.last_chunk_time = current_time
            self.chunk_buffer.append(audio_bytes)
            
            # Return processed audio
            return audio_bytes
            
        except Exception as e:
            logger.error(f"Chunk recovery failed: {e}")
            # Return silence as fallback
            return b"\x00" * 3200
```

### 3. Circuit Breaker Pattern

#### Service Circuit Breaker
```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60, expected_exception=Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        
    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = 'HALF_OPEN'
                logger.info("Circuit breaker transitioning to HALF_OPEN")
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
            
    def _on_success(self):
        self.failure_count = 0
        self.state = 'CLOSED'
        
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'
            logger.error(f"Circuit breaker opened after {self.failure_count} failures")
```

### 4. Audio Quality Degradation Handling

#### Adaptive Quality Management
```python
class AdaptiveQualityManager:
    def __init__(self, initial_quality='high'):
        self.quality_levels = ['high', 'medium', 'low']
        self.current_quality = initial_quality
        self.error_count = 0
        self.success_count = 0
        self.quality_thresholds = {
            'high': {'error_rate': 0.05, 'latency_ms': 100},
            'medium': {'error_rate': 0.10, 'latency_ms': 200},
            'low': {'error_rate': 0.20, 'latency_ms': 500}
        }
        
    def adjust_quality(self, error_rate: float, avg_latency_ms: float):
        """Dynamically adjust quality based on performance metrics."""
        current_thresholds = self.quality_thresholds[self.current_quality]
        
        if (error_rate > current_thresholds['error_rate'] or 
            avg_latency_ms > current_thresholds['latency_ms']):
            self._degrade_quality()
        elif (error_rate < current_thresholds['error_rate'] * 0.5 and
              avg_latency_ms < current_thresholds['latency_ms'] * 0.5):
            self._improve_quality()
            
    def _degrade_quality(self):
        current_index = self.quality_levels.index(self.current_quality)
        if current_index < len(self.quality_levels) - 1:
            self.current_quality = self.quality_levels[current_index + 1]
            logger.warning(f"Degrading quality to {self.current_quality}")
            
    def _improve_quality(self):
        current_index = self.quality_levels.index(self.current_quality)
        if current_index > 0:
            self.current_quality = self.quality_levels[current_index - 1]
            logger.info(f"Improving quality to {self.current_quality}")
```

## Resilience Testing Framework

### 1. Network Failure Simulation

#### Network Condition Simulator
```python
class NetworkConditionSimulator:
    def __init__(self):
        self.latency_ms = 0
        self.packet_loss_rate = 0.0
        self.bandwidth_limit = None
        self.connection_drops = False
        
    async def simulate_network_conditions(self, websocket, message):
        """Simulate various network conditions for testing."""
        # Simulate latency
        if self.latency_ms > 0:
            await asyncio.sleep(self.latency_ms / 1000)
            
        # Simulate packet loss
        if random.random() < self.packet_loss_rate:
            logger.info("Simulating packet loss")
            return None
            
        # Simulate connection drop
        if self.connection_drops and random.random() < 0.1:
            logger.info("Simulating connection drop")
            await websocket.close()
            return None
            
        return message
```

### 2. Audio Processing Failure Tests

#### Audio Corruption Simulator
```python
class AudioCorruptionSimulator:
    @staticmethod
    def corrupt_audio_data(audio_bytes: bytes, corruption_type: str) -> bytes:
        """Simulate various types of audio data corruption."""
        if corruption_type == 'truncated':
            return audio_bytes[:len(audio_bytes)//2]
        elif corruption_type == 'noise':
            noise = bytes(random.getrandbits(8) for _ in range(len(audio_bytes)//10))
            return audio_bytes + noise
        elif corruption_type == 'malformed_base64':
            return base64.b64encode(audio_bytes + b'invalid').decode('utf-8')
        elif corruption_type == 'empty':
            return b''
        else:
            return audio_bytes
```

### 3. Comprehensive Test Scenarios

#### Resilience Test Suite
```python
class ResilienceTestSuite:
    def __init__(self):
        self.network_simulator = NetworkConditionSimulator()
        self.audio_corruptor = AudioCorruptionSimulator()
        
    async def test_network_jitter_recovery(self):
        """Test system recovery from network jitter."""
        # Simulate varying network conditions
        test_conditions = [
            {'latency_ms': 50, 'packet_loss_rate': 0.01},
            {'latency_ms': 200, 'packet_loss_rate': 0.05},
            {'latency_ms': 500, 'packet_loss_rate': 0.10},
        ]
        
        for condition in test_conditions:
            self.network_simulator.latency_ms = condition['latency_ms']
            self.network_simulator.packet_loss_rate = condition['packet_loss_rate']
            
            # Run test scenario
            success_rate = await self._run_audio_conversation_test()
            assert success_rate > 0.8, f"Success rate {success_rate} below threshold for condition {condition}"
            
    async def test_audio_corruption_handling(self):
        """Test system handling of corrupted audio data."""
        corruption_types = ['truncated', 'noise', 'malformed_base64', 'empty']
        
        for corruption_type in corruption_types:
            # Inject corrupted audio
            corrupted_audio = self.audio_corruptor.corrupt_audio_data(
                self._generate_test_audio(), corruption_type
            )
            
            # Verify system handles corruption gracefully
            result = await self._process_corrupted_audio(corrupted_audio)
            assert result['handled_gracefully'], f"Failed to handle {corruption_type} corruption"
            
    async def test_service_degradation(self):
        """Test system behavior during service degradation."""
        # Simulate OpenAI API slowdown
        with patch('openai.AsyncOpenAI') as mock_openai:
            mock_openai.side_effect = Exception("Service unavailable")
            
            # Verify fallback behavior
            result = await self._run_conversation_with_fallback()
            assert result['fallback_activated'], "Fallback not activated during service failure"
```

## Implementation Recommendations

### 1. Immediate Improvements

1. **Enhanced Base64 Validation**: Implement comprehensive validation in `AudioStreamHandler.handle_incoming_audio()`
2. **Retry Mechanisms**: Add exponential backoff for WebSocket operations
3. **Circuit Breakers**: Implement for OpenAI API calls
4. **Audio Recovery**: Add chunk timing recovery for network jitter

### 2. Monitoring and Alerting

1. **Error Rate Tracking**: Monitor error rates by type and severity
2. **Latency Monitoring**: Track audio processing and network latency
3. **Quality Metrics**: Monitor audio quality degradation
4. **Circuit Breaker Status**: Alert when circuit breakers open

### 3. Testing Strategy

1. **Unit Tests**: Test individual error handling components
2. **Integration Tests**: Test error scenarios in full system
3. **Load Tests**: Test system under various failure conditions
4. **Chaos Engineering**: Randomly inject failures in production-like environment

## Metrics and KPIs

### Error Handling Metrics
- Error rate by type (network, audio, service)
- Recovery time from failures
- Circuit breaker activation frequency
- Audio quality degradation frequency

### Resilience Metrics
- System availability during failures
- Audio conversation success rate
- Mean time to recovery (MTTR)
- Mean time between failures (MTBF)

## Conclusion

Implementing these error handling and resilience strategies will significantly improve the system's robustness in real-world conditions. The key is to start with the most critical paths (audio processing and network communication) and gradually expand coverage based on observed failure patterns. 