# shallnotcrash/path_planner/utils/calculations.py
from typing import List, Tuple
from ..data_models import AircraftState, Waypoint
from ..constants import PlannerConstants, AircraftProfile
from .coordinates import haversine_distance_nm, calculate_bearing

def calculate_path_distance(waypoints: List[Waypoint]) -> float:
    distance = 0.0
    for i in range(len(waypoints) - 1):
        distance += haversine_distance_nm(waypoints[i].lat, waypoints[i].lon, waypoints[i+1].lat, waypoints[i+1].lon)
    return distance

# In shallnotcrash/path_planner/utils/calculations.py

def calculate_heuristic(state: AircraftState, goal: Waypoint, final_approach_hdg: float) -> float:
    """
    [DEFINITIVE FIX - V26]
    This heuristic is now mathematically "admissible," which is critical for A*
    to find the true shortest path.

    The flaw in the previous version was adding a massive turn penalty, which
    tricked the algorithm into preferring long, looping paths over direct turns.

    The correct heuristic is simply the best-case-scenario cost, which is the
    straight-line distance to the goal. The cost of turning is correctly handled
    by the `calculate_move_cost` function, not the heuristic.
    """
    # The heuristic is the straight-line (Haversine) distance. This is the
    # most common and robust heuristic for geographic A* pathfinding.
    distance_to_goal_nm = haversine_distance_nm(state.lat, state.lon, goal.lat, goal.lon)
    
    return distance_to_goal_nm

def find_longest_axis(polygon_coords: list[tuple[float, float]]) -> Tuple[Waypoint, Waypoint, float]:
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
