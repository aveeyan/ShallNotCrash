# In shallnotcrash/autopilot/core.py

import math
import sys
from .data_models import AutopilotState, ControlOutput, FlightPath, Waypoint
from .utils.coordinates import get_bearing_and_distance

# --- PID CONTROLLER CLASS (Unchanged) ---
class PIDController:
    """A robust PID controller with integral anti-windup."""
    def __init__(self, kp, ki, kd, setpoint=0, output_limits=(-1, 1)):
        self.kp, self.ki, self.kd = kp, ki, kd
        self.setpoint, self.output_limits = setpoint, output_limits
        self._proportional = self._integral = self._derivative = self._last_error = 0

    def update(self, current_value, dt):
        error = self.setpoint - current_value
        self._proportional = self.kp * error
        self._integral += self.ki * error * dt
        self._integral = max(self.output_limits[0], min(self._integral, self.output_limits[1]))
        if dt > 0:
            self._derivative = self.kd * (error - self._last_error) / dt
        else:
            self._derivative = 0
        self._last_error = error
        output = self._proportional + self._integral + self._derivative
        return max(self.output_limits[0], min(output, self.output_limits[1]))

# --- THE RE-ARCHITECTED AUTOPILOT ---
class Autopilot:
    """
    A cascaded PID-based autopilot for navigation and attitude hold.
    """
    def __init__(self, flight_path: FlightPath):
        self.flight_path = flight_path
        self.target_waypoint_index = 0
        self.roll_controller = PIDController(kp=0.03, ki=0.001, kd=0.05, output_limits=(-1, 1))
        self.heading_to_roll_gain = 2.0
        self.max_bank_angle = 25.0
        self.pitch_controller = PIDController(kp=0.005, ki=0.001, kd=0.002, output_limits=(-1, 1))
        
    # --- NEW METHOD: LIVE TELEMETRY DISPLAY ---
    def _display_telemetry(self, **kwargs):
        """Formats and prints a single line of telemetry data to the console."""
        status_string = (
            f"WP: {kwargs.get('wp_idx', 0):>2} | "
            f"HDG ERR: {kwargs.get('hdg_err', 0):5.1f}° | "
            f"TGT ROLL: {kwargs.get('tgt_roll', 0):5.1f}° | "
            f"ACT ROLL: {kwargs.get('act_roll', 0):5.1f}° | "
            f"AIL CMD: {kwargs.get('ail_cmd', 0):+5.2f} | "
            f"TGT ALT: {kwargs.get('tgt_alt', 0):7.1f}ft | "
            f"ACT ALT: {kwargs.get('act_alt', 0):7.1f}ft | "
            f"ELEV CMD: {kwargs.get('elev_cmd', 0):+5.2f}"
        )
        # Use carriage return to print on the same line
        sys.stdout.write(f"\r{status_string}")
        sys.stdout.flush()

    def update(self, aircraft_state: AutopilotState, dt: float) -> ControlOutput:
        """
        Executes one cycle of the autopilot logic.
        """
        if self.target_waypoint_index >= len(self.flight_path.waypoints):
            print("\nEnd of flight path reached.")
            return ControlOutput(0, 0, 0, 0)

        target_wp = self.flight_path.waypoints[self.target_waypoint_index]
        
        bearing_to_target, distance_to_target = get_bearing_and_distance(
            aircraft_state.lat, aircraft_state.lon, target_wp.lat, target_wp.lon
        )
        
        if distance_to_target < 0.1:
            self.target_waypoint_index += 1
            print(f"\nSwitching to waypoint {self.target_waypoint_index}")
            return ControlOutput(0, 0, 0, 0)

        heading_error = bearing_to_target - aircraft_state.heading_deg
        heading_error = (heading_error + 180) % 360 - 180

        target_roll = heading_error * self.heading_to_roll_gain
        target_roll = max(-self.max_bank_angle, min(target_roll, self.max_bank_angle))
        
        self.roll_controller.setpoint = target_roll
        aileron_cmd = self.roll_controller.update(aircraft_state.roll_deg, dt)
        
        self.pitch_controller.setpoint = target_wp.alt_ft
        elevator_cmd = -self.pitch_controller.update(aircraft_state.alt_ft, dt)

        rudder_cmd = 0.0
        
        # --- CALL THE TELEMETRY DISPLAY ---
        self._display_telemetry(
            wp_idx=self.target_waypoint_index,
            hdg_err=heading_error,
            tgt_roll=target_roll,
            act_roll=aircraft_state.roll_deg,
            ail_cmd=aileron_cmd,
            tgt_alt=target_wp.alt_ft,
            act_alt=aircraft_state.alt_ft,
            elev_cmd=elevator_cmd
        )

        return ControlOutput(aileron_cmd, elevator_cmd, rudder_cmd)
    