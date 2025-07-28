# shallnotcrash/path_planner/constants.py
"""
Centralized constants for the Path Planner module.
This includes physical constants, A* search parameters, and imports of the
specific aircraft performance profile being used.
"""
import math
from shallnotcrash.airplane.constants import C172PConstants

class PlannerConstants:
    """Configuration for the A* path planner's behavior."""
    
    # --- A* Search Parameters ---
    # The time, in seconds, for each step of the kinematic projection.
    # Smaller values are more accurate but computationally expensive.
    TIME_DELTA_SEC = 10
    
    # The bank angle the planner will use for standard rate turns.
    # Kept conservative for safety and passenger comfort.
    DEFAULT_BANK_ANGLE_DEG = 25.0

    # --- Physical Constants ---
    FEET_PER_NAUTICAL_MILE = 6076.12
    DEGREES_TO_RADIANS = math.pi / 180.0
    RADIANS_TO_DEGREES = 180.0 / math.pi
    EARTH_RADIUS_NM = 3440.065 # Earth's radius in nautical miles

class AircraftProfile:
    """
    Imports and exposes the specific aircraft constants for the planner to use.
    This acts as a single point of reference for all aircraft performance data.
    """
    # Currently locked to the Cessna 172P operational profile.
    PERFORMANCE = C172PConstants