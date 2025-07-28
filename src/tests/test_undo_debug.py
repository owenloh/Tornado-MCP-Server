#!/usr/bin/env python3

import sys
import os
sys.path.append('src')

import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

from core.bookmark_engine_v2 import BookmarkHTMLEngineV2

def test_undo_functionality():
    print("=== Testing Undo Functionality ===")
    
    # Initialize the bookmark engine
    print("1. Initializing bookmark engine...")
    engine = BookmarkHTMLEngineV2("default_bookmark.html", in_tornado=False)
    
    print(f"After init: history_length={len(engine.history)}, index={engine.history_index}")
    print(f"Can undo: {engine.can_undo}, undo_count: {engine.undo_count}")
    print(f"Can redo: {engine.can_redo}, redo_count: {engine.redo_count}")
    
    # Make a change
    print("\n2. Making a change (toggle seismic visibility)...")
    engine.toggle_data_visibility('seismic', False)
    engine.update_params()
    
    print(f"After change: history_length={len(engine.history)}, index={engine.history_index}")
    print(f"Can undo: {engine.can_undo}, undo_count: {engine.undo_count}")
    print(f"Can redo: {engine.can_redo}, redo_count: {engine.redo_count}")
    
    # Try to undo
    print("\n3. Attempting undo...")
    if engine.can_undo:
        engine.undo()
        print("Undo successful!")
    else:
        print("Undo not available!")
    
    print(f"After undo: history_length={len(engine.history)}, index={engine.history_index}")
    print(f"Can undo: {engine.can_undo}, undo_count: {engine.undo_count}")
    print(f"Can redo: {engine.can_redo}, redo_count: {engine.redo_count}")

if __name__ == "__main__":
    test_undo_functionality()