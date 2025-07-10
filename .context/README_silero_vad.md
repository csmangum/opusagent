# Silero VAD Test Script

This directory contains scripts to test Silero VAD (Voice Activity Detection) with your microphone.

## What is Silero VAD?

Silero VAD is a pre-trained enterprise-grade Voice Activity Detector that can accurately detect speech in audio streams. It's fast, lightweight, and works well with various audio qualities and background noise levels.

**Key Features:**
- Stellar accuracy on speech detection tasks
- Fast processing (< 1ms per audio chunk)
- Lightweight (~2MB model size)
- Supports 8000 Hz and 16000 Hz sampling rates
- Works on CPU and GPU
- No strings attached (MIT license)

## Installation

### Option 1: Automatic Setup (Recommended)

Run the setup script to automatically install all dependencies:

```bash
python scripts/setup_silero_vad.py
```

### Option 2: Manual Installation

1. Install core dependencies:
```bash
pip install torch torchaudio numpy sounddevice matplotlib
```

2. Install Silero VAD:
```bash
pip install silero-vad
```

Or from GitHub:
```bash
pip install git+https://github.com/snakers4/silero-vad.git
```

## Usage

### Basic Test

Test Silero VAD with a single sensitivity threshold:

```bash
python scripts/test_silero_vad.py --duration 10 --sensitivity 0.5
```

### Multiple Sensitivity Test

Test different sensitivity levels and get recommendations:

```bash
python scripts/test_silero_vad.py --test-sensitivity --duration 10
```

### With Visualization

Test with real-time visualization of results:

```bash
python scripts/test_silero_vad.py --test-sensitivity --visualize
```

### Save Results

Save the visualization plot to a file:

```bash
python scripts/test_silero_vad.py --test-sensitivity --visualize --save-plot
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--duration` | Test duration in seconds per sensitivity level | 10.0 |
| `--sensitivity` | Single VAD threshold to test (0.0-1.0) | 0.5 |
| `--test-sensitivity` | Test multiple sensitivity levels | False |
| `--sensitivities` | List of sensitivities to test | [0.1, 0.3, 0.5, 0.7, 0.9] |
| `--visualize` | Show visualization of results | False |
| `--save-plot` | Save plot to file | False |
| `--device` | Device to run VAD on (cpu/cuda) | cpu |
| `--sample-rate` | Audio sample rate | 16000 |
| `--chunk-size` | Audio chunk size | 1024 |

## Understanding VAD Thresholds

The VAD threshold controls how sensitive the speech detection is:

- **Lower thresholds (0.1-0.3)**: More sensitive, detects more speech but may have false positives
- **Medium thresholds (0.4-0.6)**: Balanced detection, good for most use cases
- **Higher thresholds (0.7-0.9)**: Less sensitive, fewer false positives but may miss quiet speech

## Example Output

```
🎤 Silero VAD Test Script
==================================================
🔧 Testing sensitivity: 0.5
📝 Speak at different volumes for 10 seconds
🎤 Started recording from microphone
🔍 Processing audio with Silero VAD...
⏹️  Stopped recording
📊 Results for threshold 0.5:
   Speech chunks: 45
   Silence chunks: 55
   Speech percentage: 45.0%

🎯 VAD THRESHOLD RECOMMENDATIONS
============================================================
🎯 Recommended threshold: 0.50
   Speech percentage: 45.0%
   Speech chunks: 45
   Silence chunks: 55

📋 Threshold Analysis:
   ⚠️ 0.10: 78.5% speech
   ⚠️ 0.30: 62.3% speech
   ✅ 0.50: 45.0% speech
   ✅ 0.70: 28.7% speech
   ⚠️ 0.90: 12.1% speech
```

## Troubleshooting

### Common Issues

1. **"module 'silero_vad' has no attribute 'load_vad_model'"**
   - The API has changed. Use the updated script or reinstall Silero VAD.

2. **Audio device not found**
   - Make sure your microphone is connected and working.
   - Check system audio settings.

3. **Import errors**
   - Run the setup script: `python scripts/setup_silero_vad.py`
   - Or install manually: `pip install silero-vad`

4. **Poor VAD performance**
   - Try different sensitivity thresholds
   - Ensure good microphone quality
   - Test in a quiet environment first

### Performance Tips

- Use GPU if available: `--device cuda`
- Lower chunk sizes for faster response: `--chunk-size 512`
- Test in your actual usage environment for best results

## Integration with Your Project

The Silero VAD test script can be integrated into your existing audio processing pipeline. The `SileroVADTester` class provides methods for:

- Loading the VAD model
- Real-time speech detection
- Audio processing and analysis
- Result visualization

## Resources

- [Silero VAD GitHub Repository](https://github.com/snakers4/silero-vad)
- [Silero VAD Documentation](https://github.com/snakers4/silero-vad#readme)
- [PyTorch Documentation](https://pytorch.org/docs/)
- [SoundDevice Documentation](https://python-sounddevice.readthedocs.io/)

## License

This script is part of the FastAgent project and follows the same license terms. Silero VAD is licensed under MIT. 