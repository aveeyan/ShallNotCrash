# shallnotcrash/autopilot/guidance.py
import math
from typing import List, Tuple, Optional

from ..path_planner.data_models import AircraftState, Waypoint
from ..path_planner.utils.coordinates import calculate_bearing, haversine_distance_nm
from ..path_planner.utils.calculations import distance_to_corridor

def find_active_segment(aircraft_state: AircraftState, flight_path: List[Waypoint]) -> Tuple[Waypoint, Waypoint]:
    """Finds the path segment the aircraft is currently flying along."""
    if len(flight_path) < 2:
        return flight_path[0], flight_path[0]

    # A simple approach: find the closest waypoint and assume the segment is leading to it.
    # A more robust solution would find the closest point on the path itself.
    closest_dist = float('inf')
    closest_index = 0
    for i, wp in enumerate(flight_path):
        dist = haversine_distance_nm(aircraft_state.lat, aircraft_state.lon, wp.lat, wp.lon)
        if dist < closest_dist:
            closest_dist = dist
            closest_index = i
            
    if closest_index == 0:
        return flight_path[0], flight_path[1]
    
    return flight_path[closest_index - 1], flight_path[closest_index]

def calculate_guidance_commands(aircraft_state: AircraftState, flight_path: List[Waypoint]) -> dict:
    """Calculates the required pitch and roll commands to follow the flight path."""
    if not flight_path:
        return {"roll_command": 0, "pitch_command": 0}

    start_wp, end_wp = find_active_segment(aircraft_state, flight_path)

    # --- 1. Lateral Guidance (Roll Command) ---
    # Cross-Track Error (XTE): How far left/right are we from the path?
    xt_error_nm = distance_to_corridor(
        aircraft_state.lat, aircraft_state.lon,
        start_wp.lat, start_wp.lon,
        end_wp.lat, end_wp.lon
    )
    
    # Determine if we are left or right of the track
    path_bearing = calculate_bearing(start_wp.lat, start_wp.lon, end_wp.lat, end_wp.lon)
    bearing_to_plane = calculate_bearing(start_wp.lat, start_wp.lon, aircraft_state.lat, aircraft_state.lon)
    angle_diff = (bearing_to_plane - path_bearing + 360) % 360
    if angle_diff > 180:
        xt_error_nm *= -1 # Left of track is negative

    # Command a roll to correct the XTE. A simple proportional controller.
    # We also add a component to turn towards the path's heading.
    heading_error = ((path_bearing - aircraft_state.heading_deg + 180) % 360) - 180
    
    # A 25-degree bank to correct a 15-degree heading error or 0.1nm of cross-track error.
    roll_command = (heading_error * (25.0 / 15.0)) + (xt_error_nm * (25.0 / 0.1))
    roll_command = max(-25, min(25, roll_command)) # Clamp to a max 25-degree bank

    # --- 2. Vertical Guidance (Pitch Command) ---
    # Vertical Deviation: How far above/below the ideal glideslope are we?
    dist_along_segment = haversine_distance_nm(start_wp.lat, start_wp.lon, aircraft_state.lat, aircraft_state.lon)
    total_segment_dist = haversine_distance_nm(start_wp.lat, start_wp.lon, end_wp.lat, end_wp.lon)
    
    fraction_along = dist_along_segment / total_segment_dist if total_segment_dist > 0 else 0
    
    desired_altitude_ft = start_wp.alt_ft + fraction_along * (end_wp.alt_ft - start_wp.alt_ft)
    vertical_error_ft = aircraft_state.alt_ft - desired_altitude_ft
    
    # Command a pitch change to correct the vertical error.
    # Command a 5-degree pitch change for every 200ft of error.
    pitch_command = -(vertical_error_ft * (5.0 / 200.0))
    pitch_command = max(-10, min(10, pitch_command)) # Clamp to a max 10-degree pitch

    return {
        "roll_command": round(roll_command, 1),
        "pitch_command": round(pitch_command, 1),
        "desired_heading": round(path_bearing, 1),
        "xt_error_nm": round(xt_error_nm, 3),
        "vertical_error_ft": round(vertical_error_ft, 1)
    }
