# In examples/E080_autopilot.py

import sys
import time
from pathlib import Path
import subprocess
import multiprocessing  # --- VISUALIZATION: Import multiprocessing

# Add project root to Python path
sys.path.append(str(Path(__file__).parent.parent))

# --- Local Module Imports ---
from shallnotcrash.random_flight import RandomFlight
from shallnotcrash.fg_interface import FGConnection
from shallnotcrash.constants.flightgear import FGProps
from shallnotcrash.autopilot.core import Autopilot, FlightPath, Waypoint, AutopilotState
from shallnotcrash.autopilot.data_models import ControlOutput, TelemetryPacket  # --- VISUALIZATION: Import TelemetryPacket
from shallnotcrash.autopilot.visualization.panel import run_visualizer  # --- VISUALIZATION: Import the panel runner

# --- Helper Functions (Unchanged) ---

def launch_flightgear(command: str) -> subprocess.Popen:
    """Launch FlightGear and return the process object."""
    args = command.split()
    return subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def read_state_from_fg(fg: FGConnection) -> AutopilotState | None:
    """Reads aircraft properties from FlightGear."""
    try:
        lat = fg.get(FGProps.FLIGHT.LATITUDE)['data']['value']
        lon = fg.get(FGProps.FLIGHT.LONGITUDE)['data']['value']
        alt = fg.get(FGProps.FLIGHT.ALTITUDE_FT)['data']['value']
        hdg = fg.get(FGProps.FLIGHT.HEADING_DEG)['data']['value']
        roll = fg.get(FGProps.FLIGHT.ROLL_DEG)['data']['value']
        pitch = fg.get(FGProps.FLIGHT.PITCH_DEG)['data']['value']
        speed = fg.get(FGProps.FLIGHT.AIRSPEED_KT)['data']['value']
        return AutopilotState(lat, lon, alt, hdg, roll, pitch, speed)
    except (KeyError, TypeError):
        return None

def write_controls_to_fg(fg: FGConnection, controls: ControlOutput):
    """Writes control commands to FlightGear."""
    fg.set(FGProps.CONTROLS.AILERON, controls.aileron_cmd)
    fg.set(FGProps.CONTROLS.ELEVATOR, controls.elevator_cmd)
    fg.set(FGProps.CONTROLS.RUDDER, controls.rudder_cmd)
    fg.set(FGProps.ENGINE.THROTTLE, 0.0)

# --- Main Application ---

def main():
    """
    A self-contained script to launch FlightGear and run the autopilot,
    now with an integrated real-time visualization panel.
    """
    print("--- Fully Automated Autopilot Demonstration ---")
    
    # 1. DEFINE FLIGHT PLAN
    static_waypoints = [
        Waypoint(lat=64.0500, lon=-22.5800, alt_ft=5000, airspeed_kts=65),
        Waypoint(lat=64.04, lon=-22.57, alt_ft=4800, airspeed_kts=65),
        Waypoint(lat=64.03, lon=-22.56, alt_ft=4600, airspeed_kts=65),
        Waypoint(lat=64.02, lon=-22.55, alt_ft=4400, airspeed_kts=65),
        Waypoint(lat=64.00, lon=-22.54, alt_ft=4000, airspeed_kts=65),
        Waypoint(lat=63.98, lon=-22.54, alt_ft=3600, airspeed_kts=65),
        Waypoint(lat=63.9632, lon=-22.5383, alt_ft=1119, airspeed_kts=65),
    ]
    path_to_follow = FlightPath(waypoints=static_waypoints)
    autopilot = Autopilot(path_to_follow)
    print(f"Loaded static flight path with {len(path_to_follow.waypoints)} waypoints.")

    # --- VISUALIZATION SETUP (MODIFIED) ---
    print("Initializing visualization panel...")
    telemetry_queue = multiprocessing.Queue()
    # Pass the entire flight path object to the visualizer process
    vis_process = multiprocessing.Process(target=run_visualizer, args=(telemetry_queue, path_to_follow))
    vis_process.start()
    # ---------------------------

    # 2. LAUNCH FLIGHTGEAR
    flight_gen = RandomFlight()
    response = flight_gen.generate(airport_icao="BIKF", altitude_ft=5000, heading=135)
    if not response['success']:
        print(f"! FATAL: Could not generate flight parameters: {response['message']}")
        return

    fg_command = response['data']['fg_launch_command']
    fg_process = None
    try:
        print(f"Launching FlightGear normally...")
        fg_process = launch_flightgear(fg_command)
        print(f"FlightGear process started (PID: {fg_process.pid}). Waiting for simulator to load...")
    except Exception as e:
        print(f"! FATAL: Failed to launch FlightGear: {e}")
        if vis_process.is_alive(): vis_process.terminate()
        return

    # 3. CONNECT AND IMMEDIATELY FREEZE
    fg = FGConnection()
    # ... (Connection logic is unchanged) ...
    max_retries = 15
    for i in range(max_retries):
        print(f"\rAttempting to connect to FlightGear... ({i+1}/{max_retries})", end="")
        result = fg.connect()
        if result["success"]:
            print("\nSuccessfully connected to FlightGear.")
            print("Freezing simulation programmatically...")
            fg.set(FGProps.SIMULATION.FREEZE, 1)
            time.sleep(0.5)
            break
        time.sleep(5)
    else:
        print("\n! FATAL: Could not connect to FlightGear after multiple attempts.")
        if fg_process: fg_process.kill()
        if vis_process.is_alive(): vis_process.terminate()
        return

    # 4. RUN AUTOPILOT
    last_time = time.time()
    try:
        print("Autopilot taking control. Un-freezing simulation...")
        fg.set(FGProps.SIMULATION.FREEZE, 0)

        while autopilot.target_waypoint_index < len(path_to_follow.waypoints):
            current_time = time.time()
            dt = current_time - last_time
            if dt <= 1e-6: continue
            last_time = current_time

            aircraft_state = read_state_from_fg(fg)
            if not aircraft_state:
                time.sleep(0.5)
                continue

            control_commands = autopilot.update(aircraft_state, dt)
            write_controls_to_fg(fg, control_commands)

            # --- SEND TELEMETRY TO VISUALIZER ---
            if not telemetry_queue.full():
                wp_idx = min(autopilot.target_waypoint_index, len(path_to_follow.waypoints) - 1)
                target_wp = path_to_follow.waypoints[wp_idx]
                
                # CRITICAL FIX: Read from the public 'target_roll' attribute,
                # NOT the non-existent 'roll_controller'.
                packet = TelemetryPacket(
                    current_lat=aircraft_state.lat, current_lon=aircraft_state.lon, current_alt=aircraft_state.alt_ft,
                    current_roll=aircraft_state.roll_deg, target_roll=autopilot.target_roll,
                    target_alt=target_wp.alt_ft,
                    flight_path_lats=[wp.lat for wp in path_to_follow.waypoints],
                    flight_path_lons=[wp.lon for wp in path_to_follow.waypoints],
                    flight_path_alts=[wp.alt_ft for wp in path_to_follow.waypoints]
                )
                telemetry_queue.put(packet)
            # ------------------------------------
            # ------------------------------------
            
            time.sleep(1/30) # Maintain a consistent loop rate

        print("\n--- Flight path complete. ---")

    except KeyboardInterrupt:
        print("\n--- Autopilot interrupted by user. ---")
    except Exception as e:
        print(f"\n! An unexpected error occurred during flight: {e}")
    finally:
        # 5. CLEANUP
        print("\nDisengaging autopilot and shutting down.")
        try:
            print("Freezing simulation...")
            fg.set(FGProps.SIMULATION.FREEZE, 1)
            write_controls_to_fg(fg, ControlOutput(0,0,0))
            fg.disconnect()
            print("Disconnected gracefully.")
        except Exception as e:
            print(f"! WARN: Could not disconnect gracefully: {e}")
        
        if fg_process:
            print(f"Terminating FlightGear process (PID: {fg_process.pid})...")
            fg_process.kill()
            fg_process.wait()
            print("FlightGear process terminated.")

        # --- CLEANUP VISUALIZER ---
        if 'vis_process' in locals() and vis_process.is_alive():
            print("Terminating visualization process...")
            vis_process.terminate()
        # --------------------------

if __name__ == "__main__":
    main()
