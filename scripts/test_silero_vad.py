#!/usr/bin/env python3
"""
Silero VAD Test Script

This script tests Silero VAD (Voice Activity Detection) with real-time microphone input.
It provides visualization of VAD results and allows testing different sensitivity levels.

Requirements:
- torch
- torchaudio
- sounddevice
- numpy
- matplotlib (for visualization)
- silero-vad (from https://github.com/snakers4/silero-vad)

Usage:
    python scripts/test_silero_vad.py --duration 30 --sensitivity 0.5
    python scripts/test_silero_vad.py --visualize --test-sensitivity
"""

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import sounddevice as sd
import torch
import torchaudio

# Add the project root to the path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class SileroVADTester:
    """
    Silero VAD tester with real-time microphone input and visualization.
    """
    
    def __init__(
        self,
        sample_rate: int = 16000,
        chunk_size: int = 512,  # Silero VAD requires 512 for 16kHz, 256 for 8kHz
        device: str = "cpu",
        logger: Optional[logging.Logger] = None
    ):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.device = device
        self.logger = logger or logging.getLogger(__name__)
        
        # VAD model
        self.vad_model = None
        self.vad_utils = None
        
        # Validate chunk size for sample rate
        self._validate_chunk_size()
        
        # Audio state
        self.recording = False
        self.audio_buffer = []
        self.vad_results = []
        
        # Statistics
        self.total_chunks = 0
        self.speech_chunks = 0
        self.silence_chunks = 0
    
    def _validate_chunk_size(self):
        """Validate that chunk size is correct for the sample rate."""
        if self.sample_rate == 16000 and self.chunk_size != 512:
            self.logger.warning(f"Chunk size {self.chunk_size} is not optimal for 16kHz. Using 512.")
            self.chunk_size = 512
        elif self.sample_rate == 8000 and self.chunk_size != 256:
            self.logger.warning(f"Chunk size {self.chunk_size} is not optimal for 8kHz. Using 256.")
            self.chunk_size = 256
        elif self.sample_rate not in [8000, 16000]:
            self.logger.warning(f"Sample rate {self.sample_rate} is not supported. Using 16kHz with chunk size 512.")
            self.sample_rate = 16000
            self.chunk_size = 512
        
    def load_silero_vad(self):
        """Load Silero VAD model."""
        try:
            # Import silero-vad
            from silero_vad import load_silero_vad, read_audio, get_speech_timestamps
            
            self.logger.info("Loading Silero VAD model...")
            
            # Load model using the correct API
            self.vad_model = load_silero_vad()
            
            # Store utility functions
            self.read_audio = read_audio
            self.get_speech_timestamps = get_speech_timestamps
            
            self.logger.info(f"Silero VAD model loaded successfully on {self.device}")
            return True
            
        except ImportError:
            self.logger.error("silero-vad not found. Install with: pip install silero-vad")
            return False
        except Exception as e:
            self.logger.error(f"Error loading Silero VAD model: {e}")
            return False
    
    def detect_speech_silero(self, audio_chunk: np.ndarray, threshold: float = 0.5) -> bool:
        """
        Detect speech using Silero VAD.
        
        Args:
            audio_chunk: Audio data as numpy array (float32, -1 to 1)
            threshold: VAD threshold (0.0 to 1.0)
            
        Returns:
            True if speech detected, False otherwise
        """
        if self.vad_model is None:
            return False
            
        try:
            # Convert to tensor
            audio_tensor = torch.from_numpy(audio_chunk).float()
            
            # Get VAD prediction using the correct API
            speech_prob = self.vad_model(audio_tensor, self.sample_rate).item()
            
            # Store result for visualization
            self.vad_results.append({
                'timestamp': time.time(),
                'speech_prob': speech_prob,
                'is_speech': speech_prob > threshold
            })
            
            return speech_prob > threshold
            
        except Exception as e:
            self.logger.error(f"Error in Silero VAD detection: {e}")
            return False
    
    def audio_callback(self, indata, frames, time_info, status):
        """Audio callback for real-time processing."""
        if status:
            self.logger.warning(f"Audio callback status: {status}")
        
        if not self.recording:
            return
        
        try:
            # Convert to float32 and normalize
            audio_chunk = indata[:, 0].astype(np.float32) / 32768.0
            
            # Store audio for analysis
            self.audio_buffer.append(audio_chunk.copy())
            
            # Limit buffer size to prevent memory issues
            if len(self.audio_buffer) > 1000:  # Keep last ~64 seconds
                self.audio_buffer.pop(0)
            
            self.total_chunks += 1
            
        except Exception as e:
            self.logger.error(f"Error in audio callback: {e}")
    
    def start_recording(self):
        """Start recording from microphone."""
        self.recording = True
        self.audio_buffer.clear()
        self.vad_results.clear()
        self.total_chunks = 0
        self.speech_chunks = 0
        self.silence_chunks = 0
        
        self.logger.info("🎤 Started recording from microphone")
    
    def stop_recording(self):
        """Stop recording."""
        self.recording = False
        self.logger.info("⏹️  Stopped recording")
    
    def test_single_sensitivity(self, threshold: float, duration: float = 10.0) -> dict:
        """
        Test VAD with a single sensitivity threshold.
        
        Args:
            threshold: VAD threshold (0.0 to 1.0)
            duration: Test duration in seconds
            
        Returns:
            Dictionary with test results
        """
        self.logger.info(f"🔧 Testing sensitivity: {threshold}")
        self.logger.info(f"📝 Speak at different volumes for {duration} seconds")
        
        # Clear previous results
        self.vad_results.clear()
        self.total_chunks = 0
        self.speech_chunks = 0
        self.silence_chunks = 0
        
        # Start recording
        self.start_recording()
        
        # Process audio in real-time
        start_time = time.time()
        
        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype=np.int16,
            blocksize=self.chunk_size,
            callback=self.audio_callback
        ):
            while time.time() - start_time < duration:
                time.sleep(0.1)
        
        # Stop recording
        self.stop_recording()
        
        # Process all audio chunks with VAD
        self.logger.info("🔍 Processing audio with Silero VAD...")
        
        for audio_chunk in self.audio_buffer:
            is_speech = self.detect_speech_silero(audio_chunk, threshold)
            if is_speech:
                self.speech_chunks += 1
            else:
                self.silence_chunks += 1
        
        # Calculate statistics
        total_processed = self.speech_chunks + self.silence_chunks
        speech_percentage = (self.speech_chunks / total_processed * 100) if total_processed > 0 else 0
        
        results = {
            'threshold': threshold,
            'duration': duration,
            'total_chunks': total_processed,
            'speech_chunks': self.speech_chunks,
            'silence_chunks': self.silence_chunks,
            'speech_percentage': speech_percentage,
            'vad_results': self.vad_results.copy()
        }
        
        self.logger.info(f"📊 Results for threshold {threshold}:")
        self.logger.info(f"   Speech chunks: {self.speech_chunks}")
        self.logger.info(f"   Silence chunks: {self.silence_chunks}")
        self.logger.info(f"   Speech percentage: {speech_percentage:.1f}%")
        
        return results
    
    def test_multiple_sensitivities(self, thresholds: list, duration_per_test: float = 10.0) -> list:
        """
        Test VAD with multiple sensitivity thresholds.
        
        Args:
            thresholds: List of VAD thresholds to test
            duration_per_test: Duration for each test in seconds
            
        Returns:
            List of test results
        """
        results = []
        
        for threshold in thresholds:
            self.logger.info(f"\n{'='*50}")
            self.logger.info(f"Testing threshold: {threshold}")
            self.logger.info(f"{'='*50}")
            
            result = self.test_single_sensitivity(threshold, duration_per_test)
            results.append(result)
            
            # Brief pause between tests
            time.sleep(1)
        
        return results
    
    def visualize_results(self, results: list, save_plot: bool = False):
        """
        Visualize VAD test results.
        
        Args:
            results: List of test results from test_multiple_sensitivities
            save_plot: Whether to save the plot to file
        """
        try:
            import matplotlib.pyplot as plt
            
            if not results:
                self.logger.warning("No results to visualize")
                return
            
            # Create figure with subplots
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle('Silero VAD Test Results', fontsize=16)
            
            # Plot 1: Speech percentage by threshold
            thresholds = [r['threshold'] for r in results]
            speech_percentages = [r['speech_percentage'] for r in results]
            
            ax1.plot(thresholds, speech_percentages, 'bo-', linewidth=2, markersize=8)
            ax1.set_xlabel('VAD Threshold')
            ax1.set_ylabel('Speech Percentage (%)')
            ax1.set_title('Speech Detection Rate vs Threshold')
            ax1.grid(True, alpha=0.3)
            
            # Plot 2: Speech vs Silence chunks
            speech_chunks = [r['speech_chunks'] for r in results]
            silence_chunks = [r['silence_chunks'] for r in results]
            
            x = np.arange(len(thresholds))
            width = 0.35
            
            ax2.bar(x - width/2, speech_chunks, width, label='Speech', color='green', alpha=0.7)
            ax2.bar(x + width/2, silence_chunks, width, label='Silence', color='red', alpha=0.7)
            ax2.set_xlabel('VAD Threshold')
            ax2.set_ylabel('Number of Chunks')
            ax2.set_title('Speech vs Silence Chunks')
            ax2.set_xticks(x)
            ax2.set_xticklabels([f'{t:.2f}' for t in thresholds])
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            
            # Plot 3: VAD probability over time (for first result)
            if results[0]['vad_results']:
                timestamps = [r['timestamp'] - results[0]['vad_results'][0]['timestamp'] 
                            for r in results[0]['vad_results']]
                speech_probs = [r['speech_prob'] for r in results[0]['vad_results']]
                
                ax3.plot(timestamps, speech_probs, 'b-', alpha=0.7, linewidth=1)
                ax3.axhline(y=results[0]['threshold'], color='r', linestyle='--', 
                           label=f'Threshold ({results[0]["threshold"]})')
                ax3.set_xlabel('Time (seconds)')
                ax3.set_ylabel('Speech Probability')
                ax3.set_title(f'VAD Probability Over Time (Threshold: {results[0]["threshold"]})')
                ax3.legend()
                ax3.grid(True, alpha=0.3)
            
            # Plot 4: Summary statistics
            ax4.axis('off')
            summary_text = "Test Summary:\n\n"
            for result in results:
                summary_text += f"Threshold {result['threshold']:.2f}:\n"
                summary_text += f"  Speech: {result['speech_chunks']} chunks\n"
                summary_text += f"  Silence: {result['silence_chunks']} chunks\n"
                summary_text += f"  Speech %: {result['speech_percentage']:.1f}%\n\n"
            
            ax4.text(0.1, 0.9, summary_text, transform=ax4.transAxes, 
                    fontsize=10, verticalalignment='top', fontfamily='monospace')
            
            plt.tight_layout()
            
            if save_plot:
                plot_path = f"silero_vad_test_{int(time.time())}.png"
                plt.savefig(plot_path, dpi=300, bbox_inches='tight')
                self.logger.info(f"📊 Plot saved to: {plot_path}")
            
            plt.show()
            
        except ImportError:
            self.logger.warning("matplotlib not available. Install with: pip install matplotlib")
        except Exception as e:
            self.logger.error(f"Error creating visualization: {e}")
    
    def print_recommendations(self, results: list):
        """Print recommendations based on test results."""
        if not results:
            return
        
        self.logger.info("\n" + "="*60)
        self.logger.info("🎯 VAD THRESHOLD RECOMMENDATIONS")
        self.logger.info("="*60)
        
        # Find optimal threshold (closest to 50% speech)
        optimal_result = min(results, key=lambda x: abs(x['speech_percentage'] - 50))
        
        self.logger.info(f"🎯 Recommended threshold: {optimal_result['threshold']:.2f}")
        self.logger.info(f"   Speech percentage: {optimal_result['speech_percentage']:.1f}%")
        self.logger.info(f"   Speech chunks: {optimal_result['speech_chunks']}")
        self.logger.info(f"   Silence chunks: {optimal_result['silence_chunks']}")
        
        self.logger.info("\n📋 Threshold Analysis:")
        for result in results:
            status = "✅" if 30 <= result['speech_percentage'] <= 70 else "⚠️"
            self.logger.info(f"   {status} {result['threshold']:.2f}: {result['speech_percentage']:.1f}% speech")
        
        self.logger.info("\n💡 Tips:")
        self.logger.info("   - Aim for 30-70% speech percentage for balanced detection")
        self.logger.info("   - Lower thresholds = more sensitive (detects more speech)")
        self.logger.info("   - Higher thresholds = less sensitive (fewer false positives)")
        self.logger.info("   - Test in your actual usage environment for best results")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Test Silero VAD with microphone")
    parser.add_argument("--duration", type=float, default=10.0,
                       help="Test duration in seconds per sensitivity level")
    parser.add_argument("--sensitivity", type=float, default=0.5,
                       help="Single VAD threshold to test (0.0-1.0)")
    parser.add_argument("--test-sensitivity", action="store_true",
                       help="Test multiple sensitivity levels")
    parser.add_argument("--sensitivities", nargs="+", type=float,
                       default=[0.1, 0.3, 0.5, 0.7, 0.9],
                       help="List of sensitivities to test")
    parser.add_argument("--visualize", action="store_true",
                       help="Show visualization of results")
    parser.add_argument("--save-plot", action="store_true",
                       help="Save plot to file")
    parser.add_argument("--device", default="cpu",
                       help="Device to run VAD on (cpu/cuda)")
    parser.add_argument("--sample-rate", type=int, default=16000,
                       help="Audio sample rate")
    parser.add_argument("--chunk-size", type=int, default=512,
                       help="Audio chunk size (512 for 16kHz, 256 for 8kHz)")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Create VAD tester
    tester = SileroVADTester(
        sample_rate=args.sample_rate,
        chunk_size=args.chunk_size,
        device=args.device
    )
    
    # Load Silero VAD model
    if not tester.load_silero_vad():
        sys.exit(1)
    
    try:
        if args.test_sensitivity:
            # Test multiple sensitivities
            results = tester.test_multiple_sensitivities(
                args.sensitivities, 
                args.duration
            )
            
            # Print recommendations
            tester.print_recommendations(results)
            
            # Visualize if requested
            if args.visualize:
                tester.visualize_results(results, args.save_plot)
        else:
            # Test single sensitivity
            result = tester.test_single_sensitivity(args.sensitivity, args.duration)
            
            if args.visualize:
                tester.visualize_results([result], args.save_plot)
    
    except KeyboardInterrupt:
        tester.stop_recording()
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        logging.error(f"Error during test: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 