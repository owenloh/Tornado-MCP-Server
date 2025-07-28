#!/usr/bin/env python3

import sys
import os
sys.path.append('src')

from firebase.firebase_config import FirebaseConfig, CommandQueueManager
import time

def test_firebase_queue():
    print("=== Testing Firebase Queue ===")
    
    # Initialize Firebase
    firebase_config = FirebaseConfig()
    if not firebase_config.initialize_firebase():
        print("❌ Failed to initialize Firebase")
        return
    
    queue_manager = CommandQueueManager(firebase_config)
    user_id = "test_user_001"
    
    print("1. Checking pending commands...")
    pending = queue_manager.get_pending_commands(user_id)
    print(f"Pending commands: {len(pending)}")
    for cmd in pending:
        print(f"  - {cmd.get('command_id', 'unknown')}: {cmd.get('method', 'unknown')} - {cmd.get('status', 'unknown')}")
    
    print("\n2. Checking recent commands...")
    # Get all commands for the user (not just pending)
    try:
        commands_ref = firebase_config.db.collection('command_queue').where('user_id', '==', user_id).order_by('timestamp', direction='DESCENDING').limit(10)
        commands = commands_ref.get()
        
        print(f"Recent commands: {len(commands)}")
        for doc in commands:
            data = doc.to_dict()
            print(f"  - {data.get('command_id', 'unknown')}: {data.get('method', 'unknown')} - {data.get('status', 'unknown')} - {data.get('timestamp', 'unknown')}")
    except Exception as e:
        print(f"Error getting recent commands: {e}")
    
    print("\n3. Checking current state...")
    try:
        state_ref = firebase_config.db.collection('tornado_state').document(user_id)
        state_doc = state_ref.get()
        
        if state_doc.exists:
            state_data = state_doc.to_dict()
            print("Current state in Firebase:")
            print(f"Raw state data: {state_data}")
            
            # Check current params
            current_params = state_data.get('current_params', {})
            if current_params:
                print(f"  X visible: {current_params.get('x_visible', 'unknown')}")
                print(f"  Y visible: {current_params.get('y_visible', 'unknown')}")
                print(f"  Z visible: {current_params.get('z_visible', 'unknown')}")
            else:
                print("  No current_params found")
            
            # Check undo/redo state
            undo_redo = state_data.get('undo_redo_state', {})
            if undo_redo:
                print(f"  Can undo: {undo_redo.get('can_undo', 'unknown')}")
                print(f"  Undo count: {undo_redo.get('undo_count', 'unknown')}")
                print(f"  Can redo: {undo_redo.get('can_redo', 'unknown')}")
                print(f"  Redo count: {undo_redo.get('redo_count', 'unknown')}")
            else:
                print("  No undo_redo_state found")
            
            print(f"  Timestamp: {state_data.get('timestamp', 'unknown')}")
        else:
            print("No state document found in Firebase")
    except Exception as e:
        print(f"Error getting current state: {e}")

if __name__ == "__main__":
    test_firebase_queue()