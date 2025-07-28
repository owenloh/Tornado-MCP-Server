#!/usr/bin/env python3
"""
HTML Bookmark Monitor for Real-time Change Detection

This module monitors the TEMP_BKM.html file for changes and extracts
parameter differences to show users the effects of their commands.

Features:
- Real-time file watching for HTML changes
- Parameter extraction and comparison
- Before/after change visualization
- Integration with NLP terminal for feedback
"""

import os
import time
import threading
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
import xml.etree.ElementTree as ET
import re


@dataclass
class BookmarkParameters:
    """Extracted bookmark parameters for comparison"""
    x_position: Optional[float] = None
    y_position: Optional[float] = None
    z_position: Optional[float] = None
    orient: Optional[tuple] = None
    shift: Optional[tuple] = None
    scale: Optional[tuple] = None
    seismic_visible: Optional[bool] = None
    attribute_visible: Optional[bool] = None
    horizon_visible: Optional[bool] = None
    well_visible: Optional[bool] = None
    x_visible: Optional[bool] = None
    y_visible: Optional[bool] = None
    z_visible: Optional[bool] = None
    seismic_range: Optional[tuple] = None
    seismic_colormap_index: Optional[int] = None
    seismic_times: Optional[int] = None


class HTMLBookmarkMonitor:
    """Monitor TEMP_BKM.html for changes and extract parameters"""
    
    def __init__(self, html_file_path: str = "data/bookmarks/TEMP_BKM.html"):
        """Initialize HTML monitor"""
        self.html_file_path = Path(html_file_path)
        self.last_modified = 0
        self.last_parameters = None
        self.monitoring = False
        self.monitor_thread = None
        self.change_callback = None
        
        # Ensure file exists
        if not self.html_file_path.exists():
            print(f"Warning: HTML file not found: {self.html_file_path}")
    
    def extract_parameters(self, html_content: str) -> BookmarkParameters:
        """Extract parameters from HTML bookmark content"""
        params = BookmarkParameters()
        
        try:
            # Parse XML content
            root = ET.fromstring(html_content)
            
            # Extract position parameters
            x_elem = root.find(".//X/POSITION")
            if x_elem is not None:
                params.x_position = float(x_elem.text)
            
            y_elem = root.find(".//Y/POSITION")
            if y_elem is not None:
                params.y_position = float(y_elem.text)
            
            z_elem = root.find(".//Z/POSITION")
            if z_elem is not None:
                params.z_position = float(z_elem.text)
            
            # Extract orientation (ORIENT element)
            orient_elem = root.find(".//ORIENT")
            if orient_elem is not None:
                orient_values = orient_elem.text.strip().split()
                if len(orient_values) >= 3:
                    params.orient = (float(orient_values[0]), float(orient_values[1]), float(orient_values[2]))
            
            # Extract shift (SHIFT element)
            shift_elem = root.find(".//SHIFT")
            if shift_elem is not None:
                shift_values = shift_elem.text.strip().split()
                if len(shift_values) >= 3:
                    params.shift = (float(shift_values[0]), float(shift_values[1]), float(shift_values[2]))
            
            # Extract scale (SCALE element)
            scale_elem = root.find(".//SCALE")
            if scale_elem is not None:
                scale_values = scale_elem.text.strip().split()
                if len(scale_values) >= 2:
                    params.scale = (float(scale_values[0]), float(scale_values[1]))
            
            # Extract visibility parameters
            seismic_vis = root.find(".//SEISMIC_VISIBILITY")
            if seismic_vis is not None:
                params.seismic_visible = seismic_vis.text.strip().upper() == 'T'
            
            attr_vis = root.find(".//ATTRIBUTE_VISIBILITY")
            if attr_vis is not None:
                params.attribute_visible = attr_vis.text.strip().upper() == 'T'
            
            horizon_vis = root.find(".//HORIZON_VISIBILITY")
            if horizon_vis is not None:
                params.horizon_visible = horizon_vis.text.strip().upper() == 'T'
            
            well_vis = root.find(".//WELL_VISIBILITY")
            if well_vis is not None:
                params.well_visible = well_vis.text.strip().upper() == 'T'
            
            # Extract slice visibility
            x_vis = root.find(".//X/VISIBLE")
            if x_vis is not None:
                params.x_visible = x_vis.text.strip().upper() == 'T'
            
            y_vis = root.find(".//Y/VISIBLE")
            if y_vis is not None:
                params.y_visible = y_vis.text.strip().upper() == 'T'
            
            z_vis = root.find(".//Z/VISIBLE")
            if z_vis is not None:
                params.z_visible = z_vis.text.strip().upper() == 'T'
            
            # Extract seismic range
            range_elem = root.find(".//SEISMIC_COLORMAP/SPECTRUM/RANGE")
            if range_elem is not None:
                range_values = range_elem.text.strip().split()
                if len(range_values) >= 2:
                    params.seismic_range = (float(range_values[0]), float(range_values[1]))
            
            # Extract colormap index
            colormap_elem = root.find(".//COLORMAP_INDEX")
            if colormap_elem is not None:
                params.seismic_colormap_index = int(colormap_elem.text.strip())
            
            # Extract times value
            times_elem = root.find(".//SEISMIC_COLORMAP/SPECTRUM/TIMES")
            if times_elem is not None:
                params.seismic_times = int(times_elem.text.strip())
            
        except Exception as e:
            print(f"Error parsing HTML parameters: {e}")
        
        return params
    
    def compare_parameters(self, old_params: BookmarkParameters, new_params: BookmarkParameters) -> Dict[str, Dict[str, Any]]:
        """Compare two parameter sets and return differences"""
        changes = {}
        
        # Compare all parameter fields
        for field_name in old_params.__dataclass_fields__.keys():
            old_value = getattr(old_params, field_name)
            new_value = getattr(new_params, field_name)
            
            if old_value != new_value:
                changes[field_name] = {
                    "old": old_value,
                    "new": new_value,
                    "change_type": self._get_change_type(field_name, old_value, new_value)
                }
        
        return changes
    
    def _get_change_type(self, field_name: str, old_value: Any, new_value: Any) -> str:
        """Determine the type of change for better display"""
        if old_value is None and new_value is not None:
            return "added"
        elif old_value is not None and new_value is None:
            return "removed"
        elif isinstance(old_value, (int, float)) and isinstance(new_value, (int, float)):
            if new_value > old_value:
                return "increased"
            else:
                return "decreased"
        elif isinstance(old_value, bool) and isinstance(new_value, bool):
            return "toggled"
        else:
            return "changed"
    
    def format_change_message(self, changes: Dict[str, Dict[str, Any]]) -> str:
        """Format changes into a human-readable message"""
        if not changes:
            return "No changes detected in HTML file"
        
        messages = []
        
        for field_name, change_info in changes.items():
            old_val = change_info["old"]
            new_val = change_info["new"]
            change_type = change_info["change_type"]
            
            # Format based on field type
            if field_name in ["x_position", "y_position", "z_position"]:
                coord_name = {"x_position": "Crossline", "y_position": "Inline", "z_position": "Depth"}[field_name]
                if old_val is not None and new_val is not None:
                    messages.append(f"📍 {coord_name}: {old_val:.0f} → {new_val:.0f}")
                else:
                    messages.append(f"📍 {coord_name}: {old_val} → {new_val}")
            
            elif field_name == "orient":
                if old_val and new_val:
                    messages.append(f"🔄 Rotation: ({old_val[0]:.2f}, {old_val[1]:.2f}, {old_val[2]:.2f}) → ({new_val[0]:.2f}, {new_val[1]:.2f}, {new_val[2]:.2f})")
            
            elif field_name == "scale":
                if old_val and new_val:
                    messages.append(f"🔍 Scale: ({old_val[0]:.2f}, {old_val[1]:.2f}) → ({new_val[0]:.2f}, {new_val[1]:.2f})")
            
            elif field_name == "shift":
                if old_val and new_val:
                    messages.append(f"↔️ Shift: ({old_val[0]:.0f}, {old_val[1]:.0f}, {old_val[2]:.0f}) → ({new_val[0]:.0f}, {new_val[1]:.0f}, {new_val[2]:.0f})")
            
            elif field_name.endswith("_visible"):
                data_type = field_name.replace("_visible", "").replace("_", " ").title()
                status = "✅ Shown" if new_val else "❌ Hidden"
                messages.append(f"👁️ {data_type}: {status}")
            
            elif field_name == "seismic_range":
                if old_val and new_val:
                    messages.append(f"📊 Gain Range: ({old_val[0]:.0f}, {old_val[1]:.0f}) → ({new_val[0]:.0f}, {new_val[1]:.0f})")
            
            elif field_name == "seismic_colormap_index":
                messages.append(f"🎨 Colormap: {old_val} → {new_val}")
            
            elif field_name == "seismic_times":
                messages.append(f"🌈 Color Scale: {old_val} → {new_val}")
        
        return "\n".join(messages)
    
    def check_for_changes(self) -> Optional[str]:
        """Check for changes in HTML file and return formatted message"""
        if not self.html_file_path.exists():
            return None
        
        try:
            # Check if file was modified
            current_modified = os.path.getmtime(self.html_file_path)
            if current_modified <= self.last_modified:
                return None
            
            self.last_modified = current_modified
            
            # Read and parse new content
            with open(self.html_file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            new_parameters = self.extract_parameters(html_content)
            
            # Compare with previous parameters
            if self.last_parameters is not None:
                changes = self.compare_parameters(self.last_parameters, new_parameters)
                if changes:
                    message = self.format_change_message(changes)
                    self.last_parameters = new_parameters
                    return message
            
            # Store current parameters for next comparison
            self.last_parameters = new_parameters
            return None
            
        except Exception as e:
            return f"Error monitoring HTML file: {e}"
    
    def start_monitoring(self, callback: Callable[[str], None], interval: float = 1.0):
        """Start monitoring HTML file for changes"""
        self.change_callback = callback
        self.monitoring = True
        
        def monitor_loop():
            while self.monitoring:
                try:
                    change_message = self.check_for_changes()
                    if change_message and self.change_callback:
                        self.change_callback(change_message)
                    
                    time.sleep(interval)
                    
                except Exception as e:
                    if self.monitoring:  # Only print if still monitoring
                        print(f"HTML monitor error: {e}")
                    break
        
        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop monitoring HTML file"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
    
    def get_current_parameters(self) -> Optional[BookmarkParameters]:
        """Get current parameters from HTML file"""
        if not self.html_file_path.exists():
            return None
        
        try:
            with open(self.html_file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            return self.extract_parameters(html_content)
        except Exception as e:
            print(f"Error reading current parameters: {e}")
            return None


def main():
    """Test the HTML monitor"""
    print("🔍 Testing HTML Bookmark Monitor...")
    
    monitor = HTMLBookmarkMonitor()
    
    # Test parameter extraction
    current_params = monitor.get_current_parameters()
    if current_params:
        print("✅ Current parameters extracted:")
        print(f"   Position: X={current_params.x_position}, Y={current_params.y_position}, Z={current_params.z_position}")
        print(f"   Scale: {current_params.scale}")
        print(f"   Seismic Visible: {current_params.seismic_visible}")
    else:
        print("❌ Could not extract parameters")
    
    # Test monitoring
    def on_change(message):
        print(f"🔄 HTML Changed:\n{message}")
    
    print("\n🔍 Starting HTML monitoring (press Ctrl+C to stop)...")
    monitor.start_monitoring(on_change)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Stopping monitor...")
        monitor.stop_monitoring()


if __name__ == "__main__":
    main()