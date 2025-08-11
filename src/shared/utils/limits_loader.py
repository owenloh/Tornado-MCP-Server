#!/usr/bin/env python3
"""
Transformation Limits Loader

Loads and manages transformation limits from transformation_limits.json
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

class TransformationLimits:
    """Load and manage transformation limits from configuration file"""
    
    def __init__(self, limits_file: Optional[str] = None):
        """
        Initialize limits loader
        
        Args:
            limits_file: Path to limits file. If None, looks for transformation_limits.json in src
        """
        if limits_file is None:
            # Get src directory (3 levels up from src/shared/utils/limits_loader.py)
            src_dir = Path(__file__).parent.parent.parent
            self.limits_file = src_dir / "transformation_limits.json"
        else:
            self.limits_file = Path(limits_file)
        
        self.limits = {}
        self.load_limits()
    
    def load_limits(self) -> bool:
        """
        Load limits from file
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.limits_file.exists():
                print(f"Limits file not found: {self.limits_file}")
                print("Using default limits")
                self._create_default_limits()
                return False
            
            with open(self.limits_file, 'r', encoding='utf-8') as f:
                self.limits = json.load(f)
            
            print(f"Transformation limits loaded from {self.limits_file}")
            return True
            
        except Exception as e:
            print(f"Error loading limits: {e}")
            print("Using default limits")
            self._create_default_limits()
            return False
    
    def _create_default_limits(self):
        """Create default limits if file doesn't exist"""
        self.limits = {
            "position": {
                "x": {"min": 100000, "max": 200000},
                "y": {"min": 100000, "max": 150000},
                "z": {"min": 1000, "max": 6000}
            },
            "scale": {
                "x": {"min": 0.1, "max": 3.0},
                "y": {"min": 0.1, "max": 3.0}
            },
            "rotation": {
                "auto_normalize": True
            },
            "gain": {
                "min": 0.1,
                "max": 5.0
            },
            "colormap": {
                "min": 0,
                "max": 15,
                "integer_only": True
            },
            "system": {
                "max_commands_per_cycle": 10,
                "max_clarifications": 2
            }
        }
    
    def get_position_limits(self, axis: str) -> Tuple[float, float]:
        """Get position limits for specified axis (x, y, z)"""
        axis_limits = self.limits.get("position", {}).get(axis, {})
        return axis_limits.get("min", 0), axis_limits.get("max", 1000000)
    
    def get_scale_limits(self, axis: str) -> Tuple[float, float]:
        """Get scale limits for specified axis (x, y)"""
        axis_limits = self.limits.get("scale", {}).get(axis, {})
        return axis_limits.get("min", 0.1), axis_limits.get("max", 3.0)
    
    def get_gain_limits(self) -> Tuple[float, float]:
        """Get gain limits"""
        gain_limits = self.limits.get("gain", {})
        return gain_limits.get("min", 0.1), gain_limits.get("max", 5.0)
    
    def get_colormap_limits(self) -> Tuple[int, int]:
        """Get colormap limits"""
        colormap_limits = self.limits.get("colormap", {})
        return colormap_limits.get("min", 0), colormap_limits.get("max", 15)
    
    def is_colormap_integer_only(self) -> bool:
        """Check if colormap requires integer values only"""
        return self.limits.get("colormap", {}).get("integer_only", True)
    
    def is_rotation_auto_normalize(self) -> bool:
        """Check if rotation should be auto-normalized"""
        return self.limits.get("rotation", {}).get("auto_normalize", True)
    
    def get_system_limit(self, key: str) -> int:
        """Get system limit by key"""
        return self.limits.get("system", {}).get(key, 10)
    
    def validate_position(self, axis: str, value: float) -> Tuple[bool, str]:
        """Validate position value against limits"""
        min_val, max_val = self.get_position_limits(axis)
        if min_val <= value <= max_val:
            return True, ""
        return False, f"{axis.upper()} position {value} out of range ({min_val}-{max_val})"
    
    def validate_scale(self, axis: str, value: float) -> Tuple[bool, str]:
        """Validate scale value against limits"""
        min_val, max_val = self.get_scale_limits(axis)
        if min_val <= value <= max_val:
            return True, ""
        return False, f"Scale {axis.upper()} {value} out of range ({min_val}-{max_val})"
    
    def validate_gain(self, value: float) -> Tuple[bool, str]:
        """Validate gain value against limits"""
        min_val, max_val = self.get_gain_limits()
        if min_val <= value <= max_val:
            return True, ""
        return False, f"Gain {value} out of range ({min_val}-{max_val})"
    
    def validate_colormap(self, value: int) -> Tuple[bool, str]:
        """Validate colormap value against limits"""
        min_val, max_val = self.get_colormap_limits()
        
        # Check if integer only
        if self.is_colormap_integer_only():
            try:
                value = int(value)
            except (ValueError, TypeError):
                return False, f"Colormap index must be an integer, got {value}"
        
        if min_val <= value <= max_val:
            return True, ""
        return False, f"Colormap index {value} out of range ({min_val}-{max_val})"
    
    def get_limits_summary(self) -> str:
        """Get a formatted summary of all limits"""
        pos_x_min, pos_x_max = self.get_position_limits("x")
        pos_y_min, pos_y_max = self.get_position_limits("y")
        pos_z_min, pos_z_max = self.get_position_limits("z")
        scale_x_min, scale_x_max = self.get_scale_limits("x")
        scale_y_min, scale_y_max = self.get_scale_limits("y")
        gain_min, gain_max = self.get_gain_limits()
        colormap_min, colormap_max = self.get_colormap_limits()
        
        return f"""Current Transformation Limits:
- Position ranges: X({pos_x_min}-{pos_x_max}), Y({pos_y_min}-{pos_y_max}), Z({pos_z_min}-{pos_z_max})
- Scale ranges: X({scale_x_min}-{scale_x_max}), Y({scale_y_min}-{scale_y_max})
- Rotation: {'Auto-normalized to -π to π' if self.is_rotation_auto_normalize() else 'Manual limits'}
- Gain range: {gain_min}-{gain_max}
- Colormap range: {colormap_min}-{colormap_max} ({'integer only' if self.is_colormap_integer_only() else 'any number'})"""


# Global limits instance
_limits_instance = None

def get_limits() -> TransformationLimits:
    """Get global limits instance (singleton pattern)"""
    global _limits_instance
    if _limits_instance is None:
        _limits_instance = TransformationLimits()
    return _limits_instance

def reload_limits() -> TransformationLimits:
    """Reload limits from file"""
    global _limits_instance
    _limits_instance = TransformationLimits()
    return _limits_instance