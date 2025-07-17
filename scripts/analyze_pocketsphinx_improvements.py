#!/usr/bin/env python3
"""
PocketSphinx Improvement Analysis

This script analyzes potential improvements for PocketSphinx transcription accuracy
by testing different configurations, audio preprocessing, and model parameters.

Usage:
    python scripts/analyze_pocketsphinx_improvements.py
"""

import asyncio
import logging
import sys
import yaml
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from opusagent.mock.transcription import TranscriptionFactory, TranscriptionConfig
from opusagent.config.logging_config import configure_logging


class PocketSphinxImprovementAnalyzer:
    """Analyzes potential improvements for PocketSphinx accuracy."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.audio_dir = project_root / "opusagent" / "mock" / "audio"
        self.phrases_mapping_file = self.audio_dir / "phrases_mapping.yml"
        
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
                
                # Select first phrase from each category
                if phrases:
                    first_phrase = phrases[0]
                    file_path = self.audio_dir / category / first_phrase['file']
                    if file_path.exists():
                        test_files.append((
                            str(file_path),
                            first_phrase['phrase'],
                            category
                        ))
        
        return test_files
    
    def resample_audio_to_16khz(self, audio_file: str) -> bytes:
        """Resample audio file from 24kHz to 16kHz for PocketSphinx."""
        try:
            import librosa
            
            # Load audio with librosa (handles resampling automatically)
            audio_array, sample_rate = librosa.load(audio_file, sr=16000, mono=True)
            
            # Convert to 16-bit PCM
            audio_int16 = (audio_array * 32767).astype(np.int16)
            
            return audio_int16.tobytes()
            
        except ImportError:
            self.logger.warning("librosa not available, using basic resampling")
            return self._basic_resample_audio(audio_file)
        except Exception as e:
            self.logger.error(f"Error resampling {audio_file}: {e}")
            return self._basic_resample_audio(audio_file)
    
    def _basic_resample_audio(self, audio_file: str) -> bytes:
        """Basic audio resampling using scipy."""
        try:
            import wave
            from scipy import signal
            
            with wave.open(audio_file, 'rb') as wav_file:
                sample_rate = wav_file.getframerate()
                audio_data = wav_file.readframes(wav_file.getnframes())
                
                # Convert to numpy array
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                
                # Resample to 16kHz
                if sample_rate != 16000:
                    number_of_samples = round(len(audio_array) * 16000 / sample_rate)
                    audio_array = signal.resample(audio_array, number_of_samples)
                    audio_array = np.array(audio_array, dtype=np.int16)
                
                return audio_array.tobytes()
                
        except Exception as e:
            self.logger.error(f"Basic resampling failed for {audio_file}: {e}")
            # Return original audio as fallback
            with open(audio_file, 'rb') as f:
                return f.read()
    
    def apply_audio_preprocessing(self, audio_data: bytes, preprocessing_type: str) -> bytes:
        """Apply different audio preprocessing techniques."""
        try:
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            if preprocessing_type == "normalize":
                # Normalize audio
                if np.max(np.abs(audio_array)) > 0:
                    audio_array = audio_array / np.max(np.abs(audio_array))
            
            elif preprocessing_type == "noise_reduction":
                # Simple noise reduction (high-pass filter)
                from scipy import signal
                b, a = signal.butter(4, 0.1, btype='high')
                audio_array = signal.filtfilt(b, a, audio_array)
            
            elif preprocessing_type == "amplify":
                # Amplify audio
                audio_array = audio_array * 1.5
                audio_array = np.clip(audio_array, -1.0, 1.0)
            
            elif preprocessing_type == "silence_trim":
                # Trim silence from beginning and end
                threshold = 0.01
                start_idx = np.where(np.abs(audio_array) > threshold)[0]
                if len(start_idx) > 0:
                    start = start_idx[0]
                    end = start_idx[-1]
                    audio_array = audio_array[start:end+1]
            
            # Convert back to int16
            audio_int16 = (audio_array * 32767).astype(np.int16)
            return audio_int16.tobytes()
            
        except Exception as e:
            self.logger.error(f"Audio preprocessing failed: {e}")
            return audio_data
    
    def create_pocketsphinx_config(self, config_type: str) -> TranscriptionConfig:
        """Create different PocketSphinx configurations for testing."""
        if config_type == "default":
            return TranscriptionConfig(
                backend="pocketsphinx",
                language="en",
                chunk_duration=1.0,
                confidence_threshold=0.5,
                sample_rate=16000,
                enable_vad=False,
                device="cpu"
            )
        elif config_type == "aggressive":
            return TranscriptionConfig(
                backend="pocketsphinx",
                language="en",
                chunk_duration=0.5,  # Shorter chunks
                confidence_threshold=0.3,  # Lower threshold
                sample_rate=16000,
                enable_vad=False,
                device="cpu"
            )
        elif config_type == "conservative":
            return TranscriptionConfig(
                backend="pocketsphinx",
                language="en",
                chunk_duration=2.0,  # Longer chunks
                confidence_threshold=0.7,  # Higher threshold
                sample_rate=16000,
                enable_vad=False,
                device="cpu"
            )
        else:
            return self.create_pocketsphinx_config("default")
    
    async def test_transcription(self, audio_file: str, expected_text: str, category: str, 
                               config_type: str, preprocessing_type: str = "none") -> Dict:
        """Test transcription with specific configuration and preprocessing."""
        try:
            # Create PocketSphinx configuration
            config = self.create_pocketsphinx_config(config_type)
            
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
                    'success': False,
                    'config_type': config_type,
                    'preprocessing': preprocessing_type
                }
            
            # Resample audio to 16kHz
            audio_data = self.resample_audio_to_16khz(audio_file)
            
            # Apply preprocessing if specified
            if preprocessing_type != "none":
                audio_data = self.apply_audio_preprocessing(audio_data, preprocessing_type)
            
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
            
            # Calculate similarity
            similarity = self.calculate_similarity(transcribed_text, expected_text)
            
            return {
                'file': audio_file,
                'category': category,
                'expected': expected_text,
                'result': transcribed_text,
                'confidence': final_result.confidence,
                'similarity': similarity,
                'error': None,
                'success': True,
                'config_type': config_type,
                'preprocessing': preprocessing_type
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
                'success': False,
                'config_type': config_type,
                'preprocessing': preprocessing_type
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
    
    def analyze_results(self, results: List[Dict]):
        """Analyze results and provide improvement recommendations."""
        print("\n" + "="*80)
        print("POCKETSPHINX IMPROVEMENT ANALYSIS")
        print("="*80)
        
        # Group results by configuration
        config_results = {}
        for result in results:
            if result['success']:
                key = f"{result['config_type']}_{result['preprocessing']}"
                if key not in config_results:
                    config_results[key] = []
                config_results[key].append(result)
        
        # Calculate averages for each configuration
        config_averages = {}
        for config_key, config_list in config_results.items():
            avg_confidence = sum(r['confidence'] for r in config_list) / len(config_list)
            avg_similarity = sum(r['similarity'] for r in config_list) / len(config_list)
            config_averages[config_key] = {
                'avg_confidence': avg_confidence,
                'avg_similarity': avg_similarity,
                'count': len(config_list)
            }
        
        # Print configuration comparison
        print("\nCONFIGURATION COMPARISON:")
        print("-" * 60)
        print(f"{'Configuration':<25} {'Avg Confidence':<15} {'Avg Similarity':<15} {'Tests':<8}")
        print("-" * 60)
        
        for config_key, stats in config_averages.items():
            print(f"{config_key:<25} {stats['avg_confidence']:<15.3f} {stats['avg_similarity']:<15.3f} {stats['count']:<8}")
        
        # Find best configuration
        best_config = max(config_averages.items(), key=lambda x: x[1]['avg_similarity'])
        print(f"\nBEST CONFIGURATION: {best_config[0]} (Similarity: {best_config[1]['avg_similarity']:.3f})")
        
        # Analyze by category
        print("\n" + "-"*80)
        print("CATEGORY ANALYSIS")
        print("-"*80)
        
        categories = {}
        for result in results:
            if result['success']:
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
            
            # Find best result for this category
            best_result = max(cat_results, key=lambda x: x['similarity'])
            print(f"  Best Result: {best_result['config_type']}_{best_result['preprocessing']} (Similarity: {best_result['similarity']:.3f})")
        
        # Provide recommendations
        print("\n" + "-"*80)
        print("IMPROVEMENT RECOMMENDATIONS")
        print("-"*80)
        
        print("\n1. AUDIO PREPROCESSING:")
        preprocessing_results = {}
        for result in results:
            if result['success']:
                prep = result['preprocessing']
                if prep not in preprocessing_results:
                    preprocessing_results[prep] = []
                preprocessing_results[prep].append(result)
        
        for prep, prep_results in preprocessing_results.items():
            avg_similarity = sum(r['similarity'] for r in prep_results) / len(prep_results)
            print(f"   {prep}: {avg_similarity:.3f} average similarity")
        
        print("\n2. CONFIGURATION SETTINGS:")
        config_results = {}
        for result in results:
            if result['success']:
                config = result['config_type']
                if config not in config_results:
                    config_results[config] = []
                config_results[config].append(result)
        
        for config, config_list in config_results.items():
            avg_similarity = sum(r['similarity'] for r in config_list) / len(config_list)
            print(f"   {config}: {avg_similarity:.3f} average similarity")
        
        print("\n3. GENERAL RECOMMENDATIONS:")
        print("   - Use audio resampling to 16kHz (already implemented)")
        print("   - Consider audio normalization for consistent levels")
        print("   - Test different confidence thresholds")
        print("   - Experiment with chunk durations")
        print("   - Consider using Whisper for better accuracy")
        
        # Identify common transcription errors
        print("\n4. COMMON TRANSCRIPTION ERRORS:")
        error_patterns = {}
        for result in results:
            if result['success'] and result['similarity'] < 0.5:
                expected_words = set(result['expected'].lower().split())
                result_words = set(result['result'].lower().split())
                missing_words = expected_words - result_words
                extra_words = result_words - expected_words
                
                for word in missing_words:
                    error_patterns[word] = error_patterns.get(word, 0) + 1
                
                for word in extra_words:
                    error_patterns[word] = error_patterns.get(word, 0) + 1
        
        if error_patterns:
            sorted_errors = sorted(error_patterns.items(), key=lambda x: x[1], reverse=True)
            print("   Most common errors:")
            for word, count in sorted_errors[:10]:
                print(f"     '{word}': {count} occurrences")
    
    async def run_analysis(self):
        """Run the complete improvement analysis."""
        self.logger.info("Starting PocketSphinx improvement analysis...")
        
        # Load phrases mapping
        phrases_mapping = self.load_phrases_mapping()
        if not phrases_mapping:
            self.logger.error("Failed to load phrases mapping")
            return
        
        # Select test files
        test_files = self.select_test_files(phrases_mapping)
        self.logger.info(f"Selected {len(test_files)} test files")
        
        # Test configurations
        config_types = ["default", "aggressive", "conservative"]
        preprocessing_types = ["none", "normalize", "noise_reduction", "amplify", "silence_trim"]
        
        # Run tests
        results = []
        for audio_file, expected_text, category in test_files:
            self.logger.info(f"Testing: {Path(audio_file).name}")
            
            for config_type in config_types:
                for preprocessing_type in preprocessing_types:
                    result = await self.test_transcription(
                        audio_file, expected_text, category, config_type, preprocessing_type
                    )
                    results.append(result)
        
        # Analyze results
        self.analyze_results(results)
        
        # Save results
        self.save_results(results)
        
        self.logger.info("PocketSphinx improvement analysis completed")
    
    def save_results(self, results: List[Dict]):
        """Save results to a JSON file."""
        import json
        from datetime import datetime
        
        output_file = project_root / "test_logs" / f"pocketsphinx_improvement_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        output_file.parent.mkdir(exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        self.logger.info(f"Results saved to: {output_file}")


async def main():
    """Main function."""
    # Configure logging
    logger = configure_logging(name="pocketsphinx_improvement_analyzer", log_filename="pocketsphinx_improvement_analysis.log")
    
    # Create analyzer and run analysis
    analyzer = PocketSphinxImprovementAnalyzer(logger)
    await analyzer.run_analysis()


if __name__ == "__main__":
    asyncio.run(main()) 