#!/usr/bin/env python3
"""Test template listing"""

import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from terminal.nlp_chat_terminal import NLPChatTerminal
from utils.env_config import EnvConfig

def test_templates():
    """Test template listing"""
    env_config = EnvConfig(silent=True)
    api_key = env_config.gemini_api_key
    
    if not api_key:
        print("❌ No API key available")
        return
    
    print("🧪 Testing template listing...")
    terminal = NLPChatTerminal(api_key)
    
    # Wait a moment for state sync
    import time
    time.sleep(3)
    
    # Test template query
    result = terminal.process_user_input("what are the available bookmarks")
    terminal.display_result(result, "what are the available bookmarks")

if __name__ == "__main__":
    test_templates()