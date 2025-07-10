# Real-time VAD Visualization

This feature allows you to visualize Voice Activity Detection (VAD) in real-time using your microphone. You can see your voice levels, VAD confidence scores, and speech start/stop events as they happen.

## Features

- **Real-time microphone input**: Captures audio from your microphone continuously
- **Live visualization**: Shows audio levels and VAD confidence in real-time
- **Speech event detection**: Highlights when speech starts and stops
- **Configurable threshold**: Adjust the VAD sensitivity
- **Event logging**: Prints speech start/stop events with timestamps
- **Summary statistics**: Shows VAD performance metrics when you stop

## Requirements

### Dependencies
- `matplotlib` - For real-time plotting
- `sounddevice` - For microphone input
- `numpy` - For audio processing
- `silero-vad` - For voice activity detection

### Installation
```bash
# Install required packages
pip install matplotlib sounddevice

# The project should already have silero-vad installed
```

## Usage

### 1. Test Setup (Recommended)
First, run the setup test to verify everything is working:

```bash
python scripts/test_vad_visualization.py
```

This will check:
- All required imports
- VAD configuration
- Audio device detection
- Matplotlib setup

### 2. Run Real-time VAD Test

```bash
# Basic usage with default threshold (0.5)
python scripts/test_local_vad_bridge.py

# Custom threshold (lower = more sensitive)
python scripts/test_local_vad_bridge.py --threshold 0.3

# Higher threshold (less sensitive)
python scripts/test_local_vad_bridge.py --threshold 0.7
```

### 3. Using the Visualization

When you run the script:

1. **A matplotlib window will open** showing two plots:
   - **Top plot**: Audio level over time
   - **Bottom plot**: VAD confidence over time

2. **Speak into your microphone** and watch:
   - The audio level plot shows your voice amplitude
   - The VAD confidence plot shows speech detection probability
   - Green vertical lines mark speech start events
   - Red vertical lines mark speech stop events
   - The background color indicates current speech state

3. **Console output** shows:
   - Real-time speech start/stop events with timestamps
   - VAD confidence scores for each event

4. **Press Ctrl+C** to stop recording and see a summary

## Understanding the Visualization

### Audio Level Plot
- **Blue line**: Your voice amplitude (RMS level)
- **Red dashed line**: VAD threshold
- **Y-axis**: Amplitude from -1 to 1
- **X-axis**: Time in seconds

### VAD Confidence Plot
- **Green line**: VAD confidence score (0-1)
- **Red dashed line**: VAD threshold
- **Green background**: Speech is currently active
- **Red background**: No speech detected
- **Vertical lines**: Speech start (green) and stop (red) events

### Threshold Adjustment

- **Lower threshold (0.1-0.3)**: More sensitive, detects quiet speech
- **Medium threshold (0.4-0.6)**: Balanced detection
- **Higher threshold (0.7-0.9)**: Less sensitive, only detects loud speech

## Troubleshooting

### No Audio Input
- Check your microphone is connected and working
- Verify microphone permissions in your OS
- Try running the setup test first

### No Visualization
- Ensure matplotlib is installed: `pip install matplotlib`
- Check if you have a display available (for headless systems)
- Try running the setup test

### Poor VAD Performance
- Adjust the threshold value
- Speak clearly and at a consistent volume
- Reduce background noise
- Check microphone quality

### Performance Issues
- Reduce chunk size in the script if needed
- Close other audio applications
- Check CPU usage during recording

## Technical Details

### Audio Processing
- **Sample rate**: 16kHz
- **Chunk size**: 1024 samples (~64ms)
- **Format**: 16-bit PCM
- **Channels**: Mono

### VAD Configuration
- **Backend**: Silero VAD
- **Model**: Pre-trained neural network
- **Device**: CPU (configurable)
- **Chunk size**: 512 samples for VAD processing

### Visualization Updates
- **Update rate**: ~15 FPS
- **Buffer size**: 1000 samples
- **Time window**: Rolling 10-second view

## Examples

### Testing Different Thresholds

```bash
# Very sensitive - detects quiet speech
python scripts/test_local_vad_bridge.py --threshold 0.2

# Balanced - good for normal conversation
python scripts/test_local_vad_bridge.py --threshold 0.5

# Less sensitive - only loud speech
python scripts/test_local_vad_bridge.py --threshold 0.8
```

### Typical Output
```
🎤 Real-time VAD Test with Microphone Input
Threshold: 0.5
Speak into your microphone to see VAD events in real-time!
Press Ctrl+C to stop

🎤 Started recording from microphone
Press Ctrl+C to stop
🎤 Speech STARTED at 2.34s (confidence: 0.892)
🔇 Speech STOPPED at 4.67s (confidence: 0.234)
🎤 Speech STARTED at 6.12s (confidence: 0.756)
...

Stopping...

==================================================
VAD TEST SUMMARY
==================================================
Total VAD events: 8
Speech starts: 4
Speech stops: 4
Average VAD confidence: 0.623
Maximum VAD confidence: 0.892
==================================================
```

## Integration with FastAgent

This visualization tool uses the same VAD system as the main FastAgent application, so the results you see here will be similar to what happens during actual calls. This makes it useful for:

- **Testing VAD sensitivity** before deployment
- **Debugging speech detection issues**
- **Optimizing threshold values** for your environment
- **Understanding VAD behavior** with different speakers and conditions 