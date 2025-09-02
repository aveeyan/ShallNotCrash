# shallnotcrash/path_planner/utils/touchdown.py
"""
[FLEXIBLE APPROACH - V19]
This version creates a more flexible final approach that considers the aircraft's
current position and heading, allowing for gradual alignment instead of sharp turns.
"""
import math
from typing import Optional, Tuple, List, Dict
from ..data_models import Waypoint, AircraftState
from ...landing_site.data_models import LandingSite
from ..constants import PlannerConstants, AircraftProfile
from .coordinates import destination_point, calculate_bearing, haversine_distance_nm
from .calculations import find_longest_axis, calculate_turn_radius
from .flight_dynamics import get_minimum_turn_radius_nm

def _generate_runway_options(site: LandingSite) -> List[Dict]:
    """Generates landing options for a formal runway."""
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
    """Generates landing options for roads or other long polygons."""
    options = []
    end1, end2, _ = find_longest_axis(site.polygon_coords)
    if end1 is None or end2 is None:
        return []

    options.append({'threshold': end1, 'approach_hdg': calculate_bearing(end2.lat, end2.lon, end1.lat, end1.lon)})
    options.append({'threshold': end2, 'approach_hdg': calculate_bearing(end1.lat, end1.lon, end2.lat, end2.lon)})
    return options

# shallnotcrash/path_planner/utils/touchdown.py
# ... existing code ...

def _calculate_curved_approach(current_state: AircraftState, threshold: Waypoint, 
                             approach_hdg: float, site_elevation_ft: float) -> List[Waypoint]:
    """
    Creates a curved approach path that gradually aligns with the runway heading.
    """
    # Calculate current position relative to runway
    current_bearing_to_threshold = calculate_bearing(
        current_state.lat, current_state.lon,
        threshold.lat, threshold.lon
    )
    
    heading_diff = (approach_hdg - current_bearing_to_threshold + 180) % 360 - 180
    
    # If already well-aligned, use straight approach
    if abs(heading_diff) < 20:
        return _calculate_straight_approach(threshold, approach_hdg, site_elevation_ft)
    
    # Create curved approach with multiple waypoints
    approach_waypoints = []
    
    # Add intermediate turning points
    num_turn_points = max(2, min(5, int(abs(heading_diff) / 15)))
    
    for i in range(1, num_turn_points + 1):
        fraction = i / (num_turn_points + 1)
        turn_angle = heading_diff * fraction
        
        # Calculate position along the turn
        turn_distance = PlannerConstants.FINAL_APPROACH_FIX_DISTANCE_NM * (1.0 + fraction)
        turn_heading = (approach_hdg + 180 + turn_angle) % 360
        
        turn_lat, turn_lon = destination_point(
            threshold.lat, threshold.lon, turn_heading, turn_distance
        )
        
        # Calculate altitude for this point
        gs_angle_rad = math.radians(PlannerConstants.FINAL_APPROACH_GLIDESLOPE_DEG)
        turn_alt = site_elevation_ft + turn_distance * PlannerConstants.FEET_PER_NAUTICAL_MILE * math.tan(gs_angle_rad)
        
        turn_waypoint = Waypoint(turn_lat, turn_lon, turn_alt, AircraftProfile.GLIDE_SPEED_KTS)
        approach_waypoints.append(turn_waypoint)
    
    # Add FAF
    faf_lat, faf_lon = destination_point(
        threshold.lat, threshold.lon, 
        (approach_hdg + 180) % 360,
        PlannerConstants.FINAL_APPROACH_FIX_DISTANCE_NM
    )
    
    faf_alt_ft = site_elevation_ft + (
        PlannerConstants.FEET_PER_NAUTICAL_MILE * 
        PlannerConstants.FINAL_APPROACH_FIX_DISTANCE_NM * 
        math.tan(math.radians(PlannerConstants.FINAL_APPROACH_GLIDESLOPE_DEG))
    )
    
    faf = Waypoint(lat=faf_lat, lon=faf_lon, alt_ft=faf_alt_ft, airspeed_kts=AircraftProfile.GLIDE_SPEED_KTS)
    approach_waypoints.append(faf)
    
    # Add threshold
    threshold.alt_ft = site_elevation_ft
    threshold.airspeed_kts = AircraftProfile.GLIDE_SPEED_KTS
    approach_waypoints.append(threshold)
    
    # Reverse order so it goes from farthest to closest
    approach_waypoints.reverse()
    
    return approach_waypoints

def _calculate_straight_approach(threshold: Waypoint, approach_hdg: float, site_elevation_ft: float) -> List[Waypoint]:
    """Creates a straight approach path (for when already aligned)."""
    approach_waypoints = []
    
    # Final approach fix
    faf_lat, faf_lon = destination_point(
        threshold.lat, threshold.lon, 
        (approach_hdg + 180) % 360,
        PlannerConstants.FINAL_APPROACH_FIX_DISTANCE_NM
    )
    
    faf_alt_ft = site_elevation_ft + (
        PlannerConstants.FEET_PER_NAUTICAL_MILE * 
        PlannerConstants.FINAL_APPROACH_FIX_DISTANCE_NM * 
        math.tan(math.radians(PlannerConstants.FINAL_APPROACH_GLIDESLOPE_DEG))
    )
    
    faf = Waypoint(lat=faf_lat, lon=faf_lon, alt_ft=faf_alt_ft, airspeed_kts=AircraftProfile.GLIDE_SPEED_KTS)
    approach_waypoints.append(faf)
    
    # Threshold
    threshold.alt_ft = site_elevation_ft
    threshold.airspeed_kts = AircraftProfile.GLIDE_SPEED_KTS
    approach_waypoints.append(threshold)
    
    return approach_waypoints

def select_optimal_landing_approach(site: LandingSite, current_state: AircraftState) -> Optional[Tuple[Waypoint, Waypoint, float, List[Waypoint]]]:
    """
    [FLEXIBLE APPROACH - V19]
    Returns the optimal landing approach including intermediate waypoints for gradual alignment.
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
    best_score = float('inf')
    best_approach_waypoints = []

    for option in options:
        threshold = option['threshold']
        threshold.alt_ft = site_elevation_ft
        approach_hdg = option['approach_hdg']

        # Calculate approach waypoints (curved or straight based on alignment)
        approach_waypoints = _calculate_curved_approach(current_state, threshold, approach_hdg, site_elevation_ft)
        
        # Use the FAF from the approach waypoints
        faf = approach_waypoints[0]  # First waypoint is the FAF or turn start
        
        # Factor 1: Distance to first approach waypoint
        dist_to_approach = haversine_distance_nm(current_state.lat, current_state.lon, faf.lat, faf.lon)
        
        # Factor 2: Heading alignment
        current_bearing_to_faf = calculate_bearing(current_state.lat, current_state.lon, faf.lat, faf.lon)
        heading_diff = abs(current_state.heading_deg - current_bearing_to_faf)
        if heading_diff > 180:
            heading_diff = 360 - heading_diff
        heading_penalty = heading_diff / 180.0
        
        # Factor 3: Altitude feasibility
        altitude_needed = faf.alt_ft
        altitude_available = current_state.alt_ft
        altitude_penalty = 0.0
        
        if altitude_available < altitude_needed:
            altitude_deficit_ft = altitude_needed - altitude_available
            # Penalize approaches that require climbing
            altitude_penalty = altitude_deficit_ft / 1000.0
            
        # Factor 4: Approach smoothness (penalize approaches that require sharp turns)
        turn_severity = 0.0
        if len(approach_waypoints) > 2:
            # Check for sharp turns in the approach path
            for i in range(1, len(approach_waypoints) - 1):
                bearing1 = calculate_bearing(
                    approach_waypoints[i-1].lat, approach_waypoints[i-1].lon,
                    approach_waypoints[i].lat, approach_waypoints[i].lon
                )
                bearing2 = calculate_bearing(
                    approach_waypoints[i].lat, approach_waypoints[i].lon,
                    approach_waypoints[i+1].lat, approach_waypoints[i+1].lon
                )
                turn_angle = abs(bearing2 - bearing1)
                if turn_angle > 180:
                    turn_angle = 360 - turn_angle
                if turn_angle > 30:  # Penalize turns sharper than 30 degrees
                    turn_severity += (turn_angle - 30) / 10.0
        
        # Combine all factors
        score = (
            dist_to_approach +
            heading_penalty * 2.0 +
            altitude_penalty * 3.0 +
            turn_severity * 1.5
        )

        if score < best_score:
            best_score = score
            best_option = (faf, threshold, approach_hdg)
            best_approach_waypoints = approach_waypoints

    if best_option:
        # Return both the optimal approach and the waypoints for it
        return (*best_option, best_approach_waypoints)
    return None
