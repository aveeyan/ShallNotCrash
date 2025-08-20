# shallnotcrash/path_planner/constants.py
"""
[ULTRA-REALISTIC POLISH - V25]
This version provides the final tuning for "ultra-realistic" path generation.
By significantly increasing the SMOOTHING_FACTOR, the spline algorithm is given
more authority to create a natural, flowing curve that is not rigidly bound to
the coarse waypoints of the A* search. This eliminates the final jagged
artifacts at the entry and exit of turns.
"""
import math
from shallnotcrash.airplane.constants import C172PConstants

class PlannerConstants:
    # --- A* Search Resolution Parameters ---
    TIME_DELTA_SEC = 15
    HEADING_PRECISION_DEG = 5
    MAX_ASTAR_ITERATIONS = 900000

    # --- Smoothing and Final Path Parameters ---
    SMOOTHED_PATH_NUM_POINTS = 500
    
    # [CRITICAL FIX] Increased from 0.5 to 3.0 for ultra-smooth, realistic curves.
    # This allows the smoother to prioritize the path's flow over strict
    # adherence to the coarse A* vertices.
    SMOOTHING_FACTOR = 3.0

    # --- Heuristic and Costing Parameters ---
    TURN_PENALTY_FACTOR = 2.5
    HEADING_MISMATCH_PENALTY = 5.0
    ALTITUDE_DEVIATION_PENALTY = 1.5
    
    # --- Geographic and Physical Constants ---
    FEET_PER_NAUTICAL_MILE = 6076.12
    METERS_TO_FEET = 3.28084
    METERS_PER_NAUTICAL_MILE = 1852.0
    EARTH_RADIUS_NM = 3440.065

    # --- Goal and State Precision ---
    LAT_LON_PRECISION = 4
    FINAL_APPROACH_FIX_DISTANCE_NM = 3.0
    FINAL_APPROACH_GLIDESLOPE_DEG = 3.0
    GOAL_DISTANCE_TOLERANCE_NM: float = 0.15
    GOAL_HEADING_TOLERANCE_DEG: float = 15.0
    GOAL_ALTITUDE_TOLERANCE_FT: float = 200.0  # Allow ±200 ft altitude tolerance

class AircraftProfile:
    SAFE_DEFAULT_GLIDE_RATIO = 9.0
    IMPORTED_GLIDE_RATIO = getattr(C172PConstants.EMERGENCY, 'GLIDE_RATIO', SAFE_DEFAULT_GLIDE_RATIO)
    GLIDE_RATIO: float = IMPORTED_GLIDE_RATIO if IMPORTED_GLIDE_RATIO > 3.0 else SAFE_DEFAULT_GLIDE_RATIO
    GLIDE_SPEED_KTS: float = C172PConstants.EMERGENCY['GLIDE_SPEED']
    STANDARD_TURN_RATE_DEG_S = 3.0
    TURN_RADIUS_NM = GLIDE_SPEED_KTS / (20 * math.pi)

    # [AERODYNAMIC FIX] Add a physical limit for the steepest safe descent angle.
    # A standard 3-degree slope is normal. A high-drag configuration might
    # achieve 5-6 degrees. Anything more is likely unrealistic and unsafe.
    MAX_SAFE_GLIDESLOPE_DEG: float = 5.0
