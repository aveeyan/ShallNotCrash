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

# In shallnotcrash/path_planner/utils/touchdown.py

def _generate_runway_options(site: LandingSite) -> List[Dict]:
    """Generates landing options for a formal runway."""
    options = []
    if site.orientation_degrees is None or site.length_m is None:
        return []

    runway_orientation = site.orientation_degrees
    reciprocal_orientation = (runway_orientation + 180) % 360

    # [THE FIX] Use the correct, refactored constant for the conversion
    half_length_nm = (site.length_m / 2.0) * PlannerConstants.METERS_TO_NM

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
    [EFFICIENCY FIX - V18]
    Now considers multiple factors for runway end selection:
    1. Distance to FAF
    2. Heading alignment (reduces required turns)
    3. Altitude feasibility (can the aircraft reach the FAF?)
    4. Energy efficiency of the approach
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
    best_score = float('inf')  # Lower score is better

    for option in options:
        threshold = option['threshold']
        threshold.alt_ft = site_elevation_ft
        approach_hdg = option['approach_hdg']

        bearing_to_faf = (approach_hdg + 180) % 360
        
        faf_lat, faf_lon = destination_point(
            threshold.lat, threshold.lon, bearing_to_faf, PlannerConstants.FINAL_APPROACH_FIX_DISTANCE_NM
        )
        
        faf_alt_ft = site_elevation_ft + (
            PlannerConstants.FEET_PER_NAUTICAL_MILE * 
            PlannerConstants.FINAL_APPROACH_FIX_DISTANCE_NM * 
            math.tan(math.radians(PlannerConstants.FINAL_APPROACH_GLIDESLOPE_DEG))
        )
        
        faf = Waypoint(lat=faf_lat, lon=faf_lon, alt_ft=faf_alt_ft, airspeed_kts=0)
        
        # Factor 1: Distance to FAF
        dist_to_faf = haversine_distance_nm(current_state.lat, current_state.lon, faf.lat, faf.lon)
        
        # Factor 2: Heading alignment (penalize large turns)
        current_bearing_to_faf = calculate_bearing(current_state.lat, current_state.lon, faf.lat, faf.lon)
        heading_diff = abs(current_state.heading_deg - current_bearing_to_faf)
        if heading_diff > 180:
            heading_diff = 360 - heading_diff
        heading_penalty = heading_diff / 180.0  # Normalized 0-1
        
        # Factor 3: Altitude feasibility
        altitude_needed = faf_alt_ft
        altitude_available = current_state.alt_ft
        if altitude_available > altitude_needed:
            altitude_surplus_ft = altitude_available - altitude_needed
            min_glide_distance_nm = (altitude_surplus_ft * AircraftProfile.GLIDE_RATIO) / PlannerConstants.FEET_PER_NAUTICAL_MILE
        else:
            altitude_deficit_ft = altitude_needed - altitude_available
            min_glide_distance_nm = -(altitude_deficit_ft * AircraftProfile.GLIDE_RATIO) / PlannerConstants.FEET_PER_NAUTICAL_MILE
        
        altitude_penalty = 0.0
        if min_glide_distance_nm < dist_to_faf:
            # Can't reach FAF with current altitude - heavy penalty
            altitude_penalty = 10.0
        elif altitude_available < altitude_needed:
            # Below required altitude - moderate penalty
            altitude_penalty = 2.0
            
        # Factor 4: Approach angle efficiency (prefer approaches that align with current trajectory)
        approach_bearing_from_current = calculate_bearing(current_state.lat, current_state.lon, threshold.lat, threshold.lon)
        approach_alignment = abs(current_state.heading_deg - approach_bearing_from_current)
        if approach_alignment > 180:
            approach_alignment = 360 - approach_alignment
        approach_penalty = approach_alignment / 180.0  # Normalized 0-1
        
        # Combine all factors into a single score
        # Distance is primary factor, others are weighted penalties
        score = (
            dist_to_faf +  # Primary: minimize distance
            heading_penalty * 2.0 +  # Secondary: minimize required turns
            altitude_penalty +  # Critical: ensure reachability
            approach_penalty * 0.5  # Tertiary: prefer aligned approaches
        )

        if score < best_score:
            best_score = score
            best_option = (faf, threshold, approach_hdg)
            
    return best_option
