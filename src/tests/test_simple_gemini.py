#!/usr/bin/env python3
"""
Simple test of Gemini function calling
"""

import google.generativeai as genai
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from nlp.gemini_command_parser import GeminiCommandParser
from test_utils import get_test_api_key

def test_simple_command():
    """Test a simple command"""
    api_key = get_test_api_key()
    if not api_key:
        return False
    
    try:
        print("🧪 Testing simple Gemini command...")
        print(f"🔑 Using API key: {api_key[:10]}...")
        
        parser = GeminiCommandParser(api_key)
        print("✅ Parser initialized")
        
        # Test simple position command
        command = "move to crossline 165000, inline 115000, depth 4000"
        print(f"📝 Testing command: {command}")
        
        result = parser.parse_command(command)
        
        print(f"📋 Result: {result}")
        
        if result.get('type') == 'command':
            print("✅ Command parsed successfully!")
            print(f"   Method: {result['method']}")
            print(f"   Params: {result['params']}")
        else:
            print(f"❌ Command parsing failed: {result}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simple_command()