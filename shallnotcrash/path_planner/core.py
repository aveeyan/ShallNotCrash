# shallnotcrash/path_planner/core.py
import logging
import math
from typing import List, Optional

from .data_models import AircraftState, Waypoint, FlightPath
from .utils.calculations import calculate_path_distance, calculate_turn_radius
from .utils.coordinates import haversine_distance_nm, calculate_bearing
# [MODIFIED] Import the new geometric turn function
from .utils.flight_dynamics import generate_turn_arc
from .utils.smoothing import smooth_path_3d
from .utils.touchdown import select_optimal_landing_approach
from .constants import PlannerConstants, AircraftProfile
from ..landing_site.data_models import LandingSite, SafetyReport

class PathPlanner:
    def __init__(self, terrain_analyzer): # terrain_analyzer is kept for future obstacle checks
        self.terrain_analyzer = terrain_analyzer
        logging.info("PathPlanner initialized with GEOMETRIC path constructor.")

    def generate_path_to_site(self, aircraft_state: AircraftState, site: LandingSite) -> Optional[FlightPath]:
        logging.info(f"Constructing geometric path to {site.site_type} at ({site.lat:.4f}, {site.lon:.4f})")
        
        approach_data = select_optimal_landing_approach(site, aircraft_state)
        if not approach_data:
            logging.warning("No valid approach could be calculated for the site.")
            return self._generate_fallback_path(aircraft_state, site)

        faf_waypoint, _, _, approach_waypoints = approach_data

        path_to_faf = self._construct_geometric_path(aircraft_state, faf_waypoint)
        if not path_to_faf:
            logging.warning("Geometric path construction to FAF failed.")
            return self._generate_fallback_path(aircraft_state, site)
        
        # [FIX] The final path is a simple, clean combination of the two segments.
        # The first waypoint of the approach is the FAF itself, so we skip it to avoid duplication.
        full_path_waypoints = path_to_faf + approach_waypoints[1:]
        
        # [FIX] Smoothing is removed. The geometric path is clean enough for the autopilot to follow.
        # smoothed_path = smooth_path_3d(full_path_waypoints)

        total_distance = calculate_path_distance(full_path_waypoints)
        estimated_time = (total_distance / aircraft_state.airspeed_kts) * 60 if aircraft_state.airspeed_kts > 0 else 0
        
        return FlightPath(
            waypoints=full_path_waypoints, # Use the direct waypoints
            total_distance_nm=total_distance, 
            estimated_time_min=estimated_time,
            emergency_profile="Geometric Glide Path", 
            safety_report=site.safety_report
        )
    
    def _construct_geometric_path(self, start_state: AircraftState, faf: Waypoint) -> Optional[List[Waypoint]]:
        """
        Constructs a 3D path using a Turn-Glide-Align methodology.
        """
        turn_radius_nm = calculate_turn_radius(start_state.airspeed_kts)
        bearing_to_faf = calculate_bearing(start_state.lat, start_state.lon, faf.lat, faf.lon)

        # Generate the initial turn arc to align with the FAF
        turn_wps, state_after_turn, turn_dist = generate_turn_arc(start_state, bearing_to_faf, turn_radius_nm, 'right') # Assume right turn for now
        
        # The straight glide segment is from the end of the turn to the FAF
        straight_dist = haversine_distance_nm(state_after_turn.lat, state_after_turn.lon, faf.lat, faf.lon)
        straight_wps = [faf] # The FAF is the end of the straight segment

        path_2d = turn_wps + straight_wps
        total_dist_to_faf = turn_dist + straight_dist
        
        # Apply the 3D glide slope to the 2D path
        alt_to_lose = start_state.alt_ft - faf.alt_ft
        if alt_to_lose < 0 and abs(alt_to_lose) > 500: # Check if we are significantly below the glide path
             logging.warning(f"Aircraft is {abs(alt_to_lose):.0f} ft below the required altitude for FAF. Path may be impossible.")
        
        path_3d = self._apply_descent_profile(path_2d, start_state, faf, total_dist_to_faf)
        
        return path_3d

    def _apply_descent_profile(self, waypoints_2d: List[Waypoint], start: AircraftState, end: Waypoint, total_distance: float) -> List[Waypoint]:
        """Distributes altitude loss linearly across a series of waypoints."""
        path_3d = [start] + waypoints_2d
        
        initial_alt = start.alt_ft
        final_alt = end.alt_ft
        alt_to_lose = initial_alt - final_alt
        
        dist_so_far = 0.0
        for i in range(1, len(path_3d)):
            dist_segment = haversine_distance_nm(path_3d[i-1].lat, path_3d[i-1].lon, path_3d[i].lat, path_3d[i].lon)
            dist_so_far += dist_segment
            
            fraction_of_path = dist_so_far / total_distance if total_distance > 0 else 0
            path_3d[i].alt_ft = initial_alt - (alt_to_lose * fraction_of_path)
        
        return path_3d[1:] # Return the path excluding the initial aircraft state

    def _generate_fallback_path(self, aircraft_state: AircraftState, site: LandingSite) -> Optional[FlightPath]:
        """Generate a simple direct path when advanced planning fails."""
        logging.warning("Using fallback direct path")
        start_wp = Waypoint(lat=aircraft_state.lat, lon=aircraft_state.lon, alt_ft=aircraft_state.alt_ft, airspeed_kts=aircraft_state.airspeed_kts)
        end_wp = Waypoint(lat=site.lat, lon=site.lon, alt_ft=site.elevation_m * PlannerConstants.METERS_TO_FEET, airspeed_kts=AircraftProfile.GLIDE_SPEED_KTS)
        
        total_distance = haversine_distance_nm(start_wp.lat, start_wp.lon, end_wp.lat, end_wp.lon)
        estimated_time = (total_distance / aircraft_state.airspeed_kts) * 60 if aircraft_state.airspeed_kts > 0 else 0
        
        fallback_report = SafetyReport(is_safe=True, risk_level="HIGH", safety_score=50, obstacle_count=99, closest_civilian_distance_km=999)
        
        return FlightPath(waypoints=[start_wp, end_wp], total_distance_nm=total_distance, 
                          estimated_time_min=estimated_time, emergency_profile="Direct Fallback Path", 
                          safety_report=fallback_report)
    