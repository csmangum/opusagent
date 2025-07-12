#!/usr/bin/env python3
"""
Simple runner script for LocalRealtimeClient validation.

This script provides a convenient way to run the comprehensive validation
with proper error handling and formatted output.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.validate_local_realtime_client import LocalRealtimeClientValidator


async def run_validation():
    """Run the validation with nice formatting."""
    print("🔍 LocalRealtimeClient Validation")
    print("=" * 50)
    print("This will test all aspects of the LocalRealtimeClient including:")
    print("• Client initialization and configuration")
    print("• Response configuration management")
    print("• Intent detection and keyword matching")
    print("• Conversation context management")
    print("• WebSocket connection lifecycle")
    print("• Performance metrics and timing")
    print("• Error handling and edge cases")
    print("• Smart response selection algorithms")
    print("• Session state management")
    print("=" * 50)
    
    try:
        # Run validation with verbose output
        validator = LocalRealtimeClientValidator(verbose=True)
        success = await validator.run_all_tests()
        
        if success:
            print("\n🎉 Validation completed successfully!")
            print("All tests passed - LocalRealtimeClient is working correctly.")
            return 0
        else:
            print("\n❌ Validation completed with failures.")
            print("Please review the failed tests above.")
            return 1
            
    except KeyboardInterrupt:
        print("\n⏹️  Validation interrupted by user.")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error during validation: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_validation())
    sys.exit(exit_code)
