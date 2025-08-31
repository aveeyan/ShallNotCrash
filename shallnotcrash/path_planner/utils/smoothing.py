# shallnotcrash/path_planner/utils/smoothing.py
import numpy as np
from scipy.interpolate import splprep, splev
from typing import List
from ..data_models import Waypoint
from ..constants import PlannerConstants, AircraftProfile

def _chaikin_pre_smooth(points: np.ndarray, iterations: int = 2) -> np.ndarray:
    if len(points) < 2: return points
    for _ in range(iterations):
        new_points = [points[0]]
        for i in range(len(points) - 1):
            p1, p2 = points[i], points[i+1]
            q, r = p1 * 0.75 + p2 * 0.25, p1 * 0.25 + p2 * 0.75
            new_points.extend([q, r])
        new_points.append(points[-1])
        points = np.array(new_points)
    return points

def smooth_path_3d(waypoints: List[Waypoint]) -> List[Waypoint]:
    if len(waypoints) < 3: return waypoints
    coords = np.array([(wp.lon, wp.lat, wp.alt_ft) for wp in waypoints])
    unique_coords, indices = np.unique(coords, axis=0, return_index=True)
    if len(unique_coords) < 3: return waypoints
    control_points = _chaikin_pre_smooth(unique_coords[np.argsort(indices)])
    x, y, z = control_points[:, 0], control_points[:, 1], control_points[:, 2]
    diffs = np.diff(control_points, axis=0)
    u = np.concatenate(([0], np.cumsum(np.linalg.norm(diffs, axis=1))))
    if u[-1] == 0: return waypoints
    k = min(3, len(x) - 1)
    tck, _ = splprep([x, y, z], u=u, s=0, k=k)
    u_new = np.linspace(0, u[-1], PlannerConstants.SMOOTHED_PATH_NUM_POINTS)
    x_new, y_new, z_new = splev(u_new, tck)
    return [
        Waypoint(lat=lat, lon=lon, alt_ft=alt, airspeed_kts=AircraftProfile.GLIDE_SPEED_KTS)
        for lon, lat, alt in zip(x_new, y_new, z_new)
    ]
