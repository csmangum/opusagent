#!/usr/bin/env python3
"""
Transcription Validation Script

This script validates the transcription model by processing audio files from the mock audio directory
and comparing the results with expected phrases from the phrases_mapping.yml file.

Usage:
    python scripts/validate_transcription_with_audio_files.py
    
    
    
2025-07-16 17:00:21,931 - transcription_validator - INFO - Logging configured
2025-07-16 17:00:21,932 - transcription_validator - INFO - Starting transcription validation...
2025-07-16 17:00:21,944 - transcription_validator - INFO - Selected 8 test files
2025-07-16 17:00:21,945 - transcription_validator - INFO - Testing: greetings_01.wav
2025-07-16 17:00:21,945 - transcription_validator - INFO - Testing with backend: pocketsphinx
2025-07-16 17:00:22,784 - transcription_validator - INFO - Testing: greetings_10.wav
2025-07-16 17:00:22,784 - transcription_validator - INFO - Testing with backend: pocketsphinx
2025-07-16 17:00:23,960 - transcription_validator - INFO - Testing: customer_service_01.wav
2025-07-16 17:00:23,960 - transcription_validator - INFO - Testing with backend: pocketsphinx
2025-07-16 17:00:25,487 - transcription_validator - INFO - Testing: customer_service_10.wav
2025-07-16 17:00:25,487 - transcription_validator - INFO - Testing with backend: pocketsphinx
2025-07-16 17:00:26,359 - transcription_validator - INFO - Testing: errors_01.wav
2025-07-16 17:00:26,359 - transcription_validator - INFO - Testing with backend: pocketsphinx
2025-07-16 17:00:27,767 - transcription_validator - INFO - Testing: errors_10.wav
2025-07-16 17:00:27,768 - transcription_validator - INFO - Testing with backend: pocketsphinx
2025-07-16 17:00:28,886 - transcription_validator - INFO - Testing: confirmations_01.wav
2025-07-16 17:00:28,886 - transcription_validator - INFO - Testing with backend: pocketsphinx
2025-07-16 17:00:29,652 - transcription_validator - INFO - Testing: confirmations_10.wav
2025-07-16 17:00:29,653 - transcription_validator - INFO - Testing with backend: pocketsphinx

================================================================================
TRANSCRIPTION VALIDATION RESULTS
================================================================================

Total tests: 8
Successful: 8
Failed: 0
Average confidence: 1.000
Average similarity: 0.050

--------------------------------------------------------------------------------
DETAILED RESULTS
--------------------------------------------------------------------------------

1. greetings_01.wav (greetings)
   Expected: Hello! How can I assist you today?
   Result:   angle how open air since two to
   Confidence: 1.000
   Similarity: 0.077

2. greetings_10.wav (greetings)
   Expected: Hello! I'm your AI assistant, ready to assist.
   Result:   oh hang are real good so stood would you too will serve start
   Confidence: 1.000
   Similarity: 0.000

3. customer_service_01.wav (customer_service)
   Expected: Hello, welcome to our customer service. How can I help you today?
   Result:   oh no control costume shows it's hard to their head to to turn
   Confidence: 1.000
   Similarity: 0.045

4. customer_service_10.wav (customer_service)
   Expected: I'm here to help you resolve this issue.
   Result:   our new art and i hope i do worse moved to spit shoot
   Confidence: 1.000
   Similarity: 0.053

5. errors_01.wav (errors)
   Expected: I apologize for the inconvenience. Let me fix that.
   Result:   are you pay for church who do you need to do newark stop what we fix for a
   Confidence: 1.000
   Similarity: 0.091

6. errors_10.wav (errors)
   Expected: I apologize for the error. Let me resolve it quickly.
   Result:   our banter is true to your are dinner you're saying for work
   Confidence: 1.000
   Similarity: 0.048

7. confirmations_01.wav (confirmations)
   Expected: I've confirmed your information is correct.
   Result:   or if consumed during solution is part
   Confidence: 1.000
   Similarity: 0.083

8. confirmations_10.wav (confirmations)
   Expected: Confirmed. Everything is in order.
   Result:   russell not our food for news and the poor girl
   Confidence: 1.000
   Similarity: 0.000

--------------------------------------------------------------------------------
SUMMARY BY CATEGORY
--------------------------------------------------------------------------------

GREETINGS:
  Tests: 2
  Avg Confidence: 1.000
  Avg Similarity: 0.038

CUSTOMER_SERVICE:
  Tests: 2
  Avg Confidence: 1.000
  Avg Similarity: 0.049

ERRORS:
  Tests: 2
  Avg Confidence: 1.000
  Avg Similarity: 0.069

CONFIRMATIONS:
  Tests: 2
  Avg Confidence: 1.000
  Avg Similarity: 0.042
2025-07-16 17:00:30,527 - transcription_validator - INFO - Results saved to: c:\Users\peril\Dropbox\Development\fastagent\test_logs\transcription_validation_20250716_170030.json
2025-07-16 17:00:30,528 - transcription_validator - INFO - Transcription validation completed

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

from opusagent.mock.transcription import TranscriptionFactory, load_transcription_config
from opusagent.config.logging_config import configure_logging


class TranscriptionValidator:
    """Validates transcription model with audio files."""
    
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
    
    async def test_transcription(self, audio_file: str, expected_text: str, category: str) -> Dict:
        """Test transcription on a single audio file."""
        try:
            # Load transcription configuration
            config = load_transcription_config()
            self.logger.info(f"Testing with backend: {config.backend}")
            
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
            chunk_size = 3200  # 200ms at 16kHz 16-bit
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
        print("TRANSCRIPTION VALIDATION RESULTS")
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
        self.logger.info("Starting transcription validation...")
        
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
        
        self.logger.info("Transcription validation completed")
    
    def save_results(self, results: List[Dict]):
        """Save results to a JSON file."""
        import json
        from datetime import datetime
        
        output_file = project_root / "test_logs" / f"transcription_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        output_file.parent.mkdir(exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        self.logger.info(f"Results saved to: {output_file}")


async def main():
    """Main function."""
    # Configure logging
    logger = configure_logging(name="transcription_validator", log_filename="transcription_validation.log")
    
    # Create validator and run validation
    validator = TranscriptionValidator(logger)
    await validator.run_validation()


if __name__ == "__main__":
    asyncio.run(main()) 