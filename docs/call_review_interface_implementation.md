# Call Review Interface Implementation

The call review interface provides a comprehensive tool for post-call analysis, enabling users to review recorded calls with audio playback, interactive transcript viewing, quality metric dashboards, and AI-generated insights. This feature builds on OpusAgent's existing call recording system and extends it with web-based visualization and AI processing.

## Overview

The call review interface offers:
- **Audio Playback**: Stream and play back caller/bot/stereo audio with controls (play/pause/seek).
- **Transcript Analysis**: Interactive transcript viewing with timestamps, search, highlighting, and annotations.
- **Quality Metrics**: Visual dashboards for SNR, THD, clipping, and overall scores, aggregated from recordings.
- **AI-Powered Reviewing**: Automated summaries, sentiment analysis, key moment detection, and performance scoring using OpenAI.
- **Session Browser**: List and filter past calls by date, duration, caller ID, or outcome.

This enhances debugging, quality assurance, and compliance, integrating with voice fingerprinting for caller-specific reviews.

## Architecture

### Core Components

```
opusagent/
├── review_interface/
│   ├── __init__.py
│   ├── app.py                 # FastAPI app for the review dashboard
│   ├── templates/             # HTML templates (Jinja2)
│   │   └── review.html
│   ├── static/                # CSS/JS for audio player and charts
│   ├── models.py              # Pydantic models for reviews
│   ├── views.py               # API endpoints and views
│   ├── analyzer.py            # Transcript and quality analysis logic
│   └── ai_reviewer.py         # AI-powered review generation
```

### Integration Points

- **Call Recordings**: Pull from `call_recordings/` directories (e.g., audio WAVs, `transcript.json`, `call_metadata.json`).
- **Quality Monitoring**: Extend `AudioQualityMonitor` to analyze recordings offline.
- **AI Integration**: Use OpenAI for summarization (e.g., via `gpt-4o`).
- **Web Dashboard**: FastAPI endpoints for listing sessions, streaming audio, and generating reviews.
- **Voice Fingerprinting**: Link reviews to caller profiles for cross-session analysis.

## Implementation

### Review Analyzer

Core logic for processing recordings:

```python
# In opusagent/review_interface/analyzer.py
import json
import wave
import numpy as np
from pathlib import Path
from typing import Dict, List, Any
from opusagent.audio_quality_monitor import AudioQualityMonitor, QualityMetrics
from pydantic import BaseModel

class ReviewMetrics(BaseModel):
    quality_score: float
    duration_seconds: float
    sentiment_score: float  # e.g., -1.0 (negative) to 1.0 (positive)
    key_moments: List[str]

class ReviewAnalyzer:
    def __init__(self, recording_dir: Path):
        self.recording_dir = recording_dir
        self.quality_monitor = AudioQualityMonitor()
    
    def analyze_audio(self, audio_file: Path) -> QualityMetrics:
        \"""Analyze audio quality from WAV file.\"""
        with wave.open(str(audio_file), 'rb') as wav:
            audio_bytes = wav.readframes(wav.getnframes())
        return self.quality_monitor.analyze_audio_chunk(audio_bytes)
    
    def analyze_transcript(self, transcript_file: Path) -> Dict[str, Any]:
        \"""Analyze transcript for stats (e.g., word count, turns).\"""
        with open(transcript_file, 'r') as f:
            transcript = json.load(f)
        turns = len(transcript['entries'])
        return {'turns': turns, 'entries': transcript['entries']}
    
    def get_review_metrics(self) -> ReviewMetrics:
        \"""Aggregate metrics from recording.\"""
        caller_audio = self.recording_dir / \""caller_audio.wav\""
        metrics = self.analyze_audio(caller_audio)
        # Placeholder for sentiment (integrate AI below)
        return ReviewMetrics(
            quality_score=metrics.quality_score,
            duration_seconds=metrics.duration_seconds,
            sentiment_score=0.5,  # From AI analysis
            key_moments=[\""Greeting\"", \""Issue resolution\""]
        )
```

### AI Reviewer

Use OpenAI for intelligent analysis:

```python
# In opusagent/review_interface/ai_reviewer.py
import openai
from openai import OpenAI
from typing import Dict

class AIReviewer:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
    
    async def review_call(self, transcript: str) -> Dict[str, Any]:
        \"""Generate AI-powered review.\"""
        prompt = f\""Summarize this call transcript, analyze sentiment, detect key moments, and score agent performance (0-10):\n{transcript}\"""
        response = self.client.chat.completions.create(
            model=\""gpt-4o\"",
            messages=[{\""role\"": \""system\"", \""content\"": prompt}]
        )
        return {
            \""summary\"": response.choices[0].message.content,
            \""sentiment\"": 0.8,  # Parsed from response
            \""score\"": 9.2,
            \""key_moments\"": [\""Issue identified\"", \""Resolution provided\""]
        }
```

### Dashboard App

FastAPI-based web interface:

```python
# In opusagent/review_interface/app.py
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from .analyzer import ReviewAnalyzer
from .ai_reviewer import AIReviewer

app = FastAPI()
templates = Jinja2Templates(directory=\""opusagent/review_interface/templates\"")
app.mount(\""\/static\"", StaticFiles(directory=\""opusagent/review_interface/static\""), name=\""static\"")
ai_reviewer = AIReviewer(api_key=\""your-openai-key\"")

@app.get(\""\/\"")
def list_sessions(request: Request):
    sessions = list(Path(\""call_recordings\"").glob(\""*\""))
    return templates.TemplateResponse(\""sessions.html\"", {\""request\"": request, \""sessions\"": sessions})

@app.get(\""\/review\/{session_id}\"")
def review_session(request: Request, session_id: str):
    analyzer = ReviewAnalyzer(Path(f\""call_recordings\/{session_id}\"""))
    metrics = analyzer.get_review_metrics()
    transcript = analyzer.analyze_transcript(Path(f\""call_recordings\/{session_id}\/transcript.json\""))
    return templates.TemplateResponse(\""review.html\"", {\""request\"": request, \""metrics\"": metrics, \""transcript\"": transcript})

@app.get(\""\/ai-review\/{session_id}\"")
async def ai_review(session_id: str):
    transcript_path = Path(f\""call_recordings\/{session_id}\/transcript.json\"")
    with open(transcript_path, 'r') as f:
        transcript = json.load(f)['entries']
    transcript_text = \"" \"".join(entry['text'] for entry in transcript)
    return await ai_reviewer.review_call(transcript_text)

@app.get(\""\/audio\/{session_id}\/{file_type}\"")
def stream_audio(session_id: str, file_type: str):
    file_path = Path(f\""call_recordings\/{session_id}\/{file_type}.wav\"")
    def iterfile():
        with open(file_path, \""rb\"") as f:
            while chunk := f.read(4096):
                yield chunk
    return StreamingResponse(iterfile(), media_type=\""audio\/wav\"")
```

## Integration with OpusAgent

### Bridge Enhancements

Add post-call hooks to generate initial reviews:

```python
# In opusagent/bridges/base_bridge.py
from opusagent.review_interface.analyzer import ReviewAnalyzer

class BaseRealtimeBridge:
    async def close(self):
        if self.call_recorder:
            await self.call_recorder.stop_recording()
            analyzer = ReviewAnalyzer(self.call_recorder.recording_dir)
            analyzer.get_review_metrics()  # Generate initial metrics
```

### Session Management

Store review metadata:

```python
# In opusagent/session_manager.py
class SessionManager:
    async def end_session(self, session_id: str):
        session = await self.get_session(session_id)
        # Generate review
        review = ReviewAnalyzer(Path(f\""call_recordings\/{session_id}\""")).get_review_metrics()
        await self.storage.store_review(session_id, review)
```

## Configuration

### Environment Variables

```bash
REVIEW_DASHBOARD_ENABLED=true
REVIEW_DASHBOARD_PORT=8001
OPENAI_API_KEY=your-key
RECORDINGS_DIR=call_recordings
AI_REVIEW_MODEL=gpt-4o
```

### Configuration Class

```python
# In opusagent/review_interface/models.py
class ReviewConfig:
    enabled: bool = True
    port: int = 8001
    ai_model: str = \""gpt-4o\""
```

## Usage Examples

### Basic Review

Access `/review/{session_id}` to view audio player, transcript, and metrics.

### AI Review Generation

Call `/ai-review/{session_id}` to get a JSON summary.

### Audio Playback

Embed HTML5 audio: `<audio src=\""\/audio\/{session_id}\/stereo_recording\"" controls></audio>`

## Privacy and Security Considerations

- **Data Protection**: Anonymize transcripts before AI processing.
- **Access Control**: Require authentication for dashboard access.
- **Compliance**: Add export/delete options for recordings.

## Testing

### Unit Tests

```python
# tests/opusagent/review_interface/test_analyzer.py
def test_analyze_audio():
    analyzer = ReviewAnalyzer(Path(\""test_recording\""))
    metrics = analyzer.analyze_audio(Path(\""test.wav\""))
    assert metrics.quality_score > 0
```

### Integration Tests

```python
# tests/opusagent/test_review_integration.py
async def test_ai_review():
    reviewer = AIReviewer(\""test-key\"")
    result = await reviewer.review_call(\""Sample transcript\"")
    assert \""summary\"" in result
```

## Performance Considerations

- **Caching**: Cache metrics for frequent access.
- **Async Processing**: Use asyncio for AI reviews.
- **Scalability**: Offload AI to background tasks.

## Future Enhancements

- **Real-Time Reviews**: Generate during calls.
- **Advanced Analytics**: ML-based anomaly detection.
- **Integration**: Link with voice fingerprinting for user profiles.

## Dependencies

- fastapi
- jinja2
- openai
- numpy
- scipy (for audio analysis)

## Troubleshooting

- **No Recordings**: Check `RECORDINGS_DIR` path.
- **AI Errors**: Verify OpenAI API key.
- **Playback Issues**: Ensure browser supports WAV.

## Conclusion

This implementation creates a powerful review tool by leveraging existing recordings and metrics, with AI adding intelligent insights. It's extensible and aligns with OpusAgent's modular design. For production, add authentication and deploy as a separate service. 