# shallnotcrash/path_planner/utils/flight_dynamics.py
"""
[DEFINITIVE FINAL FIX - V11]
Fixed debug output placement and removed duplicate calculations.
"""
import math
from typing import List, Tuple
from ..data_models import AircraftState
from ..constants import PlannerConstants, AircraftProfile
from .coordinates import destination_point

def _average_headings(h1_deg: float, h2_deg: float) -> float:
    """Correctly averages two headings using vector arithmetic."""
    h1_rad = math.radians(h1_deg)
    h2_rad = math.radians(h2_deg)
    
    x1, y1 = math.cos(h1_rad), math.sin(h1_rad)
    x2, y2 = math.cos(h2_rad), math.sin(h2_rad)
    
    avg_x = (x1 + x2) / 2.0
    avg_y = (y1 + y2) / 2.0
    
    avg_heading_rad = math.atan2(avg_y, avg_x)
    
    return (math.degrees(avg_heading_rad) + 360) % 360

# In path_planner/utils/flight_dynamics.py

def get_reachable_states(current_state: AircraftState) -> List[Tuple[AircraftState, float]]:
    """
    [FINAL CORRECTED VERSION - V14]
    This version removes the flawed MAX_SAFE_GLIDESLOPE_DEG check, which was
    creating a physical paradox that made pathfinding impossible. The planner
    is now free to use the aircraft's natural glide angle, and energy management
    is correctly handled by the cost function.
    """
    dist_per_step_nm = (AircraftProfile.GLIDE_SPEED_KTS * PlannerConstants.TIME_DELTA_SEC) / 3600.0
    base_alt_loss_ft = (dist_per_step_nm * PlannerConstants.FEET_PER_NAUTICAL_MILE) / AircraftProfile.GLIDE_RATIO
    turn_angle_per_step = AircraftProfile.STANDARD_TURN_RATE_DEG_S * PlannerConstants.TIME_DELTA_SEC
    
    reachable_states = []
    
    for turn_deg in [0, -turn_angle_per_step, turn_angle_per_step]:
        
        if turn_deg == 0:
            actual_alt_loss = base_alt_loss_ft
        else:
            actual_alt_loss = base_alt_loss_ft * AircraftProfile.TURN_DRAG_PENALTY_FACTOR

        new_heading = (current_state.heading_deg + turn_deg) % 360
        avg_heading = _average_headings(current_state.heading_deg, new_heading)
        
        new_lat, new_lon = destination_point(current_state.lat, current_state.lon, avg_heading, dist_per_step_nm)
        new_alt = current_state.alt_ft - actual_alt_loss
        
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
