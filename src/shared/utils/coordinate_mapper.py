"""
Coordinate Mapping System for Seismic Navigation

This module provides linear transformation between seismic domain coordinates 
(crossline, inline, depth) and Cartesian coordinates (X, Y, Z) used by Tornado.

The mapping is configurable via config.json using two-point linear interpolation.
"""

import logging
from typing import Dict, Any, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CoordinatePoint:
    """A coordinate mapping point"""
    seismic_value: float  # crossline, inline, or depth
    cartesian_value: float  # X, Y, or Z


@dataclass
class LinearMapping:
    """Linear mapping between seismic and Cartesian coordinates"""
    point1: CoordinatePoint
    point2: CoordinatePoint
    
    def __post_init__(self):
        """Calculate linear transformation parameters"""
        # Calculate slope (m) and intercept (b) for: cartesian = m * seismic + b
        if self.point1.seismic_value == self.point2.seismic_value:
            raise ValueError("Cannot create mapping with identical seismic values")
        
        self.slope = (self.point2.cartesian_value - self.point1.cartesian_value) / \
                    (self.point2.seismic_value - self.point1.seismic_value)
        self.intercept = self.point1.cartesian_value - (self.slope * self.point1.seismic_value)
    
    def seismic_to_cartesian(self, seismic_value: float) -> int:
        """Convert seismic coordinate to Cartesian coordinate (returns integer)"""
        result = self.slope * seismic_value + self.intercept
        return int(round(result))
    
    def cartesian_to_seismic(self, cartesian_value: float) -> int:
        """Convert Cartesian coordinate to seismic coordinate (returns integer)"""
        result = (cartesian_value - self.intercept) / self.slope
        return int(round(result))


class CoordinateMapper:
    """
    Coordinate transformation system for seismic navigation.
    
    Provides bidirectional mapping between:
    - Crossline ↔ X
    - Inline ↔ Y  
    - Depth ↔ Z
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize coordinate mapper from configuration.
        
        Args:
            config: Configuration dictionary with coordinate_mapping section
        """
        self.config = config
        self.crossline_mapping = None
        self.inline_mapping = None
        self.depth_mapping = None
        
        self._initialize_mappings()
    
    def _initialize_mappings(self):
        """Initialize linear mappings from configuration"""
        try:
            coord_config = self.config.get('coordinate_mapping', {})
            
            # Initialize crossline to X mapping
            if 'crossline_to_x' in coord_config:
                crossline_config = coord_config['crossline_to_x']
                p1 = crossline_config['point1']
                p2 = crossline_config['point2']
                
                self.crossline_mapping = LinearMapping(
                    CoordinatePoint(p1['crossline'], p1['x']),
                    CoordinatePoint(p2['crossline'], p2['x'])
                )
                logger.info(f"Crossline mapping: slope={self.crossline_mapping.slope:.2f}, intercept={self.crossline_mapping.intercept:.2f}")
            
            # Initialize inline to Y mapping
            if 'inline_to_y' in coord_config:
                inline_config = coord_config['inline_to_y']
                p1 = inline_config['point1']
                p2 = inline_config['point2']
                
                self.inline_mapping = LinearMapping(
                    CoordinatePoint(p1['inline'], p1['y']),
                    CoordinatePoint(p2['inline'], p2['y'])
                )
                logger.info(f"Inline mapping: slope={self.inline_mapping.slope:.2f}, intercept={self.inline_mapping.intercept:.2f}")
            
            # Initialize depth to Z mapping
            if 'depth_to_z' in coord_config:
                depth_config = coord_config['depth_to_z']
                p1 = depth_config['point1']
                p2 = depth_config['point2']
                
                self.depth_mapping = LinearMapping(
                    CoordinatePoint(p1['depth'], p1['z']),
                    CoordinatePoint(p2['depth'], p2['z'])
                )
                logger.info(f"Depth mapping: slope={self.depth_mapping.slope:.2f}, intercept={self.depth_mapping.intercept:.2f}")
            
        except Exception as e:
            logger.error(f"Failed to initialize coordinate mappings: {e}")
            raise ValueError(f"Invalid coordinate mapping configuration: {e}")
    
    def seismic_to_cartesian(self, crossline: Optional[float] = None, 
                           inline: Optional[float] = None, 
                           depth: Optional[float] = None) -> Tuple[Optional[int], Optional[int], Optional[int]]:
        """
        Convert seismic coordinates to Cartesian coordinates.
        
        Args:
            crossline: Crossline value (optional)
            inline: Inline value (optional)
            depth: Depth value (optional)
            
        Returns:
            Tuple of (x, y, z) where None means no conversion requested
        """
        x = None
        y = None
        z = None
        
        if crossline is not None and self.crossline_mapping:
            x = self.crossline_mapping.seismic_to_cartesian(crossline)
            logger.debug(f"Crossline {crossline} → X {x:.2f}")
        
        if inline is not None and self.inline_mapping:
            y = self.inline_mapping.seismic_to_cartesian(inline)
            logger.debug(f"Inline {inline} → Y {y:.2f}")
        
        if depth is not None and self.depth_mapping:
            z = self.depth_mapping.seismic_to_cartesian(depth)
            logger.debug(f"Depth {depth} → Z {z:.2f}")
        
        return x, y, z
    
    def cartesian_to_seismic(self, x: Optional[float] = None, 
                           y: Optional[float] = None, 
                           z: Optional[float] = None) -> Tuple[Optional[int], Optional[int], Optional[int]]:
        """
        Convert Cartesian coordinates to seismic coordinates.
        
        Args:
            x: X coordinate (optional)
            y: Y coordinate (optional)
            z: Z coordinate (optional)
            
        Returns:
            Tuple of (crossline, inline, depth) where None means no conversion requested
        """
        crossline = None
        inline = None
        depth = None
        
        if x is not None and self.crossline_mapping:
            crossline = self.crossline_mapping.cartesian_to_seismic(x)
            logger.debug(f"X {x:.2f} → Crossline {crossline:.2f}")
        
        if y is not None and self.inline_mapping:
            inline = self.inline_mapping.cartesian_to_seismic(y)
            logger.debug(f"Y {y:.2f} → Inline {inline:.2f}")
        
        if z is not None and self.depth_mapping:
            depth = self.depth_mapping.cartesian_to_seismic(z)
            logger.debug(f"Z {z:.2f} → Depth {depth:.2f}")
        
        return crossline, inline, depth
    
    def get_current_seismic_position(self, x: float, y: float, z: float) -> Dict[str, int]:
        """
        Get current position in seismic coordinates.
        
        Args:
            x, y, z: Current Cartesian coordinates
            
        Returns:
            Dictionary with crossline, inline, depth values (all integers)
        """
        crossline, inline, depth = self.cartesian_to_seismic(x, y, z)
        
        return {
            'crossline': crossline if crossline is not None else int(round(x)),
            'inline': inline if inline is not None else int(round(y)),
            'depth': depth if depth is not None else int(round(z))
        }
    
    def is_mapping_available(self) -> Dict[str, bool]:
        """Check which coordinate mappings are available"""
        return {
            'crossline': self.crossline_mapping is not None,
            'inline': self.inline_mapping is not None,
            'depth': self.depth_mapping is not None
        }


# Global coordinate mapper instance
_coordinate_mapper = None

def get_coordinate_mapper() -> CoordinateMapper:
    """Get global coordinate mapper instance (singleton pattern)"""
    global _coordinate_mapper
    if _coordinate_mapper is None:
        from shared.utils.config_loader import get_config
        config = get_config()
        _coordinate_mapper = CoordinateMapper(config.config)
    return _coordinate_mapper

def reload_coordinate_mapper() -> CoordinateMapper:
    """Reload coordinate mapper from configuration"""
    global _coordinate_mapper
    from shared.utils.config_loader import get_config
    config = get_config()
    _coordinate_mapper = CoordinateMapper(config.config)
    return _coordinate_mapper