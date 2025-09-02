# shallnotcrash/path_planner/utils/smoothing.py
import numpy as np
from scipy.interpolate import splprep, splev
from typing import List
from ..data_models import Waypoint
from ..constants import PlannerConstants, AircraftProfile
from .coordinates import haversine_distance_nm, calculate_bearing

def _calculate_turn_angle(p1: np.ndarray, p2: np.ndarray, p3: np.ndarray) -> float:
    """Calculate the turn angle at point p2 when moving from p1 to p2 to p3."""
    # Convert to bearings
    bearing1 = calculate_bearing(p1[1], p1[0], p2[1], p2[0])  # lat, lon order
    bearing2 = calculate_bearing(p2[1], p2[0], p3[1], p3[0])
    
    # Calculate turn angle
    turn_angle = bearing2 - bearing1
    if turn_angle > 180:
        turn_angle -= 360
    elif turn_angle < -180:
        turn_angle += 360
        
    return abs(turn_angle)

def _physics_constrained_smoothing(points: np.ndarray, max_turn_angle: float = 30.0) -> np.ndarray:
    """
    Apply smoothing while respecting aircraft turn limitations.
    Reduces sharp turns without creating impossible flight paths.
    """
    if len(points) < 3:
        return points
        
    smoothed = [points[0]]  # Keep first point
    
    for i in range(1, len(points) - 1):
        prev_point = smoothed[-1]
        current_point = points[i]
        next_point = points[i + 1]
        
        # Check if the turn angle is too sharp
        turn_angle = _calculate_turn_angle(prev_point, current_point, next_point)
        
        if turn_angle > max_turn_angle:
            # Create a gentler turn by interpolating
            # Move the current point slightly toward the line between prev and next
            interp_factor = max(0.1, min(0.9, max_turn_angle / turn_angle))
            
            # Linear interpolation to reduce turn sharpness
            direction_vector = next_point - prev_point
            new_current = prev_point + direction_vector * 0.5  # Move toward midpoint
            
            # Blend with original position to maintain some of the original path
            blended_point = current_point * interp_factor + new_current * (1 - interp_factor)
            smoothed.append(blended_point)
        else:
            smoothed.append(current_point)
    
    smoothed.append(points[-1])  # Keep last point
    return np.array(smoothed)

def smooth_path_3d(waypoints: List[Waypoint], aggressive: bool = False) -> List[Waypoint]:
    """
    Enhanced path smoothing with physics constraints.
    
    Args:
        waypoints: Input waypoints to smooth
        aggressive: If True, allows sharper turns for shorter paths. If False, prioritizes flyable paths.
    """
    if len(waypoints) < 3:
        return waypoints
    
    # Convert to numpy array for easier manipulation
    coords = np.array([(wp.lon, wp.lat, wp.alt_ft) for wp in waypoints])
    
    # Remove duplicate points that can cause smoothing issues
    unique_coords, indices = np.unique(coords, axis=0, return_index=True)
    if len(unique_coords) < 3:
        return waypoints
        
    # Sort by original order
    control_points = unique_coords[np.argsort(indices)]
    
    # [NEW] Apply physics-constrained pre-smoothing
    max_turn_angle = 45.0 if aggressive else 25.0  # Degrees
    physics_smoothed = _physics_constrained_smoothing(control_points, max_turn_angle)
    
    # Apply gentle Chaikin smoothing (reduced iterations)
    iterations = 1 if aggressive else 2
    chaikin_smoothed = _chaikin_pre_smooth(physics_smoothed, iterations=iterations)
    
    # Prepare for spline fitting
    x, y, z = chaikin_smoothed[:, 0], chaikin_smoothed[:, 1], chaikin_smoothed[:, 2]
    
    # Calculate cumulative distance for parameterization
    diffs = np.diff(chaikin_smoothed, axis=0)
    u = np.concatenate(([0], np.cumsum(np.linalg.norm(diffs, axis=1))))
    
    if u[-1] == 0:
        return waypoints
    
    # Use lower smoothing factor to preserve more of the original path shape
    k = min(3, len(x) - 1)
    smoothing_factor = 0 if aggressive else len(x) * 0.1  # Adaptive smoothing
    
    try:
        tck, _ = splprep([x, y, z], u=u, s=smoothing_factor, k=k)
        
        # Generate fewer points for less aggressive smoothing
        num_points = min(PlannerConstants.SMOOTHED_PATH_NUM_POINTS, len(waypoints) * 3)
        u_new = np.linspace(0, u[-1], num_points)
        x_new, y_new, z_new = splev(u_new, tck)
        
        # [NEW] Validate that no turn exceeds aircraft capabilities
        result_waypoints = []
        for i, (lon, lat, alt) in enumerate(zip(x_new, y_new, z_new)):
            wp = Waypoint(lat=lat, lon=lon, alt_ft=alt, airspeed_kts=AircraftProfile.GLIDE_SPEED_KTS)
            
            # Check turn angle if we have previous waypoints
            if len(result_waypoints) >= 2:
                turn_angle = _calculate_turn_angle(
                    np.array([result_waypoints[-2].lon, result_waypoints[-2].lat]),
                    np.array([result_waypoints[-1].lon, result_waypoints[-1].lat]),
                    np.array([lon, lat])
                )
                
                # Skip waypoints that create impossible turns
                if turn_angle > 60.0 and not aggressive:  # 60° is absolute maximum
                    continue
                    
            result_waypoints.append(wp)
        
        return result_waypoints if len(result_waypoints) >= 2 else waypoints
        
    except Exception as e:
        # Fall back to original waypoints if smoothing fails
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
