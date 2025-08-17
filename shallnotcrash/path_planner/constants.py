# shallnotcrash/path_planner/constants.py
"""
Centralized constants for the Path Planner module.
This includes physical constants, A* search parameters, and an adapter
for the specific aircraft performance profile being used.
"""
import math
from shallnotcrash.airplane.constants import C172PConstants

class PlannerConstants:
    """Configuration for the A* path planner's behavior."""
    
    # --- Planner's Maneuvering Assumptions ---
    DEFAULT_TURN_RATE_DEG_S = 3.0

    # --- Physical & Conversion Constants ---
    FEET_PER_NAUTICAL_MILE = 6076.12
    METERS_TO_FEET = 3.28084
    METERS_PER_NAUTICAL_MILE = 1852.0
    EARTH_RADIUS_NM = 3440.065

    # --- A* Search & Kinematics ---
    TIME_DELTA_SEC = 20.0
    
    # --- Discretization (State-space resolution for A*) ---
    LAT_LON_PRECISION = 4
    ALT_PRECISION_FT = 100
    HEADING_PRECISION_DEG = 15

    # --- Final Approach & Landing Sequence ---
    FINAL_APPROACH_FIX_DISTANCE_NM = 3.0
    FINAL_APPROACH_GLIDESLOPE_DEG = 3.0

    # --- Path Smoothing ---
    SMOOTHED_PATH_NUM_POINTS = 500
    SMOOTHING_FACTOR = 0.00001

    # --- Costing and Heuristics ---
    TURN_PENALTY_FACTOR = 5.0
    # --- [NEW] Add a significant penalty for being pointed away from the goal.
    # This value is an "equivalent distance" in nautical miles.
    HEADING_MISMATCH_PENALTY = 75.0

class AircraftProfile:
    """
    Acts as an adapter to provide a clean, consistent interface to the
    planner, regardless of the source constant file's structure.
    """
    GLIDE_SPEED_KTS: float = C172PConstants.EMERGENCY['GLIDE_SPEED']
    GLIDE_RATIO: float = C172PConstants.EMERGENCY['GLIDE_RATIO']
