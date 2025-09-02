# shallnotcrash/path_planner/constants.py
import math
from shallnotcrash.airplane.constants import C172PConstants

class PlannerConstants:
    G_ACCEL_MPS2: float = 9.80665
    EARTH_RADIUS_NM: float = 3440.065
    METERS_TO_NM: float = 1 / 1852.0
    
    # [THE FIX] Reduce the time step for a higher-resolution A* search.
    # This creates more detailed paths that can be smoothed effectively.
    TIME_DELTA_SEC = 30
    
    METERS_PER_SECOND_PER_KNOT: float = 0.514444
    MAX_ASTAR_ITERATIONS = 75000
    SMOOTHED_PATH_NUM_POINTS = 500
    TURN_PENALTY_FACTOR = 0.8
    ALTITUDE_DEVIATION_PENALTY = 1.2
    FEET_PER_NAUTICAL_MILE = 6076.12
    METERS_TO_FEET = 3.28084
    FINAL_APPROACH_FIX_DISTANCE_NM = 3.0
    FINAL_APPROACH_GLIDESLOPE_DEG = 3.0
    GOAL_DISTANCE_TOLERANCE_NM: float = 0.5
    GOAL_ALTITUDE_TOLERANCE_FT: float = 500.0
    HIGH_ALTITUDE_THRESHOLD_FT = 3000.0
    HIGH_ALTITUDE_TURN_INCENTIVE = 0.7
    
    # Path smoothing parameters
    MAX_TURN_ANGLE_AGGRESSIVE = 45.0  # Maximum turn angle for aggressive smoothing
    MAX_TURN_ANGLE_CONSERVATIVE = 25.0  # Maximum turn angle for conservative smoothing
    SMOOTHING_ITERATIONS_CONSERVATIVE = 2
    SMOOTHING_ITERATIONS_AGGRESSIVE = 1

class AircraftProfile:
    SAFE_DEFAULT_GLIDE_RATIO = 9.0
    GLIDE_RATIO: float = SAFE_DEFAULT_GLIDE_RATIO
    GLIDE_SPEED_KTS: float = C172PConstants.EMERGENCY['GLIDE_SPEED']
    STANDARD_TURN_RATE_DEG_S = 3.0
    TURN_DRAG_PENALTY_FACTOR = 1.5
    STANDARD_BANK_ANGLE_DEG = 25.0
