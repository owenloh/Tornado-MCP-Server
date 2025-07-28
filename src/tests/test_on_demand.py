#!/usr/bin/env python3
"""Test on-demand state requests"""

import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from terminal.nlp_chat_terminal import NLPChatTerminal
from utils.env_config import EnvConfig

def test_on_demand():
    """Test on-demand state and template requests"""
    env_config = EnvConfig(silent=True)
    api_key = env_config.gemini_api_key
    
    if not api_key:
        print("❌ No API key available")
        return
    
    print("🧪 Testing on-demand requests...")
    terminal = NLPChatTerminal(api_key)
    
    print("\n1. Testing fresh state request:")
    result = terminal.process_user_input("what's my current position?")
    terminal.display_result(result, "what's my current position?")
    
    print("\n2. Testing fresh template request:")
    result = terminal.process_user_input("what are the available bookmarks")
    terminal.display_result(result, "what are the available bookmarks")

if __name__ == "__main__":
    test_on_demand()