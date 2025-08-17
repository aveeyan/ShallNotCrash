# shallnotcrash/path_planner/utils/flight_dynamics.py
"""
Models the aircraft's performance to generate reachable next states for the A* search.
"""
from typing import List, Tuple
from ..data_models import AircraftState, Waypoint
from ..constants import PlannerConstants, AircraftProfile
from .coordinates import destination_point, calculate_bearing

def get_reachable_states(current_state: AircraftState, goal_waypoint: Waypoint) -> List[Tuple[AircraftState, float]]:
    """
    Generates a robust set of next possible aircraft states.
    """
    # --- [FIX] Removed the incorrect ".PERFORMANCE" attribute from all calls ---
    dist_per_step_nm = (AircraftProfile.GLIDE_SPEED_KTS * PlannerConstants.TIME_DELTA_SEC) / 3600.0
    alt_loss_per_step_ft = (dist_per_step_nm * PlannerConstants.FEET_PER_NAUTICAL_MILE) / AircraftProfile.GLIDE_RATIO
    max_turn_per_step = PlannerConstants.DEFAULT_TURN_RATE_DEG_S * PlannerConstants.TIME_DELTA_SEC

    turn_angles = [0, -max_turn_per_step, max_turn_per_step]
    
    bearing_to_goal = calculate_bearing(current_state.lat, current_state.lon, goal_waypoint.lat, goal_waypoint.lon)
    required_turn = bearing_to_goal - current_state.heading_deg
    if required_turn > 180: required_turn -= 360
    if required_turn < -180: required_turn += 360
    
    smart_turn = max(-max_turn_per_step, min(max_turn_per_step, required_turn))
    turn_angles.append(smart_turn)

    reachable_states = []
    for turn_deg in set(turn_angles):
        new_heading = (current_state.heading_deg + turn_deg) % 360
        new_lat, new_lon = destination_point(current_state.lat, current_state.lon, new_heading, dist_per_step_nm)
        new_alt = current_state.alt_ft - alt_loss_per_step_ft
        
        new_state = AircraftState(
            lat=new_lat, lon=new_lon, alt_ft=new_alt, heading_deg=new_heading,
            airspeed_kts=AircraftProfile.GLIDE_SPEED_KTS
        )
        reachable_states.append((new_state, turn_deg))
        
    return reachable_states
