#!/usr/bin/env python3
"""
Gemini-based Natural Language Command Parser for Seismic Navigation

This module uses Google's Gemini API to parse natural language commands
into JSON-RPC format for the seismic navigation system.

Features:
- Function calling for structured JSON-RPC output
- Context awareness and conversation history
- Follow-up questions for ambiguous commands
- Parameter validation and guardrails
- Geophysical domain knowledge
"""

import json
import os
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent.parent / '.win-venv' / 'Lib' / 'site-packages') )
import google.generativeai as genai

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from database.database_config import DatabaseConfig
from database.command_queue_manager import CommandQueueManager
from database.state_manager import TornadoStateManager, EnhancedCommandQueueManager


@dataclass
class SeismicContext:
    """Current seismic navigation context"""
    # Position
    x_position: float = 160112.5
    y_position: float = 112487.5
    z_position: float = 3500.0
    
    # Scale and orientation
    scale_x: float = 0.75
    scale_y: float = 0.75
    rotation: float = -0.785
    
    # Shift
    shift_x: float = 0.0
    shift_y: float = 0.0
    shift_z: float = 0.0
    
    # Visibility
    seismic_visible: bool = True
    attribute_visible: bool = False
    horizon_visible: bool = False
    well_visible: bool = True
    x_visible: bool = True
    y_visible: bool = True
    z_visible: bool = False
    
    # Display settings
    seismic_range: List[float] = None
    seismic_colormap_index: int = 0
    gain_value: float = 1.0
    
    # Command tracking
    last_command: Optional[str] = None
    command_history: List[str] = None
    
    def __post_init__(self):
        if self.command_history is None:
            self.command_history = []
        if self.seismic_range is None:
            self.seismic_range = [-200000, 200000]


class GeminiCommandParser:
    """Gemini-based natural language to JSON-RPC command parser with real-time state"""
    
    def __init__(self, api_key: str, database_config: DatabaseConfig = None):
        """Initialize Gemini parser with API key and optional database state manager"""
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.context = SeismicContext()
        self.conversation_history = []
        self.pending_clarification = None
        self.clarification_count = 0
        self.max_clarifications = 2
        
        # Initialize state manager if database is available
        self.state_manager = None
        self.enhanced_queue = None
        if database_config and database_config.is_initialized():
            self.state_manager = TornadoStateManager(database_config)
            self.enhanced_queue = EnhancedCommandQueueManager(database_config, self.state_manager)
            # Start monitoring for real-time state updates
            self.state_manager.start_state_monitoring()
            print("On-demand state requests enabled")
        
        # Define seismic navigation functions for Gemini
        self.functions = self._define_seismic_functions()
    
    def _update_context_from_state(self, new_state: Dict[str, Any]):
        """Update context from fresh state data"""
        try:
            # Handle JSON-RPC format - curr_params might be nested in params
            curr_params = new_state.get('curr_params', {})
            
            # Check if data is nested in params (JSON-RPC format)
            if 'params' in new_state:
                params = new_state['params']
                if not curr_params:
                    curr_params = params.get('curr_params', {})
            
            # Update context with current parameters
            if curr_params:
                # Position
                self.context.x_position = curr_params.get('x_position', self.context.x_position)
                self.context.y_position = curr_params.get('y_position', self.context.y_position)
                self.context.z_position = curr_params.get('z_position', self.context.z_position)
                
                # Scale and orientation
                scale = curr_params.get('scale', [self.context.scale_x, self.context.scale_y])
                if isinstance(scale, list) and len(scale) >= 2:
                    self.context.scale_x = scale[0]
                    self.context.scale_y = scale[1]
                else:
                    self.context.scale_x = curr_params.get('scale_x', self.context.scale_x)
                    self.context.scale_y = curr_params.get('scale_y', self.context.scale_y)
                
                # Orientation (rotation)
                orient = curr_params.get('orient', [0, 0, self.context.rotation])
                if isinstance(orient, list) and len(orient) >= 3:
                    self.context.rotation = orient[2]  # Z-axis rotation
                else:
                    self.context.rotation = curr_params.get('rotation', self.context.rotation)
                
                # Shift
                shift = curr_params.get('shift', [0, 0, 0])
                if isinstance(shift, list) and len(shift) >= 3:
                    self.context.shift_x = shift[0]
                    self.context.shift_y = shift[1] 
                    self.context.shift_z = shift[2]
                
                # Visibility
                self.context.seismic_visible = curr_params.get('seismic_visible', self.context.seismic_visible)
                self.context.attribute_visible = curr_params.get('attribute_visible', self.context.attribute_visible)
                self.context.horizon_visible = curr_params.get('horizon_visible', self.context.horizon_visible)
                self.context.well_visible = curr_params.get('well_visible', self.context.well_visible)
                self.context.x_visible = curr_params.get('x_visible', getattr(self.context, 'x_visible', True))
                self.context.y_visible = curr_params.get('y_visible', getattr(self.context, 'y_visible', True))
                self.context.z_visible = curr_params.get('z_visible', getattr(self.context, 'z_visible', False))
                
                # Seismic display settings
                self.context.seismic_range = curr_params.get('seismic_range', getattr(self.context, 'seismic_range', [-200000, 200000]))
                self.context.seismic_colormap_index = curr_params.get('seismic_colormap_index', getattr(self.context, 'seismic_colormap_index', 0))
                self.context.seismic_times = curr_params.get('seismic_times', getattr(self.context, 'seismic_times', 1))
                self.context.seismic_range_is_default = curr_params.get('seismic_range_is_default', getattr(self.context, 'seismic_range_is_default', False))
                
                # Calculate gain from actual seismic_range (gain is inverse of range size)
                if 'seismic_range' in curr_params and curr_params['seismic_range']:
                    range_size = curr_params['seismic_range'][1] - curr_params['seismic_range'][0]
                    # Use a reference range to calculate relative gain (default range from bookmark)
                    reference_range = 384761.0  # 187430.0 - (-197331.0) from default bookmark
                    self.context.gain_value = reference_range / range_size if range_size > 0 else 1.0
                else:
                    self.context.gain_value = getattr(self.context, 'gain_value', 1.0)
                
        except Exception as e:
            print(f"Error updating context from state: {e}")
    
    def _on_state_update(self, new_state: Dict[str, Any]):
        """Handle real-time state updates from Tornado"""
        try:
            # Handle JSON-RPC format - curr_params might be nested in params
            curr_params = new_state.get('curr_params', {})
            available_templates = new_state.get('available_templates', [])
            
            # Check if data is nested in params (JSON-RPC format)
            if 'params' in new_state:
                params = new_state['params']
                if not curr_params:
                    curr_params = params.get('curr_params', {})
                if not available_templates:
                    available_templates = params.get('available_templates', [])
            
            # Update context with current parameters
            if curr_params:
                # Position
                self.context.x_position = curr_params.get('x_position', self.context.x_position)
                self.context.y_position = curr_params.get('y_position', self.context.y_position)
                self.context.z_position = curr_params.get('z_position', self.context.z_position)
                
                # Scale and orientation
                scale = curr_params.get('scale', [self.context.scale_x, self.context.scale_y])
                if isinstance(scale, list) and len(scale) >= 2:
                    self.context.scale_x = scale[0]
                    self.context.scale_y = scale[1]
                else:
                    self.context.scale_x = curr_params.get('scale_x', self.context.scale_x)
                    self.context.scale_y = curr_params.get('scale_y', self.context.scale_y)
                
                # Orientation (rotation)
                orient = curr_params.get('orient', [0, 0, self.context.rotation])
                if isinstance(orient, list) and len(orient) >= 3:
                    self.context.rotation = orient[2]  # Z-axis rotation
                else:
                    self.context.rotation = curr_params.get('rotation', self.context.rotation)
                
                # Shift
                shift = curr_params.get('shift', [0, 0, 0])
                if isinstance(shift, list) and len(shift) >= 3:
                    self.context.shift_x = shift[0]
                    self.context.shift_y = shift[1] 
                    self.context.shift_z = shift[2]
                
                # Visibility
                self.context.seismic_visible = curr_params.get('seismic_visible', self.context.seismic_visible)
                self.context.attribute_visible = curr_params.get('attribute_visible', self.context.attribute_visible)
                self.context.horizon_visible = curr_params.get('horizon_visible', self.context.horizon_visible)
                self.context.well_visible = curr_params.get('well_visible', self.context.well_visible)
                self.context.x_visible = curr_params.get('x_visible', getattr(self.context, 'x_visible', True))
                self.context.y_visible = curr_params.get('y_visible', getattr(self.context, 'y_visible', True))
                self.context.z_visible = curr_params.get('z_visible', getattr(self.context, 'z_visible', False))
                
                # Seismic display settings
                self.context.seismic_range = curr_params.get('seismic_range', getattr(self.context, 'seismic_range', [-200000, 200000]))
                self.context.seismic_colormap_index = curr_params.get('seismic_colormap_index', getattr(self.context, 'seismic_colormap_index', 0))
                self.context.seismic_times = curr_params.get('seismic_times', getattr(self.context, 'seismic_times', 1))
                self.context.seismic_range_is_default = curr_params.get('seismic_range_is_default', getattr(self.context, 'seismic_range_is_default', False))
                
                # Calculate gain from actual seismic_range (gain is inverse of range size)
                if 'seismic_range' in curr_params and curr_params['seismic_range']:
                    range_size = curr_params['seismic_range'][1] - curr_params['seismic_range'][0]
                    # Use a reference range to calculate relative gain (default range from bookmark)
                    reference_range = 384761.0  # 187430.0 - (-197331.0) from default bookmark
                    self.context.gain_value = reference_range / range_size if range_size > 0 else 1.0
                else:
                    self.context.gain_value = getattr(self.context, 'gain_value', 1.0)
            
            # Store available templates for quick access
            if available_templates and self.state_manager:
                self.state_manager.cached_templates = available_templates
                
            # Silent update - no console clutter for users
        except Exception as e:
            print(f"⚠️ Error updating context from database state")
        
    def _define_seismic_functions(self) -> List[Dict]:
        """Define all available seismic navigation functions for Gemini"""
        return [
            # Position and Navigation Functions
            {
                "name": "update_position",
                "description": "Update crossline (X), inline (Y), and depth (Z) position in seismic view",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "x": {"type": "NUMBER", "description": "Crossline position (100000-200000)"},
                        "y": {"type": "NUMBER", "description": "Inline position (100000-150000)"},
                        "z": {"type": "NUMBER", "description": "Depth position (1000-6000)"}
                    },
                    "required": ["x", "y", "z"]
                }
            },
            {
                "name": "update_orientation",
                "description": "Update view rotation angles in radians",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "rot1": {"type": "NUMBER", "description": "First rotation angle (-π to π)"},
                        "rot2": {"type": "NUMBER", "description": "Second rotation angle (-π to π)"},
                        "rot3": {"type": "NUMBER", "description": "Z-axis rotation angle (-π to π)"}
                    },
                    "required": ["rot1", "rot2", "rot3"]
                }
            },
            {
                "name": "update_scale",
                "description": "Update zoom/scale values",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "scale_x": {"type": "NUMBER", "description": "X scale factor (0.1-3.0)"},
                        "scale_y": {"type": "NUMBER", "description": "Y scale factor (0.1-3.0)"}
                    },
                    "required": ["scale_x", "scale_y"]
                }
            },
            {
                "name": "update_shift",
                "description": "Update view shift/translation",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "shift_x": {"type": "NUMBER", "description": "X shift (-5000 to 5000)"},
                        "shift_y": {"type": "NUMBER", "description": "Y shift (-5000 to 5000)"},
                        "shift_z": {"type": "NUMBER", "description": "Z shift (-5000 to 5000)"}
                    },
                    "required": ["shift_x", "shift_y", "shift_z"]
                }
            },
            
            # Relative Movement Functions
            {
                "name": "move_crossline_relative",
                "description": "Move crossline slice left/right by relative amount",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "direction": {"type": "STRING", "enum": ["left", "right"]},
                        "amount": {"type": "STRING", "enum": ["tiny", "bit", "small", "medium", "large"]}
                    },
                    "required": ["direction", "amount"]
                }
            },
            {
                "name": "move_inline_relative",
                "description": "Move inline slice up/down by relative amount",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "direction": {"type": "STRING", "enum": ["up", "down", "forward", "backward"]},
                        "amount": {"type": "STRING", "enum": ["tiny", "bit", "small", "medium", "large"]}
                    },
                    "required": ["direction", "amount"]
                }
            },
            {
                "name": "move_depth_relative",
                "description": "Move depth slice deeper/shallower by relative amount",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "direction": {"type": "STRING", "enum": ["deeper", "shallower", "up", "down"]},
                        "amount": {"type": "STRING", "enum": ["tiny", "bit", "small", "medium", "large"]}
                    },
                    "required": ["direction", "amount"]
                }
            },
            
            # Visibility Functions
            {
                "name": "update_visibility",
                "description": "Toggle data type visibility (seismic, attributes, horizons, wells)",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "seismic": {"type": "BOOLEAN", "description": "Show/hide seismic data"},
                        "attribute": {"type": "BOOLEAN", "description": "Show/hide attribute data"},
                        "horizon": {"type": "BOOLEAN", "description": "Show/hide horizon data"},
                        "well": {"type": "BOOLEAN", "description": "Show/hide well data"}
                    }
                }
            },
            {
                "name": "update_slice_visibility",
                "description": "Toggle slice visibility (X=crossline, Y=inline, Z=depth)",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "x_slice": {"type": "BOOLEAN", "description": "Show/hide crossline slice"},
                        "y_slice": {"type": "BOOLEAN", "description": "Show/hide inline slice"},
                        "z_slice": {"type": "BOOLEAN", "description": "Show/hide depth slice"}
                    }
                }
            },
            
            # Display Adjustment Functions
            {
                "name": "update_gain",
                "description": "Adjust seismic gain/amplitude",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "gain_value": {"type": "NUMBER", "description": "Gain value (0.1-5.0, 1.0=default)"}
                    },
                    "required": ["gain_value"]
                }
            },
            {
                "name": "update_colormap",
                "description": "Change colormap/color scheme",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "colormap_index": {"type": "INTEGER", "description": "Colormap index (0-15)"}
                    },
                    "required": ["colormap_index"]
                }
            },
            {
                "name": "update_color_scale",
                "description": "Adjust color scale multiplier",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "times_value": {"type": "INTEGER", "description": "Color scale times (1-10)"}
                    },
                    "required": ["times_value"]
                }
            },
            
            # Quick Action Functions
            {
                "name": "zoom_in",
                "description": "Zoom into the seismic view",
                "parameters": {"type": "OBJECT", "properties": {}}
            },
            {
                "name": "zoom_out", 
                "description": "Zoom out of the seismic view",
                "parameters": {"type": "OBJECT", "properties": {}}
            },
            {
                "name": "zoom_reset",
                "description": "Reset zoom to default level",
                "parameters": {"type": "OBJECT", "properties": {}}
            },
            {
                "name": "rotate_left",
                "description": "Rotate view to the left",
                "parameters": {"type": "OBJECT", "properties": {}}
            },
            {
                "name": "rotate_right",
                "description": "Rotate view to the right", 
                "parameters": {"type": "OBJECT", "properties": {}}
            },
            {
                "name": "increase_gain",
                "description": "Increase seismic gain/amplitude",
                "parameters": {"type": "OBJECT", "properties": {}}
            },
            {
                "name": "decrease_gain",
                "description": "Decrease seismic gain/amplitude",
                "parameters": {"type": "OBJECT", "properties": {}}
            },
            
            # State Management Functions

            {
                "name": "reset_parameters",
                "description": "Reset all parameters to default values",
                "parameters": {"type": "OBJECT", "properties": {}}
            },
            {
                "name": "reload_template",
                "description": "Reload the bookmark template",
                "parameters": {"type": "OBJECT", "properties": {}}
            },
            
            # Multi-Function and Correction Commands
            {
                "name": "execute_sequence",
                "description": "Execute multiple commands in sequence (e.g., undo then move, zoom then adjust gain)",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "commands": {
                            "type": "ARRAY",
                            "items": {
                                "type": "OBJECT",
                                "properties": {
                                    "method": {"type": "STRING", "description": "Command method name"},
                                    "params": {"type": "OBJECT", "description": "Command parameters"}
                                }
                            },
                            "description": "List of commands to execute in order"
                        },
                        "description": {"type": "STRING", "description": "Description of the sequence"}
                    },
                    "required": ["commands"]
                }
            },
            
            # Clarification and Help Functions
            {
                "name": "ask_clarification",
                "description": "Ask user for clarification ONLY when truly critical - use sparingly",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "question": {"type": "STRING", "description": "Clarification question to ask"},
                        "options": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Available options"}
                    },
                    "required": ["question"]
                }
            },
            {
                "name": "show_current_state",
                "description": "Show current seismic navigation state",
                "parameters": {"type": "OBJECT", "properties": {}}
            },
            {
                "name": "show_help",
                "description": "Show available commands and help information",
                "parameters": {"type": "OBJECT", "properties": {}}
            },
            
            # Template Management Functions
            {
                "name": "list_templates",
                "description": "Show available bookmark templates",
                "parameters": {"type": "OBJECT", "properties": {}}
            },
            {
                "name": "load_template",
                "description": "Load a specific bookmark template",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "template_name": {"type": "STRING", "description": "Name of template to load"}
                    },
                    "required": ["template_name"]
                }
            },
            
            # Undo/Redo Functions
            {
                "name": "undo_last_action",
                "description": "Undo the last action/command",
                "parameters": {"type": "OBJECT", "properties": {}}
            },
            {
                "name": "redo_last_action", 
                "description": "Redo the previously undone action",
                "parameters": {"type": "OBJECT", "properties": {}}
            },
            {
                "name": "check_undo_redo_status",
                "description": "Check if undo or redo operations are available",
                "parameters": {"type": "OBJECT", "properties": {}}
            },
            
            # Multi-action Functions
            {
                "name": "undo_and_execute",
                "description": "Undo last action then execute a new command",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "new_method": {"type": "STRING", "description": "Method to execute after undo"},
                        "new_params": {"type": "OBJECT", "description": "Parameters for new command"}
                    },
                    "required": ["new_method", "new_params"]
                }
            }
        ]
    
    def _create_context_prompt(self, user_input: str) -> str:
        """Create context-aware prompt for Gemini with real-time state"""
        recent_history = self.conversation_history[-3:] if len(self.conversation_history) > 3 else self.conversation_history
        
        # Get real-time state if available
        real_time_state = ""
        if self.state_manager:
            real_time_state = self.state_manager.format_current_state_for_llm()
        
        base_state = f"""
CURRENT STATE:
- Position: X={self.context.x_position:.0f} (crossline), Y={self.context.y_position:.0f} (inline), Z={self.context.z_position:.0f} (depth)
- Scale: {self.context.scale_x:.2f}x zoom
- Rotation: {self.context.rotation:.2f} radians
- Visible: Seismic={self.context.seismic_visible}, Attributes={self.context.attribute_visible}, Horizons={self.context.horizon_visible}, Wells={self.context.well_visible}
- Last command: {self.context.last_command or 'None'}"""

        return f"""
You are an expert seismic navigation assistant for Tornado software. You help geophysicists navigate and analyze seismic data through natural language commands.

{real_time_state if real_time_state else base_state}

RECENT CONVERSATION:
{chr(10).join(recent_history) if recent_history else 'None'}

COMMAND INTERPRETATION GUIDELINES:
1. "slice" usually refers to crossline (X direction) unless specified otherwise
2. "left/right" for crossline means decrease/increase X coordinate  
3. "up/down" for inline means increase/decrease Y coordinate
4. "deeper/shallower" for depth means increase/decrease Z coordinate
5. Relative amounts: tiny=100-200, bit=500, small=1000, medium=2000, large=5000
6. BE DECISIVE - Make reasonable assumptions rather than asking too many questions
7. Maximum 2 clarification questions per conversation - after that, make best guess
8. "shift view" = update_shift, "move slice" = update_position
9. "bottom right" = positive X and Y shift, "top left" = negative X and Y shift
10. If user says "no, I want X instead", call undo_last_action THEN the new command

SAFETY GUARDRAILS:
- Position ranges: X(100000-200000), Y(100000-150000), Z(1000-6000)
- Scale ranges: 0.1-3.0
- Rotation ranges: -π to π
- Gain ranges: 0.1-5.0
- Only ask for clarification if truly critical - better to act and let user undo

MULTI-FUNCTION CALLS:
- You can call multiple functions in sequence
- Example: If user says "no, move crossline instead", call undo_last_action then update_position
- Example: If user says "undo and zoom in", call undo_last_action then zoom_in

USER INPUT: "{user_input}"

Be decisive and helpful. Make reasonable assumptions. Users can always undo if wrong.
"""
    
    def parse_command(self, user_input: str) -> Dict[str, Any]:
        """
        Parse natural language command into JSON-RPC format
        
        Args:
            user_input: Natural language command from user
            
        Returns:
            dict: Parsed command result with method, params, or clarification
        """
        try:
            # Create context-aware prompt
            prompt = self._create_context_prompt(user_input)
            
            # Generate response with function calling
            response = self.model.generate_content(
                prompt,
                tools=self.functions,
                tool_config={'function_calling_config': {'mode': 'ANY'}}
            )
            
            # Process the response
            result = self._process_gemini_response(response, user_input)
            
            # Reset clarification count on successful command
            if result.get("type") in ["command", "multi_command"]:
                self.clarification_count = 0
            
            return result
            
        except Exception as e:
            return {
                "type": "error",
                "message": f"Error parsing command: {str(e)}",
                "suggestion": "Please try rephrasing your command or type 'help' for available commands."
            }
    
    def _process_gemini_response(self, response, user_input: str) -> Dict[str, Any]:
        """Process Gemini response and extract function call"""
        try:
            # Check if response has function call
            if (response.candidates and 
                response.candidates[0].content and 
                response.candidates[0].content.parts):
                
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        func_call = part.function_call
                        
                        # Handle different function types
                        if func_call.name == "ask_clarification":
                            return self._handle_clarification(func_call.args, user_input)
                        elif func_call.name in ["show_current_state", "show_help", "list_templates", "check_undo_redo_status"]:
                            return self._handle_info_request(func_call.name)
                        elif func_call.name in ["load_template", "undo_last_action", "redo_last_action"]:
                            return self._handle_special_command(func_call.name, func_call.args)
                        elif func_call.name == "execute_sequence":
                            return self._handle_command_sequence(func_call.args)
                        elif func_call.name in ["undo_and_execute", "execute_sequence"]:
                            return self._handle_multi_action(func_call.name, func_call.args)
                        elif func_call.name.startswith("move_") and func_call.name.endswith("_relative"):
                            return self._handle_relative_movement(func_call.name, func_call.args)
                        else:
                            return self._handle_direct_command(func_call.name, func_call.args, user_input)
            
            # If no function call, return error
            return {
                "type": "error", 
                "message": "Could not understand the command",
                "suggestion": "Please try rephrasing or type 'help' for available commands."
            }
            
        except Exception as e:
            return {
                "type": "error",
                "message": f"Error processing response: {str(e)}",
                "suggestion": "Please try again or type 'help' for assistance."
            }
    
    def _handle_clarification(self, args: Dict, original_input: str) -> Dict[str, Any]:
        """Handle clarification requests from Gemini"""
        # Check clarification limit
        if self.clarification_count >= self.max_clarifications:
            return {
                "type": "error",
                "message": "Too many clarification attempts. Making best guess with available information.",
                "suggestion": "Please try a more specific command, or use undo if the result isn't what you wanted."
            }
        
        self.clarification_count += 1
        self.pending_clarification = {
            "original_input": original_input,
            "question": args.get("question", "Could you clarify your request?"),
            "options": args.get("options", [])
        }
        
        return {
            "type": "clarification",
            "question": self.pending_clarification["question"],
            "options": self.pending_clarification["options"],
            "message": f"I need clarification to proceed. ({self.clarification_count}/{self.max_clarifications} questions)"
        }
    
    def _handle_info_request(self, function_name: str) -> Dict[str, Any]:
        """Handle information requests (help, current state)"""
        if function_name == "show_current_state":
            # Request fresh state from tornado_listener via database
            fresh_state = None
            if self.state_manager:
                self.state_manager.request_current_state()
                
                # Wait for response with retry logic
                import time
                for attempt in range(3):
                    time.sleep(1)
                    current_state = self.state_manager.current_state
                    if current_state and isinstance(current_state, dict) and current_state:
                        fresh_state = current_state
                        self._update_context_from_state(fresh_state)
                        break
            
            # Get current template and undo/redo info
            current_template = "Unknown"
            can_undo = False
            can_redo = False
            undo_count = 0
            redo_count = 0
            
            if self.state_manager:
                print("📤 Requesting fresh templates from Tornado...")
                self.state_manager.request_available_templates()
                import time
                # Wait for response with retry logic
                templates = []
                for attempt in range(3):
                    time.sleep(1)
                    templates = self.state_manager.get_available_templates()
                    if templates:
                        break
                
                if templates:
                    current_template = templates[0] if len(templates) == 1 else f"One of {len(templates)} available"
                
                # Get undo/redo state from fresh data
                if fresh_state:
                    undo_redo_state = fresh_state.get('undo_redo_state', {})
                    if 'params' in fresh_state:
                        undo_redo_state = fresh_state['params'].get('undo_redo_state', undo_redo_state)
                else:
                    undo_redo_state = {}
                
                can_undo = undo_redo_state.get('can_undo', False)
                can_redo = undo_redo_state.get('can_redo', False)
                undo_count = undo_redo_state.get('undo_count', 0)
                redo_count = undo_redo_state.get('redo_count', 0)
            
            # Format colormap info
            colormap_names = ["Grayscale", "Rainbow", "Hot", "Cool", "Jet", "Seismic", "Custom"]
            colormap_name = colormap_names[self.context.seismic_colormap_index] if self.context.seismic_colormap_index < len(colormap_names) else f"Index {self.context.seismic_colormap_index}"
            
            return {
                "type": "info",
                "message": f"""╔══════════════════════════════════════════════════════════════╗
║                    SEISMIC NAVIGATION STATE                  ║
╚══════════════════════════════════════════════════════════════╝

📍 POSITION:
  • Crossline (X): {self.context.x_position:.1f}
  • Inline (Y): {self.context.y_position:.1f}  
  • Depth (Z): {self.context.z_position:.1f}

🔧 VIEW CONFIGURATION:
  • Scale: {self.context.scale_x:.3f} x {self.context.scale_y:.3f}
  • Rotation: {self.context.rotation:.3f} radians ({self.context.rotation * 180 / 3.14159:.1f}°)
  • Shift: X={self.context.shift_x:.1f}, Y={self.context.shift_y:.1f}, Z={self.context.shift_z:.1f}

🎨 DISPLAY SETTINGS:
  • Colormap: {colormap_name}
  • Gain: {self.context.gain_value:.2f}
  • Seismic Range: {self.context.seismic_range[0]:.0f} to {self.context.seismic_range[1]:.0f}
  • Color Scale: {getattr(self.context, 'seismic_times', 1)}x

👁️ VISIBILITY:
  • Seismic Data: {'✓' if self.context.seismic_visible else '✗'}
  • Attributes: {'✓' if self.context.attribute_visible else '✗'}
  • Horizons: {'✓' if self.context.horizon_visible else '✗'}
  • Wells: {'✓' if self.context.well_visible else '✗'}

📐 SLICE VISIBILITY:
  • X-Slice (Crossline): {'✓' if self.context.x_visible else '✗'}
  • Y-Slice (Inline): {'✓' if self.context.y_visible else '✗'}
  • Z-Slice (Depth): {'✓' if self.context.z_visible else '✗'}

📋 TEMPLATE:
  • Current: {current_template}

🔄 UNDO/REDO STATE:
  • Can Undo: {'✓' if can_undo else '✗'} ({undo_count} actions available)
  • Can Redo: {'✓' if can_redo else '✗'} ({redo_count} actions available)

⚡ LAST COMMAND: {self.context.last_command or 'None'}"""
            }
        
        elif function_name == "show_help":
            return {
                "type": "info", 
                "message": """Available Seismic Navigation Commands:

POSITION & NAVIGATION:
  • "move to crossline 165000, inline 115000, depth 4000"
  • "move the slice a bit to the left"
  • "go deeper by 500 units"
  • "navigate to position X Y Z"

VIEW CONTROLS:
  • "zoom in" / "zoom out" / "reset zoom"
  • "rotate left" / "rotate right"
  • "increase gain" / "decrease gain"

VISIBILITY:
  • "show only seismic data"
  • "hide attributes and horizons"
  • "toggle well visibility"

STATE MANAGEMENT:
  • "undo" / "redo"
  • "reset all parameters"
  • "show current state"

EXAMPLES:
  • "Move crossline slice left by 1000 units"
  • "Zoom in and increase the gain a bit"
  • "Show me the current position"
  • "Hide everything except seismic data"

Type your command naturally - I'll understand and ask for clarification if needed!

TEMPLATE MANAGEMENT:
  • "show available templates"
  • "load template [name]"
  • "switch to default view"

UNDO/REDO:
  • "undo" / "undo last action"
  • "redo" / "redo last action"
  • "go back" / "revert changes"

The system tracks your current position and state in real-time for better relative movements!"""
            }
        
        elif function_name == "list_templates":
            # Request fresh templates from Tornado
            templates = []
            if self.state_manager:
                print("📤 Requesting fresh templates from Tornado...")
                self.state_manager.request_available_templates()
                # Wait for response with retry logic
                import time
                templates = []
                for attempt in range(3):
                    time.sleep(1)
                    templates = self.state_manager.get_available_templates()
                    if templates:
                        break
            
            if templates:
                template_list = "\n".join([f"  • {template}" for template in templates])
                return {
                    "type": "info",
                    "message": f"Available Bookmark Templates:\n\n{template_list}\n\nTo load a template, say: 'load template [name]' or 'switch to [name]'"
                }
            else:
                return {
                    "type": "info", 
                    "message": "❌ Could not retrieve templates from Tornado. Please ensure Tornado listener is running."
                }
        
        elif function_name == "check_undo_redo_status":
            # Get fresh undo/redo state from Tornado
            if self.state_manager:
                print("📤 Checking undo/redo status from Tornado...")
                self.state_manager.request_current_state()
                import time
                time.sleep(1)
                
                fresh_state = self.state_manager.current_state
                undo_state = {}
                if fresh_state:
                    undo_state = fresh_state.get('undo_redo_state', {})
                    if 'params' in fresh_state:
                        undo_state = fresh_state['params'].get('undo_redo_state', undo_state)
                
                can_undo = undo_state.get('can_undo', False)
                can_redo = undo_state.get('can_redo', False)
                undo_count = undo_state.get('undo_count', 0)
                redo_count = undo_state.get('redo_count', 0)
                
                return {
                    "type": "info",
                    "message": f"""🔄 UNDO/REDO STATUS:

📤 UNDO:
  • Available: {'✓ Yes' if can_undo else '✗ No'}
  • Actions: {undo_count} operations can be undone

📥 REDO:
  • Available: {'✓ Yes' if can_redo else '✗ No'}  
  • Actions: {redo_count} operations can be redone

💡 Use 'undo' or 'redo' commands to perform these operations."""
                }
            
            return {
                "type": "info",
                "message": "❌ Cannot check undo/redo status - database not connected"
            }
    
    def _handle_special_command(self, function_name: str, args: Dict) -> Dict[str, Any]:
        """Handle special commands like templates and undo/redo"""
        if function_name == "load_template":
            template_name = args.get("template_name")
            if not template_name:
                return {
                    "type": "error",
                    "message": "Template name is required",
                    "suggestion": "Please specify which template to load"
                }
            
            # Use enhanced queue if available
            if self.enhanced_queue:
                command_id = self.enhanced_queue.add_template_command(template_name)
                if command_id:
                    return {
                        "type": "command",
                        "method": "load_template",
                        "params": {"template_name": template_name},
                        "feedback": f"Loading template '{template_name}'...",
                        "command_id": command_id
                    }
            
            return {
                "type": "command",
                "method": "load_template", 
                "params": {"template_name": template_name},
                "feedback": f"Loading template '{template_name}'..."
            }
        
        elif function_name == "undo_last_action":
            # Get fresh undo state from Tornado
            if self.state_manager and self.state_manager.current_state:
                print("📊 Checking undo availability from real-time state...")
                fresh_state = self.state_manager.current_state
                undo_state = fresh_state.get('undo_redo_state', {})
                if 'params' in fresh_state:
                    undo_state = fresh_state['params'].get('undo_redo_state', undo_state)
                
                if not undo_state.get('can_undo', False):
                    return {
                        "type": "info",
                        "message": f"❌ No actions available to undo (current undo count: {undo_state.get('undo_count', 0)})"
                    }
                
                command_id = self.enhanced_queue.add_undo_command()
                return {
                    "type": "command",
                    "method": "undo",
                    "params": {},
                    "feedback": f"Undoing last action... ({undo_state.get('undo_count', 0)} operations available)",
                    "command_id": command_id
                }
            
            return {
                "type": "command",
                "method": "undo",
                "params": {},
                "feedback": "Undoing last action..."
            }
        
        elif function_name == "redo_last_action":
            # Get fresh redo state from Tornado
            if self.state_manager and self.state_manager.current_state:
                print("📊 Checking redo availability from real-time state...")
                fresh_state = self.state_manager.current_state
                undo_state = fresh_state.get('undo_redo_state', {})
                if 'params' in fresh_state:
                    undo_state = fresh_state['params'].get('undo_redo_state', undo_state)
                
                if not undo_state.get('can_redo', False):
                    return {
                        "type": "info",
                        "message": f"❌ No actions available to redo (current redo count: {undo_state.get('redo_count', 0)})"
                    }
                
                command_id = self.enhanced_queue.add_redo_command()
                return {
                    "type": "command",
                    "method": "redo",
                    "params": {},
                    "feedback": f"Redoing last action... ({undo_state.get('redo_count', 0)} operations available)",
                    "command_id": command_id
                }
            
            return {
                "type": "command",
                "method": "redo",
                "params": {},
                "feedback": "Redoing last action..."
            }
    
    def _handle_command_sequence(self, args: Dict) -> Dict[str, Any]:
        """Handle multiple commands in sequence"""
        commands = args.get("commands", [])
        description = args.get("description", "Executing command sequence")
        
        if not commands:
            return {
                "type": "error",
                "message": "No commands provided in sequence",
                "suggestion": "Please specify the commands to execute"
            }
        
        # For now, execute the first command and note the sequence
        # In a full implementation, this would queue all commands
        first_command = commands[0]
        method = first_command.get("method")
        params = first_command.get("params", {})
        
        # Send first command with sequence info
        if self.enhanced_queue:
            command_id = self.enhanced_queue.add_command_with_context({
                "method": method,
                "params": params,
                "sequence": commands[1:],  # Remaining commands
                "sequence_description": description
            })
            
            return {
                "type": "command",
                "method": method,
                "params": params,
                "feedback": f"{description} - Starting with {method}",
                "command_id": command_id,
                "sequence_remaining": len(commands) - 1
            }
        
        return {
            "type": "command",
            "method": method,
            "params": params,
            "feedback": f"{description} - Executing {method}"
        }
    
    def _handle_multi_action(self, function_name: str, args: Dict) -> Dict[str, Any]:
        """Handle multi-action commands like undo_and_execute"""
        if function_name == "undo_and_execute":
            new_method = args.get("new_method")
            new_params = args.get("new_params", {})
            
            if not new_method:
                return {
                    "type": "error",
                    "message": "New method is required for undo_and_execute",
                    "suggestion": "Please specify what to do after undo"
                }
            
            # Create sequence of commands
            commands = [
                {"method": "undo", "params": {}},
                {"method": new_method, "params": new_params}
            ]
            
            return {
                "type": "multi_command",
                "commands": commands,
                "feedback": f"Undoing last action and then executing {new_method}..."
            }
        
        elif function_name == "execute_sequence":
            commands = args.get("commands", [])
            
            if not commands:
                return {
                    "type": "error",
                    "message": "No commands provided for sequence",
                    "suggestion": "Please specify commands to execute"
                }
            
            return {
                "type": "multi_command", 
                "commands": commands,
                "feedback": f"Executing sequence of {len(commands)} commands..."
            }
        
        return {
            "type": "error",
            "message": f"Unknown multi-action function: {function_name}"
        }
    
    def _handle_relative_movement(self, function_name: str, args: Dict) -> Dict[str, Any]:
        """Handle relative movement commands and convert to absolute positions"""
        direction = args.get("direction")
        amount = args.get("amount", "small")
        
        # Define increment amounts
        increments = {
            "tiny": 200,
            "bit": 500, 
            "small": 1000,
            "medium": 2000,
            "large": 5000
        }
        
        delta = increments.get(amount, 1000)
        
        if function_name == "move_crossline_relative":
            current_x = self.context.x_position
            new_x = current_x + (delta if direction == "right" else -delta)
            
            # Validate range
            if not (100000 <= new_x <= 200000):
                return {
                    "type": "error",
                    "message": f"Crossline position {new_x:.0f} is out of range (100000-200000)",
                    "suggestion": f"Current position is {current_x:.0f}. Try a smaller movement."
                }
            
            return {
                "type": "command",
                "method": "update_position",
                "params": {"x": new_x, "y": self.context.y_position, "z": self.context.z_position},
                "feedback": f"Moving crossline {direction} by {amount} amount ({delta} units): {current_x:.0f} → {new_x:.0f}"
            }
        
        elif function_name == "move_inline_relative":
            current_y = self.context.y_position
            # Map directions
            if direction in ["up", "forward"]:
                new_y = current_y + delta
            else:  # down, backward
                new_y = current_y - delta
            
            if not (100000 <= new_y <= 150000):
                return {
                    "type": "error", 
                    "message": f"Inline position {new_y:.0f} is out of range (100000-150000)",
                    "suggestion": f"Current position is {current_y:.0f}. Try a smaller movement."
                }
            
            return {
                "type": "command",
                "method": "update_position", 
                "params": {"x": self.context.x_position, "y": new_y, "z": self.context.z_position},
                "feedback": f"Moving inline {direction} by {amount} amount ({delta} units): {current_y:.0f} → {new_y:.0f}"
            }
        
        elif function_name == "move_depth_relative":
            current_z = self.context.z_position
            if direction in ["deeper", "down"]:
                new_z = current_z + delta
            else:  # shallower, up
                new_z = current_z - delta
            
            if not (1000 <= new_z <= 6000):
                return {
                    "type": "error",
                    "message": f"Depth position {new_z:.0f} is out of range (1000-6000)",
                    "suggestion": f"Current position is {current_z:.0f}. Try a smaller movement."
                }
            
            return {
                "type": "command",
                "method": "update_position",
                "params": {"x": self.context.x_position, "y": self.context.y_position, "z": new_z},
                "feedback": f"Moving depth {direction} by {amount} amount ({delta} units): {current_z:.0f} → {new_z:.0f}"
            }
    
    def _handle_direct_command(self, function_name: str, args: Dict, user_input: str) -> Dict[str, Any]:
        """Handle direct command execution with validation"""
        # Validate parameters
        validation_result = self._validate_parameters(function_name, args)
        if validation_result["valid"] == False:
            return {
                "type": "error",
                "message": validation_result["message"],
                "suggestion": validation_result.get("suggestion", "Please check your parameters and try again.")
            }
        
        # Create command
        command = {
            "type": "command",
            "method": function_name,
            "params": dict(args) if args else {},
            "feedback": self._generate_feedback(function_name, args, user_input)
        }
        
        # Update context for position commands
        if function_name == "update_position":
            self.context.x_position = args.get("x", self.context.x_position)
            self.context.y_position = args.get("y", self.context.y_position) 
            self.context.z_position = args.get("z", self.context.z_position)
        
        return command
    
    def _validate_parameters(self, function_name: str, args: Dict) -> Dict[str, Any]:
        """Validate function parameters against ranges and constraints"""
        if function_name == "update_position":
            x, y, z = args.get("x"), args.get("y"), args.get("z")
            
            if x is not None and not (100000 <= x <= 200000):
                return {"valid": False, "message": f"Crossline position {x} out of range (100000-200000)"}
            if y is not None and not (100000 <= y <= 150000):
                return {"valid": False, "message": f"Inline position {y} out of range (100000-150000)"}
            if z is not None and not (1000 <= z <= 6000):
                return {"valid": False, "message": f"Depth position {z} out of range (1000-6000)"}
        
        elif function_name == "update_scale":
            scale_x, scale_y = args.get("scale_x"), args.get("scale_y")
            if scale_x is not None and not (0.1 <= scale_x <= 3.0):
                return {"valid": False, "message": f"Scale X {scale_x} out of range (0.1-3.0)"}
            if scale_y is not None and not (0.1 <= scale_y <= 3.0):
                return {"valid": False, "message": f"Scale Y {scale_y} out of range (0.1-3.0)"}
        
        elif function_name == "update_gain":
            gain = args.get("gain_value")
            if gain is not None and not (0.1 <= gain <= 5.0):
                return {"valid": False, "message": f"Gain {gain} out of range (0.1-5.0)"}
        
        elif function_name == "update_colormap":
            colormap = args.get("colormap_index")
            if colormap is not None and not (0 <= colormap <= 15):
                return {"valid": False, "message": f"Colormap index {colormap} out of range (0-15)"}
        
        return {"valid": True}
    
    def _generate_feedback(self, function_name: str, args: Dict, user_input: str) -> str:
        """Generate user-friendly feedback for commands"""
        if function_name == "update_position":
            x, y, z = args.get("x"), args.get("y"), args.get("z")
            return f"Moving to position: Crossline={x:.0f}, Inline={y:.0f}, Depth={z:.0f}"
        
        elif function_name == "zoom_in":
            return "Zooming in on seismic view"
        elif function_name == "zoom_out":
            return "Zooming out of seismic view"
        elif function_name == "rotate_left":
            return "Rotating view to the left"
        elif function_name == "rotate_right":
            return "Rotating view to the right"
        elif function_name == "increase_gain":
            return "Increasing seismic gain/amplitude"
        elif function_name == "decrease_gain":
            return "Decreasing seismic gain/amplitude"
        
        elif function_name == "update_visibility":
            visible_items = [k for k, v in args.items() if v == True]
            hidden_items = [k for k, v in args.items() if v == False]
            feedback_parts = []
            if visible_items:
                feedback_parts.append(f"Showing: {', '.join(visible_items)}")
            if hidden_items:
                feedback_parts.append(f"Hiding: {', '.join(hidden_items)}")
            return "; ".join(feedback_parts) if feedback_parts else "Updating data visibility"
        


        elif function_name == "reset_parameters":
            return "Resetting all parameters to defaults"
        
        else:
            return f"Executing: {function_name}"
    
    def handle_clarification_response(self, response: str) -> Dict[str, Any]:
        """Handle user response to clarification question"""
        if not self.pending_clarification:
            return {
                "type": "error",
                "message": "No pending clarification question.",
                "suggestion": "Please enter a new command."
            }
        
        # Try to parse the clarification response
        original_input = self.pending_clarification["original_input"]
        clarified_input = f"{original_input} - {response}"
        
        # Clear pending clarification
        self.pending_clarification = None
        
        # Re-parse with clarification
        return self.parse_command(clarified_input)
    
    def update_conversation_history(self, user_input: str, result: Dict[str, Any]):
        """Update conversation history for context"""
        if result.get("type") == "command":
            self.conversation_history.append(f"User: {user_input} → {result.get('feedback', 'Command executed')}")
            self.context.last_command = user_input
            self.context.command_history.append(user_input)
        
        # Keep only last 10 entries
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]
        if len(self.context.command_history) > 10:
            self.context.command_history = self.context.command_history[-10:]