# shallnotcrash/path_planner/core.py
"""
[ARCHITECTURAL REWORK - V27]
FIXED: Added closed set tracking to prevent infinite loops
FIXED: Added altitude to state key for proper physics
FIXED: Added altitude tolerance to goal checking
"""
import heapq
import math
from typing import List, Optional, Set, Dict, Tuple

from ..landing_site.data_models import LandingSite
from .data_models import AircraftState, FlightPath, Waypoint
from .constants import PlannerConstants, AircraftProfile
from .utils import touchdown, flight_dynamics, cost_functions, smoothing, calculations, coordinates

class PathPlanner:
    def generate_path(self, current_state: AircraftState, target_site: LandingSite) -> Optional[FlightPath]:
        """
        Orchestrates the generation of a flight path. It runs a single,
        authoritative A* search and then smoothes the result.
        """
        sequence = touchdown.select_optimal_landing_approach(target_site, current_state)
        if not sequence:
            print("! No landing approach sequence found")
            return None
            
        faf_goal, threshold_final, final_approach_hdg = sequence

        # Pre-flight check: Can we reach the goal?
        required_alt_loss = current_state.alt_ft - faf_goal.alt_ft
        if required_alt_loss < 0:
            print(f"! Already below goal altitude: {current_state.alt_ft:.0f} ft < {faf_goal.alt_ft:.0f} ft")
            return None
            
        max_glide_dist = (required_alt_loss / PlannerConstants.FEET_PER_NAUTICAL_MILE) * AircraftProfile.GLIDE_RATIO
        dist_to_goal = coordinates.haversine_distance_nm(current_state.lat, current_state.lon, faf_goal.lat, faf_goal.lon)
        
        if max_glide_dist < dist_to_goal:
            print(f"! Cannot reach goal: Need {dist_to_goal:.1f} NM but can only glide {max_glide_dist:.1f} NM")
            return None

        print(f"Path planning: {current_state.alt_ft:.0f} ft -> {faf_goal.alt_ft:.0f} ft, {dist_to_goal:.1f} NM")
        
        coarse_path_waypoints = self._run_astar_search(current_state, faf_goal, final_approach_hdg)

        if not coarse_path_waypoints:
            print("! A* search failed to find a path")
            return None

        # Stitch the path from A* to the final touchdown point.
        full_coarse_path = coarse_path_waypoints + [threshold_final]
        full_coarse_path = self._remove_consecutive_duplicates(full_coarse_path)
        
        # Smooth the final, valid path.
        smoothed_path = smoothing.smooth_path_3d(full_coarse_path)

        return FlightPath(
            waypoints=smoothed_path,
            total_distance_nm=calculations.calculate_path_distance(smoothed_path),
            estimated_time_min=(calculations.calculate_path_distance(smoothed_path) / AircraftProfile.GLIDE_SPEED_KTS) * 60,
            emergency_profile="C172P_EMERGENCY_GLIDE"
        )

    # shallnotcrash/path_planner/core.py

# ... (keep all imports and the PathPlanner class definition) ...

# Replace the _run_astar_search method in your PathPlanner class with this version:

# In shallnotcrash/path_planner/core.py, inside the PathPlanner class

# In shallnotcrash/path_planner/core.py, inside the PathPlanner class

    def _run_astar_search(self, start: AircraftState, goal: Waypoint, final_approach_hdg: float) -> Optional[List[Waypoint]]:
        """
        [CORRECTED - V30]
        Fixes a NameError typo introduced in the previous version. The logical
        correction to 'came_from' is preserved.
        """
        # ... (initialization code remains the same) ...
        total_dist_to_goal_nm = coordinates.haversine_distance_nm(start.lat, start.lon, goal.lat, goal.lon)
        total_alt_to_lose_ft = start.alt_ft - goal.alt_ft
        target_descent_rate_ft_per_nm = total_alt_to_lose_ft / total_dist_to_goal_nm if total_dist_to_goal_nm > 0.01 else 0

        open_set = [(0, 0, start)]
        came_from: Dict[Tuple, AircraftState] = {}
        g_score = {self._get_key(start): 0}
        closed_set: Set[Tuple] = set()
        counter = 1

        while open_set:
            if counter > PlannerConstants.MAX_ASTAR_ITERATIONS:
                print(f"! A* search exceeded maximum iterations ({PlannerConstants.MAX_ASTAR_ITERATIONS})")
                return None
            
            _, _, current_node = heapq.heappop(open_set)
            current_key = self._get_key(current_node)
            
            if current_key in closed_set:
                continue
            closed_set.add(current_key)
            
            if self._is_goal(current_node, goal, final_approach_hdg):
                print(f"A* search succeeded after {counter} iterations")
                return self._reconstruct_path(came_from, current_node)
            
            for neighbor_state, turn_deg in flight_dynamics.get_reachable_states(current_node):
                neighbor_key = self._get_key(neighbor_state)
                
                if neighbor_key in closed_set:
                    continue
                
                dist_from_start_to_neighbor = coordinates.haversine_distance_nm(start.lat, start.lon, neighbor_state.lat, neighbor_state.lon)
                ideal_alt_at_neighbor = start.alt_ft - (dist_from_start_to_neighbor * target_descent_rate_ft_per_nm)
                altitude_surplus = neighbor_state.alt_ft - ideal_alt_at_neighbor

                # [TYPO FIX] 'current_lon' has been corrected to 'current_node.lon'
                dist_moved = coordinates.haversine_distance_nm(current_node.lat, current_node.lon, neighbor_state.lat, neighbor_state.lon)
                
                move_cost = cost_functions.calculate_move_cost(
                    distance_nm=dist_moved,
                    turn_angle_deg=turn_deg,
                    altitude_surplus_ft=altitude_surplus
                )
                
                tentative_g_score = g_score.get(current_key, float('inf')) + move_cost
                
                if tentative_g_score < g_score.get(neighbor_key, float('inf')):
                    # The correct logic from the previous fix is preserved.
                    came_from[neighbor_key] = current_node
                    g_score[neighbor_key] = tentative_g_score
                    
                    heuristic_cost = calculations.calculate_heuristic(neighbor_state, goal, final_approach_hdg)
                    f_score = tentative_g_score + heuristic_cost
                    
                    heapq.heappush(open_set, (f_score, counter, neighbor_state))
                    counter += 1
                    
        print("! A* search exhausted all possibilities without finding a path")
        return None
      
    def _is_goal(self, s: AircraftState, g: Waypoint, final_approach_hdg: float) -> bool:
        dist_ok = coordinates.haversine_distance_nm(s.lat, s.lon, g.lat, g.lon) < PlannerConstants.GOAL_DISTANCE_TOLERANCE_NM
        hdg_diff = abs((s.heading_deg - final_approach_hdg + 180) % 360 - 180)
        hdg_ok = hdg_diff < PlannerConstants.GOAL_HEADING_TOLERANCE_DEG
        # Altitude check - allow some tolerance
        alt_ok = abs(s.alt_ft - g.alt_ft) < 500.0  # 500 ft tolerance for goal altitude
        return dist_ok and hdg_ok and alt_ok

# In shallnotcrash/path_planner/core.py

    def _reconstruct_path(self, came_from: dict, current: AircraftState) -> List[Waypoint]:
        """
        [HARDENED - V28]
        This version is hardened against infinite loops. It tracks the keys visited
        during reconstruction and will break if a cycle is detected, preventing a
        system hang caused by a corrupted 'came_from' map from the A* search.
        """
        path = [current]
        
        # Defensive check to prevent infinite loops from a corrupted came_from map
        reconstruction_visited_keys = {self._get_key(current)}

        while self._get_key(current) in came_from:
            # Move to the parent node
            current = came_from[self._get_key(current)]
            current_key = self._get_key(current)

            # If we have already seen this key during this specific reconstruction,
            # we have detected a cycle. We must break to prevent a hang.
            if current_key in reconstruction_visited_keys:
                print(f"! CRITICAL ERROR: Cycle detected in path history at key {current_key}.")
                print("! This indicates a flaw in the A* closed_set logic, but a hang has been prevented.")
                break
            
            path.append(current)
            reconstruction_visited_keys.add(current_key)
        
        # The original debug printing remains valuable
        print(f"Reconstructed path ({len(path)} waypoints):")
        
        # Reverse the path so it goes from start to finish
        final_path_states = list(reversed(path))
        
        total_alt_loss = final_path_states[0].alt_ft - final_path_states[-1].alt_ft
        total_distance = calculations.calculate_path_distance([Waypoint(s.lat, s.lon, s.alt_ft, s.airspeed_kts) for s in final_path_states])
        
        # Avoid division by zero if there's no altitude loss
        if total_alt_loss > 1:
            # Convert altitude loss to thousands of feet for the ratio
            glide_ratio = total_distance / (total_alt_loss / 1000.0) 
            print(f"  Effective glide ratio: {glide_ratio:.1f} kft/NM") # Corrected unit
        else:
            print("  Effective glide ratio: N/A (no significant altitude loss)")

        print(f"  Total altitude loss: {total_alt_loss:.0f} ft")
        print(f"  Total distance: {total_distance:.2f} NM")
        
        for i, state in enumerate(final_path_states):
            if i % 20 == 0 or i == len(final_path_states) - 1:
                print(f"  WP {i}: Alt={state.alt_ft:.0f} ft, Lat={state.lat:.4f}, Lon={state.lon:.4f}")
        
        return [Waypoint(s.lat, s.lon, s.alt_ft, s.airspeed_kts) for s in final_path_states]
        
    def _get_key(self, s: AircraftState) -> tuple:
        # Include altitude in state key (grouped in 50 ft increments)
        alt_precision = 50
        return (
            round(s.lat, PlannerConstants.LAT_LON_PRECISION), 
            round(s.lon, PlannerConstants.LAT_LON_PRECISION), 
            round(s.alt_ft / alt_precision),
            round(s.heading_deg / PlannerConstants.HEADING_PRECISION_DEG)
        )

    def _remove_consecutive_duplicates(self, waypoints: List[Waypoint]) -> List[Waypoint]:
        if not waypoints: 
            return []
        cleaned_wps = [waypoints[0]]
        for i in range(1, len(waypoints)):
            lat_diff = abs(waypoints[i].lat - cleaned_wps[-1].lat)
            lon_diff = abs(waypoints[i].lon - cleaned_wps[-1].lon)
            if lat_diff > 1e-7 or lon_diff > 1e-7:
                cleaned_wps.append(waypoints[i])
        return cleaned_wps
