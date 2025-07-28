#!/usr/bin/env python3
"""Test template response fix"""

import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from terminal.nlp_chat_terminal import NLPChatTerminal
from utils.env_config import EnvConfig

def test_template_response():
    """Test that template requests return properly"""
    env_config = EnvConfig(silent=True)
    api_key = env_config.gemini_api_key
    
    if not api_key:
        print("❌ No API key available")
        return
    
    print("🧪 Testing template response fix...")
    terminal = NLPChatTerminal(api_key)
    
    print("\n1. Testing template request (should return templates):")
    result = terminal.process_user_input("what are the available bookmarks")
    terminal.display_result(result, "what are the available bookmarks")
    
    print("\n2. Testing state request (should return current state):")
    result = terminal.process_user_input("what's my current position?")
    terminal.display_result(result, "what's my current position?")

if __name__ == "__main__":
    test_template_response()