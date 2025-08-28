# shallnotcrash/path_planner/utils/touchdown.py
"""
[DEFINITIVE FIX - V16]
This version corrects the critical, root-cause bug in FAF calculation.
The FAF is now correctly calculated by moving from the threshold in the
OPPOSITE direction of the final approach heading, creating a geometrically
sane target for the A* search.
"""
import math
from typing import Optional, Tuple, List, Dict
from ..data_models import Waypoint, AircraftState
from ...landing_site.data_models import LandingSite
from ..constants import PlannerConstants, AircraftProfile
from .coordinates import destination_point, calculate_bearing, haversine_distance_nm
from .calculations import find_longest_axis

def _generate_runway_options(site: LandingSite) -> List[Dict]:
    """Generates landing options for a formal runway."""
    options = []
    if site.orientation_degrees is None or site.length_m is None:
        return []

    runway_orientation = site.orientation_degrees
    reciprocal_orientation = (runway_orientation + 180) % 360
    half_length_nm = (site.length_m / 2.0) / PlannerConstants.METERS_PER_NAUTICAL_MILE

    thresh1_lat, thresh1_lon = destination_point(site.lat, site.lon, runway_orientation, half_length_nm)
    thresh2_lat, thresh2_lon = destination_point(site.lat, site.lon, reciprocal_orientation, half_length_nm)

    options.append({'threshold': Waypoint(thresh1_lat, thresh1_lon, 0, 0), 'approach_hdg': reciprocal_orientation})
    options.append({'threshold': Waypoint(thresh2_lat, thresh2_lon, 0, 0), 'approach_hdg': runway_orientation})
    return options

def _generate_road_options(site: LandingSite) -> List[Dict]:
    """Generates landing options for roads or other long polygons."""
    options = []
    end1, end2, _ = find_longest_axis(site.polygon_coords)
    if end1 is None or end2 is None:
        return []

    options.append({'threshold': end1, 'approach_hdg': calculate_bearing(end2.lat, end2.lon, end1.lat, end1.lon)})
    options.append({'threshold': end2, 'approach_hdg': calculate_bearing(end1.lat, end1.lon, end2.lat, end2.lon)})
    return options

# In shallnotcrash/path_planner/utils/touchdown.py

def select_optimal_landing_approach(site: LandingSite, current_state: AircraftState) -> Optional[Tuple[Waypoint, Waypoint, float]]:
    """
    [SYSTEM INTEGRATION FIX - V17]
    Removes the orphaned reference to the flawed MAX_SAFE_GLIDESLOPE_DEG constant.
    The Final Approach Fix (FAF) altitude is now calculated exclusively using the
    standard, non-negotiable FINAL_APPROACH_GLIDESLOPE_DEG, resolving the
    AttributeError and aligning the module with the corrected physics model.
    """
    site_elevation_ft = site.elevation_m * PlannerConstants.METERS_TO_FEET if site.elevation_m is not None else 0.0
    
    options = []
    if site.site_type.upper() == "RUNWAY":
        options = _generate_runway_options(site)
    else:
        options = _generate_road_options(site)

    if not options:
        return None

    best_option = None
    min_dist_to_faf = float('inf')

    for option in options:
        threshold = option['threshold']
        threshold.alt_ft = site_elevation_ft
        approach_hdg = option['approach_hdg']

        bearing_to_faf = (approach_hdg + 180) % 360
        
        faf_lat, faf_lon = destination_point(
            threshold.lat, threshold.lon, bearing_to_faf, PlannerConstants.FINAL_APPROACH_FIX_DISTANCE_NM
        )
        
        # [SYSTEM FIX] The flawed logic comparing against a non-existent constant has been removed.
        # The FAF altitude is now correctly and consistently calculated using the standard 3-degree glideslope.
        faf_alt_ft = site_elevation_ft + (
            PlannerConstants.FEET_PER_NAUTICAL_MILE * 
            PlannerConstants.FINAL_APPROACH_FIX_DISTANCE_NM * 
            math.tan(math.radians(PlannerConstants.FINAL_APPROACH_GLIDESLOPE_DEG))
        )
        
        faf = Waypoint(lat=faf_lat, lon=faf_lon, alt_ft=faf_alt_ft, airspeed_kts=0)
        
        dist_to_faf = haversine_distance_nm(current_state.lat, current_state.lon, faf.lat, faf.lon)

        if dist_to_faf < min_dist_to_faf:
            min_dist_to_faf = dist_to_faf
            best_option = (faf, threshold, approach_hdg)
            
    return best_option
