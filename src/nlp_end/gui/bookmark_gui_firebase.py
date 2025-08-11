#!/usr/bin/env python3
"""
Firebase-based Interactive GUI for distributed bookmark manipulation

This module provides a Tkinter-based GUI that sends JSON-RPC commands through Firebase
instead of directly calling the bookmark engine. This creates a distributed system where:
- GUI sends commands to Firebase queue
- tornado_listener.py processes commands and updates HTML
- Multiple GUIs can control the same Tornado instance

Key Changes from tornadoless version:
- No direct bookmark engine integration
- Sends JSON-RPC commands via Firebase
- Real-time status monitoring
- Command queue feedback
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sys
import json
import threading
import time
from pathlib import Path
from typing import Optional

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

# Setup Windows virtual environment for LLM dependencies
try:
    from shared.utils.venv_setup import ensure_windows_venv
    ensure_windows_venv()
except ImportError as e:
    print(f"Warning: Failed to setup Windows virtual environment: {e}")
    # Continue anyway for development/testing

from shared.database.database_config import DatabaseConfig
from shared.database.command_queue_manager import CommandQueueManager


class BookmarkGUIFirebase:
    """Firebase-based GUI for distributed bookmark parameter manipulation"""
    
    def __init__(self):
        # Firebase setup
        self.firebase_config = None
        self.queue_manager = None
        self.connected = False
        
        # GUI state tracking
        self.current_params = {
            'x_position': 160112.5,
            'y_position': 112487.5,
            'z_position': 3500.0,
            'orient': (0.0, 0.39269908169872414, -0.7853981633974483),
            'shift': (-1122.499999999998, 521.3388347648317, -1601.125),
            'scale': (0.7511687840078737, 0.7511687840078737),
            'seismic_visible': True,
            'attribute_visible': False,
            'horizon_visible': False,
            'well_visible': True,
            'x_visible': True,
            'y_visible': True,
            'z_visible': False,
            'seismic_range': (-197331.0, 187430.0),
            'seismic_colormap_index': 3,
            'seismic_times': 1
        }
        
        # Initialize Firebase connection
        self.initialize_firebase()
        
        # Initialize GUI
        self.setup_gui()
        
        # Start status monitoring thread
        self.start_status_monitor()
        
    def initialize_firebase(self) -> bool:
        """Initialize Firebase connection"""
        try:
            print("Initializing Firebase connection...")
            self.firebase_config = FirebaseConfig()
            
            if not self.firebase_config.initialize_firebase():
                print("❌ Failed to initialize Firebase")
                return False
                
            self.queue_manager = CommandQueueManager(self.firebase_config)
            self.connected = True
            print("✅ Firebase connection established")
            return True
            
        except Exception as e:
            print(f"❌ Error initializing Firebase: {e}")
            self.connected = False
            return False
    
    def send_command(self, method: str, params: dict, wait_for_response: bool = False) -> bool:
        """
        Send JSON-RPC command to Firebase queue
        
        Args:
            method: Command method name
            params: Command parameters
            wait_for_response: Whether to wait for and return response
            
        Returns:
            bool: True if command sent successfully
        """
        if not self.connected:
            self.update_status("❌ Not connected to Firebase")
            return False
            
        try:
            command_data = {
                'method': method,
                'params': params
            }
            
            command_id = self.queue_manager.add_command(command_data)
            if command_id:
                self.update_status(f"✅ Command sent: {method}")
                print(f"📤 Sent command: {method} with params: {params}")
                
                # Optionally wait for response
                if wait_for_response:
                    response = self.wait_for_command_result(command_id)
                    return response
                    
                return True
            else:
                self.update_status(f"❌ Failed to send: {method}")
                return False
                
        except Exception as e:
            self.update_status(f"❌ Error sending command: {e}")
            print(f"Error sending command: {e}")
            return False
    
    def wait_for_command_result(self, command_id: str, timeout: int = 10) -> dict:
        """
        Wait for command result from Firebase
        
        Args:
            command_id: Command ID to wait for
            timeout: Timeout in seconds
            
        Returns:
            dict: Command result or None if timeout
        """
        import time
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Check command status in Firebase
                command_ref = self.firebase_config.db.collection('command_queues').document(self.queue_manager.user_id).collection('commands').document(command_id)
                command_doc = command_ref.get()
                
                if command_doc.exists:
                    command_data = command_doc.to_dict()
                    if command_data.get('status') == 'executed':
                        return command_data.get('result', {})
                    elif command_data.get('status') == 'failed':
                        return {'error': command_data.get('error', 'Unknown error')}
                
                time.sleep(0.5)  # Poll every 500ms
                
            except Exception as e:
                print(f"Error waiting for result: {e}")
                break
        
        return {'error': 'Timeout waiting for response'}
    
    def setup_gui(self):
        """Set up the Tkinter GUI with proper layout management"""
        # Create main window
        self.root = tk.Tk()
        self.root.title('Seismic Navigation - Firebase Distributed GUI')
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
        self.left_panel.rowconfigure(0, weight=1)
        self.left_panel.rowconfigure(1, weight=1)
        self.left_panel.rowconfigure(2, weight=1)
        
        self.right_panel.rowconfigure(0, weight=0)
        self.right_panel.rowconfigure(1, weight=0)
        self.right_panel.rowconfigure(2, weight=0)
        self.right_panel.rowconfigure(3, weight=3)
        
        # Create sections
        self.create_position_section(self.left_panel)
        self.create_orientation_section(self.left_panel)
        self.create_view_section(self.left_panel)
        
        self.create_visibility_section(self.right_panel)
        self.create_display_section(self.right_panel)
        self.create_action_section(self.right_panel)
        self.create_status_section(self.right_panel)
        
    def create_position_section(self, parent):
        """Create position controls section"""
        pos_frame = ttk.LabelFrame(parent, text="Position Controls (Crossline/Inline/Depth)", padding="10")
        pos_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=2)
        pos_frame.columnconfigure(1, weight=1)
        
        # X Position (Crossline)
        ttk.Label(pos_frame, text="X (Crossline):").grid(row=0, column=0, sticky=tk.W, padx=2)
        self.x_var = tk.DoubleVar(value=self.current_params['x_position'])
        self.x_scale = ttk.Scale(pos_frame, from_=100000, to=200000, variable=self.x_var, 
                                orient=tk.HORIZONTAL, command=self.update_x_label)
        self.x_scale.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=2)
        self.x_label = ttk.Label(pos_frame, text=f"{self.current_params['x_position']:.1f}")
        self.x_label.grid(row=0, column=2, padx=2)
        
        # Y Position (Inline)
        ttk.Label(pos_frame, text="Y (Inline):").grid(row=1, column=0, sticky=tk.W, padx=2, pady=2)
        self.y_var = tk.DoubleVar(value=self.current_params['y_position'])
        self.y_scale = ttk.Scale(pos_frame, from_=100000, to=150000, variable=self.y_var,
                                orient=tk.HORIZONTAL, command=self.update_y_label)
        self.y_scale.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=2, pady=2)
        self.y_label = ttk.Label(pos_frame, text=f"{self.current_params['y_position']:.1f}")
        self.y_label.grid(row=1, column=2, padx=2, pady=2)
        
        # Z Position (Depth)
        ttk.Label(pos_frame, text="Z (Depth):").grid(row=2, column=0, sticky=tk.W, padx=2)
        self.z_var = tk.DoubleVar(value=self.current_params['z_position'])
        self.z_scale = ttk.Scale(pos_frame, from_=1000, to=6000, variable=self.z_var,
                                orient=tk.HORIZONTAL, command=self.update_z_label)
        self.z_scale.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=2)
        self.z_label = ttk.Label(pos_frame, text=f"{self.current_params['z_position']:.1f}")
        self.z_label.grid(row=2, column=2, padx=2)

        # Bind sliders to send commands
        self.x_scale.bind("<ButtonRelease-1>", self.update_position)
        self.y_scale.bind("<ButtonRelease-1>", self.update_position)
        self.z_scale.bind("<ButtonRelease-1>", self.update_position)
        
    def create_orientation_section(self, parent):
        """Create orientation controls section"""
        orient_frame = ttk.LabelFrame(parent, text="Orientation Controls (Rotation Angles)", padding="10")
        orient_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=2)
        orient_frame.columnconfigure(1, weight=1)
        
        orient = self.current_params['orient']
        
        # Rotation 1
        ttk.Label(orient_frame, text="Rot1 (Fixed):").grid(row=0, column=0, sticky=tk.W, padx=2)
        self.rot1_var = tk.DoubleVar(value=orient[0])
        self.rot1_scale = ttk.Scale(orient_frame, from_=-3.14159, to=3.14159, variable=self.rot1_var,
                                   orient=tk.HORIZONTAL, command=self.update_rot1_label)
        self.rot1_scale.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=2)
        self.rot1_label = ttk.Label(orient_frame, text=f"{orient[0]:.2f} rad")
        self.rot1_label.grid(row=0, column=2, padx=2)
        
        # Rotation 2
        ttk.Label(orient_frame, text="Rot2 (Perp):").grid(row=1, column=0, sticky=tk.W, padx=2, pady=2)
        self.rot2_var = tk.DoubleVar(value=orient[1])
        self.rot2_scale = ttk.Scale(orient_frame, from_=-3.14159, to=3.14159, variable=self.rot2_var,
                                   orient=tk.HORIZONTAL, command=self.update_rot2_label)
        self.rot2_scale.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=2, pady=2)
        self.rot2_label = ttk.Label(orient_frame, text=f"{orient[1]:.2f} rad")
        self.rot2_label.grid(row=1, column=2, padx=2, pady=2)
        
        # Rotation 3
        ttk.Label(orient_frame, text="Rot3 (Z-axis):").grid(row=2, column=0, sticky=tk.W, padx=2)
        self.rot3_var = tk.DoubleVar(value=orient[2])
        self.rot3_scale = ttk.Scale(orient_frame, from_=-3.14159, to=3.14159, variable=self.rot3_var,
                                   orient=tk.HORIZONTAL, command=self.update_rot3_label)
        self.rot3_scale.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=2)
        self.rot3_label = ttk.Label(orient_frame, text=f"{orient[2]:.2f} rad")
        self.rot3_label.grid(row=2, column=2, padx=2)

        # Bind sliders to send commands
        self.rot1_scale.bind("<ButtonRelease-1>", self.update_orientation)
        self.rot2_scale.bind("<ButtonRelease-1>", self.update_orientation)
        self.rot3_scale.bind("<ButtonRelease-1>", self.update_orientation)
        
    def create_view_section(self, parent):
        """Create view controls section"""
        view_frame = ttk.LabelFrame(parent, text="View Controls", padding="10")
        view_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=2)
        
        self.create_scale_section(view_frame)
        self.create_shift_section(view_frame)
        
    def create_scale_section(self, parent_frame):
        """Create scale controls section"""
        scale_frame = ttk.LabelFrame(parent_frame, text="Scale/Zoom Controls", padding="10")
        scale_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=2, padx=2)
        scale_frame.columnconfigure(1, weight=1)
        
        scale = self.current_params['scale']
        
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
        self.scale_y_var = tk.DoubleVar(value=scale[1])
        self.scale_y_scale = ttk.Scale(scale_frame, from_=0.1, to=3.0, variable=self.scale_y_var,
                                      orient=tk.HORIZONTAL, command=self.update_scale_y_label)
        self.scale_y_scale.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=2, pady=2)
        self.scale_y_label = ttk.Label(scale_frame, text=f"{scale[1]:.2f}")
        self.scale_y_label.grid(row=1, column=2, padx=2, pady=2)
        
        # Bind sliders
        self.scale_x_scale.bind("<ButtonRelease-1>", self.update_scale)
        self.scale_y_scale.bind("<ButtonRelease-1>", self.update_scale)
        
    def create_shift_section(self, parent_frame):
        """Create shift controls section"""
        shift_frame = ttk.LabelFrame(parent_frame, text="Shift Controls", padding="10")
        shift_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=2, padx=2)
        shift_frame.columnconfigure(1, weight=1)
        
        shift = self.current_params['shift']
        
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
        self.shift_y_var = tk.DoubleVar(value=shift[1])
        self.shift_y_scale = ttk.Scale(shift_frame, from_=-5000, to=5000, variable=self.shift_y_var,
                                      orient=tk.HORIZONTAL, command=self.update_shift_y_label)
        self.shift_y_scale.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=2, pady=2)
        self.shift_y_label = ttk.Label(shift_frame, text=f"{shift[1]:.1f}")
        self.shift_y_label.grid(row=1, column=2, padx=2, pady=2)
        
        # Shift Z
        ttk.Label(shift_frame, text="Shift Z:").grid(row=2, column=0, sticky=tk.W, padx=2)
        self.shift_z_var = tk.DoubleVar(value=shift[2])
        self.shift_z_scale = ttk.Scale(shift_frame, from_=-5000, to=5000, variable=self.shift_z_var,
                                      orient=tk.HORIZONTAL, command=self.update_shift_z_label)
        self.shift_z_scale.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=2)
        self.shift_z_label = ttk.Label(shift_frame, text=f"{shift[2]:.1f}")
        self.shift_z_label.grid(row=2, column=2, padx=2)
        
        # Bind sliders
        self.shift_x_scale.bind("<ButtonRelease-1>", self.update_shift)
        self.shift_y_scale.bind("<ButtonRelease-1>", self.update_shift)
        self.shift_z_scale.bind("<ButtonRelease-1>", self.update_shift)
      
    def create_visibility_section(self, parent):
        """Create visibility controls section"""
        vis_frame = ttk.LabelFrame(parent, text="Data Visibility Controls", padding="10")
        vis_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=2)
        
        # Create two columns for checkboxes
        left_frame = ttk.Frame(vis_frame)
        left_frame.grid(row=0, column=0, sticky=(tk.W, tk.N), padx=2)
        right_frame = ttk.Frame(vis_frame)
        right_frame.grid(row=0, column=1, sticky=(tk.W, tk.N), padx=2)
        
        # Data visibility checkboxes
        self.seismic_var = tk.BooleanVar(value=self.current_params['seismic_visible'])
        ttk.Checkbutton(left_frame, text="Seismic", variable=self.seismic_var, 
                       command=self.update_visibility).grid(row=0, column=0, sticky=tk.W, pady=2)
        
        self.attribute_var = tk.BooleanVar(value=self.current_params['attribute_visible'])
        ttk.Checkbutton(left_frame, text="Attributes", variable=self.attribute_var,
                       command=self.update_visibility).grid(row=1, column=0, sticky=tk.W, pady=2)
        
        self.horizon_var = tk.BooleanVar(value=self.current_params['horizon_visible'])
        ttk.Checkbutton(left_frame, text="Horizons", variable=self.horizon_var,
                       command=self.update_visibility).grid(row=2, column=0, sticky=tk.W, pady=2)
        
        self.well_var = tk.BooleanVar(value=self.current_params['well_visible'])
        ttk.Checkbutton(left_frame, text="Wells", variable=self.well_var,
                       command=self.update_visibility).grid(row=3, column=0, sticky=tk.W, pady=2)
        
        # Slice visibility checkboxes
        self.x_slice_var = tk.BooleanVar(value=self.current_params['x_visible'])
        ttk.Checkbutton(right_frame, text="X Slice", variable=self.x_slice_var,
                       command=self.update_slice_visibility).grid(row=0, column=0, sticky=tk.W, pady=2)
        
        self.y_slice_var = tk.BooleanVar(value=self.current_params['y_visible'])
        ttk.Checkbutton(right_frame, text="Y Slice", variable=self.y_slice_var,
                       command=self.update_slice_visibility).grid(row=1, column=0, sticky=tk.W, pady=2)
        
        self.z_slice_var = tk.BooleanVar(value=self.current_params['z_visible'])
        ttk.Checkbutton(right_frame, text="Z Slice", variable=self.z_slice_var,
                       command=self.update_slice_visibility).grid(row=2, column=0, sticky=tk.W, pady=2)
        
    def create_display_section(self, parent):
        """Create display adjustment controls section"""
        display_frame = ttk.LabelFrame(parent, text="Display Adjustment Controls", padding="10")
        display_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=2)
        display_frame.columnconfigure(1, weight=1)
        
        # Gain control
        ttk.Label(display_frame, text="Gain:").grid(row=0, column=0, sticky=tk.W, padx=2)
        self.gain_var = tk.DoubleVar(value=1.0)
        self.gain_scale = ttk.Scale(display_frame, from_=0.1, to=5.0, variable=self.gain_var,
                                   orient=tk.HORIZONTAL, command=self.update_gain_label)
        self.gain_scale.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=2)
        self.gain_label = ttk.Label(display_frame, text="1.0")
        self.gain_label.grid(row=0, column=2, padx=2)
        
        # Colormap Index
        ttk.Label(display_frame, text="Colormap:").grid(row=1, column=0, sticky=tk.W, padx=2, pady=2)
        self.colormap_var = tk.IntVar(value=self.current_params['seismic_colormap_index'])
        self.colormap_scale = ttk.Scale(display_frame, from_=0, to=15, variable=self.colormap_var,
                                       orient=tk.HORIZONTAL, command=self.update_colormap_label)
        self.colormap_scale.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=2, pady=2)
        self.colormap_label = ttk.Label(display_frame, text=f"{self.current_params['seismic_colormap_index']}")
        self.colormap_label.grid(row=1, column=2, padx=2, pady=2)
        
        # Color Scale
        ttk.Label(display_frame, text="Color Scale:").grid(row=2, column=0, sticky=tk.W, padx=2)
        self.times_var = tk.IntVar(value=self.current_params['seismic_times'])
        self.times_scale = ttk.Scale(display_frame, from_=1, to=10, variable=self.times_var,
                                    orient=tk.HORIZONTAL, command=self.update_times_label)
        self.times_scale.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=2)
        self.times_label = ttk.Label(display_frame, text=f"{self.current_params['seismic_times']}")
        self.times_label.grid(row=2, column=2, padx=2)

        # Bind sliders
        self.gain_scale.bind("<ButtonRelease-1>", self.update_gain)
        self.colormap_scale.bind("<ButtonRelease-1>", self.update_colormap)
        self.times_scale.bind("<ButtonRelease-1>", self.update_color_scale)
        
    def create_action_section(self, parent):
        """Create action buttons section"""
        action_frame = ttk.LabelFrame(parent, text="Quick Actions", padding="10")
        action_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=2)
        
        # Create button frames
        button_frame1 = ttk.Frame(action_frame)
        button_frame1.grid(row=0, column=0, sticky=tk.W, padx=2)
        
        button_frame2 = ttk.Frame(action_frame)
        button_frame2.grid(row=1, column=0, sticky=tk.W, padx=2, pady=2)
        
        # Quick action buttons - Row 1
        ttk.Button(button_frame1, text="Gain +", command=self.increase_gain).grid(row=0, column=0, padx=2)
        ttk.Button(button_frame1, text="Gain -", command=self.decrease_gain).grid(row=0, column=1, padx=2)
        ttk.Button(button_frame1, text="Rotate Left", command=self.rotate_left).grid(row=0, column=2, padx=2)
        ttk.Button(button_frame1, text="Rotate Right", command=self.rotate_right).grid(row=0, column=3, padx=2)
        
        # Quick action buttons - Row 2
        ttk.Button(button_frame2, text="Zoom In", command=self.zoom_in).grid(row=0, column=0, padx=2)
        ttk.Button(button_frame2, text="Zoom Out", command=self.zoom_out).grid(row=0, column=1, padx=2)
        ttk.Button(button_frame2, text="Zoom Reset", command=self.zoom_reset).grid(row=0, column=2, padx=2)
        ttk.Button(button_frame2, text="Reset All", command=self.reset_parameters).grid(row=0, column=3, padx=2)
        
        # State management buttons
        button_frame3 = ttk.Frame(action_frame)
        button_frame3.grid(row=2, column=0, sticky=tk.W, padx=2, pady=2)
        
        ttk.Button(button_frame3, text="Undo", command=self.undo_action).grid(row=0, column=0, padx=2)
        ttk.Button(button_frame3, text="Redo", command=self.redo_action).grid(row=0, column=1, padx=2)
        ttk.Button(button_frame3, text="Reload Template", command=self.reload_template).grid(row=0, column=2, padx=2)
        
    def create_status_section(self, parent):
        """Create status display section"""
        status_frame = ttk.LabelFrame(parent, text="Firebase Status & Connection", padding="10")
        status_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=2)
        
        parent.rowconfigure(3, weight=1)
        status_frame.columnconfigure(0, weight=1)
        status_frame.rowconfigure(1, weight=1)
        
        # Connection status
        connection_frame = ttk.Frame(status_frame)
        connection_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=2)
        
        ttk.Label(connection_frame, text="Firebase:").grid(row=0, column=0, sticky=tk.W)
        self.connection_status = ttk.Label(connection_frame, text="✅ Connected" if self.connected else "❌ Disconnected")
        self.connection_status.grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # Status label
        self.status_var = tk.StringVar(value="Status: Ready - Firebase GUI Initialized")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var)
        self.status_label.grid(row=1, column=0, sticky=tk.W, pady=2)
        
        # Command log text area
        self.log_text = tk.Text(status_frame, height=6, width=80, wrap=tk.WORD)
        self.log_text.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=2)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(status_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.grid(row=2, column=1, sticky=(tk.N, tk.S))
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        # Add initial log message
        self.add_log_message("🚀 Firebase GUI initialized")
        if self.connected:
            self.add_log_message("✅ Connected to Firebase - Ready to send commands")
        else:
            self.add_log_message("❌ Firebase connection failed - Check credentials")
    
    # Command sending methods - these replace the direct engine calls
    
    def update_position(self, event=None):
        """Send update_position command via Firebase"""
        x = self.x_var.get()
        y = self.y_var.get()
        z = self.z_var.get()
        
        success = self.send_command('update_position', {
            'x': x, 'y': y, 'z': z
        })
        
        if success:
            self.current_params['x_position'] = x
            self.current_params['y_position'] = y
            self.current_params['z_position'] = z
            self.add_log_message(f"📍 Position: X={x:.1f}, Y={y:.1f}, Z={z:.1f}")
    
    def update_orientation(self, event=None):
        """Send update_orientation command via Firebase"""
        rot1 = self.rot1_var.get()
        rot2 = self.rot2_var.get()
        rot3 = self.rot3_var.get()
        
        success = self.send_command('update_orientation', {
            'rot1': rot1, 'rot2': rot2, 'rot3': rot3
        })
        
        if success:
            self.current_params['orient'] = (rot1, rot2, rot3)
            self.add_log_message(f"🔄 Orientation: {rot1:.2f}, {rot2:.2f}, {rot3:.2f}")
    
    def update_scale(self, event=None):
        """Send update_scale command via Firebase"""
        scale_x = self.scale_x_var.get()
        scale_y = self.scale_y_var.get()
        
        success = self.send_command('update_scale', {
            'scale_x': scale_x, 'scale_y': scale_y
        })
        
        if success:
            self.current_params['scale'] = (scale_x, scale_y)
            self.add_log_message(f"🔍 Scale: X={scale_x:.2f}, Y={scale_y:.2f}")
    
    def update_shift(self, event=None):
        """Send update_shift command via Firebase"""
        shift_x = self.shift_x_var.get()
        shift_y = self.shift_y_var.get()
        shift_z = self.shift_z_var.get()
        
        success = self.send_command('update_shift', {
            'shift_x': shift_x, 'shift_y': shift_y, 'shift_z': shift_z
        })
        
        if success:
            self.current_params['shift'] = (shift_x, shift_y, shift_z)
            self.add_log_message(f"↔️ Shift: X={shift_x:.1f}, Y={shift_y:.1f}, Z={shift_z:.1f}")
    
    def update_visibility(self):
        """Send update_visibility command via Firebase"""
        seismic = self.seismic_var.get()
        attribute = self.attribute_var.get()
        horizon = self.horizon_var.get()
        well = self.well_var.get()
        
        success = self.send_command('update_visibility', {
            'seismic': seismic, 'attribute': attribute, 
            'horizon': horizon, 'well': well
        })
        
        if success:
            self.current_params['seismic_visible'] = seismic
            self.current_params['attribute_visible'] = attribute
            self.current_params['horizon_visible'] = horizon
            self.current_params['well_visible'] = well
            self.add_log_message(f"👁️ Data Visibility: S={seismic}, A={attribute}, H={horizon}, W={well}")
    
    def update_slice_visibility(self):
        """Send update_slice_visibility command via Firebase"""
        x_slice = self.x_slice_var.get()
        y_slice = self.y_slice_var.get()
        z_slice = self.z_slice_var.get()
        
        success = self.send_command('update_slice_visibility', {
            'x_slice': x_slice, 'y_slice': y_slice, 'z_slice': z_slice
        })
        
        if success:
            self.current_params['x_visible'] = x_slice
            self.current_params['y_visible'] = y_slice
            self.current_params['z_visible'] = z_slice
            self.add_log_message(f"🔲 Slice Visibility: X={x_slice}, Y={y_slice}, Z={z_slice}")
    
    def update_gain(self, event=None):
        """Send update_gain command via Firebase"""
        gain_value = self.gain_var.get()
        
        success = self.send_command('update_gain', {
            'gain_value': gain_value
        })
        
        if success:
            self.add_log_message(f"📊 Gain: {gain_value:.1f}")
    
    def update_colormap(self, event=None):
        """Send update_colormap command via Firebase"""
        colormap_index = int(self.colormap_var.get())
        
        success = self.send_command('update_colormap', {
            'colormap_index': colormap_index
        })
        
        if success:
            self.current_params['seismic_colormap_index'] = colormap_index
            self.add_log_message(f"🎨 Colormap: {colormap_index}")
    
    def update_color_scale(self, event=None):
        """Send update_color_scale command via Firebase"""
        times_value = int(self.times_var.get())
        
        success = self.send_command('update_color_scale', {
            'times_value': times_value
        })
        
        if success:
            self.current_params['seismic_times'] = times_value
            self.add_log_message(f"🌈 Color Scale: {times_value}")
    
    # Quick action methods - send JSON-RPC commands
    
    def increase_gain(self):
        """Send increase_gain command via Firebase"""
        success = self.send_command('increase_gain', {})
        if success:
            self.add_log_message("📈 Gain increased")
    
    def decrease_gain(self):
        """Send decrease_gain command via Firebase"""
        success = self.send_command('decrease_gain', {})
        if success:
            self.add_log_message("📉 Gain decreased")
    
    def rotate_left(self):
        """Send rotate_left command via Firebase"""
        success = self.send_command('rotate_left', {})
        if success:
            self.add_log_message("↺ Rotated left")
    
    def rotate_right(self):
        """Send rotate_right command via Firebase"""
        success = self.send_command('rotate_right', {})
        if success:
            self.add_log_message("↻ Rotated right")
    
    def zoom_in(self):
        """Send zoom_in command via Firebase"""
        success = self.send_command('zoom_in', {})
        if success:
            self.add_log_message("🔍+ Zoomed in")
    
    def zoom_out(self):
        """Send zoom_out command via Firebase"""
        success = self.send_command('zoom_out', {})
        if success:
            self.add_log_message("🔍- Zoomed out")
    
    def zoom_reset(self):
        """Send zoom_reset command via Firebase"""
        success = self.send_command('zoom_reset', {})
        if success:
            self.add_log_message("🔍↺ Zoom reset")
    
    def reset_parameters(self):
        """Send reset_parameters command via Firebase"""
        success = self.send_command('reset_parameters', {})
        if success:
            self.add_log_message("🔄 Parameters reset to defaults")
    
    def undo_action(self):
        """Send undo_action command via Firebase"""
        success = self.send_command('undo_action', {})
        if success:
            self.add_log_message("↶ Undo performed")
    
    def redo_action(self):
        """Send redo_action command via Firebase"""
        success = self.send_command('redo_action', {})
        if success:
            self.add_log_message("↷ Redo performed")
    
    def reload_template(self):
        """Send reload_template command via Firebase"""
        success = self.send_command('reload_template', {})
        if success:
            self.add_log_message("📄 Template reloaded")
    
    # Label update methods (for real-time slider feedback)
    
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
        self.shift_x_label.config(text=f"{float(value):.1f}")
    def update_shift_y_label(self, value):
        self.shift_y_label.config(text=f"{float(value):.1f}")
    def update_shift_z_label(self, value):
        self.shift_z_label.config(text=f"{float(value):.1f}")
    def update_gain_label(self, value):
        self.gain_label.config(text=f"{float(value):.1f}")
    def update_colormap_label(self, value):
        self.colormap_label.config(text=f"{int(float(value))}")
    def update_times_label(self, value):
        self.times_label.config(text=f"{int(float(value))}")
    
    # Status and logging methods
    
    def update_status(self, message: str):
        """Update status display"""
        self.status_var.set(f"Status: {message}")
    
    def add_log_message(self, message: str):
        """Add message to command log"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)  # Auto-scroll to bottom
    
    def start_status_monitor(self):
        """Start background thread to monitor Firebase connection"""
        def monitor():
            while True:
                try:
                    time.sleep(5)  # Check every 5 seconds
                    
                    # Update connection status
                    if self.connected:
                        self.connection_status.config(text="✅ Connected")
                    else:
                        self.connection_status.config(text="❌ Disconnected")
                        
                except Exception as e:
                    print(f"Status monitor error: {e}")
                    break
        
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
    
    def run(self):
        """Start the GUI main loop"""
        self.root.mainloop()


def main():
    """Main function to run the Firebase GUI"""
    try:
        print("Starting Seismic Navigation - Firebase Distributed GUI...")
        print("This GUI sends JSON-RPC commands through Firebase to tornado_listener.py")
        print("Make sure tornado_listener.py is running to process commands!")
        print()
        
        # Create and run GUI
        gui = BookmarkGUIFirebase()
        gui.run()
        
    except Exception as e:
        print(f"Error starting Firebase GUI: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()