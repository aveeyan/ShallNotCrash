# shallnotcrash/path_planner/core.py
"""
Contains the primary PathPlanner class, which orchestrates the A* search
and path generation process using the refactored utilities.
"""
import heapq
from typing import List, Dict, Optional, Tuple

from ..landing_site.data_models import LandingSite
from .data_models import AircraftState, FlightPath, Waypoint
from .constants import PlannerConstants, AircraftProfile
from .utils import touchdown, flight_dynamics, cost_functions, smoothing, calculations
from .utils.coordinates import haversine_distance_nm

class PathPlanner:
    """
    Generates an optimal flight path using a 3D A* search algorithm.
    """
    def generate_path(
        self,
        current_state: AircraftState,
        target_site: LandingSite,
        wind_heading_deg: float = 0.0,
        # --- [FIX] Changed parameter name from 'emergency_profile' to 'emergency_type' ---
        emergency_type: str = "EMERGENCY_GLIDE"
    ) -> Optional[FlightPath]:
        """
        Main method to generate a complete, smoothed flight path to a landing site.
        """
        landing_sequence = touchdown.get_landing_sequence(target_site, wind_heading_deg)
        if not landing_sequence:
            print("PATH PLANNER FAILURE: Could not determine a landing sequence.")
            return None
        
        faf_goal, threshold_final = landing_sequence
        print(f"PATH PLANNER: A* Target is FAF -> Lat: {faf_goal.lat:.4f}, Lon: {faf_goal.lon:.4f}, Alt: {faf_goal.alt_ft:.0f} ft")

        raw_path_states = self._run_astar_search(current_state, faf_goal)
        if not raw_path_states:
            print("PATH PLANNER FAILURE: A* search could not find a valid path.")
            return None

        raw_waypoints = [Waypoint(s.lat, s.lon, s.alt_ft, s.airspeed_kts) for s in raw_path_states]
        raw_waypoints.append(threshold_final)
        
        final_waypoints = smoothing.smooth_path(raw_waypoints)
        
        path_distance = calculations.calculate_path_distance(final_waypoints)
        est_time = (path_distance / AircraftProfile.GLIDE_SPEED_KTS) * 60 if AircraftProfile.GLIDE_SPEED_KTS > 0 else 0
        
        return FlightPath(
            waypoints=final_waypoints,
            total_distance_nm=path_distance,
            estimated_time_min=est_time,
            # --- [FIX] Pass the correct variable to the FlightPath constructor ---
            emergency_profile=emergency_type
        )

    def _get_discrete_key(self, state: AircraftState) -> Tuple[float, float, int, int]:
        lat = round(state.lat, PlannerConstants.LAT_LON_PRECISION)
        lon = round(state.lon, PlannerConstants.LAT_LON_PRECISION)
        alt = round(state.alt_ft / PlannerConstants.ALT_PRECISION_FT)
        hdg = round(state.heading_deg / PlannerConstants.HEADING_PRECISION_DEG)
        return (lat, lon, alt, hdg)

    def _is_goal_reached(self, state: AircraftState, goal: Waypoint) -> bool:
        dist_nm = haversine_distance_nm(state.lat, state.lon, goal.lat, goal.lon)
        alt_diff_ft = abs(state.alt_ft - goal.alt_ft)
        return dist_nm < 0.5 and alt_diff_ft < (PlannerConstants.ALT_PRECISION_FT * 2)

    def _reconstruct_path(self, came_from: Dict, current: AircraftState) -> List[AircraftState]:
        total_path = [current]
        current_key = self._get_discrete_key(current)
        while current_key in came_from:
            current = came_from[current_key]
            total_path.append(current)
            current_key = self._get_discrete_key(current)
        return total_path[::-1]

    def _run_astar_search(self, start_state: AircraftState, goal_waypoint: Waypoint) -> Optional[List[AircraftState]]:
        counter = 0
        start_key = self._get_discrete_key(start_state)
        
        open_set = [(0, counter, start_state)]
        came_from: Dict[tuple, AircraftState] = {}
        g_score: Dict[tuple, float] = {start_key: 0}
        f_score: Dict[tuple, float] = {start_key: calculations.calculate_heuristic(start_state, goal_waypoint)}

        while open_set:
            _, _, current = heapq.heappop(open_set)
            current_key = self._get_discrete_key(current)

            if self._is_goal_reached(current, goal_waypoint):
                return self._reconstruct_path(came_from, current)

            neighbors = flight_dynamics.get_reachable_states(current, goal_waypoint)
            
            for neighbor, turn_deg in neighbors:
                dist_moved = haversine_distance_nm(current.lat, current.lon, neighbor.lat, neighbor.lon)
                move_cost = cost_functions.calculate_move_cost(dist_moved, turn_deg)
                
                tentative_g_score = g_score.get(current_key, float('inf')) + move_cost
                neighbor_key = self._get_discrete_key(neighbor)

                if tentative_g_score < g_score.get(neighbor_key, float('inf')):
                    came_from[neighbor_key] = current
                    g_score[neighbor_key] = tentative_g_score
                    h_cost = calculations.calculate_heuristic(neighbor, goal_waypoint)
                    if h_cost == float('inf'): continue

                    f_score[neighbor_key] = tentative_g_score + h_cost
                    counter += 1
                    heapq.heappush(open_set, (f_score[neighbor_key], counter, neighbor))
        
        return None
