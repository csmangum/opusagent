#!/usr/bin/env python3
"""
Example script demonstrating PocketSphinx transcription of card_replacement audio files.

This script shows how to use the transcribe_with_pocketsphinx.py script to transcribe
the audio files in opusagent/mock/audio/card_replacement/.

Usage:
    python scripts/example_pocketsphinx_transcription.py
"""

import sys
import os
from pathlib import Path

# Add the project root to the path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.transcribe_with_pocketsphinx import PocketSphinxTranscriber


def main():
    """Main function to demonstrate PocketSphinx transcription."""
    print("🎤 PocketSphinx Transcription Example")
    print("=" * 50)
    
    # Path to the card_replacement audio files
    audio_dir = "opusagent/mock/audio/card_replacement"
    
    if not Path(audio_dir).exists():
        print(f"❌ Audio directory not found: {audio_dir}")
        print("Please ensure the audio files exist in the specified directory.")
        return
    
    # Initialize the transcriber
    print("🔧 Initializing PocketSphinx transcriber...")
    transcriber = PocketSphinxTranscriber()
    
    # Transcribe all files in the directory
    print(f"📁 Transcribing files in: {audio_dir}")
    print("-" * 50)
    
    try:
        results = transcriber.transcribe_directory(
            directory_path=audio_dir,
            output_file="card_replacement_transcriptions.json"
        )
        
        # Print summary
        print("\n📊 Transcription Summary:")
        print("=" * 50)
        
        successful = sum(1 for r in results if r['success'])
        total = len(results)
        
        print(f"Total files processed: {total}")
        print(f"Successful transcriptions: {successful}")
        print(f"Failed transcriptions: {total - successful}")
        
        if successful > 0:
            avg_confidence = sum(r['confidence'] for r in results if r['success']) / successful
            print(f"Average confidence: {avg_confidence:.2f}")
        
        # Show individual results
        print("\n📝 Individual Results:")
        print("-" * 50)
        
        for result in results:
            filename = Path(result['file_path']).name
            if result['success']:
                transcription = result['transcription']
                confidence = result['confidence']
                print(f"✅ {filename}:")
                print(f"   Text: {transcription}")
                print(f"   Confidence: {confidence:.2f}")
            else:
                error = result.get('error', 'Unknown error')
                print(f"❌ {filename}: {error}")
            print()
        
        print(f"💾 Results saved to: card_replacement_transcriptions.json")
        
    except Exception as e:
        print(f"❌ Error during transcription: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 