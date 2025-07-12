#!/usr/bin/env python3
"""
Simple runner script for VAD Integration Validation.

This script provides a convenient way to run the comprehensive VAD validation
with proper error handling and formatted output.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.validate_vad_integration import VADIntegrationValidator


async def run_validation():
    """Run the VAD validation with nice formatting."""
    print("🔍 VAD Integration Validation")
    print("=" * 60)
    print("This will test all aspects of the VAD integration including:")
    print("• VAD initialization with different configurations")
    print("• Audio processing and format conversion")
    print("• Speech detection and state management")
    print("• Runtime control and configuration updates")
    print("• Performance characteristics and benchmarks")
    print("• Error handling and fallback mechanisms")
    print("• Integration with existing components")
    print("• Session configuration management")
    print("=" * 60)
    
    try:
        # Run validation with verbose output
        validator = VADIntegrationValidator(verbose=True)
        validator.run_all_tests()
        
        # Print summary
        validator.print_summary()
        
        # Check results
        summary = validator.results["summary"]
        
        if summary["failed"] == 0 and summary["errors"] == 0:
            print("\n🎉 VAD validation completed successfully!")
            print("All tests passed - VAD integration is working correctly.")
            return 0
        else:
            print("\n❌ VAD validation completed with failures.")
            print("Please review the failed tests above.")
            return 1
            
    except KeyboardInterrupt:
        print("\n⏹️  Validation interrupted by user.")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error during validation: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(run_validation())) 