#!/usr/bin/env python3
"""
Simple test script for the Realtime Transcription Validation

This script demonstrates how to use the new realtime transcription validation
and provides a quick way to test the functionality.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.validate_realtime_transcription import RealtimeTranscriptionValidator, setup_logging


async def quick_test():
    """Run a quick test of the realtime transcription validation."""
    print("=== Realtime Transcription Validation Quick Test ===")
    
    # Set up logging
    logger = setup_logging(verbose=True)
    
    # Create validator
    validator = RealtimeTranscriptionValidator(logger)
    
    # Test with PocketSphinx backend
    print("\n1. Testing PocketSphinx backend...")
    results = await validator.run_validation(
        backends=["pocketsphinx"],
        generate_test_audio=True,
        output_dir="quick_test_results"
    )
    
    # Print summary
    summary = results["summary"]
    print(f"\nQuick Test Summary:")
    print(f"  Total Tests: {summary['total_tests']}")
    print(f"  Passed: {summary['passed']}")
    print(f"  Failed: {summary['failed']}")
    print(f"  Success Rate: {(summary['passed'] / max(1, summary['total_tests'])) * 100:.1f}%")
    
    return results


def main():
    """Main entry point for the quick test."""
    try:
        results = asyncio.run(quick_test())
        
        # Exit with appropriate code
        summary = results["summary"]
        if summary["failed"] > 0:
            print("\n❌ Some tests failed")
            sys.exit(1)
        else:
            print("\n✅ All tests passed")
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 