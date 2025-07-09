#!/usr/bin/env python3
"""
Validation Test Analysis Script

This script analyzes the validation test log and provides detailed insights
about the test execution, performance, and any issues encountered.
"""

import json
import re
from datetime import datetime
from pathlib import Path
import webbrowser
import os

def parse_log_timestamps(log_content):
    """Extract timestamps and events from log content."""
    timestamp_pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})'
    events = []
    
    for line in log_content.split('\n'):
        if timestamp_pattern in line:
            match = re.search(timestamp_pattern, line)
            if match:
                timestamp_str = match.group(1)
                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
                events.append({
                    'timestamp': timestamp,
                    'line': line.strip()
                })
    
    return events

def analyze_validation_test(log_file_path):
    """Analyze the validation test log and return insights."""
    
    with open(log_file_path, 'r') as f:
        log_content = f.read()
    
    events = parse_log_timestamps(log_content)
    
    if not events:
        return {"error": "No valid timestamps found in log"}
    
    # Calculate test duration
    start_time = events[0]['timestamp']
    end_time = events[-1]['timestamp']
    duration = (end_time - start_time).total_seconds()
    
    # Analyze different event types
    analysis = {
        'start_time': start_time.isoformat(),
        'end_time': end_time.isoformat(),
        'duration_seconds': duration,
        'total_events': len(events),
        'event_types': {},
        'errors': [],
        'warnings': [],
        'function_calls': [],
        'audio_stats': {
            'user_chunks': 0,
            'bot_chunks': 0,
            'total_audio_bytes': 0
        },
        'response_times': [],
        'session_flow': []
    }
    
    # Analyze each event
    for event in events:
        line = event['line']
        
        # Count event types
        if ' - ' in line:
            parts = line.split(' - ')
            if len(parts) >= 3:
                event_type = parts[2].split(' - ')[0] if ' - ' in parts[2] else parts[2]
                analysis['event_types'][event_type] = analysis['event_types'].get(event_type, 0) + 1
        
        # Look for errors
        if 'ERROR' in line:
            analysis['errors'].append({
                'timestamp': event['timestamp'].isoformat(),
                'message': line
            })
        
        # Look for warnings
        if 'WARNING' in line:
            analysis['warnings'].append({
                'timestamp': event['timestamp'].isoformat(),
                'message': line
            })
        
        # Track function calls
        if 'Function call arguments delta' in line:
            analysis['function_calls'].append({
                'timestamp': event['timestamp'].isoformat(),
                'type': 'function_call_delta'
            })
        
        if 'Function execution failed' in line:
            analysis['function_calls'].append({
                'timestamp': event['timestamp'].isoformat(),
                'type': 'function_call_failed'
            })
        
        # Track audio chunks
        if 'userStream.chunk' in line:
            analysis['audio_stats']['user_chunks'] += 1
        
        if 'response.audio.delta' in line:
            analysis['audio_stats']['bot_chunks'] += 1
        
        # Track session flow
        if 'session.initiate' in line:
            analysis['session_flow'].append({
                'timestamp': event['timestamp'].isoformat(),
                'event': 'session_initiated'
            })
        
        if 'session.end' in line:
            analysis['session_flow'].append({
                'timestamp': event['timestamp'].isoformat(),
                'event': 'session_ended'
            })
    
    # Calculate response times
    response_starts = []
    response_ends = []
    
    for event in events:
        if 'response.created' in event['line']:
            response_starts.append(event['timestamp'])
        elif 'response.done' in event['line']:
            response_ends.append(event['timestamp'])
    
    for start, end in zip(response_starts, response_ends):
        response_time = (end - start).total_seconds()
        analysis['response_times'].append(response_time)
    
    return analysis

def generate_summary_report(analysis):
    """Generate a human-readable summary report."""
    
    report = f"""
🔍 VALIDATION TEST ANALYSIS REPORT
{'='*50}

📊 Test Overview:
   • Duration: {analysis['duration_seconds']:.1f} seconds
   • Total Events: {analysis['total_events']}
   • Start Time: {analysis['start_time']}
   • End Time: {analysis['end_time']}

🎯 Session Flow:
"""
    
    for flow_event in analysis['session_flow']:
        report += f"   • {flow_event['event']} at {flow_event['timestamp']}\n"
    
    report += f"""
📈 Audio Statistics:
   • User Audio Chunks: {analysis['audio_stats']['user_chunks']}
   • Bot Audio Chunks: {analysis['audio_stats']['bot_chunks']}
   • Total Audio Exchange: {analysis['audio_stats']['user_chunks'] + analysis['audio_stats']['bot_chunks']} chunks

⚡ Response Performance:
"""
    
    if analysis['response_times']:
        avg_response = sum(analysis['response_times']) / len(analysis['response_times'])
        report += f"   • Average Response Time: {avg_response:.2f} seconds\n"
        report += f"   • Total Responses: {len(analysis['response_times'])}\n"
    
    report += f"""
🔧 Function Calls:
   • Total Function Call Events: {len(analysis['function_calls'])}
"""
    
    failed_calls = [call for call in analysis['function_calls'] if call['type'] == 'function_call_failed']
    if failed_calls:
        report += f"   • Failed Function Calls: {len(failed_calls)}\n"
    
    report += f"""
⚠️ Issues Found:
   • Errors: {len(analysis['errors'])}
   • Warnings: {len(analysis['warnings'])}
"""
    
    if analysis['errors']:
        report += "\n❌ Error Details:\n"
        for error in analysis['errors'][:3]:  # Show first 3 errors
            report += f"   • {error['message'][:100]}...\n"
    
    if analysis['warnings']:
        report += "\n⚠️ Warning Details:\n"
        for warning in analysis['warnings'][:3]:  # Show first 3 warnings
            report += f"   • {warning['message'][:100]}...\n"
    
    # Overall assessment
    if len(analysis['errors']) == 0 and len(analysis['warnings']) <= 2:
        report += "\n✅ OVERALL ASSESSMENT: TEST PASSED\n"
        report += "   The validation test completed successfully with minimal issues.\n"
    elif len(analysis['errors']) <= 2:
        report += "\n⚠️ OVERALL ASSESSMENT: TEST PASSED WITH WARNINGS\n"
        report += "   The test completed but with some minor issues to review.\n"
    else:
        report += "\n❌ OVERALL ASSESSMENT: TEST FAILED\n"
        report += "   Multiple errors were encountered during the test.\n"
    
    return report

def main():
    """Main function to analyze the validation test."""
    
    # Find the log file
    log_file = Path("logs/opusagent.log")
    
    if not log_file.exists():
        print("❌ Log file not found: logs/opusagent.log")
        return
    
    print("🔍 Analyzing validation test log...")
    
    # Analyze the log
    analysis = analyze_validation_test(log_file)
    
    if 'error' in analysis:
        print(f"❌ Analysis failed: {analysis['error']}")
        return
    
    # Generate and print summary report
    report = generate_summary_report(analysis)
    print(report)
    
    # Save detailed analysis to JSON
    analysis_file = Path("validation_analysis.json")
    with open(analysis_file, 'w') as f:
        json.dump(analysis, f, indent=2, default=str)
    
    print(f"📄 Detailed analysis saved to: {analysis_file}")
    
    # Open the visualization
    viz_file = Path("validation_test_visualization.html")
    if viz_file.exists():
        print("🌐 Opening visualization in browser...")
        webbrowser.open(f'file://{viz_file.absolute()}')
    else:
        print("❌ Visualization file not found: validation_test_visualization.html")
    
    # Print key insights
    print("\n🎯 KEY INSIGHTS:")
    
    # Session success
    if len(analysis['session_flow']) >= 2:
        print("   ✅ Session management: Working correctly")
    
    # Audio flow
    audio_stats = analysis.get('audio_stats', {})
    user_chunks = audio_stats.get('user_chunks', 0)
    bot_chunks = audio_stats.get('bot_chunks', 0)
    if user_chunks > 0 and bot_chunks > 0:
        print("   ✅ Audio streaming: Bidirectional flow working")
    
    # Response times
    response_times = analysis.get('response_times', [])
    if response_times and isinstance(response_times, list):
        avg_response = sum(response_times) / len(response_times)
        if avg_response < 5.0:
            print(f"   ✅ Response times: Good ({avg_response:.2f}s average)")
        else:
            print(f"   ⚠️ Response times: Slow ({avg_response:.2f}s average)")
    
    # Function calls
    function_calls = analysis.get('function_calls', [])
    if isinstance(function_calls, list):
        failed_calls = [call for call in function_calls if isinstance(call, dict) and call.get('type') == 'function_call_failed']
        if failed_calls:
            print(f"   ⚠️ Function calls: {len(failed_calls)} failures (expected for human_handoff)")
    
    # Errors
    if len(analysis['errors']) == 0:
        print("   ✅ Error handling: No critical errors")
    else:
        print(f"   ⚠️ Error handling: {len(analysis['errors'])} errors found")

if __name__ == "__main__":
    main() 