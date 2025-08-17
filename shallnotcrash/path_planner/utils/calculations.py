# shallnotcrash/path_planner/utils/calculations.py
"""
Provides calculation functions for the A* search, including path distance
and the crucial heuristic estimation.
"""
from typing import List
from ..data_models import AircraftState, Waypoint
from ..constants import PlannerConstants, AircraftProfile
from .coordinates import haversine_distance_nm, calculate_bearing

def calculate_path_distance(waypoints: List[Waypoint]) -> float:
    """Calculates the total length of a path in nautical miles."""
    distance = 0.0
    for i in range(len(waypoints) - 1):
        wp1 = waypoints[i]
        wp2 = waypoints[i+1]
        distance += haversine_distance_nm(wp1.lat, wp1.lon, wp2.lat, wp2.lon)
    return distance

def calculate_heuristic(state: AircraftState, goal: Waypoint) -> float:
    """
    Calculates the A* heuristic cost (h_cost) from a state to the goal.

    This is an "orientation-aware" heuristic. It combines two factors:
    1.  The direct distance to the goal (a classic heuristic).
    2.  A significant penalty for having a heading that points away from the goal.

    This prevents the planner from exploring "spikes" or hairpin turns where
    the aircraft is close to the goal but facing the wrong direction.
    """
    # --- Altitude Check: Is the goal reachable from this altitude? ---
    min_alt_req = goal.alt_ft + (haversine_distance_nm(state.lat, state.lon, goal.lat, goal.lon) * PlannerConstants.FEET_PER_NAUTICAL_MILE) / AircraftProfile.GLIDE_RATIO
    if state.alt_ft < min_alt_req:
        return float('inf') # This path is impossible.

    # --- 1. Distance Component ---
    distance_to_goal_nm = haversine_distance_nm(state.lat, state.lon, goal.lat, goal.lon)

    # --- 2. Heading Penalty Component ---
    bearing_to_goal_deg = calculate_bearing(state.lat, state.lon, goal.lat, goal.lon)
    
    # Calculate the absolute angular difference (0 to 180 degrees)
    heading_error_deg = abs(((state.heading_deg - bearing_to_goal_deg + 180) % 360) - 180)
    
    # Normalize the error to a [0, 1] penalty factor
    normalized_penalty = heading_error_deg / 180.0
    
    # Apply the penalty constant
    heading_penalty = normalized_penalty * PlannerConstants.HEADING_MISMATCH_PENALTY

    # --- 3. Final Heuristic ---
    # The estimated cost is the distance plus the penalty for being poorly oriented.
    return distance_to_goal_nm + heading_penalty
