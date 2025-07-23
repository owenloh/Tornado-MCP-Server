"""
Crossline/Slice Navigation Handler using VolumeLocation method

This module implements navigation to specific crosslines, inlines, and depth positions
using the VolumeLocation + captureImage workaround method as specified in the design.

The handler provides user-friendly coordinate navigation with proper validation,
error handling, and temporary file cleanup.
"""

import time
import logging
from pathlib import Path
from typing import Optional, Tuple
import glob
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CrosslineNavigationHandler:
    """
    Handler for crossline/slice navigation using VolumeLocation method
    
    This class implements the VolumeLocation + captureImage workaround for navigating
    to specific coordinates in the seismic data. It handles coordinate validation,
    error handling, and cleanup of temporary files.
    """
    
    def __init__(self, temp_file_path: str = "/tpa/trutl07/Tornado_Agentic/"):
        """
        Initialize the navigation handler
        
        Args:
            temp_file_path: Path where temporary capture files will be created
        """
        self.temp_file_path = temp_file_path
        self.temp_file_prefix = "temp_capture"
        
        # Coordinate validation ranges (these should be configurable based on data)
        self.xl_range = (25000, 26000)  # Typical crossline range
        self.il_range = (8000, 10000)   # Typical inline range  
        self.z_range = (1000, 4000)     # Typical depth range
        
        logger.info(f"CrosslineNavigationHandler initialized with temp path: {temp_file_path}")
    
    def navigate_to_crossline(self, xl_coord: int) -> bool:
        """
        Navigate to specific crossline using VolumeLocation.setXL() + captureImage() workaround
        
        Args:
            xl_coord: Crossline coordinate (e.g., 25619)
            
        Returns:
            bool: True if navigation successful, False otherwise
        """
        try:
            # Validate crossline coordinate
            if not self._validate_xl_coordinate(xl_coord):
                logger.error(f"Invalid crossline coordinate: {xl_coord}")
                return False
            
            logger.info(f"Navigating to crossline {xl_coord}")
            
            # This is the implementation that would be used in the Tornado environment
            # For now, we'll simulate the process and log the steps
            success = self._execute_volume_location_navigation(xl=xl_coord)
            
            if success:
                logger.info(f"Successfully navigated to crossline {xl_coord}")
                return True
            else:
                logger.error(f"Failed to navigate to crossline {xl_coord}")
                return False
                
        except Exception as e:
            logger.error(f"Error navigating to crossline {xl_coord}: {e}")
            return False
    
    def navigate_to_inline(self, il_coord: int) -> bool:
        """
        Navigate to specific inline using VolumeLocation.setIL() + captureImage() workaround
        
        Args:
            il_coord: Inline coordinate (e.g., 9000)
            
        Returns:
            bool: True if navigation successful, False otherwise
        """
        try:
            # Validate inline coordinate
            if not self._validate_il_coordinate(il_coord):
                logger.error(f"Invalid inline coordinate: {il_coord}")
                return False
            
            logger.info(f"Navigating to inline {il_coord}")
            
            # This is the implementation that would be used in the Tornado environment
            success = self._execute_volume_location_navigation(il=il_coord)
            
            if success:
                logger.info(f"Successfully navigated to inline {il_coord}")
                return True
            else:
                logger.error(f"Failed to navigate to inline {il_coord}")
                return False
                
        except Exception as e:
            logger.error(f"Error navigating to inline {il_coord}: {e}")
            return False
    
    def navigate_to_depth(self, z_coord: float) -> bool:
        """
        Navigate to specific depth using VolumeLocation.setZ() + captureImage() workaround
        
        Args:
            z_coord: Depth coordinate (e.g., 1000.0)
            
        Returns:
            bool: True if navigation successful, False otherwise
        """
        try:
            # Validate depth coordinate
            if not self._validate_z_coordinate(z_coord):
                logger.error(f"Invalid depth coordinate: {z_coord}")
                return False
            
            logger.info(f"Navigating to depth {z_coord}")
            
            # This is the implementation that would be used in the Tornado environment
            success = self._execute_volume_location_navigation(z=z_coord)
            
            if success:
                logger.info(f"Successfully navigated to depth {z_coord}")
                return True
            else:
                logger.error(f"Failed to navigate to depth {z_coord}")
                return False
                
        except Exception as e:
            logger.error(f"Error navigating to depth {z_coord}: {e}")
            return False
    
    def navigate_to_coordinates(self, xl: int, il: int, z: Optional[float] = None) -> bool:
        """
        Navigate to specific coordinates (crossline, inline, and optionally depth)
        
        Args:
            xl: Crossline coordinate
            il: Inline coordinate
            z: Optional depth coordinate
            
        Returns:
            bool: True if navigation successful, False otherwise
        """
        try:
            # Validate all coordinates
            if not self.validate_coordinates(xl, il, z):
                return False
            
            logger.info(f"Navigating to coordinates XL={xl}, IL={il}" + 
                       (f", Z={z}" if z is not None else ""))
            
            # Execute navigation with all coordinates
            success = self._execute_volume_location_navigation(xl=xl, il=il, z=z)
            
            if success:
                logger.info(f"Successfully navigated to coordinates XL={xl}, IL={il}" + 
                           (f", Z={z}" if z is not None else ""))
                return True
            else:
                logger.error(f"Failed to navigate to coordinates XL={xl}, IL={il}" + 
                            (f", Z={z}" if z is not None else ""))
                return False
                
        except Exception as e:
            logger.error(f"Error navigating to coordinates: {e}")
            return False
    
    def _execute_volume_location_navigation(self, xl: Optional[int] = None, 
                                          il: Optional[int] = None, 
                                          z: Optional[float] = None) -> bool:
        """
        Execute the VolumeLocation + captureImage navigation sequence
        
        This method contains the actual Tornado API calls that would be executed
        in the Tornado environment. For development/testing, it simulates the process.
        
        Args:
            xl: Optional crossline coordinate
            il: Optional inline coordinate  
            z: Optional depth coordinate
            
        Returns:
            bool: True if navigation successful, False otherwise
        """
        try:
            # In the actual Tornado environment, this would be:
            """
            # Create VolumeLocation instance
            vol_location = VolumeLocation()
            
            # Set coordinates as specified
            if xl is not None:
                vol_location.setXL(xl)
            if il is not None:
                vol_location.setIL(il)
            if z is not None:
                vol_location.setZ(z)
            
            # Set up capture parameters
            file_parameters = CaptureFileParameters()
            file_parameters.setPrefix(self.temp_file_prefix)
            file_parameters.setPath(self.temp_file_path)
            file_parameters.setFormat('png')
            
            params = CaptureParameters()
            params.setFileParameters(file_parameters)
            params.setLocations(vol_location)
            
            # Execute capture to apply navigation
            captureImage(Window.MAIN_VIEW).capture(params)
            
            # Wait for operation to complete
            time.sleep(5)
            
            # Clean up temporary files immediately
            self.cleanup_temp_files(self.temp_file_path, self.temp_file_prefix)
            """
            
            # For development/testing, simulate the process
            logger.info("Simulating VolumeLocation navigation sequence:")
            if xl is not None:
                logger.info(f"  - Setting XL coordinate to {xl}")
            if il is not None:
                logger.info(f"  - Setting IL coordinate to {il}")
            if z is not None:
                logger.info(f"  - Setting Z coordinate to {z}")
            
            logger.info("  - Executing captureImage() to apply navigation")
            logger.info("  - Waiting for operation to complete...")
            
            # Simulate processing time
            time.sleep(0.1)  # Reduced for testing
            
            logger.info("  - Cleaning up temporary files")
            # In development, we'll simulate cleanup
            self._simulate_cleanup()
            
            return True
            
        except Exception as e:
            logger.error(f"Error in VolumeLocation navigation sequence: {e}")
            return False
    
    def cleanup_temp_files(self, path: str, prefix: str = "temp_capture") -> None:
        """
        Delete temporary capture files immediately after navigation
        
        Args:
            path: Directory path where temp files are located
            prefix: Filename prefix to match for deletion
        """
        try:
            # Create pattern to match temp files
            pattern = os.path.join(path, f"{prefix}*.png")
            temp_files = glob.glob(pattern)
            
            deleted_count = 0
            for temp_file in temp_files:
                try:
                    os.remove(temp_file)
                    deleted_count += 1
                    logger.debug(f"Deleted temp file: {temp_file}")
                except OSError as e:
                    logger.warning(f"Failed to delete temp file {temp_file}: {e}")
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} temporary capture files")
            else:
                logger.debug("No temporary capture files found to clean up")
                
        except Exception as e:
            logger.error(f"Error during temp file cleanup: {e}")
    
    def _simulate_cleanup(self) -> None:
        """Simulate cleanup for development/testing"""
        logger.info("  - Simulated cleanup of temporary capture files")
    
    def validate_coordinates(self, xl: int, il: int, z: Optional[float]) -> bool:
        """
        Validate coordinate values against expected ranges
        
        Args:
            xl: Crossline coordinate
            il: Inline coordinate
            z: Optional depth coordinate
            
        Returns:
            bool: True if all coordinates are valid, False otherwise
        """
        try:
            # Validate crossline
            if not self._validate_xl_coordinate(xl):
                return False
            
            # Validate inline
            if not self._validate_il_coordinate(il):
                return False
            
            # Validate depth if provided
            if z is not None and not self._validate_z_coordinate(z):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating coordinates: {e}")
            return False
    
    def _validate_xl_coordinate(self, xl: int) -> bool:
        """Validate crossline coordinate"""
        if not isinstance(xl, int):
            logger.error(f"Crossline coordinate must be an integer, got {type(xl)}")
            return False
        
        if not (self.xl_range[0] <= xl <= self.xl_range[1]):
            logger.error(f"Crossline coordinate {xl} outside valid range {self.xl_range}")
            return False
        
        return True
    
    def _validate_il_coordinate(self, il: int) -> bool:
        """Validate inline coordinate"""
        if not isinstance(il, int):
            logger.error(f"Inline coordinate must be an integer, got {type(il)}")
            return False
        
        if not (self.il_range[0] <= il <= self.il_range[1]):
            logger.error(f"Inline coordinate {il} outside valid range {self.il_range}")
            return False
        
        return True
    
    def _validate_z_coordinate(self, z: float) -> bool:
        """Validate depth coordinate"""
        if not isinstance(z, (int, float)):
            logger.error(f"Depth coordinate must be a number, got {type(z)}")
            return False
        
        if not (self.z_range[0] <= z <= self.z_range[1]):
            logger.error(f"Depth coordinate {z} outside valid range {self.z_range}")
            return False
        
        return True
    
    def set_coordinate_ranges(self, xl_range: Tuple[int, int], 
                            il_range: Tuple[int, int], 
                            z_range: Tuple[float, float]) -> None:
        """
        Set valid coordinate ranges for validation
        
        Args:
            xl_range: (min, max) crossline range
            il_range: (min, max) inline range
            z_range: (min, max) depth range
        """
        self.xl_range = xl_range
        self.il_range = il_range
        self.z_range = z_range
        
        logger.info(f"Updated coordinate ranges - XL: {xl_range}, IL: {il_range}, Z: {z_range}")
    
    def get_coordinate_ranges(self) -> dict:
        """
        Get current coordinate validation ranges
        
        Returns:
            dict: Dictionary with xl_range, il_range, and z_range
        """
        return {
            'xl_range': self.xl_range,
            'il_range': self.il_range,
            'z_range': self.z_range
        }