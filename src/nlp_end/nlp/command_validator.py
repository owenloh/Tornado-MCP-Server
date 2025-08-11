#!/usr/bin/env python3
"""
JSON-RPC Command Validator for Seismic Navigation

This module provides validation for JSON-RPC commands to ensure they conform
to the expected format and parameter ranges before being sent to Firebase.

Features:
- JSON-RPC format validation
- Parameter type and range checking
- Seismic domain-specific validation
- Detailed error messages with suggestions
- Integration with existing command system
"""

import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of command validation"""
    valid: bool
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.suggestions is None:
            self.suggestions = []


class CommandValidator:
    """Validates JSON-RPC commands for seismic navigation"""
    
    def __init__(self):
        """Initialize validator with command specifications"""
        self.command_specs = self._define_command_specifications()
    
    def _define_command_specifications(self) -> Dict[str, Dict]:
        """Define specifications for all valid commands"""
        return {
            # Position and Navigation Commands
            "update_position": {
                "description": "Update crossline, inline, and depth position",
                "required_params": ["x", "y", "z"],
                "optional_params": [],
                "param_types": {"x": float, "y": float, "z": float},
                "param_ranges": {
                    "x": (100000, 200000, "Crossline position"),
                    "y": (100000, 150000, "Inline position"), 
                    "z": (1000, 6000, "Depth position")
                }
            },
            "update_orientation": {
                "description": "Update view rotation angles",
                "required_params": ["rot1", "rot2", "rot3"],
                "optional_params": [],
                "param_types": {"rot1": float, "rot2": float, "rot3": float},
                "param_ranges": {
                    "rot1": (-3.14159, 3.14159, "Rotation 1 (radians)"),
                    "rot2": (-3.14159, 3.14159, "Rotation 2 (radians)"),
                    "rot3": (-3.14159, 3.14159, "Rotation 3 (radians)")
                }
            },
            "update_scale": {
                "description": "Update zoom/scale values",
                "required_params": ["scale_x", "scale_y"],
                "optional_params": [],
                "param_types": {"scale_x": float, "scale_y": float},
                "param_ranges": {
                    "scale_x": (0.1, 3.0, "X scale factor"),
                    "scale_y": (0.1, 3.0, "Y scale factor")
                }
            },
            "update_shift": {
                "description": "Update view shift/translation",
                "required_params": ["shift_x", "shift_y", "shift_z"],
                "optional_params": [],
                "param_types": {"shift_x": float, "shift_y": float, "shift_z": float},
                "param_ranges": {
                    "shift_x": (-5000, 5000, "X shift"),
                    "shift_y": (-5000, 5000, "Y shift"),
                    "shift_z": (-5000, 5000, "Z shift")
                }
            },
            
            # Visibility Commands
            "update_visibility": {
                "description": "Toggle data type visibility",
                "required_params": [],
                "optional_params": ["seismic", "attribute", "horizon", "well"],
                "param_types": {"seismic": bool, "attribute": bool, "horizon": bool, "well": bool},
                "param_ranges": {}
            },
            "update_slice_visibility": {
                "description": "Toggle slice visibility",
                "required_params": [],
                "optional_params": ["x_slice", "y_slice", "z_slice"],
                "param_types": {"x_slice": bool, "y_slice": bool, "z_slice": bool},
                "param_ranges": {}
            },
            
            # Display Adjustment Commands
            "update_gain": {
                "description": "Adjust seismic gain/amplitude",
                "required_params": ["gain_value"],
                "optional_params": [],
                "param_types": {"gain_value": float},
                "param_ranges": {
                    "gain_value": (0.1, 5.0, "Gain value (1.0 = default)")
                }
            },
            "update_colormap": {
                "description": "Change colormap/color scheme",
                "required_params": ["colormap_index"],
                "optional_params": [],
                "param_types": {"colormap_index": int},
                "param_ranges": {
                    "colormap_index": (0, 15, "Colormap index")
                }
            },
            "update_color_scale": {
                "description": "Adjust color scale multiplier",
                "required_params": ["times_value"],
                "optional_params": [],
                "param_types": {"times_value": int},
                "param_ranges": {
                    "times_value": (1, 10, "Color scale times")
                }
            },
            
            # Quick Action Commands (no parameters)
            "zoom_in": {
                "description": "Zoom into the seismic view",
                "required_params": [],
                "optional_params": [],
                "param_types": {},
                "param_ranges": {}
            },
            "zoom_out": {
                "description": "Zoom out of the seismic view", 
                "required_params": [],
                "optional_params": [],
                "param_types": {},
                "param_ranges": {}
            },
            "zoom_reset": {
                "description": "Reset zoom to default level",
                "required_params": [],
                "optional_params": [],
                "param_types": {},
                "param_ranges": {}
            },
            "rotate_left": {
                "description": "Rotate view to the left",
                "required_params": [],
                "optional_params": [],
                "param_types": {},
                "param_ranges": {}
            },
            "rotate_right": {
                "description": "Rotate view to the right",
                "required_params": [],
                "optional_params": [],
                "param_types": {},
                "param_ranges": {}
            },
            "increase_gain": {
                "description": "Increase seismic gain/amplitude",
                "required_params": [],
                "optional_params": [],
                "param_types": {},
                "param_ranges": {}
            },
            "decrease_gain": {
                "description": "Decrease seismic gain/amplitude",
                "required_params": [],
                "optional_params": [],
                "param_types": {},
                "param_ranges": {}
            },
            
            # State Management Commands
            "undo_action": {
                "description": "Undo the last action",
                "required_params": [],
                "optional_params": [],
                "param_types": {},
                "param_ranges": {}
            },
            "redo_action": {
                "description": "Redo the last undone action",
                "required_params": [],
                "optional_params": [],
                "param_types": {},
                "param_ranges": {}
            },
            "reset_parameters": {
                "description": "Reset all parameters to default values",
                "required_params": [],
                "optional_params": [],
                "param_types": {},
                "param_ranges": {}
            },
            "reload_template": {
                "description": "Reload the bookmark template",
                "required_params": [],
                "optional_params": [],
                "param_types": {},
                "param_ranges": {}
            }
        }
    
    def validate_command(self, command: Dict[str, Any]) -> ValidationResult:
        """
        Validate a JSON-RPC command
        
        Args:
            command: Command dictionary with 'method' and 'params'
            
        Returns:
            ValidationResult: Validation result with errors and suggestions
        """
        result = ValidationResult(valid=True, errors=[], warnings=[], suggestions=[])
        
        # Validate JSON-RPC structure
        structure_valid = self._validate_structure(command, result)
        if not structure_valid:
            result.valid = False
            return result
        
        method = command["method"]
        params = command.get("params", {})
        
        # Validate method exists
        if method not in self.command_specs:
            result.valid = False
            result.errors.append(f"Unknown method: '{method}'")
            result.suggestions.append(f"Available methods: {', '.join(sorted(self.command_specs.keys()))}")
            return result
        
        # Validate parameters
        spec = self.command_specs[method]
        self._validate_parameters(params, spec, result)
        
        if result.errors:
            result.valid = False
        
        return result
    
    def _validate_structure(self, command: Dict[str, Any], result: ValidationResult) -> bool:
        """Validate basic JSON-RPC structure"""
        if not isinstance(command, dict):
            result.errors.append("Command must be a dictionary")
            return False
        
        if "method" not in command:
            result.errors.append("Missing required field: 'method'")
            result.suggestions.append("Command format: {'method': 'command_name', 'params': {...}}")
            return False
        
        if not isinstance(command["method"], str):
            result.errors.append("Method must be a string")
            return False
        
        if "params" in command and not isinstance(command["params"], dict):
            result.errors.append("Params must be a dictionary")
            return False
        
        return True
    
    def _validate_parameters(self, params: Dict[str, Any], spec: Dict, result: ValidationResult):
        """Validate command parameters against specification"""
        required_params = spec["required_params"]
        optional_params = spec["optional_params"]
        param_types = spec["param_types"]
        param_ranges = spec["param_ranges"]
        
        # Check required parameters
        for param in required_params:
            if param not in params:
                result.errors.append(f"Missing required parameter: '{param}'")
                result.suggestions.append(f"Required parameters: {required_params}")
        
        # Check parameter types and ranges
        for param, value in params.items():
            # Check if parameter is allowed
            if param not in required_params and param not in optional_params:
                result.warnings.append(f"Unexpected parameter: '{param}'")
                continue
            
            # Check parameter type
            if param in param_types:
                expected_type = param_types[param]
                if not isinstance(value, expected_type):
                    # Try to convert numeric types
                    if expected_type in [int, float] and isinstance(value, (int, float)):
                        if expected_type == int:
                            params[param] = int(value)
                        else:
                            params[param] = float(value)
                    else:
                        result.errors.append(f"Parameter '{param}' must be {expected_type.__name__}, got {type(value).__name__}")
                        continue
            
            # Check parameter range
            if param in param_ranges:
                min_val, max_val, description = param_ranges[param]
                if not (min_val <= value <= max_val):
                    result.errors.append(f"{description} '{param}' = {value} out of range ({min_val} to {max_val})")
                    result.suggestions.append(f"Valid range for {param}: {min_val} to {max_val}")
    
    def validate_json_string(self, json_string: str) -> Tuple[ValidationResult, Optional[Dict]]:
        """
        Validate JSON string and parse command
        
        Args:
            json_string: JSON string to validate
            
        Returns:
            Tuple of (ValidationResult, parsed_command or None)
        """
        result = ValidationResult(valid=True, errors=[], warnings=[], suggestions=[])
        
        # Try to parse JSON
        try:
            command = json.loads(json_string)
        except json.JSONDecodeError as e:
            result.valid = False
            result.errors.append(f"Invalid JSON: {str(e)}")
            result.suggestions.append("Ensure proper JSON format with double quotes")
            return result, None
        
        # Validate command structure and parameters
        validation_result = self.validate_command(command)
        
        return validation_result, command if validation_result.valid else None
    
    def get_command_help(self, method: Optional[str] = None) -> str:
        """
        Get help information for commands
        
        Args:
            method: Specific method to get help for, or None for all commands
            
        Returns:
            str: Help information
        """
        if method:
            if method not in self.command_specs:
                return f"Unknown command: {method}"
            
            spec = self.command_specs[method]
            help_text = f"Command: {method}\n"
            help_text += f"Description: {spec['description']}\n"
            
            if spec['required_params']:
                help_text += f"Required parameters: {', '.join(spec['required_params'])}\n"
            if spec['optional_params']:
                help_text += f"Optional parameters: {', '.join(spec['optional_params'])}\n"
            
            if spec['param_ranges']:
                help_text += "Parameter ranges:\n"
                for param, (min_val, max_val, desc) in spec['param_ranges'].items():
                    help_text += f"  {param}: {min_val} to {max_val} ({desc})\n"
            
            return help_text
        else:
            # Return summary of all commands
            help_text = "Available Commands:\n\n"
            
            categories = {
                "Position & Navigation": ["update_position", "update_orientation", "update_scale", "update_shift"],
                "Visibility": ["update_visibility", "update_slice_visibility"],
                "Display": ["update_gain", "update_colormap", "update_color_scale"],
                "Quick Actions": ["zoom_in", "zoom_out", "zoom_reset", "rotate_left", "rotate_right", "increase_gain", "decrease_gain"],
                "State Management": ["undo_action", "redo_action", "reset_parameters", "reload_template"]
            }
            
            for category, commands in categories.items():
                help_text += f"{category}:\n"
                for cmd in commands:
                    if cmd in self.command_specs:
                        help_text += f"  {cmd}: {self.command_specs[cmd]['description']}\n"
                help_text += "\n"
            
            return help_text
    
    def suggest_corrections(self, invalid_command: Dict[str, Any]) -> List[str]:
        """
        Suggest corrections for invalid commands
        
        Args:
            invalid_command: Invalid command dictionary
            
        Returns:
            List of correction suggestions
        """
        suggestions = []
        
        if "method" in invalid_command:
            method = invalid_command["method"]
            
            # Find similar method names
            similar_methods = []
            for valid_method in self.command_specs.keys():
                if method.lower() in valid_method.lower() or valid_method.lower() in method.lower():
                    similar_methods.append(valid_method)
            
            if similar_methods:
                suggestions.append(f"Did you mean: {', '.join(similar_methods[:3])}?")
        
        return suggestions


def main():
    """Test the command validator"""
    validator = CommandValidator()
    
    # Test valid commands
    test_commands = [
        {"method": "update_position", "params": {"x": 165000, "y": 115000, "z": 4000}},
        {"method": "zoom_in", "params": {}},
        {"method": "update_gain", "params": {"gain_value": 1.5}},
        {"method": "invalid_method", "params": {}},
        {"method": "update_position", "params": {"x": 999999, "y": 115000, "z": 4000}}  # Out of range
    ]
    
    for i, cmd in enumerate(test_commands, 1):
        print(f"\nTest {i}: {cmd}")
        result = validator.validate_command(cmd)
        print(f"Valid: {result.valid}")
        if result.errors:
            print(f"Errors: {result.errors}")
        if result.warnings:
            print(f"Warnings: {result.warnings}")
        if result.suggestions:
            print(f"Suggestions: {result.suggestions}")


if __name__ == "__main__":
    main()