#!/usr/bin/env python3
"""
Debug script to test tool serialization.
"""

import json
from opusagent.customer_service_agent import get_customer_service_tools

def debug_tools():
    """Debug the tool serialization."""
    tools = get_customer_service_tools()
    
    print("=== Tool Serialization Debug ===")
    for i, tool in enumerate(tools):
        print(f"\nTool {i}: {tool['name']}")
        print(f"Type: {tool['type']}")
        print(f"Description: {tool['description']}")
        print(f"Parameters: {json.dumps(tool['parameters'], indent=2)}")
        
        # Check if parameters is None
        if tool['parameters'] is None:
            print("❌ ERROR: Parameters is None!")
        else:
            print("✅ Parameters is not None")

if __name__ == "__main__":
    debug_tools() 