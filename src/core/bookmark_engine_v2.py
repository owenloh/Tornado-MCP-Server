import shutil
from pathlib import Path
import copy
import logging
import os
from .file_structure import FileStructure
from .bookmark_tools import BookmarkParameters, BookmarkTemplate
import re

# Mapping: param_name -> (tag, count) for tuples, or tag for single values
PARAM_PLACEHOLDER_MAP = {
    'x_position': 'X/POSITION',
    'y_position': 'Y/POSITION',
    'z_position': 'Z/POSITION',
    'x_visible': 'X/VISIBLE',
    'y_visible': 'Y/VISIBLE',
    'z_visible': 'Z/VISIBLE',
    'seismic_visible': 'SEISMIC_VISIBILITY',
    'attribute_visible': 'ATTRIBUTE_VISIBILITY',
    'horizon_visible': 'HORIZON_VISIBILITY',
    'well_visible': 'WELL_VISIBILITY',
    'cigpick_visible': 'CIGPICK_VISIBILITY',
    'misc_plot_visible': 'MISC_PLOT_VISIBILITY',
    'profile_visible': 'PROFILE_VISIBILITY',
    'seismic_colormap_index': 'COLORMAP_INDEX',
    'seismic_times': 'TIMES',
    # Tuple fields:
    'orient': ('ORIENT', 3),
    'shift': ('SHIFT', 3),
    'scale': ('SCALE', 2),
    'seismic_range': ('RANGE', 2),
}

def generate_master_template(template_str, param_map):
    """
    Replace values in template_str with {param} placeholders based on param_map.
    Handles both single-value and tuple fields.
    """
    for param, value in param_map.items():
        if isinstance(value, tuple):
            tag, count = value
            # Build regex for the tag
            pattern = rf'(<{tag}>)([\d\.\-\s]+)(</{tag}>)'
            # Build replacement string
            placeholders = ' '.join([f'{{{param}{i}}}' for i in range(count)])
            template_str = re.sub(pattern, rf'\1{placeholders}\3', template_str)
        else:
            tag_path = value.split('/')
            if len(tag_path) == 2:
                tag, subtag = tag_path
                pattern = rf'(<{tag}>.*?<{subtag}>)(.*?)(</{subtag}>.*?</{tag}>)'
                template_str = re.sub(pattern, rf'\1{{{param}}}\3', template_str, flags=re.DOTALL)
            else:
                tag = value
                pattern = rf'(<{tag}>)(.*?)(</{tag}>)'
                template_str = re.sub(pattern, rf'\1{{{param}}}\3', template_str)
    return template_str

logger = logging.getLogger(__name__)

class BookmarkHTMLEngineV2:
    """
    New engine using string template for bookmark generation and parameter management.
    - Uses a master template with {} placeholders.
    - All parameter changes update self.curr_params (BookmarkParameters).
    - update_params() writes to TEMP_BKM.html, loads into Tornado, and appends to history.
    """
    def load_template(self, template_name: str):
        """
        Load a template HTML file, copy it to TEMP_BKM.html, parse it for parameters,
        generate the master template with placeholders, and set curr_params.
        Calls update_params() at the end to sync state.
        """

        src_template = self.templates_dir / template_name
        if not src_template.exists():
            raise FileNotFoundError(f"Template file not found: {src_template}")
        shutil.copyfile(src_template, self.temp_bkm_path)

        self.curr_params = self._parse_temp_bkm_to_params()

        with open(self.temp_bkm_path, 'r', encoding='utf-8') as f:
            template_str = f.read()
        self.master_template = generate_master_template(template_str, PARAM_PLACEHOLDER_MAP)

    def __init__(self, template_name: str = "default_bookmark.html", in_tornado: bool = True):
        self.bookmarks_dir = FileStructure.BOOKMARKS_DIR
        self.templates_dir = FileStructure.TEMPLATES_DIR
        self.captures_dir = FileStructure.CAPTURES_DIR
        self.temp_bkm_path = self.bookmarks_dir / "TEMP_BKM.html"

        self.master_template = None
        self.curr_params = None
        self.default_params = None  # Default range from default bookmark
        self.history = []
        self.history_index = -1  # Points to the current state in historys

        # load initial template, also appends template params to self.curr_params
        self.load_template(template_name)
        
        # Store the default params from the loaded template
        self.default_params = copy.deepcopy(self.curr_params)
        
        logger.info(f"Initialization: loaded template, history_length={len(self.history)}, index={self.history_index}")

        # store whether we are actively controlling tornado or just the html file
        self.tornado = in_tornado
        self.vision_subclses = tuple()

        if self.tornado:
            try:
                # Specific imports from vision module - everything should be in vision
                import base
                from vision import (
                    BookmarkDisplay, BookmarkLocation, CaptureParameters, 
                    CaptureFileParameters, captureImage, Window
                )

                self.vision_subclses = BookmarkDisplay, BookmarkLocation, CaptureParameters, CaptureFileParameters, captureImage, Window

                # print("loading seismic")
                # vision.loadSeismic('a:eamea::trutl07:/seisml_miniproject/original_seismic_w_dipxy')
                # print("seismic loaded")
            except ImportError:
                print("Warning: not in tornado environment, vision module does not exist")
                print("Setting tornado mode to False for testing")
                self.tornado = False

        if self.tornado:

            # bkm
            self.bkm_dis = BookmarkDisplay()
            self.bkm_loc = BookmarkLocation()
            self.framing = captureImage(Window.MAIN_VIEW)

            # tornado capture
            self.capture_param_obj = CaptureParameters()

            # setting saving location for capture
            self.file_parameters = CaptureFileParameters()
            # self.file_parameters.setPrefix('test_capture')
            # self.file_parameters.setPath(str(self.captures_dir.resolve()))
            # self.file_parameters.setFormat('png')
            # self.capture_param_obj.setFileParameters(self.file_parameters)

        # update just to make sure
        logger.info("Calling final update_params() in initialization")
        self.update_params()
        logger.info(f"Initialization complete: history_length={len(self.history)}, index={self.history_index}, can_undo={self.can_undo}, undo_count={self.undo_count}")


    def _parse_temp_bkm_to_params(self) -> BookmarkParameters:
        """Parse TEMP_BKM.html and extract parameters into a BookmarkParameters object."""
        with open(self.temp_bkm_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        template = BookmarkTemplate(xml_content)
        return template.get_parameters()

    def _params_to_dict(self) -> dict:
        """Flatten BookmarkParameters for string formatting."""
        p = self.curr_params
        d = p.__dict__.copy()
        d.update({
            'orient0': p.orient[0], 'orient1': p.orient[1], 'orient2': p.orient[2],
            'shift0': p.shift[0], 'shift1': p.shift[1], 'shift2': p.shift[2],
            'scale0': p.scale[0], 'scale1': p.scale[1],
            'seismic_range0': p.seismic_range[0], 'seismic_range1': p.seismic_range[1],
            # Convert booleans to 'T'/'F'
            'x_visible': 'T' if p.x_visible else 'F',
            'y_visible': 'T' if p.y_visible else 'F',
            'z_visible': 'T' if p.z_visible else 'F',
            'seismic_visible': 'T' if p.seismic_visible else 'F',
            'attribute_visible': 'T' if p.attribute_visible else 'F',
            'horizon_visible': 'T' if p.horizon_visible else 'F',
            'well_visible': 'T' if p.well_visible else 'F',
            'cigpick_visible': 'T' if p.cigpick_visible else 'F',
            'misc_plot_visible': 'T' if p.misc_plot_visible else 'F',
            'profile_visible': 'T' if p.profile_visible else 'F',
        })
        return d

    def update_params(self):
        """
        1. Render self.curr_params into the master template.
        2. Write to TEMP_BKM.html in bookmarks folder.
        3. Load TEMP_BKM.html into Tornado (placeholder).
        4. Append a tuple (master_template, curr_params) to self.history (unless initial=True), keeping max 20 entries.
        """

        # write to temp_bkm_path
        params_dict = self._params_to_dict()
        bookmark_html = self.master_template.format(**params_dict)
        with open(self.temp_bkm_path, 'w', encoding='utf-8') as f:
            f.write(bookmark_html)
        # then load into tornado
        self._load_into_tornado(self.temp_bkm_path)

        # update history
        # here is the part that handles clearing the future redo branch once you update after an undo (creating/entering a new branch)
        if self.history_index < len(self.history) - 1:
            self.history = self.history[:self.history_index + 1]
        self.history.append((self.master_template, copy.deepcopy(self.curr_params)))
        self.history_index += 1
        if len(self.history) > 20:
            self.history.pop(0)
            self.history_index -= 1
        
        logger.info(f"History updated: length={len(self.history)}, index={self.history_index}, can_undo={self.can_undo}, undo_count={self.undo_count}")

    def undo(self):
        """Revert to the previous (template, params) in history, if possible."""
        logger.info(f"Undo requested: history_length={len(self.history)}, current_index={self.history_index}, can_undo={self.can_undo}")
        if self.history_index > 0:
            self.history_index -= 1
            self.master_template, params = self.history[self.history_index]
            self.curr_params = copy.deepcopy(params)
            self.update_params_no_history()
            logger.info(f"Undo: Reverted to history index {self.history_index}")
        else:
            logger.warning(f"Undo: Already at the oldest state; cannot undo. history_length={len(self.history)}, index={self.history_index}")

    def redo(self):
        """Advance to the next (template, params) in history, if possible."""
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.master_template, params = self.history[self.history_index]
            self.curr_params = copy.deepcopy(params)
            self.update_params_no_history()
            logger.info(f"Redo: Advanced to history index {self.history_index}")
        else:
            logger.warning("Redo: Already at the latest state; cannot redo.")

    def update_params_no_history(self):
        """
        Update TEMP_BKM.html and Tornado with the current template and parameters,
        but do not modify the history list or index.
        Used internally by undo/redo.
        """
        params_dict = self._params_to_dict()
        bookmark_html = self.master_template.format(**params_dict)
        with open(self.temp_bkm_path, 'w', encoding='utf-8') as f:
            f.write(bookmark_html)
        self._load_into_tornado(self.temp_bkm_path)

    def _load_into_tornado(self, bookmark_path: Path):
        """
        Load the bookmark into the Tornado app using BookmarkLocation from vision.
        """

        # bookmark_path = self.templates_dir / 'default_bookmark.html'

        if not self.tornado:
            print(f"'mock' loaded {self.curr_params} into tornado")
            return

        bookmark_file = str(bookmark_path)

        if os.path.exists(bookmark_file):

            # import base
            # from vision import (
            #     BookmarkDisplay, BookmarkLocation, CaptureParameters, 
            #     CaptureFileParameters, captureImage, Window
            # )
            
            BookmarkDisplay, BookmarkLocation, CaptureParameters, CaptureFileParameters, captureImage, Window = self.vision_subclses

            # bkm
            self.bkm_dis = BookmarkDisplay()
            self.bkm_loc = BookmarkLocation()
            self.framing = captureImage(Window.MAIN_VIEW)

            # tornado capture
            self.capture_param_obj = CaptureParameters()

            # setting saving location for capture
            self.file_parameters = CaptureFileParameters()
            
            # have to initiatlise this everytime?

            self.file_parameters.setPrefix('test_capture')
            self.file_parameters.setPath(str(self.captures_dir.resolve()))
            self.file_parameters.setFormat('png')
            self.capture_param_obj.setFileParameters(self.file_parameters)

            # after loading bookmark file, the first bookmark inside is used, by name
            self.bkm_dis.load(bookmark_file)
            self.bkm_loc.load(bookmark_file)

            print(bookmark_file + '   number of bookmarks saved is   ' + str(self.bkm_dis.size()))
            
            bkm_name = self.bkm_dis.getBookmarkName(self.bkm_dis.size()-1)
 
            self.bkm_dis.selectBookmark([bkm_name])
            self.bkm_loc.selectBookmark([bkm_name])

            # need to add setLocation and BookmarkLocation() as well
            self.capture_param_obj.setDisplayParameters(self.bkm_dis)
            self.capture_param_obj.setLocations(self.bkm_loc)
            logger.info('checkpoint before capture, configured params')
            self.framing.capture(self.capture_param_obj)
        else:
            logger.warning(f"Bookmark file '{bookmark_file}' does not exist. Please create it manually in the GUI.")
        

    # --- Parameter adjustment functions ---
    @property
    def can_undo(self) -> bool:
        """Return True if undo is possible (not at the oldest state)."""
        return self.history_index > 0

    @property
    def can_redo(self) -> bool:
        """Return True if redo is possible (not at the latest state)."""
        return self.history_index < len(self.history) - 1

    @property
    def undo_count(self) -> int:
        """Return the number of undo operations available."""
        return self.history_index

    @property
    def redo_count(self) -> int:
        """Return the number of redo operations available."""
        return len(self.history) - 1 - self.history_index

    def change_colormap(self, colormap_index: int):
        """Change the colormap index in curr_params."""
        old_value = self.curr_params.seismic_colormap_index
        self.curr_params.seismic_colormap_index = colormap_index
        logger.info(f"Colormap changed from {old_value} to {colormap_index}")

    def adjust_gain(self, gain_value: float):
        """
        Adjust seismic range based on a single gain parameter:
        - gain_value = 1: Default seismic range from the default bookmark
        - gain_value > 1: Narrower range (higher contrast)
        - gain_value < 1: Wider range (lower contrast)
        
        The function interpolates between these states based on the gain value.
        """
        # Get the default range values from the class initialization
        # These are initialized from the default bookmark
        DEFAULT_MIN, DEFAULT_MAX = self.default_params.seismic_range
        DEFAULT_RANGE = DEFAULT_MAX - DEFAULT_MIN
        DEFAULT_CENTER = (DEFAULT_MIN + DEFAULT_MAX) / 2
        
        # Store the old range for logging
        old_range = self.curr_params.seismic_range
        
        # Handle special case for gain = 1 (default range)
        if gain_value == 1.0:
            self.curr_params.seismic_range = (DEFAULT_MIN, DEFAULT_MAX)
            logger.info(f"Gain set to default (1.0): range changed from {old_range} to {self.curr_params.seismic_range}")
            return
            
        # Calculate the new range size based on gain_value
        if gain_value > 1.0:
            # For gain > 1, make the range narrower (higher contrast)
            # As gain increases, range decreases (higher contrast)
            new_range_size = DEFAULT_RANGE / gain_value
        else:
            # For gain < 1, make the range wider (lower contrast)
            # As gain approaches 0, range approaches a very large value (low contrast)
            # Ensure we don't divide by zero
            safe_gain = max(0.1, gain_value)
            new_range_size = DEFAULT_RANGE / safe_gain
            
        # Get the current center of the range
        current_min, current_max = self.curr_params.seismic_range
        current_center = (current_min + current_max) / 2
        
        # Calculate new min and max values around the current center
        new_min = current_center - new_range_size / 2
        new_max = current_center + new_range_size / 2
        
        # Update the seismic range
        self.curr_params.seismic_range = (new_min, new_max)
        logger.info(f"Gain set to {gain_value}: range changed from {old_range} to {self.curr_params.seismic_range}")

    def adjust_color_scale(self, times_value: int):
        """Adjust color scale multiplier in curr_params."""
        old_value = self.curr_params.seismic_times
        self.curr_params.seismic_times = max(1, min(10, times_value))
        logger.info(f"Color scale TIMES changed from {old_value} to {self.curr_params.seismic_times}")

    def adjust_zoom(self, zoom_factor: float = None, scale_x: float = None, scale_y: float = None):
        """Adjust zoom/scale in curr_params."""
        sx, sy = self.curr_params.scale
        old_scale = self.curr_params.scale
        if scale_x is not None and scale_y is not None:
            new_sx, new_sy = scale_x, scale_y
        elif zoom_factor is not None:
            new_sx = sx * zoom_factor
            new_sy = sy * zoom_factor
        else:
            raise ValueError("Either zoom_factor or both scale_x and scale_y must be provided")
        self.curr_params.scale = (max(0.01, min(10.0, new_sx)), max(0.01, min(10.0, new_sy)))
        logger.info(f"Scale changed from {old_scale} to {self.curr_params.scale}")

    def change_slices_position(self, x: float, y: float, z: float):
        """
        Update the crossline (x), inline (y), and depth (z) positions in curr_params.
        """
        old = (self.curr_params.x_position, self.curr_params.y_position, self.curr_params.z_position)
        self.curr_params.x_position = x
        self.curr_params.y_position = y
        self.curr_params.z_position = z
        logger.info(f"Position changed from {old} to {(x, y, z)}")
        
    def adjust_shift(self, x: float, y: float, z: float):
        """
        Update the shift values (x, y, z) in curr_params.
        """
        old = self.curr_params.shift
        self.curr_params.shift = (x, y, z)
        logger.info(f"Shift changed from {old} to {(x, y, z)}")

    def adjust_orientation(self, rot1: float, rot2: float, rot3: float):
        """
        Update the rotational orientations in curr_params.
        """
        old = self.curr_params.orient
        self.curr_params.orient = rot1, rot2, rot3
        logger.info(f"Position changed from {old} to {(rot1, rot2, rot3)}")

    def toggle_data_visibility(self, data_type: str, visible: bool):
        """
        Toggle visibility of a data type (e.g., 'seismic', 'attribute', 'horizon', 'well', 'cigpick', 'misc_plot', 'profile').
        """
        attr = f"{data_type.lower()}_visible"
        if hasattr(self.curr_params, attr):
            old = getattr(self.curr_params, attr)
            setattr(self.curr_params, attr, visible)
            logger.info(f"{attr} changed from {old} to {visible}")
        else:
            logger.warning(f"Unknown data type for visibility: {data_type}")

    def toggle_slice_visibility(self, slice_type: str, visible: bool):
        """
        Toggle visibility of a slice (crossline 'x', inline 'y', or depth 'z').
        """
        axis = slice_type.lower()
        attr = f"{axis}_visible"
        if hasattr(self.curr_params, attr):
            old = getattr(self.curr_params, attr)
            setattr(self.curr_params, attr, visible)
            logger.info(f"{attr} changed from {old} to {visible}")
        else:
            logger.warning(f"Unknown slice type for visibility: {slice_type}")

    # Add more parameter adjustment functions as needed...

    def create_valid_bookmark(self, output_name: str = "valid_bookmark.html") -> bool:
        """Utility: Save the current parameters as a valid bookmark file in the bookmarks directory."""
        try:
            params_dict = self._params_to_dict()
            bookmark_html = self.master_template.format(**params_dict)
            output_path = self.bookmarks_dir / output_name
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(bookmark_html)
            logger.info(f"Created valid bookmark at {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create valid bookmark: {e}")
            return False
