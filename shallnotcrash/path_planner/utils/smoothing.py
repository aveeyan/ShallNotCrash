# shallnotcrash/path_planner/utils/smoothing.py
import numpy as np
from scipy.interpolate import splprep, splev
from typing import List
import math
from ..data_models import Waypoint
from ..constants import PlannerConstants, AircraftProfile
from .coordinates import haversine_distance_nm, calculate_bearing
from .calculations import calculate_turn_radius

def _calculate_turn_radius_constraint(p1: np.ndarray, p2: np.ndarray, p3: np.ndarray, airspeed_kts: float) -> bool:
    """Check if the turn between three points is physically possible."""
    # Calculate bearings and turn angle
    bearing1 = calculate_bearing(p1[1], p1[0], p2[1], p2[0])
    bearing2 = calculate_bearing(p2[1], p2[0], p3[1], p3[0])
    
    turn_angle = bearing2 - bearing1
    if turn_angle > 180:
        turn_angle -= 360
    elif turn_angle < -180:
        turn_angle += 360
    
    # Calculate required turn radius
    dist1 = haversine_distance_nm(p1[1], p1[0], p2[1], p2[0])
    dist2 = haversine_distance_nm(p2[1], p2[0], p3[1], p3[0])
    avg_dist = (dist1 + dist2) / 2
    
    # For sharp turns, the required radius is approximately: R = d / (2 * sin(θ/2))
    required_radius_nm = avg_dist / (2 * math.sin(math.radians(abs(turn_angle) / 2)))
    
    # Get aircraft's minimum turn radius
    min_turn_radius_nm = calculate_turn_radius(airspeed_kts)
    
    return required_radius_nm >= min_turn_radius_nm

def smooth_path_3d(waypoints: List[Waypoint], aggressive: bool = False) -> List[Waypoint]:
    """
    Enhanced path smoothing with physical turn radius constraints.
    """
    if len(waypoints) < 3:
        return waypoints
    
    # Convert to numpy array
    coords = np.array([(wp.lon, wp.lat, wp.alt_ft) for wp in waypoints])
    
    # Remove duplicates
    unique_coords, indices = np.unique(coords, axis=0, return_index=True)
    if len(unique_coords) < 3:
        return waypoints
        
    control_points = unique_coords[np.argsort(indices)]
    
    # Check for physically impossible turns and adjust
    adjusted_points = [control_points[0]]
    for i in range(1, len(control_points) - 1):
        current_point = control_points[i]
        prev_point = adjusted_points[-1]
        next_point = control_points[i + 1]
        
        if not _calculate_turn_radius_constraint(prev_point, current_point, next_point, AircraftProfile.GLIDE_SPEED_KTS):
            # Turn is too sharp, insert intermediate point
            mid_lat = (prev_point[1] + next_point[1]) / 2
            mid_lon = (prev_point[0] + next_point[0]) / 2
            mid_alt = (prev_point[2] + next_point[2]) / 2
            intermediate_point = np.array([mid_lon, mid_lat, mid_alt])
            adjusted_points.append(intermediate_point)
        
        adjusted_points.append(current_point)
    
    adjusted_points.append(control_points[-1])
    adjusted_points = np.array(adjusted_points)
    
    # Continue with original smoothing but with gentler parameters
    x, y, z = adjusted_points[:, 0], adjusted_points[:, 1], adjusted_points[:, 2]
    
    diffs = np.diff(adjusted_points, axis=0)
    u = np.concatenate(([0], np.cumsum(np.linalg.norm(diffs, axis=1))))
    
    if u[-1] == 0:
        return waypoints
    
    k = min(2, len(x) - 1)  # Use quadratic splines for smoother curves
    smoothing_factor = len(x) * 0.5  # More smoothing
    
    try:
        tck, _ = splprep([x, y, z], u=u, s=smoothing_factor, k=k)
        
        num_points = min(PlannerConstants.SMOOTHED_PATH_NUM_POINTS, len(waypoints) * 2)
        u_new = np.linspace(0, u[-1], num_points)
        x_new, y_new, z_new = splev(u_new, tck)
        
        result_waypoints = []
        for lon, lat, alt in zip(x_new, y_new, z_new):
            wp = Waypoint(lat=lat, lon=lon, alt_ft=alt, airspeed_kts=AircraftProfile.GLIDE_SPEED_KTS)
            result_waypoints.append(wp)
        
        return result_waypoints
        
    except Exception as e:
        return waypoints

def _chaikin_pre_smooth(points: np.ndarray, iterations: int = 2) -> np.ndarray:
    """Gentle Chaikin smoothing with reduced aggressiveness."""
    if len(points) < 2:
        return points
        
    for _ in range(iterations):
        new_points = [points[0]]
        for i in range(len(points) - 1):
            p1, p2 = points[i], points[i+1]
            # Less aggressive smoothing ratios
            q = p1 * 0.85 + p2 * 0.15  # Closer to original points
            r = p1 * 0.15 + p2 * 0.85
            new_points.extend([q, r])
        new_points.append(points[-1])
        points = np.array(new_points)
    
    return points
