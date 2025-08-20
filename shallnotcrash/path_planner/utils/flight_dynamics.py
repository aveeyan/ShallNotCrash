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

def get_reachable_states(current_state: AircraftState) -> List[Tuple[AircraftState, float]]:
    """Generates the next possible states using corrected geometry."""
    # Calculate movement parameters FIRST
    dist_per_step_nm = (AircraftProfile.GLIDE_SPEED_KTS * PlannerConstants.TIME_DELTA_SEC) / 3600.0
    alt_loss_per_step_ft = (dist_per_step_nm * PlannerConstants.FEET_PER_NAUTICAL_MILE) / AircraftProfile.GLIDE_RATIO
    turn_angle_per_step = AircraftProfile.STANDARD_TURN_RATE_DEG_S * PlannerConstants.TIME_DELTA_SEC
    
    # DEBUG: Print the calculated values BEFORE using them
    print(f"DEBUG Flight Dynamics:")
    print(f"  Glide Speed: {AircraftProfile.GLIDE_SPEED_KTS} KTS")
    print(f"  Time Delta: {PlannerConstants.TIME_DELTA_SEC} sec")
    print(f"  Distance per step: {dist_per_step_nm:.3f} NM")
    print(f"  Feet per NM: {PlannerConstants.FEET_PER_NAUTICAL_MILE}")
    print(f"  Glide Ratio: {AircraftProfile.GLIDE_RATIO}")
    print(f"  Altitude loss per step: {alt_loss_per_step_ft:.1f} ft")
    print(f"  Current altitude: {current_state.alt_ft:.0f} ft")
    print(f"  Turn angle per step: {turn_angle_per_step:.1f}°")
    
    reachable_states = []
    
    for turn_deg in [0, -turn_angle_per_step, turn_angle_per_step]:
        new_heading = (current_state.heading_deg + turn_deg) % 360
        
        # Use the mathematically correct averaging function
        avg_heading = _average_headings(current_state.heading_deg, new_heading)
        
        new_lat, new_lon = destination_point(current_state.lat, current_state.lon, avg_heading, dist_per_step_nm)
        new_alt = current_state.alt_ft - alt_loss_per_step_ft
        
        new_state = AircraftState(
            lat=new_lat, 
            lon=new_lon, 
            alt_ft=new_alt, 
            heading_deg=new_heading, 
            airspeed_kts=AircraftProfile.GLIDE_SPEED_KTS
        )
        
        reachable_states.append((new_state, turn_deg))
        
    return reachable_states
