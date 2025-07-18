#!/usr/bin/env python3
"""
Test PocketSphinx Fix

This script tests the PocketSphinx initialization fix for Windows.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from opusagent.local.realtime import TranscriptionConfig, TranscriptionFactory


async def test_pocketsphinx_initialization():
    """Test PocketSphinx initialization with the fix."""
    print("Testing PocketSphinx initialization...")
    
    try:
        # Create PocketSphinx configuration
        config = TranscriptionConfig(backend="pocketsphinx")
        
        # Create transcriber
        transcriber = TranscriptionFactory.create_transcriber(config)
        
        # Test initialization
        print("Initializing PocketSphinx transcriber...")
        initialized = await transcriber.initialize()
        
        if initialized:
            print("✅ SUCCESS: PocketSphinx initialized successfully!")
            
            # Test cleanup
            await transcriber.cleanup()
            print("✅ SUCCESS: PocketSphinx cleaned up successfully!")
            return True
        else:
            print("❌ FAILED: PocketSphinx initialization failed")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


async def main():
    """Main test function."""
    print("=== PocketSphinx Fix Test ===")
    
    success = await test_pocketsphinx_initialization()
    
    if success:
        print("\n🎉 All tests passed! PocketSphinx fix is working.")
        sys.exit(0)
    else:
        print("\n💥 Tests failed. PocketSphinx still has issues.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 