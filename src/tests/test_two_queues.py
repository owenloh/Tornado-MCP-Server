#!/usr/bin/env python3
"""Test two-queue system is working"""

import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from terminal.nlp_chat_terminal import NLPChatTerminal
from utils.env_config import EnvConfig

def test_two_queues():
    """Test that two-queue system is working properly"""
    env_config = EnvConfig(silent=True)
    api_key = env_config.gemini_api_key
    
    if not api_key:
        print("❌ No API key available")
        return
    
    print("🧪 Testing two-queue system...")
    terminal = NLPChatTerminal(api_key)
    
    print("\n1. Testing tornado_requests queue (templates):")
    result = terminal.process_user_input("what are the available bookmarks")
    terminal.display_result(result, "what are the available bookmarks")
    
    print("\n2. Testing commands queue (position move):")
    result = terminal.process_user_input("move to crossline 165000")
    terminal.display_result(result, "move to crossline 165000")
    
    print("\n3. Testing tornado_requests queue (state):")
    result = terminal.process_user_input("what's my current position?")
    terminal.display_result(result, "what's my current position?")

if __name__ == "__main__":
    test_two_queues()