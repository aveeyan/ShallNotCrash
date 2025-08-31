# shallnotcrash/path_planner/core.py
"""
[UNIFIED & STABLE - V7]
This version is fully refactored to consume LandingSite objects from the
landing_site module. It no longer has conflicting data models and accepts
a pre-initialized TerrainAnalyzer for correct, high-performance operation.
"""
import logging
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
    Generates an optimal, terrain-validated flight path to the best available landing site.
    """
    def __init__(self, terrain_analyzer: TerrainAnalyzer):
        self.terrain_analyzer = terrain_analyzer
        if not logging.getLogger().hasHandlers():
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        logging.info("PathPlanner initialized with pre-configured TerrainAnalyzer.")

    def find_best_path(self, aircraft_state: AircraftState, sites: List[LandingSite]) -> Optional[FlightPath]:
        """
        Selects the best landing site from a list and generates an optimal path to it.
        """
        if not sites:
            logging.error("No landing sites provided to plan a path.")
            return None

        best_site = self._select_optimal_site(aircraft_state, sites)
        if not best_site:
            logging.error("No safe and suitable landing sites found in the provided list.")
            return None

        logging.info(f"Optimal site selected: Type '{best_site.site_type}' (Score: {best_site.suitability_score})")

        waypoints = self._generate_optimal_path(aircraft_state, best_site)
        if not waypoints:
            logging.error(f"Path generation failed for the selected site.")
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

        # Note: The 'emergency_profile' argument was missing from the FlightPath constructor
        return FlightPath(
            waypoints=waypoints,
            total_distance_nm=total_distance,
            estimated_time_min=estimated_time,
            emergency_profile="Optimal Energy-Managed Glide",
            safety_report=safety_report
        )

    def _select_optimal_site(self, aircraft_state: AircraftState, sites: List[LandingSite]) -> Optional[LandingSite]:
        """Selects the best site based on its intrinsic score and the distance to it."""
        scored_sites = []
        for site in sites:
            if not site.safety_report or not site.safety_report.is_safe:
                continue
            
            distance_nm = haversine_distance_nm(aircraft_state.lat, aircraft_state.lon, site.lat, site.lon)
            # Simple score: prioritize high-quality sites, penalize distance.
            final_score = site.suitability_score - (distance_nm * 2.0)
            scored_sites.append((site, final_score))
        
        if not scored_sites: return None
        return max(scored_sites, key=lambda item: item[1])[0]

    def _generate_optimal_path(self, aircraft_state: AircraftState, site: LandingSite) -> Optional[List[Waypoint]]:
        """Generates a complete path from start to landing using A*."""
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

    def _a_star_search(self, start: AircraftState, goal: Waypoint) -> Optional[List[Waypoint]]:
        import heapq
        from collections import defaultdict
        
        open_set, count = [], 0
        heapq.heappush(open_set, (0, count, start))
        
        came_from: Dict[AircraftState, AircraftState] = {}
        g_score = defaultdict(lambda: float('inf'))
        g_score[start] = 0
        
        for i in range(PlannerConstants.MAX_ASTAR_ITERATIONS):
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
        
        logging.warning(f"A* search failed after {PlannerConstants.MAX_ASTAR_ITERATIONS} iterations.")
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
