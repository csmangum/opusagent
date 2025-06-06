#!/usr/bin/env python3
"""
Latency Analyzer for OpusAgent Logs

This script analyzes the opusagent.log file to calculate latencies between key conversation events:
- User speech completion → AI response start
- Function call → AI response
- Overall conversation turn latencies
"""

import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path


@dataclass
class LogEvent:
    """Represents a parsed log event."""
    timestamp: datetime
    level: str
    logger: str
    message: str
    raw_line: str


@dataclass
class ConversationTurn:
    """Represents a complete conversation turn."""
    turn_number: int
    user_speech_start: Optional[datetime] = None
    user_speech_end: Optional[datetime] = None
    user_transcript_complete: Optional[datetime] = None
    user_transcript: str = ""
    
    function_call_start: Optional[datetime] = None
    function_call_end: Optional[datetime] = None
    function_name: str = ""
    
    ai_response_start: Optional[datetime] = None
    ai_response_end: Optional[datetime] = None
    ai_transcript_complete: Optional[datetime] = None
    ai_transcript: str = ""
    
    audio_playback_start: Optional[datetime] = None
    audio_playback_end: Optional[datetime] = None
    
    @property
    def user_to_ai_latency(self) -> Optional[float]:
        """Latency from user speech end to AI response start (in seconds)."""
        if self.user_speech_end and self.ai_response_start:
            return (self.ai_response_start - self.user_speech_end).total_seconds()
        return None
    
    @property
    def user_to_audio_latency(self) -> Optional[float]:
        """Latency from user speech end to AI audio playback start (in seconds)."""
        if self.user_speech_end and self.audio_playback_start:
            return (self.audio_playback_start - self.user_speech_end).total_seconds()
        return None
    
    @property
    def transcript_to_response_latency(self) -> Optional[float]:
        """Latency from user transcript completion to AI response start (in seconds)."""
        if self.user_transcript_complete and self.ai_response_start:
            return (self.ai_response_start - self.user_transcript_complete).total_seconds()
        return None
    
    @property
    def function_call_latency(self) -> Optional[float]:
        """Function call processing time (in seconds)."""
        if self.function_call_start and self.function_call_end:
            return (self.function_call_end - self.function_call_start).total_seconds()
        return None
    
    @property
    def total_turn_latency(self) -> Optional[float]:
        """Total turn latency from user speech end to AI audio start (in seconds)."""
        return self.user_to_audio_latency


class LogParser:
    """Parses OpusAgent log files and extracts timing information."""
    
    def __init__(self, log_file_path: str):
        self.log_file_path = Path(log_file_path)
        self.events: List[LogEvent] = []
        self.turns: List[ConversationTurn] = []
        
        # Regex patterns for parsing log lines
        self.log_pattern = re.compile(
            r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - ([^-]+) - (\w+) - (.+)'
        )
    
    def parse_log_file(self) -> List[LogEvent]:
        """Parse the log file and extract all events."""
        print(f"📖 Parsing log file: {self.log_file_path}")
        
        with open(self.log_file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                event = self._parse_log_line(line, line_num)
                if event:
                    self.events.append(event)
        
        print(f"📊 Parsed {len(self.events)} log events")
        return self.events
    
    def _parse_log_line(self, line: str, line_num: int) -> Optional[LogEvent]:
        """Parse a single log line."""
        match = self.log_pattern.match(line)
        if not match:
            return None
        
        timestamp_str, logger, level, message = match.groups()
        
        # Parse timestamp
        try:
            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
        except ValueError:
            print(f"⚠️  Failed to parse timestamp at line {line_num}: {timestamp_str}")
            return None
        
        return LogEvent(
            timestamp=timestamp,
            level=level.strip(),
            logger=logger.strip(),
            message=message.strip(),
            raw_line=line
        )
    
    def analyze_conversations(self) -> List[ConversationTurn]:
        """Analyze the events to extract conversation turns and calculate latencies."""
        print("🔍 Analyzing conversation turns...")
        
        current_turn = None
        turn_number = 0
        
        for event in self.events:
            # Detect start of new user speech
            if 'userStream.start' in event.message:
                turn_number += 1
                current_turn = ConversationTurn(turn_number=turn_number)
                current_turn.user_speech_start = event.timestamp
                self.turns.append(current_turn)
                continue
            
            if current_turn is None:
                continue
            
            # User speech events
            if 'userStream.stop' in event.message:
                current_turn.user_speech_end = event.timestamp
            
            elif 'Full user transcript (input audio):' in event.message:
                current_turn.user_transcript_complete = event.timestamp
                # Extract transcript text
                transcript_match = re.search(r'Full user transcript \(input audio\): (.+)', event.message)
                if transcript_match:
                    current_turn.user_transcript = transcript_match.group(1).strip()
            
            # Function call events
            elif 'Captured function call:' in event.message:
                current_turn.function_call_start = event.timestamp
                # Extract function name
                func_match = re.search(r'Captured function call: (\w+)', event.message)
                if func_match:
                    current_turn.function_name = func_match.group(1)
            
            elif 'Function call logged:' in event.message:
                current_turn.function_call_end = event.timestamp
            
            # AI response events
            elif 'Response creation started' in event.message:
                current_turn.ai_response_start = event.timestamp
            
            elif 'Response event details:' in event.message and '"status": "completed"' in event.message:
                current_turn.ai_response_end = event.timestamp
            
            elif 'Full AI transcript (output audio):' in event.message:
                current_turn.ai_transcript_complete = event.timestamp
                # Extract AI transcript
                ai_transcript_match = re.search(r'Full AI transcript \(output audio\): (.+)', event.message)
                if ai_transcript_match:
                    current_turn.ai_transcript = ai_transcript_match.group(1).strip()
            
            # Audio playback events
            elif 'Started play stream:' in event.message:
                current_turn.audio_playback_start = event.timestamp
            
            elif 'Stopped play stream:' in event.message:
                current_turn.audio_playback_end = event.timestamp
        
        print(f"📊 Found {len(self.turns)} conversation turns")
        return self.turns
    
    def calculate_latency_statistics(self) -> Dict[str, Any]:
        """Calculate overall latency statistics."""
        user_to_ai_latencies = [turn.user_to_ai_latency for turn in self.turns if turn.user_to_ai_latency is not None]
        user_to_audio_latencies = [turn.user_to_audio_latency for turn in self.turns if turn.user_to_audio_latency is not None]
        transcript_to_response_latencies = [turn.transcript_to_response_latency for turn in self.turns if turn.transcript_to_response_latency is not None]
        function_call_latencies = [turn.function_call_latency for turn in self.turns if turn.function_call_latency is not None]
        
        def stats(values: List[float]) -> Dict[str, float]:
            if not values:
                return {"count": 0, "min": 0, "max": 0, "avg": 0, "median": 0}
            
            values_sorted = sorted(values)
            return {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "median": values_sorted[len(values_sorted) // 2]
            }
        
        return {
            "user_to_ai_response": stats(user_to_ai_latencies),
            "user_to_audio_playback": stats(user_to_audio_latencies),
            "transcript_to_response": stats(transcript_to_response_latencies),
            "function_call_processing": stats(function_call_latencies),
            "raw_latencies": {
                "user_to_ai": user_to_ai_latencies,
                "user_to_audio": user_to_audio_latencies,
                "transcript_to_response": transcript_to_response_latencies,
                "function_calls": function_call_latencies
            }
        }
    
    def print_detailed_analysis(self):
        """Print a detailed analysis of the conversation turns."""
        print("\n" + "="*80)
        print("📊 DETAILED CONVERSATION ANALYSIS")
        print("="*80)
        
        for turn in self.turns:
            print(f"\n🔄 Turn {turn.turn_number}")
            print("-" * 40)
            
            if turn.user_transcript:
                print(f"👤 User: \"{turn.user_transcript}\"")
            if turn.ai_transcript:
                print(f"🤖 AI: \"{turn.ai_transcript}\"")
            if turn.function_name:
                print(f"⚙️  Function: {turn.function_name}")
            
            print("\n⏱️  Timings:")
            if turn.user_speech_start and turn.user_speech_end:
                duration = (turn.user_speech_end - turn.user_speech_start).total_seconds()
                print(f"   User speech duration: {duration:.2f}s")
            
            if turn.user_to_ai_latency is not None:
                print(f"   User speech → AI response: {turn.user_to_ai_latency:.3f}s")
            
            if turn.user_to_audio_latency is not None:
                print(f"   User speech → Audio playback: {turn.user_to_audio_latency:.3f}s")
            
            if turn.transcript_to_response_latency is not None:
                print(f"   Transcript complete → AI response: {turn.transcript_to_response_latency:.3f}s")
            
            if turn.function_call_latency is not None:
                print(f"   Function call processing: {turn.function_call_latency:.3f}s")
    
    def print_summary_statistics(self):
        """Print summary statistics."""
        stats = self.calculate_latency_statistics()
        
        print("\n" + "="*80)
        print("📈 LATENCY SUMMARY STATISTICS")
        print("="*80)
        
        def print_stat_block(title: str, stat_data: Dict[str, float]):
            print(f"\n{title}:")
            if stat_data["count"] == 0:
                print("   No data available")
                return
            
            print(f"   Count: {stat_data['count']}")
            print(f"   Min:   {stat_data['min']:.3f}s")
            print(f"   Max:   {stat_data['max']:.3f}s")
            print(f"   Avg:   {stat_data['avg']:.3f}s")
            print(f"   Median: {stat_data['median']:.3f}s")
        
        print_stat_block("🎤 User Speech End → AI Response Start", stats["user_to_ai_response"])
        print_stat_block("🎤 User Speech End → Audio Playback Start", stats["user_to_audio_playback"])
        print_stat_block("📝 Transcript Complete → AI Response Start", stats["transcript_to_response"])
        print_stat_block("⚙️  Function Call Processing Time", stats["function_call_processing"])
        
        # Customer-perceived latency analysis
        customer_latencies = stats["raw_latencies"]["user_to_audio"]
        if customer_latencies:
            print(f"\n🎯 CUSTOMER-PERCEIVED LATENCIES:")
            print(f"   Best case:  {min(customer_latencies):.3f}s")
            print(f"   Worst case: {max(customer_latencies):.3f}s")
            print(f"   Average:    {sum(customer_latencies)/len(customer_latencies):.3f}s")
            
            # Categorize latencies
            excellent = sum(1 for lat in customer_latencies if lat <= 1.0)
            good = sum(1 for lat in customer_latencies if 1.0 < lat <= 2.0)
            acceptable = sum(1 for lat in customer_latencies if 2.0 < lat <= 3.0)
            poor = sum(1 for lat in customer_latencies if lat > 3.0)
            
            total = len(customer_latencies)
            print(f"\n   Performance Distribution:")
            print(f"   Excellent (≤1.0s): {excellent}/{total} ({excellent/total*100:.1f}%)")
            print(f"   Good (1.0-2.0s):   {good}/{total} ({good/total*100:.1f}%)")
            print(f"   Acceptable (2.0-3.0s): {acceptable}/{total} ({acceptable/total*100:.1f}%)")
            print(f"   Poor (>3.0s):      {poor}/{total} ({poor/total*100:.1f}%)")


def main():
    """Main function to run the latency analysis."""
    log_file = "demo/opusagent.log"
    
    if not Path(log_file).exists():
        print(f"❌ Log file not found: {log_file}")
        return
    
    # Initialize parser and analyze
    parser = LogParser(log_file)
    
    # Parse log file
    events = parser.parse_log_file()
    if not events:
        print("❌ No events found in log file")
        return
    
    # Analyze conversations
    turns = parser.analyze_conversations()
    if not turns:
        print("❌ No conversation turns found")
        return
    
    # Print detailed analysis
    parser.print_detailed_analysis()
    
    # Print summary statistics
    parser.print_summary_statistics()
    
    # Save results to JSON
    stats = parser.calculate_latency_statistics()
    output_file = "latency_analysis.json"
    with open(output_file, 'w') as f:
        json.dump(stats, f, indent=2, default=str)
    
    print(f"\n💾 Detailed results saved to: {output_file}")
    print("\n✅ Analysis complete!")


if __name__ == "__main__":
    main() 