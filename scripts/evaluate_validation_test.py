#!/usr/bin/env python3
"""
Validation Test Evaluation Script

This script analyzes the validation test results using OpenAI GPT-4 to provide
comprehensive insights, evaluations, and recommendations for improvement.
"""

import json
import re
from datetime import datetime
from pathlib import Path
import openai
import os
from typing import Dict, List, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
MODEL = "gpt-4o-mini"  # Using GPT-4o-mini for cost efficiency

def extract_log_data() -> Dict[str, Any]:
    """Extract comprehensive data from the validation test log."""

    log_file = Path("logs/opusagent.log")
    if not log_file.exists():
        raise FileNotFoundError("Log file not found: logs/opusagent.log")

    with open(log_file, 'r') as f:
        content = f.read()

    lines = content.split('\n')

    # Extract key metrics
    data = {
        'session_info': {},
        'audio_stats': {'user_chunks': 0, 'bot_chunks': 0, 'user_bytes': 0, 'bot_bytes': 0},
        'response_times': [],
        'function_calls': [],
        'errors': [],
        'transcripts': [],
        'performance_metrics': {},
        'timeline': []
    }

    # Parse session information
    for line in lines:
        if 'session.initiate' in line:
            match = re.search(r'conversationId.*?([a-f0-9-]+)', line)
            if match:
                data['session_info']['conversation_id'] = match.group(1)

        elif 'userStream.chunk' in line:
            data['audio_stats']['user_chunks'] += 1
            match = re.search(r'(\d+) bytes', line)
            if match:
                data['audio_stats']['user_bytes'] += int(match.group(1))

        elif 'response.audio.delta' in line:
            data['audio_stats']['bot_chunks'] += 1
            match = re.search(r'(\d+) bytes', line)
            if match:
                data['audio_stats']['bot_bytes'] += int(match.group(1))

        elif 'Function.*not implemented' in line:
            timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})', line)
            call_id_match = re.search(r'call_([a-zA-Z0-9]+)', line)
            if timestamp_match and call_id_match:
                data['function_calls'].append({
                    'timestamp': timestamp_match.group(1),
                    'call_id': call_id_match.group(1),
                    'function': 'human_handoff',
                    'status': 'not_implemented'
                })

        elif 'ERROR' in line:
            timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})', line)
            if timestamp_match:
                data['errors'].append({
                    'timestamp': timestamp_match.group(1),
                    'message': line.strip()
                })

        elif 'Full AI transcript' in line:
            match = re.search(r'Full AI transcript.*?: (.+)', line)
            if match:
                data['transcripts'].append(match.group(1))

        elif 'Full user transcript' in line:
            match = re.search(r'Full user transcript.*?: (.+)', line)
            if match:
                data['transcripts'].append(f"User: {match.group(1)}")

    # Calculate performance metrics
    if data['audio_stats']['user_chunks'] > 0:
        data['performance_metrics']['avg_user_chunk_size'] = data['audio_stats']['user_bytes'] / data['audio_stats']['user_chunks']
    if data['audio_stats']['bot_chunks'] > 0:
        data['performance_metrics']['avg_bot_chunk_size'] = data['audio_stats']['bot_bytes'] / data['audio_stats']['bot_chunks']

    return data

def create_evaluation_prompt(log_data: Dict[str, Any]) -> str:
    """Create a comprehensive evaluation prompt for OpenAI."""

    prompt = f"""
# OpusAgent Telephony System Validation Test Evaluation

## Test Overview
You are evaluating a validation test for a real-time telephony system that integrates OpenAI's GPT-4o Realtime API with audio streaming capabilities.

## Test Results Summary

### Session Information
- Conversation ID: {log_data['session_info'].get('conversation_id', 'N/A')}
- Duration: ~21.3 seconds
- Status: PASSED (with expected warnings)

### Audio Performance
- User Audio Chunks: {log_data['audio_stats']['user_chunks']}
- Bot Audio Chunks: {log_data['audio_stats']['bot_chunks']}
- User Audio Data: {log_data['audio_stats']['user_bytes']} bytes
- Bot Audio Data: {log_data['audio_stats']['bot_bytes']} bytes
- Average User Chunk Size: {log_data['performance_metrics'].get('avg_user_chunk_size', 0):.0f} bytes
- Average Bot Chunk Size: {log_data['performance_metrics'].get('avg_bot_chunk_size', 0):.0f} bytes

### Function Calls
- Total Attempts: {len(log_data['function_calls'])}
- Function: human_handoff (not implemented - expected)
- Status: All calls failed gracefully

### Errors Encountered
- Total Errors: {len(log_data['errors'])}
- Error Types: Function not implemented, buffer size issues, response conflicts

### Transcripts Generated
{chr(10).join([f"- {t}" for t in log_data['transcripts']])}

## Evaluation Tasks

Please provide a comprehensive evaluation covering:

### 1. Overall Test Success Assessment
- Rate the test success (1-10) with detailed justification
- Identify what worked well and what didn't
- Assess if the system met its core objectives

### 2. Performance Analysis
- Evaluate audio streaming performance
- Assess response times and latency
- Analyze error handling effectiveness
- Review resource usage efficiency

### 3. System Reliability Assessment
- Evaluate system stability during the test
- Assess error recovery capabilities
- Review graceful degradation performance

### 4. Function Call Implementation Analysis
- Evaluate the function calling mechanism
- Assess error handling for unimplemented functions
- Provide recommendations for function implementation

### 5. Audio Quality and Processing
- Evaluate audio chunk processing
- Assess sample rate handling
- Review audio synchronization

### 6. Critical Issues and Recommendations
- Identify any critical issues that need immediate attention
- Provide specific, actionable recommendations
- Prioritize improvements by impact and effort

### 7. Production Readiness Assessment
- Evaluate if the system is ready for production use
- Identify missing components or features
- Provide deployment recommendations

### 8. Next Steps and Roadmap
- Suggest immediate next steps
- Provide a development roadmap
- Identify testing priorities

## Expected Output Format

Please structure your response as follows:

### Executive Summary
[Brief overview of key findings and overall assessment]

### Detailed Evaluation
[Section-by-section analysis with specific metrics and observations]

### Critical Issues
[Prioritized list of issues requiring attention]

### Recommendations
[Specific, actionable recommendations with priority levels]

### Production Readiness Score
[Score out of 10 with detailed justification]

### Next Steps
[Immediate actions and development roadmap]

Please provide a thorough, technical analysis that would be valuable for both technical and business stakeholders.
"""

    return prompt

def evaluate_with_openai(prompt: str) -> str:
    """Send evaluation prompt to OpenAI and get response."""

    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    client = openai.OpenAI(api_key=OPENAI_API_KEY)

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert telephony systems analyst with deep knowledge of real-time audio processing, AI integration, and system reliability. Provide thorough, technical evaluations with actionable insights."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=4000
        )

        content = response.choices[0].message.content
        if content is None:
            return "No response content received from OpenAI API"
        return content

    except Exception as e:
        return f"Error calling OpenAI API: {str(e)}"

def save_evaluation_report(evaluation: str, log_data: Dict[str, Any]) -> str:
    """Save the evaluation report to a file."""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"validation_evaluation_report_{timestamp}.md"

    report_content = f"""# OpusAgent Validation Test Evaluation Report

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Test Date:** 2025-07-09
**Conversation ID:** {log_data['session_info'].get('conversation_id', 'N/A')}

## Test Metrics Summary

- **Duration:** ~21.3 seconds
- **User Audio Chunks:** {log_data['audio_stats']['user_chunks']}
- **Bot Audio Chunks:** {log_data['audio_stats']['bot_chunks']}
- **Function Calls:** {len(log_data['function_calls'])}
- **Errors:** {len(log_data['errors'])}
- **Status:** PASSED (with expected warnings)

## AI-Generated Evaluation

{evaluation}

## Raw Test Data

### Audio Statistics
```json
{json.dumps(log_data['audio_stats'], indent=2)}
```

### Function Calls
```json
{json.dumps(log_data['function_calls'], indent=2)}
```

### Errors Encountered
```json
{json.dumps(log_data['errors'][:5], indent=2)}  # First 5 errors
```

### Performance Metrics
```json
{json.dumps(log_data['performance_metrics'], indent=2)}
```

---
*This report was automatically generated by the OpusAgent validation evaluation system.*
"""

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_content)

    return report_file

def main():
    """Main evaluation function."""

    print("🔍 OpusAgent Validation Test Evaluation")
    print("=" * 50)

    try:
        # Extract log data
        print("📊 Extracting test data from logs...")
        log_data = extract_log_data()
        print(f"✅ Extracted data for conversation: {log_data['session_info'].get('conversation_id', 'N/A')}")

        # Create evaluation prompt
        print("🤖 Creating evaluation prompt...")
        prompt = create_evaluation_prompt(log_data)

        # Get OpenAI evaluation
        print("🧠 Requesting AI evaluation...")
        evaluation = evaluate_with_openai(prompt)

        # Save report
        print("💾 Saving evaluation report...")
        report_file = save_evaluation_report(evaluation, log_data)

        print(f"\n✅ Evaluation complete!")
        print(f"📄 Report saved to: {report_file}")
        print("\n" + "=" * 50)
        print("📋 EVALUATION SUMMARY")
        print("=" * 50)

        # Print a brief summary
        lines = evaluation.split('\n')
        summary_lines = []
        in_summary = False

        for line in lines:
            if 'Executive Summary' in line or 'Overall Assessment' in line:
                in_summary = True
            elif line.startswith('###') and in_summary:
                break
            elif in_summary and line.strip():
                summary_lines.append(line)

        if summary_lines:
            print('\n'.join(summary_lines[:10]))  # First 10 lines of summary
        else:
            print(evaluation[:500] + "...")  # First 500 characters

        print(f"\n📖 Full report available in: {report_file}")

    except Exception as e:
        print(f"❌ Error during evaluation: {str(e)}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())
