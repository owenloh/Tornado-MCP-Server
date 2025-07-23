from vision import *
import time
import os

# --- User configuration: set these to match your current view ---
# These should be set to the current IL/XL/Depth range you want to zoom from
current_il_min = 20000
current_il_max = 21000
current_xl_min = 40000
current_xl_max = 41000
current_z_min = 1000   # Example depth minimum
current_z_max = 2000   # mExample depth maximum

# --- Calculate new zoomed-in window (2x zoom = halve the window size) ---
il_center = (current_il_min + current_il_max) / 2
xl_center = (current_xl_min + current_xl_max) / 2
z_center = (current_z_min + current_z_max) / 2
il_half_range = (current_il_max - current_il_min) / 2
xl_half_range = (current_xl_max - current_xl_min) / 2
z_half_range = (current_z_max - current_z_min) / 2

new_il_half_range = il_half_range / 2
new_xl_half_range = xl_half_range / 2
new_z_half_range = z_half_range / 2

new_il_min = int(il_center - new_il_half_range)
new_il_max = int(il_center + new_il_half_range)
new_xl_min = int(xl_center - new_xl_half_range)
new_xl_max = int(xl_center + new_xl_half_range)
new_z_min = int(z_center - new_z_half_range)
new_z_max = int(z_center + new_z_half_range)

# --- Set the new view using VolumeLocation ---
vol_location = VolumeLocation()
vol_location.setIL(new_il_min, new_il_max, 1)
vol_location.setXL(new_xl_min, new_xl_max, 1)
vol_location.setDepth(new_z_min, new_z_max, 1)

# --- Attempt to save as a bookmark (no API for this, so inform the user) ---
bookmark_file = "/tmp/zoom_x2.bmk"
bookmark_name = "zoom_x2"

print("NOTE: Tornado API does not provide a way to programmatically save a bookmark.")
print("Please use the GUI to save the current view as a bookmark named '{}', at: {}".format(bookmark_name, bookmark_file))

# --- Load and display the bookmark (if it exists) ---
if os.path.exists(bookmark_file):
    bkm = BookmarkLocation()
    bkm.load(bookmark_file)
    bkm.selectBookmark(bookmark_name)
    bkm.updateDisplay(True)
    print("Loaded and displayed bookmark '{}'.".format(bookmark_name))
else:
    print("Bookmark file '{}' does not exist. Please create it manually in the GUI.".format(bookmark_file))

# --- Keep the script alive briefly to allow the display to update ---
time.sleep(2) 