# shallnotcrash/path_planner/utils/cost_functions.py
"""
[REFINED - V27]
The cost function is now aware of an ideal energy state. It penalizes moves
that result in the aircraft being too high above a target glide path,
forcing the A* search to favor longer, energy-dissipating paths over
unrealistic dives.
"""
from ..constants import PlannerConstants, AircraftProfile

def calculate_move_cost(
    distance_nm: float, 
    turn_angle_deg: float, 
    altitude_surplus_ft: float  # We now pass in the surplus directly
) -> float:
    """
    Calculates the total cost of a move, including distance, turn, and altitude deviation.
    """
    # 1. Base cost is the distance traveled.
    distance_cost = distance_nm
    
    # 2. Penalty for turning.
    turn_penalty = (abs(turn_angle_deg) / 180.0) * PlannerConstants.TURN_PENALTY_FACTOR
    
    # 3. Penalty for being above the ideal glide path.
    altitude_deviation_penalty = 0.0
    if altitude_surplus_ft > 0:
        # The penalty scales with how far above the ideal path we are.
        # This makes the planner strongly prefer to stay near the target slope.
        altitude_deviation_penalty = (altitude_surplus_ft / 100.0) * PlannerConstants.ALTITUDE_DEVIATION_PENALTY
        
    return distance_cost + turn_penalty + altitude_deviation_penalty
