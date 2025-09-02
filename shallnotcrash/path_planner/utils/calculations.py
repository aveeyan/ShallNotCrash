# shallnotcrash/path_planner/utils/calculations.py
"""
[UNIFIED - V2]
This module provides core mathematical and geometric calculations, now fully
aligned with the unified data models. The obsolete `calculate_final_approach_path`
function has been removed.
"""
import math
from typing import List, Tuple, Optional

# --- [CHANGED] Correctly import dependencies from other modules ---
# The invalid 'Runway' import has been removed.
from ..data_models import AircraftState, Waypoint
from ..constants import PlannerConstants, AircraftProfile
from .coordinates import haversine_distance_nm, calculate_bearing

# --- Existing, correct functions ---

def calculate_path_distance(waypoints: List[Waypoint]) -> float:
    """Calculates the total geographic distance of a path in nautical miles."""
    distance = 0.0
    for i in range(len(waypoints) - 1):
        distance += haversine_distance_nm(waypoints[i].lat, waypoints[i].lon, waypoints[i+1].lat, waypoints[i+1].lon)
    return distance

# shallnotcrash/path_planner/utils/calculations.py
# ... existing code ...

def calculate_heuristic(state: AircraftState, goal: Waypoint, target_heading: Optional[float] = None) -> float:
    """Enhanced heuristic that considers altitude, distance, and optional heading alignment."""
    distance_to_goal_nm = haversine_distance_nm(state.lat, state.lon, goal.lat, goal.lon)
    altitude_to_lose_ft = state.alt_ft - goal.alt_ft
    
    if altitude_to_lose_ft <= 0:
        min_glide_dist_nm = 0.0
    else:
        min_glide_dist_ft = altitude_to_lose_ft * AircraftProfile.GLIDE_RATIO
        min_glide_dist_nm = min_glide_dist_ft / PlannerConstants.FEET_PER_NAUTICAL_MILE
    
    base_heuristic = max(distance_to_goal_nm, min_glide_dist_nm)
    
    # Add heading alignment penalty if target heading is provided
    if target_heading is not None and distance_to_goal_nm < 20.0:
        current_bearing = calculate_bearing(state.lat, state.lon, goal.lat, goal.lon)
        heading_diff = abs(current_bearing - target_heading)
        if heading_diff > 180:
            heading_diff = 360 - heading_diff
        
        alignment_penalty = (heading_diff / 180.0) * (1.0 - (distance_to_goal_nm / 20.0)) * 3.0
        return base_heuristic + alignment_penalty
    
    return base_heuristic

def find_longest_axis(polygon_coords: list[tuple[float, float]]) -> Tuple[Waypoint, Waypoint, float]:
    """Finds the longest possible straight line within a polygon."""
    max_dist_m = 0.0
    best_pair = (None, None)
    if not polygon_coords:
        return (None, None, 0.0)
    if len(polygon_coords) < 2:
        lat, lon = polygon_coords[0]
        wp = Waypoint(lat=lat, lon=lon, alt_ft=0, airspeed_kts=0)
        return (wp, wp, 0.0)

    for i in range(len(polygon_coords)):
        for j in range(i + 1, len(polygon_coords)):
            p1_lat, p1_lon = polygon_coords[i]
            p2_lat, p2_lon = polygon_coords[j]
            dist_nm = haversine_distance_nm(p1_lat, p1_lon, p2_lat, p2_lon)
            dist_m = dist_nm * (1 / PlannerConstants.METERS_TO_NM)
            if dist_m > max_dist_m:
                max_dist_m = dist_m
                wp1 = Waypoint(lat=p1_lat, lon=p1_lon, alt_ft=0, airspeed_kts=AircraftProfile.GLIDE_SPEED_KTS)
                wp2 = Waypoint(lat=p2_lat, lon=p2_lon, alt_ft=0, airspeed_kts=AircraftProfile.GLIDE_SPEED_KTS)
                best_pair = (wp1, wp2)
    return (best_pair[0], best_pair[1], max_dist_m)

def calculate_turn_radius(airspeed_kts: float, bank_angle_deg: float = AircraftProfile.STANDARD_BANK_ANGLE_DEG) -> float:
    """Calculates the turn radius in nautical miles."""
    if bank_angle_deg == 0:
        return float('inf')
        
    speed_mps = airspeed_kts * PlannerConstants.METERS_PER_SECOND_PER_KNOT
    bank_angle_rad = math.radians(bank_angle_deg)
    radius_m = (speed_mps ** 2) / (PlannerConstants.G_ACCEL_MPS2 * math.tan(bank_angle_rad))
    return radius_m * PlannerConstants.METERS_TO_NM

# --- [REMOVED] Obsolete Function ---
# The 'calculate_final_approach_path' function was deleted. Its logic was incorrect
# and has been superseded by the 'select_optimal_landing_approach' function in touchdown.py,
# which the core PathPlanner already uses.
def calculate_max_turn_rate(airspeed_kts: float, bank_angle_deg: float = AircraftProfile.STANDARD_BANK_ANGLE_DEG) -> float:
    """Calculate maximum turn rate in degrees per second."""
    if bank_angle_deg == 0:
        return 0.0
        
    turn_radius_nm = calculate_turn_radius(airspeed_kts, bank_angle_deg)
    if turn_radius_nm == 0:
        return float('inf')
        
    # Turn rate = (airspeed * 6076.12) / (2 * π * turn_radius) * (180/π)
    turn_rate_deg_s = (airspeed_kts * 6076.12) / (2 * math.pi * turn_radius_nm) * (180 / math.pi)
    return turn_rate_deg_s


def is_point_in_polygon(lat: float, lon: float, polygon: List[Tuple[float, float]]) -> bool:
    """Determines if a point is inside a given polygon using the Ray Casting algorithm."""
    n = len(polygon)
    if n == 0:
        return False
        
    inside = False
    p1_lat, p1_lon = polygon[0]
    
    for i in range(n + 1):
        p2_lat, p2_lon = polygon[i % n]
        if min(p1_lat, p2_lat) < lat <= max(p1_lat, p2_lat):
            if lon <= max(p1_lon, p2_lon):
                if p1_lat != p2_lat:
                    x_intersection = (lat - p1_lat) * (p2_lon - p1_lon) / (p2_lat - p1_lat) + p1_lon
                if p1_lon == p2_lon or lon <= x_intersection:
                    inside = not inside
        p1_lat, p1_lon = p2_lat, p2_lon
        
    return inside
