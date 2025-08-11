"""
Seismic Navigation System

This module provides high-level navigation functions that work with seismic coordinates
(crossline, inline, depth) and automatically convert to Cartesian coordinates for Tornado.
"""

import logging
from typing import Dict, Any, Optional, Tuple
from shared.utils.coordinate_mapper import get_coordinate_mapper

logger = logging.getLogger(__name__)


class SeismicNavigator:
    """
    High-level seismic navigation system that handles coordinate transformations.
    
    This class provides user-friendly navigation methods that accept seismic coordinates
    and automatically convert them to Cartesian coordinates for the bookmark engine.
    """
    
    def __init__(self, bookmark_engine):
        """
        Initialize seismic navigator.
        
        Args:
            bookmark_engine: BookmarkHTMLEngineV2 instance
        """
        self.bookmark_engine = bookmark_engine
        self.coordinate_mapper = get_coordinate_mapper()
        
        # Log available mappings
        mappings = self.coordinate_mapper.is_mapping_available()
        logger.info(f"Seismic coordinate mappings: {mappings}")
    
    def move_to_seismic_position(self, crossline: Optional[float] = None, 
                               inline: Optional[float] = None, 
                               depth: Optional[float] = None) -> Dict[str, Any]:
        """
        Move to specified seismic coordinates.
        
        Args:
            crossline: Target crossline (optional)
            inline: Target inline (optional)
            depth: Target depth (optional)
            
        Returns:
            Dictionary with movement details and converted coordinates
        """
        try:
            # Convert seismic coordinates to Cartesian
            x, y, z = self.coordinate_mapper.seismic_to_cartesian(crossline, inline, depth)
            
            # Get current position for partial updates
            current_x = self.bookmark_engine.curr_params.x_position
            current_y = self.bookmark_engine.curr_params.y_position
            current_z = self.bookmark_engine.curr_params.z_position
            
            # Use current values if no new value provided
            target_x = x if x is not None else current_x
            target_y = y if y is not None else current_y
            target_z = z if z is not None else current_z
            
            # Ensure all coordinates are integers for XML compatibility
            target_x = int(round(target_x))
            target_y = int(round(target_y))
            target_z = int(round(target_z))
            
            # Execute the movement
            self.bookmark_engine.change_slices_position(target_x, target_y, target_z)
            self.bookmark_engine.update_params()
            
            # Get final seismic coordinates for feedback
            final_seismic = self.coordinate_mapper.get_current_seismic_position(target_x, target_y, target_z)
            
            # Build response message
            movements = []
            if crossline is not None:
                movements.append(f"crossline {crossline:.1f}")
            if inline is not None:
                movements.append(f"inline {inline:.1f}")
            if depth is not None:
                movements.append(f"depth {depth:.1f}")
            
            message = f"Moved to {', '.join(movements)}"
            
            return {
                'message': message,
                'seismic_coordinates': {
                    'crossline': final_seismic['crossline'],
                    'inline': final_seismic['inline'],
                    'depth': final_seismic['depth']
                },
                'cartesian_coordinates': {
                    'x': target_x,
                    'y': target_y,
                    'z': target_z
                }
            }
            
        except Exception as e:
            logger.error(f"Error in seismic navigation: {e}")
            return {
                'message': f"Navigation failed: {str(e)}",
                'error': str(e)
            }
    
    def get_current_seismic_position(self) -> Dict[str, Any]:
        """
        Get current position in both seismic and Cartesian coordinates.
        
        Returns:
            Dictionary with current position information
        """
        try:
            # Get current Cartesian coordinates
            current_x = self.bookmark_engine.curr_params.x_position
            current_y = self.bookmark_engine.curr_params.y_position
            current_z = self.bookmark_engine.curr_params.z_position
            
            # Convert to seismic coordinates
            seismic_pos = self.coordinate_mapper.get_current_seismic_position(current_x, current_y, current_z)
            
            return {
                'seismic_coordinates': seismic_pos,
                'cartesian_coordinates': {
                    'x': current_x,
                    'y': current_y,
                    'z': current_z
                },
                'mappings_available': self.coordinate_mapper.is_mapping_available()
            }
            
        except Exception as e:
            logger.error(f"Error getting current position: {e}")
            return {
                'error': str(e),
                'cartesian_coordinates': {
                    'x': self.bookmark_engine.curr_params.x_position,
                    'y': self.bookmark_engine.curr_params.y_position,
                    'z': self.bookmark_engine.curr_params.z_position
                }
            }
    
    def move_relative_seismic(self, crossline_delta: Optional[float] = None,
                            inline_delta: Optional[float] = None,
                            depth_delta: Optional[float] = None) -> Dict[str, Any]:
        """
        Move relative to current position in seismic coordinates.
        
        Args:
            crossline_delta: Crossline offset (optional)
            inline_delta: Inline offset (optional)
            depth_delta: Depth offset (optional)
            
        Returns:
            Dictionary with movement details
        """
        try:
            # Get current seismic position
            current_pos = self.get_current_seismic_position()
            current_seismic = current_pos['seismic_coordinates']
            
            # Calculate target seismic coordinates
            target_crossline = None
            target_inline = None
            target_depth = None
            
            if crossline_delta is not None:
                target_crossline = current_seismic['crossline'] + crossline_delta
            
            if inline_delta is not None:
                target_inline = current_seismic['inline'] + inline_delta
            
            if depth_delta is not None:
                target_depth = current_seismic['depth'] + depth_delta
            
            # Execute the movement
            return self.move_to_seismic_position(target_crossline, target_inline, target_depth)
            
        except Exception as e:
            logger.error(f"Error in relative seismic movement: {e}")
            return {
                'message': f"Relative movement failed: {str(e)}",
                'error': str(e)
            }