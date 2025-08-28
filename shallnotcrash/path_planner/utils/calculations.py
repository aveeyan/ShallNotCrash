# shallnotcrash/path_planner/utils/calculations.py
from typing import List, Tuple
from ..data_models import AircraftState, Waypoint
from ..constants import PlannerConstants, AircraftProfile
from .coordinates import haversine_distance_nm, calculate_bearing

def calculate_path_distance(waypoints: List[Waypoint]) -> float:
    """
    [RESTORED] Calculates the total geographic distance of a path.
    This function is essential for analysis and was restored.
    """
    distance = 0.0
    for i in range(len(waypoints) - 1):
        distance += haversine_distance_nm(waypoints[i].lat, waypoints[i].lon, waypoints[i+1].lat, waypoints[i+1].lon)
    return distance

def calculate_heuristic(state: AircraftState, goal: Waypoint, final_approach_hdg: float) -> float:
    """
    [INTEGRATED - ENERGY-AWARE HEURISTIC V27]
    This definitive version makes the heuristic "energy-aware." It calculates
    two costs and uses the more constraining of the two:

    1. Geographic Cost: The straight-line distance to the target.
    2. Energy Cost: The minimum horizontal distance the aircraft MUST travel
       to safely descend from its current altitude to the goal altitude.

    This provides a much more accurate, physically-grounded estimate of the
    true remaining path cost, enabling efficient long-range planning.
    """
    # 1. Calculate the simple geographic distance cost.
    distance_to_goal_nm = haversine_distance_nm(state.lat, state.lon, goal.lat, goal.lon)

    # 2. Calculate the energy-based distance cost.
    altitude_to_lose_ft = state.alt_ft - goal.alt_ft
    
    if altitude_to_lose_ft <= 0:
        min_glide_dist_nm = 0.0
    else:
        # Minimum horizontal distance required to lose the surplus altitude.
        min_glide_dist_ft = altitude_to_lose_ft * AircraftProfile.GLIDE_RATIO
        min_glide_dist_nm = min_glide_dist_ft / PlannerConstants.FEET_PER_NAUTICAL_MILE
    
    # The heuristic is the more constraining of the two costs.
    return max(distance_to_goal_nm, min_glide_dist_nm)

def find_longest_axis(polygon_coords: list[tuple[float, float]]) -> Tuple[Waypoint, Waypoint, float]:
    """
    [RESTORED] Finds the longest possible straight line within a polygon.
    This function is critical for defining runway orientation and was restored.
    """
    max_dist_m = 0.0
    best_pair = (None, None)
    if len(polygon_coords) < 2:
        lat, lon = polygon_coords[0] if polygon_coords else (0.0, 0.0)
        wp = Waypoint(lat=lat, lon=lon, alt_ft=0, airspeed_kts=0)
        return (wp, wp, 0.0)
    for i in range(len(polygon_coords)):
        for j in range(i + 1, len(polygon_coords)):
            p1_lat, p1_lon = polygon_coords[i]
            p2_lat, p2_lon = polygon_coords[j]
            dist_nm = haversine_distance_nm(p1_lat, p1_lon, p2_lat, p2_lon)
            dist_m = dist_nm * PlannerConstants.METERS_PER_NAUTICAL_MILE
            if dist_m > max_dist_m:
                max_dist_m = dist_m
                wp1 = Waypoint(lat=p1_lat, lon=p1_lon, alt_ft=0, airspeed_kts=AircraftProfile.GLIDE_SPEED_KTS)
                wp2 = Waypoint(lat=p2_lat, lon=p2_lon, alt_ft=0, airspeed_kts=AircraftProfile.GLIDE_SPEED_KTS)
                best_pair = (wp1, wp2)
    return (best_pair[0], best_pair[1], max_dist_m)
