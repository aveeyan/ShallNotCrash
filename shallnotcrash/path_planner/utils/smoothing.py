# shallnotcrash/path_planner/utils/smoothing.py
"""
[REFACTORED AND ROBUST - V16]
This version provides robust 3D spline smoothing that gracefully degrades
its spline degree (k) based on the number of unique waypoints available.
It handles short paths by using quadratic (k=2) or linear (k=1) splines
instead of failing, ensuring a consistently smoothed output. It also still
enforces the boundary conditions to guarantee a perfect anchor to the start
and end points of the trajectory.
"""
import numpy as np
from scipy.interpolate import splprep, splev
from typing import List
from ..data_models import Waypoint
from ..constants import PlannerConstants, AircraftProfile

def smooth_path_3d(waypoints: List[Waypoint]) -> List[Waypoint]:
    # A path with 0 or 1 point cannot be smoothed or interpolated.
    if len(waypoints) < 2:
        return waypoints

    original_start_wp = waypoints[0]
    original_end_wp = waypoints[-1]

    coords = np.array([(wp.lon, wp.lat, wp.alt_ft) for wp in waypoints])
    
    # Remove duplicate points, which are fatal to the spline algorithm,
    # while preserving the original order of the unique points.
    unique_coords, indices = np.unique(coords, axis=0, return_index=True)
    
    # Not enough unique points to form any kind of path.
    if len(unique_coords) < 2:
        return waypoints

    # Sort the unique coordinates by their original appearance
    sorted_unique_coords = unique_coords[np.argsort(indices)]
    x, y, z = sorted_unique_coords[:, 0], sorted_unique_coords[:, 1], sorted_unique_coords[:, 2]

    # Gracefully degrade the spline degree 'k' based on the number of available points.
    # k must be less than the number of points.
    # k=3: cubic (ideal), k=2: quadratic, k=1: linear.
    k = min(3, len(sorted_unique_coords) - 1)

    # Parameterize the path based on the cumulative distance between points.
    # This provides a better distribution for the spline parameter 'u'.
    diffs = np.diff(sorted_unique_coords, axis=0)
    segment_lengths = np.linalg.norm(diffs, axis=1)
    u = np.concatenate(([0], np.cumsum(segment_lengths)))
    
    # If the total path length is zero (all points are identical), return the original path.
    if u[-1] == 0:
        return waypoints
    
    u_normalized = u / u[-1]

    # Perform spline interpolation
    tck, _ = splprep([x, y, z], u=u_normalized, s=PlannerConstants.SMOOTHING_FACTOR, k=k)
    
    # Generate a new set of evenly spaced points along the smoothed spline.
    u_new_normalized = np.linspace(0, 1, PlannerConstants.SMOOTHED_PATH_NUM_POINTS)
    x_new, y_new, z_new = splev(u_new_normalized, tck)

    smoothed_path = [
        Waypoint(lat=lat, lon=lon, alt_ft=alt, airspeed_kts=AircraftProfile.GLIDE_SPEED_KTS)
        for lon, lat, alt in zip(x_new, y_new, z_new)
    ]

    # Enforce the start and end points to guarantee perfect alignment with the coarse path.
    if smoothed_path:
        smoothed_path[0] = original_start_wp
        smoothed_path[-1] = original_end_wp

    return smoothed_path
