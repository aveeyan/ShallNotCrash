# shallnotcrash/path_planner/utils/flight_dynamics.py
import math
from typing import List, Tuple
from ..data_models import AircraftState
from ..constants import PlannerConstants, AircraftProfile
from .coordinates import destination_point, calculate_bearing
from .calculations import calculate_turn_radius

def _average_headings(h1_deg: float, h2_deg: float) -> float:
    h1_rad, h2_rad = math.radians(h1_deg), math.radians(h2_deg)
    avg_x = (math.cos(h1_rad) + math.cos(h2_rad)) / 2.0
    avg_y = (math.sin(h1_rad) + math.sin(h2_rad)) / 2.0
    return (math.degrees(math.atan2(avg_y, avg_x)) + 360) % 360

def get_reachable_states(current_state: AircraftState, distance_to_goal_nm: float = None) -> List[Tuple[AircraftState, float]]:
    """
    Enhanced reachable states with proper turn radius constraints and adaptive resolution.
    """
    dist_per_step_nm = (AircraftProfile.GLIDE_SPEED_KTS * PlannerConstants.TIME_DELTA_SEC) / 3600.0
    base_alt_loss_ft = (dist_per_step_nm * PlannerConstants.FEET_PER_NAUTICAL_MILE) / AircraftProfile.GLIDE_RATIO
    
    # Calculate minimum turn radius for current speed
    min_turn_radius_nm = calculate_turn_radius(current_state.airspeed_kts)
    
    # Calculate maximum turn rate based on physics and turn radius
    max_turn_rate_deg_s = (current_state.airspeed_kts * 6076.12) / (min_turn_radius_nm * 2 * math.pi) * 360
    max_turn_per_step = max_turn_rate_deg_s * PlannerConstants.TIME_DELTA_SEC
    
    # Adaptive turn resolution
    if distance_to_goal_nm is None or distance_to_goal_nm > 5.0:
        turn_options = [0, -15, 15, -30, 30, -max_turn_per_step, max_turn_per_step]
    else:
        turn_options = [0, -10, 10, -max_turn_per_step/2, max_turn_per_step/2]
    
    reachable_states = []
    
    for turn_deg in turn_options:
        # Clamp turn to maximum physically possible
        turn_deg = max(-max_turn_per_step, min(max_turn_per_step, turn_deg))
        
        # Calculate turn penalty based on banking
        abs_turn = abs(turn_deg)
        if abs_turn == 0:
            turn_penalty_factor = 1.0
        else:
            required_bank_angle = min(abs_turn / max_turn_per_step * AircraftProfile.STANDARD_BANK_ANGLE_DEG, 45.0)
            bank_factor = 1 + (required_bank_angle / 45.0) ** 1.5
            turn_penalty_factor = bank_factor * AircraftProfile.TURN_DRAG_PENALTY_FACTOR
        
        actual_alt_loss = base_alt_loss_ft * turn_penalty_factor
        
        # Calculate new heading and position
        new_heading = (current_state.heading_deg + turn_deg) % 360
        
        # Use more accurate position calculation for turns
        if abs_turn > 0:
            # For turns, calculate arc movement
            turn_radius_nm = calculate_turn_radius(current_state.airspeed_kts)
            arc_angle_deg = turn_deg
            arc_distance_nm = (abs(arc_angle_deg) * math.pi / 180) * turn_radius_nm
            
            # Calculate position along turn arc
            avg_heading = _average_headings(current_state.heading_deg, new_heading)
            new_lat, new_lon = destination_point(
                current_state.lat, current_state.lon, 
                avg_heading, arc_distance_nm
            )
        else:
            # Straight movement
            new_lat, new_lon = destination_point(
                current_state.lat, current_state.lon, 
                new_heading, dist_per_step_nm
            )
        
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

def get_minimum_turn_radius_nm(airspeed_kts: float) -> float:
    """Calculate minimum turn radius for the aircraft at given airspeed."""
    return calculate_turn_radius(airspeed_kts)
