# shallnotcrash/path_planner/utils/calculations.py
"""
[CORRECTED & COMPLETED]
This module provides core mathematical and geometric calculations for path planning.

This version removes a circular self-import and adds the required functions
`calculate_turn_radius` and `calculate_final_approach_path` that are used
by the core planner.
"""
import math
from typing import List, Tuple

# --- Correctly import dependencies from other modules ---
from ..data_models import AircraftState, Waypoint, Runway
from ..constants import PlannerConstants, AircraftProfile
from .coordinates import haversine_distance_nm, get_destination_point

# --- Existing, correct functions ---

def calculate_path_distance(waypoints: List[Waypoint]) -> float:
    """Calculates the total geographic distance of a path in nautical miles."""
    distance = 0.0
    for i in range(len(waypoints) - 1):
        distance += haversine_distance_nm(waypoints[i].lat, waypoints[i].lon, waypoints[i+1].lat, waypoints[i+1].lon)
    return distance

def calculate_heuristic(state: AircraftState, goal: Waypoint) -> float:
    """
    [INTEGRATED - ENERGY-AWARE HEURISTIC V27]
    Calculates a physically-grounded estimate of the true remaining path cost.
    """
    distance_to_goal_nm = haversine_distance_nm(state.lat, state.lon, goal.lat, goal.lon)
    altitude_to_lose_ft = state.alt_ft - goal.alt_ft
    
    if altitude_to_lose_ft <= 0:
        min_glide_dist_nm = 0.0
    else:
        min_glide_dist_ft = altitude_to_lose_ft * AircraftProfile.GLIDE_RATIO
        min_glide_dist_nm = min_glide_dist_ft / PlannerConstants.FEET_PER_NAUTICAL_MILE
    
    return max(distance_to_goal_nm, min_glide_dist_nm)

def find_longest_axis(polygon_coords: list[tuple[float, float]]) -> Tuple[Waypoint, Waypoint, float]:
    """Finds the longest possible straight line within a polygon."""
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

# --- [FIX] ADDED MISSING FUNCTIONS ---

def calculate_turn_radius(airspeed_kts: float, bank_angle_deg: float = AircraftProfile.STANDARD_BANK_ANGLE_DEG) -> float:
    """
    Calculates the turn radius in nautical miles.
    
    Formula: R = V^2 / (g * tan(phi))
    R: Turn Radius (m)
    V: True Airspeed (m/s)
    g: Gravitational acceleration (m/s^2)
    phi: Bank angle (radians)
    """
    if bank_angle_deg == 0:
        return float('inf')
        
    speed_mps = airspeed_kts * PlannerConstants.METERS_PER_SECOND_PER_KNOT
    bank_angle_rad = math.radians(bank_angle_deg)
    
    # Radius in meters
    radius_m = (speed_mps ** 2) / (PlannerConstants.G_ACCEL_MPS2 * math.tan(bank_angle_rad))
    
    # Convert radius to nautical miles
    radius_nm = radius_m / PlannerConstants.METERS_PER_NAUTICAL_MILE
    return radius_nm

def calculate_final_approach_path(runway: Runway, final_approach_nm: float) -> Tuple[float, float, float, float]:
    """
    Calculates the coordinates for the Final Approach Fix (FAF) and the runway threshold.

    Returns a tuple of (faf_lat, faf_lon, threshold_lat, threshold_lon).
    """
    # The approach heading is the reciprocal of the runway's primary bearing
    approach_heading_deg = (runway.bearing_deg + 180) % 360
    
    # The landing threshold is the "start" of the runway from the perspective of the approach
    threshold_lat, threshold_lon = runway.end_lat, runway.end_lon
    
    # Calculate the FAF by projecting backwards from the threshold along the approach path
    faf_lat, faf_lon = get_destination_point(
        lat=threshold_lat,
        lon=threshold_lon,
        bearing_deg=approach_heading_deg,
        distance_nm=final_approach_nm
    )
    
    return faf_lat, faf_lon, threshold_lat, threshold_lon

# --- [NEW ADDITION] ---
def is_point_in_polygon(lat: float, lon: float, polygon: List[Tuple[float, float]]) -> bool:
    """
    Determines if a point is inside a given polygon using the Ray Casting algorithm.
    This is a fundamental geometric utility.
    
    Args:
        lat: Latitude of the point to check.
        lon: Longitude of the point to check.
        polygon: A list of (lat, lon) tuples defining the vertices of the polygon.

    Returns:
        True if the point is inside the polygon, False otherwise.
    """
    n = len(polygon)
    if n == 0:
        return False
        
    inside = False
    p1_lat, p1_lon = polygon[0]
    
    for i in range(n + 1):
        p2_lat, p2_lon = polygon[i % n]
        # Check if the point's latitude is within the edge's latitude range
        if min(p1_lat, p2_lat) < lat <= max(p1_lat, p2_lat):
            # Check if the point's longitude is to the left of the edge's maximum longitude
            if lon <= max(p1_lon, p2_lon):
                # Calculate the intersection of the ray with the edge
                if p1_lat != p2_lat:
                    x_intersection = (lat - p1_lat) * (p2_lon - p1_lon) / (p2_lat - p1_lat) + p1_lon
                
                # If the point is to the left of the intersection, it crosses the edge
                if p1_lon == p2_lon or lon <= x_intersection:
                    inside = not inside
                    
        p1_lat, p1_lon = p2_lat, p2_lon
        
    return inside

