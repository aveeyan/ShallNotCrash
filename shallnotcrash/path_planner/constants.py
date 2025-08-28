# shallnotcrash/path_planner/constants.py
"""
[PERFORMANCE-TUNED - V26]
This version is tuned for rapid and decisive path generation. By dramatically
increasing the turn penalty and coarsening the search grid, the A* algorithm
is strongly guided towards efficient paths, eliminating state space explosion
and enabling near-instantaneous solutions. The final path quality is
maintained by the high-fidelity smoothing algorithm.
"""
import math
from shallnotcrash.airplane.constants import C172PConstants

class PlannerConstants:
    # --- A* Search Resolution Parameters ---
    TIME_DELTA_SEC = 15
    
    # [PERFORMANCE TUNE] Coarsen heading precision. The aircraft turns in 45-degree
    # steps, so a 15-degree resolution is more than sufficient and drastically
    # reduces the state space from 72 to 24 heading buckets.
    HEADING_PRECISION_DEG = 15
    
    MAX_ASTAR_ITERATIONS = 50000 # A well-tuned search should not need more.

    # --- Smoothing and Final Path Parameters ---
    SMOOTHED_PATH_NUM_POINTS = 500
    SMOOTHING_FACTOR = 0.5

    # --- Heuristic and Costing Parameters ---
    
    # [CRITICAL PERFORMANCE TUNE] Dramatically increase the turn penalty.
    # This is the most important change. It tells the planner that turns are
    # extremely "expensive" and should be avoided unless necessary to reach the
    # goal. This provides strong guidance and prunes inefficient paths early.
    TURN_PENALTY_FACTOR = 15.0 
    
    HEADING_MISMATCH_PENALTY = 5.0
    ALTITUDE_DEVIATION_PENALTY = 1.5
    
    # --- Geographic and Physical Constants ---
    FEET_PER_NAUTICAL_MILE = 6076.12
    METERS_TO_FEET = 3.28084
    METERS_PER_NAUTICAL_MILE = 1852.0
    EARTH_RADIUS_NM = 3440.065

    # --- Goal and State Precision ---
    
    # [PERFORMANCE TUNE] Coarsen geographic precision for the A* search.
    # A resolution of ~111 meters is sufficient for coarse planning. The
    # smoothing algorithm will create the high-fidelity final track.
    LAT_LON_PRECISION = 3 
    
    FINAL_APPROACH_FIX_DISTANCE_NM = 3.0
    FINAL_APPROACH_GLIDESLOPE_DEG = 3.0
    GOAL_DISTANCE_TOLERANCE_NM: float = 0.2 # Slightly increase tolerance for coarser grid
    GOAL_HEADING_TOLERANCE_DEG: float = 20.0 # Slightly increase tolerance for coarser grid
    GOAL_ALTITUDE_Tolerance_FT: float = 250.0

class AircraftProfile:
    SAFE_DEFAULT_GLIDE_RATIO = 9.0
    IMPORTED_GLIDE_RATIO = getattr(C172PConstants.EMERGENCY, 'GLIDE_RATIO', SAFE_DEFAULT_GLIDE_RATIO)
    GLIDE_RATIO: float = IMPORTED_GLIDE_RATIO if IMPORTED_GLIDE_RATIO > 3.0 else SAFE_DEFAULT_GLIDE_RATIO
    GLIDE_SPEED_KTS: float = C172PConstants.EMERGENCY['GLIDE_SPEED']
    STANDARD_TURN_RATE_DEG_S = 3.0
    TURN_RADIUS_NM = GLIDE_SPEED_KTS / (20 * math.pi)
    # MAX_SAFE_GLIDESLOPE_DEG: float = 5.0
    TURN_DRAG_PENALTY_FACTOR = 1.5