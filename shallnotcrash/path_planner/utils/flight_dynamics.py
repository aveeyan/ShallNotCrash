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
    [CORRECTED AERODYNAMIC MODEL - V12]
    Generates next states with a more realistic physics model that penalizes
    turns with increased altitude loss due to higher induced drag.
    """
    dist_per_step_nm = (AircraftProfile.GLIDE_SPEED_KTS * PlannerConstants.TIME_DELTA_SEC) / 3600.0
    base_alt_loss_ft = (dist_per_step_nm * PlannerConstants.FEET_PER_NAUTICAL_MILE) / AircraftProfile.GLIDE_RATIO
    turn_angle_per_step = AircraftProfile.STANDARD_TURN_RATE_DEG_S * PlannerConstants.TIME_DELTA_SEC
    
    reachable_states = []
    
    # Define the possible maneuvers: straight, left turn, right turn
    for turn_deg in [0, -turn_angle_per_step, turn_angle_per_step]:
        
        # Apply the aerodynamic penalty for turning
        if turn_deg == 0:
            actual_alt_loss = base_alt_loss_ft
        else:
            actual_alt_loss = base_alt_loss_ft * AircraftProfile.TURN_DRAG_PENALTY_FACTOR

        new_heading = (current_state.heading_deg + turn_deg) % 360
        avg_heading = _average_headings(current_state.heading_deg, new_heading)
        
        new_lat, new_lon = destination_point(current_state.lat, current_state.lon, avg_heading, dist_per_step_nm)
        new_alt = current_state.alt_ft - actual_alt_loss
        
        # The aircraft cannot glide underground. Discard any states that result in this.
        if new_alt < -500: # Allow a small negative buffer for landing site elevation variance
            continue

        # --- Optional: More informative debug output ---
        print(f"DEBUG Flight Dynamics (Turn: {turn_deg:.0f}°):")
        print(f"  Start Alt: {current_state.alt_ft:.0f} ft -> End Alt: {new_alt:.0f} ft (Loss: {actual_alt_loss:.1f} ft)")
        
        new_state = AircraftState(
            lat=new_lat, 
            lon=new_lon, 
            alt_ft=new_alt, 
            heading_deg=new_heading, 
            airspeed_kts=AircraftProfile.GLIDE_SPEED_KTS
        )
        
        reachable_states.append((new_state, turn_deg))
        
    return reachable_states
