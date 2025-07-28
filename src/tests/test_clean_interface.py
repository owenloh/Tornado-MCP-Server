#!/usr/bin/env python3
"""Test the cleaned up interface"""

import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from terminal.nlp_chat_terminal import NLPChatTerminal
from utils.env_config import EnvConfig

def test_clean_interface():
    """Test the interface without debug clutter"""
    env_config = EnvConfig(silent=True)
    api_key = env_config.gemini_api_key
    
    if not api_key:
        print("❌ No API key available")
        return
    
    print("🧪 Testing clean interface...")
    terminal = NLPChatTerminal(api_key)
    
    # Simulate a position query
    result = terminal.process_user_input("what's my current position?")
    terminal.display_result(result, "what's my current position?")

if __name__ == "__main__":
    test_clean_interface()