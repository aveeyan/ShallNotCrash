# shallnotcrash/path_planner/constants.py
"""
[STABLE CALIBRATION - V29]
This version corrects the code to match the intended logic described in
the comments, resolving the critical A* turn penalty bug.
"""
import math
from shallnotcrash.airplane.constants import C172PConstants

class PlannerConstants:
    G_ACCEL_MPS2: float = 9.80665
    EARTH_RADIUS_NM: float = 3440.065
    METERS_TO_NM: float = 1 / 1852.0
    TIME_DELTA_SEC = 30
    METERS_PER_SECOND_PER_KNOT: float = 0.514444
    MAX_ASTAR_ITERATIONS = 75000
    SMOOTHED_PATH_NUM_POINTS = 100
    SMOOTHING_FACTOR = 0.5

    # --- [CRITICAL BUG FIX] ---
    # Value corrected to match documented logic. The previous value of 15.0
    # made turns prohibitively expensive, causing the A* search to fail.
    TURN_PENALTY_FACTOR = 1.2
    
    ALTITUDE_DEVIATION_PENALTY = 1.5
    FEET_PER_NAUTICAL_MILE = 6076.12
    METERS_TO_FEET = 3.28084
    FINAL_APPROACH_FIX_DISTANCE_NM = 3.0
    FINAL_APPROACH_GLIDESLOPE_DEG = 3.0
    GOAL_DISTANCE_TOLERANCE_NM: float = 0.2
    GOAL_ALTITUDE_TOLERANCE_FT: float = 250.0
    
class AircraftProfile:
    SAFE_DEFAULT_GLIDE_RATIO = 9.0
    GLIDE_RATIO: float = SAFE_DEFAULT_GLIDE_RATIO
    GLIDE_SPEED_KTS: float = C172PConstants.EMERGENCY['GLIDE_SPEED']
    STANDARD_TURN_RATE_DEG_S = 3.0
    TURN_DRAG_PENALTY_FACTOR = 1.5
    STANDARD_BANK_ANGLE_DEG = 25.0
