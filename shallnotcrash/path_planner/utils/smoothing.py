# shallnotcrash/path_planner/utils/smoothing.py
import numpy as np
from scipy.interpolate import splprep, splev
from typing import List
import math
import logging
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
    [UPGRADED] Smooths a 3D path using B-spline interpolation for a flyable trajectory.
    """
    if len(waypoints) < 3:
        return waypoints
    
    # Convert to numpy array for numerical operations
    coords = np.array([(wp.lon, wp.lat, wp.alt_ft) for wp in waypoints])
    
    # Remove consecutive duplicate points that can cause interpolation errors
    unique_mask = np.concatenate(([True], np.any(np.diff(coords, axis=0) != 0, axis=1)))
    coords = coords[unique_mask]
    
    if len(coords) < 3:
        return waypoints
        
    x, y, z = coords[:, 0], coords[:, 1], coords[:, 2]
    
    # Parameterize the path based on cumulative distance
    u = np.concatenate(([0], np.cumsum(np.linalg.norm(np.diff(coords, axis=0), axis=1))))
    
    if u[-1] == 0:
        return waypoints
    
    # Use quadratic splines (k=2) for a good balance of smoothness and path adherence
    k = min(2, len(x) - 1)
    
    # The smoothing factor 's' controls how closely the spline fits the waypoints.
    # A larger 's' value creates a smoother path.
    smoothing_factor = len(x) * 0.1
    
    try:
        # Create the B-spline representation of the path
        tck, _ = splprep([x, y, z], u=u, s=smoothing_factor, k=k)
        
        # Evaluate the spline at a higher resolution to get the smooth path
        num_points = PlannerConstants.SMOOTHED_PATH_NUM_POINTS
        u_new = np.linspace(0, u[-1], num_points)
        x_new, y_new, z_new = splev(u_new, tck)
        
        # Convert the new coordinates back into Waypoint objects
        result_waypoints = []
        for lon, lat, alt in zip(x_new, y_new, z_new):
            wp = Waypoint(lat=lat, lon=lon, alt_ft=alt, airspeed_kts=AircraftProfile.GLIDE_SPEED_KTS)
            result_waypoints.append(wp)
        
        return result_waypoints
        
    except Exception as e:
        # If spline fitting fails for any reason, return the original (unsmoothed) path
        logging.warning(f"Path smoothing failed: {e}. Returning raw path.")
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
