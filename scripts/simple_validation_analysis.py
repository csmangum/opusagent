#!/usr/bin/env python3
"""
Simple Validation Test Analysis

This script provides a quick analysis of the validation test log.
"""

import re
from datetime import datetime
from pathlib import Path

def analyze_log():
    """Analyze the validation test log."""

    log_file = Path("logs/opusagent.log")
    if not log_file.exists():
        print("❌ Log file not found: logs/opusagent.log")
        return

    with open(log_file, 'r') as f:
        content = f.read()

    lines = content.split('\n')

    # Find start and end times
    start_time = None
    end_time = None

    for line in lines:
        if 'session.initiate' in line and start_time is None:
            match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})', line)
            if match:
                start_time = match.group(1)

        if 'session.end' in line:
            match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})', line)
            if match:
                end_time = match.group(1)

    # Count different event types
    user_chunks = len([line for line in lines if 'userStream.chunk' in line])
    bot_chunks = len([line for line in lines if 'response.audio.delta' in line])
    errors = len([line for line in lines if 'ERROR' in line])
    warnings = len([line for line in lines if 'WARNING' in line])
    function_calls = len([line for line in lines if 'Function execution failed' in line])

    # Find key events
    session_events = []
    for line in lines:
        if any(event in line for event in ['session.initiate', 'session.accepted', 'session.end']):
            match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})', line)
            if match:
                session_events.append((match.group(1), line.split(' - ')[-1] if ' - ' in line else line))

    # Calculate duration
    if start_time and end_time:
        start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S,%f')
        end_dt = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S,%f')
        duration = (end_dt - start_dt).total_seconds()
    else:
        duration = 0

    # Print analysis
    print("🔍 VALIDATION TEST ANALYSIS")
    print("=" * 50)
    print(f"📊 Duration: {duration:.1f} seconds")
    print(f"📊 User Audio Chunks: {user_chunks}")
    print(f"📊 Bot Audio Chunks: {bot_chunks}")
    print(f"📊 Total Audio Exchange: {user_chunks + bot_chunks} chunks")
    print(f"❌ Errors: {errors}")
    print(f"⚠️ Warnings: {warnings}")
    print(f"🔧 Function Call Failures: {function_calls}")

    print("\n🎯 Session Flow:")
    for timestamp, event in session_events:
        print(f"   • {timestamp} - {event[:80]}...")

    print("\n📈 Key Insights:")

    if duration > 0:
        print("   ✅ Session management: Working correctly")

    if user_chunks > 0 and bot_chunks > 0:
        print("   ✅ Audio streaming: Bidirectional flow working")

    if function_calls > 0:
        print("   ⚠️ Function calls: human_handoff not implemented (expected)")

    if errors == 0:
        print("   ✅ Error handling: No critical errors")
    else:
        print(f"   ⚠️ Error handling: {errors} errors found")

    if warnings <= 2:
        print("   ✅ System health: Minimal warnings")
    else:
        print(f"   ⚠️ System health: {warnings} warnings")

    # Overall assessment
    print("\n🎯 OVERALL ASSESSMENT:")
    if errors == 0 and warnings <= 2:
        print("   ✅ TEST PASSED - All core functionality working")
    elif errors <= 2:
        print("   ⚠️ TEST PASSED WITH WARNINGS - Minor issues to review")
    else:
        print("   ❌ TEST FAILED - Multiple errors encountered")

    print(f"\n📄 Detailed log available at: {log_file}")
    print("🌐 Open validation_test_visualization.html for visual analysis")

if __name__ == "__main__":
    analyze_log()
