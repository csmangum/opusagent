"""
Run the concurrent execution example.

This script demonstrates how AFSM task agents can run concurrently with the main
conversation flow in FastAgent.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# Import the demo function
from app.examples.concurrent_task_example import demonstrate_concurrent_execution

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the demonstration
    asyncio.run(demonstrate_concurrent_execution()) 