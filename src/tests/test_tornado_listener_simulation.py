#!/usr/bin/env python3

import sys
import os
sys.path.append('src')

import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

from core.bookmark_engine_v2 import BookmarkHTMLEngineV2

def simulate_tornado_listener_command():
    print("=== Simulating Tornado Listener Command Processing ===")
    
    # Initialize bookmark engine like tornado_listener does
    print("1. Initializing bookmark engine (like tornado_listener)...")
    bookmark_engine = BookmarkHTMLEngineV2("default_bookmark.html", in_tornado=False)
    
    print(f"Initial state:")
    print(f"  X visible: {bookmark_engine.curr_params.x_visible}")
    print(f"  Y visible: {bookmark_engine.curr_params.y_visible}")
    print(f"  Z visible: {bookmark_engine.curr_params.z_visible}")
    print(f"  Can undo: {bookmark_engine.can_undo}, undo_count: {bookmark_engine.undo_count}")
    
    # Simulate the handle_update_slice_visibility method
    print("\n2. Simulating handle_update_slice_visibility command...")
    
    # This is what the tornado_listener does when it receives update_slice_visibility
    params = {
        'x_slice': False,  # Turn off X slice
        'y_slice': False,  # Turn off Y slice
        'z_slice': False   # Turn off Z slice
    }
    
    # Use individual toggle_slice_visibility calls for each slice type
    x_slice = params.get('x_slice')
    y_slice = params.get('y_slice')
    z_slice = params.get('z_slice')
    
    if x_slice is not None:
        bookmark_engine.toggle_slice_visibility('x', x_slice)
    if y_slice is not None:
        bookmark_engine.toggle_slice_visibility('y', y_slice)
    if z_slice is not None:
        bookmark_engine.toggle_slice_visibility('z', z_slice)
        
    bookmark_engine.update_params()
    
    print(f"After command execution:")
    print(f"  X visible: {bookmark_engine.curr_params.x_visible}")
    print(f"  Y visible: {bookmark_engine.curr_params.y_visible}")
    print(f"  Z visible: {bookmark_engine.curr_params.z_visible}")
    print(f"  Can undo: {bookmark_engine.can_undo}, undo_count: {bookmark_engine.undo_count}")
    
    # Simulate what send_state_update() would send
    print("\n3. Simulating state update that would be sent to Firebase...")
    state_data = {
        'current_params': bookmark_engine.curr_params.__dict__,
        'undo_redo_state': {
            'can_undo': bookmark_engine.can_undo,
            'can_redo': bookmark_engine.can_redo,
            'undo_count': getattr(bookmark_engine, 'undo_count', 0),
            'redo_count': getattr(bookmark_engine, 'redo_count', 0)
        }
    }
    
    print(f"State that would be sent to Firebase:")
    print(f"  X visible: {state_data['current_params']['x_visible']}")
    print(f"  Y visible: {state_data['current_params']['y_visible']}")
    print(f"  Z visible: {state_data['current_params']['z_visible']}")
    print(f"  Can undo: {state_data['undo_redo_state']['can_undo']}")
    print(f"  Undo count: {state_data['undo_redo_state']['undo_count']}")
    
    # Test undo
    print("\n4. Testing undo...")
    if bookmark_engine.can_undo:
        bookmark_engine.undo()
        print(f"After undo:")
        print(f"  X visible: {bookmark_engine.curr_params.x_visible}")
        print(f"  Y visible: {bookmark_engine.curr_params.y_visible}")
        print(f"  Z visible: {bookmark_engine.curr_params.z_visible}")
        print(f"  Can undo: {bookmark_engine.can_undo}, undo_count: {bookmark_engine.undo_count}")
    else:
        print("Cannot undo!")

if __name__ == "__main__":
    simulate_tornado_listener_command()