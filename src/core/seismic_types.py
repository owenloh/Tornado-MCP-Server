"""
Data types and enumerations for seismic navigation interface

This module contains all the data types, enums, and data classes
used throughout the seismic navigation system.
"""

from typing import Tuple
from dataclasses import dataclass
from enum import Enum


class DataType(Enum):
    """Enumeration of seismic data types that can be toggled"""
    SEISMIC = "SEISMIC_VISIBILITY"
    ATTRIBUTE = "ATTRIBUTE_VISIBILITY" 
    HORIZON = "HORIZON_VISIBILITY"
    WELL = "WELL_VISIBILITY"
    CIGPICK = "CIGPICK_VISIBILITY"
    MISC_PLOT = "MISC_PLOT_VISIBILITY"
    PROFILE = "PROFILE_VISIBILITY"


class SliceType(Enum):
    """Enumeration of slice types (X=crossline, Y=inline, Z=depth)"""
    X = "X"  # Crossline
    Y = "Y"  # Inline  
    Z = "Z"  # Depth/Time


@dataclass
class SeismicTerminology:
    """Mapping of seismic terminology for user-friendly interface"""
    CROSSLINE = "X"  # XL coordinate
    INLINE = "Y"     # IL coordinate
    DEPTH = "Z"      # Depth/Time coordinate
    
    @classmethod
    def get_axis_from_term(cls, term: str) -> str:
        """Convert user-friendly terms to XML axis names"""
        term_map = {
            'crossline': cls.CROSSLINE,
            'xl': cls.CROSSLINE,
            'x': cls.CROSSLINE,
            'inline': cls.INLINE,
            'il': cls.INLINE,
            'y': cls.INLINE,
            'depth': cls.DEPTH,
            'time': cls.DEPTH,
            'z': cls.DEPTH
        }
        return term_map.get(term.lower(), term.upper())