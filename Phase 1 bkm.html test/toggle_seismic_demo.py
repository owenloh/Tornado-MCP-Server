from enum import IntEnum
from base import *
from vision import *
import time
import logging
import os

# Enumerations from Tornado Python API as IntEnum classes:
class SliceVis(IntEnum):
    NONE = 0
    X = 1
    Y = 2
    Z = 3
    T = 4
    ALL = 5

class DataVis(IntEnum):
    NONE = 0
    SEIS = 1
    ATTR = 2
    HORZ = 3
    PROF = 4
    WELL = 5
    CIGP = 6
    SCAT = 7
    ALL = 8

class DomainPick(IntEnum):
    TIME = 0
    DEPTH = 1
    UNKNOWN = 2

# Windows available for the snapshot.
class SnapWindow(IntEnum):
    MAIN_VIEW = 0
    GATHER = 1
    ATTR_PROFILE = 2

# Set up logging
log_dir = "/tpa/trutl07/Tornado_Agentic/"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "tornado_vision_demo.log")
logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

try:
    # Load seismic data
    vision.loadSeismic('a:eamea::trutl07:/seisml_miniproject/original_seismic_w_dipxy')
    logging.info("Seismic loaded.")
    print("Seismic loaded.")

    # Show seismic
    vision.setDataTypeVis(DataVis.SEIS)
    logging.info("Seismic display ON.")
    print("Seismic display ON.")

    # Set specific slices (XL,IL,Z)
    # how about using setRealWorldCoord
    # you MUST have both XL and IL set, challenge
    vol_location = VolumeLocation()
    vol_location.setXL(25619) 
    vol_location.setIL(9000)
    # vol_location.setZ(1000)

    # Enable crossline slice view (SliceVis.Y is typically crossline)
    vision.setSliceVis(SliceVis.X)
    logging.info("Crossline slice view enabled.")
    print("Crossline slice view enabled.")

    # setting saving location for capture
    file_parameters = CaptureFileParameters()
    file_parameters.setPrefix('test_capture')
    file_parameters.setPath('/tpa/trutl07/Tornado_Agentic/')
    file_parameters.setFormat('png')

    # for ImageRecorder? could work for setting locations as well
    params = CaptureParameters()
    params.setFileParameters(file_parameters)
    params.setLocations(vol_location)

    # to lock and show the changes, wrap into a .show() function
    captureImage(Window.MAIN_VIEW).capture(params)
    time.sleep(5)

    # Continue with periodic toggling as before...
    vision.setDataTypeVis(DataVis.NONE)
    logging.info("Seismic display OFF.")
    print("Seismic display OFF.")
    time.sleep(5)

    vision.setDataTypeVis(DataVis.SEIS)
    logging.info("Seismic display ON.")
    print("Seismic display ON.")
    time.sleep(5)

    vision.setDataTypeVis(DataVis.NONE)
    logging.info("Seismic display OFF.")
    print("Seismic display OFF.")
    time.sleep(5)

    vision.setDataTypeVis(DataVis.SEIS)
    logging.info("Seismic display ON again.")
    print("Seismic display ON again.")

except Exception as e:
    logging.exception(f"Exception occurred: {e}")
    print(f"Exception occurred: {e}")



