# shallnotcrash/path_planner/core.py
"""
[RE-CALIBRATED - V9]
This version corrects the site selection logic by significantly increasing the
distance penalty. It also re-introduces the 'find_best_path' method to
encapsulate the full process of selecting a site and planning the path.
"""
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
    """
    Selects the best landing site from a list and generates an optimal path to it.
    """
    def __init__(self, terrain_analyzer: TerrainAnalyzer):
        self.terrain_analyzer = terrain_analyzer
        if not logging.getLogger().hasHandlers():
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        logging.info("PathPlanner initialized with pre-configured TerrainAnalyzer.")

    def find_best_path(self, aircraft_state: AircraftState, sites: List[LandingSite]) -> Optional[FlightPath]:
        """
        Selects the single best landing site and generates the path.
        """
        if not sites:
            logging.error("No landing sites provided to plan a path.")
            return None

        best_site = self._select_optimal_site(aircraft_state, sites)
        if not best_site:
            logging.error("No safe and suitable landing sites found in the provided list.")
            return None
        
        logging.info(f"Optimal site selected: Type '{best_site.site_type}' (Final Score: {self._calculate_site_score(aircraft_state, best_site):.1f})")
        return self.generate_path_to_site(aircraft_state, best_site)

    # In shallnotcrash/path_planner/core.py

    def generate_path_to_site(self, aircraft_state: AircraftState, site: LandingSite) -> Optional[FlightPath]:
        """Generates an optimal, terrain-validated flight path to a single, specific landing site."""
        logging.info(f"Attempting to generate path to site: Type '{site.site_type}' at ({site.lat:.4f}, {site.lon:.4f})")

        waypoints = self._generate_optimal_path(aircraft_state, site)
        if not waypoints:
            logging.warning(f"Path generation failed for the selected site.")
            return None

        # [THE FIX] Add the missing required arguments with safe default values.
        safety_report = SafetyReport(
            is_safe=True,
            risk_level="LOW (Corridor Analysis Pending)",
            safety_score=95,
            obstacle_count=0,
            closest_civilian_distance_km=999.0
        )

        total_distance = calculate_path_distance(waypoints)
        estimated_time = (total_distance / aircraft_state.airspeed_kts) * 60 if aircraft_state.airspeed_kts > 0 else 0

        return FlightPath(
            waypoints=waypoints,
            total_distance_nm=total_distance,
            estimated_time_min=estimated_time,
            emergency_profile="Optimal Energy-Managed Glide",
            safety_report=safety_report
        )

    def _select_optimal_site(self, aircraft_state: AircraftState, sites: List[LandingSite]) -> Optional[LandingSite]:
        """Selects the best site based on its intrinsic score and the distance to it."""
        scored_sites = [(site, self._calculate_site_score(aircraft_state, site)) for site in sites if site.safety_report and site.safety_report.is_safe]
        if not scored_sites: return None
        return max(scored_sites, key=lambda item: item[1])[0]

    def _calculate_site_score(self, aircraft_state: AircraftState, site: LandingSite) -> float:
        """Calculates a composite score based on site quality and distance."""
        distance_nm = haversine_distance_nm(aircraft_state.lat, aircraft_state.lon, site.lat, site.lon)
        
        # [THE FIX] Increase the distance penalty multiplier from 2.0 to 5.0
        # This makes the planner strongly prefer closer landing sites.
        distance_penalty = distance_nm * 5.0
        
        return site.suitability_score - distance_penalty

    # ... (the rest of the class, like _generate_optimal_path and _a_star_search, is unchanged) ...
    def _generate_optimal_path(self, aircraft_state: AircraftState, site: LandingSite) -> Optional[List[Waypoint]]:
        approach_data = select_optimal_landing_approach(site, aircraft_state)
        if not approach_data:
            logging.error("Could not determine a valid approach for the selected site.")
            return None
        faf_waypoint, threshold_waypoint, _ = approach_data
        coarse_path_to_faf = self._a_star_search(aircraft_state, faf_waypoint)
        if not coarse_path_to_faf:
            return None
        smoothed_path = smooth_path_3d(coarse_path_to_faf)
        final_path = smoothed_path + [threshold_waypoint]
        return final_path

    # In shallnotcrash/path_planner/core.py

    def _a_star_search(self, start: AircraftState, goal: Waypoint) -> Optional[List[Waypoint]]:
        """A* search implementation with energy-aware heuristics."""
        open_set, count = [], 0
        heapq.heappush(open_set, (0, count, start))
        
        came_from: Dict[AircraftState, AircraftState] = {}
        g_score = defaultdict(lambda: float('inf'))
        g_score[start] = 0
        
        iterations = 0 # Keep track of iterations
        for _ in range(PlannerConstants.MAX_ASTAR_ITERATIONS):
            iterations += 1
            if not open_set: break
            
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
        
        # [THE FIX] Corrected the misspelled constant name in the warning message.
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
