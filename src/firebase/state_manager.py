#!/usr/bin/env python3
"""
Two-way Firebase State Manager for Tornado Engine Integration

This module handles bidirectional communication between the NLP system and Tornado,
including current parameters, undo/redo state, and template management.
"""

import json
import time
import threading
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timezone
from firebase_admin import firestore
from .firebase_config import FirebaseConfig


class TornadoStateManager:
    """Manages two-way state synchronization with Tornado engine"""
    
    def __init__(self, firebase_config: FirebaseConfig, user_id: str = "test_user_001"):
        """Initialize state manager"""
        self.db = firebase_config.db
        self.user_id = user_id
        self.current_state = {}
        self.state_listeners = []
        self.monitoring = False
        self.monitor_thread = None
        
    def start_state_monitoring(self):
        """Start monitoring Tornado state changes"""
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_state_changes, daemon=True)
        self.monitor_thread.start()
        print("🔄 Started Tornado state monitoring")
    
    def stop_state_monitoring(self):
        """Stop monitoring state changes"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        print("⏹️ Stopped Tornado state monitoring")
    
    def _monitor_state_changes(self):
        """Monitor Firebase for state updates from Tornado"""
        try:
            # Listen to state updates from Tornado
            state_ref = self.db.collection('tornado_state').document(self.user_id)
            
            def on_state_change(doc_snapshot, changes, read_time):
                for change in changes:
                    if change.type.name in ['ADDED', 'MODIFIED']:
                        new_state = change.document.to_dict()
                        self._handle_state_update(new_state)
            
            # Set up real-time listener
            state_ref.on_snapshot(on_state_change)
            
            # Keep thread alive
            while self.monitoring:
                time.sleep(1)
                
        except Exception as e:
            print(f"❌ Error monitoring state changes: {e}")
    
    def _handle_state_update(self, new_state: Dict[str, Any]):
        """Handle incoming state update from Tornado"""

        self.current_state = new_state
        
        # Notify all listeners
        for listener in self.state_listeners:
            try:
                listener(new_state)
            except Exception as e:
                print(f"⚠️ Error in state listener: {e}")
    
    def add_state_listener(self, callback: Callable[[Dict[str, Any]], None]):
        """Add a callback for state changes"""
        self.state_listeners.append(callback)
    
    def request_current_state(self) -> bool:
        """Request current state from Tornado engine"""
        try:
            # Send state request command
            request_ref = self.db.collection('tornado_requests').document(self.user_id)
            request_ref.set({
                'type': 'get_current_state',
                'timestamp': firestore.SERVER_TIMESTAMP,
                'user_id': self.user_id
            })
            print("📤 Requested current state from Tornado")
            return True
            
        except Exception as e:
            print(f"❌ Error requesting current state: {e}")
            return False
    
    def request_available_templates(self) -> bool:
        """Request list of available templates from Tornado"""
        try:
            request_ref = self.db.collection('tornado_requests').document(self.user_id)
            request_ref.set({
                'type': 'get_templates',
                'timestamp': firestore.SERVER_TIMESTAMP,
                'user_id': self.user_id
            })
            print("📤 Requested available templates from Tornado")
            return True
            
        except Exception as e:
            print(f"❌ Error requesting templates: {e}")
            return False
    
    def load_template(self, template_name: str) -> bool:
        """Request to load a specific template"""
        try:
            request_ref = self.db.collection('tornado_requests').document(self.user_id)
            request_ref.set({
                'type': 'load_template',
                'template_name': template_name,
                'timestamp': firestore.SERVER_TIMESTAMP,
                'user_id': self.user_id
            })
            print(f"📤 Requested to load template: {template_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error requesting template load: {e}")
            return False
    
    def request_undo(self) -> bool:
        """Request undo operation"""
        try:
            request_ref = self.db.collection('tornado_requests').document(self.user_id)
            request_ref.set({
                'type': 'undo',
                'timestamp': firestore.SERVER_TIMESTAMP,
                'user_id': self.user_id
            })
            print("📤 Requested undo operation")
            return True
            
        except Exception as e:
            print(f"❌ Error requesting undo: {e}")
            return False
    
    def request_redo(self) -> bool:
        """Request redo operation"""
        try:
            request_ref = self.db.collection('tornado_requests').document(self.user_id)
            request_ref.set({
                'type': 'redo',
                'timestamp': firestore.SERVER_TIMESTAMP,
                'user_id': self.user_id
            })
            print("📤 Requested redo operation")
            return True
            
        except Exception as e:
            print(f"❌ Error requesting redo: {e}")
            return False
    
    def get_current_parameters(self) -> Dict[str, Any]:
        """Get current parameters from cached state"""
        return self.current_state.get('curr_params', {})
    
    def get_undo_redo_state(self) -> Dict[str, Any]:
        """Get undo/redo availability"""
        return {
            'can_undo': self.current_state.get('can_undo', False),
            'can_redo': self.current_state.get('can_redo', False),
            'undo_count': self.current_state.get('undo_count', 0),
            'redo_count': self.current_state.get('redo_count', 0)
        }
    
    def get_available_templates(self) -> List[str]:
        """Get list of available templates"""
        # Check top level first
        templates = self.current_state.get('available_templates', [])
        
        # Check nested in params (JSON-RPC format)
        if not templates and 'params' in self.current_state:
            templates = self.current_state['params'].get('available_templates', [])
        
        return templates
    
    def format_current_state_for_llm(self) -> str:
        """Format current state for LLM context"""
        params = self.get_current_parameters()
        undo_redo = self.get_undo_redo_state()
        templates = self.get_available_templates()
        
        state_text = "CURRENT TORNADO STATE:\n"
        
        # Current parameters
        if params:
            state_text += f"Position: X={params.get('x_position', 'Unknown')}, Y={params.get('y_position', 'Unknown')}, Z={params.get('z_position', 'Unknown')}\n"
            state_text += f"Scale: X={params.get('scale_x', 'Unknown')}, Y={params.get('scale_y', 'Unknown')}\n"
            state_text += f"Rotation: {params.get('rotation', 'Unknown')} radians\n"
            state_text += f"Visibility: Seismic={params.get('seismic_visible', 'Unknown')}, Attributes={params.get('attribute_visible', 'Unknown')}, Horizons={params.get('horizon_visible', 'Unknown')}\n"
            state_text += f"Gain Range: {params.get('seismic_range', 'Unknown')}\n"
        else:
            state_text += "Parameters: Not available (requesting from Tornado...)\n"
        
        # Undo/Redo state
        state_text += f"\nUNDO/REDO STATE:\n"
        state_text += f"Can Undo: {undo_redo['can_undo']} ({undo_redo['undo_count']} operations)\n"
        state_text += f"Can Redo: {undo_redo['can_redo']} ({undo_redo['redo_count']} operations)\n"
        
        # Available templates
        if templates:
            state_text += f"\nAVAILABLE TEMPLATES:\n"
            for i, template in enumerate(templates, 1):
                state_text += f"{i}. {template}\n"
        else:
            state_text += "\nAVAILABLE TEMPLATES: Requesting from Tornado...\n"
        
        return state_text


class EnhancedCommandQueueManager:
    """Enhanced command queue manager with state synchronization"""
    
    def __init__(self, firebase_config: FirebaseConfig, state_manager: TornadoStateManager):
        """Initialize enhanced command queue manager"""
        self.db = firebase_config.db
        self.state_manager = state_manager
        self.user_id = state_manager.user_id
    
    def add_command_with_context(self, command_data: Dict[str, Any], current_context: Dict[str, Any] = None) -> str:
        """Add command with current context for better execution"""
        try:
            command_id = str(__import__('uuid').uuid4())
            
            # Get current state for context
            if not current_context:
                current_context = self.state_manager.get_current_parameters()
            
            # Prepare enhanced command document
            command_doc = {
                'command_id': command_id,
                'user_id': self.user_id,
                'method': command_data.get('method'),
                'params': command_data.get('params', {}),
                'context': current_context,  # Include current state
                'status': 'queued',
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP,
                'priority': command_data.get('priority', 1),
                'retry_count': 0,
                'max_retries': 3
            }
            
            # Add to command queue
            command_ref = self.db.collection('command_queues').document(self.user_id).collection('commands').document(command_id)
            command_ref.set(command_doc)
            
            print(f"📤 Command {command_id} added with context: {command_data.get('method')}")
            return command_id
            
        except Exception as e:
            print(f"❌ Error adding command with context: {e}")
            return None
    
    def add_template_command(self, template_name: str) -> str:
        """Add command to load a specific template"""
        command_data = {
            'method': 'load_template',
            'params': {'template_name': template_name}
        }
        return self.add_command_with_context(command_data)
    
    def add_undo_command(self) -> str:
        """Add undo command"""
        command_data = {
            'method': 'undo',
            'params': {}
        }
        return self.add_command_with_context(command_data)
    
    def add_redo_command(self) -> str:
        """Add redo command"""
        command_data = {
            'method': 'redo', 
            'params': {}
        }
        return self.add_command_with_context(command_data)


def main():
    """Test the enhanced state manager"""
    print("🧪 Testing Enhanced Tornado State Manager...")
    
    # Initialize Firebase
    firebase_config = FirebaseConfig()
    if not firebase_config.initialize_firebase():
        print("❌ Failed to initialize Firebase")
        return
    
    # Initialize state manager
    state_manager = TornadoStateManager(firebase_config)
    
    # Add state change listener
    def on_state_change(new_state):
        print(f"🔄 State updated: {new_state}")
    
    state_manager.add_state_listener(on_state_change)
    
    # Start monitoring
    state_manager.start_state_monitoring()
    
    # Request current state
    state_manager.request_current_state()
    state_manager.request_available_templates()
    
    # Test enhanced command queue
    enhanced_queue = EnhancedCommandQueueManager(firebase_config, state_manager)
    
    # Add test commands
    enhanced_queue.add_template_command("default_view")
    enhanced_queue.add_undo_command()
    
    print("✅ Enhanced state manager test completed")
    
    # Keep running for a bit to test real-time updates
    try:
        time.sleep(10)
    except KeyboardInterrupt:
        pass
    finally:
        state_manager.stop_state_monitoring()


if __name__ == "__main__":
    main()