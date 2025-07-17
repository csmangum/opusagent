#!/usr/bin/env python3
"""
Transcription Validation Script with Whisper

This script validates the transcription model using Whisper backend by processing audio files 
from the mock audio directory and comparing the results with expected phrases from the phrases_mapping.yml file.

Usage:
    python scripts/validate_transcription_with_whisper.py
"""

import asyncio
import logging
import os
import sys
import yaml
from pathlib import Path
from typing import Dict, List, Tuple

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from opusagent.mock.transcription import TranscriptionFactory, TranscriptionConfig
from opusagent.config.logging_config import configure_logging


class WhisperTranscriptionValidator:
    """Validates transcription model with Whisper backend."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.audio_dir = project_root / "opusagent" / "mock" / "audio"
        self.phrases_mapping_file = self.audio_dir / "phrases_mapping.yml"
        self.results = []
        
    def load_phrases_mapping(self) -> Dict:
        """Load the phrases mapping from YAML file."""
        try:
            with open(self.phrases_mapping_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Failed to load phrases mapping: {e}")
            return {}
    
    def select_test_files(self, phrases_mapping: Dict) -> List[Tuple[str, str, str]]:
        """Select a diverse set of audio files for testing."""
        test_files = []
        
        # Select files from different categories
        categories = ['greetings', 'customer_service', 'errors', 'confirmations']
        
        for category in categories:
            if category in phrases_mapping.get('scenarios', {}):
                scenario = phrases_mapping['scenarios'][category]
                phrases = scenario.get('phrases', [])
                
                # Select first and last phrase from each category
                if phrases:
                    # First phrase
                    first_phrase = phrases[0]
                    file_path = self.audio_dir / category / first_phrase['file']
                    if file_path.exists():
                        test_files.append((
                            str(file_path),
                            first_phrase['phrase'],
                            category
                        ))
                    
                    # Last phrase (if different from first)
                    if len(phrases) > 1:
                        last_phrase = phrases[-1]
                        file_path = self.audio_dir / category / last_phrase['file']
                        if file_path.exists():
                            test_files.append((
                                str(file_path),
                                last_phrase['phrase'],
                                category
                            ))
        
        return test_files
    
    def create_whisper_config(self) -> TranscriptionConfig:
        """Create a Whisper-specific transcription configuration."""
        return TranscriptionConfig(
            backend="whisper",
            language="en",
            model_size="base",  # Use base model for faster processing
            chunk_duration=2.0,  # Longer chunks for Whisper
            confidence_threshold=0.5,
            sample_rate=16000,
            enable_vad=False,  # Disable VAD for file processing
            device="cpu",
            whisper_temperature=0.0  # Deterministic output
        )
    
    async def test_transcription(self, audio_file: str, expected_text: str, category: str) -> Dict:
        """Test transcription on a single audio file using Whisper."""
        try:
            # Create Whisper configuration
            config = self.create_whisper_config()
            self.logger.info(f"Testing with backend: {config.backend}, model: {config.model_size}")
            
            # Create transcriber
            transcriber = TranscriptionFactory.create_transcriber(config)
            
            # Initialize transcriber
            if not await transcriber.initialize():
                return {
                    'file': audio_file,
                    'category': category,
                    'expected': expected_text,
                    'result': '',
                    'confidence': 0.0,
                    'error': 'Failed to initialize transcriber',
                    'success': False
                }
            
            # Read audio file
            with open(audio_file, 'rb') as f:
                audio_data = f.read()
            
            # Start transcription session
            transcriber.start_session()
            
            # Process audio in chunks
            chunk_size = 6400  # 400ms at 16kHz 16-bit (larger chunks for Whisper)
            accumulated_text = ""
            
            for i in range(0, len(audio_data), chunk_size):
                chunk = audio_data[i:i + chunk_size]
                result = await transcriber.transcribe_chunk(chunk)
                
                if result.error:
                    self.logger.warning(f"Chunk transcription error: {result.error}")
                
                if result.text:
                    accumulated_text += result.text
            
            # Finalize transcription
            final_result = await transcriber.finalize()
            
            # Use final result or accumulated text
            transcribed_text = final_result.text if final_result.text else accumulated_text
            
            # Clean up
            await transcriber.cleanup()
            
            # Calculate similarity (simple word overlap)
            similarity = self.calculate_similarity(transcribed_text, expected_text)
            
            return {
                'file': audio_file,
                'category': category,
                'expected': expected_text,
                'result': transcribed_text,
                'confidence': final_result.confidence,
                'similarity': similarity,
                'error': None,
                'success': True
            }
            
        except Exception as e:
            self.logger.error(f"Error testing transcription for {audio_file}: {e}")
            return {
                'file': audio_file,
                'category': category,
                'expected': expected_text,
                'result': '',
                'confidence': 0.0,
                'error': str(e),
                'success': False
            }
    
    def calculate_similarity(self, transcribed: str, expected: str) -> float:
        """Calculate similarity between transcribed and expected text."""
        if not transcribed or not expected:
            return 0.0
        
        # Convert to lowercase and split into words
        transcribed_words = set(transcribed.lower().split())
        expected_words = set(expected.lower().split())
        
        if not expected_words:
            return 0.0
        
        # Calculate word overlap
        intersection = transcribed_words & expected_words
        union = transcribed_words | expected_words
        
        # Jaccard similarity
        if union:
            return len(intersection) / len(union)
        
        return 0.0
    
    def print_results(self, results: List[Dict]):
        """Print transcription validation results."""
        print("\n" + "="*80)
        print("WHISPER TRANSCRIPTION VALIDATION RESULTS")
        print("="*80)
        
        successful_tests = [r for r in results if r['success']]
        failed_tests = [r for r in results if not r['success']]
        
        print(f"\nTotal tests: {len(results)}")
        print(f"Successful: {len(successful_tests)}")
        print(f"Failed: {len(failed_tests)}")
        
        if successful_tests:
            avg_confidence = sum(r['confidence'] for r in successful_tests) / len(successful_tests)
            avg_similarity = sum(r['similarity'] for r in successful_tests) / len(successful_tests)
            print(f"Average confidence: {avg_confidence:.3f}")
            print(f"Average similarity: {avg_similarity:.3f}")
        
        print("\n" + "-"*80)
        print("DETAILED RESULTS")
        print("-"*80)
        
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {Path(result['file']).name} ({result['category']})")
            print(f"   Expected: {result['expected']}")
            print(f"   Result:   {result['result']}")
            
            if result['success']:
                print(f"   Confidence: {result['confidence']:.3f}")
                print(f"   Similarity: {result['similarity']:.3f}")
            else:
                print(f"   Error: {result['error']}")
        
        # Summary by category
        print("\n" + "-"*80)
        print("SUMMARY BY CATEGORY")
        print("-"*80)
        
        categories = {}
        for result in successful_tests:
            cat = result['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(result)
        
        for category, cat_results in categories.items():
            avg_confidence = sum(r['confidence'] for r in cat_results) / len(cat_results)
            avg_similarity = sum(r['similarity'] for r in cat_results) / len(cat_results)
            print(f"\n{category.upper()}:")
            print(f"  Tests: {len(cat_results)}")
            print(f"  Avg Confidence: {avg_confidence:.3f}")
            print(f"  Avg Similarity: {avg_similarity:.3f}")
    
    async def run_validation(self):
        """Run the complete transcription validation."""
        self.logger.info("Starting Whisper transcription validation...")
        
        # Load phrases mapping
        phrases_mapping = self.load_phrases_mapping()
        if not phrases_mapping:
            self.logger.error("Failed to load phrases mapping")
            return
        
        # Select test files
        test_files = self.select_test_files(phrases_mapping)
        self.logger.info(f"Selected {len(test_files)} test files")
        
        # Test each file
        results = []
        for audio_file, expected_text, category in test_files:
            self.logger.info(f"Testing: {Path(audio_file).name}")
            result = await self.test_transcription(audio_file, expected_text, category)
            results.append(result)
        
        # Print results
        self.print_results(results)
        
        # Save results to file
        self.save_results(results)
        
        self.logger.info("Whisper transcription validation completed")
    
    def save_results(self, results: List[Dict]):
        """Save results to a JSON file."""
        import json
        from datetime import datetime
        
        output_file = project_root / "test_logs" / f"whisper_transcription_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        output_file.parent.mkdir(exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        self.logger.info(f"Results saved to: {output_file}")


async def main():
    """Main function."""
    # Configure logging
    logger = configure_logging(name="whisper_transcription_validator", log_filename="whisper_transcription_validation.log")
    
    # Create validator and run validation
    validator = WhisperTranscriptionValidator(logger)
    await validator.run_validation()


if __name__ == "__main__":
    asyncio.run(main()) 