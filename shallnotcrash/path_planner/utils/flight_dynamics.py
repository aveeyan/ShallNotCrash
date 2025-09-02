# shallnotcrash/path_planner/utils/flight_dynamics.py
import math
from typing import List, Tuple
from ..data_models import AircraftState
from ..constants import PlannerConstants, AircraftProfile
from .coordinates import destination_point

def _average_headings(h1_deg: float, h2_deg: float) -> float:
    h1_rad, h2_rad = math.radians(h1_deg), math.radians(h2_deg)
    avg_x = (math.cos(h1_rad) + math.cos(h2_rad)) / 2.0
    avg_y = (math.sin(h1_rad) + math.sin(h2_rad)) / 2.0
    return (math.degrees(math.atan2(avg_y, avg_x)) + 360) % 360

def get_reachable_states(current_state: AircraftState, distance_to_goal_nm: float = None) -> List[Tuple[AircraftState, float]]:
    """
    Enhanced reachable states with adaptive turn resolution and banking physics.
    Provides more turn options when far from goal, fewer when close for efficiency.
    """
    dist_per_step_nm = (AircraftProfile.GLIDE_SPEED_KTS * PlannerConstants.TIME_DELTA_SEC) / 3600.0
    base_alt_loss_ft = (dist_per_step_nm * PlannerConstants.FEET_PER_NAUTICAL_MILE) / AircraftProfile.GLIDE_RATIO
    
    # Calculate maximum turn rate based on physics
    max_turn_per_step = AircraftProfile.STANDARD_TURN_RATE_DEG_S * PlannerConstants.TIME_DELTA_SEC
    
    # [ENHANCED] Adaptive turn resolution - more options when maneuvering needed
    if distance_to_goal_nm is None or distance_to_goal_nm > 5.0:
        # Far from goal: use full resolution for better path planning
        turn_increment = max_turn_per_step / 4.0  # 8 turn options + straight
        turn_options = [
            0,  # Straight
            -turn_increment, turn_increment,  # Small turns
            -turn_increment * 2, turn_increment * 2,  # Medium turns  
            -turn_increment * 3, turn_increment * 3,  # Large turns
            -max_turn_per_step, max_turn_per_step  # Maximum turns
        ]
    else:
        # Close to goal: reduce options for efficiency, focus on precision
        turn_increment = max_turn_per_step / 2.0
        turn_options = [
            0,  # Straight
            -turn_increment, turn_increment,  # Small turns
            -max_turn_per_step, max_turn_per_step  # Maximum turns
        ]
    
    reachable_states = []
    
    for turn_deg in turn_options:
        # [ENHANCED] More realistic turn physics
        abs_turn = abs(turn_deg)
        
        # Calculate drag penalty based on banking angle needed for the turn
        if abs_turn == 0:
            turn_penalty_factor = 1.0
        else:
            # Bank angle required for this turn rate (simplified)
            required_bank_angle = min(abs_turn / max_turn_per_step * AircraftProfile.STANDARD_BANK_ANGLE_DEG, 45.0)
            # Drag increases with square of bank angle (approximation)
            bank_factor = 1 + (required_bank_angle / 45.0) ** 1.5
            turn_penalty_factor = bank_factor * AircraftProfile.TURN_DRAG_PENALTY_FACTOR
        
        actual_alt_loss = base_alt_loss_ft * turn_penalty_factor if turn_deg != 0 else base_alt_loss_ft
        
        # Calculate new position using average heading (more accurate)
        new_heading = (current_state.heading_deg + turn_deg) % 360
        avg_heading = _average_headings(current_state.heading_deg, new_heading)
        new_lat, new_lon = destination_point(current_state.lat, current_state.lon, avg_heading, dist_per_step_nm)
        
        new_alt = current_state.alt_ft - actual_alt_loss
        if new_alt < -500: 
            continue  # Skip states that crash into ground
            
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
    speed_mps = airspeed_kts * PlannerConstants.METERS_PER_SECOND_PER_KNOT
    bank_angle_rad = math.radians(AircraftProfile.STANDARD_BANK_ANGLE_DEG)
    radius_m = (speed_mps ** 2) / (PlannerConstants.G_ACCEL_MPS2 * math.tan(bank_angle_rad))
    return radius_m * PlannerConstants.METERS_TO_NM
