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

# In path_planner/utils/smoothing.py

def smooth_path_3d(waypoints: List[Waypoint]) -> List[Waypoint]:
    """
    [AERODYNAMICALLY CORRECTED - V17]
    This version removes the artificial enforcement of start/end boundary
    conditions, which created visual "kinks" or jagged edges. The spline is
    now allowed to flow naturally from start to finish, relying on the
    SMOOTHING_FACTOR to control its adherence to the coarse path.
    """
    if len(waypoints) < 2:
        return waypoints

    coords = np.array([(wp.lon, wp.lat, wp.alt_ft) for wp in waypoints])
    unique_coords, indices = np.unique(coords, axis=0, return_index=True)
    
    if len(unique_coords) < 2:
        return waypoints

    sorted_unique_coords = unique_coords[np.argsort(indices)]
    x, y, z = sorted_unique_coords[:, 0], sorted_unique_coords[:, 1], sorted_unique_coords[:, 2]

    k = min(3, len(sorted_unique_coords) - 1)

    diffs = np.diff(sorted_unique_coords, axis=0)
    segment_lengths = np.linalg.norm(diffs, axis=1)
    u = np.concatenate(([0], np.cumsum(segment_lengths)))
    
    if u[-1] == 0:
        return waypoints
    
    u_normalized = u / u[-1]

    tck, _ = splprep([x, y, z], u=u_normalized, s=PlannerConstants.SMOOTHING_FACTOR, k=k)
    u_new_normalized = np.linspace(0, 1, PlannerConstants.SMOOTHED_PATH_NUM_POINTS)
    x_new, y_new, z_new = splev(u_new_normalized, tck)

    smoothed_path = [
        Waypoint(lat=lat, lon=lon, alt_ft=alt, airspeed_kts=AircraftProfile.GLIDE_SPEED_KTS)
        for lon, lat, alt in zip(x_new, y_new, z_new)
    ]

    # The blunt enforcement of boundary conditions has been removed.
    # The smoothing factor is the sole authority on the path's final shape.
    return smoothed_path