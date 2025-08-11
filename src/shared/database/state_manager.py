#!/usr/bin/env python3
"""
Two-way SQLite State Manager for Tornado Engine Integration

This module handles bidirectional communication between the NLP system and Tornado,
including current parameters, undo/redo state, and template management.
Replaces Firebase with local SQLite database.
"""

import json
import time
import threading
import uuid
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timezone
from .sqlite_manager import get_database
from .database_config import DatabaseConfig


class TornadoStateManager:
    """Manages two-way state synchronization with Tornado engine using SQLite"""
    
    def __init__(self, database_config: DatabaseConfig, user_id: str = "test_user_001"):
        """Initialize state manager"""
        self.db = database_config.db if database_config.db else get_database()
        self.user_id = user_id
        self.current_state = {}
        self.state_listeners = []
        self.monitoring = False
        self.monitor_thread = None
        self.cached_templates = []
        
        # Load existing state from database on startup
        try:
            existing_state = self.db.get_tornado_state(self.user_id)
            if existing_state:
                self.current_state = existing_state
                
                # Extract and cache templates if available
                if 'params' in existing_state and 'available_templates' in existing_state['params']:
                    templates = existing_state['params']['available_templates']
                    if templates:
                        self.cached_templates = templates
        except Exception as e:
            pass  # Silently handle errors
        
    def start_state_monitoring(self):
        """Start monitoring Tornado state changes"""
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_state_changes, daemon=True)
        self.monitor_thread.start()
    
    def stop_state_monitoring(self):
        """Stop monitoring state changes"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
    
    def _monitor_state_changes(self):
        """Monitor SQLite database for state updates from Tornado"""
        try:
            last_check_time = None
            
            while self.monitoring:
                try:
                    # Get current state from database
                    current_state = self.db.get_tornado_state(self.user_id)
                    
                    if current_state:
                        # Check if state has changed using database timestamp
                        state_timestamp = current_state.get('_db_timestamp')
                        
                        if state_timestamp != last_check_time:
                            last_check_time = state_timestamp
                            self._handle_state_update(current_state)
                    
                    # Poll every 0.5 seconds for responsive updates
                    time.sleep(0.5)
                    
                except Exception as e:
                    time.sleep(1)  # Wait longer on error
                    
        except Exception as e:
            pass  # Silently handle errors
    
    def _handle_state_update(self, new_state: Dict[str, Any]):
        """Handle incoming state update from Tornado"""
        self.current_state = new_state
        
        # Notify all listeners
        for listener in self.state_listeners:
            try:
                listener(new_state)
            except Exception as e:
                pass  # Silently handle listener errors
    
    def add_state_listener(self, callback: Callable[[Dict[str, Any]], None]):
        """Add a callback for state changes"""
        self.state_listeners.append(callback)
    
    def request_current_state(self) -> bool:
        """Request current state from Tornado engine"""
        try:
            # Send state request
            success = self.db.set_tornado_request(
                self.user_id,
                'get_current_state',
                {'timestamp': datetime.now(timezone.utc).isoformat()}
            )
            
            return success
            
        except Exception as e:
            return False
    
    def request_available_templates(self) -> bool:
        """Request list of available templates from Tornado"""
        try:
            success = self.db.set_tornado_request(
                self.user_id,
                'get_templates',
                {'timestamp': datetime.now(timezone.utc).isoformat()}
            )
            
            return success
            
        except Exception as e:
            return False
    
    def get_available_templates(self) -> List[str]:
        """Get cached list of available templates"""
        return self.cached_templates
    
    def format_current_state_for_llm(self) -> str:
        """Format current state for LLM context"""
        if not self.current_state:
            return "No current state available"
        
        try:
            # Extract parameters from JSON-RPC format if needed
            curr_params = self.current_state.get('curr_params', {})
            if 'params' in self.current_state:
                curr_params = self.current_state['params'].get('curr_params', curr_params)
            
            if not curr_params:
                return "Current state parameters not available"
            
            # Format key parameters for LLM
            state_info = []
            
            # Position
            if 'x_position' in curr_params:
                state_info.append(f"Position: X={curr_params['x_position']}, Y={curr_params['y_position']}, Z={curr_params['z_position']}")
            
            # Visibility
            if 'seismic_visible' in curr_params:
                visibility = []
                if curr_params.get('seismic_visible'): visibility.append("seismic")
                if curr_params.get('attribute_visible'): visibility.append("attributes")
                if curr_params.get('horizon_visible'): visibility.append("horizons")
                if curr_params.get('well_visible'): visibility.append("wells")
                state_info.append(f"Visible data: {', '.join(visibility) if visibility else 'none'}")
            
            # Slice visibility
            if 'x_visible' in curr_params:
                slices = []
                if curr_params.get('x_visible'): slices.append("X-slice")
                if curr_params.get('y_visible'): slices.append("Y-slice")
                if curr_params.get('z_visible'): slices.append("Z-slice")
                state_info.append(f"Visible slices: {', '.join(slices) if slices else 'none'}")
            
            # Scale and orientation
            if 'scale' in curr_params:
                scale = curr_params['scale']
                if isinstance(scale, list) and len(scale) >= 2:
                    state_info.append(f"Scale: {scale[0]:.3f} x {scale[1]:.3f}")
            
            if 'orient' in curr_params:
                orient = curr_params['orient']
                if isinstance(orient, list) and len(orient) >= 3:
                    rotation_deg = orient[2] * 180 / 3.14159
                    state_info.append(f"Rotation: {rotation_deg:.1f}°")
            
            return "; ".join(state_info)
            
        except Exception as e:
            return "Error formatting current state"
    
    def get_undo_redo_state(self) -> Dict[str, Any]:
        """Get current undo/redo state"""
        if not self.current_state:
            return {'can_undo': False, 'can_redo': False, 'undo_count': 0, 'redo_count': 0}
        
        try:
            # Extract undo/redo state from JSON-RPC format if needed
            undo_redo_state = self.current_state.get('undo_redo_state', {})
            if 'params' in self.current_state:
                undo_redo_state = self.current_state['params'].get('undo_redo_state', undo_redo_state)
            
            return {
                'can_undo': undo_redo_state.get('can_undo', False),
                'can_redo': undo_redo_state.get('can_redo', False),
                'undo_count': undo_redo_state.get('undo_count', 0),
                'redo_count': undo_redo_state.get('redo_count', 0)
            }
            
        except Exception as e:
            return {'can_undo': False, 'can_redo': False, 'undo_count': 0, 'redo_count': 0}
    
    def update_state(self, state_data: Dict[str, Any]) -> bool:
        """
        Update state in database (called by tornado_listener)
        
        Args:
            state_data: State data to store
            
        Returns:
            bool: True if successful
        """
        try:
            # Always update in-memory state first (immediate availability)
            self.current_state = state_data
            
            # Extract and cache templates if available
            if 'params' in state_data and 'available_templates' in state_data['params']:
                templates = state_data['params']['available_templates']
                if templates:
                    self.cached_templates = templates
            
            # Try to write to database (but don't fail if it doesn't work)
            try:
                success = self.db.set_tornado_state(self.user_id, state_data)
                return success
            except Exception as db_error:
                return False
            
        except Exception as e:
            return False
    
    def get_pending_requests(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get pending requests for tornado_listener to process
        
        Args:
            user_id: User identifier
            
        Returns:
            List of pending requests
        """
        try:
            # Get pending requests from tornado_requests table
            request = self.db.get_tornado_request(user_id)
            
            if request:
                return [{
                    'id': str(uuid.uuid4()),  # Generate ID for tracking
                    'type': request['request_type'],
                    'data': request.get('request_data', {}),
                    'timestamp': request['timestamp']
                }]
            
            return []
            
        except Exception as e:
            return []
    
    def mark_request_processed(self, request_id: str):
        """
        Mark request as processed (for compatibility with tornado_listener)
        
        Args:
            request_id: Request identifier
        """
        # Since get_tornado_request already removes the request,
        # this method is just for compatibility
        pass


class EnhancedCommandQueueManager:
    """Enhanced command queue manager with state integration"""
    
    def __init__(self, database_config: DatabaseConfig, state_manager: TornadoStateManager):
        """Initialize enhanced command queue manager"""
        self.db = database_config.db if database_config.db else get_database()
        self.state_manager = state_manager
        self.user_id = state_manager.user_id
    
    def add_command_with_context(self, method: str, params: Dict[str, Any] = None, 
                               feedback: str = None) -> str:
        """
        Add command with context and feedback
        
        Args:
            method: Command method name
            params: Command parameters
            feedback: User feedback message
            
        Returns:
            str: Command ID
        """
        import uuid
        command_id = str(uuid.uuid4())
        
        # Add context information
        if params is None:
            params = {}
        
        params['command_id'] = command_id
        params['user_id'] = self.user_id
        params['feedback'] = feedback
        
        print(f"📝 Inserting command into database: {command_id} - {method}")
        success = self.db.insert_command(command_id, self.user_id, method, params)
        
        return command_id
    
    def add_undo_command(self) -> str:
        """Add undo command to queue"""
        return self.add_command_with_context(
            method="undo",
            params={},
            feedback="Undoing last action..."
        )
    
    def add_redo_command(self) -> str:
        """Add redo command to queue"""
        return self.add_command_with_context(
            method="redo", 
            params={},
            feedback="Redoing last action..."
        )
    
    def add_template_command(self, template_name: str) -> str:
        """Add template load command to queue"""
        return self.add_command_with_context(
            method="load_template",
            params={"template_name": template_name},
            feedback=f"Loading template: {template_name}"
        )


def main():
    """Test state manager"""
    print("Testing SQLite State Manager...")
    
    # Initialize database
    from .database_config import DatabaseConfig
    config = DatabaseConfig()
    if not config.initialize_database():
        print("Failed to initialize database")
        return
    
    # Test state manager
    state_manager = TornadoStateManager(config)
    
    # Test state operations
    test_state = {
        'curr_params': {
            'x_position': 160112.5,
            'y_position': 112487.5,
            'z_position': 3500.0,
            'seismic_visible': True,
            'x_visible': True,
            'y_visible': True,
            'z_visible': False
        },
        'undo_redo_state': {
            'can_undo': True,
            'undo_count': 2,
            'can_redo': False,
            'redo_count': 0
        },
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    
    # Set state
    success = state_manager.db.set_tornado_state("test_user_001", test_state)
    print(f"Set state: {success}")
    
    # Get state
    retrieved_state = state_manager.db.get_tornado_state("test_user_001")
    print(f"Retrieved state: {retrieved_state is not None}")
    
    # Format for LLM
    state_manager.current_state = test_state
    formatted = state_manager.format_current_state_for_llm()
    print(f"Formatted state: {formatted}")
    
    print("State manager test completed")


if __name__ == "__main__":
    main()