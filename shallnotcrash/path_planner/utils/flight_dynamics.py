# shallnotcrash/path_planner/utils/flight_dynamics.py
"""
[ENHANCED MANEUVERABILITY - V15]
This version improves the A* planner's success rate by providing it with
more nuanced maneuvering options. By adding half-rate turns, the planner
can generate more efficient paths to off-angle targets without exhausting
its iteration limit.
"""
import math
from typing import List, Tuple
from ..data_models import AircraftState
from ..constants import PlannerConstants, AircraftProfile
from .coordinates import destination_point

def _average_headings(h1_deg: float, h2_deg: float) -> float:
    """Correctly averages two headings using vector arithmetic."""
    h1_rad, h2_rad = math.radians(h1_deg), math.radians(h2_deg)
    avg_x = (math.cos(h1_rad) + math.cos(h2_rad)) / 2.0
    avg_y = (math.sin(h1_rad) + math.sin(h2_rad)) / 2.0
    return (math.degrees(math.atan2(avg_y, avg_x)) + 360) % 360

def get_reachable_states(current_state: AircraftState) -> List[Tuple[AircraftState, float]]:
    """
    Generates a list of next possible states the aircraft can reach.
    This version includes half-rate turns for improved maneuverability.
    """
    dist_per_step_nm = (AircraftProfile.GLIDE_SPEED_KTS * PlannerConstants.TIME_DELTA_SEC) / 3600.0
    base_alt_loss_ft = (dist_per_step_nm * PlannerConstants.FEET_PER_NAUTICAL_MILE) / AircraftProfile.GLIDE_RATIO
    
    # The maximum turn the aircraft can make in one step (e.g., 90 degrees)
    turn_angle_per_step = AircraftProfile.STANDARD_TURN_RATE_DEG_S * PlannerConstants.TIME_DELTA_SEC
    
    reachable_states = []
    
    # [THE FIX] Provide more turn options: straight, half-left, half-right, full-left, full-right
    turn_options = [
        0,                                  # Straight
        -turn_angle_per_step / 2,           # Half-rate turn left
        turn_angle_per_step / 2,            # Half-rate turn right
        -turn_angle_per_step,               # Standard-rate turn left
        turn_angle_per_step,                # Standard-rate turn right
    ]
    
    for turn_deg in turn_options:
        
        # Apply a drag penalty for turning, proportional to the turn sharpness
        turn_penalty_factor = 1 + (abs(turn_deg) / turn_angle_per_step) * (AircraftProfile.TURN_DRAG_PENALTY_FACTOR - 1)
        actual_alt_loss = base_alt_loss_ft * turn_penalty_factor if turn_deg != 0 else base_alt_loss_ft

        new_heading = (current_state.heading_deg + turn_deg) % 360
        avg_heading = _average_headings(current_state.heading_deg, new_heading)
        
        new_lat, new_lon = destination_point(current_state.lat, current_state.lon, avg_heading, dist_per_step_nm)
        new_alt = current_state.alt_ft - actual_alt_loss
        
        # Don't generate states that are far below the ground
        if new_alt < -500:
            continue

        new_state = AircraftState(
            lat=new_lat, 
            lon=new_lon, 
            alt_ft=new_alt, 
            heading_deg=new_heading, 
            airspeed_kts=AircraftProfile.GLIDE_SPEED_KTS
        )
        
        reachable_states.append((new_state, turn_deg))
        
    return reachable_states
