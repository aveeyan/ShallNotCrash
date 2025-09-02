# shallnotcrash/path_planner/utils/calculations.py
import math
from typing import List, Tuple, Optional

from ..data_models import AircraftState, Waypoint
from ..constants import PlannerConstants, AircraftProfile
from .coordinates import haversine_distance_nm, calculate_bearing

def calculate_path_distance(waypoints: List[Waypoint]) -> float:
    """Calculates the total geographic distance of a path in nautical miles."""
    distance = 0.0
    for i in range(len(waypoints) - 1):
        distance += haversine_distance_nm(waypoints[i].lat, waypoints[i].lon, waypoints[i+1].lat, waypoints[i+1].lon)
    return distance

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

def calculate_max_turn_rate(airspeed_kts: float, bank_angle_deg: float = AircraftProfile.STANDARD_BANK_ANGLE_DEG) -> float:
    """Calculate maximum turn rate in degrees per second."""
    if bank_angle_deg == 0:
        return 0.0
        
    turn_radius_nm = calculate_turn_radius(airspeed_kts, bank_angle_deg)
    if turn_radius_nm == 0:
        return float('inf')
        
    turn_rate_deg_s = (airspeed_kts * 6076.12) / (2 * math.pi * turn_radius_nm) * (180 / math.pi)
    return turn_rate_deg_s

# [NEW] Helper function for the "Greedy Corridor" A* algorithm.
def distance_to_corridor(p_lat, p_lon, a_lat, a_lon, b_lat, b_lon) -> float:
    """Calculates the shortest distance from a point to a line segment (corridor)."""
    # Uses a fast equirectangular projection for local distances
    p_x, p_y = math.radians(p_lon), math.radians(p_lat)
    a_x, a_y = math.radians(a_lon), math.radians(a_lat)
    b_x, b_y = math.radians(b_lon), math.radians(b_lat)
    
    ab_x, ab_y = b_x - a_x, b_y - a_y
    ap_x, ap_y = p_x - a_x, p_y - a_y

    dot_product = ap_x * ab_x + ap_y * ab_y
    if dot_product <= 0:
        return haversine_distance_nm(p_lat, p_lon, a_lat, a_lon)

    squared_length_ab = ab_x**2 + ab_y**2
    if squared_length_ab <= dot_product:
        return haversine_distance_nm(p_lat, p_lon, b_lat, b_lon)

    cross_product = ap_x * ab_y - ap_y * ab_x
    distance_rad = abs(cross_product) / math.sqrt(squared_length_ab)
    return distance_rad * PlannerConstants.EARTH_RADIUS_NM

def is_point_in_polygon(lat: float, lon: float, polygon: List[Tuple[float, float]]) -> bool:
    """Determines if a point is inside a given polygon using the Ray Casting algorithm."""
    # ... (function is unchanged) ...
    n = len(polygon)
    if n == 0: return False
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
