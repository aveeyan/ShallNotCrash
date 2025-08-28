# In shallnotcrash/autopilot/core.py

import math
import sys
from .data_models import AutopilotState, ControlOutput, FlightPath, Waypoint
from .utils.coordinates import get_bearing_and_distance

# --- INSTRUMENTED PID CONTROLLER CLASS ---
class PIDController:
    """
    A PID controller with Derivative on Measurement and exposed internal terms for debugging.
    """
    def __init__(self, kp, ki, kd, setpoint=0, output_limits=(-1, 1)):
        self.kp, self.ki, self.kd = kp, ki, kd
        self.setpoint, self.output_limits = setpoint, output_limits
        self._integral = 0
        self._last_error = 0
        self._last_measurement = None
        
        # Exposed component terms for advanced diagnostics
        self.p_term = 0
        self.i_term = 0
        self.d_term = 0
        
    def update(self, current_value, dt):
        if dt <= 0:
            return 0
            
        error = self.setpoint - current_value
        
        # Proportional term
        self.p_term = self.kp * error
        
        # Integral term with anti-windup
        self._integral += error * dt
        # Apply integral limits to prevent windup
        self._integral = max(self.output_limits[0]/self.ki, min(self._integral, self.output_limits[1]/self.ki))
        self.i_term = self.ki * self._integral
        
        # Derivative term (using error derivative, not measurement derivative)
        if self._last_measurement is not None:
            derivative = (error - self._last_error) / dt
            self.d_term = self.kd * derivative
        else:
            self.d_term = 0
            
        self._last_error = error
        self._last_measurement = current_value
        
        # Final output is P + I + D
        output = self.p_term + self.i_term + self.d_term
        return max(self.output_limits[0], min(output, self.output_limits[1]))

class Autopilot:
    def __init__(self, flight_path: FlightPath):
        self.flight_path = flight_path
        self.target_waypoint_index = 0
        self.update_counter = 0

        # Initialize PID controllers for roll and pitch
        self.roll_controller = PIDController(
            kp=0.15,    # Increased for better response
            ki=0.001,   # Small integral to handle steady-state error
            kd=0.08,    # Reduced derivative to prevent over-damping
            output_limits=(-1, 1)
        )
        
        self.pitch_controller = PIDController(
            kp=0.12,    # Balanced proportional gain
            ki=0.002,   # Small integral
            kd=0.06,    # Moderate derivative
            output_limits=(-1, 1)
        )

        self.max_bank_angle = 25.0
        self.heading_to_roll_gain = 1.5  # Increased for better turning response
                
    def _display_debug_telemetry(self, **kwargs):
        parts = []
        order = ['wp', 'dist', 'hdg_err', 'tgt_roll', 'act_roll', 'ail_cmd', '|', 'tgt_alt', 'alt_err', 'tgt_pitch', 'act_pitch', 'elev_cmd']
        for key in order:
            if key == '|': parts.append('|'); continue
            if key not in kwargs: continue
            value = kwargs[key]
            if isinstance(value, float): parts.append(f"{key.upper()}: {value:7.1f}")
            else: parts.append(f"{key.upper()}: {str(value):>7}")
        print(f"\r{' '.join(parts)}", end="")

    def _update_navigation_targets(self, state: AutopilotState, target_wp: Waypoint):
        """Calculates and stores the target roll and pitch."""
        # Update Target Roll based on heading
        bearing_to_target, _ = get_bearing_and_distance(state.lat, state.lon, target_wp.lat, target_wp.lon)
        heading_error = (bearing_to_target - state.heading_deg + 180) % 360 - 180
        
        # Apply heading error to roll with limits
        self.target_roll = max(-self.max_bank_angle, min(heading_error * self.heading_to_roll_gain, self.max_bank_angle))
        
        # Update roll controller setpoint
        self.roll_controller.setpoint = self.target_roll

        # Update Target Pitch based on altitude
        altitude_error = target_wp.alt_ft - state.alt_ft
        # More sophisticated pitch calculation with vertical speed consideration
        self.target_pitch = max(-10, min(altitude_error * 0.008, 10))
        
        # Update pitch controller setpoint
        self.pitch_controller.setpoint = self.target_pitch

    def _calculate_control_outputs(self, state: AutopilotState, dt: float) -> tuple[float, float]:
        """Calculates aileron and elevator commands using PID controllers."""
        # Aileron command from roll controller
        aileron_cmd = self.roll_controller.update(state.roll_deg, dt)
        
        # Elevator command from pitch controller
        elevator_cmd = self.pitch_controller.update(state.pitch_deg, dt)
        
        return aileron_cmd, elevator_cmd

    def update(self, aircraft_state: AutopilotState, dt: float) -> ControlOutput:
        """Orchestrates the main control loop."""
        if dt <= 0: 
            return ControlOutput(0, 0, 0.0)

        if self.target_waypoint_index >= len(self.flight_path.waypoints):
            return ControlOutput(0, 0, 0, 0)

        target_wp = self.flight_path.waypoints[self.target_waypoint_index]

        _, distance_to_target = get_bearing_and_distance(aircraft_state.lat, aircraft_state.lon, target_wp.lat, target_wp.lon)
        if distance_to_target < 0.5:  # Slightly increased waypoint capture radius
            self.target_waypoint_index += 1
            if self.target_waypoint_index >= len(self.flight_path.waypoints):
                return ControlOutput(0, 0, 0, 0)
            target_wp = self.flight_path.waypoints[self.target_waypoint_index]

        # 1. Calculate desired state
        self._update_navigation_targets(aircraft_state, target_wp)
        
        # 2. Calculate control outputs to achieve desired state
        aileron_cmd, elevator_cmd = self._calculate_control_outputs(aircraft_state, dt)

        # 4. Display telemetry
        if self.update_counter % 5 == 0:
            bearing, _ = get_bearing_and_distance(aircraft_state.lat, aircraft_state.lon, target_wp.lat, target_wp.lon)
            heading_error = (bearing - aircraft_state.heading_deg + 180) % 360 - 180
            
            self._display_debug_telemetry(
                wp=self.target_waypoint_index, 
                dist=distance_to_target, 
                hdg_err=heading_error,
                tgt_roll=self.target_roll, 
                act_roll=aircraft_state.roll_deg, 
                ail_cmd=aileron_cmd,
                tgt_alt=target_wp.alt_ft, 
                alt_err=target_wp.alt_ft - aircraft_state.alt_ft,
                tgt_pitch=self.target_pitch, 
                act_pitch=aircraft_state.pitch_deg, 
                elev_cmd=elevator_cmd
            )
        self.update_counter += 1

        return ControlOutput(aileron_cmd, elevator_cmd, 0.0)
