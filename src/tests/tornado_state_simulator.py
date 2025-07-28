#!/usr/bin/env python3
"""
Tornado State Simulator for Testing Enhanced NLP System

This simulates the tornado_listener.py sending state updates back to Firebase
for testing the two-way communication and real-time state sync.
"""

import sys
import time
import json
import random
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from firebase.firebase_config import FirebaseConfig


class TornadoStateSimulator:
    """Simulates Tornado engine state updates"""
    
    def __init__(self):
        """Initialize simulator"""
        self.firebase_config = FirebaseConfig()
        self.db = None
        self.user_id = "test_user_001"
        self.running = False
        
        # Simulated current state
        self.current_state = {
            'curr_params': {
                'x_position': 164000.0,
                'y_position': 115000.0,
                'z_position': 4000.0,
                'scale_x': 0.91,
                'scale_y': 0.91,
                'rotation': -0.785,
                'seismic_visible': True,
                'attribute_visible': False,
                'horizon_visible': False,
                'well_visible': True,
                'seismic_range': (-138548, 128647),
                'colormap_index': 2,
                'gain_value': 1.2
            },
            'can_undo': True,
            'can_redo': True,
            'undo_count': 3,
            'redo_count': 2,
            'available_templates': [
                'default_view',
                'structural_analysis',
                'amplitude_analysis',
                'frequency_analysis',
                'custom_view_1',
                'custom_view_2'
            ],
            'last_updated': time.time()
        }
    
    def initialize(self) -> bool:
        """Initialize Firebase connection"""
        if not self.firebase_config.initialize_firebase():
            print("❌ Failed to initialize Firebase")
            return False
        
        self.db = self.firebase_config.db
        print("✅ Tornado State Simulator initialized")
        return True
    
    def publish_current_state(self):
        """Publish current state to Firebase"""
        try:
            state_ref = self.db.collection('tornado_state').document(self.user_id)
            self.current_state['last_updated'] = time.time()
            state_ref.set(self.current_state)
            print(f"📤 Published state: X={self.current_state['curr_params']['x_position']:.0f}, Y={self.current_state['curr_params']['y_position']:.0f}")
            
        except Exception as e:
            print(f"❌ Error publishing state: {e}")
    
    def simulate_command_execution(self, command_data: dict):
        """Simulate executing a command and updating state"""
        method = command_data.get('method')
        params = command_data.get('params', {})
        
        print(f"🔄 Simulating command: {method} with params {params}")
        
        # Update state based on command
        if method == 'update_position':
            if 'x' in params:
                self.current_state['curr_params']['x_position'] = params['x']
            if 'y' in params:
                self.current_state['curr_params']['y_position'] = params['y']
            if 'z' in params:
                self.current_state['curr_params']['z_position'] = params['z']
                
        elif method == 'zoom_in':
            current_scale = self.current_state['curr_params']['scale_x']
            new_scale = min(3.0, current_scale * 1.2)
            self.current_state['curr_params']['scale_x'] = new_scale
            self.current_state['curr_params']['scale_y'] = new_scale
            
        elif method == 'zoom_out':
            current_scale = self.current_state['curr_params']['scale_x']
            new_scale = max(0.1, current_scale * 0.8)
            self.current_state['curr_params']['scale_x'] = new_scale
            self.current_state['curr_params']['scale_y'] = new_scale
            
        elif method == 'increase_gain':
            current_range = self.current_state['curr_params']['seismic_range']
            # Decrease range for higher gain
            new_range = (int(current_range[0] * 0.8), int(current_range[1] * 0.8))
            self.current_state['curr_params']['seismic_range'] = new_range
            
        elif method == 'update_visibility':
            if 'seismic' in params:
                self.current_state['curr_params']['seismic_visible'] = params['seismic']
            if 'attribute' in params:
                self.current_state['curr_params']['attribute_visible'] = params['attribute']
            if 'horizon' in params:
                self.current_state['curr_params']['horizon_visible'] = params['horizon']
                
        elif method == 'load_template':
            template_name = params.get('template_name', 'default_view')
            print(f"📋 Loading template: {template_name}")
            # Simulate template loading with random position changes
            self.current_state['curr_params']['x_position'] = random.randint(150000, 180000)
            self.current_state['curr_params']['y_position'] = random.randint(110000, 120000)
            self.current_state['curr_params']['z_position'] = random.randint(3000, 5000)
            
        elif method == 'undo':
            if self.current_state['can_undo']:
                self.current_state['undo_count'] -= 1
                self.current_state['redo_count'] += 1
                self.current_state['can_undo'] = self.current_state['undo_count'] > 0
                self.current_state['can_redo'] = True
                print("↶ Undo operation simulated")
                
        elif method == 'redo':
            if self.current_state['can_redo']:
                self.current_state['redo_count'] -= 1
                self.current_state['undo_count'] += 1
                self.current_state['can_redo'] = self.current_state['redo_count'] > 0
                self.current_state['can_undo'] = True
                print("↷ Redo operation simulated")
        
        # Update undo state for most commands
        if method not in ['undo', 'redo', 'show_current_state', 'list_templates']:
            self.current_state['undo_count'] += 1
            self.current_state['can_undo'] = True
            self.current_state['redo_count'] = 0
            self.current_state['can_redo'] = False
        
        # Publish updated state
        self.publish_current_state()
    
    def monitor_commands(self):
        """Monitor Firebase for incoming commands"""
        print("👁️ Monitoring Firebase for commands...")
        
        try:
            # Listen for new commands
            commands_ref = self.db.collection('command_queues').document(self.user_id).collection('commands')
            
            def on_command_change(col_snapshot, changes, read_time):
                for change in changes:
                    if change.type.name == 'ADDED':
                        command_data = change.document.to_dict()
                        if command_data.get('status') == 'queued':
                            print(f"📨 New command received: {command_data.get('method')}")
                            
                            # Simulate command execution
                            self.simulate_command_execution(command_data)
                            
                            # Update command status
                            change.document.reference.update({
                                'status': 'executed',
                                'result': {'success': True, 'simulated': True}
                            })
            
            # Set up real-time listener
            commands_ref.on_snapshot(on_command_change)
            
            # Keep monitoring
            while self.running:
                time.sleep(1)
                
        except Exception as e:
            print(f"❌ Error monitoring commands: {e}")
    
    def run(self):
        """Run the simulator"""
        if not self.initialize():
            return
        
        print("🚀 Starting Tornado State Simulator...")
        print("   This simulates tornado_listener.py with two-way communication")
        print("   Commands will be processed and state updates published")
        print()
        
        # Publish initial state
        self.publish_current_state()
        
        # Start monitoring
        self.running = True
        
        try:
            self.monitor_commands()
        except KeyboardInterrupt:
            print("\n👋 Stopping simulator...")
        finally:
            self.running = False


def main():
    """Run the simulator"""
    simulator = TornadoStateSimulator()
    simulator.run()


if __name__ == "__main__":
    main()