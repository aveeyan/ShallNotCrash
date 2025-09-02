# shallnotcrash/path_planner/core.py
import logging
import math
import heapq
from collections import defaultdict
from typing import List, Optional, Dict

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
        if not logging.getLogger().hasHandlers():
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        logging.info("PathPlanner initialized with pre-configured TerrainAnalyzer.")

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

    def _generate_optimal_path(self, aircraft_state: AircraftState, site: LandingSite) -> Optional[List[Waypoint]]:
        approach_data = select_optimal_landing_approach(site, aircraft_state)
        if not approach_data: return None
        faf_waypoint, threshold_waypoint, _ = approach_data
        coarse_path_to_faf = self._a_star_search(aircraft_state, faf_waypoint)
        if not coarse_path_to_faf: return None
        smoothed_path = smooth_path_3d(coarse_path_to_faf)
        return smoothed_path + [threshold_waypoint]

    # --- [NEW] Faster method for real-time use with cached data ---
    def generate_path_from_precomputed(self, aircraft_state: AircraftState, faf_waypoint: Waypoint, threshold_waypoint: Waypoint) -> Optional[FlightPath]:
        """
        Generates a path using pre-computed FAF and threshold waypoints.
        This is much faster as it skips the 'select_optimal_landing_approach' step.
        """
        logging.info(f"Generating real-time path to pre-computed FAF at ({faf_waypoint.lat:.4f}, {faf_waypoint.lon:.4f})")
        
        # 1. Run A* search from current state to the pre-computed FAF
        coarse_path_to_faf = self._a_star_search(aircraft_state, faf_waypoint)
        if not coarse_path_to_faf:
            logging.warning("A* search failed to find a path to the FAF.")
            return None
            
        # 2. Smooth the path and add the final approach
        smoothed_path = smooth_path_3d(coarse_path_to_faf)
        final_waypoints = smoothed_path + [threshold_waypoint]

        # 3. Package the results into a FlightPath object
        total_distance = calculate_path_distance(final_waypoints)
        estimated_time = (total_distance / aircraft_state.airspeed_kts) * 60 if aircraft_state.airspeed_kts > 0 else 0
        
        return FlightPath(
            waypoints=final_waypoints, 
            total_distance_nm=total_distance, 
            estimated_time_min=estimated_time,
            emergency_profile="Real-Time Glide Path"
        )
        

    def _a_star_search(self, start: AircraftState, goal: Waypoint) -> Optional[List[Waypoint]]:
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
            for next_state, turn in get_reachable_states(current):
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
    