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
import logging

# Add Windows venv to path FIRST
win_venv_path = Path(__file__).resolve().parent.parent.parent.parent / '.win-venv' / 'Lib' / 'site-packages'
if win_venv_path.exists():
    sys.path.insert(0, str(win_venv_path))

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from shared.database.database_config import DatabaseConfig
from shared.database.command_queue_manager import CommandQueueManager
from shared.database.state_manager import TornadoStateManager, EnhancedCommandQueueManager
from shared.utils.limits_loader import get_limits
from shared.utils.context_loader import get_domain_context
from shared.llm.llm_provider import LLMFactory, LLMResponse

logger = logging.getLogger(__name__)


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
    profile_visible: bool = False
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
    """LLM-based natural language to JSON-RPC command parser with HTTP LLM and Gemini fallback"""
    
    def __init__(self, api_key: str = None, database_config: DatabaseConfig = None):
        """Initialize LLM parser with fallback support and optional database state manager"""
        # Initialize LLM factory with fallback support
        self.llm_factory = LLMFactory()
        self.current_provider = None
        
        # Store API key for backward compatibility (used by Gemini fallback)
        self.api_key = api_key
        
        self.context = SeismicContext()
        self.conversation_history = []
        self.pending_clarification = None
        self.clarification_count = 0
        self.max_clarifications = get_limits().get_system_limit("max_clarifications")
        
        # Initialize state manager if database is available
        self.state_manager = None
        self.enhanced_queue = None
        if database_config and database_config.is_initialized():
            self.state_manager = TornadoStateManager(database_config)
            self.enhanced_queue = EnhancedCommandQueueManager(database_config, self.state_manager)
            # Start monitoring for real-time state updates
            self.state_manager.start_state_monitoring()
            print("On-demand state requests enabled")
        
        # Define seismic navigation functions for LLM
        self.functions = self._define_seismic_functions()
        
        # Log provider status
        self._log_provider_status()
    
    def _log_provider_status(self):
        """Log the status of all LLM providers"""
        try:
            status = self.llm_factory.get_provider_status()
            logger.info("LLM Provider Status:")
            for provider_name, is_available in status.items():
                status_icon = "✅" if is_available else "❌"
                logger.info(f"  {status_icon} {provider_name}: {'Available' if is_available else 'Unavailable'}")
            
            # Get current provider
            self.current_provider = self.llm_factory.get_available_provider()
            if self.current_provider:
                logger.info(f"🎯 Active provider: {self.current_provider.name}")
            else:
                logger.error("⚠️ No LLM providers available!")
        except Exception as e:
            logger.warning(f"Error checking provider status: {e}")
    
    def _get_seismic_crossline(self) -> float:
        """Get current crossline from Cartesian X coordinate"""
        try:
            from shared.utils.coordinate_mapper import get_coordinate_mapper
            mapper = get_coordinate_mapper()
            crossline, _, _ = mapper.cartesian_to_seismic(x=self.context.x_position)
            return crossline if crossline is not None else self.context.x_position
        except:
            return self.context.x_position
    
    def _get_seismic_inline(self) -> float:
        """Get current inline from Cartesian Y coordinate"""
        try:
            from shared.utils.coordinate_mapper import get_coordinate_mapper
            mapper = get_coordinate_mapper()
            _, inline, _ = mapper.cartesian_to_seismic(y=self.context.y_position)
            return inline if inline is not None else self.context.y_position
        except:
            return self.context.y_position
    
    def _get_seismic_depth(self) -> float:
        """Get current depth from Cartesian Z coordinate"""
        try:
            from shared.utils.coordinate_mapper import get_coordinate_mapper
            mapper = get_coordinate_mapper()
            _, _, depth = mapper.cartesian_to_seismic(z=self.context.z_position)
            return depth if depth is not None else self.context.z_position
        except:
            return self.context.z_position
    
    def _invoke_llm_with_fallback(self, system_prompt: str, user_prompt: str, **kwargs) -> LLMResponse:
        """
        Invoke LLM with automatic fallback support.
        
        This method handles the HTTP LLM → Gemini fallback logic transparently.
        """
        try:
            # Get available provider (with fallback logic)
            provider = self.llm_factory.get_available_provider()
            
            if not provider:
                return LLMResponse(
                    content="",
                    success=False,
                    error_message="No LLM providers available",
                    provider_name="None"
                )
            
            # Invoke the provider
            response = provider.invoke_prompt(system_prompt, user_prompt, **kwargs)
            
            # Log provider usage
            if response.success:
                logger.debug(f"LLM success with {response.provider_name}")
            else:
                logger.warning(f"LLM failed with {response.provider_name}: {response.error_message}")
            
            return response
            
        except Exception as e:
            logger.error(f"LLM invocation error: {e}")
            return LLMResponse(
                content="",
                success=False,
                error_message=f"LLM invocation failed: {str(e)}",
                provider_name="Error"
            )
    
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
                self.context.profile_visible = curr_params.get('profile_visible', self.context.profile_visible)
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
                self.context.profile_visible = curr_params.get('profile_visible', self.context.profile_visible)
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
                "name": "move_to_seismic_position",
                "description": "Move to specific seismic coordinates (crossline, inline, depth)",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "crossline": {"type": "NUMBER", "description": "Crossline number (e.g., 25519-25599)"},
                        "inline": {"type": "NUMBER", "description": "Inline number (e.g., 3000-8931)"},
                        "depth": {"type": "NUMBER", "description": "Depth in meters (e.g., 0-3500)"}
                    }
                }
            },
            {
                "name": "update_orientation",
                "description": "Update view rotation angles in radians (any value accepted, automatically normalized to -π to π)",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "rot1": {"type": "NUMBER", "description": "First rotation angle in radians (any value, auto-normalized)"},
                        "rot2": {"type": "NUMBER", "description": "Second rotation angle in radians (any value, auto-normalized)"},
                        "rot3": {"type": "NUMBER", "description": "Z-axis rotation angle in radians (any value, auto-normalized)"}
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
                "description": "Toggle data type visibility (seismic, attributes, horizons, wells, profiles)",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "seismic": {"type": "BOOLEAN", "description": "Show/hide seismic data"},
                        "attribute": {"type": "BOOLEAN", "description": "Show/hide attribute data"},
                        "horizon": {"type": "BOOLEAN", "description": "Show/hide horizon data"},
                        "well": {"type": "BOOLEAN", "description": "Show/hide well data"},
                        "profile": {"type": "BOOLEAN", "description": "Show/hide profile data"}
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
                "description": "Change colormap/color scheme (integer index only)",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "colormap_index": {"type": "INTEGER", "description": "Integer colormap index (0-15, no decimals)"}
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
                "description": "Rotate view to the left by π/8 radians (22.5 degrees)",
                "parameters": {"type": "OBJECT", "properties": {}}
            },
            {
                "name": "rotate_right",
                "description": "Rotate view to the right by π/8 radians (22.5 degrees)", 
                "parameters": {"type": "OBJECT", "properties": {}}
            },
            {
                "name": "increase_gain",
                "description": "Increase seismic gain/amplitude by 4dB",
                "parameters": {"type": "OBJECT", "properties": {}}
            },
            {
                "name": "decrease_gain",
                "description": "Decrease seismic gain/amplitude by 4dB",
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
            {
                "name": "reload_limits",
                "description": "Reload transformation limits from configuration file",
                "parameters": {"type": "OBJECT", "properties": {}}
            },
            
            # Multi-Function and Correction Commands
            {
                "name": "execute_sequence",
                "description": "Execute multiple commands in sequence - ONLY use when user explicitly requests multiple actions (e.g., 'zoom then adjust gain', 'move then rotate')",
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
                "description": "Load a specific bookmark template based on user's viewing preference",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "template_name": {
                            "type": "STRING", 
                            "description": "Template name or natural description. Available templates: 'default_bookmark' (standard view), 'top_view' (view from above/top), 'crossline_view' (crossline perspective), 'inline_view' (inline perspective), 'ortho_view' (orthogonal view). You can also use natural language like 'top', 'above', 'crossline', 'inline', 'orthogonal', etc."
                        }
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
            },
            {
                "name": "reload_context",
                "description": "Reload domain context from context.json file",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {}
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
        
        domain_context = get_domain_context()
        
        domain_section = ""
        if domain_context:
            domain_section = f"""

DOMAIN KNOWLEDGE:
{domain_context}"""
        
        base_state = f"""
CURRENT STATE:
- Position: Crossline={int(self._get_seismic_crossline())}, Inline={int(self._get_seismic_inline())}, Depth={int(self._get_seismic_depth())}
- Scale: {self.context.scale_x:.2f}x zoom
- Rotation: {self.context.rotation:.2f} radians
- Visible: Seismic={self.context.seismic_visible}, Attributes={self.context.attribute_visible}, Horizons={self.context.horizon_visible}, Wells={self.context.well_visible}, Profiles={self.context.profile_visible}
- Last command: {self.context.last_command or 'None'}{domain_section}"""

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
11. TEMPLATE REQUESTS: "from the top"→top_view, "crossline view"→crossline_view, "inline"→inline_view, "orthogonal"→ortho_view
12. ROTATION: All rotations are in RADIANS. Any value accepted (auto-normalized). "rotate a bit"→π/8 rad, "rotate left/right"→π/8 rad, "rotate 720°"→4π rad, etc.

SAFETY GUARDRAILS:
{get_limits().get_limits_summary()}
- Rotation: ANY radian value accepted (auto-normalized to -π to π range). All rotations are in RADIANS, not degrees
- Only ask for clarification if truly critical - better to act and let user undo

SINGLE vs MULTI-FUNCTION CALLS:
- For single actions like "undo", "redo", "zoom in" - use ONE function call
- For multiple actions like "zoom in and increase gain", "move left and rotate" - use MULTIPLE function calls (2-3 max)
- Example: "undo" → call undo_last_action (single function)
- Example: "zoom in and increase gain" → call zoom_in AND increase_gain (two separate function calls)
- Example: "move left, zoom in, and increase gain" → call update_position AND zoom_in AND increase_gain (three function calls)
- KEEP IT MINIMAL: Use 2-3 function calls maximum, avoid over-complicating simple requests
- DON'T use multiple calls for: clarifications, info requests, single template loads, single movements

USER INPUT: "{user_input}"

Be decisive and helpful. Make reasonable assumptions. Users can always undo if wrong.
"""
    
    def parse_command(self, user_input: str) -> Dict[str, Any]:
        """
        Parse natural language command into JSON-RPC format with LLM fallback support
        
        Args:
            user_input: Natural language command from user
            
        Returns:
            dict: Parsed command result with method, params, or clarification
        """
        try:
            # Get current provider
            provider = self.llm_factory.get_available_provider()
            if not provider:
                return {
                    "type": "error",
                    "message": "No LLM providers available",
                    "suggestion": "Please check your network connection and API configuration."
                }
            
            # Use different approaches based on provider type
            if provider.name == "GeminiProvider":
                # Use Gemini's native function calling
                return self._parse_with_gemini_functions(user_input)
            else:
                # Use JSON-based function calling for HTTP LLM
                return self._parse_with_json_functions(user_input)
                
        except Exception as e:
            logger.error(f"Error in parse_command: {e}")
            return {
                "type": "error",
                "message": f"Error parsing command: {str(e)}",
                "suggestion": "Please try rephrasing your command or type 'help' for available commands."
            }
    
    def _parse_with_gemini_functions(self, user_input: str) -> Dict[str, Any]:
        """Parse using Gemini's native function calling (fallback method)"""
        try:
            # Import Gemini here for fallback use only (venv path already setup)
            import google.generativeai as genai
            
            # Configure Gemini with API key
            if self.api_key:
                genai.configure(api_key=self.api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
            else:
                # Try to get API key from environment
                api_key = os.getenv('GEMINI_API_KEY')
                if not api_key:
                    raise Exception("Gemini API key not available")
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Create context-aware prompt
            prompt = self._create_context_prompt(user_input)
            
            # Generate response with function calling
            response = model.generate_content(
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
            logger.error(f"Gemini function calling failed: {e}")
            # Fallback to JSON-based parsing
            return self._parse_with_json_functions(user_input)
    
    def _parse_with_json_functions(self, user_input: str) -> Dict[str, Any]:
        """Parse using JSON-based function calling for HTTP LLM"""
        try:
            # Create system prompt with function definitions
            system_prompt = self._create_json_system_prompt()
            
            # Create user prompt with context
            user_prompt = self._create_json_user_prompt(user_input)
            
            # Invoke LLM with fallback
            response = self._invoke_llm_with_fallback(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.4,
                max_tokens=4000
            )
            
            if not response.success:
                return {
                    "type": "error",
                    "message": f"LLM request failed: {response.error_message}",
                    "suggestion": "Please try again or check your connection."
                }
            
            # Parse JSON response
            result = self._process_json_response(response.content, user_input)
            
            # Reset clarification count on successful command
            if result.get("type") in ["command", "multi_command"]:
                self.clarification_count = 0
            
            return result
            
        except Exception as e:
            logger.error(f"JSON function calling failed: {e}")
            return {
                "type": "error",
                "message": f"Error processing command: {str(e)}",
                "suggestion": "Please try rephrasing your command."
            }
    
    def _process_gemini_response(self, response, user_input: str) -> Dict[str, Any]:
        """Process Gemini response and extract function calls (supports multiple calls)"""
        try:
            # Check if response has function calls
            if (response.candidates and 
                response.candidates[0].content and 
                response.candidates[0].content.parts):
                
                function_calls = []
                
                # Collect all function calls from the response
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        function_calls.append(part.function_call)
                
                if not function_calls:
                    return {
                        "type": "error", 
                        "message": "Could not understand the command",
                        "suggestion": "Please try rephrasing or type 'help' for available commands."
                    }
                
                # Debug: Print all function calls
                if len(function_calls) > 1:
                    print(f"🤖 AI called {len(function_calls)} functions:")
                    for i, func_call in enumerate(function_calls, 1):
                        print(f"   {i}. {func_call.name} with args: {func_call.args}")
                else:
                    print(f"🤖 AI called function: {function_calls[0].name} with args: {function_calls[0].args}")
                
                # Handle single function call (existing behavior)
                if len(function_calls) == 1:
                    return self._handle_single_function_call(function_calls[0], user_input)
                
                # Handle multiple function calls
                else:
                    return self._handle_multiple_function_calls(function_calls, user_input)
            
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
    
    def _handle_single_function_call(self, func_call, user_input: str) -> Dict[str, Any]:
        """Handle a single function call (existing logic)"""
        # Handle different function types
        if func_call.name == "ask_clarification":
            return self._handle_clarification(func_call.args, user_input)
        elif func_call.name in ["show_current_state", "show_help", "list_templates", "check_undo_redo_status", "reload_limits"]:
            return self._handle_info_request(func_call.name)
        elif func_call.name in ["load_template", "undo_last_action", "redo_last_action"]:
            return self._handle_special_command(func_call.name, func_call.args)
        elif func_call.name == "execute_sequence":
            return self._handle_command_sequence(func_call.args)
        elif func_call.name == "undo_and_execute":
            return self._handle_multi_action(func_call.name, func_call.args)
        elif func_call.name.startswith("move_") and func_call.name.endswith("_relative"):
            return self._handle_relative_movement(func_call.name, func_call.args)
        else:
            return self._handle_direct_command(func_call.name, func_call.args, user_input)
    
    def _handle_multiple_function_calls(self, function_calls, user_input: str) -> Dict[str, Any]:
        """Handle multiple function calls in sequence"""
        commands = []
        feedback_parts = []
        
        # Process each function call
        for func_call in function_calls:
            # Skip clarification and info requests in multi-call scenarios
            if func_call.name in ["ask_clarification", "show_current_state", "show_help", "list_templates", "check_undo_redo_status", "reload_limits"]:
                continue
            
            # Convert function call to command format
            if func_call.name in ["load_template", "undo_last_action", "redo_last_action"]:
                # Handle special commands
                result = self._handle_special_command(func_call.name, func_call.args)
                if result.get("type") == "command":
                    commands.append({
                        "method": result["method"],
                        "params": result["params"]
                    })
                    feedback_parts.append(result.get("feedback", f"Executing {func_call.name}"))
            
            elif func_call.name.startswith("move_") and func_call.name.endswith("_relative"):
                # Handle relative movement
                result = self._handle_relative_movement(func_call.name, func_call.args)
                if result.get("type") == "command":
                    commands.append({
                        "method": result["method"],
                        "params": result["params"]
                    })
                    feedback_parts.append(result.get("feedback", f"Executing {func_call.name}"))
            
            else:
                # Handle direct commands
                result = self._handle_direct_command(func_call.name, func_call.args, user_input)
                if result.get("type") == "command":
                    commands.append({
                        "method": result["method"],
                        "params": result["params"]
                    })
                    feedback_parts.append(result.get("feedback", f"Executing {func_call.name}"))
        
        if not commands:
            return {
                "type": "error",
                "message": "No valid commands found in the request",
                "suggestion": "Please try rephrasing your command."
            }
        
        # Return as multi-command sequence
        return {
            "type": "multi_command",
            "commands": commands,
            "feedback": f"Executing {len(commands)} commands: " + " → ".join(feedback_parts),
            "description": f"Multi-command sequence from: {user_input}"
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
  • Crossline: {int(self._get_seismic_crossline())}
  • Inline: {int(self._get_seismic_inline())}  
  • Depth: {int(self._get_seismic_depth())}

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
  • Profiles: {'✓' if self.context.profile_visible else '✗'}

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
  • "rotate left" / "rotate right" (π/8 radians each)
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
  • "Move crossline slice left by 1000 units" (single function)
  • "Zoom in and increase the gain a bit" (two functions: zoom_in + increase_gain)
  • "Show me the current position" (single function)
  • "Hide everything except seismic data" (single function)
  • "Show me from the top" / "I want to see it from above" (single function)
  • "Move left, zoom in, and rotate right" (three functions: update_position + zoom_in + rotate_right)

Type your command naturally - I'll understand and ask for clarification if needed!

TEMPLATE MANAGEMENT:
  • "show available templates" / "list templates"
  • "load template [name]" / "switch to [view]"
  • Natural language: "show me from the top", "view from above", "crossline view", "inline perspective"
  • Available views: top_view, crossline_view, inline_view, ortho_view, default_bookmark

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
        
        elif function_name == "reload_limits":
            from shared.utils.limits_loader import reload_limits
            
            # Reload limits from file
            limits = reload_limits()
            
            return {
                "type": "info",
                "message": f"""🔄 TRANSFORMATION LIMITS RELOADED

{limits.get_limits_summary()}

✅ Limits have been reloaded from configuration file."""
            }
        
        elif function_name == "reload_context":
            from shared.utils.context_loader import reload_context_loader, get_domain_context
            
            # Reload context from file
            reload_context_loader()
            context = get_domain_context()
            
            return {
                "type": "info",
                "message": f"""🔄 DOMAIN CONTEXT RELOADED

Context length: {len(context)} characters
Preview: {context[:200] + '...' if len(context) > 200 else context}

✅ Domain context has been reloaded from context.json file."""
            }
    
    def _map_template_name(self, user_input: str) -> str:
        """Map natural language template requests to actual template names"""
        user_input_lower = user_input.lower().strip()
        
        # Template mapping dictionary
        template_mappings = {
            # Top view mappings
            "top": "top_view",
            "top_view": "top_view", 
            "from above": "top_view",
            "above": "top_view",
            "bird's eye": "top_view",
            "birds eye": "top_view",
            "overhead": "top_view",
            "from the top": "top_view",
            "looking down": "top_view",
            
            # Crossline view mappings
            "crossline": "crossline_view",
            "crossline_view": "crossline_view",
            "cross line": "crossline_view",
            "x-line": "crossline_view",
            "xline": "crossline_view",
            
            # Inline view mappings
            "inline": "inline_view",
            "inline_view": "inline_view", 
            "in line": "inline_view",
            "y-line": "inline_view",
            "yline": "inline_view",
            
            # Orthogonal view mappings
            "ortho": "ortho_view",
            "ortho_view": "ortho_view",
            "orthogonal": "ortho_view",
            "orthogonal_view": "ortho_view",
            "perpendicular": "ortho_view",
            "90 degrees": "ortho_view",
            
            # Default view mappings
            "default": "default_bookmark",
            "default_bookmark": "default_bookmark",
            "standard": "default_bookmark",
            "normal": "default_bookmark",
            "regular": "default_bookmark",
            "original": "default_bookmark"
        }
        
        # Check for exact matches first
        if user_input_lower in template_mappings:
            return template_mappings[user_input_lower]
        
        # Check for partial matches (contains keywords)
        for keyword, template in template_mappings.items():
            if keyword in user_input_lower:
                return template
        
        # If no mapping found, return the original input (assume it's a direct template name)
        return user_input

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
            
            # Map natural language to actual template names
            actual_template = self._map_template_name(template_name)
            
            # Use enhanced queue if available
            if self.enhanced_queue:
                command_id = self.enhanced_queue.add_template_command(actual_template)
                if command_id:
                    return {
                        "type": "command",
                        "method": "load_template",
                        "params": {"template_name": actual_template},
                        "feedback": f"Loading {actual_template} template ('{template_name}')...",
                        "command_id": command_id
                    }
            
            return {
                "type": "command",
                "method": "load_template", 
                "params": {"template_name": actual_template},
                "feedback": f"Loading {actual_template} template ('{template_name}')..."
            }
        
        elif function_name == "undo_last_action":
            print("🔙 Processing single undo command")
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
                print(f"🔙 Added undo command to queue with ID: {command_id}")
                return {
                    "type": "command",
                    "method": "undo",
                    "params": {},
                    "feedback": f"Undoing last action... ({undo_state.get('undo_count', 0)} operations available)",
                    "command_id": command_id
                }
            
            print("⚠️ Using fallback undo path (no enhanced queue)")
            return {
                "type": "command",
                "method": "undo",
                "params": {},
                "feedback": "Undoing last action..."
            }
        
        elif function_name == "redo_last_action":
            print("🔜 Processing single redo command")
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
                print(f"🔜 Added redo command to queue with ID: {command_id}")
                return {
                    "type": "command",
                    "method": "redo",
                    "params": {},
                    "feedback": f"Redoing last action... ({undo_state.get('redo_count', 0)} operations available)",
                    "command_id": command_id
                }
            
            print("⚠️ Using fallback redo path (no enhanced queue)")
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
        
        # Debug: Print what sequence is being executed
        print(f"🔄 Executing command sequence: {len(commands)} commands")
        for i, cmd in enumerate(commands):
            print(f"   {i+1}. {cmd.get('method')} with params: {cmd.get('params', {})}")
        
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
        """Validate function parameters against ranges and constraints from config"""
        limits = get_limits()
        
        if function_name == "update_position":
            x, y, z = args.get("x"), args.get("y"), args.get("z")
            
            if x is not None:
                valid, message = limits.validate_position("x", x)
                if not valid:
                    return {"valid": False, "message": message}
            
            if y is not None:
                valid, message = limits.validate_position("y", y)
                if not valid:
                    return {"valid": False, "message": message}
            
            if z is not None:
                valid, message = limits.validate_position("z", z)
                if not valid:
                    return {"valid": False, "message": message}
        
        elif function_name == "update_scale":
            scale_x, scale_y = args.get("scale_x"), args.get("scale_y")
            
            if scale_x is not None:
                valid, message = limits.validate_scale("x", scale_x)
                if not valid:
                    return {"valid": False, "message": message}
            
            if scale_y is not None:
                valid, message = limits.validate_scale("y", scale_y)
                if not valid:
                    return {"valid": False, "message": message}
        
        elif function_name == "update_gain":
            gain = args.get("gain_value")
            if gain is not None:
                valid, message = limits.validate_gain(gain)
                if not valid:
                    return {"valid": False, "message": message}
        
        elif function_name == "update_colormap":
            colormap = args.get("colormap_index")
            if colormap is not None:
                valid, message = limits.validate_colormap(colormap)
                if not valid:
                    return {"valid": False, "message": message}
                
                # Update args with integer value if validation passed
                args["colormap_index"] = int(colormap)
        
        return {"valid": True}
    
    def _generate_feedback(self, function_name: str, args: Dict, user_input: str) -> str:
        """Generate user-friendly feedback for commands"""
        if function_name == "move_to_seismic_position":
            crossline = args.get("crossline")
            inline = args.get("inline") 
            depth = args.get("depth")
            
            parts = []
            if crossline is not None:
                parts.append(f"crossline {int(crossline)}")
            if inline is not None:
                parts.append(f"inline {int(inline)}")
            if depth is not None:
                parts.append(f"depth {int(depth)}")
            
            return f"Moving to {', '.join(parts)}"
        
        elif function_name == "zoom_in":
            return "Zooming in on seismic view"
        elif function_name == "zoom_out":
            return "Zooming out of seismic view"
        elif function_name == "rotate_left":
            return "Rotating view to the left by π/8 radians (22.5°)"
        elif function_name == "rotate_right":
            return "Rotating view to the right by π/8 radians (22.5°)"
        elif function_name == "increase_gain":
            return "Increasing seismic gain/amplitude by 4dB"
        elif function_name == "decrease_gain":
            return "Decreasing seismic gain/amplitude by 4dB"
        
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
    def _create_json_system_prompt(self) -> str:
        """Create system prompt for JSON-based function calling"""
        functions_json = self._convert_functions_to_json_schema()
        
        domain_context = get_domain_context()
        
        context_section = ""
        if domain_context:
            context_section = f"""

DOMAIN KNOWLEDGE:
{domain_context}"""
        
        return f"""You are an expert seismic navigation assistant. Parse user commands into JSON function calls.

CURRENT CONTEXT:
- Position: Crossline={int(self._get_seismic_crossline())}, Inline={int(self._get_seismic_inline())}, Depth={int(self._get_seismic_depth())}
- Scale: {self.context.scale_x:.2f}x zoom
- Rotation: {self.context.rotation:.2f} radians
- Visible: Seismic={self.context.seismic_visible}, Attributes={self.context.attribute_visible}, Horizons={self.context.horizon_visible}, Wells={self.context.well_visible}, Profiles={self.context.profile_visible}
- Last command: {self.context.last_command or 'None'}{context_section}

AVAILABLE FUNCTIONS:
{functions_json}

RESPONSE FORMAT:
Return ONLY a JSON object with this structure:
{{
    "type": "command" | "multi_command" | "clarification" | "info",
    "function_calls": [
        {{
            "name": "function_name",
            "arguments": {{
                "param1": value1,
                "param2": value2
            }}
        }}
    ],
    "feedback": "User-friendly description of what will happen",
    "question": "Clarification question (only if type is clarification)",
    "message": "Information message (only if type is info)"
}}

RULES:
- For single actions: use ONE function call
- For multiple actions: use MULTIPLE function calls (2-3 max)
- Be decisive and make reasonable assumptions
- Use "clarification" type only when truly ambiguous
- Use "info" type for status queries and help requests"""

    def _create_json_user_prompt(self, user_input: str) -> str:
        """Create user prompt for JSON-based function calling"""
        return f"""Parse this seismic navigation command into JSON function calls:

USER INPUT: "{user_input}"

Remember to:
- Use current context to make intelligent decisions
- Be decisive and helpful
- Return valid JSON only
- Make reasonable assumptions rather than asking for clarification"""

    def _convert_functions_to_json_schema(self) -> str:
        """Convert Gemini function definitions to JSON schema format"""
        json_functions = []
        
        # Convert each function from Gemini format to JSON schema
        for func in self.functions:
            if hasattr(func, 'function_declarations'):
                for decl in func.function_declarations:
                    json_func = {
                        "name": decl.name,
                        "description": decl.description,
                        "parameters": {}
                    }
                    
                    # Convert parameters
                    if hasattr(decl, 'parameters') and decl.parameters:
                        if hasattr(decl.parameters, 'properties'):
                            json_func["parameters"] = {}
                            for prop_name, prop_def in decl.parameters.properties.items():
                                json_func["parameters"][prop_name] = {
                                    "type": prop_def.type_.name.lower() if hasattr(prop_def.type_, 'name') else "string",
                                    "description": prop_def.description if hasattr(prop_def, 'description') else ""
                                }
                    
                    json_functions.append(json_func)
        
        return json.dumps(json_functions, indent=2)

    def _process_json_response(self, response_content: str, user_input: str) -> Dict[str, Any]:
        """Process JSON response from HTTP LLM"""
        try:
            # Clean up response content
            content = response_content.strip()
            
            # Remove markdown formatting if present
            if content.startswith("```json"):
                content = content.replace("```json", "").replace("```", "").strip()
            elif content.startswith("```"):
                content = content.replace("```", "").strip()
            
            # Parse JSON
            parsed = json.loads(content)
            
            # Validate response structure
            if not isinstance(parsed, dict):
                raise ValueError("Response is not a JSON object")
            
            response_type = parsed.get("type", "command")
            
            if response_type == "clarification":
                return {
                    "type": "clarification",
                    "question": parsed.get("question", "Could you clarify your request?"),
                    "options": parsed.get("options", [])
                }
            
            elif response_type == "info":
                return {
                    "type": "info",
                    "message": parsed.get("message", "Information not available")
                }
            
            elif response_type in ["command", "multi_command"]:
                function_calls = parsed.get("function_calls", [])
                
                if not function_calls:
                    raise ValueError("No function calls found in response")
                
                if len(function_calls) == 1:
                    # Single command
                    func_call = function_calls[0]
                    return {
                        "type": "command",
                        "method": func_call["name"],
                        "params": func_call.get("arguments", {}),
                        "feedback": parsed.get("feedback", f"Executing {func_call['name']}")
                    }
                else:
                    # Multiple commands
                    commands = []
                    for func_call in function_calls:
                        commands.append({
                            "method": func_call["name"],
                            "params": func_call.get("arguments", {}),
                            "feedback": self._generate_function_feedback(func_call["name"], func_call.get("arguments", {}))
                        })
                    
                    return {
                        "type": "multi_command",
                        "commands": commands,
                        "feedback": parsed.get("feedback", f"Executing {len(commands)} commands")
                    }
            
            else:
                raise ValueError(f"Unknown response type: {response_type}")
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            logger.error(f"Response content: {response_content}")
            return {
                "type": "error",
                "message": "Failed to parse LLM response",
                "suggestion": "Please try rephrasing your command."
            }
        except Exception as e:
            logger.error(f"Error processing JSON response: {e}")
            return {
                "type": "error",
                "message": f"Error processing response: {str(e)}",
                "suggestion": "Please try again."
            }