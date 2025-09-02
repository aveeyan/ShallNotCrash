# shallnotcrash/path_planner/utils/touchdown.py
"""
[STATE-AWARE - V22]
This final version adds an "On Final" check to handle scenarios where the
aircraft is already close and aligned with the runway, preventing unnecessary
"go-around" paths.
"""
import math
import logging
from typing import Optional, Tuple, List, Dict
import numpy as np

from ..data_models import Waypoint, AircraftState
from ...landing_site.data_models import LandingSite
from ..constants import PlannerConstants, AircraftProfile
from .coordinates import destination_point, calculate_bearing, haversine_distance_nm
from .calculations import find_longest_axis

# ... (_generate_runway_options and _generate_road_options are unchanged) ...
def _generate_runway_options(site: LandingSite) -> List[Dict]:
    options = []
    if site.orientation_degrees is None or site.length_m is None:
        return []
    runway_orientation = site.orientation_degrees
    reciprocal_orientation = (runway_orientation + 180) % 360
    half_length_nm = (site.length_m / 2.0) * PlannerConstants.METERS_TO_NM
    thresh1_lat, thresh1_lon = destination_point(site.lat, site.lon, runway_orientation, half_length_nm)
    thresh2_lat, thresh2_lon = destination_point(site.lat, site.lon, reciprocal_orientation, half_length_nm)
    options.append({'threshold': Waypoint(thresh1_lat, thresh1_lon, 0, 0), 'approach_hdg': reciprocal_orientation})
    options.append({'threshold': Waypoint(thresh2_lat, thresh2_lon, 0, 0), 'approach_hdg': runway_orientation})
    return options

def _generate_road_options(site: LandingSite) -> List[Dict]:
    options = []
    end1, end2, _ = find_longest_axis(site.polygon_coords)
    if end1 is None or end2 is None:
        return []
    options.append({'threshold': end1, 'approach_hdg': calculate_bearing(end2.lat, end2.lon, end1.lat, end1.lon)})
    options.append({'threshold': end2, 'approach_hdg': calculate_bearing(end1.lat, end1.lon, end2.lat, end2.lon)})
    return options

def _calculate_straight_approach(threshold: Waypoint, approach_hdg: float, site_elevation_ft: float, current_state: AircraftState) -> Tuple[List[Waypoint], float]:
    alt_to_lose_ft = current_state.alt_ft - site_elevation_ft
    if alt_to_lose_ft <= 50: # If very low, use minimum distance
        dynamic_faf_dist_nm = 0.3
    else:
        ideal_dist_ft = alt_to_lose_ft / math.tan(math.radians(PlannerConstants.FINAL_APPROACH_GLIDESLOPE_DEG))
        ideal_dist_nm = ideal_dist_ft / PlannerConstants.FEET_PER_NAUTICAL_MILE
        dynamic_faf_dist_nm = np.clip(ideal_dist_nm, 0.3, 2.0)

    faf_lat, faf_lon = destination_point(
        threshold.lat, threshold.lon, (approach_hdg + 180) % 360, dynamic_faf_dist_nm
    )
    faf_alt_ft = site_elevation_ft + (
        PlannerConstants.FEET_PER_NAUTICAL_MILE * dynamic_faf_dist_nm * math.tan(math.radians(PlannerConstants.FINAL_APPROACH_GLIDESLOPE_DEG))
    )
    faf = Waypoint(lat=faf_lat, lon=faf_lon, alt_ft=faf_alt_ft, airspeed_kts=AircraftProfile.GLIDE_SPEED_KTS)
    
    threshold.alt_ft = site_elevation_ft
    threshold.airspeed_kts = AircraftProfile.GLIDE_SPEED_KTS
    
    return [faf, threshold], dynamic_faf_dist_nm

def select_optimal_landing_approach(site: LandingSite, current_state: AircraftState) -> Optional[Tuple[Waypoint, Waypoint, float, List[Waypoint]]]:
    site_elevation_ft = site.elevation_m * PlannerConstants.METERS_TO_FEET if site.elevation_m is not None else 0.0
    
    options = _generate_runway_options(site) or _generate_road_options(site)
    if not options: return None

    best_option = None
    best_score = float('inf')
    best_approach_waypoints = []

    for option in options:
        threshold = option['threshold']
        approach_hdg = option['approach_hdg']

        # [FINAL LOGIC] Add a special check for when the aircraft is already on final approach.
        dist_to_threshold_nm = haversine_distance_nm(current_state.lat, current_state.lon, threshold.lat, threshold.lon)
        
        # If we are very close and aligned, override normal planning with a direct path.
        if dist_to_threshold_nm < 0.4:
            bearing_to_threshold = calculate_bearing(current_state.lat, current_state.lon, threshold.lat, threshold.lon)
            
            # Check if aircraft is pointing towards the threshold
            heading_vs_bearing_diff = abs(current_state.heading_deg - bearing_to_threshold)
            if heading_vs_bearing_diff > 180: heading_vs_bearing_diff = 360 - heading_vs_bearing_diff
            
            # Check if aircraft is aligned with the runway itself
            alignment_diff = abs(current_state.heading_deg - approach_hdg)
            if alignment_diff > 180: alignment_diff = 360 - alignment_diff

            if heading_vs_bearing_diff < 25 and alignment_diff < 25:
                logging.info("Aircraft is on final approach. Generating direct path to threshold.")
                # The path starts from the aircraft's current position.
                start_waypoint = Waypoint(
                    lat=current_state.lat, lon=current_state.lon, 
                    alt_ft=current_state.alt_ft, airspeed_kts=current_state.airspeed_kts
                )
                threshold.alt_ft = site_elevation_ft
                threshold.airspeed_kts = AircraftProfile.GLIDE_SPEED_KTS
                # Return this simple path immediately as the best option.
                return (start_waypoint, threshold, approach_hdg, [start_waypoint, threshold])
        
        # --- If not on final, proceed with normal FAF-based planning ---
        approach_waypoints, faf_dist_nm = _calculate_straight_approach(threshold, approach_hdg, site_elevation_ft, current_state)
        faf = approach_waypoints[0]
        
        dist_to_faf = haversine_distance_nm(current_state.lat, current_state.lon, faf.lat, faf.lon)
        total_distance_flown = dist_to_faf + faf_dist_nm
        
        bearing_to_faf = calculate_bearing(current_state.lat, current_state.lon, faf.lat, faf.lon)
        heading_diff = abs(current_state.heading_deg - bearing_to_faf)
        if heading_diff > 180: heading_diff = 360 - heading_diff
        heading_penalty = (heading_diff / 180.0) * 3.0
        
        min_alt_required = faf.alt_ft + (dist_to_faf * PlannerConstants.FEET_PER_NAUTICAL_MILE) / AircraftProfile.GLIDE_RATIO
        altitude_penalty = 0.0
        if current_state.alt_ft < min_alt_required:
            altitude_penalty = (min_alt_required - current_state.alt_ft) / 100.0

        score = total_distance_flown + heading_penalty + altitude_penalty

        if score < best_score:
            best_score = score
            best_option = (faf, threshold, approach_hdg)
            best_approach_waypoints = approach_waypoints

    if best_option:
        return (*best_option, best_approach_waypoints)
    return None
