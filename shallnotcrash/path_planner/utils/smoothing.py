# shallnotcrash/path_planner/utils/smoothing.py
"""
Provides path smoothing capabilities using B-Spline interpolation.
This converts the jagged A* path into a flyable trajectory.
"""
from typing import List
import numpy as np
from scipy.interpolate import splprep, splev
from ..data_models import Waypoint

class PathSmoother:
    """A class to handle the smoothing of a flight path."""

    @staticmethod
    def smooth_path(waypoints: List[Waypoint], smoothness_factor: float = 0.5, num_points: int = 100) -> List[Waypoint]:
        """
        Smooths a list of waypoints using B-spline interpolation.

        :param waypoints: The raw list of waypoints from the A* search.
        :param smoothness_factor: Controls the smoothness of the spline. 0 is a line through all points.
        :param num_points: The number of points to generate for the final smooth path.
        :return: A new, denser list of waypoints representing the smooth path.
        """
        if len(waypoints) < 4:
            # Cannot create a cubic spline with fewer than 4 points.
            print("SMOOTHER WARNING: Path too short for smoothing. Returning original path.")
            return waypoints

        try:
            # Unpack waypoint data into separate lists for processing
            lats = [wp.lat for wp in waypoints]
            lons = [wp.lon for wp in waypoints]
            alts = [wp.alt_ft for wp in waypoints]
            airspeeds = [wp.airspeed_kts for wp in waypoints]

            # The B-spline needs to be parameterized. We stack our 3D coordinates.
            coords = np.vstack((lats, lons, alts))

            # Generate the B-spline representation of the path.
            # splprep finds the parameterization of the curve.
            # k=3 specifies a cubic spline, which is standard for smooth curves.
            # s is the smoothness factor.
            tck, u = splprep(coords, s=smoothness_factor, k=3)

            # Evaluate the spline at a high number of points to create the smooth path
            u_new = np.linspace(u.min(), u.max(), num_points)
            new_lats, new_lons, new_alts = splev(u_new, tck)

            # Airspeed can be linearly interpolated for the new points
            new_airspeeds = np.interp(u_new, u, airspeeds)

            # Assemble the new list of smooth waypoints
            smooth_waypoints = []
            for i in range(len(new_lats)):
                smooth_waypoints.append(
                    Waypoint(
                        lat=new_lats[i],
                        lon=new_lons[i],
                        alt_ft=new_alts[i],
                        airspeed_kts=new_airspeeds[i]
                    )
                )
            
            print(f"SMOOTHER: Path successfully smoothed from {len(waypoints)} to {len(smooth_waypoints)} waypoints.")
            return smooth_waypoints

        except Exception as e:
            print(f"SMOOTHER CRITICAL ERROR: Failed to smooth path - {e}. Returning original path.")
            return waypoints