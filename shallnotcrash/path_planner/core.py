# shallnotcrash/path_planner/core.py
import logging
import math
import heapq
from collections import defaultdict
from typing import List, Optional, Dict, Tuple

from .data_models import AircraftState, Waypoint, FlightPath
from .utils.calculations import calculate_path_distance, calculate_heuristic
from .utils.coordinates import haversine_distance_nm
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
        
        # [NEW] Runway selection caching to prevent inefficient re-routing
        self._cached_runway_selection = None
        self._cached_site_id = None
        self._last_aircraft_position = None
        self._runway_selection_threshold_nm = 1.0  # Re-select if aircraft moves >1nm
        self._runway_selection_heading_threshold = 30.0  # Re-select if heading changes >30°
        
        if not logging.getLogger().hasHandlers():
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        logging.info("PathPlanner initialized with runway selection caching.")

    def generate_path_to_site(self, aircraft_state: AircraftState, site: LandingSite) -> Optional[FlightPath]:
        logging.info(f"Attempting to generate path to site: Type '{site.site_type}' at ({site.lat:.4f}, {site.lon:.4f})")
        waypoints = self._generate_optimal_path(aircraft_state, site)
        if not waypoints:
            logging.warning(f"Path generation failed for the selected site.")
            return None
        safety_report = SafetyReport(is_safe=True, risk_level="LOW (Corridor Analysis Pending)", safety_score=95,
                                     obstacle_count=0, closest_civilian_distance_km=999.0)
        total_distance = calculate_path_distance(waypoints)
        estimated_time = (total_distance / aircraft_state.airspeed_kts) * 60 if aircraft_state.airspeed_kts > 0 else 0
        return FlightPath(waypoints=waypoints, total_distance_nm=total_distance, estimated_time_min=estimated_time,
                          emergency_profile="Optimal Energy-Managed Glide", safety_report=safety_report)

    def _should_recalculate_runway_selection(self, aircraft_state: AircraftState, site: LandingSite) -> bool:
        """Determines if runway selection should be recalculated based on aircraft movement."""
        # Always recalculate if we don't have a cached selection or it's for a different site
        site_id = f"{site.lat}_{site.lon}_{site.site_type}"
        if not self._cached_runway_selection or self._cached_site_id != site_id:
            return True
            
        # Check if aircraft has moved significantly
        if self._last_aircraft_position:
            distance_moved = haversine_distance_nm(
                self._last_aircraft_position.lat, self._last_aircraft_position.lon,
                aircraft_state.lat, aircraft_state.lon
            )
            
            heading_change = abs(self._last_aircraft_position.heading_deg - aircraft_state.heading_deg)
            if heading_change > 180:
                heading_change = 360 - heading_change
                
            if (distance_moved > self._runway_selection_threshold_nm or 
                heading_change > self._runway_selection_heading_threshold):
                return True
                
        return False

    def _generate_optimal_path(self, aircraft_state: AircraftState, site: LandingSite) -> Optional[List[Waypoint]]:
        # [ENHANCED] Use cached runway selection when appropriate
        if self._should_recalculate_runway_selection(aircraft_state, site):
            logging.info("Recalculating runway selection...")
            approach_data = select_optimal_landing_approach(site, aircraft_state)
            if not approach_data:
                return None
                
            # Cache the new selection
            self._cached_runway_selection = approach_data
            self._cached_site_id = f"{site.lat}_{site.lon}_{site.site_type}"
            self._last_aircraft_position = aircraft_state
            
            faf_waypoint, threshold_waypoint, approach_heading = approach_data
            logging.info(f"Selected runway end with approach heading {approach_heading:.1f}°")
        else:
            logging.info("Using cached runway selection...")
            faf_waypoint, threshold_waypoint, approach_heading = self._cached_runway_selection
            
        # Run A* search with runway awareness
        coarse_path_to_faf = self._a_star_search_with_runway_awareness(
            aircraft_state, faf_waypoint, approach_heading
        )
        if not coarse_path_to_faf: 
            return None
            
        # Use conservative smoothing to prevent sharp turns
        smoothed_path = smooth_path_3d(coarse_path_to_faf, aggressive=False)
        return smoothed_path + [threshold_waypoint]

    def generate_path_from_precomputed(self, aircraft_state: AircraftState, faf_waypoint: Waypoint, threshold_waypoint: Waypoint) -> Optional[FlightPath]:
        """
        Generates a path using pre-computed FAF and threshold waypoints.
        This is much faster as it skips the 'select_optimal_landing_approach' step.
        """
        logging.info(f"Generating real-time path to pre-computed FAF at ({faf_waypoint.lat:.4f}, {faf_waypoint.lon:.4f})")
        
        # For precomputed paths, we don't have the approach heading, so use standard A*
        coarse_path_to_faf = self._a_star_search(aircraft_state, faf_waypoint)
        if not coarse_path_to_faf:
            logging.warning("A* search failed to find a path to the FAF.")
            return None
            
        smoothed_path = smooth_path_3d(coarse_path_to_faf)
        final_waypoints = smoothed_path + [threshold_waypoint]

        total_distance = calculate_path_distance(final_waypoints)
        estimated_time = (total_distance / aircraft_state.airspeed_kts) * 60 if aircraft_state.airspeed_kts > 0 else 0
        
        return FlightPath(
            waypoints=final_waypoints, 
            total_distance_nm=total_distance, 
            estimated_time_min=estimated_time,
            emergency_profile="Real-Time Glide Path"
        )

    def _a_star_search_with_runway_awareness(self, start: AircraftState, goal: Waypoint, target_approach_heading: float) -> Optional[List[Waypoint]]:
        """Enhanced A* search that considers runway alignment for more efficient routing."""
        open_set, count = [], 0
        heapq.heappush(open_set, (0, count, start))
        came_from: Dict[AircraftState, AircraftState] = {}
        g_score = defaultdict(lambda: float('inf'))
        g_score[start] = 0
        iterations = 0
        
        for _ in range(PlannerConstants.MAX_ASTAR_ITERATIONS):
            if not open_set: 
                break
                
            iterations += 1
            _, _, current = heapq.heappop(open_set)
            
            if self._is_goal_reached(current, goal):
                return self._reconstruct_path(came_from, current)
                
            # Calculate distance to goal for adaptive turn resolution
            distance_to_goal = haversine_distance_nm(current.lat, current.lon, goal.lat, goal.lon)
            
            for next_state, turn in get_reachable_states(current, distance_to_goal):
                dist = haversine_distance_nm(current.lat, current.lon, next_state.lat, next_state.lon)
                alt_surplus = next_state.alt_ft - self._calculate_ideal_glide_altitude(next_state, goal)
                
                # [ENHANCED] Use runway-aware cost function
                tentative_g = g_score[current] + self._calculate_runway_aware_cost(
                    dist, turn, alt_surplus, next_state.heading_deg, target_approach_heading, current, goal
                )
                
                if tentative_g < g_score[next_state]:
                    came_from[next_state] = current
                    g_score[next_state] = tentative_g
                    f_score = tentative_g + calculate_heuristic(next_state, goal)
                    count += 1
                    heapq.heappush(open_set, (f_score, count, next_state))
                    
        logging.warning(f"A* search failed after {iterations} iterations (limit: {PlannerConstants.MAX_ASTAR_ITERATIONS}).")
        return None

    def _calculate_runway_aware_cost(self, distance_nm: float, turn_angle_deg: float, altitude_surplus_ft: float, 
                                   current_heading_deg: float, target_approach_heading: float, 
                                   current_state: AircraftState, goal: Waypoint) -> float:
        """Calculate move cost with runway alignment awareness."""
        base_cost = calculate_move_cost(distance_nm, turn_angle_deg, altitude_surplus_ft)
        
        # Add runway alignment bonus
        distance_to_goal = haversine_distance_nm(current_state.lat, current_state.lon, goal.lat, goal.lon)
        
        # Only apply runway alignment when getting close to the runway (within 10nm)
        if distance_to_goal < 10.0:
            heading_diff = abs(current_heading_deg - target_approach_heading)
            if heading_diff > 180:
                heading_diff = 360 - heading_diff
                
            # Stronger alignment bonus as we get closer to the runway
            proximity_factor = max(0.1, 1.0 - (distance_to_goal / 10.0))
            alignment_factor = 1.0 - (heading_diff / 180.0)  # 1.0 = perfect alignment
            
            runway_alignment_bonus = alignment_factor * proximity_factor * 0.5  # Max 0.5nm cost reduction
            return base_cost - runway_alignment_bonus
            
        return base_cost

    def _a_star_search(self, start: AircraftState, goal: Waypoint) -> Optional[List[Waypoint]]:
        """Standard A* search without runway awareness (for backward compatibility)."""
        open_set, count = [], 0
        heapq.heappush(open_set, (0, count, start))
        came_from: Dict[AircraftState, AircraftState] = {}
        g_score = defaultdict(lambda: float('inf'))
        g_score[start] = 0
        iterations = 0
        
        for _ in range(PlannerConstants.MAX_ASTAR_ITERATIONS):
            if not open_set: break
            iterations += 1
            _, _, current = heapq.heappop(open_set)
            if self._is_goal_reached(current, goal):
                return self._reconstruct_path(came_from, current)
            for next_state, turn in get_reachable_states(current, haversine_distance_nm(current.lat, current.lon, goal.lat, goal.lon)):
                dist = haversine_distance_nm(current.lat, current.lon, next_state.lat, next_state.lon)
                alt_surplus = next_state.alt_ft - self._calculate_ideal_glide_altitude(next_state, goal)
                tentative_g = g_score[current] + calculate_move_cost(dist, turn, alt_surplus)
                if tentative_g < g_score[next_state]:
                    came_from[next_state] = current
                    g_score[next_state] = tentative_g
                    f_score = tentative_g + calculate_heuristic(next_state, goal)
                    count += 1
                    heapq.heappush(open_set, (f_score, count, next_state))
        logging.warning(f"A* search failed after {iterations} iterations (limit: {PlannerConstants.MAX_ASTAR_ITERATIONS}).")
        return None

    def _is_goal_reached(self, state: AircraftState, goal: Waypoint) -> bool:
        dist_nm = haversine_distance_nm(state.lat, state.lon, goal.lat, goal.lon)
        alt_diff = abs(state.alt_ft - goal.alt_ft)
        return dist_nm < PlannerConstants.GOAL_DISTANCE_TOLERANCE_NM and alt_diff < PlannerConstants.GOAL_ALTITUDE_TOLERANCE_FT

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

    def clear_runway_cache(self):
        """Clear the runway selection cache to force recalculation."""
        self._cached_runway_selection = None
        self._cached_site_id = None
        self._last_aircraft_position = None
        logging.info("Runway selection cache cleared.")
    