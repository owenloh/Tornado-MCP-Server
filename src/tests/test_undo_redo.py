#!/usr/bin/env python3
"""Test undo/redo functionality"""

import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from terminal.nlp_chat_terminal import NLPChatTerminal
from utils.env_config import EnvConfig

def test_undo_redo():
    """Test undo/redo functionality and validation"""
    env_config = EnvConfig(silent=True)
    api_key = env_config.gemini_api_key
    
    if not api_key:
        print("❌ No API key available")
        return
    
    print("🧪 Testing undo/redo functionality...")
    terminal = NLPChatTerminal(api_key)
    
    print("\n1. Check initial undo/redo status:")
    result = terminal.process_user_input("can I undo or redo anything?")
    terminal.display_result(result, "can I undo or redo anything?")
    
    print("\n2. Try to undo when nothing to undo:")
    result = terminal.process_user_input("undo")
    terminal.display_result(result, "undo")
    
    print("\n3. Check current state with undo/redo info:")
    result = terminal.process_user_input("what's my current position?")
    terminal.display_result(result, "what's my current position?")

if __name__ == "__main__":
    test_undo_redo()