# In autopilot/constants.py

class AutopilotConstants:
    # --- NAVIGATION ---
    WAYPOINT_CAPTURE_RADIUS_NM = 0.05  # How close we need to be to a waypoint to switch to the next

    # --- CONTROL LIMITS ---
    MAX_BANK_ANGLE_DEG = 25.0   # The autopilot will not command a bank steeper than this
    MAX_PITCH_ANGLE_DEG = 15.0  # Max pitch up command
    MIN_PITCH_ANGLE_DEG = -15.0 # Max pitch down command

    # --- PID GAINS ---
    # These values are highly dependent on the flight model and will require extensive tuning.

    # Roll Controller: Controls ailerons to achieve a target bank angle.
    # This is a fast-acting loop.
    ROLL_PID = {
        "Kp": 0.08,  # Proportional: High gain for quick response to bank error
        "Ki": 0.01,  # Integral: Corrects for steady-state error (e.g., from aerodynamic trim)
        "Kd": 0.03   # Derivative: Dampens oscillations
    }

    # Heading Controller: Calculates a target bank angle to correct heading error.
    # This is a slower, outer loop that commands the Roll Controller.
    HEADING_PID = {
        "Kp": 0.9,   # Proportional: A 10-degree error results in a ~9-degree bank command
        "Ki": 0.05,  # Integral: Corrects for crosswind
        "Kd": 0.2
    }

    # Pitch Controller: Controls the elevator to achieve a target pitch angle.
    # This is used to hold the glide slope.
    PITCH_PID = {
        "Kp": 0.09,
        "Ki": 0.02,
        "Kd": 0.04
    }

    # Altitude Controller: Calculates a target pitch angle to correct altitude error.
    # This is the outer loop that commands the Pitch Controller.
    ALTITUDE_PID = {
        "Kp": 0.02,  # Proportional: A 100ft error results in a 2-degree pitch command
        "Ki": 0.001,
        "Kd": 0.01
    }