#!/usr/bin/env python3
"""
Tornado Listener Service for Processing Firebase Command Queue

This script runs continuously inside Tornado and processes commands from Firebase queue.
It must never terminate or Tornado will close.

Task 3.2: Implement tornado_listener.py for continuous command processing
- Create main listener loop that never exits (critical for Tornado)
- Implement initialization sequence (load seismic data, set default view)
- Implement Firebase queue polling with error handling
- Add command deserialization and validation
- Integrate bookmark manipulation functions from Stage 1
- Add command status reporting back to Firebase
- Include comprehensive error handling and logging
"""

import sys
import time
import json
import traceback
import os
import copy
import uuid
from pathlib import Path
from typing import Dict, Any, Optional
import logging
from datetime import datetime, timezone

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Import Tornado API modules (these are available directly in Tornado environment)
try:
    # Specific imports from vision module - everything should be in vision
    from vision import (
        vision
    )
    TORNADO_AVAILABLE = True
except ImportError:
    # For development/testing outside Tornado
    print("Warning: Tornado API not available - running in development mode")
    TORNADO_AVAILABLE = False

# Import our bookmark engine and Firebase components
from core.bookmark_engine_v2 import BookmarkHTMLEngineV2
from firebase.firebase_config import FirebaseConfig, CommandQueueManager
from protocols.jsonrpc_protocol import JSONRPCProtocol, TornadoStateProtocol
from utils.config_loader import get_config


class TornadoListener:
    """
    Tornado listener service that processes commands from Firebase queue
    
    This service runs continuously inside Tornado and must never terminate.
    It polls Firebase for new commands and executes them using the bookmark engine.
    """
    
    def __init__(self):
        """Initialize Tornado listener service"""
        self.firebase_config = None
        self.queue_manager = None
        self.bookmark_engine = None
        self.running = False
        self.user_id = "test_user_001"  # Default user for testing
        
        # Setup logging
        self.setup_logging()
        
        # Command method mapping
        self.command_methods = {
            'update_position': self.handle_update_position,
            'update_orientation': self.handle_update_orientation,
            'update_scale': self.handle_update_scale,
            'update_shift': self.handle_update_shift,
            'update_visibility': self.handle_update_visibility,
            'update_slice_visibility': self.handle_update_slice_visibility,
            'update_gain': self.handle_update_gain,
            'update_colormap': self.handle_update_colormap,
            'update_color_scale': self.handle_update_color_scale,
            'increase_gain': self.handle_increase_gain,
            'decrease_gain': self.handle_decrease_gain,
            'rotate_left': self.handle_rotate_left,
            'rotate_right': self.handle_rotate_right,
            'zoom_in': self.handle_zoom_in,
            'zoom_out': self.handle_zoom_out,
            'zoom_reset': self.handle_zoom_reset,
            'undo_action': self.handle_undo_action,
            'undo': self.handle_undo_action,  # Alias for undo_action
            'redo_action': self.handle_redo_action,
            'redo': self.handle_redo_action,  # Alias for redo_action
            'reset_parameters': self.handle_reset_parameters,
            'reload_template': self.handle_reload_template,
            'load_template': self.handle_load_template,  # Add missing load_template mapping
            'query_state': self.handle_query_state
        }
    
    def setup_logging(self):
        """Setup logging for the listener service"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('tornado_listener.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger('TornadoListener')
    
    def initialize_seismic_view(self) -> bool:
        """
        Initialize seismic data and default view in Tornado
        
        Returns:
            bool: True if initialization successful
        """
        try:
            self.logger.info("Initializing seismic view in Tornado...")
            
            if TORNADO_AVAILABLE:
                # Load seismic data from config
                config = get_config()
                seismic_path = config.get_seismic_path()
                self.logger.info(f"Loading seismic data from: {seismic_path}")
                vision.loadSeismic(seismic_path)
                
                '''
                # Show seismic data initially
                self.logger.info("Setting seismic data visibility...")
                vision.setDataTypeVis(DataVis.SEIS)
                
                # Load default bookmark with proper slice visibility
                # This replaces: vision.setSliceVis(SliceVis.X)
                self.logger.info("Loading default bookmark...")
                default_bookmark = BookmarkLocation()
                default_bookmark.load('default_bookmark.html')
                default_bookmark.selectBookmark('default')
                default_bookmark.updateDisplay(True)
                '''
                
                self.logger.info("✅ Seismic view initialized successfully")
            else:
                self.logger.warning("Tornado API not available - skipping seismic initialization")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error initializing seismic view: {e}")
            self.logger.error(traceback.format_exc())
            return False
    
    def initialize_firebase(self) -> bool:
        """
        Initialize Firebase connection and command queue manager
        
        Returns:
            bool: True if initialization successful
        """
        try:
            self.logger.info("Initializing Firebase connection...")
            
            self.firebase_config = FirebaseConfig()
            if not self.firebase_config.initialize_firebase():
                self.logger.error("Failed to initialize Firebase")
                return False
            
            self.queue_manager = CommandQueueManager(self.firebase_config)
            self.logger.info("✅ Firebase connection established")
            
            # Update system status to online
            self.update_system_status('online')
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error initializing Firebase: {e}")
            return False
    
    def initialize_bookmark_engine(self) -> bool:
        """
        Initialize bookmark HTML manipulation engine
        
        Returns:
            bool: True if initialization successful
        """
        try:
            self.logger.info("Initializing bookmark engine...")
            
            # Initialize with Tornado mode based on TORNADO_AVAILABLE
            config = get_config()
            default_template = config.get_default_template()
            self.bookmark_engine = BookmarkHTMLEngineV2(default_template, in_tornado=TORNADO_AVAILABLE)
            
            self.logger.info("✅ Bookmark engine initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error initializing bookmark engine: {e}")
            self.logger.error(traceback.format_exc())
            return False
    
    def update_system_status(self, status: str):
        """
        Update system status in Firebase
        
        Args:
            status: Current system status (online, offline, error)
        """
        try:
            if self.firebase_config and self.firebase_config.db:
                from firebase_admin import firestore
                system_ref = self.firebase_config.db.collection('system_status').document('tornado_listener')
                system_ref.update({
                    'status': status,
                    'last_heartbeat': firestore.SERVER_TIMESTAMP
                })
        except Exception as e:
            self.logger.warning(f"Failed to update system status: {e}")
    
    def cleanup(self):
        """Clean shutdown of Firebase connections and resources"""
        try:
            self.logger.info("Cleaning up resources...")
            
            # Update status to offline
            self.update_system_status('offline')
            
            # Close Firebase connections gracefully
            if self.firebase_config and self.firebase_config.app:
                import firebase_admin
                try:
                    firebase_admin.delete_app(self.firebase_config.app)
                    self.logger.info("Firebase app deleted successfully")
                except Exception as e:
                    self.logger.warning(f"Error deleting Firebase app: {e}")
                    
        except Exception as e:
            self.logger.warning(f"Error during cleanup: {e}")
    
    def process_command_queue(self):
        """Process pending commands from Firebase queue"""
        try:
            # Process tornado_requests (state queries, template requests, etc.)
            self.process_tornado_requests()
            
            # Get pending commands for current user
            pending_commands = self.queue_manager.get_pending_commands(self.user_id)
            
            # Limit processing to prevent infinite loops
            max_commands_per_cycle = 10
            processed_count = 0
            
            for command in pending_commands:
                # Limit processing to prevent infinite loops
                if processed_count >= max_commands_per_cycle:
                    self.logger.warning(f"⚠️ Reached max commands per cycle ({max_commands_per_cycle}), will continue next cycle")
                    break
                
                try:
                    # Get command ID (could be 'command_id' or 'doc_id')
                    cmd_id = command.get('command_id') or command.get('doc_id', 'unknown')
                    method = command.get('method', 'unknown')
                    
                    # Skip if command is malformed
                    if not method or method == 'unknown':
                        self.logger.error(f"❌ Malformed command, marking as failed: {command}")
                        if cmd_id != 'unknown':
                            self.queue_manager.update_command_status(cmd_id, 'failed', error="Malformed command")
                        processed_count += 1
                        continue
                    
                    self.logger.info(f"Processing command: {cmd_id} - {method}")
                    
                    # Update command status to processing
                    self.queue_manager.update_command_status(cmd_id, 'processing')
                    processed_count += 1
                    
                    # Execute the command
                    result = self.execute_command(command)
                    
                    # Check if result is JSON-RPC response
                    if result.get('jsonrpc') == '2.0':
                        if 'result' in result:
                            # Success - add current state
                            result['result']['current_state'] = {
                                'can_undo': self.bookmark_engine.can_undo,
                                'can_redo': self.bookmark_engine.can_redo,
                                'current_params': self.bookmark_engine.curr_params.__dict__
                            }
                            
                            # Update command status to executed
                            self.queue_manager.update_command_status(
                                cmd_id, 
                                'executed', 
                                result=result
                            )
                            self.logger.info(f"✅ Command {cmd_id} executed successfully")
                        else:
                            # Error response
                            self.queue_manager.update_command_status(
                                cmd_id, 
                                'failed', 
                                error=result.get('error', {}).get('message', 'Unknown error')
                            )
                            self.logger.error(f"❌ Command {cmd_id} failed: {result.get('error', {}).get('message')}")
                    else:
                        # Legacy format - treat as error
                        self.queue_manager.update_command_status(
                            cmd_id, 
                            'failed', 
                            error="Invalid response format"
                        )
                        self.logger.error(f"❌ Command {cmd_id} returned invalid format")
                
                except Exception as e:
                    self.logger.error(f"❌ Error processing command {cmd_id}: {e}")
                    self.logger.error(traceback.format_exc())
                    
                    # Update command status to failed to prevent reprocessing
                    try:
                        self.queue_manager.update_command_status(
                            cmd_id, 
                            'failed',
                            error=str(e)
                        )
                    except Exception as status_error:
                        self.logger.error(
                            f"❌ Failed to update command status: {status_error}",
                            error=str(e)
                        )
        
        except Exception as e:
            self.logger.error(f"❌ Error in process_command_queue: {e}")
            self.logger.error(traceback.format_exc())
    
    def process_tornado_requests(self):
        """Process requests from tornado_requests collection"""
        try:
            # Check for pending requests
            request_ref = self.firebase_config.db.collection('tornado_requests').document(self.user_id)
            request_doc = request_ref.get()
            
            if request_doc.exists:
                request_data = request_doc.to_dict()
                request_type = request_data.get('type')
                
                if request_type == 'get_templates':
                    # Handle template request
                    result = self.handle_get_templates({})
                    
                    # Send response to tornado_state
                    state_update = {
                        'jsonrpc': '2.0',
                        'method': 'state_update',
                        'id': str(uuid.uuid4()),
                        'params': {
                            'available_templates': result.get('templates', []),
                            'timestamp': datetime.now(timezone.utc).isoformat()
                        }
                    }
                    
                    state_ref = self.firebase_config.db.collection('tornado_state').document(self.user_id)
                    state_ref.set(state_update)
                    
                    # Clear the request
                    request_ref.delete()
                    self.logger.info(f"📤 Processed template request: {len(result.get('templates', []))} templates")
                
                elif request_type == 'get_current_state':
                    # Handle state request
                    self.send_state_update()
                    
                    # Clear the request
                    request_ref.delete()
                    self.logger.info("📤 Processed state request")
                
                elif request_type == 'load_template':
                    # Handle template load request
                    template_name = request_data.get('template_name')
                    if template_name:
                        result = self.handle_load_template({'template_name': template_name})
                        self.send_state_update()  # Send updated state after template load
                        
                        # Clear the request
                        request_ref.delete()
                        self.logger.info(f"📤 Processed template load: {template_name}")
                
                elif request_type in ['undo', 'redo']:
                    # Handle undo/redo requests
                    if request_type == 'undo':
                        result = self.handle_undo_action({})
                    else:
                        result = self.handle_redo_action({})
                    
                    self.send_state_update()  # Send updated state after undo/redo
                    
                    # Clear the request
                    request_ref.delete()
                    self.logger.info(f"📤 Processed {request_type} request")
                    
        except Exception as e:
            self.logger.error(f"Error processing tornado requests: {e}")

    def execute_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single command using the appropriate handler
        
        Args:
            command: Command data from Firebase
            
        Returns:
            dict: Execution result with success status and data/error
        """
        try:
            method = command.get('method')
            params = command.get('params', {})
            
            if method not in self.command_methods:
                return {
                    'success': False,
                    'error': f"Unknown method: {method}"
                }
            
            # Call the appropriate handler method
            handler = self.command_methods[method]
            result = handler(params)
            
            # Send state update to Firebase after successful command execution
            self.send_state_update()
            
            # Create JSON-RPC success response
            return JSONRPCProtocol.create_success_response(
                request_id=command.get('id', 'unknown'),
                result={
                    'method': method,
                    'params': params,
                    'data': result,
                    'timestamp': time.time()
                }
            ).to_dict()
            
        except Exception as e:
            # Create JSON-RPC error response
            return JSONRPCProtocol.create_error_response(
                request_id=command.get('id', 'unknown'),
                code=JSONRPCProtocol.TORNADO_ERROR,
                message=str(e),
                data={
                    'method': method,
                    'params': params,
                    'traceback': traceback.format_exc()
                }
            ).to_dict()
    
    # Command handler methods - these call the bookmark engine methods
    
    def handle_update_position(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle update_position command"""
        x = params.get('x')
        y = params.get('y') 
        z = params.get('z')
        
        self.bookmark_engine.change_slices_position(x, y, z)
        self.bookmark_engine.update_params()
        
        return {
            'message': f'Position updated to X={x}, Y={y}, Z={z}',
            'new_position': {'x': x, 'y': y, 'z': z}
        }
    
    def handle_update_orientation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle update_orientation command"""
        rot1 = params.get('rot1')
        rot2 = params.get('rot2')
        rot3 = params.get('rot3')
        
        self.bookmark_engine.adjust_orientation(rot1, rot2, rot3)
        self.bookmark_engine.update_params()
        
        return {
            'message': f'Orientation updated to rot1={rot1}, rot2={rot2}, rot3={rot3}',
            'new_orientation': {'rot1': rot1, 'rot2': rot2, 'rot3': rot3}
        }
    
    def handle_update_scale(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle update_scale command"""
        scale_x = params.get('scale_x')
        scale_y = params.get('scale_y')
        
        self.bookmark_engine.adjust_zoom(scale_x=scale_x, scale_y=scale_y)
        self.bookmark_engine.update_params()
        
        return {
            'message': f'Scale updated to X={scale_x}, Y={scale_y}',
            'new_scale': {'scale_x': scale_x, 'scale_y': scale_y}
        }
    
    def handle_update_shift(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle update_shift command"""
        shift_x = params.get('shift_x')
        shift_y = params.get('shift_y')
        shift_z = params.get('shift_z')
        
        self.bookmark_engine.adjust_shift(shift_x, shift_y, shift_z)
        self.bookmark_engine.update_params()
        
        return {
            'message': f'Shift updated to X={shift_x}, Y={shift_y}, Z={shift_z}',
            'new_shift': {'shift_x': shift_x, 'shift_y': shift_y, 'shift_z': shift_z}
        }
    
    def handle_update_visibility(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle update_visibility command"""
        seismic = params.get('seismic')
        attribute = params.get('attribute')
        horizon = params.get('horizon')
        well = params.get('well')
        
        # Use individual toggle_data_visibility calls for each data type
        if seismic is not None:
            self.bookmark_engine.toggle_data_visibility('seismic', seismic)
        if attribute is not None:
            self.bookmark_engine.toggle_data_visibility('attribute', attribute)
        if horizon is not None:
            self.bookmark_engine.toggle_data_visibility('horizon', horizon)
        if well is not None:
            self.bookmark_engine.toggle_data_visibility('well', well)
            
        self.bookmark_engine.update_params()
        
        return {
            'message': 'Data visibility updated',
            'new_visibility': {
                'seismic': seismic,
                'attribute': attribute,
                'horizon': horizon,
                'well': well
            }
        }
    
    def handle_update_slice_visibility(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle update_slice_visibility command"""
        x_slice = params.get('x_slice')
        y_slice = params.get('y_slice')
        z_slice = params.get('z_slice')
        
        self.logger.info(f"🔄 Processing slice visibility update: x={x_slice}, y={y_slice}, z={z_slice}")
        self.logger.info(f"📊 Before update: x_visible={self.bookmark_engine.curr_params.x_visible}, y_visible={self.bookmark_engine.curr_params.y_visible}, z_visible={self.bookmark_engine.curr_params.z_visible}, undo_count={self.bookmark_engine.undo_count}")
        
        # Use individual toggle_slice_visibility calls for each slice type
        if x_slice is not None:
            self.bookmark_engine.toggle_slice_visibility('x', x_slice)
        if y_slice is not None:
            self.bookmark_engine.toggle_slice_visibility('y', y_slice)
        if z_slice is not None:
            self.bookmark_engine.toggle_slice_visibility('z', z_slice)
            
        self.bookmark_engine.update_params()
        
        self.logger.info(f"📊 After update: x_visible={self.bookmark_engine.curr_params.x_visible}, y_visible={self.bookmark_engine.curr_params.y_visible}, z_visible={self.bookmark_engine.curr_params.z_visible}, undo_count={self.bookmark_engine.undo_count}")
        
        return {
            'message': 'Slice visibility updated',
            'new_slice_visibility': {
                'x_slice': x_slice,
                'y_slice': y_slice,
                'z_slice': z_slice
            }
        }
    
    def handle_update_gain(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle update_gain command"""
        gain_value = params.get('gain_value')
        
        self.bookmark_engine.adjust_gain(gain_value)
        self.bookmark_engine.update_params()
        
        return {
            'message': f'Gain updated to {gain_value}',
            'new_gain': gain_value
        }
    
    def handle_update_colormap(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle update_colormap command"""
        colormap_index = params.get('colormap_index')
        
        self.bookmark_engine.change_colormap(colormap_index)
        self.bookmark_engine.update_params()
        
        return {
            'message': f'Colormap updated to index {colormap_index}',
            'new_colormap_index': colormap_index
        }
    
    def handle_update_color_scale(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle update_color_scale command"""
        times_value = params.get('times_value')
        
        self.bookmark_engine.adjust_color_scale(times_value)
        self.bookmark_engine.update_params()
        
        return {
            'message': f'Color scale updated to {times_value}',
            'new_color_scale': times_value
        }
    
    def handle_increase_gain(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle increase_gain command"""
        # Get current gain value (approximate from seismic range)
        current_min, current_max = self.bookmark_engine.curr_params.seismic_range
        current_range = current_max - current_min
        default_min, default_max = self.bookmark_engine.default_params.seismic_range
        default_range = default_max - default_min
        
        # Estimate current gain value
        if current_range != 0:
            current_gain = default_range / current_range
        else:
            current_gain = 1.0
        
        # Increase gain by 20% (makes range narrower, contrast higher)
        new_gain = current_gain * 1.2
        
        # Apply new gain
        self.bookmark_engine.adjust_gain(new_gain)
        self.bookmark_engine.update_params()
        
        return {
            'message': f'Gain increased to {new_gain:.1f}',
            'new_gain': new_gain
        }
    
    def handle_decrease_gain(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle decrease_gain command"""
        # Get current gain value (approximate from seismic range)
        current_min, current_max = self.bookmark_engine.curr_params.seismic_range
        current_range = current_max - current_min
        default_min, default_max = self.bookmark_engine.default_params.seismic_range
        default_range = default_max - default_min
        
        # Estimate current gain value
        if current_range != 0:
            current_gain = default_range / current_range
        else:
            current_gain = 1.0
        
        # Decrease gain by 20% (makes range wider, contrast lower)
        new_gain = current_gain * 0.8
        
        # Apply new gain
        self.bookmark_engine.adjust_gain(new_gain)
        self.bookmark_engine.update_params()
        
        return {
            'message': f'Gain decreased to {new_gain:.1f}',
            'new_gain': new_gain
        }
    
    def handle_rotate_left(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle rotate_left command"""
        # Get current orientation
        current_rot1, current_rot2, current_rot3 = self.bookmark_engine.curr_params.orient
        
        # Rotate left by 0.1 radians on Z-axis
        new_rot3 = current_rot3 - 0.1
        
        # Keep within bounds
        if new_rot3 < -3.14159:
            new_rot3 = 3.14159
        
        # Apply new orientation
        self.bookmark_engine.adjust_orientation(current_rot1, current_rot2, new_rot3)
        self.bookmark_engine.update_params()
        
        return {
            'message': 'Rotated left',
            'new_rotation': new_rot3
        }
    
    def handle_rotate_right(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle rotate_right command"""
        # Get current orientation
        current_rot1, current_rot2, current_rot3 = self.bookmark_engine.curr_params.orient
        
        # Rotate right by 0.1 radians on Z-axis
        new_rot3 = current_rot3 + 0.1
        
        # Keep within bounds
        if new_rot3 > 3.14159:
            new_rot3 = -3.14159
        
        # Apply new orientation
        self.bookmark_engine.adjust_orientation(current_rot1, current_rot2, new_rot3)
        self.bookmark_engine.update_params()
        
        return {
            'message': 'Rotated right',
            'new_rotation': new_rot3
        }
    
    def handle_zoom_in(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle zoom_in command"""
        # Get current scale
        current_scale_x, current_scale_y = self.bookmark_engine.curr_params.scale
        
        # Increase scale by 10%
        new_scale_x = min(3.0, current_scale_x * 1.1)
        new_scale_y = min(3.0, current_scale_y * 1.1)
        
        # Apply new scale
        self.bookmark_engine.adjust_zoom(scale_x=new_scale_x, scale_y=new_scale_y)
        self.bookmark_engine.update_params()
        
        return {
            'message': 'Zoomed in',
            'new_scale': {'scale_x': new_scale_x, 'scale_y': new_scale_y}
        }
    
    def handle_zoom_out(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle zoom_out command"""
        # Get current scale
        current_scale_x, current_scale_y = self.bookmark_engine.curr_params.scale
        
        # Decrease scale by 10%
        new_scale_x = max(0.1, current_scale_x * 0.9)
        new_scale_y = max(0.1, current_scale_y * 0.9)
        
        # Apply new scale
        self.bookmark_engine.adjust_zoom(scale_x=new_scale_x, scale_y=new_scale_y)
        self.bookmark_engine.update_params()
        
        return {
            'message': 'Zoomed out',
            'new_scale': {'scale_x': new_scale_x, 'scale_y': new_scale_y}
        }
    
    def handle_zoom_reset(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle zoom_reset command"""
        # Get default scale values from the engine
        if hasattr(self.bookmark_engine, 'default_params') and self.bookmark_engine.default_params:
            default_scale_x, default_scale_y = self.bookmark_engine.default_params.scale
        else:
            # Fallback to 1.0 if default scale is not available
            default_scale_x, default_scale_y = 1.0, 1.0
        
        # Apply default scale
        self.bookmark_engine.adjust_zoom(scale_x=default_scale_x, scale_y=default_scale_y)
        self.bookmark_engine.update_params()
        
        return {
            'message': f'Zoom reset to default ({default_scale_x:.2f}, {default_scale_y:.2f})',
            'new_scale': {'scale_x': default_scale_x, 'scale_y': default_scale_y}
        }
    
    def handle_undo_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle undo_action command"""
        self.logger.info(f"🔄 Processing undo request: can_undo={self.bookmark_engine.can_undo}, undo_count={self.bookmark_engine.undo_count}")
        
        if self.bookmark_engine.can_undo:
            self.bookmark_engine.undo()
            self.logger.info(f"✅ Undo performed: new undo_count={self.bookmark_engine.undo_count}")
            return {'message': 'Undo action performed'}
        else:
            self.logger.warning(f"❌ Cannot undo: undo_count={self.bookmark_engine.undo_count}")
            return {'message': 'No actions to undo'}
    
    def handle_redo_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle redo_action command"""
        if self.bookmark_engine.can_redo:
            self.bookmark_engine.redo()
            return {'message': 'Redo action performed'}
        else:
            return {'message': 'No actions to redo'}
    
    def handle_reset_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle reset_parameters command"""
        import copy
        
        # Reset current parameters to default parameters
        self.bookmark_engine.curr_params = copy.deepcopy(self.bookmark_engine.default_params)
        self.bookmark_engine.update_params()
        
        return {'message': 'Parameters reset to defaults'}
    
    def handle_reload_template(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle reload_template command"""
        # Reload the template
        self.bookmark_engine.load_template("default_bookmark.html")
        
        return {'message': 'Template reloaded'}
    
    def handle_load_template(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle load_template command"""
        template_name = params.get('template_name', 'default_bookmark.html')
        
        # Add .html extension if not present
        if not template_name.endswith('.html'):
            template_name = f"{template_name}.html"
        
        try:
            # Load the specified template
            self.bookmark_engine.load_template(template_name)
            self.logger.info(f"✅ Template loaded: {template_name}")
            return {'message': f'Template {template_name} loaded successfully'}
        except Exception as e:
            self.logger.error(f"❌ Failed to load template {template_name}: {e}")
            return {'message': f'Failed to load template {template_name}: {str(e)}'}
    
    def handle_get_state(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_state query command"""
        return {
            'message': 'Current state retrieved',
            'state': {
                'can_undo': self.bookmark_engine.can_undo,
                'can_redo': self.bookmark_engine.can_redo,
                'current_params': self.bookmark_engine.curr_params.__dict__
            }
        }
    
    def handle_get_templates(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_templates query command"""
        try:
            template_dir = self.bookmark_engine.templates_dir
            templates = [f.name for f in template_dir.glob("*.html") if f.is_file()]
            
            return {
                'message': 'Available templates retrieved',
                'templates': templates
            }
        except Exception as e:
            return {
                'message': f'Error getting templates: {e}',
                'templates': []
            }
    
    def handle_query_state(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle JSON-RPC state query"""
        query_type = params.get('query_type', 'current_state')
        
        if query_type == 'current_state':
            return {
                'curr_params': self.bookmark_engine.curr_params.__dict__,
                'undo_redo_state': {
                    'can_undo': self.bookmark_engine.can_undo,
                    'can_redo': self.bookmark_engine.can_redo,
                    'undo_count': getattr(self.bookmark_engine, 'undo_count', 0),
                    'redo_count': getattr(self.bookmark_engine, 'redo_count', 0)
                },
                'timestamp': time.time()
            }
        elif query_type == 'templates':
            try:
                template_dir = self.bookmark_engine.templates_dir
                templates = [f.stem for f in template_dir.glob("*.html") if f.is_file()]
                return {
                    'available_templates': templates,
                    'timestamp': time.time()
                }
            except Exception as e:
                return {
                    'available_templates': ['default_view', 'structural_analysis', 'amplitude_analysis'],
                    'error': str(e),
                    'timestamp': time.time()
                }
        else:
            return {
                'error': f'Unknown query type: {query_type}',
                'timestamp': time.time()
            }
    
    def send_state_update(self):
        """Send state update to NLP via Firebase using JSON-RPC format"""
        try:
            # Create state update using JSON-RPC protocol
            state_update = TornadoStateProtocol.create_state_update(
                current_params=self.bookmark_engine.curr_params.__dict__,
                undo_redo_state={
                    'can_undo': self.bookmark_engine.can_undo,
                    'can_redo': self.bookmark_engine.can_redo,
                    'undo_count': getattr(self.bookmark_engine, 'undo_count', 0),
                    'redo_count': getattr(self.bookmark_engine, 'redo_count', 0)
                },
                available_templates=self.get_available_templates()
            )
            
            # Send to Firebase tornado_state collection
            state_ref = self.firebase_config.db.collection('tornado_state').document(self.user_id)
            state_ref.set(state_update)
            
            self.logger.info("📤 State update sent to NLP via Firebase")
            
        except Exception as e:
            self.logger.error(f"❌ Error sending state update: {e}")
    
    def get_available_templates(self) -> list:
        """Get list of available templates"""
        try:
            template_dir = self.bookmark_engine.templates_dir
            return [f.stem for f in template_dir.glob("*.html") if f.is_file()]
        except Exception:
            # Fallback templates
            return ['default_view', 'structural_analysis', 'amplitude_analysis', 'frequency_analysis']
    
    def start_listening(self):
        """
        Main listener loop - this must never exit or Tornado will close
        
        This is the critical method that keeps Tornado running.
        """
        self.logger.info("🚀 Starting Tornado listener service...")
        
        # Initialize all components
        if not self.initialize_seismic_view():
            self.logger.error("Failed to initialize seismic view")
            return
        
        if not self.initialize_firebase():
            self.logger.error("Failed to initialize Firebase")
            return
        
        if not self.initialize_bookmark_engine():
            self.logger.error("Failed to initialize bookmark engine")
            return
        
        self.running = True
        self.logger.info("✅ Tornado listener service started successfully")
        self.logger.info("🔄 Entering main processing loop...")
        
        # Main processing loop - MUST NEVER EXIT
        loop_count = 0
        while True:  # Infinite loop - critical for Tornado
            try:
                loop_count += 1
                
                # Process command queue
                self.process_command_queue()
                
                # Update heartbeat every 10 loops (approximately every 20 seconds)
                if loop_count % 10 == 0:
                    self.update_system_status('online')
                    self.logger.debug(f"Heartbeat sent (loop {loop_count})")
                
                # Sleep for 2 seconds before next check
                time.sleep(2)
                
            except KeyboardInterrupt:
                if TORNADO_AVAILABLE:
                    self.logger.info("Received interrupt signal - but continuing to run (Tornado requirement)")
                    # Don't break - Tornado must keep running
                    continue
                else:
                    self.logger.info("Received interrupt signal - exiting development mode")
                    self.running = False
                    # Clean shutdown
                    self.cleanup()
                    break
                
            except Exception as e:
                self.logger.error(f"❌ Error in main loop: {e}")
                self.logger.error(traceback.format_exc())
                
                # Update status to error but keep running
                self.update_system_status('error')
                
                # Sleep longer on error to avoid rapid error loops
                time.sleep(5)
                
                # Continue running - don't exit
                continue


def main():
    """
    Main function to start the Tornado listener
    
    This function is called when the script is run inside Tornado.
    """
    try:
        print("="*60)
        print("TORNADO LISTENER SERVICE")
        print("="*60)
        print("Starting seismic navigation command processor...")
        print("This service processes JSON-RPC commands from Firebase queue")
        print("WARNING: This script must never terminate or Tornado will close!")
        print("="*60)
        
        # Create and start listener
        listener = TornadoListener()
        listener.start_listening()
        
    except Exception as e:
        print(f"❌ FATAL ERROR in Tornado listener: {e}")
        traceback.print_exc()
        
        # Even on fatal error, try to keep running
        print("⚠️  Attempting to continue despite error...")
        time.sleep(10)
        
        # Try to restart
        try:
            listener = TornadoListener()
            listener.start_listening()
        except:
            print("❌ Failed to restart - entering infinite sleep to keep Tornado alive")
            while True:
                time.sleep(60)


if __name__ == "__main__":
    main()