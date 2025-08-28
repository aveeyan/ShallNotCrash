# shallnotcrash/path_planner/__init__.py
"""
Initializes the path_planner module, defining its public API.

This file makes the core components of the planner directly accessible
to client modules, simplifying imports and hiding the internal structure.
"""
# Core logic classes from core.py
from .core import PathPlanner, GuidanceComputer

# Public data models from data_models.py
from .data_models import AircraftState, Runway, Waypoint, FlightPath

# Expose key utility functions as part of the public API
from .utils.coordinates import get_midpoint, get_bearing, get_destination_point, haversine_distance_nm

# Expose the AptDatLoader for clients that need to use it directly
from .runway_loader import AptDatLoader