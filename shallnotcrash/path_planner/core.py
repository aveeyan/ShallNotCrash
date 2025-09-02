# shallnotcrash/path_planner/core.py
import logging
import math
import heapq
from collections import defaultdict
from typing import List, Optional, Dict, Tuple

from .data_models import AircraftState, Waypoint, FlightPath
from .utils.calculations import calculate_path_distance
from .utils.coordinates import haversine_distance_nm, calculate_bearing, destination_point
from .utils.cost_functions import calculate_move_cost
from .utils.flight_dynamics import get_reachable_states
from .utils.smoothing import smooth_path_3d
from .utils.touchdown import select_optimal_landing_approach
from .constants import PlannerConstants, AircraftProfile
from ..landing_site.data_models import LandingSite, SafetyReport
from ..landing_site.terrain_analyzer import TerrainAnalyzer

class PathPlanner:
    def __init__(self, terrain_analyzer: TerrainAnalyzer):
        self.terrain_analyzer = terrain_analyzer
        
        # No caching - always plan fresh paths
        self._last_planning_result = None
        self._last_aircraft_state = None
        self._last_site_id = None
        
        logging.info("PathPlanner initialized with dynamic path planning.")

    def generate_path_to_site(self, aircraft_state: AircraftState, site: LandingSite) -> Optional[FlightPath]:
        """Generate a fresh path to the landing site based on current position."""
        logging.info(f"Generating fresh path to {site.site_type} at ({site.lat:.4f}, {site.lon:.4f})")
        
        # Always calculate new approach based on current position
        approach_data = select_optimal_landing_approach(site, aircraft_state)
        if not approach_data:
            logging.warning("No valid approach found for current position")
            return self._generate_fallback_path(aircraft_state, site)
            
        # Handle both return formats (3 or 4 values)
        if len(approach_data) == 3:
            faf_waypoint, threshold_waypoint, approach_heading = approach_data
            approach_waypoints = None
        else:
            faf_waypoint, threshold_waypoint, approach_heading, approach_waypoints = approach_data
        
        # Use approach waypoints if available for smoother paths
        if approach_waypoints and len(approach_waypoints) > 1:
            logging.info(f"Using {len(approach_waypoints)} approach waypoints")
            final_waypoints = self._plan_to_approach_path(aircraft_state, approach_waypoints, approach_heading)
        else:
            logging.info("Planning directly to FAF")
            final_waypoints = self._plan_to_faf(aircraft_state, faf_waypoint, approach_heading, threshold_waypoint)
        
        if not final_waypoints:
            logging.warning("Path planning failed, using fallback")
            return self._generate_fallback_path(aircraft_state, site)
            
        total_distance = calculate_path_distance(final_waypoints)
        estimated_time = (total_distance / aircraft_state.airspeed_kts) * 60 if aircraft_state.airspeed_kts > 0 else 0
        
        return FlightPath(
            waypoints=final_waypoints,
            total_distance_nm=total_distance,
            estimated_time_min=estimated_time,
            emergency_profile="Dynamic Glide Path",
            safety_report=SafetyReport(is_safe=True, risk_level="LOW", safety_score=90, obstacle_count=0, closest_civilian_distance_km=999.0)
        )

    def _plan_to_approach_path(self, aircraft_state: AircraftState, approach_waypoints: List[Waypoint], approach_heading: float) -> Optional[List[Waypoint]]:
        """Plan path to join the approach waypoints at the optimal point."""
        # Find the best point to join the approach path
        best_join_index = self._find_best_join_point(aircraft_state, approach_waypoints)
        
        if best_join_index == 0:
            # Join at the beginning - plan to first waypoint
            path_to_join = self._a_star_search_dynamic(aircraft_state, approach_waypoints[0], approach_heading)
            if not path_to_join:
                return None
            return path_to_join + approach_waypoints[1:]
        else:
            # Join in the middle - plan to that point and take remaining waypoints
            join_waypoint = approach_waypoints[best_join_index]
            path_to_join = self._a_star_search_dynamic(aircraft_state, join_waypoint, approach_heading)
            if not path_to_join:
                return None
            return path_to_join + approach_waypoints[best_join_index + 1:]

    def _find_best_join_point(self, aircraft_state: AircraftState, approach_waypoints: List[Waypoint]) -> int:
        """Find the optimal point to join the approach path based on current position."""
        best_index = 0
        best_score = float('inf')
        
        for i, waypoint in enumerate(approach_waypoints):
            distance = haversine_distance_nm(aircraft_state.lat, aircraft_state.lon, waypoint.lat, waypoint.lon)
            # Prefer joining later in the approach if possible
            join_score = distance * (1.0 + i * 0.1)  # Later points get slight preference
            
            if join_score < best_score:
                best_score = join_score
                best_index = i
                
        return best_index

    def _plan_to_faf(self, aircraft_state: AircraftState, faf_waypoint: Waypoint, approach_heading: float, threshold_waypoint: Waypoint) -> Optional[List[Waypoint]]:
        """Plan path to FAF and then to threshold."""
        path_to_faf = self._a_star_search_dynamic(aircraft_state, faf_waypoint, approach_heading)
        if not path_to_faf:
            return None
            
        smoothed_path = smooth_path_3d(path_to_faf, aggressive=False)
        return smoothed_path + [threshold_waypoint]

    def _a_star_search_dynamic(self, start: AircraftState, goal: Waypoint, target_heading: float) -> Optional[List[Waypoint]]:
        """Dynamic A* search that adapts to the current situation."""
        open_set, count = [], 0
        heapq.heappush(open_set, (0, count, start))
        came_from: Dict[AircraftState, AircraftState] = {}
        g_score = defaultdict(lambda: float('inf'))
        g_score[start] = 0
        iterations = 0
        
        max_iterations = 25000  # Reasonable limit for most scenarios
        
        while open_set and iterations < max_iterations:
            iterations += 1
            current_f_score, _, current = heapq.heappop(open_set)
            
            if self._is_goal_reached(current, goal):
                logging.info(f"A* found path in {iterations} iterations")
                return self._reconstruct_path(came_from, current)
            
            distance_to_goal = haversine_distance_nm(current.lat, current.lon, goal.lat, goal.lon)
            
            for next_state, turn in get_reachable_states(current, distance_to_goal):
                dist = haversine_distance_nm(current.lat, current.lon, next_state.lat, next_state.lon)
                alt_surplus = next_state.alt_ft - self._calculate_ideal_glide_altitude(next_state, goal)
                
                tentative_g = g_score[current] + self._calculate_dynamic_cost(
                    dist, turn, alt_surplus, next_state.heading_deg, target_heading, 
                    current, goal, distance_to_goal
                )
                
                if tentative_g < g_score[next_state]:
                    came_from[next_state] = current
                    g_score[next_state] = tentative_g
                    f_score = tentative_g + self._dynamic_heuristic(next_state, goal, target_heading, distance_to_goal)
                    count += 1
                    heapq.heappush(open_set, (f_score, count, next_state))
        
        logging.warning(f"A* search failed after {iterations} iterations")
        return None

    def _calculate_dynamic_cost(self, distance_nm: float, turn_angle_deg: float, altitude_surplus_ft: float,
                              current_heading_deg: float, target_heading: float,
                              current_state: AircraftState, goal: Waypoint, distance_to_goal: float) -> float:
        """Dynamic cost calculation that adapts based on distance to goal."""
        base_cost = calculate_move_cost(distance_nm, turn_angle_deg, altitude_surplus_ft)
        
        # Only consider heading alignment when reasonably close to goal
        if distance_to_goal < 20.0:
            heading_diff = abs(current_heading_deg - target_heading)
            if heading_diff > 180:
                heading_diff = 360 - heading_diff
            
            # Gradually increase heading alignment importance as we approach
            alignment_factor = max(0, 1.0 - (distance_to_goal / 20.0))
            heading_penalty = (heading_diff / 180.0) * alignment_factor * 1.5
            
            return base_cost + heading_penalty
        
        return base_cost

    def _dynamic_heuristic(self, state: AircraftState, goal: Waypoint, target_heading: float, distance_to_goal: float) -> float:
        """Heuristic that balances distance and heading alignment."""
        # Base distance heuristic
        base_heuristic = distance_to_goal
        
        # Add heading alignment component when close
        if distance_to_goal < 25.0:
            current_bearing = calculate_bearing(state.lat, state.lon, goal.lat, goal.lon)
            heading_diff = abs(current_bearing - target_heading)
            if heading_diff > 180:
                heading_diff = 360 - heading_diff
            
            alignment_penalty = (heading_diff / 180.0) * (1.0 - (distance_to_goal / 25.0)) * 2.0
            return base_heuristic + alignment_penalty
        
        return base_heuristic

    def _generate_fallback_path(self, aircraft_state: AircraftState, site: LandingSite) -> Optional[FlightPath]:
        """Generate a simple direct path when advanced planning fails."""
        logging.warning("Using fallback direct path")
        
        site_altitude = site.elevation_m * PlannerConstants.METERS_TO_FEET if site.elevation_m else 0
        goal_waypoint = Waypoint(
            lat=site.lat, lon=site.lon, alt_ft=site_altitude,
            airspeed_kts=AircraftProfile.GLIDE_SPEED_KTS
        )
        
        direct_path = []
        current_lat, current_lon = aircraft_state.lat, aircraft_state.lon
        current_alt = aircraft_state.alt_ft
        
        distance_to_goal = haversine_distance_nm(current_lat, current_lon, site.lat, site.lon)
        altitude_difference = current_alt - site_altitude
        
        # Check if we have enough altitude
        required_glide_ratio = distance_to_goal * PlannerConstants.FEET_PER_NAUTICAL_MILE / altitude_difference
        if required_glide_ratio > AircraftProfile.GLIDE_RATIO:
            logging.error("Not enough altitude for fallback path")
            return None
        
        # Create simple direct path with 5 segments
        num_segments = 5
        for i in range(num_segments + 1):
            fraction = i / num_segments
            lat = current_lat + (site.lat - current_lat) * fraction
            lon = current_lon + (site.lon - current_lon) * fraction
            alt = current_alt - altitude_difference * fraction
            
            waypoint = Waypoint(lat=lat, lon=lon, alt_ft=alt, airspeed_kts=aircraft_state.airspeed_kts)
            direct_path.append(waypoint)
        
        total_distance = calculate_path_distance(direct_path)
        estimated_time = (total_distance / aircraft_state.airspeed_kts) * 60 if aircraft_state.airspeed_kts > 0 else 0
        
        return FlightPath(
            waypoints=direct_path,
            total_distance_nm=total_distance,
            estimated_time_min=estimated_time,
            emergency_profile="Direct Fallback Path",
            safety_report=SafetyReport(is_safe=True, risk_level="LOW", safety_score=80, obstacle_count=0, closest_civilian_distance_km=999.0)
        )

    def _is_goal_reached(self, state: AircraftState, goal: Waypoint) -> bool:
        dist_nm = haversine_distance_nm(state.lat, state.lon, goal.lat, goal.lon)
        alt_diff = abs(state.alt_ft - goal.alt_ft)
        return dist_nm < PlannerConstants.GOAL_DISTANCE_TOLERANCE_NM

    def _reconstruct_path(self, came_from: Dict, current: AircraftState) -> List[Waypoint]:
        path = [Waypoint(lat=current.lat, lon=current.lon, alt_ft=current.alt_ft, airspeed_kts=current.airspeed_kts)]
        while current in came_from:
            current = came_from[current]
            path.append(Waypoint(lat=current.lat, lon=current.lon, alt_ft=current.alt_ft, airspeed_kts=current.airspeed_kts))
        path.reverse()
        return path

    def _calculate_ideal_glide_altitude(self, state: AircraftState, goal: Waypoint) -> float:
        dist_nm = haversine_distance_nm(state.lat, state.lon, goal.lat, goal.lon)
        alt_needed = (dist_nm * PlannerConstants.FEET_PER_NAUTICAL_MILE) / AircraftProfile.GLIDE_RATIO
        return goal.alt_ft + alt_needed

    def generate_path_from_precomputed(self, aircraft_state: AircraftState, faf_waypoint: Waypoint, threshold_waypoint: Waypoint) -> Optional[FlightPath]:
        """Legacy method for precomputed paths - uses dynamic planning."""
        logging.info(f"Generating path to pre-computed FAF")
        
        # Use dynamic planning instead of fixed approach
        approach_heading = calculate_bearing(faf_waypoint.lat, faf_waypoint.lon, threshold_waypoint.lat, threshold_waypoint.lon)
        path_to_faf = self._a_star_search_dynamic(aircraft_state, faf_waypoint, approach_heading)
        
        if not path_to_faf:
            logging.warning("Failed to plan path to FAF")
            return None
            
        smoothed_path = smooth_path_3d(path_to_faf, aggressive=False)
        final_waypoints = smoothed_path + [threshold_waypoint]

        total_distance = calculate_path_distance(final_waypoints)
        estimated_time = (total_distance / aircraft_state.airspeed_kts) * 60 if aircraft_state.airspeed_kts > 0 else 0
        
        return FlightPath(
            waypoints=final_waypoints, 
            total_distance_nm=total_distance, 
            estimated_time_min=estimated_time,
            emergency_profile="Precomputed Glide Path"
        )
