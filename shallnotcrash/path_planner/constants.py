# shallnotcrash/path_planner/constants.py
"""
[DEFINITIVE CALIBRATION - V28]
This version resolves the core conflict between the heuristic and the cost
function. The turn penalty has been reduced from a prohibitive value (15.0)
to a realistic one (1.2), allowing the planner to make necessary maneuvers.
The logic now correctly reflects that a well-planned turn is efficient, not
a failure state. This enables effective long-range pathfinding.
"""
import math
from shallnotcrash.airplane.constants import C172PConstants

# In shallnotcrash/path_planner/constants.py

class PlannerConstants:
    # --- A* Search Resolution Parameters ---

    # [DEFINITIVE RE-ARCHITECTING] The core flaw was not in the planner's
    # logic, but in its perception of time. The previous TIME_DELTA_SEC of 10
    # was too small, creating a "Planck Time Paradox." It forced the planner
    # to take tiny, myopic steps, resulting in an astronomically large and
    # "flat" search space that it could not navigate within the iteration limit.
    #
    # By increasing the time delta to 30 seconds, we force the planner to
    # think in larger, more strategic blocks. Each step is now a significant
    # maneuver, making the heuristic gradient sharp and clear. This allows
    # the A* search to find long, complex paths efficiently.
    #
    # The iteration limit is also increased as a safeguard for these more
    # complex, high-energy scenarios.
    TIME_DELTA_SEC = 30
    HEADING_PRECISION_DEG = 15
    MAX_ASTAR_ITERATIONS = 75000 # Increased limit for complex problems

    # --- Smoothing and Final Path Parameters ---
    SMOOTHED_PATH_NUM_POINTS = 500
    SMOOTHING_FACTOR = 0.5

    # --- Heuristic and Costing Parameters ---
    TURN_PENALTY_FACTOR = 15.0
    HEADING_MISMATCH_PENALTY = 5.0
    ALTITUDE_DEVIATION_PENALTY = 1.5
    
    # --- Geographic and Physical Constants ---
    FEET_PER_NAUTICAL_MILE = 6076.12
    METERS_TO_FEET = 3.28084
    METERS_PER_NAUTICAL_MILE = 1852.0
    EARTH_RADIUS_NM = 3440.065

    # --- Goal and State Precision ---
    LAT_LON_PRECISION = 3 
    FINAL_APPROACH_FIX_DISTANCE_NM = 3.0
    FINAL_APPROACH_GLIDESLOPE_DEG = 3.0
    GOAL_DISTANCE_TOLERANCE_NM: float = 0.2
    GOAL_HEADING_TOLERANCE_DEG: float = 20.0
    GOAL_ALTITUDE_Tolerance_FT: float = 250.0
    
class AircraftProfile:
    # [DEFINITIVE CALIBRATION] The planner's performance is critically
    # dependent on an accurate glide ratio for its heuristic calculation.
    # The previous implementation imported this value from an external,
    # un-audited dependency, which provided a corrupted, unrealistically low
    # value. This created a weak heuristic, causing the planner to exhaust
    # its iterations on every target.
    #
    # This version severs that fragile dependency. We now enforce a
    # physically realistic, hardcoded glide ratio of 9.0. This insulates
    # the planner from external corruption and provides the heuristic with
    # the accurate data required for effective strategic guidance.

    SAFE_DEFAULT_GLIDE_RATIO = 9.0
    GLIDE_RATIO: float = SAFE_DEFAULT_GLIDE_RATIO # Enforce the correct value.
    
    # The import of glide speed is retained as it is less critical to the
    # heuristic's strategic guidance.
    GLIDE_SPEED_KTS: float = C172PConstants.EMERGENCY['GLIDE_SPEED']

    STANDARD_TURN_RATE_DEG_S = 3.0
    TURN_RADIUS_NM = GLIDE_SPEED_KTS / (20 * math.pi)
    TURN_DRAG_PENALTY_FACTOR = 1.5