# shallnotcrash/path_planner/core.py
import logging
import math
from typing import List, Optional

from .data_models import AircraftState, Waypoint, FlightPath
from .utils.calculations import calculate_path_distance, calculate_turn_radius, get_line_intersection
from .utils.coordinates import haversine_distance_nm, calculate_bearing, destination_point
from .utils.flight_dynamics import generate_turn_arc
from .utils.touchdown import select_optimal_landing_approach
from .constants import PlannerConstants, AircraftProfile
from ..landing_site.data_models import LandingSite, SafetyReport

class PathPlanner:
    def __init__(self, terrain_analyzer):
        self.terrain_analyzer = terrain_analyzer
        logging.info("PathPlanner initialized with INTERCEPT path constructor.")

    def generate_path_to_site(self, aircraft_state: AircraftState, site: LandingSite) -> Optional[FlightPath]:
        approach_data = select_optimal_landing_approach(site, aircraft_state)
        if not approach_data:
            return self._generate_fallback_path(aircraft_state, site)

        faf_waypoint, threshold, approach_hdg, approach_waypoints = approach_data

        path_to_faf = self._construct_intercept_path(aircraft_state, faf_waypoint, approach_hdg)
        if not path_to_faf:
            return self._generate_fallback_path(aircraft_state, site)
        
        full_path_waypoints = path_to_faf + approach_waypoints[1:]

        total_distance = calculate_path_distance(full_path_waypoints)
        estimated_time = (total_distance / aircraft_state.airspeed_kts) * 60 if aircraft_state.airspeed_kts > 0 else 0
        
        return FlightPath(
            waypoints=full_path_waypoints, total_distance_nm=total_distance, estimated_time_min=estimated_time,
            emergency_profile="Course Intercept Glide Path", safety_report=site.safety_report
        )

    def _construct_intercept_path(self, start_state: AircraftState, faf: Waypoint, approach_hdg: float) -> Optional[List[Waypoint]]:
        final_course_bearing = calculate_bearing(faf.lat, faf.lon, faf.lat + 1, faf.lon + 1) # Approximation of the final approach course line
        final_course_bearing = approach_hdg
        
        # Determine the optimal intercept angle (45 degrees is standard)
        intercept_angle = 45.0
        heading_diff = (approach_hdg - start_state.heading_deg + 360) % 360
        intercept_bearing = (approach_hdg + intercept_angle) % 360 if heading_diff < 180 else (approach_hdg - intercept_angle + 360) % 360

        # Find the intersection point of the aircraft's intercept path and the final approach course
        intersection_coords = get_line_intersection(
            (start_state.lat, start_state.lon), intercept_bearing,
            (faf.lat, faf.lon), approach_hdg
        )
        if not intersection_coords: return None
        
        int_lat, int_lon = intersection_coords
        dist_to_intercept = haversine_distance_nm(start_state.lat, start_state.lon, int_lat, int_lon)
        
        # Ensure the intercept point is before the FAF
        if haversine_distance_nm(int_lat, int_lon, faf.lat, faf.lon) < 0.1 or dist_to_intercept > 20:
             # Fallback for complex cases: simple turn-and-glide to FAF
             return self._simple_turn_glide(start_state, faf)

        intercept_wp = Waypoint(lat=int_lat, lon=int_lon, alt_ft=0, airspeed_kts=start_state.airspeed_kts)
        
        # Generate the turn from the intercept point to the FAF
        state_at_intercept = AircraftState(lat=int_lat, lon=int_lon, alt_ft=0, heading_deg=intercept_bearing, airspeed_kts=start_state.airspeed_kts)
        turn_radius_nm = calculate_turn_radius(start_state.airspeed_kts)
        
        turn_direction = 'left' if heading_diff < 180 else 'right'
        turn_wps, _, _ = generate_turn_arc(state_at_intercept, approach_hdg, turn_radius_nm, turn_direction)
        
        path_2d = [intercept_wp] + turn_wps + [faf]
        path_3d = self._apply_descent_profile(path_2d, start_state, faf)
        
        return path_3d
    
    def _simple_turn_glide(self, start_state: AircraftState, faf: Waypoint) -> List[Waypoint]:
        """A robust fallback for when intercept geometry is complex."""
        turn_radius_nm = calculate_turn_radius(start_state.airspeed_kts)
        bearing_to_faf = calculate_bearing(start_state.lat, start_state.lon, faf.lat, faf.lon)
        heading_diff = bearing_to_faf - start_state.heading_deg
        if heading_diff > 180: heading_diff -= 360
        if heading_diff < -180: heading_diff += 360
        turn_direction = 'right' if heading_diff > 0 else 'left'
        turn_wps, _, _ = generate_turn_arc(start_state, bearing_to_faf, turn_radius_nm, turn_direction)
        path_2d = turn_wps + [faf]
        return self._apply_descent_profile(path_2d, start_state, faf)

    def _apply_descent_profile(self, waypoints_2d: List[Waypoint], start: AircraftState, end: Waypoint) -> List[Waypoint]:
        path_3d = []
        dist_traveled_nm = 0.0
        last_lat, last_lon = start.lat, start.lon
        for wp in waypoints_2d:
            segment_dist = haversine_distance_nm(last_lat, last_lon, wp.lat, wp.lon)
            dist_traveled_nm += segment_dist
            altitude_loss_ft = (dist_traveled_nm * PlannerConstants.FEET_PER_NAUTICAL_MILE) / AircraftProfile.GLIDE_RATIO
            new_altitude = start.alt_ft - altitude_loss_ft
            wp.alt_ft = max(new_altitude, end.alt_ft)
            path_3d.append(wp)
            last_lat, last_lon = wp.lat, wp.lon
        return path_3d

    def _generate_fallback_path(self, aircraft_state: AircraftState, site: LandingSite) -> Optional[FlightPath]:
        start_wp = Waypoint(lat=aircraft_state.lat, lon=aircraft_state.lon, alt_ft=aircraft_state.alt_ft, airspeed_kts=aircraft_state.airspeed_kts)
        end_wp = Waypoint(lat=site.lat, lon=site.lon, alt_ft=site.elevation_m * PlannerConstants.METERS_TO_FEET, airspeed_kts=AircraftProfile.GLIDE_SPEED_KTS)
        total_distance = haversine_distance_nm(start_wp.lat, start_wp.lon, end_wp.lat, end_wp.lon)
        estimated_time = (total_distance / aircraft_state.airspeed_kts) * 60 if aircraft_state.airspeed_kts > 0 else 0
        fallback_report = SafetyReport(is_safe=True, risk_level="HIGH", safety_score=50, obstacle_count=99, closest_civilian_distance_km=999)
        return FlightPath(waypoints=[start_wp, end_wp], total_distance_nm=total_distance, 
                          estimated_time_min=estimated_time, emergency_profile="Direct Fallback Path", 
                          safety_report=fallback_report)
    