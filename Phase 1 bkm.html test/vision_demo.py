from vision import *
import time
import os

# 1. Load a volume (if you have a volume file, otherwise skip this step)
# volume = Volume()
# volume.load('/path/to/your/volume.fdm')
# vision.addSeismic(volume)

# 2. Set up a region of interest
vol_location = VolumeLocation()
vol_location.setIL(20200, 20400, 1)
vol_location.setXL(41284, 41684, 64)
vol_location.setDepth(1000, 1200, 1)

# 3. Set up capture parameters
param = CaptureParameters()
param.setLocations(vol_location)

# 4. Set up file output parameters
fileParameters = CaptureFileParameters()
fileParameters.setPrefix("vision_demo")
fileParameters.setPath("/tmp/")  # Make sure this directory exists
fileParameters.setFormat("png")
param.setFileParameters(fileParameters)

# 5. Change colormap visibility (show seismic and attributes)
vision.setColormapVis(vision.VIS_SEIS | vision.VIS_ATTR)

# 6. Capture an image of the current region
captureImage(Window.MAIN_VIEW).capture(param)
print("Image captured to /tmp/ with prefix 'vision_demo'.")

# 7. (Optional) Load and display a bookmark if it exists
bookmark_file = "/tmp/vision_demo.bmk"
bookmark_name = "demo_view"
if os.path.exists(bookmark_file):
    bkm = BookmarkLocation()
    bkm.load(bookmark_file)
    bkm.selectBookmark(bookmark_name)
    bkm.updateDisplay(True)
    print(f"Displayed bookmark '{bookmark_name}'.")
else:
    print(f"Bookmark file '{bookmark_file}' not found. Skipping bookmark display.")

# 8. Keep the script alive briefly to allow display update
time.sleep(2) 