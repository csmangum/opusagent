#!/usr/bin/env python3
"""
Resilience Features Demonstration

This script demonstrates the enhanced error handling and resilience features
of the FastAgent system, showing how it handles various failure scenarios.
"""

import asyncio
import base64
import logging
import random
import time
from typing import Dict, Any

# Add the project root to the path
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from opusagent.resilience import (
    AudioDataValidator,
    AudioChunkRecovery,
    CircuitBreaker,
    AdaptiveQualityManager
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ResilienceDemo:
    """Demonstrates resilience features with various failure scenarios."""
    
    def __init__(self):
        self.demo_results = []
    
    async def demo_audio_validation(self):
        """Demonstrate audio validation with corrupted data."""
        logger.info("\n" + "="*60)
        logger.info("DEMO: Audio Validation Resilience")
        logger.info("="*60)
        
        # Generate test audio
        test_audio = b"\x00\x01\x02\x03" * 800  # 100ms at 16kHz
        
        test_cases = [
            ("Valid Audio", test_audio, "Normal audio data"),
            ("Truncated Audio", test_audio[:len(test_audio)//2], "Audio cut in half"),
            ("Empty Audio", b"", "No audio data"),
            ("Corrupted Base64", "invalid_base64_data!", "Malformed base64"),
            ("Null Audio", b"\x00" * 3200, "Silence"),
        ]
        
        for test_name, audio_data, description in test_cases:
            logger.info(f"\nTesting: {test_name}")
            logger.info(f"Description: {description}")
            
            try:
                if isinstance(audio_data, bytes):
                    audio_b64 = base64.b64encode(audio_data).decode('utf-8')
                else:
                    audio_b64 = audio_data
                
                # Test validation
                result = AudioDataValidator.validate_and_decode_audio(audio_b64)
                
                success = len(result) > 0
                logger.info(f"Result: {'✓ SUCCESS' if success else '✗ FAILED'}")
                logger.info(f"Output size: {len(result)} bytes")
                
                if success:
                    # Analyze quality
                    quality = AudioDataValidator.validate_audio_quality(result)
                    logger.info(f"Quality: {quality['issues'] if quality['issues'] else 'Good'}")
                
            except Exception as e:
                logger.error(f"Error: {e}")
    
    async def demo_chunk_recovery(self):
        """Demonstrate audio chunk recovery with network jitter."""
        logger.info("\n" + "="*60)
        logger.info("DEMO: Audio Chunk Recovery")
        logger.info("="*60)
        
        recovery = AudioChunkRecovery(max_chunk_delay_ms=500)
        
        # Generate test chunks
        test_chunk = b"\x00\x01\x02\x03" * 400  # 50ms at 16kHz
        test_chunk_b64 = base64.b64encode(test_chunk).decode('utf-8')
        
        scenarios = [
            ("Normal Timing", 0.1, "Regular 100ms intervals"),
            ("Network Jitter", 0.6, "600ms delay (should trigger recovery)"),
            ("Very Fast", 0.05, "50ms intervals (too fast)"),
            ("Corrupted Chunk", 0.1, "Malformed audio data"),
        ]
        
        for scenario_name, delay, description in scenarios:
            logger.info(f"\nScenario: {scenario_name}")
            logger.info(f"Description: {description}")
            
            if scenario_name == "Corrupted Chunk":
                # Corrupt the audio data
                corrupted_chunk = test_chunk[:len(test_chunk)//2]
                chunk_b64 = base64.b64encode(corrupted_chunk).decode('utf-8')
            else:
                chunk_b64 = test_chunk_b64
            
            # Simulate delay
            if delay > 0:
                await asyncio.sleep(delay)
            
            # Process chunk
            result = await recovery.process_chunk_with_recovery(chunk_b64)
            
            logger.info(f"Processed: {'✓' if result['processed'] else '✗'}")
            logger.info(f"Recovery Applied: {'✓' if result['recovery_applied'] else '✗'}")
            if result['recovery_applied']:
                logger.info(f"Recovery Type: {result.get('recovery_type', 'unknown')}")
                logger.info(f"Silence Inserted: {result['silence_inserted']} bytes")
        
        # Show statistics
        stats = recovery.get_recovery_statistics()
        logger.info(f"\nRecovery Statistics:")
        logger.info(f"Total chunks: {stats['total_chunks']}")
        logger.info(f"Chunks with delay: {stats['chunks_with_delay']}")
        logger.info(f"Silence insertions: {stats['silence_insertions']}")
        logger.info(f"Recovery rate: {stats['recovery_rate']:.2%}")
    
    async def demo_circuit_breaker(self):
        """Demonstrate circuit breaker pattern."""
        logger.info("\n" + "="*60)
        logger.info("DEMO: Circuit Breaker Pattern")
        logger.info("="*60)
        
        # Create circuit breaker
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=2.0)
        
        # Mock services
        def reliable_service():
            return "success"
        
        def unreliable_service():
            if random.random() < 0.8:  # 80% failure rate
                raise Exception("Service temporarily unavailable")
            return "success"
        
        def recovering_service():
            # Simulate service that recovers after failures
            if hasattr(recovering_service, 'failure_count'):
                recovering_service.failure_count += 1
            else:
                recovering_service.failure_count = 1
            
            if recovering_service.failure_count <= 5:
                raise Exception("Service down")
            else:
                return "recovered"
        
        # Test 1: Reliable service
        logger.info("\nTest 1: Reliable Service")
        for i in range(5):
            try:
                result = await cb.call(reliable_service)
                logger.info(f"Call {i+1}: ✓ {result}")
            except Exception as e:
                logger.error(f"Call {i+1}: ✗ {e}")
        
        # Test 2: Unreliable service
        logger.info("\nTest 2: Unreliable Service")
        for i in range(8):
            try:
                result = await cb.call(unreliable_service)
                logger.info(f"Call {i+1}: ✓ {result}")
            except Exception as e:
                logger.info(f"Call {i+1}: ✗ {e}")
            
            # Show circuit state
            logger.info(f"Circuit state: {cb.state.value}")
            
            if cb.state.value == 'OPEN':
                logger.info("Circuit is OPEN - requests are being rejected")
                break
        
        # Test 3: Service recovery
        logger.info("\nTest 3: Service Recovery")
        await asyncio.sleep(2.1)  # Wait for recovery timeout
        
        try:
            result = await cb.call(recovering_service)
            logger.info(f"Recovery test: ✓ {result}")
            logger.info(f"Circuit state: {cb.state.value}")
        except Exception as e:
            logger.error(f"Recovery test: ✗ {e}")
        
        # Show statistics
        stats = cb.get_statistics()
        logger.info(f"\nCircuit Breaker Statistics:")
        logger.info(f"Total requests: {stats['total_requests']}")
        logger.info(f"Success rate: {stats['success_rate']:.2%}")
        logger.info(f"Circuit opens: {stats['circuit_opens']}")
        logger.info(f"Circuit closes: {stats['circuit_closes']}")
    
    async def demo_quality_management(self):
        """Demonstrate adaptive quality management."""
        logger.info("\n" + "="*60)
        logger.info("DEMO: Adaptive Quality Management")
        logger.info("="*60)
        
        qm = AdaptiveQualityManager(initial_quality='high')
        
        # Show initial state
        logger.info(f"Initial quality: {qm.current_quality}")
        
        # Simulate poor network conditions
        logger.info("\nSimulating poor network conditions...")
        for i in range(20):
            qm.record_error(250.0)  # High latency errors
            if i % 5 == 4:
                logger.info(f"After {i+1} errors: {qm.current_quality} quality")
                await asyncio.sleep(11)  # Wait for min interval
                # Check for quality adjustment after each batch
                new_quality = qm.adjust_quality()
                if new_quality:
                    logger.info(f"Quality degraded to: {new_quality}")
                    break  # Stop if quality degraded
        
        # Simulate network improvement
        logger.info("\nSimulating network improvement...")
        for i in range(25):
            qm.record_success(50.0)  # Low latency successes
            if i % 5 == 4:
                logger.info(f"After {i+1} successes: {qm.current_quality} quality")
                await asyncio.sleep(11)  # Wait for min interval
                # Check for quality improvement after each batch
                new_quality = qm.adjust_quality()
                if new_quality:
                    logger.info(f"Quality improved to: {new_quality}")
                    break  # Stop if quality improved
        
        # Show statistics
        stats = qm.get_statistics()
        logger.info(f"\nQuality Management Statistics:")
        logger.info(f"Current quality: {stats['current_quality']}")
        logger.info(f"Total requests: {stats['total_requests']}")
        logger.info(f"Error rate: {stats['error_rate']:.2%}")
        logger.info(f"Quality downgrades: {stats['quality_downgrades']}")
        logger.info(f"Quality upgrades: {stats['quality_upgrades']}")
        logger.info(f"Quality changes: {stats['quality_changes']}")
    
    async def demo_integrated_scenario(self):
        """Demonstrate integrated resilience scenario."""
        logger.info("\n" + "="*60)
        logger.info("DEMO: Integrated Resilience Scenario")
        logger.info("="*60)
        
        logger.info("Simulating real-world scenario with multiple failure types...")
        
        # Create components
        audio_validator = AudioDataValidator()
        chunk_recovery = AudioChunkRecovery()
        circuit_breaker = CircuitBreaker(failure_threshold=2)
        quality_manager = AdaptiveQualityManager()
        
        # Scenario: Network issues + audio corruption + service degradation
        test_audio = b"\x00\x01\x02\x03" * 800
        
        # Phase 1: Normal operation
        logger.info("\nPhase 1: Normal Operation")
        for i in range(5):
            audio_b64 = base64.b64encode(test_audio).decode('utf-8')
            result = await chunk_recovery.process_chunk_with_recovery(audio_b64)
            quality_manager.record_success(50.0)
            logger.info(f"Chunk {i+1}: Normal processing")
        
        # Phase 2: Network jitter
        logger.info("\nPhase 2: Network Jitter")
        for i in range(3):
            await asyncio.sleep(0.6)  # Simulate delay
            audio_b64 = base64.b64encode(test_audio).decode('utf-8')
            result = await chunk_recovery.process_chunk_with_recovery(audio_b64)
            quality_manager.record_error(200.0)
            logger.info(f"Chunk {i+1}: Network jitter detected")
        
        # Phase 3: Audio corruption
        logger.info("\nPhase 3: Audio Corruption")
        for i in range(3):
            corrupted_audio = test_audio[:len(test_audio)//2]  # Truncated
            audio_b64 = base64.b64encode(corrupted_audio).decode('utf-8')
            result = await chunk_recovery.process_chunk_with_recovery(audio_b64)
            quality_manager.record_error(150.0)
            logger.info(f"Chunk {i+1}: Corrupted audio handled")
        
        # Phase 4: Service degradation
        logger.info("\nPhase 4: Service Degradation")
        def degraded_service():
            if random.random() < 0.7:
                raise Exception("Service degraded")
            return "success"
        
        for i in range(5):
            try:
                await circuit_breaker.call(degraded_service)
                logger.info(f"Service call {i+1}: Success")
            except Exception as e:
                logger.info(f"Service call {i+1}: Failed - {e}")
        
        # Phase 5: Recovery
        logger.info("\nPhase 5: Recovery")
        await asyncio.sleep(2.1)  # Wait for circuit breaker recovery
        
        for i in range(3):
            audio_b64 = base64.b64encode(test_audio).decode('utf-8')
            result = await chunk_recovery.process_chunk_with_recovery(audio_b64)
            quality_manager.record_success(60.0)
            logger.info(f"Chunk {i+1}: Recovery processing")
        
        # Show final statistics
        logger.info("\nFinal Statistics:")
        logger.info(f"Chunk Recovery: {chunk_recovery.get_recovery_statistics()}")
        logger.info(f"Circuit Breaker: {circuit_breaker.get_statistics()}")
        logger.info(f"Quality Management: {quality_manager.get_statistics()}")
    
    async def run_all_demos(self):
        """Run all demonstration scenarios."""
        logger.info("Starting Resilience Features Demonstration")
        logger.info("This demo shows how the system handles various failure scenarios")
        
        demos = [
            self.demo_audio_validation,
            self.demo_chunk_recovery,
            self.demo_circuit_breaker,
            self.demo_quality_management,
            self.demo_integrated_scenario
        ]
        
        for demo in demos:
            try:
                await demo()
                await asyncio.sleep(1)  # Brief pause between demos
            except Exception as e:
                logger.error(f"Demo {demo.__name__} failed: {e}")
        
        logger.info("\n" + "="*60)
        logger.info("DEMONSTRATION COMPLETE")
        logger.info("="*60)
        logger.info("The resilience features provide:")
        logger.info("✓ Robust error handling for audio processing")
        logger.info("✓ Network jitter recovery and timing compensation")
        logger.info("✓ Circuit breaker protection for external services")
        logger.info("✓ Adaptive quality management based on performance")
        logger.info("✓ Comprehensive monitoring and statistics")


async def main():
    """Main demonstration runner."""
    demo = ResilienceDemo()
    await demo.run_all_demos()


if __name__ == "__main__":
    asyncio.run(main()) 