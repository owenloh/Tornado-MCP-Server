import sys
from pathlib import Path
import platform

# Only add linux-venv path if running on Linux with Python 3.6.8
if platform.system() == 'Linux' and sys.version_info[:2] == (3, 6):
    venv_site_packages = Path(__file__).resolve().parent.parent.parent / '.linux-venv' / 'lib' / 'python3.6' / 'site-packages'
    sys.path.insert(0, str(venv_site_packages))


from typing import Tuple
from dataclasses import dataclass
import xml.etree.ElementTree as ET
import logging

logger = logging.getLogger(__name__)

@dataclass
class BookmarkParameters:
    """Container for all bookmark parameters that can be modified"""
    # Slice Position
    x_position: float = 160112.5
    y_position: float = 112487.5
    z_position: float = 3500.0

    # Slice visibility
    x_visible: bool = True
    y_visible: bool = True
    z_visible: bool = False

    # View parameters
    orient: Tuple[float, float, float] = (0.0, 0.39269908169872414, -0.78539816339744828)
    shift: Tuple[float, float, float] = (-1122.499999999998, 521.33883476483174, -1601.125)
    scale: Tuple[float, float] = (0.75116878400787368, 0.75116878400787368)

    # Data visibility
    seismic_visible: bool = True
    attribute_visible: bool = False
    horizon_visible: bool = False
    well_visible: bool = True
    cigpick_visible: bool = True
    misc_plot_visible: bool = True
    profile_visible: bool = False

    # Display parameters
    seismic_range: Tuple[float, float] = (-197331.0, 187430.0)
    seismic_times: int = 1
    seismic_colormap_index: int = 3
    seismic_range_is_default: bool = False

class BookmarkTemplate:
    """Represents a parsed bookmark template with validation and manipulation capabilities"""
    def __init__(self, xml_content: str):
        """Initialize template from XML content"""
        self.xml_content = xml_content
        self.root = None
        self.snapshot = None
        self._parse_xml()
        self._validate_structure()

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