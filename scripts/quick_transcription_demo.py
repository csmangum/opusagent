#!/usr/bin/env python3
"""
Quick Transcription Demo

This script provides a quick demonstration of transcription capabilities
using a few selected audio files. It's designed to give immediate evidence
of transcription quality and acceptability.

Usage:
    python scripts/quick_transcription_demo.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from opusagent.local.realtime import (
    TranscriptionConfig,
    TranscriptionFactory
)


async def quick_transcription_demo():
    """Quick demonstration of transcription capabilities."""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("🎤 Quick Transcription Demo")
    logger.info("=" * 50)
    
    # Find a few audio files to test
    mock_audio_dir = project_root / "opusagent" / "mock" / "audio"
    test_files = []
    
    # Look for files in different categories
    categories = ["greetings", "customer_service", "technical_support"]
    for category in categories:
        category_dir = mock_audio_dir / category
        if category_dir.exists():
            wav_files = list(category_dir.glob("*.wav"))
            if wav_files:
                test_files.append(wav_files[0])  # Take first file from each category
                logger.info(f"Found test file: {wav_files[0].name} ({category})")
    
    if not test_files:
        logger.error("No audio files found for testing")
        return
    
    # Test configurations
    configs = [
        ("PocketSphinx", TranscriptionConfig(backend="pocketsphinx")),
        ("Whisper Base", TranscriptionConfig(backend="whisper", model_size="base")),
    ]
    
    for config_name, config in configs:
        logger.info(f"\n🔧 Testing {config_name}")
        logger.info("-" * 30)
        
        # Create transcriber
        transcriber = TranscriptionFactory.create_transcriber(config)
        
        # Initialize
        logger.info("Initializing transcriber...")
        init_success = await transcriber.initialize()
        
        if not init_success:
            logger.error(f"❌ Failed to initialize {config_name}")
            continue
        
        logger.info(f"✅ {config_name} initialized successfully")
        
        # Test each audio file
        for audio_file in test_files:
            logger.info(f"\n📁 Testing: {audio_file.name}")
            
            try:
                # Load audio file
                with open(audio_file, 'rb') as f:
                    audio_data = f.read()
                
                # Skip WAV header if present
                if len(audio_data) > 44 and audio_data[:4] == b'RIFF' and audio_data[8:12] == b'WAVE':
                    audio_data = audio_data[44:]  # Skip WAV header
                
                # Start session
                transcriber.start_session()
                
                # Process in chunks
                chunk_size = 3200  # 200ms at 16kHz 16-bit
                chunks = [audio_data[i:i + chunk_size] for i in range(0, len(audio_data), chunk_size)]
                
                accumulated_text = ""
                logger.info(f"Processing {len(chunks)} chunks...")
                
                for i, chunk in enumerate(chunks):
                    result = await transcriber.transcribe_chunk(chunk)
                    
                    if result.error:
                        logger.error(f"❌ Transcription error: {result.error}")
                        break
                    
                    if result.text:
                        accumulated_text += result.text
                        logger.info(f"  Chunk {i+1}: '{result.text}' (confidence: {result.confidence:.3f})")
                
                # Finalize
                final_result = await transcriber.finalize()
                
                # Use final result or accumulated text
                final_text = final_result.text if final_result.text else accumulated_text
                
                if final_text:
                    logger.info(f"✅ Final transcription: '{final_text}'")
                    logger.info(f"   Confidence: {final_result.confidence:.3f}")
                    logger.info(f"   Audio duration: ~{len(audio_data) / (16000 * 2):.1f}s")
                else:
                    logger.warning("⚠️  No transcription produced")
                
            except Exception as e:
                logger.error(f"❌ Error processing {audio_file.name}: {e}")
            
            finally:
                # Reset session for next file (don't cleanup until all files are done)
                transcriber.reset_session()
        
        logger.info(f"\n✅ {config_name} testing completed")


async def test_single_file_detailed():
    """Test a single file with detailed output for quality assessment."""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("\n🎯 Detailed Single File Test")
    logger.info("=" * 50)
    
    # Find a greeting file for detailed testing
    mock_audio_dir = project_root / "opusagent" / "mock" / "audio" / "greetings"
    if not mock_audio_dir.exists():
        logger.error("Greetings directory not found")
        return
    
    wav_files = list(mock_audio_dir.glob("*.wav"))
    if not wav_files:
        logger.error("No greeting files found")
        return
    
    test_file = wav_files[0]
    logger.info(f"Testing file: {test_file.name}")
    
    # Test both backends
    for backend_name, config in [
        ("PocketSphinx", TranscriptionConfig(backend="pocketsphinx")),
        ("Whisper Base", TranscriptionConfig(backend="whisper", model_size="base")),
    ]:
        logger.info(f"\n🔬 {backend_name} - Detailed Analysis")
        logger.info("-" * 40)
        
        transcriber = TranscriptionFactory.create_transcriber(config)
        
        if not await transcriber.initialize():
            logger.error(f"Failed to initialize {backend_name}")
            continue
        
        try:
            # Load and process audio
            with open(test_file, 'rb') as f:
                audio_data = f.read()
            
            if len(audio_data) > 44 and audio_data[:4] == b'RIFF' and audio_data[8:12] == b'WAVE':
                audio_data = audio_data[44:]
            
            transcriber.start_session()
            
            # Process with smaller chunks for more detailed output
            chunk_size = 1600  # 100ms chunks for more granular results
            chunks = [audio_data[i:i + chunk_size] for i in range(0, len(audio_data), chunk_size)]
            
            logger.info(f"Audio size: {len(audio_data)} bytes")
            logger.info(f"Estimated duration: {len(audio_data) / (16000 * 2):.2f}s")
            logger.info(f"Processing {len(chunks)} chunks of {chunk_size} bytes each")
            logger.info("")
            
            accumulated_text = ""
            chunk_results = []
            
            for i, chunk in enumerate(chunks):
                result = await transcriber.transcribe_chunk(chunk)
                
                if result.error:
                    logger.error(f"Chunk {i+1}: Error - {result.error}")
                    break
                
                chunk_results.append({
                    "chunk": i + 1,
                    "text": result.text,
                    "confidence": result.confidence,
                    "processing_time": result.processing_time
                })
                
                if result.text:
                    accumulated_text += result.text
                    logger.info(f"Chunk {i+1:2d}: '{result.text:20s}' | Confidence: {result.confidence:.3f}")
                else:
                    logger.info(f"Chunk {i+1:2d}: (no text)                    | Confidence: {result.confidence:.3f}")
            
            # Finalize
            final_result = await transcriber.finalize()
            final_text = final_result.text if final_result.text else accumulated_text
            
            logger.info("")
            logger.info("📊 RESULTS SUMMARY:")
            logger.info(f"Final transcription: '{final_text}'")
            logger.info(f"Final confidence: {final_result.confidence:.3f}")
            logger.info(f"Chunks with text: {len([r for r in chunk_results if r['text']])}/{len(chunk_results)}")
            
            if chunk_results:
                avg_confidence = sum(r['confidence'] for r in chunk_results) / len(chunk_results)
                logger.info(f"Average chunk confidence: {avg_confidence:.3f}")
            
            # Quality assessment
            if final_text.strip():
                if final_result.confidence > 0.7:
                    quality = "🟢 EXCELLENT"
                elif final_result.confidence > 0.5:
                    quality = "🟡 GOOD"
                elif final_result.confidence > 0.3:
                    quality = "🟠 ACCEPTABLE"
                else:
                    quality = "🔴 POOR"
                
                logger.info(f"Quality assessment: {quality}")
            else:
                logger.info("Quality assessment: 🔴 NO TRANSCRIPTION")
            
        except Exception as e:
            logger.error(f"Error during detailed testing: {e}")
        
        finally:
            # Clean up transcriber after detailed analysis
            await transcriber.cleanup()


async def main():
    """Main function to run the quick demo."""
    print("🎤 Transcription Quality Demo")
    print("=" * 60)
    
    # Run quick demo
    await quick_transcription_demo()
    
    # Run detailed single file test
    await test_single_file_detailed()
    
    print("\n" + "=" * 60)
    print("✅ Demo completed! Check the output above for transcription quality evidence.")
    print("📁 Detailed results are also saved to transcription_test_results.json")


if __name__ == "__main__":
    asyncio.run(main()) 