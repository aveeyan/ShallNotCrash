# shallnotcrash/path_planner/core.py
"""
Contains the primary PathPlanner class, which orchestrates the A* search
and path generation process.
"""
import heapq
import math
from typing import List, Dict, Optional
# --- [No change to imports] ---
from .data_models import AircraftState, FlightPath, Waypoint
from ..landing_site.data_models import LandingSite
from ..emergency.constants import EmergencySeverity
from .utils.flight_dynamics import AircraftPerformanceModel
from .utils.touchdown import TouchdownSelector
from .utils.coordinates import haversine_distance_nm
from .utils.smoothing import PathSmoother

class PathPlanner:
    """
    Generates an optimal flight path using a 3D A* search algorithm,
    respecting aircraft performance constraints and emergency scenarios.
    """
    def __init__(self):
        self.performance_model = AircraftPerformanceModel()
        self.touchdown_selector = TouchdownSelector()
        self.path_smoother = PathSmoother()

    def generate_path(
        self,
        current_state: AircraftState,
        target_site: LandingSite,
        emergency_type: EmergencySeverity,
        wind_heading_deg: float = 0.0
    ) -> Optional[FlightPath]:
        print(f"PATH PLANNER: Generating path for {emergency_type.name} to {target_site.site_type}.")
        touchdown_points = self.touchdown_selector.get_touchdown_points(target_site, wind_heading_deg)
        if not touchdown_points:
            print("PATH PLANNER ERROR: No valid touchdown point could be determined.")
            return None
        goal_waypoint = touchdown_points[0]
        print(f"PATH PLANNER: Target acquired -> Lat: {goal_waypoint.lat:.4f}, Lon: {goal_waypoint.lon:.4f}")
        raw_path_states = self._run_astar_search(current_state, goal_waypoint, emergency_type.name)
        if not raw_path_states:
            print("PATH PLANNER FAILURE: A* search could not find a valid path.")
            return None
        raw_waypoints = [Waypoint(lat=s.lat, lon=s.lon, alt_ft=s.alt_ft, airspeed_kts=s.airspeed_kts) for s in raw_path_states]
        final_waypoints = self.path_smoother.smooth_path(raw_waypoints)
        path_distance = self._calculate_path_distance(final_waypoints)
        glide_speed = self.performance_model.glide_speed_kts
        estimated_time = (path_distance / glide_speed) * 60 if glide_speed > 0 else 0
        return FlightPath(
            waypoints=final_waypoints,
            total_distance_nm=path_distance,
            estimated_time_min=estimated_time,
            emergency_profile=emergency_type.name
        )
    
    # --- [CORRECTIVE PATCH APPLIED TO _run_astar_search] ---
    def _run_astar_search(self, start_state: AircraftState, goal_waypoint: Waypoint, emergency_profile: str) -> Optional[List[AircraftState]]:
        """The core A* search algorithm implementation."""
        
        # --- PATCH 1: Initialize a unique counter for tie-breaking. ---
        counter = 0

        # The open set is a priority queue of (f_cost, unique_id, state).
        # The unique_id (counter) ensures heapq never has to compare two AircraftState objects.
        open_set = [(0, counter, start_state)]
        
        came_from: Dict[AircraftState, AircraftState] = {}
        g_score: Dict[AircraftState, float] = {start_state: 0}
        f_score: Dict[AircraftState, float] = {start_state: self._calculate_heuristic(start_state, goal_waypoint)}

        while open_set:
            # Get the node in the open set with the lowest f_score
            # The counter is discarded with '_' as it's only for sorting.
            _, _, current = heapq.heappop(open_set)

            if self._is_goal_reached(current, goal_waypoint):
                print("PATH PLANNER: Goal reached. Reconstructing path.")
                return self._reconstruct_path(came_from, current)

            neighbors = self.performance_model.get_reachable_states(current, emergency_profile)
            
            for neighbor in neighbors:
                move_cost = haversine_distance_nm(current.lat, current.lon, neighbor.lat, neighbor.lon)
                tentative_g_score = g_score.get(current, float('inf')) + move_cost

                if tentative_g_score < g_score.get(neighbor, float('inf')):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    h_cost = self._calculate_heuristic(neighbor, goal_waypoint)
                    f_score[neighbor] = tentative_g_score + h_cost
                    
                    # --- PATCH 2: Increment the counter with each push. ---
                    counter += 1
                    # --- PATCH 3: Push the tuple with the counter as the tie-breaker. ---
                    heapq.heappush(open_set, (f_score[neighbor], counter, neighbor))
        
        return None
    
    def _calculate_heuristic(self, state: AircraftState, goal: Waypoint) -> float:
        """Heuristic function h(n). Estimates cost from state to goal (distance in nm)."""
        dist_nm = haversine_distance_nm(state.lat, state.lon, goal.lat, goal.lon)
        alt_diff_ft = state.alt_ft - goal.alt_ft

        if alt_diff_ft <= 0:
            return float('inf')

        glide_ratio = self.performance_model.get_glide_ratio()
        if glide_ratio <= 0:
            return float('inf')
        
        # Maximum distance the aircraft can glide from its current altitude
        max_glide_dist_ft = alt_diff_ft * glide_ratio
        max_glide_dist_nm = max_glide_dist_ft / 6076.12
        
        if max_glide_dist_nm < dist_nm:
            return float('inf') # Physically impossible to reach

        return dist_nm

    def _is_goal_reached(self, state: AircraftState, goal: Waypoint) -> bool:
        """Checks if the state is within the goal's tolerance."""
        dist_nm = haversine_distance_nm(state.lat, state.lon, goal.lat, goal.lon)
        alt_diff_ft = abs(state.alt_ft - goal.alt_ft)
        return dist_nm < 0.2 and alt_diff_ft < 150

    def _reconstruct_path(self, came_from: Dict, current: AircraftState) -> List[AircraftState]:
        """Traces back from the goal to the start to build the path."""
        total_path = [current]
        while current in came_from:
            current = came_from[current]
            total_path.append(current)
        return total_path[::-1]

    def _calculate_path_distance(self, waypoints: List[Waypoint]) -> float:
        """Calculates the total distance of a path."""
        total_dist = 0.0
        for i in range(len(waypoints) - 1):
            p1 = waypoints[i]
            p2 = waypoints[i+1]
            total_dist += haversine_distance_nm(p1.lat, p1.lon, p2.lat, p2.lon)
        return total_dist