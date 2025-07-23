#!/usr/bin/env python3
"""
Tkinter-based Interactive GUI for real-time bookmark manipulation testing

This module provides a clean Tkinter-based GUI with proper layout management,
replacing the problematic matplotlib implementation that had overlapping elements.

Task 2.2: Create clean GUI with parameter controls
- Build GUI with sliders for crossline, inline, depth positions
- Add sliders for orientation angles (3 rotation axes)
- Add sliders for zoom/scale adjustment
- Add checkboxes for data visibility toggles
- Add sliders for gain range adjustment
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sys
import copy
from pathlib import Path
from typing import Optional
import pandas as pd

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from core.bookmark_engine_v2 import BookmarkHTMLEngineV2


class BookmarkGUITkinter:
    """Clean Tkinter-based GUI for bookmark parameter manipulation"""
    
    def __init__(self):
        self.engine = BookmarkHTMLEngineV2("default_bookmark.html", in_tornado=True)
        self.current_params = self.engine.curr_params
        print(f"Loaded template with params: {self.current_params}")
        
        # Initialize GUI
        self.setup_gui()
        
    def setup_gui(self):
        """Set up the Tkinter GUI with proper layout management"""
        # Create main window
        self.root = tk.Tk()
        self.root.title('Seismic Bookmark Parameter Control GUI - Tkinter Version')
        self.root.geometry('1200x700')
        self.root.configure(bg='#f0f0f0')
        
        # Create main container
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=10)
        
        # Configure grid weights for responsive layout
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Create left and right panels
        self.left_panel = ttk.Frame(self.main_frame)
        self.left_panel.grid(row=0, column=0, sticky=(tk.N, tk.W, tk.E, tk.S), padx=5)
        
        self.right_panel = ttk.Frame(self.main_frame)
        self.right_panel.grid(row=0, column=1, sticky=(tk.N, tk.W, tk.E, tk.S), padx=5)
        
        # Configure panel weights
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.rowconfigure(0, weight=1)
        
        # Configure internal panel weights
        self.left_panel.columnconfigure(0, weight=1)
        self.right_panel.columnconfigure(0, weight=1)
        
        # Configure row weights for panels
        # Left panel - equal weight for all sections
        self.left_panel.rowconfigure(0, weight=1)
        self.left_panel.rowconfigure(1, weight=1)
        self.left_panel.rowconfigure(2, weight=1)
        
        # Right panel - give more weight to status section
        self.right_panel.rowconfigure(0, weight=0)
        self.right_panel.rowconfigure(1, weight=0)
        self.right_panel.rowconfigure(2, weight=0)
        self.right_panel.rowconfigure(3, weight=3)  # Status section gets more space
        
        # Create left panel sections (position, orientation, view)
        self.create_position_section(self.left_panel)
        self.create_orientation_section(self.left_panel)
        self.create_view_section(self.left_panel)
        
        # Create right panel sections (visibility, display, actions, status)
        self.create_visibility_section(self.right_panel)
        self.create_display_section(self.right_panel)
        self.create_action_section(self.right_panel)
        self.create_status_section(self.right_panel)
        
        # Update initial parameter display
        self.update_parameter_display()
        
    def create_position_section(self, parent=None):
        """Create position controls section"""
        # Use provided parent or default to main_frame
        parent = parent or self.main_frame
        
        # Position frame
        pos_frame = ttk.LabelFrame(parent, text="Position Controls (Crossline/Inline/Depth)", padding="10")
        pos_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=2)
        pos_frame.columnconfigure(1, weight=1)
        pos_frame.columnconfigure(3, weight=1)
        pos_frame.columnconfigure(5, weight=1)
        
        # X Position (Crossline)
        ttk.Label(pos_frame, text="X (Crossline):").grid(row=0, column=0, sticky=tk.W, padx=2)
        self.x_var = tk.DoubleVar(value=self.current_params.x_position)
        self.x_scale = ttk.Scale(pos_frame, from_=100000, to=200000, variable=self.x_var, 
                                orient=tk.HORIZONTAL, command=self.update_x_label)
        self.x_scale.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=2)
        self.x_label = ttk.Label(pos_frame, text=f"{self.current_params.x_position:.1f}")
        self.x_label.grid(row=0, column=2, padx=2)
        
        # Y Position (Inline)
        ttk.Label(pos_frame, text="Y (Inline):").grid(row=1, column=0, sticky=tk.W, padx=2, pady=2)
        self.y_var = tk.DoubleVar(value=self.current_params.y_position)
        self.y_scale = ttk.Scale(pos_frame, from_=100000, to=150000, variable=self.y_var,
                                orient=tk.HORIZONTAL, command=self.update_y_label)
        self.y_scale.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=2, pady=2)
        self.y_label = ttk.Label(pos_frame, text=f"{self.current_params.y_position:.1f}")
        self.y_label.grid(row=1, column=2, padx=2, pady=2)
        
        # Z Position (Depth)
        ttk.Label(pos_frame, text="Z (Depth):").grid(row=2, column=0, sticky=tk.W, padx=2)
        self.z_var = tk.DoubleVar(value=self.current_params.z_position)
        self.z_scale = ttk.Scale(pos_frame, from_=1000, to=6000, variable=self.z_var,
                                orient=tk.HORIZONTAL, command=self.update_z_label)
        self.z_scale.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=2)
        self.z_label = ttk.Label(pos_frame, text=f"{self.current_params.z_position:.1f}")
        self.z_label.grid(row=2, column=2, padx=2)

        # Bind the sliders to update_position
        self.x_scale.bind("<ButtonRelease-1>", self.update_position)
        self.y_scale.bind("<ButtonRelease-1>", self.update_position)
        self.z_scale.bind("<ButtonRelease-1>", self.update_position)
        
    def create_orientation_section(self, parent=None):
        """Create orientation controls section"""
        # Use provided parent or default to main_frame
        parent = parent or self.main_frame
        
        # Orientation frame
        orient_frame = ttk.LabelFrame(parent, text="Orientation Controls (Rotation Angles)", padding="10")
        orient_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=2)
        orient_frame.columnconfigure(1, weight=1)
        orient_frame.columnconfigure(3, weight=1)
        orient_frame.columnconfigure(5, weight=1)
        
        orient = self.current_params.orient or (0, 0, 0)
        
        # Rotation 1 (Fixed)
        ttk.Label(orient_frame, text="Rot1 (Fixed):").grid(row=0, column=0, sticky=tk.W, padx=2)
        self.rot1_var = tk.DoubleVar(value=orient[0])
        self.rot1_scale = ttk.Scale(orient_frame, from_=-3.14159, to=3.14159, variable=self.rot1_var,
                                   orient=tk.HORIZONTAL, command=self.update_rot1_label)
        self.rot1_scale.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=2)
        self.rot1_label = ttk.Label(orient_frame, text=f"{orient[0]:.2f} rad")
        self.rot1_label.grid(row=0, column=2, padx=2)
        
        # Rotation 2 (Perpendicular)
        ttk.Label(orient_frame, text="Rot2 (Perp):").grid(row=1, column=0, sticky=tk.W, padx=2, pady=2)
        self.rot2_var = tk.DoubleVar(value=orient[1] if len(orient) > 1 else 0)
        self.rot2_scale = ttk.Scale(orient_frame, from_=-3.14159, to=3.14159, variable=self.rot2_var,
                                   orient=tk.HORIZONTAL, command=self.update_rot2_label)
        self.rot2_scale.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=2, pady=2)
        # self.rot2_scale.bind("<ButtonRelease-1>", self.on_rot2_commit)
        self.rot2_label = ttk.Label(orient_frame, text=f"{orient[1] if len(orient) > 1 else 0:.2f} rad")
        self.rot2_label.grid(row=1, column=2, padx=2, pady=2)
        
        # Rotation 3 (Z-axis)
        ttk.Label(orient_frame, text="Rot3 (Z-axis):").grid(row=2, column=0, sticky=tk.W, padx=2)
        self.rot3_var = tk.DoubleVar(value=orient[2] if len(orient) > 2 else 0)
        self.rot3_scale = ttk.Scale(orient_frame, from_=-3.14159, to=3.14159, variable=self.rot3_var,
                                   orient=tk.HORIZONTAL, command=self.update_rot3_label)
        self.rot3_scale.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=2)
        self.rot3_label = ttk.Label(orient_frame, text=f"{orient[2] if len(orient) > 2 else 0:.2f} rad")
        self.rot3_label.grid(row=2, column=2, padx=2)

        # bind teh slider to update_orientation()
        self.rot1_scale.bind("<ButtonRelease-1>", self.update_orientation)
        self.rot2_scale.bind("<ButtonRelease-1>", self.update_orientation)
        self.rot3_scale.bind("<ButtonRelease-1>", self.update_orientation)
        
    def create_view_section(self, parent=None):
        """Create view controls section with separate scale and shift sections"""
        # Use provided parent or default to main_frame
        parent = parent or self.main_frame
        
        # View frame
        view_frame = ttk.LabelFrame(parent, text="View Controls", padding="10")
        view_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=2)
        
        # Create separate frames for scale and shift
        self.create_scale_section(view_frame)
        self.create_shift_section(view_frame)
        
    def create_scale_section(self, parent_frame):
        """Create scale controls section"""
        # Scale frame
        scale_frame = ttk.LabelFrame(parent_frame, text="Scale/Zoom Controls", padding="10")
        scale_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=2, padx=2)
        scale_frame.columnconfigure(1, weight=1)
        
        scale = self.current_params.scale or (1.0, 1.0)
        
        # Scale X
        ttk.Label(scale_frame, text="Scale X:").grid(row=0, column=0, sticky=tk.W, padx=2)
        self.scale_x_var = tk.DoubleVar(value=scale[0])
        self.scale_x_scale = ttk.Scale(scale_frame, from_=0.1, to=3.0, variable=self.scale_x_var,
                                      orient=tk.HORIZONTAL, command=self.update_scale_x_label)
        self.scale_x_scale.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=2)
        self.scale_x_label = ttk.Label(scale_frame, text=f"{scale[0]:.2f}")
        self.scale_x_label.grid(row=0, column=2, padx=2)
        
        # Scale Y
        ttk.Label(scale_frame, text="Scale Y:").grid(row=1, column=0, sticky=tk.W, padx=2, pady=2)
        self.scale_y_var = tk.DoubleVar(value=scale[1] if len(scale) > 1 else scale[0])
        self.scale_y_scale = ttk.Scale(scale_frame, from_=0.1, to=3.0, variable=self.scale_y_var,
                                      orient=tk.HORIZONTAL, command=self.update_scale_y_label)
        self.scale_y_scale.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=2, pady=2)
        self.scale_y_label = ttk.Label(scale_frame, text=f"{scale[1] if len(scale) > 1 else scale[0]:.2f}")
        self.scale_y_label.grid(row=1, column=2, padx=2, pady=2)
        
        # Bind the sliders to update_scale
        self.scale_x_scale.bind("<ButtonRelease-1>", self.update_scale)
        self.scale_y_scale.bind("<ButtonRelease-1>", self.update_scale)
        
    def create_shift_section(self, parent_frame):
        """Create shift controls section"""
        # Shift frame
        shift_frame = ttk.LabelFrame(parent_frame, text="Shift Controls", padding="10")
        shift_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=2, padx=2)
        shift_frame.columnconfigure(1, weight=1)
        
        shift = self.current_params.shift or (0, 0, 0)
        
        # Shift X
        ttk.Label(shift_frame, text="Shift X:").grid(row=0, column=0, sticky=tk.W, padx=2)
        self.shift_x_var = tk.DoubleVar(value=shift[0])
        self.shift_x_scale = ttk.Scale(shift_frame, from_=-5000, to=5000, variable=self.shift_x_var,
                                      orient=tk.HORIZONTAL, command=self.update_shift_x_label)
        self.shift_x_scale.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=2)
        self.shift_x_label = ttk.Label(shift_frame, text=f"{shift[0]:.1f}")
        self.shift_x_label.grid(row=0, column=2, padx=2)
        
        # Shift Y
        ttk.Label(shift_frame, text="Shift Y:").grid(row=1, column=0, sticky=tk.W, padx=2, pady=2)
        self.shift_y_var = tk.DoubleVar(value=shift[1] if len(shift) > 1 else 0)
        self.shift_y_scale = ttk.Scale(shift_frame, from_=-5000, to=5000, variable=self.shift_y_var,
                                      orient=tk.HORIZONTAL, command=self.update_shift_y_label)
        self.shift_y_scale.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=2, pady=2)
        self.shift_y_label = ttk.Label(shift_frame, text=f"{shift[1] if len(shift) > 1 else 0:.1f}")
        self.shift_y_label.grid(row=1, column=2, padx=2, pady=2)
        
        # Shift Z
        ttk.Label(shift_frame, text="Shift Z:").grid(row=2, column=0, sticky=tk.W, padx=2)
        self.shift_z_var = tk.DoubleVar(value=shift[2] if len(shift) > 2 else 0)
        self.shift_z_scale = ttk.Scale(shift_frame, from_=-5000, to=5000, variable=self.shift_z_var,
                                      orient=tk.HORIZONTAL, command=self.update_shift_z_label)
        self.shift_z_scale.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=2)
        self.shift_z_label = ttk.Label(shift_frame, text=f"{shift[2] if len(shift) > 2 else 0:.1f}")
        self.shift_z_label.grid(row=2, column=2, padx=2)
        
        # Bind all shift sliders to the same update_shift method
        self.shift_x_scale.bind("<ButtonRelease-1>", self.update_shift)
        self.shift_y_scale.bind("<ButtonRelease-1>", self.update_shift)
        self.shift_z_scale.bind("<ButtonRelease-1>", self.update_shift)
      
    def create_visibility_section(self, parent=None):
        """Create visibility controls section"""
        # Use provided parent or default to main_frame
        parent = parent or self.main_frame
        
        # Visibility frame
        vis_frame = ttk.LabelFrame(parent, text="Data Visibility Controls", padding="10")
        vis_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=2)
        
        # Create two columns for checkboxes
        left_frame = ttk.Frame(vis_frame)
        left_frame.grid(row=0, column=0, sticky=(tk.W, tk.N), padx=2)
        right_frame = ttk.Frame(vis_frame)
        right_frame.grid(row=0, column=1, sticky=(tk.W, tk.N), padx=2)
        
        # Data visibility checkboxes (left column)
        self.seismic_var = tk.BooleanVar(value=self.current_params.seismic_visible)
        ttk.Checkbutton(left_frame, text="Seismic", variable=self.seismic_var, 
                       command=self.update_visibility).grid(row=0, column=0, sticky=tk.W, pady=2)
        
        self.attribute_var = tk.BooleanVar(value=self.current_params.attribute_visible)
        ttk.Checkbutton(left_frame, text="Attributes", variable=self.attribute_var,
                       command=self.update_visibility).grid(row=1, column=0, sticky=tk.W, pady=2)
        
        self.horizon_var = tk.BooleanVar(value=self.current_params.horizon_visible)
        ttk.Checkbutton(left_frame, text="Horizons", variable=self.horizon_var,
                       command=self.update_visibility).grid(row=2, column=0, sticky=tk.W, pady=2)
        
        self.well_var = tk.BooleanVar(value=self.current_params.well_visible)
        ttk.Checkbutton(left_frame, text="Wells", variable=self.well_var,
                       command=self.update_visibility).grid(row=3, column=0, sticky=tk.W, pady=2)
        
        # Slice visibility checkboxes (right column)
        self.x_slice_var = tk.BooleanVar(value=self.current_params.x_visible)
        ttk.Checkbutton(right_frame, text="X Slice", variable=self.x_slice_var,
                       command=self.update_slice_visibility).grid(row=0, column=0, sticky=tk.W, pady=2)
        
        self.y_slice_var = tk.BooleanVar(value=self.current_params.y_visible)
        ttk.Checkbutton(right_frame, text="Y Slice", variable=self.y_slice_var,
                       command=self.update_slice_visibility).grid(row=1, column=0, sticky=tk.W, pady=2)
        
        self.z_slice_var = tk.BooleanVar(value=self.current_params.z_visible)
        ttk.Checkbutton(right_frame, text="Z Slice", variable=self.z_slice_var,
                       command=self.update_slice_visibility).grid(row=2, column=0, sticky=tk.W, pady=2)
        
    def create_display_section(self, parent=None):
        """Create display adjustment controls section"""
        # Use provided parent or default to main_frame
        parent = parent or self.main_frame
        
        # Display frame
        display_frame = ttk.LabelFrame(parent, text="Display Adjustment Controls (Gain/Colormap)", padding="10")
        display_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=2)
        display_frame.columnconfigure(1, weight=1)
        display_frame.columnconfigure(3, weight=1)
        
        seismic_range = self.current_params.seismic_range or self.engine.default_params.seismic_range
        
        # Gain control slider
        ttk.Label(display_frame, text="Gain:").grid(row=0, column=0, sticky=tk.W, padx=2)
        
        # Calculate initial gain value based on current seismic range
        default_min, default_max = self.engine.default_params.seismic_range
        default_range = default_max - default_min
        current_min, current_max = seismic_range
        current_range = current_max - current_min
        
        # If current range is wider than default, gain < 1
        # If current range is narrower than default, gain > 1
        if current_range != 0:
            initial_gain = default_range / current_range
        else:
            initial_gain = 1.0
            
        self.gain_var = tk.DoubleVar(value=initial_gain)
        self.gain_scale = ttk.Scale(display_frame, from_=0.1, to=5.0, variable=self.gain_var,
                                   orient=tk.HORIZONTAL, command=self.update_gain_label)
        self.gain_scale.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=2)
        self.gain_label = ttk.Label(display_frame, text=f"{initial_gain:.1f}")
        self.gain_label.grid(row=0, column=2, padx=2)
        
        # Colormap Index
        ttk.Label(display_frame, text="Colormap Index:").grid(row=2, column=0, sticky=tk.W, padx=2)
        self.colormap_var = tk.IntVar(value=self.current_params.seismic_colormap_index or 3)
        self.colormap_scale = ttk.Scale(display_frame, from_=0, to=15, variable=self.colormap_var,
                                       orient=tk.HORIZONTAL, command=self.update_colormap_label)
        self.colormap_scale.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=2)
        self.colormap_label = ttk.Label(display_frame, text=f"{self.current_params.seismic_colormap_index or 3}")
        self.colormap_label.grid(row=2, column=2, padx=2)
        
        # Color Scale Times
        ttk.Label(display_frame, text="Color Scale:").grid(row=3, column=0, sticky=tk.W, padx=2, pady=2)
        self.times_var = tk.IntVar(value=self.current_params.seismic_times or 1)
        self.times_scale = ttk.Scale(display_frame, from_=1, to=10, variable=self.times_var,
                                    orient=tk.HORIZONTAL, command=self.update_times_label)
        self.times_scale.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=2, pady=2)
        self.times_label = ttk.Label(display_frame, text=f"{self.current_params.seismic_times or 1}")
        self.times_label.grid(row=3, column=2, padx=2, pady=2)

        # Bind Sliders to update function
        self.gain_scale.bind("<ButtonRelease-1>", self.update_gain)
        self.colormap_scale.bind("<ButtonRelease-1>", self.update_colormap)
        self.times_scale.bind("<ButtonRelease-1>", self.update_color_scale)

        
    def create_action_section(self, parent=None):
        """Create action buttons section"""
        # Use provided parent or default to main_frame
        parent = parent or self.main_frame
        
        # Action frame
        action_frame = ttk.LabelFrame(parent, text="Actions & Controls", padding="10")
        action_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=2)
        
        # Create button frames for organization
        button_frame1 = ttk.Frame(action_frame)
        button_frame1.grid(row=0, column=0, sticky=tk.W, padx=2)
        
        button_frame2 = ttk.Frame(action_frame)
        button_frame2.grid(row=1, column=0, sticky=tk.W, padx=2, pady=2)
        
        # Create template selection frame
        template_frame = ttk.Frame(action_frame)
        template_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), padx=2, pady=(10, 2))
        
        # Configure column weights for frames
        for i in range(4):
            button_frame1.columnconfigure(i, weight=1)
            button_frame2.columnconfigure(i, weight=1)
        
        template_frame.columnconfigure(1, weight=1)
        
        # File operations buttons
        ttk.Button(button_frame1, text="Reset to Default", command=self.reset_parameters).grid(row=0, column=0, padx=2)
        ttk.Button(button_frame1, text="Reload Template", command=self.reload_template).grid(row=0, column=1, padx=2)
        
        # Quick action buttons - Row 1
        ttk.Button(button_frame2, text="Gain +", command=self.increase_gain).grid(row=0, column=0, padx=2)
        ttk.Button(button_frame2, text="Gain -", command=self.decrease_gain).grid(row=0, column=1, padx=2)
        ttk.Button(button_frame2, text="Rotate Left", command=self.rotate_left).grid(row=0, column=2, padx=2)
        ttk.Button(button_frame2, text="Rotate Right", command=self.rotate_right).grid(row=0, column=3, padx=2)
        
        # Quick action buttons - Row 2 (Zoom controls)
        ttk.Button(button_frame2, text="Zoom In", command=self.zoom_in).grid(row=1, column=0, padx=2, pady=(5,0))
        ttk.Button(button_frame2, text="Zoom Out", command=self.zoom_out).grid(row=1, column=1, padx=2, pady=(5,0))
        ttk.Button(button_frame2, text="Zoom Reset", command=self.zoom_reset).grid(row=1, column=2, padx=2, pady=(5,0))
        
        # Template selection
        ttk.Label(template_frame, text="Load Template:").grid(row=0, column=0, sticky=tk.W, padx=2)
        
        # Get available template
        available_templates = self.get_available_templates()
        
        # Create combobox for template selection
        self.template_var = tk.StringVar()
        self.template_combo = ttk.Combobox(template_frame, textvariable=self.template_var, values=available_templates)
        self.template_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=2)
        
        # Load button
        ttk.Button(template_frame, text="Load", command=self.load_selected_template).grid(row=0, column=2, padx=2)
        
        # Refresh button
        ttk.Button(template_frame, text="Refresh List", command=self.refresh_template_list).grid(row=0, column=3, padx=2)
        
    def create_status_section(self, parent=None):
        """Create status display section"""
        # Use provided parent or default to main_frame
        parent = parent or self.main_frame
        
        # Status frame
        status_frame = ttk.LabelFrame(parent, text="Current Parameters & Status", padding="10")
        status_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=2)
        
        # Make sure the status section expands vertically
        parent.rowconfigure(3, weight=1)
        status_frame.columnconfigure(0, weight=1)
        status_frame.rowconfigure(1, weight=1)
        
        # Status label
        self.status_var = tk.StringVar(value="Status: Ready - GUI Initialized")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var)
        self.status_label.grid(row=0, column=0, sticky=tk.W, pady=2)
        
        # Parameters text area
        self.params_text = tk.Text(status_frame, height=8, width=80, wrap=tk.WORD)
        self.params_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=2)
        
        # Scrollbar for text area
        scrollbar = ttk.Scrollbar(status_frame, orient=tk.VERTICAL, command=self.params_text.yview)
        scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        self.params_text.configure(yscrollcommand=scrollbar.set)
        
        # Update initial parameter display
        self.update_parameter_display()
        
    # Callback methods for GUI controls
    def update_position(self, event=None):
        """Update position parameters and regenerate bookmark"""
        try:
            x = self.x_var.get()
            y = self.y_var.get()
            z = self.z_var.get()
            
            # Update labels
            self.x_label.config(text=f"{x:.1f}")
            self.y_label.config(text=f"{y:.1f}")
            self.z_label.config(text=f"{z:.1f}")
            
            self.engine.change_slices_position(x, y, z)
            self.engine.update_params()
            self.current_params = self.engine.curr_params
            self.update_status(f"Updated position: X={x:.1f}, Y={y:.1f}, Z={z:.1f}")
            self.update_parameter_display()
            
        except Exception as e:
            self.update_status(f"Error updating position: {e}")
    
    def update_orientation(self, event=None):
        """Update orientation parameters and regenerate bookmark"""
        try:
            rot1 = self.rot1_var.get()
            rot2 = self.rot2_var.get()
            rot3 = self.rot3_var.get()
            
            # Update labels
            self.rot1_label.config(text=f"{rot1:.2f} rad")
            self.rot2_label.config(text=f"{rot2:.2f} rad")
            self.rot3_label.config(text=f"{rot3:.2f} rad")
            
            self.engine.adjust_orientation(rot1, rot2, rot3)
            self.engine.update_params()
            self.current_params = self.engine.curr_params
            self.update_status(f"Updated orientation: {rot1:.2f}, {rot2:.2f}, {rot3:.2f} rad")
            self.update_parameter_display()
            
        except Exception as e:
            self.update_status(f"Error updating orientation: {e}")
    
    def update_scale(self, event=None):
        """Update scale parameters and regenerate bookmark"""
        try:
            scale_x = self.scale_x_var.get()
            scale_y = self.scale_y_var.get()
            
            # Update labels
            self.scale_x_label.config(text=f"{scale_x:.2f}")
            self.scale_y_label.config(text=f"{scale_y:.2f}")
            
            self.engine.adjust_zoom(scale_x=scale_x, scale_y=scale_y)
            self.engine.update_params()
            self.current_params = self.engine.curr_params
            self.update_status(f"Updated scale: X={scale_x:.2f}, Y={scale_y:.2f}")
            self.update_parameter_display()
            
        except Exception as e:
            self.update_status(f"Error updating scale: {e}")
    
    def update_shift(self, event=None):
        """Update shift parameters and regenerate bookmark"""
        try:
            shift_x = self.shift_x_var.get()
            shift_y = self.shift_y_var.get()
            shift_z = self.shift_z_var.get()
            
            # Update labels
            self.shift_x_label.config(text=f"{shift_x:.1f}")
            self.shift_y_label.config(text=f"{shift_y:.1f}")
            self.shift_z_label.config(text=f"{shift_z:.1f}")
            
            # Use the new adjust_shift method instead of directly setting curr_params.shift
            self.engine.adjust_shift(shift_x, shift_y, shift_z)
            self.engine.update_params()
            self.current_params = self.engine.curr_params
            self.update_status(f"Updated shift: X={shift_x:.1f}, Y={shift_y:.1f}, Z={shift_z:.1f}")
            self.update_parameter_display()
            
        except Exception as e:
            self.update_status(f"Error updating shift: {e}")
    
    def update_visibility(self):
        """Update data visibility and regenerate bookmark"""
        try:
            # Update seismic visibility
            seismic_visible = self.seismic_var.get()
            self.engine.toggle_data_visibility('seismic', seismic_visible)
            
            # Update attribute visibility
            attribute_visible = self.attribute_var.get()
            self.engine.toggle_data_visibility('attribute', attribute_visible)
            
            # Update horizon visibility
            horizon_visible = self.horizon_var.get()
            self.engine.toggle_data_visibility('horizon', horizon_visible)
            
            # Update well visibility
            well_visible = self.well_var.get()
            self.engine.toggle_data_visibility('well', well_visible)
            
            self.engine.update_params()
            self.current_params = self.engine.curr_params
            self.update_status("Updated data visibility settings")
            self.update_parameter_display()
            
        except Exception as e:
            self.update_status(f"Error updating visibility: {e}")
    
    def update_slice_visibility(self):
        """Update slice visibility and regenerate bookmark"""
        try:
            # Update X slice visibility
            x_visible = self.x_slice_var.get()
            self.engine.toggle_slice_visibility('x', x_visible)
            
            # Update Y slice visibility
            y_visible = self.y_slice_var.get()
            self.engine.toggle_slice_visibility('y', y_visible)
            
            # Update Z slice visibility
            z_visible = self.z_slice_var.get()
            self.engine.toggle_slice_visibility('z', z_visible)
            
            self.engine.update_params()
            self.current_params = self.engine.curr_params
            self.update_status("Updated slice visibility settings")
            self.update_parameter_display()
            
        except Exception as e:
            self.update_status(f"Error updating slice visibility: {e}")
    
    def update_gain(self, event=None):
        """Update gain range and regenerate bookmark"""
        try:
            gain = self.gain_var.get()
            
            # Update labels
            self.gain_label.config(text=f"{gain:.1f}")
            
            # Use the new adjust_gain method with a single parameter
            self.engine.adjust_gain(gain)
            self.engine.update_params()
            self.current_params = self.engine.curr_params
            self.update_status(f"Updated gain: {gain:.1f}")
            self.update_parameter_display()
            
        except Exception as e:
            self.update_status(f"Error updating gain: {e}")
    
    def update_colormap(self, event=None):
        """Update colormap index and regenerate bookmark"""
        try:
            colormap_index = int(self.colormap_var.get())
            
            # Update label
            self.colormap_label.config(text=f"{colormap_index}")
            
            self.engine.change_colormap(colormap_index)
            self.engine.update_params()
            self.current_params = self.engine.curr_params
            self.update_status(f"Updated colormap index: {colormap_index}")
            self.update_parameter_display()
            
        except Exception as e:
            self.update_status(f"Error updating colormap: {e}")
    
    def update_color_scale(self, event=None):
        """Update color scale times and regenerate bookmark"""
        try:
            times_value = int(self.times_var.get())
            
            # Update label
            self.times_label.config(text=f"{times_value}")
            
            self.engine.adjust_color_scale(times_value)
            self.engine.update_params()
            self.current_params = self.engine.curr_params
            self.update_status(f"Updated color scale times: {times_value}")
            self.update_parameter_display()
            
        except Exception as e:
            self.update_status(f"Error updating color scale: {e}")   
 
    # Button callback methods
    def reset_parameters(self):
        """Reset all parameters to template defaults"""
        try:
            self.engine.curr_params = copy.deepcopy(self.engine.default_params)
            self.current_params = self.engine.curr_params # same object essentially throughout the script, but just in case
            self.engine.update_params()
            
            # Update all GUI controls to default values
            self.x_var.set(self.current_params.x_position)
            self.y_var.set(self.current_params.y_position)
            self.z_var.set(self.current_params.z_position)
            
            orient = self.current_params.orient or (0, 0, 0)
            self.rot1_var.set(orient[0])
            self.rot2_var.set(orient[1] if len(orient) > 1 else 0)
            self.rot3_var.set(orient[2] if len(orient) > 2 else 0)
            
            scale = self.current_params.scale or (1.0, 1.0)
            self.scale_x_var.set(scale[0])
            self.scale_y_var.set(scale[1] if len(scale) > 1 else scale[0])
            
            shift = self.current_params.shift or (0, 0, 0)
            self.shift_x_var.set(shift[0])
            self.shift_y_var.set(shift[1] if len(shift) > 1 else 0)
            self.shift_z_var.set(shift[2] if len(shift) > 2 else 0)
            
            # Calculate gain value based on seismic range
            default_min, default_max = self.engine.default_params.seismic_range
            default_range = default_max - default_min
            current_min, current_max = self.current_params.seismic_range
            current_range = current_max - current_min
            
            if current_range != 0:
                gain_value = default_range / current_range
            else:
                gain_value = 1.0
                
            self.gain_var.set(gain_value)
            self.colormap_var.set(self.current_params.seismic_colormap_index or 3)
            self.times_var.set(self.current_params.seismic_times or 1)
            
            # Update visibility checkboxes
            self.seismic_var.set(self.current_params.seismic_visible)
            self.attribute_var.set(self.current_params.attribute_visible)
            self.horizon_var.set(self.current_params.horizon_visible)
            self.well_var.set(self.current_params.well_visible)
            self.x_slice_var.set(self.current_params.x_visible)
            self.y_slice_var.set(self.current_params.y_visible)
            self.z_slice_var.set(self.current_params.z_visible)
            
            # Update all labels to match the new values
            self.update_all_labels()
            
            self.update_status("Reset all parameters to template defaults")
            self.update_parameter_display()
            
        except Exception as e:
            self.update_status(f"Error resetting parameters: {e}")
            messagebox.showerror("Error", f"Error resetting parameters: {e}")
    
    def reload_template(self):
        """Reload the bookmark template"""
        try:
            self.engine.load_template("default_bookmark.html")
            self.current_params = self.engine.curr_params
            
            # Call reset_parameters to update all GUI controls and labels
            self.reset_parameters()
            
            self.update_status("Reloaded bookmark template")
            messagebox.showinfo("Success", "Template reloaded successfully")
            
        except Exception as e:
            self.update_status(f"Error reloading template: {e}")
            messagebox.showerror("Error", f"Error reloading template: {e}")
    
    def increase_gain(self):
        """Increase gain using engine function"""
        try:
            # Get current gain value (approximate from seismic range)
            current_min, current_max = self.current_params.seismic_range
            current_range = current_max - current_min
            default_min, default_max = self.engine.default_params.seismic_range
            default_range = default_max - default_min
            
            # Estimate current gain value
            if current_range != 0:
                current_gain = default_range / current_range
            else:
                current_gain = 1.0
            
            # Increase gain by 20% (makes range narrower, contrast higher)
            new_gain = current_gain * 1.2
            
            # Apply new gain
            self.engine.adjust_gain(new_gain)
            self.engine.update_params()
            self.current_params = self.engine.curr_params
            self.update_status(f"Increased gain (value: {new_gain:.1f})")
            self.update_parameter_display()
            
            # Update slider if it exists
            if hasattr(self, 'gain_var'):
                self.gain_var.set(new_gain)
                self.gain_label.config(text=f"{new_gain:.1f}")
            
        except Exception as e:
            self.update_status(f"Error increasing gain: {e}")
    
    def decrease_gain(self):
        """Decrease gain using engine function"""
        try:
            # Get current gain value (approximate from seismic range)
            current_min, current_max = self.current_params.seismic_range
            current_range = current_max - current_min
            default_min, default_max = self.engine.default_params.seismic_range
            default_range = default_max - default_min
            
            # Estimate current gain value
            if current_range != 0:
                current_gain = default_range / current_range
            else:
                current_gain = 1.0
            
            # Decrease gain by 20% (makes range wider, contrast lower)
            new_gain = current_gain * 0.8
            
            # Apply new gain
            self.engine.adjust_gain(new_gain)
            self.engine.update_params()
            self.current_params = self.engine.curr_params
            self.update_status(f"Decreased gain (value: {new_gain:.1f})")
            self.update_parameter_display()
            
            # Update slider if it exists
            if hasattr(self, 'gain_var'):
                self.gain_var.set(new_gain)
                self.gain_label.config(text=f"{new_gain:.1f}")
            
        except Exception as e:
            self.update_status(f"Error decreasing gain: {e}")
    
    def rotate_left(self):
        """Rotate view left by adjusting Z-axis rotation"""
        try:
            current_rot3 = self.rot3_var.get()
            new_rot3 = current_rot3 - 0.1  # Rotate left by 0.1 radians
            
            # Keep within bounds
            if new_rot3 < -3.14159:
                new_rot3 = 3.14159
            
            self.rot3_var.set(new_rot3)
            self.update_orientation()
            self.update_status("Rotated left")
            
        except Exception as e:
            self.update_status(f"Error rotating left: {e}")
    
    def rotate_right(self):
        """Rotate view right by adjusting Z-axis rotation"""
        try:
            current_rot3 = self.rot3_var.get()
            new_rot3 = current_rot3 + 0.1  # Rotate right by 0.1 radians
            
            # Keep within bounds
            if new_rot3 > 3.14159:
                new_rot3 = -3.14159
            
            self.rot3_var.set(new_rot3)
            self.update_orientation()
            self.update_status("Rotated right")
            
        except Exception as e:
            self.update_status(f"Error rotating right: {e}")
    
    def zoom_in(self):
        """Zoom in by increasing scale values"""
        try:
            current_scale_x = self.scale_x_var.get()
            current_scale_y = self.scale_y_var.get()
            
            # Increase scale by 10%
            new_scale_x = min(3.0, current_scale_x * 1.1)
            new_scale_y = min(3.0, current_scale_y * 1.1)
            
            self.scale_x_var.set(new_scale_x)
            self.scale_y_var.set(new_scale_y)
            self.update_scale()
            self.update_status("Zoomed in")
            
        except Exception as e:
            self.update_status(f"Error zooming in: {e}")
            
    def zoom_out(self):
        """Zoom out by decreasing scale values"""
        try:
            current_scale_x = self.scale_x_var.get()
            current_scale_y = self.scale_y_var.get()
            
            # Decrease scale by 10%
            new_scale_x = max(0.1, current_scale_x * 0.9)
            new_scale_y = max(0.1, current_scale_y * 0.9)
            
            self.scale_x_var.set(new_scale_x)
            self.scale_y_var.set(new_scale_y)
            self.update_scale()
            self.update_status("Zoomed out")
            
        except Exception as e:
            self.update_status(f"Error zooming out: {e}")
            
    def zoom_reset(self):
        """Reset zoom to default scale values from the original bookmark"""
        try:
            # Get default scale values from the engine
            if hasattr(self.engine, 'default_params') and self.engine.default_params:
                default_scale_x, default_scale_y = self.engine.default_params.scale
            else:
                # Fallback to 1.0 if default scale is not available
                default_scale_x, default_scale_y = 1.0, 1.0
            
            # Set to default scale values
            self.scale_x_var.set(default_scale_x)
            self.scale_y_var.set(default_scale_y)
            
            # Update labels
            self.update_scale_x_label(default_scale_x)
            self.update_scale_y_label(default_scale_y)
            
            self.update_scale()
            self.update_status(f"Zoom reset to default ({default_scale_x:.2f}, {default_scale_y:.2f})")
            
        except Exception as e:
            self.update_status(f"Error resetting zoom: {e}")
            
    def get_available_templates(self):
        """Get a list of available bookmark files in the bookmarks directory"""
        try:
            template_dir = self.engine.templates_dir
            template_files = [f.name for f in template_dir.glob("*.html") if f.is_file() and f.name != "TEMP_BKM.html"]
            return sorted(template_files)
        except Exception as e:
            self.update_status(f"Error listing templates: {e}")
            return []
            
    def load_template_by_name(self, template_name):
        """Load a template by its filename"""
        try:
            if not template_name.endswith('.html'):
                template_name += '.html'
                
            template_path = self.engine.templates_dir / template_name
            
            if not template_path.exists():
                self.update_status(f"Template file not found: {template_name}")
                messagebox.showerror("Error", f"Template file not found: {template_name}")
                return False
                
            # Load the bookmark template
            self.engine.load_template(template_name)
            self.current_params = self.engine.curr_params
            
            # Update all GUI controls and labels
            self.reset_parameters()
            
            self.update_status(f"Loaded Template: {template_name}")
            return True
            
        except Exception as e:
            self.update_status(f"Error loading template: {e}")
            messagebox.showerror("Error", f"Error loading template: {e}")
            return False
            
    def load_selected_template(self):
        """Load the bookmark template selected in the combobox"""
        template_name = self.template_var.get()
        if not template_name:
            self.update_status("No template selected")
            return
            
        self.load_template_by_name(template_name)
        
    def refresh_template_list(self):
        """Refresh the list of available templates"""
        try:
            available_templates = self.get_available_templates()
            self.template_combo['values'] = available_templates
            self.update_status("Template list refreshed")
        except Exception as e:
            self.update_status(f"Error refreshing template list: {e}")
    
    # Helper methods
    def update_status(self, message: str):
        """Update status display"""
        self.status_var.set(f"Status: {message}")
    
    def update_parameter_display(self):
        """Update parameter display"""
        try:
            # Read the XML content directly from the file
            import xml.etree.ElementTree as ET
            
            # Check if the file exists
            if not self.engine.temp_bkm_path.exists():
                self.params_text.delete(1.0, tk.END)
                self.params_text.insert(1.0, "Error: TEMP_BKM.html file not found.")
                return
                
            # Read the file content
            try:
                with open(self.engine.temp_bkm_path, 'r', encoding='utf-8') as f:
                    xml_content = f.read()
            except Exception as e:
                self.params_text.delete(1.0, tk.END)
                self.params_text.insert(1.0, f"Error reading file: {e}")
                return
            
            # Parse the XML content
            try:
                root = ET.fromstring(xml_content)
                snapshot = root.find('SNAPSHOT')
                if snapshot is None:
                    self.params_text.delete(1.0, tk.END)
                    self.params_text.insert(1.0, "Error: No SNAPSHOT element found in the XML.")
                    return
            except ET.ParseError as e:
                self.params_text.delete(1.0, tk.END)
                self.params_text.insert(1.0, f"Error parsing XML: {e}")
                return
            
            # Extract key parameters
            x_pos = snapshot.find('X/POSITION')
            y_pos = snapshot.find('Y/POSITION')
            z_pos = snapshot.find('Z/POSITION')
            orient = snapshot.find('ORIENT')
            scale = snapshot.find('SCALE')
            shift = snapshot.find('SHIFT')
            seismic_vis = snapshot.find('SEISMIC_VISIBILITY')
            gain_range = snapshot.find('SEISMIC_COLORMAP/SPECTRUM/RANGE')
            
            params = []
            if x_pos is not None:
                params.append(f"X (Crossline): {x_pos.text}")
            if y_pos is not None:
                params.append(f"Y (Inline): {y_pos.text}")
            if z_pos is not None:
                params.append(f"Z (Depth): {z_pos.text}")
            if orient is not None:
                params.append(f"Orient: {orient.text}")
            if scale is not None:
                params.append(f"Scale, T: {scale.text}")
            if shift is not None:
                params.append(f"Shift: {shift.text}")
            if seismic_vis is not None:
                params.append(f"Seismic Vis: {seismic_vis.text}")
            if gain_range is not None:
                params.append(f"Gain Range: {gain_range.text}")
            
            param_text = "Current Parameters:\n" + "\n".join(params)
            
            # Update text widget
            self.params_text.delete(1.0, tk.END)
            self.params_text.insert(1.0, param_text)
            
        except Exception as e:
            error_text = f"Error reading parameters: {e}"
            self.params_text.delete(1.0, tk.END)
            self.params_text.insert(1.0, error_text)
            self.update_status(error_text)
            self.params_text.delete(1.0, tk.END)
            self.params_text.insert(1.0, error_text)
    
    def update_x_label(self, value):
        self.x_label.config(text=f"{float(value):.1f}")
    def update_y_label(self, value):
        self.y_label.config(text=f"{float(value):.1f}")
    def update_z_label(self, value):
        self.z_label.config(text=f"{float(value):.1f}")
    def update_rot1_label(self, value):
        self.rot1_label.config(text=f"{float(value):.2f} rad")
    def update_rot2_label(self, value):
        self.rot2_label.config(text=f"{float(value):.2f} rad")
    def update_rot3_label(self, value):
        self.rot3_label.config(text=f"{float(value):.2f} rad")
    def update_scale_x_label(self, value):
        self.scale_x_label.config(text=f"{float(value):.2f}")
    def update_scale_y_label(self, value):
        self.scale_y_label.config(text=f"{float(value):.2f}")
    def update_shift_x_label(self, value):
        """Update the shift X label when slider moves"""
        self.shift_x_label.config(text=f"{float(value):.1f}")
        
    def update_shift_y_label(self, value):
        """Update the shift Y label when slider moves"""
        self.shift_y_label.config(text=f"{float(value):.1f}")
        
    def update_shift_z_label(self, value):
        """Update the shift Z label when slider moves"""
        self.shift_z_label.config(text=f"{float(value):.1f}")
        

    def update_gain_label(self, value):
        self.gain_label.config(text=f"{float(value):.1f}")
    def update_colormap_label(self, value):
        self.colormap_label.config(text=f"{int(float(value))}")
    def update_times_label(self, value):
        self.times_label.config(text=f"{int(float(value))}")
        
    def update_all_labels(self):
        """Update all labels to match the current slider values"""
        # Position labels
        self.update_x_label(self.x_var.get())
        self.update_y_label(self.y_var.get())
        self.update_z_label(self.z_var.get())
        
        # Orientation labels
        self.update_rot1_label(self.rot1_var.get())
        self.update_rot2_label(self.rot2_var.get())
        self.update_rot3_label(self.rot3_var.get())
        
        # Scale labels
        self.update_scale_x_label(self.scale_x_var.get())
        self.update_scale_y_label(self.scale_y_var.get())
        
        # Shift labels
        self.update_shift_x_label(self.shift_x_var.get())
        self.update_shift_y_label(self.shift_y_var.get())
        self.update_shift_z_label(self.shift_z_var.get())
        
        # Display adjustment labels
        self.update_gain_label(self.gain_var.get())
        self.update_colormap_label(self.colormap_var.get())
        self.update_times_label(self.times_var.get())
    
    def run(self):
        """Start the GUI main loop"""
        self.root.mainloop()


def main():
    """Main function to run the Tkinter GUI"""

    

    try:
        print("Starting Seismic Bookmark Parameter Control GUI - Tkinter Version...")
        print("This GUI allows real-time manipulation of bookmark parameters")
        print("All changes are automatically saved to tests/gui_output/current_bookmark.html")
        print("Use the 'Save Bookmark' button to save timestamped versions")
        print("\nFeatures:")
        print("- Clean Tkinter interface with proper layout")
        print("- Position sliders for crossline, inline, depth")
        print("- Orientation controls for 3-axis rotation")
        print("- Scale and shift adjustments")
        print("- Data visibility toggles")
        print("- Gain and colormap controls")
        print("- Quick action buttons")
        
        # Create and run GUI
        gui = BookmarkGUITkinter()
        gui.run()
        
    except Exception as e:
        print(f"Error starting GUI: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()