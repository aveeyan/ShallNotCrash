# shallnotcrash/path_planner/utils/cost_functions.py
from ..constants import PlannerConstants

def calculate_move_cost(distance_nm: float, turn_angle_deg: float, altitude_surplus_ft: float) -> float:
    distance_cost = distance_nm
    turn_penalty = (abs(turn_angle_deg) / 180.0) * PlannerConstants.TURN_PENALTY_FACTOR
    altitude_deviation_penalty = 0.0
    if altitude_surplus_ft < 0:
        altitude_deviation_penalty = (abs(altitude_surplus_ft) / 100.0) * PlannerConstants.ALTITUDE_DEVIATION_PENALTY
    if altitude_surplus_ft > PlannerConstants.HIGH_ALTITUDE_THRESHOLD_FT and turn_angle_deg != 0:
        turn_penalty *= PlannerConstants.HIGH_ALTITUDE_TURN_INCENTIVE
    return distance_cost + turn_penalty + altitude_deviation_penalty
