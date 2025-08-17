# shallnotcrash/path_planner/utils/touchdown.py
"""
Handles the selection of the optimal touchdown point and Final Approach Fix (FAF).
"""
import math
from typing import Optional, Tuple
from ..data_models import Waypoint
from ...landing_site.data_models import LandingSite
from ..constants import PlannerConstants, AircraftProfile
from .coordinates import destination_point

def get_landing_sequence(site: LandingSite, wind_heading_deg: float) -> Optional[Tuple[Waypoint, Waypoint]]:
    """
    Calculates the optimal runway threshold and its FAF based on wind.
    """
    site_elevation_ft = site.elevation_m * PlannerConstants.METERS_TO_FEET if site.elevation_m is not None else 0.0
    glide_speed = AircraftProfile.GLIDE_SPEED_KTS

    if site.site_type != "RUNWAY" or site.orientation_degrees is None or site.length_m is None:
        center_point = Waypoint(lat=site.lat, lon=site.lon, alt_ft=site_elevation_ft, airspeed_kts=glide_speed)
        return (center_point, center_point)

    runway_orientation = site.orientation_degrees
    reciprocal_orientation = (runway_orientation + 180) % 360
    half_length_nm = (site.length_m / 2.0) / PlannerConstants.METERS_PER_NAUTICAL_MILE
    
    lat1, lon1 = destination_point(site.lat, site.lon, runway_orientation, half_length_nm)
    lat2, lon2 = destination_point(site.lat, site.lon, reciprocal_orientation, half_length_nm)

    wind_diff1 = abs(((reciprocal_orientation - wind_heading_deg + 180) % 360) - 180)
    wind_diff2 = abs(((runway_orientation - wind_heading_deg + 180) % 360) - 180)

    if wind_diff1 <= wind_diff2:
        best_lat, best_lon, approach_hdg = lat1, lon1, reciprocal_orientation
    else:
        best_lat, best_lon, approach_hdg = lat2, lon2, runway_orientation

    threshold = Waypoint(lat=best_lat, lon=best_lon, alt_ft=site_elevation_ft, airspeed_kts=glide_speed, notes=f"THRESHOLD_HDG_{approach_hdg:.0f}")

    faf_bearing = (approach_hdg - 180) % 360
    faf_lat, faf_lon = destination_point(threshold.lat, threshold.lon, faf_bearing, PlannerConstants.FINAL_APPROACH_FIX_DISTANCE_NM)
    alt_gain_ft = math.tan(math.radians(PlannerConstants.FINAL_APPROACH_GLIDESLOPE_DEG)) * PlannerConstants.FINAL_APPROACH_FIX_DISTANCE_NM * PlannerConstants.FEET_PER_NAUTICAL_MILE
    faf_alt_ft = site_elevation_ft + alt_gain_ft

    final_approach_fix = Waypoint(lat=faf_lat, lon=faf_lon, alt_ft=faf_alt_ft, airspeed_kts=glide_speed, notes=f"FAF_FOR_THR_{approach_hdg:.0f}")
    
    # --- [FIX] Removed the stray backslash at the end of the line ---
    return (final_approach_fix, threshold)
