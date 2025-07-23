"""
Bookmark HTML/XML Manipulation Engine for Seismic Navigation Speech Interface

This module provides comprehensive XML parsing and manipulation capabilities for Tornado bookmark files.
It handles the complex nested structure of bookmark XML and provides a clean interface for modifications.

Enterprise-level implementation with proper file organization and structure management.
"""

import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional, Tuple, List
import copy
import logging
from pathlib import Path

from .file_structure import FileStructure
from .seismic_types import SeismicTerminology, BookmarkParameters

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BookmarkTemplate:
    """Represents a parsed bookmark template with validation and manipulation capabilities"""
    
    def __init__(self, xml_content: str):
        """Initialize template from XML content"""
        self.xml_content = xml_content
        self.root = None
        self.snapshot = None # This element contains all the key visualization parameters (orientation, gain, etc.).
        self._parse_xml()
        self._validate_structure() # remove when safe
    
    def _parse_xml(self):
        """Parse XML content and extract snapshot element"""
        try:
            self.root = ET.fromstring(self.xml_content)
            self.snapshot = self.root.find('SNAPSHOT')
            if self.snapshot is None:
                raise ValueError("No SNAPSHOT element found in bookmark XML")
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML structure: {e}")
    
    def _validate_structure(self):
        """Validate that all required elements are present"""
        required_elements = [
            'ORIENT', 'SHIFT', 'SCALE', 'X', 'Y', 'Z',
            'SEISMIC_VISIBILITY', 'ATTRIBUTE_VISIBILITY', 'HORIZON_VISIBILITY',
            'SEISMIC_COLORMAP'
        ]
        
        missing_elements = []
        for element in required_elements:
            if self.snapshot.find(element) is None:
                missing_elements.append(element)
        
        if missing_elements:
            logger.warning(f"Missing elements in bookmark template: {missing_elements}")
    
    def get_parameters(self) -> BookmarkParameters:
        """Extract current parameters from the template"""
        params = BookmarkParameters()
        
        # Navigation parameters
        x_elem = self.snapshot.find('X')
        if x_elem is not None:
            pos_elem = x_elem.find('POSITION')
            if pos_elem is not None:
                params.x_position = float(pos_elem.text)
            vis_elem = x_elem.find('VISIBLE')
            if vis_elem is not None:
                params.x_visible = vis_elem.text == 'T'
        
        y_elem = self.snapshot.find('Y')
        if y_elem is not None:
            pos_elem = y_elem.find('POSITION')
            if pos_elem is not None:
                params.y_position = float(pos_elem.text)
            vis_elem = y_elem.find('VISIBLE')
            if vis_elem is not None:
                params.y_visible = vis_elem.text == 'T'
        
        z_elem = self.snapshot.find('Z')
        if z_elem is not None:
            pos_elem = z_elem.find('POSITION')
            if pos_elem is not None:
                params.z_position = float(pos_elem.text)
            vis_elem = z_elem.find('VISIBLE')
            if vis_elem is not None:
                params.z_visible = vis_elem.text == 'T'
        
        # View parameters
        orient_elem = self.snapshot.find('ORIENT')
        if orient_elem is not None:
            orient_values = [float(x) for x in orient_elem.text.split()]
            params.orient = tuple(orient_values)
        
        shift_elem = self.snapshot.find('SHIFT')
        if shift_elem is not None:
            shift_values = [float(x) for x in shift_elem.text.split()]
            params.shift = tuple(shift_values)
        
        scale_elem = self.snapshot.find('SCALE')
        if scale_elem is not None:
            scale_values = [float(x) for x in scale_elem.text.split()]
            params.scale = tuple(scale_values)
        
        # Data visibility
        params.seismic_visible = self._get_visibility('SEISMIC_VISIBILITY')
        params.attribute_visible = self._get_visibility('ATTRIBUTE_VISIBILITY')
        params.horizon_visible = self._get_visibility('HORIZON_VISIBILITY')
        params.well_visible = self._get_visibility('WELL_VISIBILITY')
        params.cigpick_visible = self._get_visibility('CIGPICK_VISIBILITY')
        params.misc_plot_visible = self._get_visibility('MISC_PLOT_VISIBILITY')
        params.profile_visible = self._get_visibility('PROFILE_VISIBILITY')
        
        # Display parameters
        seismic_colormap = self.snapshot.find('SEISMIC_COLORMAP/SPECTRUM')
        if seismic_colormap is not None:
            range_elem = seismic_colormap.find('RANGE')
            if range_elem is not None:
                range_values = [float(x) for x in range_elem.text.split()]
                params.seismic_range = tuple(range_values)
            
            times_elem = seismic_colormap.find('TIMES')
            if times_elem is not None:
                params.seismic_times = int(times_elem.text)
            
            index_elem = seismic_colormap.find('COLORMAP_INDEX')
            if index_elem is not None:
                params.seismic_colormap_index = int(index_elem.text)
            
            default_elem = seismic_colormap.find('RANGE_IS_DEFAULT')
            if default_elem is not None:
                params.seismic_range_is_default = default_elem.text == 'T'
        
        return params
    
    def _get_visibility(self, element_name: str) -> bool:
        """Helper to get visibility boolean from element"""
        elem = self.snapshot.find(element_name)
        return elem is not None and elem.text == 'T'
    
    def to_xml_string(self) -> str:
        """Convert template back to XML string"""
        return ET.tostring(self.root, encoding='unicode')


class BookmarkHTMLEngine:
    """Main engine for bookmark HTML/XML manipulation"""
    
    def __init__(self, default_template_name: str = "default_bookmark.html"):
        self.default_template: BookmarkTemplate = load_template(default_template_name)
        self.terminology = SeismicTerminology()
        # Ensure directory structure exists
        FileStructure.ensure_directories()
    
    def load_template(self, template_name: str = "default_bookmark.html") -> BookmarkTemplate:
        """Load bookmark template from templates directory into a BookmarkTemplate Object"""
        try:
            # Try to load from templates directory first
            template_path = FileStructure.get_template_path(template_name)
            
            if not template_path.exists():
                raise FileNotFoundError(f"Template file not found: {template_name}")
            
            with open(template_path, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            
            template = BookmarkTemplate(xml_content)
            logger.info(f"Successfully loaded bookmark template from {template_path}")
            return template
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Template file not found: {template_name}")
        except Exception as e:
            raise ValueError(f"Failed to load template: {e}")
    
    def create_valid_bookmark(self, output_name: str = "valid_bookmark.html") -> bool:
        """Create valid_bookmark.html in the bookmarks directory from default_bookmark.html in templates folder"""
        try:
            # Save to bookmarks directory
            output_path = FileStructure.BOOKMARKS_DIR / output_name
            return self.save_bookmark_html(self.default_template.to_xml_string(), str(output_path))
        except Exception as e:
            logger.error(f"Failed to create valid bookmark: {e}")
            return False
   
    def modify_position(self, bookmark_xml: str, x: float, y: float, z: float) -> str:
        """Modify position parameters in bookmark XML"""
        if not bookmark_xml:
            raise ValueError("Empty bookmark XML provided")
        
        try:
            root = ET.fromstring(bookmark_xml)
            snapshot = root.find('SNAPSHOT')
            
            # Update X position (crossline)
            x_elem = snapshot.find('X/POSITION')
            if x_elem is not None:
                x_elem.text = str(x)
            
            # Update Y position (inline)
            y_elem = snapshot.find('Y/POSITION')
            if y_elem is not None:
                y_elem.text = str(y)
            
            # Update Z position (depth)
            z_elem = snapshot.find('Z/POSITION')
            if z_elem is not None:
                z_elem.text = str(z)
            
            logger.info(f"Modified position to X={x}, Y={y}, Z={z}")
            return ET.tostring(root, encoding='unicode')
            
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML structure: {e}")
    
    def toggle_data_visibility(self, bookmark_xml: str, data_type: str, visible: bool) -> str:
        """Toggle visibility of data types in bookmark XML"""
        if not bookmark_xml:
            raise ValueError("Empty bookmark XML provided")
        
        try:
            # Map data type to XML element name
            data_type_map = {
                'seismic': 'SEISMIC_VISIBILITY',
                'attribute': 'ATTRIBUTE_VISIBILITY',
                'horizon': 'HORIZON_VISIBILITY',
                'well': 'WELL_VISIBILITY',
                'cigpick': 'CIGPICK_VISIBILITY',
                'misc_plot': 'MISC_PLOT_VISIBILITY',
                'profile': 'PROFILE_VISIBILITY'
            }
            
            element_name = data_type_map.get(data_type.lower())
            if not element_name:
                raise ValueError(f"Unknown data type: {data_type}")
            
            root = ET.fromstring(bookmark_xml)
            snapshot = root.find('SNAPSHOT')
            
            vis_elem = snapshot.find(element_name)
            if vis_elem is not None:
                vis_elem.text = 'T' if visible else 'F'
                logger.info(f"Set {data_type} visibility to {visible}")
            
            return ET.tostring(root, encoding='unicode')
            
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML structure: {e}")
    
    def toggle_slice_visibility(self, bookmark_xml: str, slice_type: str, visible: bool) -> str:
        """Toggle slice visibility (X=crossline, Y=inline, Z=depth)"""
        if not bookmark_xml:
            raise ValueError("Empty bookmark XML provided")
        
        try:
            axis = self.terminology.get_axis_from_term(slice_type)
            
            root = ET.fromstring(bookmark_xml)
            snapshot = root.find('SNAPSHOT')
            
            slice_elem = snapshot.find(f'{axis}/VISIBLE')
            if slice_elem is not None:
                slice_elem.text = 'T' if visible else 'F'
                logger.info(f"Set {slice_type} ({axis}) slice visibility to {visible}")
            
            return ET.tostring(root, encoding='unicode')
            
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML structure: {e}")
    
    def zoom_adjustment(self, bookmark_xml: str, zoom_factor: float = None, scale_x: float = None, scale_y: float = None) -> str:
        """
        Adjust zoom level by modifying SCALE values
        
        Args:
            bookmark_xml: The bookmark XML content to modify
            zoom_factor: Multiplier to apply to both scale values (e.g., 1.5 for 50% zoom in, 0.5 for 50% zoom out)
            scale_x: Direct X scale value (overrides zoom_factor if provided)
            scale_y: Direct Y scale value (overrides zoom_factor if provided)
        
        Returns:
            Modified bookmark XML string
        """
        if not bookmark_xml:
            raise ValueError("Empty bookmark XML provided")
        
        try:
            root = ET.fromstring(bookmark_xml)
            snapshot = root.find('SNAPSHOT')
            
            if snapshot is None:
                raise ValueError("No SNAPSHOT element found in bookmark XML")
            
            scale_elem = snapshot.find('SCALE')
            if scale_elem is not None:
                # Parse current scale values
                current_values = [float(x) for x in scale_elem.text.split()]
                if len(current_values) != 2:
                    current_values = [1.0, 1.0]  # Default scale
                
                # Calculate new scale values
                if scale_x is not None and scale_y is not None:
                    # Use direct values
                    new_scale_x, new_scale_y = scale_x, scale_y
                elif zoom_factor is not None:
                    # Apply zoom factor to current values
                    new_scale_x = current_values[0] * zoom_factor
                    new_scale_y = current_values[1] * zoom_factor
                else:
                    raise ValueError("Either zoom_factor or both scale_x and scale_y must be provided")
                
                # Ensure scale values are within reasonable bounds
                new_scale_x = max(0.01, min(10.0, new_scale_x))  # Clamp between 0.01 and 10.0
                new_scale_y = max(0.01, min(10.0, new_scale_y))
                
                scale_elem.text = f"{new_scale_x} {new_scale_y}"
                logger.info(f"Adjusted zoom/scale to {new_scale_x}, {new_scale_y}")
            else:
                logger.warning("SCALE element not found in bookmark")
            
            return ET.tostring(root, encoding='unicode')
            
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML structure: {e}")
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid scale values or XML structure: {e}")
    
    # Task 1.4 Display Adjustment Functions
    def adjust_gain(self, bookmark_xml: str, operation: str, value: float = None) -> str:
        """
        Adjust seismic gain by modifying SEISMIC_COLORMAP.SPECTRUM.RANGE values
        
        Args:
            bookmark_xml: The bookmark XML content to modify
            operation: One of 'increase', 'decrease', 'set', or 'reset'
            value: For 'set' operation, the target gain value
        
        Returns:
            Modified bookmark XML string
        """
        if not bookmark_xml:
            raise ValueError("Empty bookmark XML provided")
        
        try:
            root = ET.fromstring(bookmark_xml)
            snapshot = root.find('SNAPSHOT')
            
            if snapshot is None:
                raise ValueError("No SNAPSHOT element found in bookmark XML")
            
            range_elem = snapshot.find('SEISMIC_COLORMAP/SPECTRUM/RANGE')
            default_elem = snapshot.find('SEISMIC_COLORMAP/SPECTRUM/RANGE_IS_DEFAULT')
            
            if range_elem is None:
                logger.warning("SEISMIC_COLORMAP/SPECTRUM/RANGE element not found in bookmark")
                return bookmark_xml
            
            if operation == 'reset':
                # Reset to default range and set flag
                if default_elem is not None:
                    default_elem.text = 'T'
                # Use a reasonable default range - this should be configurable
                range_elem.text = "-200000 200000"
                logger.info("Reset gain to default range")
                
            else:
                # Parse current range values
                current_range = [float(x) for x in range_elem.text.split()]
                if len(current_range) != 2:
                    current_range = [-200000.0, 200000.0]  # Default fallback
                
                min_val, max_val = current_range
                current_range_size = max_val - min_val
                
                if operation == 'increase':
                    # Increase gain = decrease range (make range smaller for higher sensitivity)
                    new_range_size = current_range_size * 0.8  # 20% smaller range
                    center = (min_val + max_val) / 2
                    new_min = center - new_range_size / 2
                    new_max = center + new_range_size / 2
                    
                elif operation == 'decrease':
                    # Decrease gain = increase range (make range larger for lower sensitivity)
                    new_range_size = current_range_size * 1.25  # 25% larger range
                    center = (min_val + max_val) / 2
                    new_min = center - new_range_size / 2
                    new_max = center + new_range_size / 2
                    
                elif operation == 'set':
                    if value is None:
                        raise ValueError("Value must be provided for 'set' operation")
                    # Calculate appropriate range based on specified gain value
                    # Higher gain value = smaller range
                    base_range = 400000  # Base range size
                    new_range_size = base_range / max(0.1, value)  # Prevent division by zero
                    center = (min_val + max_val) / 2
                    new_min = center - new_range_size / 2
                    new_max = center + new_range_size / 2
                    
                else:
                    raise ValueError(f"Unknown operation: {operation}")
                
                # Apply the new range
                range_elem.text = f"{new_min} {new_max}"
                
                # Mark as non-default when manually adjusted
                if default_elem is not None:
                    default_elem.text = 'F'
                
                logger.info(f"Adjusted gain ({operation}) to range {new_min} - {new_max}")
            
            return ET.tostring(root, encoding='unicode')
            
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML structure: {e}")
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid gain adjustment parameters or XML structure: {e}")
    
    def change_colormap(self, bookmark_xml: str, colormap_index: int) -> str:
        """
        Change the seismic colormap by modifying COLORMAP_INDEX values
        
        Args:
            bookmark_xml: The bookmark XML content to modify
            colormap_index: The new colormap index (typically 0-15)
        
        Returns:
            Modified bookmark XML string
        """
        if not bookmark_xml:
            raise ValueError("Empty bookmark XML provided")
        
        try:
            root = ET.fromstring(bookmark_xml)
            snapshot = root.find('SNAPSHOT')
            
            if snapshot is None:
                raise ValueError("No SNAPSHOT element found in bookmark XML")
            
            colormap_elem = snapshot.find('SEISMIC_COLORMAP/SPECTRUM/COLORMAP_INDEX')
            
            if colormap_elem is not None:
                # Validate colormap index range (typically 0-15 for most systems)
                if not (0 <= colormap_index <= 15):
                    logger.warning(f"Colormap index {colormap_index} may be out of typical range (0-15)")
                
                colormap_elem.text = str(colormap_index)
                logger.info(f"Changed colormap index to {colormap_index}")
            else:
                logger.warning("SEISMIC_COLORMAP/SPECTRUM/COLORMAP_INDEX element not found in bookmark")
            
            return ET.tostring(root, encoding='unicode')
            
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML structure: {e}")
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid colormap parameters or XML structure: {e}")
    
    def adjust_color_scale(self, bookmark_xml: str, times_value: int) -> str:
        """
        Adjust color scale by modifying SEISMIC_COLORMAP.SPECTRUM.TIMES values
        
        Args:
            bookmark_xml: The bookmark XML content to modify
            times_value: The new TIMES value (typically 1-10)
        
        Returns:
            Modified bookmark XML string
        """
        if not bookmark_xml:
            raise ValueError("Empty bookmark XML provided")
        
        try:
            root = ET.fromstring(bookmark_xml)
            snapshot = root.find('SNAPSHOT')
            
            if snapshot is None:
                raise ValueError("No SNAPSHOT element found in bookmark XML")
            
            times_elem = snapshot.find('SEISMIC_COLORMAP/SPECTRUM/TIMES')
            
            if times_elem is not None:
                # Validate times value range (typically 1-10)
                if times_value < 1:
                    logger.warning(f"TIMES value {times_value} is less than 1, setting to 1")
                    times_value = 1
                elif times_value > 10:
                    logger.warning(f"TIMES value {times_value} is greater than 10, may cause display issues")
                
                times_elem.text = str(times_value)
                logger.info(f"Adjusted color scale TIMES to {times_value}")
            else:
                logger.warning("SEISMIC_COLORMAP/SPECTRUM/TIMES element not found in bookmark")
            
            return ET.tostring(root, encoding='unicode')
            
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML structure: {e}")
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid color scale parameters or XML structure: {e}")

    def save_bookmark_html(self, bookmark_content: str, filepath: str) -> bool:
        """Save bookmark content to HTML file"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(bookmark_content)
            
            logger.info(f"Successfully saved bookmark to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save bookmark: {e}")
            return False