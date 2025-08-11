#!/usr/bin/env python3
"""
NLP End Entry Point - Windows-based Natural Language Processing Terminal

This is the main entry point for the NLP end component that runs on Windows.
It provides a conversational terminal interface for seismic navigation commands.
"""

import sys
from pathlib import Path

# Add Windows venv to path FIRST
win_venv_path = Path(__file__).resolve().parent.parent / '.win-venv' / 'Lib' / 'site-packages'
if win_venv_path.exists():
    sys.path.insert(0, str(win_venv_path))

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import and run the main terminal
from nlp_end.terminal.nlp_chat_terminal import main

if __name__ == "__main__":
    main()