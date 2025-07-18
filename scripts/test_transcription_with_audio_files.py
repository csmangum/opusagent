#!/usr/bin/env python3
"""
Comprehensive Transcription Test with Audio Files

This script tests the transcription capabilities of the LocalRealtimeClient
using actual audio files from the mock audio directory. It provides detailed
evidence of transcription quality and acceptability for both PocketSphinx
and Whisper backends.

Features:
- Tests both PocketSphinx and Whisper backends
- Uses real audio files from different categories
- Provides detailed transcription results with confidence scores
- Shows processing times and performance metrics
- Generates a comprehensive report

Usage:
    python scripts/test_transcription_with_audio_files.py
"""

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from opusagent.local.realtime import (
    LocalRealtimeClient,
    TranscriptionConfig,
    TranscriptionFactory,
    load_transcription_config
)
from opusagent.mock.transcription import TranscriptionResult


class TranscriptionTester:
    """Comprehensive transcription testing with audio files."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.results: Dict[str, Dict] = {}
        self.audio_files: List[Path] = []
        self.test_categories = [
            "greetings", "farewells", "customer_service", 
            "technical_support", "sales", "confirmations"
        ]
        
    def discover_audio_files(self) -> None:
        """Discover all available audio files for testing."""
        mock_audio_dir = project_root / "opusagent" / "mock" / "audio"
        
        if not mock_audio_dir.exists():
            self.logger.error(f"Mock audio directory not found: {mock_audio_dir}")
            return
        
        for category in self.test_categories:
            category_dir = mock_audio_dir / category
            if category_dir.exists():
                wav_files = list(category_dir.glob("*.wav"))
                self.audio_files.extend(wav_files)
                self.logger.info(f"Found {len(wav_files)} audio files in {category}")
        
        self.logger.info(f"Total audio files discovered: {len(self.audio_files)}")
    
    async def test_transcriber_backend(
        self, 
        backend: str, 
        audio_file: Path,
        config: TranscriptionConfig
    ) -> Dict:
        """Test a specific transcriber backend with an audio file."""
        self.logger.info(f"Testing {backend} with {audio_file.name}")
        
        # Create transcriber
        transcriber = TranscriptionFactory.create_transcriber(config)
        
        # Initialize
        start_time = time.time()
        init_success = await transcriber.initialize()
        init_time = time.time() - start_time
        
        if not init_success:
            return {
                "backend": backend,
                "audio_file": audio_file.name,
                "category": audio_file.parent.name,
                "success": False,
                "error": "Failed to initialize transcriber",
                "init_time": init_time
            }
        
        # Load audio file
        try:
            with open(audio_file, 'rb') as f:
                audio_data = f.read()
            
            # Skip WAV header (44 bytes) to get raw PCM data
            if len(audio_data) > 44:
                # Check if it's a WAV file and extract PCM data
                if audio_data[:4] == b'RIFF' and audio_data[8:12] == b'WAVE':
                    # Find data chunk
                    data_start = 44  # Standard WAV header size
                    audio_data = audio_data[data_start:]
                # If not WAV, use as-is (assuming it's already PCM)
            
        except Exception as e:
            return {
                "backend": backend,
                "audio_file": audio_file.name,
                "category": audio_file.parent.name,
                "success": False,
                "error": f"Failed to load audio file: {e}",
                "init_time": init_time
            }
        
        # Start transcription session
        transcriber.start_session()
        
        # Process audio in chunks
        chunk_size = 3200  # 200ms at 16kHz 16-bit
        chunks = [audio_data[i:i + chunk_size] for i in range(0, len(audio_data), chunk_size)]
        
        transcription_start = time.time()
        accumulated_text = ""
        delta_results = []
        
        for i, chunk in enumerate(chunks):
            chunk_start = time.time()
            result = await transcriber.transcribe_chunk(chunk)
            chunk_time = time.time() - chunk_start
            
            if result.error:
                await transcriber.cleanup()
                return {
                    "backend": backend,
                    "audio_file": audio_file.name,
                    "category": audio_file.parent.name,
                    "success": False,
                    "error": f"Transcription error at chunk {i}: {result.error}",
                    "init_time": init_time,
                    "chunks_processed": i
                }
            
            if result.text:
                accumulated_text += result.text
                delta_results.append({
                    "chunk": i,
                    "delta_text": result.text,
                    "confidence": result.confidence,
                    "processing_time": chunk_time
                })
        
        # Finalize transcription
        final_start = time.time()
        final_result = await transcriber.finalize()
        final_time = time.time() - final_start
        
        total_time = time.time() - transcription_start
        
        # Reset session for next file (don't cleanup until all files are done)
        transcriber.reset_session()
        
        # Use final result if available, otherwise use accumulated text
        final_text = final_result.text if final_result.text else accumulated_text
        
        return {
            "backend": backend,
            "audio_file": audio_file.name,
            "category": audio_file.parent.name,
            "success": True,
            "init_time": init_time,
            "total_time": total_time,
            "final_time": final_time,
            "chunks_processed": len(chunks),
            "final_text": final_text,
            "accumulated_text": accumulated_text,
            "final_confidence": final_result.confidence,
            "delta_results": delta_results,
            "audio_size_bytes": len(audio_data),
            "audio_duration_estimated": len(audio_data) / (16000 * 2),  # 16kHz, 16-bit
            "processing_rate": len(audio_data) / total_time if total_time > 0 else 0
        }
    
    async def test_transcriber_backend_with_instance(
        self, 
        backend: str, 
        audio_file: Path,
        transcriber
    ) -> Dict:
        """Test a specific transcriber backend with an existing instance."""
        self.logger.info(f"Testing {backend} with {audio_file.name}")
        
        # Load audio file
        try:
            with open(audio_file, 'rb') as f:
                audio_data = f.read()
            
            # Skip WAV header (44 bytes) to get raw PCM data
            if len(audio_data) > 44:
                # Check if it's a WAV file and extract PCM data
                if audio_data[:4] == b'RIFF' and audio_data[8:12] == b'WAVE':
                    # Find data chunk
                    data_start = 44  # Standard WAV header size
                    audio_data = audio_data[data_start:]
                # If not WAV, use as-is (assuming it's already PCM)
            
        except Exception as e:
            return {
                "backend": backend,
                "audio_file": audio_file.name,
                "category": audio_file.parent.name,
                "success": False,
                "error": f"Failed to load audio file: {e}",
                "init_time": 0.0
            }
        
        # Start transcription session
        transcriber.start_session()
        
        # Process audio in chunks
        chunk_size = 3200  # 200ms at 16kHz 16-bit
        chunks = [audio_data[i:i + chunk_size] for i in range(0, len(audio_data), chunk_size)]
        
        transcription_start = time.time()
        accumulated_text = ""
        delta_results = []
        
        for i, chunk in enumerate(chunks):
            chunk_start = time.time()
            result = await transcriber.transcribe_chunk(chunk)
            chunk_time = time.time() - chunk_start
            
            if result.error:
                return {
                    "backend": backend,
                    "audio_file": audio_file.name,
                    "category": audio_file.parent.name,
                    "success": False,
                    "error": f"Transcription error at chunk {i}: {result.error}",
                    "init_time": 0.0,
                    "chunks_processed": i
                }
            
            if result.text:
                accumulated_text += result.text
                delta_results.append({
                    "chunk": i,
                    "delta_text": result.text,
                    "confidence": result.confidence,
                    "processing_time": chunk_time
                })
        
        # Finalize transcription
        final_start = time.time()
        final_result = await transcriber.finalize()
        final_time = time.time() - final_start
        
        total_time = time.time() - transcription_start
        
        # Reset session for next file (don't cleanup)
        transcriber.reset_session()
        
        # Use final result if available, otherwise use accumulated text
        final_text = final_result.text if final_result.text else accumulated_text
        
        return {
            "backend": backend,
            "audio_file": audio_file.name,
            "category": audio_file.parent.name,
            "success": True,
            "init_time": 0.0,  # Already initialized
            "total_time": total_time,
            "final_time": final_time,
            "chunks_processed": len(chunks),
            "final_text": final_text,
            "accumulated_text": accumulated_text,
            "final_confidence": final_result.confidence,
            "delta_results": delta_results,
            "audio_size_bytes": len(audio_data),
            "audio_duration_estimated": len(audio_data) / (16000 * 2),  # 16kHz, 16-bit
            "processing_rate": len(audio_data) / total_time if total_time > 0 else 0
        }
    
    async def run_comprehensive_test(self) -> Dict:
        """Run comprehensive transcription tests on all backends and audio files."""
        self.logger.info("Starting comprehensive transcription test")
        
        # Discover audio files
        self.discover_audio_files()
        
        if not self.audio_files:
            self.logger.error("No audio files found for testing")
            return {"error": "No audio files found"}
        
        # Test configurations
        test_configs = [
            ("pocketsphinx", TranscriptionConfig(backend="pocketsphinx")),
            ("whisper_base", TranscriptionConfig(backend="whisper", model_size="base")),
            ("whisper_small", TranscriptionConfig(backend="whisper", model_size="small")),
        ]
        
        all_results = []
        
        # Test each backend with a subset of audio files (for performance)
        test_files = self.audio_files[:10]  # Test with first 10 files
        
        for backend_name, config in test_configs:
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"Testing backend: {backend_name}")
            self.logger.info(f"{'='*60}")
            
            # Create a single transcriber instance for this backend
            transcriber = TranscriptionFactory.create_transcriber(config)
            
            # Initialize once
            init_success = await transcriber.initialize()
            if not init_success:
                self.logger.error(f"Failed to initialize {backend_name}, skipping all files")
                continue
            
            backend_results = []
            
            for audio_file in test_files:
                try:
                    result = await self.test_transcriber_backend_with_instance(backend_name, audio_file, transcriber)
                    backend_results.append(result)
                    
                    if result["success"]:
                        self.logger.info(f"✓ {audio_file.name}: '{result['final_text'][:50]}...'")
                    else:
                        self.logger.error(f"✗ {audio_file.name}: {result['error']}")
                        
                except Exception as e:
                    error_result = {
                        "backend": backend_name,
                        "audio_file": audio_file.name,
                        "category": audio_file.parent.name,
                        "success": False,
                        "error": f"Exception during testing: {e}"
                    }
                    backend_results.append(error_result)
                    self.logger.error(f"✗ {audio_file.name}: Exception - {e}")
            
            # Clean up transcriber after all files are processed
            await transcriber.cleanup()
            
            all_results.extend(backend_results)
            
            # Summary for this backend
            successful = [r for r in backend_results if r["success"]]
            failed = [r for r in backend_results if not r["success"]]
            
            self.logger.info(f"\nBackend {backend_name} Summary:")
            self.logger.info(f"  Successful: {len(successful)}/{len(backend_results)}")
            self.logger.info(f"  Failed: {len(failed)}/{len(backend_results)}")
            
            if successful:
                avg_time = sum(r["total_time"] for r in successful) / len(successful)
                avg_confidence = sum(r["final_confidence"] for r in successful) / len(successful)
                self.logger.info(f"  Average processing time: {avg_time:.3f}s")
                self.logger.info(f"  Average confidence: {avg_confidence:.3f}")
        
        return {
            "test_summary": {
                "total_files_tested": len(test_files),
                "total_results": len(all_results),
                "backends_tested": [config[0] for config in test_configs]
            },
            "results": all_results
        }
    
    def generate_detailed_report(self, test_results: Dict) -> str:
        """Generate a detailed report of transcription test results."""
        if "error" in test_results:
            return f"Test failed: {test_results['error']}"
        
        results = test_results["results"]
        summary = test_results["test_summary"]
        
        report = []
        report.append("=" * 80)
        report.append("TRANSCRIPTION TEST REPORT")
        report.append("=" * 80)
        report.append(f"Total files tested: {summary['total_files_tested']}")
        report.append(f"Backends tested: {', '.join(summary['backends_tested'])}")
        report.append("")
        
        # Group results by backend
        by_backend = {}
        for result in results:
            backend = result["backend"]
            if backend not in by_backend:
                by_backend[backend] = []
            by_backend[backend].append(result)
        
        for backend, backend_results in by_backend.items():
            report.append(f"{'='*60}")
            report.append(f"BACKEND: {backend.upper()}")
            report.append(f"{'='*60}")
            
            successful = [r for r in backend_results if r["success"]]
            failed = [r for r in backend_results if not r["success"]]
            
            report.append(f"Success Rate: {len(successful)}/{len(backend_results)} ({len(successful)/len(backend_results)*100:.1f}%)")
            report.append("")
            
            if successful:
                # Performance metrics
                avg_init_time = sum(r["init_time"] for r in successful) / len(successful)
                avg_total_time = sum(r["total_time"] for r in successful) / len(successful)
                avg_confidence = sum(r["final_confidence"] for r in successful) / len(successful)
                
                report.append("PERFORMANCE METRICS:")
                report.append(f"  Average initialization time: {avg_init_time:.3f}s")
                report.append(f"  Average processing time: {avg_total_time:.3f}s")
                report.append(f"  Average confidence score: {avg_confidence:.3f}")
                report.append("")
            
            # Detailed results
            report.append("DETAILED RESULTS:")
            for result in backend_results:
                status = "✓" if result["success"] else "✗"
                report.append(f"  {status} {result['audio_file']} ({result['category']})")
                
                if result["success"]:
                    text_preview = result["final_text"][:60] + "..." if len(result["final_text"]) > 60 else result["final_text"]
                    report.append(f"      Text: '{text_preview}'")
                    report.append(f"      Confidence: {result['final_confidence']:.3f}")
                    report.append(f"      Time: {result['total_time']:.3f}s")
                else:
                    report.append(f"      Error: {result['error']}")
                report.append("")
            
            if failed:
                report.append("FAILURES:")
                for result in failed:
                    report.append(f"  {result['audio_file']}: {result['error']}")
                report.append("")
        
        # Overall assessment
        report.append("=" * 80)
        report.append("OVERALL ASSESSMENT")
        report.append("=" * 80)
        
        total_successful = len([r for r in results if r["success"]])
        total_failed = len([r for r in results if r["success"] == False])
        
        report.append(f"Overall Success Rate: {total_successful}/{len(results)} ({total_successful/len(results)*100:.1f}%)")
        
        if total_successful > 0:
            # Quality assessment
            successful_results = [r for r in results if r["success"]]
            avg_confidence = sum(r["final_confidence"] for r in successful_results) / len(successful_results)
            
            if avg_confidence > 0.8:
                quality = "EXCELLENT"
            elif avg_confidence > 0.6:
                quality = "GOOD"
            elif avg_confidence > 0.4:
                quality = "ACCEPTABLE"
            else:
                quality = "POOR"
            
            report.append(f"Average Confidence: {avg_confidence:.3f} ({quality})")
            
            # Backend comparison
            report.append("\nBACKEND COMPARISON:")
            for backend in by_backend.keys():
                backend_results = [r for r in results if r["backend"] == backend and r["success"]]
                if backend_results:
                    avg_conf = sum(r["final_confidence"] for r in backend_results) / len(backend_results)
                    avg_time = sum(r["total_time"] for r in backend_results) / len(backend_results)
                    report.append(f"  {backend}: Confidence={avg_conf:.3f}, Time={avg_time:.3f}s")
        
        return "\n".join(report)
    
    def save_results(self, test_results: Dict, output_file: str = "transcription_test_results.json") -> None:
        """Save test results to a JSON file."""
        try:
            with open(output_file, 'w') as f:
                json.dump(test_results, f, indent=2, default=str)
            self.logger.info(f"Results saved to {output_file}")
        except Exception as e:
            self.logger.error(f"Failed to save results: {e}")


async def main():
    """Main function to run the transcription test."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    logger.info("Starting Transcription Test with Audio Files")
    logger.info("=" * 60)
    
    # Create tester
    tester = TranscriptionTester(logger)
    
    try:
        # Run comprehensive test
        test_results = await tester.run_comprehensive_test()
        
        # Generate and display report
        report = tester.generate_detailed_report(test_results)
        print("\n" + report)
        
        # Save results
        tester.save_results(test_results)
        
        # Save report to file
        with open("transcription_test_report.txt", "w") as f:
            f.write(report)
        logger.info("Detailed report saved to transcription_test_report.txt")
        
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 