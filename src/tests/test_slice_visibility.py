#!/usr/bin/env python3

import sys
import os
sys.path.append('src')

import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

from core.bookmark_engine_v2 import BookmarkHTMLEngineV2

def test_slice_visibility():
    print("=== Testing Slice Visibility Update ===")
    
    # Initialize the bookmark engine
    print("1. Initializing bookmark engine...")
    engine = BookmarkHTMLEngineV2("default_bookmark.html", in_tornado=False)
    
    print(f"Initial state:")
    print(f"  X visible: {engine.curr_params.x_visible}")
    print(f"  Y visible: {engine.curr_params.y_visible}")
    print(f"  Z visible: {engine.curr_params.z_visible}")
    print(f"  Can undo: {engine.can_undo}, undo_count: {engine.undo_count}")
    
    # Turn off all slices (like the "turn off all slices" command)
    print("\n2. Turning off all slices...")
    engine.toggle_slice_visibility('x', False)
    engine.toggle_slice_visibility('y', False)
    engine.toggle_slice_visibility('z', False)
    engine.update_params()
    
    print(f"After turning off all slices:")
    print(f"  X visible: {engine.curr_params.x_visible}")
    print(f"  Y visible: {engine.curr_params.y_visible}")
    print(f"  Z visible: {engine.curr_params.z_visible}")
    print(f"  Can undo: {engine.can_undo}, undo_count: {engine.undo_count}")
    
    # Check the HTML file
    print("\n3. Checking TEMP_BKM.html...")
    with open('data/bookmarks/TEMP_BKM.html', 'r') as f:
        content = f.read()
        
    # Look for slice visibility in HTML
    import re
    x_visible = re.search(r'<X>.*?<VISIBLE>([TF])</VISIBLE>', content, re.DOTALL)
    y_visible = re.search(r'<Y>.*?<VISIBLE>([TF])</VISIBLE>', content, re.DOTALL)
    z_visible = re.search(r'<Z>.*?<VISIBLE>([TF])</VISIBLE>', content, re.DOTALL)
    
    print(f"HTML file shows:")
    print(f"  X visible: {x_visible.group(1) if x_visible else 'NOT FOUND'}")
    print(f"  Y visible: {y_visible.group(1) if y_visible else 'NOT FOUND'}")
    print(f"  Z visible: {z_visible.group(1) if z_visible else 'NOT FOUND'}")
    
    # Test undo
    print("\n4. Testing undo...")
    if engine.can_undo:
        engine.undo()
        print(f"After undo:")
        print(f"  X visible: {engine.curr_params.x_visible}")
        print(f"  Y visible: {engine.curr_params.y_visible}")
        print(f"  Z visible: {engine.curr_params.z_visible}")
        print(f"  Can undo: {engine.can_undo}, undo_count: {engine.undo_count}")
        print(f"  Can redo: {engine.can_redo}, redo_count: {engine.redo_count}")
    else:
        print("Cannot undo!")

if __name__ == "__main__":
    test_slice_visibility()