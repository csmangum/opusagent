# PocketSphinx Transcription Scripts

This directory contains scripts for transcribing audio files using PocketSphinx, specifically designed for the audio files in `opusagent/mock/audio/card_replacement/`.

## 📋 Prerequisites

1. **Python Dependencies**: Ensure you have the required packages installed:
   ```bash
   pip install pocketsphinx==0.1.18
   ```

2. **Audio Files**: The scripts are designed to work with the WAV files in:
   ```
   opusagent/mock/audio/card_replacement/
   ├── card_replacement_01.wav
   ├── card_replacement_02.wav
   ├── ...
   └── card_replacement_10.wav
   ```

## 🚀 Quick Start

### Basic Usage

1. **Transcribe a single file**:
   ```bash
   python scripts/transcribe_with_pocketsphinx.py opusagent/mock/audio/card_replacement/card_replacement_01.wav
   ```

2. **Transcribe entire directory**:
   ```bash
   python scripts/transcribe_with_pocketsphinx.py opusagent/mock/audio/card_replacement/
   ```

3. **Save results to JSON file**:
   ```bash
   python scripts/transcribe_with_pocketsphinx.py opusagent/mock/audio/card_replacement/ --output transcriptions.json
   ```

4. **Run the example script**:
   ```bash
   python scripts/example_pocketsphinx_transcription.py
   ```

## 📁 Scripts Overview

### `transcribe_with_pocketsphinx.py`

The main transcription script with the following features:

- **Single file transcription**: Process one audio file at a time
- **Batch directory processing**: Transcribe all audio files in a directory
- **Custom model support**: Use custom language models, dictionaries, and acoustic models
- **JSON output**: Save results in structured JSON format
- **Confidence scoring**: Get confidence scores for each transcription
- **Detailed logging**: Comprehensive logging for debugging

#### Command Line Options

```bash
python transcribe_with_pocketsphinx.py [input_path] [options]

Arguments:
  input_path              Path to audio file or directory to transcribe

Options:
  --output, -o            Output file to save results (JSON format)
  --language-model, -lm   Path to custom language model file
  --dictionary, -dict     Path to custom dictionary file
  --acoustic-model, -hmm  Path to custom acoustic model directory
  --verbose, -v           Enable verbose output
```

### `example_pocketsphinx_transcription.py`

A demonstration script that shows how to use the transcription functionality programmatically.

## 🔧 Advanced Usage

### Using Custom Models

PocketSphinx supports custom language models, dictionaries, and acoustic models for improved accuracy:

```bash
python transcribe_with_pocketsphinx.py audio_file.wav \
    --language-model /path/to/custom.lm \
    --dictionary /path/to/custom.dict \
    --acoustic-model /path/to/acoustic_model/
```

### Programmatic Usage

```python
from scripts.transcribe_with_pocketsphinx import PocketSphinxTranscriber

# Initialize transcriber
transcriber = PocketSphinxTranscriber()

# Transcribe single file
result = transcriber.transcribe_file("audio_file.wav")
print(f"Transcription: {result['transcription']}")
print(f"Confidence: {result['confidence']}")

# Transcribe directory
results = transcriber.transcribe_directory(
    directory_path="audio_directory/",
    output_file="results.json"
)
```

## 📊 Output Format

The scripts output results in JSON format with the following structure:

```json
[
  {
    "file_path": "path/to/audio_file.wav",
    "transcription": "transcribed text content",
    "confidence": 0.85,
    "segments": [
      {
        "word": "hello",
        "start": 0.0,
        "end": 0.5,
        "prob": 0.9
      }
    ],
    "success": true
  }
]
```

### Output Fields

- **file_path**: Path to the processed audio file
- **transcription**: The transcribed text
- **confidence**: Overall confidence score (0.0 to 1.0)
- **segments**: Detailed word-level timing and confidence (if available)
- **success**: Boolean indicating if transcription was successful
- **error**: Error message (if success is false)

## 🎯 Use Cases

### 1. Quality Assessment
Use transcriptions to assess the quality and clarity of your audio files:

```bash
python transcribe_with_pocketsphinx.py opusagent/mock/audio/card_replacement/ \
    --output quality_assessment.json
```

### 2. Content Analysis
Analyze the content of your audio files to ensure they contain the expected phrases:

```python
import json

with open("quality_assessment.json", "r") as f:
    results = json.load(f)

for result in results:
    if "card" in result["transcription"].lower():
        print(f"Card-related content found in: {result['file_path']}")
```

### 3. Training Data Preparation
Use transcriptions to prepare training data for other speech recognition systems:

```python
# Extract high-confidence transcriptions
high_confidence_results = [
    r for r in results 
    if r["success"] and r["confidence"] > 0.8
]
```

## 🛠️ Troubleshooting

### Common Issues

1. **Import Error**: If you get an import error for PocketSphinx:
   ```bash
   pip install pocketsphinx==0.1.18
   ```

2. **Audio Format Issues**: Ensure your audio files are in supported formats:
   - WAV (recommended)
   - MP3
   - FLAC
   - M4A
   - OGG

3. **Low Confidence Scores**: This is normal for PocketSphinx, especially with:
   - Background noise
   - Multiple speakers
   - Unusual accents
   - Technical vocabulary

### Improving Accuracy

1. **Use Custom Models**: Train or download domain-specific models
2. **Audio Preprocessing**: Clean audio files before transcription
3. **Multiple Passes**: Run transcription multiple times with different settings
4. **Manual Review**: Always review low-confidence transcriptions

## 📈 Performance Notes

- **Speed**: PocketSphinx is fast but less accurate than cloud-based solutions
- **Accuracy**: Expect 60-80% accuracy for clear speech in quiet environments
- **Resource Usage**: Low CPU and memory requirements
- **Offline**: Works completely offline, no internet required

## 🔗 Related Files

- `opusagent/mock/audio/card_replacement/` - Audio files to transcribe
- `requirements.txt` - Project dependencies including PocketSphinx
- `scripts/generate_mock_audio.py` - Script that generated the audio files 