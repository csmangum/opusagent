#!/usr/bin/env python3
"""
MockRealtimeClient - Enhanced OpenAI Realtime API Simulator

This module has been refactored into a modular structure. The main functionality
is now available in the `mock_realtime` submodule.

For new code, please use:
    from opusagent.mock.mock_realtime import MockRealtimeClient, MockResponseConfig

This file is maintained for backward compatibility.
"""

# Import from the new modular structure
from .mock_realtime import MockRealtimeClient, MockResponseConfig

# Re-export for backward compatibility
__all__ = ["MockRealtimeClient", "MockResponseConfig"] 