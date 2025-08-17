# shallnotcrash/path_planner/utils/smoothing.py
"""
Smooths a raw path of waypoints using B-spline interpolation with
physically-based chordal length parameterization.
"""
import numpy as np
from scipy.interpolate import splprep, splev
from typing import List
from ..data_models import Waypoint
from ..constants import PlannerConstants, AircraftProfile

def smooth_path(waypoints: List[Waypoint]) -> List[Waypoint]:
    """
    Smooths a jagged A* path into a flyable curve using B-spline interpolation.
    This implementation uses cumulative chordal length for parameterization,
    providing a much more accurate and stable smoothing result.
    """
    if len(waypoints) < 4:
        # Path is too short for cubic B-spline interpolation.
        return waypoints

    coords = np.array([(wp.lat, wp.lon) for wp in waypoints])
    altitudes = np.array([wp.alt_ft for wp in waypoints])
    x, y = coords[:, 0], coords[:, 1]

    # --- [NEW ALGORITHM] ---
    # 1. Calculate the distance between each consecutive point.
    diffs = np.diff(coords, axis=0)
    segment_lengths = np.linalg.norm(diffs, axis=1)
    
    # 2. Create the parameter vector 'u' based on cumulative chord length.
    # This ensures the parameterization is proportional to the distance along the path.
    u = np.concatenate(([0], np.cumsum(segment_lengths)))
    u = u / u[-1] # Normalize u to the range [0, 1]

    # 3. Perform B-spline fitting with the new parameterization.
    # The smoothing factor 's' is now an absolute value, not a multiplier.
    tck, _ = splprep([x, y], u=u, s=PlannerConstants.SMOOTHING_FACTOR, k=3)
    
    # 4. Evaluate the smoothed spline at a high number of points.
    u_new = np.linspace(u.min(), u.max(), PlannerConstants.SMOOTHED_PATH_NUM_POINTS)
    x_new, y_new = splev(u_new, tck)
    
    # 5. Interpolate altitudes along the new path against the original parameterization.
    alt_new = np.interp(u_new, u, altitudes)
    airspeed = AircraftProfile.GLIDE_SPEED_KTS

    return [
        Waypoint(lat=lat, lon=lon, alt_ft=alt, airspeed_kts=airspeed)
        for lat, lon, alt in zip(x_new, y_new, alt_new)
    ]
