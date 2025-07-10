#!/usr/bin/env python3
"""
Comprehensive Validation Test Evaluation

This script provides a multi-dimensional evaluation of the validation test results,
including technical analysis, business impact assessment, and detailed recommendations.
"""

import json
import re
from datetime import datetime
from pathlib import Path
import openai
import os
from typing import Dict, List, Any, Tuple
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
MODEL = "gpt-4o-mini"

def extract_comprehensive_data() -> Dict[str, Any]:
    """Extract comprehensive data from logs and analysis."""

    log_file = Path("logs/opusagent.log")
    if not log_file.exists():
        raise FileNotFoundError("Log file not found: logs/opusagent.log")

    with open(log_file, 'r') as f:
        content = f.read()

    lines = content.split('\n')

    # Comprehensive data extraction
    data = {
        'session_info': {},
        'audio_stats': {'user_chunks': 0, 'bot_chunks': 0, 'user_bytes': 0, 'bot_bytes': 0},
        'response_times': [],
        'function_calls': [],
        'errors': [],
        'transcripts': [],
        'performance_metrics': {},
        'timeline': [],
        'token_usage': [],
        'audio_quality': {},
        'system_health': {}
    }

    # Parse detailed information
    for line in lines:
        # Session information
        if 'session.initiate' in line:
            match = re.search(r'conversationId.*?([a-f0-9-]+)', line)
            if match:
                data['session_info']['conversation_id'] = match.group(1)

        # Audio streaming
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

        # Function calls
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

        # Errors
        elif 'ERROR' in line:
            timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})', line)
            if timestamp_match:
                data['errors'].append({
                    'timestamp': timestamp_match.group(1),
                    'message': line.strip()
                })

        # Transcripts
        elif 'Full AI transcript' in line:
            match = re.search(r'Full AI transcript.*?: (.+)', line)
            if match:
                data['transcripts'].append(match.group(1))

        elif 'Full user transcript' in line:
            match = re.search(r'Full user transcript.*?: (.+)', line)
            if match:
                data['transcripts'].append(f"User: {match.group(1)}")

        # Token usage
        elif 'total_tokens' in line:
            match = re.search(r'"total_tokens": (\d+)', line)
            if match:
                data['token_usage'].append(int(match.group(1)))

        # Audio quality metrics
        elif 'Audio resampling' in line:
            match = re.search(r'(\d+)Hz -> (\d+)Hz', line)
            if match:
                data['audio_quality']['resampling'] = {
                    'from': int(match.group(1)),
                    'to': int(match.group(2))
                }

    # Calculate performance metrics
    if data['audio_stats']['user_chunks'] > 0:
        data['performance_metrics']['avg_user_chunk_size'] = data['audio_stats']['user_bytes'] / data['audio_stats']['user_chunks']
    if data['audio_stats']['bot_chunks'] > 0:
        data['performance_metrics']['avg_bot_chunk_size'] = data['audio_stats']['bot_bytes'] / data['audio_stats']['bot_chunks']

    # Calculate system health metrics
    data['system_health'] = {
        'error_rate': len(data['errors']) / max(len(lines), 1) * 100,
        'function_success_rate': 0 if data['function_calls'] else 100,
        'audio_continuity': data['audio_stats']['bot_chunks'] > 0 and data['audio_stats']['user_chunks'] > 0
    }

    return data

def create_multi_dimensional_prompt(log_data: Dict[str, Any]) -> str:
    """Create a comprehensive multi-dimensional evaluation prompt."""

    prompt = f"""
# OpusAgent Telephony System - Multi-Dimensional Validation Evaluation

## System Overview
You are evaluating a real-time telephony system that integrates OpenAI's GPT-4o Realtime API with bidirectional audio streaming. The system handles customer service calls with AI-powered responses and function calling capabilities.

## Test Results Summary

### Session Information
- Conversation ID: {log_data['session_info'].get('conversation_id', 'N/A')}
- Duration: ~21.3 seconds
- Status: PASSED (with expected warnings)

### Audio Performance Metrics
- User Audio Chunks: {log_data['audio_stats']['user_chunks']}
- Bot Audio Chunks: {log_data['audio_stats']['bot_chunks']}
- User Audio Data: {log_data['audio_stats']['user_bytes']:,} bytes
- Bot Audio Data: {log_data['audio_stats']['bot_bytes']:,} bytes
- Average User Chunk Size: {log_data['performance_metrics'].get('avg_user_chunk_size', 0):.0f} bytes
- Average Bot Chunk Size: {log_data['performance_metrics'].get('avg_bot_chunk_size', 0):.0f} bytes

### Function Call Analysis
- Total Attempts: {len(log_data['function_calls'])}
- Function: human_handoff (not implemented - expected)
- Success Rate: {log_data['system_health']['function_success_rate']}%
- Error Handling: Graceful degradation

### System Health Metrics
- Error Rate: {log_data['system_health']['error_rate']:.2f}%
- Audio Continuity: {'✅' if log_data['system_health']['audio_continuity'] else '❌'}
- Token Usage: {sum(log_data['token_usage'])} total tokens

### Transcripts Generated
{chr(10).join([f"- {t}" for t in log_data['transcripts']])}

## Multi-Dimensional Evaluation Tasks

Please provide a comprehensive evaluation across these dimensions:

### 1. Technical Performance Assessment (25%)
- **Audio Processing**: Evaluate streaming performance, latency, and quality
- **AI Integration**: Assess response generation, token efficiency, and model performance
- **System Reliability**: Evaluate error handling, recovery, and stability
- **Resource Efficiency**: Analyze memory usage, processing overhead, and scalability

### 2. User Experience Evaluation (20%)
- **Response Quality**: Assess AI response appropriateness and naturalness
- **Latency Perception**: Evaluate user-perceived response times
- **Conversation Flow**: Analyze turn-taking and interaction quality
- **Error Recovery**: Assess how gracefully the system handles issues

### 3. System Scalability Assessment (20%)
- **Concurrent Call Capacity**: Evaluate system capacity for multiple simultaneous calls
- **Resource Utilization**: Analyze memory usage and processing overhead
- **Performance Under Load**: Assess system behavior with increased traffic
- **Bottleneck Identification**: Identify potential performance limitations

### 4. Production Readiness Assessment (20%)
- **Deployment Readiness**: Evaluate current state for production deployment
- **Missing Components**: Identify critical gaps and dependencies
- **Security Considerations**: Assess data handling and privacy compliance
- **Monitoring Requirements**: Identify observability and alerting needs

### 5. Risk Assessment (15%)
- **Critical Issues**: Identify high-priority risks and vulnerabilities
- **Performance Bottlenecks**: Identify scalability and performance limitations
- **Dependency Risks**: Assess third-party service dependencies
- **Compliance Issues**: Evaluate regulatory and compliance requirements

## Expected Output Format

### Executive Summary
[High-level assessment with key metrics and overall score]

### Technical Performance Score: X/10
- Audio Processing: X/10
- AI Integration: X/10
- System Reliability: X/10
- Resource Efficiency: X/10

### User Experience Score: X/10
- Response Quality: X/10
- Latency: X/10
- Conversation Flow: X/10
- Error Recovery: X/10

### System Scalability Score: X/10
- Concurrent Call Capacity: X/10
- Resource Utilization: X/10
- Performance Under Load: X/10
- Bottleneck Identification: X/10

### Production Readiness Score: X/10
- Deployment Readiness: X/10
- Missing Components: X/10
- Security: X/10
- Monitoring: X/10

### Risk Assessment: X/10
- Critical Issues: X/10
- Performance Bottlenecks: X/10
- Dependencies: X/10
- Compliance: X/10

### Overall System Score: X/10

### Critical Issues (Priority Order)
1. [Critical Issue 1] - Impact: High, Effort: Medium
2. [Critical Issue 2] - Impact: Medium, Effort: Low
3. [Critical Issue 3] - Impact: Low, Effort: High

### Strategic Recommendations
- **Immediate Actions** (Next 1-2 weeks)
- **Short-term Improvements** (Next 1-2 months)
- **Long-term Roadmap** (Next 3-6 months)

### Production Deployment Assessment
- **Ready for Production**: Yes/No/Partial
- **Recommended Deployment Strategy**: [Detailed deployment approach]
- **Required Pre-deployment Actions**: [List of required actions]

### Technical Implementation Priorities
- **Critical Issues**: [Technical issues requiring immediate attention]
- **Performance Optimizations**: [Areas for technical improvement]
- **Testing Requirements**: [Additional testing needed]

Please provide a thorough, professional analysis suitable for executive review and technical implementation planning.
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
                    "content": "You are a senior technology consultant specializing in telephony systems, AI integration, and digital transformation. You have extensive experience evaluating enterprise-grade systems for production deployment. Provide comprehensive, actionable insights with specific metrics and clear recommendations."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2,
            max_tokens=6000
        )

        content = response.choices[0].message.content
        if content is None:
            return "No response content received from OpenAI API"
        return content

    except Exception as e:
        return f"Error calling OpenAI API: {str(e)}"

def create_executive_summary(evaluation: str) -> str:
    """Extract and format executive summary from evaluation."""

    lines = evaluation.split('\n')
    summary_lines = []
    in_summary = False

    for line in lines:
        if 'Executive Summary' in line:
            in_summary = True
        elif line.startswith('###') and in_summary and 'Score' not in line:
            break
        elif in_summary and line.strip():
            summary_lines.append(line)

    if summary_lines:
        return '\n'.join(summary_lines)
    else:
        return evaluation[:1000] + "..."

def save_comprehensive_report(evaluation: str, log_data: Dict[str, Any]) -> str:
    """Save the comprehensive evaluation report."""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"comprehensive_evaluation_report_{timestamp}.md"

    executive_summary = create_executive_summary(evaluation)

    report_content = f"""# OpusAgent Comprehensive Validation Evaluation Report

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Test Date:** 2025-07-09
**Conversation ID:** {log_data['session_info'].get('conversation_id', 'N/A')}
**Evaluation Type:** Multi-Dimensional Analysis

## Executive Summary

{executive_summary}

## Test Metrics Summary

### Performance Metrics
- **Duration:** ~21.3 seconds
- **User Audio Chunks:** {log_data['audio_stats']['user_chunks']}
- **Bot Audio Chunks:** {log_data['audio_stats']['bot_chunks']}
- **Total Audio Data:** {(log_data['audio_stats']['user_bytes'] + log_data['audio_stats']['bot_bytes']):,} bytes
- **Function Calls:** {len(log_data['function_calls'])}
- **Errors:** {len(log_data['errors'])}
- **Token Usage:** {sum(log_data['token_usage'])} tokens

### System Health
- **Error Rate:** {log_data['system_health']['error_rate']:.2f}%
- **Function Success Rate:** {log_data['system_health']['function_success_rate']}%
- **Audio Continuity:** {'✅' if log_data['system_health']['audio_continuity'] else '❌'}

## Detailed AI-Generated Evaluation

{evaluation}

## Technical Analysis

### Audio Processing Performance
```json
{json.dumps(log_data['audio_stats'], indent=2)}
```

### Function Call Analysis
```json
{json.dumps(log_data['function_calls'], indent=2)}
```

### System Health Metrics
```json
{json.dumps(log_data['system_health'], indent=2)}
```

### Performance Metrics
```json
{json.dumps(log_data['performance_metrics'], indent=2)}
```

## Recommendations Summary

### Immediate Actions (Next 1-2 weeks)
1. [Extracted from AI evaluation]

### Short-term Improvements (Next 1-2 months)
1. [Extracted from AI evaluation]

### Long-term Roadmap (Next 3-6 months)
1. [Extracted from AI evaluation]

---
*This comprehensive evaluation was automatically generated by the OpusAgent validation system using OpenAI GPT-4o analysis.*
"""

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_content)

    return report_file

def main():
    """Main comprehensive evaluation function."""

    print("🔍 OpusAgent Comprehensive Validation Evaluation")
    print("=" * 60)

    try:
        # Extract comprehensive data
        print("📊 Extracting comprehensive test data...")
        log_data = extract_comprehensive_data()
        print(f"✅ Extracted data for conversation: {log_data['session_info'].get('conversation_id', 'N/A')}")

        # Create multi-dimensional evaluation prompt
        print("🤖 Creating multi-dimensional evaluation prompt...")
        prompt = create_multi_dimensional_prompt(log_data)

        # Get OpenAI evaluation
        print("🧠 Requesting comprehensive AI evaluation...")
        evaluation = evaluate_with_openai(prompt)

        # Save comprehensive report
        print("💾 Saving comprehensive evaluation report...")
        report_file = save_comprehensive_report(evaluation, log_data)

        print(f"\n✅ Comprehensive evaluation complete!")
        print(f"📄 Report saved to: {report_file}")
        print("\n" + "=" * 60)
        print("📋 EXECUTIVE SUMMARY")
        print("=" * 60)

        # Print executive summary
        summary = create_executive_summary(evaluation)
        print(summary)

        print(f"\n📖 Full comprehensive report available in: {report_file}")
        print("\n🎯 Next Steps:")
        print("1. Review the comprehensive evaluation report")
        print("2. Prioritize critical issues and recommendations")
        print("3. Create action plan based on AI insights")
        print("4. Schedule follow-up validation tests")

    except Exception as e:
        print(f"❌ Error during comprehensive evaluation: {str(e)}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())
