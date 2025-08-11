#!/usr/bin/env python3
"""
JSON-RPC Terminal Interface for Seismic Navigation Commands

This module provides a terminal-based interface where users can type JSON-RPC
commands that get sent to Firebase queue for processing by the Tornado listener.

Task 3.3: Create command queue client for AI_laptop
- Implement CommandQueueManager class for sending commands to Firebase
- Add command serialization and queue management
- Create status monitoring and feedback mechanisms
- Implement user session isolation and command tracking
"""

import json
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional
import threading

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

# Setup Windows virtual environment for LLM dependencies
try:
    from shared.utils.venv_setup import ensure_windows_venv
    ensure_windows_venv()
except ImportError as e:
    print(f"Warning: Failed to setup Windows virtual environment: {e}")
    # Continue anyway for development/testing

from shared.database.database_config import DatabaseConfig
from shared.database.command_queue_manager import CommandQueueManager


class JSONRPCTerminal:
    """Terminal interface for JSON-RPC commands to seismic navigation system"""
    
    # Available commands from bookmark_gui_tkinter_tornadoless.py
    AVAILABLE_COMMANDS = {
        # Position/Navigation commands
        'update_position': {
            'description': 'Update crossline/inline/depth position',
            'params': ['x', 'y', 'z'],
            'example': '{"method": "update_position", "params": {"x": 160000, "y": 112000, "z": 3500}}'
        },
        'update_orientation': {
            'description': 'Update view rotation angles (radians)',
            'params': ['rot1', 'rot2', 'rot3'],
            'example': '{"method": "update_orientation", "params": {"rot1": 0, "rot2": 0.39, "rot3": -0.78}}'
        },
        'update_scale': {
            'description': 'Update zoom/scale values',
            'params': ['scale_x', 'scale_y'],
            'example': '{"method": "update_scale", "params": {"scale_x": 1.0, "scale_y": 1.0}}'
        },
        'update_shift': {
            'description': 'Update view shift/translation',
            'params': ['shift_x', 'shift_y', 'shift_z'],
            'example': '{"method": "update_shift", "params": {"shift_x": -1000, "shift_y": 500, "shift_z": -1600}}'
        },
        
        # Visibility commands
        'update_visibility': {
            'description': 'Toggle data visibility (seismic, attribute, horizon, well)',
            'params': ['seismic', 'attribute', 'horizon', 'well'],
            'example': '{"method": "update_visibility", "params": {"seismic": true, "attribute": false, "horizon": false, "well": true}}'
        },
        'update_slice_visibility': {
            'description': 'Toggle slice visibility (x_slice, y_slice, z_slice)',
            'params': ['x_slice', 'y_slice', 'z_slice'],
            'example': '{"method": "update_slice_visibility", "params": {"x_slice": true, "y_slice": false, "z_slice": false}}'
        },
        
        # Display adjustment commands
        'update_gain': {
            'description': 'Adjust gain/amplitude range',
            'params': ['gain_value'],
            'example': '{"method": "update_gain", "params": {"gain_value": 1.5}}'
        },
        'update_colormap': {
            'description': 'Change colormap index (0-15)',
            'params': ['colormap_index'],
            'example': '{"method": "update_colormap", "params": {"colormap_index": 3}}'
        },
        'update_color_scale': {
            'description': 'Adjust color scale times multiplier',
            'params': ['times_value'],
            'example': '{"method": "update_color_scale", "params": {"times_value": 2}}'
        },
        
        # Quick action commands (no parameters)
        'increase_gain': {
            'description': 'Increase gain by preset amount',
            'params': [],
            'example': '{"method": "increase_gain", "params": {}}'
        },
        'decrease_gain': {
            'description': 'Decrease gain by preset amount',
            'params': [],
            'example': '{"method": "decrease_gain", "params": {}}'
        },
        'rotate_left': {
            'description': 'Rotate view left',
            'params': [],
            'example': '{"method": "rotate_left", "params": {}}'
        },
        'rotate_right': {
            'description': 'Rotate view right',
            'params': [],
            'example': '{"method": "rotate_right", "params": {}}'
        },
        'zoom_in': {
            'description': 'Zoom in',
            'params': [],
            'example': '{"method": "zoom_in", "params": {}}'
        },
        'zoom_out': {
            'description': 'Zoom out',
            'params': [],
            'example': '{"method": "zoom_out", "params": {}}'
        },
        'zoom_reset': {
            'description': 'Reset zoom to default',
            'params': [],
            'example': '{"method": "zoom_reset", "params": {}}'
        },
        
        # State management commands
        'undo_action': {
            'description': 'Undo last change',
            'params': [],
            'example': '{"method": "undo_action", "params": {}}'
        },
        'redo_action': {
            'description': 'Redo last undone change',
            'params': [],
            'example': '{"method": "redo_action", "params": {}}'
        },
        'reset_parameters': {
            'description': 'Reset all parameters to defaults',
            'params': [],
            'example': '{"method": "reset_parameters", "params": {}}'
        },
        'reload_template': {
            'description': 'Reload bookmark template',
            'params': [],
            'example': '{"method": "reload_template", "params": {}}'
        }
    }
    
    def __init__(self):
        """Initialize JSON-RPC terminal interface"""
        self.firebase_config = FirebaseConfig()
        self.queue_manager = None
        self.running = False
        self.status_monitor_thread = None
        
    def initialize(self) -> bool:
        """
        Initialize Firebase connection and command queue manager
        
        Returns:
            bool: True if initialization successful
        """
        print("Initializing JSON-RPC Terminal for Seismic Navigation...")
        
        if not self.firebase_config.initialize_firebase():
            print("❌ Failed to initialize Firebase connection")
            return False
            
        self.queue_manager = CommandQueueManager(self.firebase_config)
        print("✅ Firebase connection established")
        print("✅ Command queue manager initialized")
        return True
    
    def show_help(self):
        """Display available commands and usage information"""
        print("\n" + "="*80)
        print("SEISMIC NAVIGATION JSON-RPC TERMINAL")
        print("="*80)
        print("\nAvailable Commands:")
        print("-" * 50)
        
        for cmd_name, cmd_info in self.AVAILABLE_COMMANDS.items():
            print(f"\n🔧 {cmd_name}")
            print(f"   Description: {cmd_info['description']}")
            if cmd_info['params']:
                print(f"   Parameters: {', '.join(cmd_info['params'])}")
            else:
                print("   Parameters: None")
            print(f"   Example: {cmd_info['example']}")
        
        print("\n" + "-" * 50)
        print("Special Commands:")
        print("  help     - Show this help message")
        print("  status   - Show system status")
        print("  quit     - Exit the terminal")
        print("  clear    - Clear the screen")
        
        print("\n" + "-" * 50)
        print("Usage:")
        print("1. Type a JSON-RPC command and press Enter")
        print("2. Commands are sent to Firebase queue for Tornado listener")
        print("3. Status updates will be shown automatically")
        print("4. Use 'help' to see available commands")
        print("="*80 + "\n")
    
    def validate_command(self, command_data: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate JSON-RPC command structure and parameters
        
        Args:
            command_data: Parsed JSON command data
            
        Returns:
            tuple: (is_valid, error_message)
        """
        # Check required fields
        if 'method' not in command_data:
            return False, "Missing 'method' field"
        
        method = command_data['method']
        if method not in self.AVAILABLE_COMMANDS:
            return False, f"Unknown method '{method}'. Use 'help' to see available commands."
        
        # Check params field exists
        if 'params' not in command_data:
            return False, "Missing 'params' field"
        
        params = command_data['params']
        if not isinstance(params, dict):
            return False, "'params' must be a dictionary"
        
        # Validate parameters for the specific method
        expected_params = self.AVAILABLE_COMMANDS[method]['params']
        
        # For methods with no parameters, params should be empty
        if not expected_params and params:
            return False, f"Method '{method}' expects no parameters, but got: {list(params.keys())}"
        
        # For methods with parameters, check if all required params are present
        if expected_params:
            missing_params = [p for p in expected_params if p not in params]
            if missing_params:
                return False, f"Missing required parameters: {missing_params}"
            
            # Check for unexpected parameters
            extra_params = [p for p in params.keys() if p not in expected_params]
            if extra_params:
                return False, f"Unexpected parameters: {extra_params}"
        
        return True, ""
    
    def send_command(self, command_data: Dict[str, Any]) -> Optional[str]:
        """
        Send validated command to Firebase queue
        
        Args:
            command_data: Validated command data
            
        Returns:
            str: Command ID if successful, None if failed
        """
        try:
            command_id = self.queue_manager.add_command(command_data)
            if command_id:
                print(f"✅ Command sent to queue: {command_id}")
                print(f"   Method: {command_data['method']}")
                if command_data['params']:
                    print(f"   Parameters: {command_data['params']}")
                return command_id
            else:
                print("❌ Failed to send command to queue")
                return None
                
        except Exception as e:
            print(f"❌ Error sending command: {e}")
            return None
    
    def show_status(self):
        """Show system and queue status"""
        try:
            print("\n" + "="*50)
            print("SYSTEM STATUS")
            print("="*50)
            
            # Get pending commands count
            pending_commands = self.queue_manager.get_pending_commands()
            print(f"📋 Pending commands: {len(pending_commands)}")
            
            if pending_commands:
                print("\nPending Commands:")
                for i, cmd in enumerate(pending_commands[:5], 1):  # Show first 5
                    print(f"  {i}. {cmd['method']} (ID: {cmd['command_id'][:8]}...)")
                if len(pending_commands) > 5:
                    print(f"  ... and {len(pending_commands) - 5} more")
            
            # Try to get system status from Firebase
            try:
                system_ref = self.firebase_config.db.collection('system_status').document('tornado_listener')
                system_doc = system_ref.get()
                if system_doc.exists:
                    system_data = system_doc.to_dict()
                    status = system_data.get('status', 'unknown')
                    print(f"🖥️  Tornado Listener: {status}")
                    if 'last_heartbeat' in system_data:
                        print(f"💓 Last heartbeat: {system_data['last_heartbeat']}")
                else:
                    print("🖥️  Tornado Listener: No status available")
            except Exception as e:
                print(f"🖥️  Tornado Listener: Error getting status - {e}")
            
            print("="*50 + "\n")
            
        except Exception as e:
            print(f"❌ Error getting status: {e}")
    
    def start_status_monitor(self):
        """Start background thread to monitor command status updates"""
        def monitor_status():
            """Background monitoring function"""
            last_check = time.time()
            
            while self.running:
                try:
                    time.sleep(2)  # Check every 2 seconds
                    
                    # Check for recently completed commands
                    # This is a simplified version - in production you'd use Firebase listeners
                    current_time = time.time()
                    if current_time - last_check > 5:  # Check every 5 seconds
                        # Could implement real-time status updates here
                        last_check = current_time
                        
                except Exception as e:
                    if self.running:  # Only print error if we're still running
                        print(f"\n⚠️  Status monitor error: {e}")
                    break
        
        self.status_monitor_thread = threading.Thread(target=monitor_status, daemon=True)
        self.status_monitor_thread.start()
    
    def run(self):
        """Main terminal loop"""
        if not self.initialize():
            return
        
        self.running = True
        self.start_status_monitor()
        
        print("🚀 JSON-RPC Terminal ready!")
        print("Type 'help' for available commands, 'quit' to exit")
        print("-" * 50)
        
        try:
            while self.running:
                try:
                    # Get user input
                    user_input = input("\n🔧 seismic> ").strip()
                    
                    if not user_input:
                        continue
                    
                    # Handle special commands
                    if user_input.lower() == 'quit':
                        print("👋 Goodbye!")
                        break
                    elif user_input.lower() == 'help':
                        self.show_help()
                        continue
                    elif user_input.lower() == 'status':
                        self.show_status()
                        continue
                    elif user_input.lower() == 'clear':
                        import os
                        os.system('cls' if os.name == 'nt' else 'clear')
                        continue
                    
                    # Try to parse as JSON
                    try:
                        command_data = json.loads(user_input)
                    except json.JSONDecodeError as e:
                        print(f"❌ Invalid JSON: {e}")
                        print("💡 Tip: Use double quotes for strings, e.g., {\"method\": \"zoom_in\", \"params\": {}}")
                        continue
                    
                    # Validate command
                    is_valid, error_msg = self.validate_command(command_data)
                    if not is_valid:
                        print(f"❌ Invalid command: {error_msg}")
                        continue
                    
                    # Send command
                    command_id = self.send_command(command_data)
                    if command_id:
                        print("⏳ Command queued for processing...")
                    
                except KeyboardInterrupt:
                    print("\n👋 Goodbye!")
                    break
                except Exception as e:
                    print(f"❌ Unexpected error: {e}")
                    
        finally:
            self.running = False
            if self.status_monitor_thread:
                self.status_monitor_thread.join(timeout=1)


def main():
    """Main function to run the JSON-RPC terminal"""
    try:
        terminal = JSONRPCTerminal()
        terminal.run()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()