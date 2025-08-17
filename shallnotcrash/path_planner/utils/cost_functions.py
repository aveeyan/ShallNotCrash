# shallnotcrash/path_planner/utils/cost_functions.py
"""
Defines the cost function for the A* search algorithm.
The cost represents the "effort" required to move between states.
"""
# --- [FIX] Import the PlannerConstants class directly ---
from ..constants import PlannerConstants

def calculate_move_cost(distance_nm: float, turn_angle_deg: float) -> float:
    """
    Calculates the cost of moving from one state to another.
    The cost is the distance traveled plus a penalty for turning.
    """
    # --- [FIX] Access TURN_PENALTY_FACTOR from the PlannerConstants class ---
    turn_penalty = (abs(turn_angle_deg) / 180.0) * PlannerConstants.TURN_PENALTY_FACTOR
    
    # The total cost is the physical distance plus the turning penalty.
    return distance_nm + turn_penalty
