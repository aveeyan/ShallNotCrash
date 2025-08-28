# shallnotcrash/path_planner/utils/cost_functions.py
"""
[DEFINITIVE CALIBRATION - V29]
The cost function's core logic is corrected. It no longer penalizes the
planner for being in a necessary high-energy state (above the ideal
glideslope). Instead, it only penalizes energy-deficient states (below the
glideslope). This resolves the conflict between the heuristic and the cost
function, enabling successful long-range energy management.
"""
from ..constants import PlannerConstants, AircraftProfile

def calculate_move_cost(
    distance_nm: float,
    turn_angle_deg: float,
    altitude_surplus_ft: float
) -> float:
    """
    [ENERGY-ALIGNED - V29]
    Calculates the total cost of a move. This definitive version aligns the
    cost function with the energy-aware heuristic.

    - A surplus of altitude (positive surplus) is a resource and is NOT penalized.
    - A deficit of altitude (negative surplus) is a critical, energy-deficient
      state and IS penalized.

    This allows the planner to freely explore the long, energy-dissipating
    paths that the heuristic correctly identifies as necessary.
    """
    # 1. Base cost is the distance traveled.
    distance_cost = distance_nm

    # 2. Penalty for turning.
    turn_penalty = (abs(turn_angle_deg) / 180.0) * PlannerConstants.TURN_PENALTY_FACTOR

    # 3. Penalty ONLY for being BELOW the ideal glideslope (energy deficit).
    altitude_deviation_penalty = 0.0
    if altitude_surplus_ft < 0:
        # Only penalize negative surplus (being too low).
        altitude_deviation_penalty = (abs(altitude_surplus_ft) / 100.0) * PlannerConstants.ALTITUDE_DEVIATION_PENALTY

    return distance_cost + turn_penalty + altitude_deviation_penalty
