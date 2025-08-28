# shallnotcrash/path_planner/utils/cost_functions.py
"""
[REFINED - V27]
The cost function is now aware of an ideal energy state. It penalizes moves
that result in the aircraft being too high above a target glide path,
forcing the A* search to favor longer, energy-dissipating paths over
unrealistic dives.
"""
from ..constants import PlannerConstants, AircraftProfile

# In path_planner/utils/cost_functions.py

def calculate_move_cost(
    distance_nm: float,
    turn_angle_deg: float,
    altitude_surplus_ft: float
) -> float:
    """
    [ENERGY-BALANCED - V28]
    Calculates the total cost of a move. This version penalizes deviations
    both ABOVE and BELOW the ideal glideslope, forcing the planner to seek a
    stable, balanced energy state and preventing it from exploring reckless,
    energy-deficient dives.
    """
    # 1. Base cost is the distance traveled.
    distance_cost = distance_nm

    # 2. Penalty for turning.
    turn_penalty = (abs(turn_angle_deg) / 180.0) * PlannerConstants.TURN_PENALTY_FACTOR

    # 3. Penalty for any deviation from the ideal glideslope (energy state).
    # We take the absolute value of the surplus. Being too low is now just as
    # costly as being too high. This provides a powerful guiding corridor for
    # the A* search.
    altitude_deviation_penalty = (abs(altitude_surplus_ft) / 100.0) * PlannerConstants.ALTITUDE_DEVIATION_PENALTY

    return distance_cost + turn_penalty + altitude_deviation_penalty
