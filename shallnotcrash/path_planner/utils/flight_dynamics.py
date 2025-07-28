# shallnotcrash/path_planner/utils/flight_dynamics.py
"""
Models the aircraft's performance envelope for path planning.
"""
from typing import List
import math
from ..data_models import AircraftState
from .coordinates import destination_point

class AircraftPerformanceModel:
    """
    Provides reachable states and performance data for a Cessna 172.
    This is a simplified model for demonstration.
    """
    def __init__(self):
        # --- C172 Performance Parameters ---
        self.glide_speed_kts: float = 68.0
        self.best_glide_fpm: float = -700.0  # Vertical speed in feet per minute
        self.turn_rate_deg_s: float = 3.0  # Standard rate turn
        self.node_time_step_s: float = 20.0 # Time between A* nodes

    def get_glide_ratio(self) -> float:
        """Calculates the glide ratio (e.g., 9:1)."""
        horizontal_speed_fps = self.glide_speed_kts * 1.68781
        vertical_speed_fps = abs(self.best_glide_fpm / 60.0)
        if vertical_speed_fps == 0:
            return float('inf')
        return horizontal_speed_fps / vertical_speed_fps

    def get_reachable_states(self, current_state: AircraftState, emergency_profile: str) -> List[AircraftState]:
        """
        Generates a list of possible next states from the current state.
        For a glide, this includes turning left, right, or continuing straight.
        """
        # TODO: This logic could be expanded to account for wind, different bank angles, etc.
        neighbors = []
        distance_per_step_nm = self.glide_speed_kts * (self.node_time_step_s / 3600.0)
        altitude_loss_ft = abs(self.best_glide_fpm) * (self.node_time_step_s / 60.0)

        # Define possible maneuvers (turn left, straight, turn right)
        turn_angle_delta = self.turn_rate_deg_s * self.node_time_step_s
        maneuvers = [-turn_angle_delta, 0, turn_angle_delta]

        for angle_change in maneuvers:
            new_heading = (current_state.heading_deg + angle_change) % 360
            
            # Calculate new position based on moving straight along the *average* heading
            # This is a simplification of a curved path.
            avg_heading = (current_state.heading_deg + new_heading) / 2
            new_lat, new_lon = destination_point(
                current_state.lat, current_state.lon, avg_heading, distance_per_step_nm
            )
            
            new_alt = current_state.alt_ft - altitude_loss_ft

            # Do not generate states below ground level (assuming 0 ft MSL for simplicity)
            if new_alt > 0:
                neighbors.append(AircraftState(
                    lat=new_lat,
                    lon=new_lon,
                    alt_ft=new_alt,
                    airspeed_kts=self.glide_speed_kts,
                    heading_deg=new_heading
                ))
        return neighbors