# shallnotcrash/path_planner/utils/__init__.py
"""
The Utils sub-package provides a collection of helper functions for
geodetic calculations and other common tasks required by the PathPlanner.

By importing them here, we create a clean, unified namespace for external modules.
"""

# Promote key functions from the coordinates module to the package level
from .coordinates import get_bearing, get_midpoint, get_destination_point

# This makes them available for import like so:
# from shallnotcrash.path_planner.utils import get_bearing