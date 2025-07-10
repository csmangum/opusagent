#!/usr/bin/env python3
"""
Script to transcribe audio files using PocketSphinx.
Specifically designed for the card_replacement audio files in opusagent/mock/audio/.
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Any
import json
import logging

# PocketSphinx imports
try:
    from pocketsphinx import AudioFile, Pocketsphinx
except ImportError:
    print("Error: PocketSphinx not installed. Please install it with:")
    print("pip install pocketsphinx")
    sys.exit(1)

# Add audio conversion imports
try:
    import soundfile as sf
    import librosa
except ImportError:
    sf = None
    librosa = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PocketSphinxTranscriber:
    """A class to handle audio transcription using PocketSphinx."""
    
    def __init__(self, language_model: Optional[str] = None, 
                 dictionary: Optional[str] = None,
                 acoustic_model: Optional[str] = None):
        """
        Initialize the transcriber with optional custom models.
        
        Args:
            language_model: Path to language model file (.lm)
            dictionary: Path to dictionary file (.dict)
            acoustic_model: Path to acoustic model directory
        """
        self.language_model = language_model
        self.dictionary = dictionary
        self.acoustic_model = acoustic_model
        
    def _convert_to_wav_pcm16_mono_16k(self, input_path: str) -> str:
        """
        Convert the input audio file to mono, 16kHz, 16-bit PCM WAV if needed.
        Returns the path to the converted file (may be the same as input if already correct).
        """
        if not sf or not librosa:
            # If conversion libraries are not available, just return the original file
            return input_path
        try:
            # Check if already correct format
            with sf.SoundFile(input_path) as f:
                if (
                    f.samplerate == 16000 and
                    f.channels == 1 and
                    f.subtype == 'PCM_16' and
                    f.format == 'WAV'
                ):
                    return input_path
            # Convert using librosa
            y, sr = librosa.load(input_path, sr=16000, mono=True)
            out_path = input_path + '.tmp_pocketsphinx.wav'
            sf.write(out_path, y, 16000, subtype='PCM_16')
            return out_path
        except Exception as e:
            logger.warning(f"Audio conversion failed for {input_path}: {e}")
            return input_path

    def transcribe_file(self, audio_file_path: str) -> Dict[str, Any]:
        """
        Transcribe a single audio file.
        
        Args:
            audio_file_path: Path to the audio file to transcribe
            
        Returns:
            Dictionary containing transcription results
        """
        import traceback
        try:
            # Print audio file properties
            if sf:
                try:
                    with sf.SoundFile(audio_file_path) as f:
                        logger.info(f"Audio file info: {audio_file_path} | Format: {f.format}, Channels: {f.channels}, Sample rate: {f.samplerate}, Frames: {f.frames}, Duration: {f.frames / f.samplerate:.2f}s, Subtype: {f.subtype}")
                        # Print first 10 samples as a quick check
                        f.seek(0)
                        samples = f.read(10)
                        logger.info(f"First 10 samples: {samples}")
                except Exception as e:
                    logger.warning(f"Could not read audio file info: {e}")
            # Convert audio to required format
            converted_path = self._convert_to_wav_pcm16_mono_16k(audio_file_path)
            if converted_path != audio_file_path and sf:
                try:
                    with sf.SoundFile(converted_path) as f:
                        logger.info(f"Converted file info: {converted_path} | Format: {f.format}, Channels: {f.channels}, Sample rate: {f.samplerate}, Frames: {f.frames}, Duration: {f.frames / f.samplerate:.2f}s, Subtype: {f.subtype}")
                except Exception as e:
                    logger.warning(f"Could not read converted file info: {e}")
            # Configure PocketSphinx
            config: Dict[str, Any] = {
                'verbose': False,
            }
            
            # Try to suppress logging output (platform-specific)
            import platform
            if platform.system() != 'Windows':
                config['logfn'] = '/dev/null'
            
            # Add custom models if provided
                
            # Create Pocketsphinx instance
            ps = Pocketsphinx(**config)
            
            # Create AudioFile object and decode
            audio = AudioFile(audio_file=converted_path, **config)
            for phrase in audio:
                pass  # Process all audio
            
            # Get results
            hypothesis = ps.hypothesis()
            confidence = ps.get_prob()
            segments = []
            try:
                logger.info("Segments detected by PocketSphinx:")
                seg_result = ps.seg()
                if seg_result is not None:
                    for seg in seg_result:
                        logger.info(f"  word='{seg.word}', start={seg.start_frame/100.0:.2f}s, end={seg.end_frame/100.0:.2f}s, prob={seg.prob}")
                        segments.append({
                            'word': seg.word,
                            'start': seg.start_frame / 100.0,
                            'end': seg.end_frame / 100.0,
                            'prob': seg.prob
                        })
                else:
                    logger.info("  (ps.seg() returned None - no segments detected)")
                if not segments:
                    logger.info("  (No segments detected)")
            except Exception as e:
                logger.warning(f"Error getting segments: {e}")
            logger.info(f"Hypothesis: '{hypothesis}' (type: {type(hypothesis)})")
            logger.info(f"Confidence: {confidence} (type: {type(confidence)})")
            
            # Clean up temp file if created
            if converted_path != audio_file_path and converted_path.endswith('.tmp_pocketsphinx.wav'):
                try:
                    os.remove(converted_path)
                except Exception:
                    pass

            return {
                'file_path': audio_file_path,
                'transcription': hypothesis,
                'confidence': confidence,
                'segments': segments,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error transcribing {audio_file_path}: {str(e)}")
            traceback.print_exc()
            return {
                'file_path': audio_file_path,
                'transcription': '',
                'confidence': 0.0,
                'segments': [],
                'success': False,
                'error': str(e)
            }
    
    def transcribe_directory(self, directory_path: str, 
                           output_file: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Transcribe all audio files in a directory.
        
        Args:
            directory_path: Path to directory containing audio files
            output_file: Optional path to save results as JSON
            
        Returns:
            List of transcription results
        """
        directory = Path(directory_path)
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory_path}")
        
        # Find all audio files
        audio_extensions = {'.wav', '.mp3', '.flac', '.m4a', '.ogg'}
        audio_files = [
            f for f in directory.iterdir() 
            if f.is_file() and f.suffix.lower() in audio_extensions
        ]
        
        if not audio_files:
            logger.warning(f"No audio files found in {directory_path}")
            return []
        
        logger.info(f"Found {len(audio_files)} audio files to transcribe")
        
        results = []
        for i, audio_file in enumerate(audio_files, 1):
            logger.info(f"Transcribing {i}/{len(audio_files)}: {audio_file.name}")
            result = self.transcribe_file(str(audio_file))
            results.append(result)
            
            # Print progress
            if result['success']:
                logger.info(f"✓ {audio_file.name}: {result['transcription'][:100]}...")
            else:
                logger.error(f"✗ {audio_file.name}: {result.get('error', 'Unknown error')}")
        
        # Save results if output file specified
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            logger.info(f"Results saved to {output_file}")
        
        return results


def main():
    """Main function to run the transcription script."""
    parser = argparse.ArgumentParser(
        description="Transcribe audio files using PocketSphinx"
    )
    parser.add_argument(
        'input_path',
        help='Path to audio file or directory to transcribe'
    )
    parser.add_argument(
        '--output', '-o',
        help='Output file to save results (JSON format)'
    )
    parser.add_argument(
        '--language-model', '-lm',
        help='Path to custom language model file'
    )
    parser.add_argument(
        '--dictionary', '-dict',
        help='Path to custom dictionary file'
    )
    parser.add_argument(
        '--acoustic-model', '-hmm',
        help='Path to custom acoustic model directory'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize transcriber
    transcriber = PocketSphinxTranscriber(
        language_model=args.language_model,
        dictionary=args.dictionary,
        acoustic_model=args.acoustic_model
    )
    
    input_path = Path(args.input_path)
    
    try:
        if input_path.is_file():
            # Transcribe single file
            logger.info(f"Transcribing single file: {input_path}")
            result = transcriber.transcribe_file(str(input_path))
            
            if result['success']:
                print(f"\nTranscription: {result['transcription']}")
                print(f"Confidence: {result['confidence']:.2f}")
                
                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump([result], f, indent=2, ensure_ascii=False)
                    logger.info(f"Results saved to {args.output}")
            else:
                print(f"Transcription failed: {result.get('error', 'Unknown error')}")
                
        elif input_path.is_dir():
            # Transcribe directory
            logger.info(f"Transcribing directory: {input_path}")
            results = transcriber.transcribe_directory(
                str(input_path), 
                args.output
            )
            
            # Print summary
            successful = sum(1 for r in results if r['success'])
            total = len(results)
            print(f"\nTranscription Summary:")
            print(f"Total files: {total}")
            print(f"Successful: {successful}")
            print(f"Failed: {total - successful}")
            
            if successful > 0:
                avg_confidence = sum(r['confidence'] for r in results if r['success']) / successful
                print(f"Average confidence: {avg_confidence:.2f}")
                
        else:
            logger.error(f"Input path does not exist: {input_path}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error during transcription: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 