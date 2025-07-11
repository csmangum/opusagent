#!/usr/bin/env python3
"""
Resilience Testing Framework for FastAgent

This script provides comprehensive testing of error handling and resilience
capabilities, including network failures, audio corruption, and service degradation.
"""

import asyncio
import base64
import json
import logging
import random
import time
from typing import Dict, List, Any
from unittest.mock import patch, MagicMock

# Add the project root to the path
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from opusagent.resilience import (
    AudioDataValidator,
    AudioChunkRecovery,
    CircuitBreaker,
    AdaptiveQualityManager,
    ResilientWebSocketManager,
    ReliableMessageSender
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NetworkConditionSimulator:
    """Simulates various network conditions for testing."""
    
    def __init__(self):
        self.latency_ms = 0
        self.packet_loss_rate = 0.0
        self.bandwidth_limit = None
        self.connection_drops = False
        self.corruption_rate = 0.0
    
    async def simulate_network_conditions(self, websocket, message):
        """Simulate various network conditions."""
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
        
        # Simulate data corruption
        if self.corruption_rate > 0 and random.random() < self.corruption_rate:
            logger.info("Simulating data corruption")
            if isinstance(message, str):
                # Corrupt JSON message
                message = message[:-10] + "CORRUPTED"
            elif isinstance(message, bytes):
                # Corrupt binary data
                message = message[:-10] + b"CORRUPTED"
        
        return message


class AudioCorruptionSimulator:
    """Simulates various types of audio data corruption."""
    
    @staticmethod
    def corrupt_audio_data(audio_bytes: bytes, corruption_type: str) -> bytes:
        """Simulate various types of audio data corruption."""
        if corruption_type == 'truncated':
            return audio_bytes[:len(audio_bytes)//2]
        elif corruption_type == 'noise':
            noise = bytes(random.getrandbits(8) for _ in range(len(audio_bytes)//10))
            return audio_bytes + noise
        elif corruption_type == 'malformed_base64':
            corrupted = base64.b64encode(audio_bytes + b'invalid').decode('utf-8')
            return corrupted.encode('utf-8')
        elif corruption_type == 'empty':
            return b''
        elif corruption_type == 'null_bytes':
            return b'\x00' * len(audio_bytes)
        else:
            return audio_bytes


class ResilienceTestSuite:
    """Comprehensive resilience testing suite."""
    
    def __init__(self):
        self.network_simulator = NetworkConditionSimulator()
        self.audio_corruptor = AudioCorruptionSimulator()
        self.test_results = []
        
    async def test_audio_validation_resilience(self):
        """Test audio data validation with corrupted data."""
        logger.info("Testing audio validation resilience...")
        
        # Generate test audio data
        test_audio = b"\x00\x01\x02\x03" * 800  # 100ms at 16kHz
        
        test_cases = [
            ('valid', test_audio, True),
            ('truncated', self.audio_corruptor.corrupt_audio_data(test_audio, 'truncated'), False),
            ('noise', self.audio_corruptor.corrupt_audio_data(test_audio, 'noise'), False),
            ('empty', b'', False),
            ('null_bytes', b'\x00' * 3200, True),
        ]
        
        for test_name, audio_data, should_succeed in test_cases:
            try:
                # Encode to base64
                audio_b64 = base64.b64encode(audio_data).decode('utf-8')
                
                # Test validation
                result = AudioDataValidator.validate_and_decode_audio(audio_b64)
                
                success = len(result) > 0
                if success == should_succeed:
                    logger.info(f"✓ {test_name}: PASS")
                else:
                    logger.error(f"✗ {test_name}: FAIL (expected {should_succeed}, got {success})")
                
                self.test_results.append({
                    'test': f'audio_validation_{test_name}',
                    'success': success == should_succeed,
                    'expected': should_succeed,
                    'actual': success
                })
                
            except Exception as e:
                logger.error(f"✗ {test_name}: ERROR - {e}")
                self.test_results.append({
                    'test': f'audio_validation_{test_name}',
                    'success': False,
                    'error': str(e)
                })
    
    async def test_chunk_recovery_resilience(self):
        """Test audio chunk recovery with network jitter."""
        logger.info("Testing chunk recovery resilience...")
        
        recovery = AudioChunkRecovery(max_chunk_delay_ms=500)
        
        # Generate test chunks
        test_chunk = b"\x00\x01\x02\x03" * 400  # 50ms at 16kHz
        test_chunk_b64 = base64.b64encode(test_chunk).decode('utf-8')
        
        # Test normal timing
        result = await recovery.process_chunk_with_recovery(test_chunk_b64)
        assert result['processed'], "Normal chunk processing failed"
        
        # Test delayed chunk
        await asyncio.sleep(0.6)  # 600ms delay
        result = await recovery.process_chunk_with_recovery(test_chunk_b64)
        assert result['processed'], "Delayed chunk processing failed"
        assert result['recovery_applied'], "Recovery not applied for delayed chunk"
        
        # Test corrupted chunk
        corrupted_chunk = self.audio_corruptor.corrupt_audio_data(test_chunk, 'truncated')
        corrupted_b64 = base64.b64encode(corrupted_chunk).decode('utf-8')
        result = await recovery.process_chunk_with_recovery(corrupted_b64)
        assert result['processed'], "Corrupted chunk fallback failed"
        
        logger.info("✓ Chunk recovery resilience: PASS")
        self.test_results.append({
            'test': 'chunk_recovery_resilience',
            'success': True
        })
    
    async def test_circuit_breaker_resilience(self):
        """Test circuit breaker pattern with service failures."""
        logger.info("Testing circuit breaker resilience...")
        
        # Create circuit breaker
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
        
        # Mock failing service
        def failing_service():
            raise Exception("Service unavailable")
        
        def working_service():
            return "success"
        
        # Test normal operation
        try:
            result = await cb.call(working_service)
            assert result == "success", "Working service should succeed"
        except Exception as e:
            logger.error(f"Working service failed: {e}")
            self.test_results.append({
                'test': 'circuit_breaker_working',
                'success': False,
                'error': str(e)
            })
            return
        
        # Test circuit opening
        failure_count = 0
        for i in range(5):
            try:
                await cb.call(failing_service)
            except Exception:
                failure_count += 1
        
        # Circuit should be open after 3 failures
        assert cb.state.value == 'OPEN', f"Circuit should be open, got {cb.state.value}"
        
        # Test circuit recovery
        await asyncio.sleep(1.1)  # Wait for recovery timeout
        
        # Circuit should be half-open
        assert cb.state.value == 'HALF_OPEN', f"Circuit should be half-open, got {cb.state.value}"
        
        # Test successful recovery
        result = await cb.call(working_service)
        assert result == "success", "Service should recover"
        assert cb.state.value == 'CLOSED', "Circuit should close after recovery"
        
        logger.info("✓ Circuit breaker resilience: PASS")
        self.test_results.append({
            'test': 'circuit_breaker_resilience',
            'success': True
        })
    
    async def test_quality_management_resilience(self):
        """Test adaptive quality management."""
        logger.info("Testing quality management resilience...")
        
        qm = AdaptiveQualityManager(initial_quality='high')
        
        # Simulate poor performance
        for i in range(15):
            qm.record_error(300.0)  # High latency errors
        
        # Quality should degrade
        new_quality = qm.adjust_quality()
        assert new_quality == 'medium', f"Quality should degrade to medium, got {new_quality}"
        
        # Simulate good performance
        for i in range(20):
            qm.record_success(50.0)  # Low latency successes
        
        # Quality should improve
        new_quality = qm.adjust_quality()
        assert new_quality == 'high', f"Quality should improve to high, got {new_quality}"
        
        logger.info("✓ Quality management resilience: PASS")
        self.test_results.append({
            'test': 'quality_management_resilience',
            'success': True
        })
    
    async def test_websocket_resilience(self):
        """Test WebSocket connection resilience."""
        logger.info("Testing WebSocket resilience...")
        
        # Create mock WebSocket
        mock_websocket = MagicMock()
        mock_websocket.send = MagicMock()
        mock_websocket.recv = MagicMock()
        mock_websocket.close = MagicMock()
        mock_websocket.ping = MagicMock()
        
        # Test message sender
        sender = ReliableMessageSender(enable_acks=False)
        
        # Test successful send
        success = await sender.send_with_ack(mock_websocket, {"type": "test"})
        assert success, "Message send should succeed"
        
        # Test failed send
        mock_websocket.send.side_effect = Exception("Connection lost")
        success = await sender.send_with_ack(mock_websocket, {"type": "test"})
        assert not success, "Message send should fail"
        
        logger.info("✓ WebSocket resilience: PASS")
        self.test_results.append({
            'test': 'websocket_resilience',
            'success': True
        })
    
    async def test_integrated_resilience(self):
        """Test integrated resilience scenarios."""
        logger.info("Testing integrated resilience scenarios...")
        
        # Create components
        audio_validator = AudioDataValidator()
        chunk_recovery = AudioChunkRecovery()
        circuit_breaker = CircuitBreaker(failure_threshold=2)
        quality_manager = AdaptiveQualityManager()
        
        # Simulate real-world scenario: network issues + audio corruption
        test_audio = b"\x00\x01\x02\x03" * 800
        
        # Test 1: Corrupted audio with recovery
        corrupted_audio = self.audio_corruptor.corrupt_audio_data(test_audio, 'truncated')
        audio_b64 = base64.b64encode(corrupted_audio).decode('utf-8')
        
        result = await chunk_recovery.process_chunk_with_recovery(audio_b64)
        assert result['processed'], "Integrated recovery should handle corrupted audio"
        
        # Test 2: Service degradation with circuit breaker
        def degraded_service():
            if random.random() < 0.7:  # 70% failure rate
                raise Exception("Service degraded")
            return "success"
        
        success_count = 0
        for i in range(10):
            try:
                await circuit_breaker.call(degraded_service)
                success_count += 1
            except Exception:
                pass
        
        # Circuit should open due to high failure rate
        assert circuit_breaker.state.value == 'OPEN', "Circuit should open under degradation"
        
        logger.info("✓ Integrated resilience: PASS")
        self.test_results.append({
            'test': 'integrated_resilience',
            'success': True
        })
    
    async def run_all_tests(self):
        """Run all resilience tests."""
        logger.info("Starting comprehensive resilience testing...")
        
        test_methods = [
            self.test_audio_validation_resilience,
            self.test_chunk_recovery_resilience,
            self.test_circuit_breaker_resilience,
            self.test_quality_management_resilience,
            self.test_websocket_resilience,
            self.test_integrated_resilience
        ]
        
        for test_method in test_methods:
            try:
                await test_method()
            except Exception as e:
                logger.error(f"Test {test_method.__name__} failed: {e}")
                self.test_results.append({
                    'test': test_method.__name__,
                    'success': False,
                    'error': str(e)
                })
        
        self.print_results()
    
    def print_results(self):
        """Print test results summary."""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result.get('success', False))
        failed_tests = total_tests - passed_tests
        
        logger.info("\n" + "="*60)
        logger.info("RESILIENCE TEST RESULTS")
        logger.info("="*60)
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {failed_tests}")
        logger.info(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            logger.info("\nFailed Tests:")
            for result in self.test_results:
                if not result.get('success', False):
                    logger.error(f"  - {result['test']}: {result.get('error', 'Unknown error')}")
        
        logger.info("="*60)


async def main():
    """Main test runner."""
    test_suite = ResilienceTestSuite()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main()) 