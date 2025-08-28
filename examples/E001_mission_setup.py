# examples/E001_mission_setup.py
"""
[MISSION SETUP UTILITY]

Objective: To programmatically launch FlightGear and position the aircraft
at the precise starting coordinates for the BIKF "Overland Approach"
validation scenario. This ensures a consistent testing environment for
the Assister system.
"""
import sys
import os
import subprocess
import json

# --- [1. MISSION PARAMETERS] ---
# These parameters define the exact starting state for the test.
MISSION_PARAMETERS = {
    "AIRCRAFT": "c172p",
    "LATITUDE": 63.98,          # Starting latitude for BIKF overland approach
    "LONGITUDE": -22.3,         # Starting longitude
    "ALTITUDE_FT": 8000,        # Starting altitude in feet
    "HEADING_DEG": 280,         # Initial heading, pointed roughly towards BIKF
    "AIRSPEED_KTS": 110,        # Initial airspeed in knots (a reasonable cruise for the C172P)
}

# --- [2. NETWORK CONFIGURATION] ---
# This is critical for allowing the Assister to connect.
NETWORK_CONFIG = {
    "TELNET_PORT": 5501
}

def construct_fg_command() -> str:
    """
    Assembles the complete fgfs command string from the mission parameters.
    """
    # Base command
    command = ["fgfs"]

    # Aircraft and position
    command.append(f"--aircraft={MISSION_PARAMETERS['AIRCRAFT']}")
    command.append(f"--lat={MISSION_PARAMETERS['LATITUDE']}")
    command.append(f"--lon={MISSION_PARAMETERS['LONGITUDE']}")
    command.append(f"--altitude={MISSION_PARAMETERS['ALTITUDE_FT']}")
    command.append(f"--heading={MISSION_PARAMETERS['HEADING_DEG']}")
    command.append(f"--vc={MISSION_PARAMETERS['AIRSPEED_KTS']}") # Sets initial airspeed

    # Network interface for Assister
    command.append(f"--telnet={NETWORK_CONFIG['TELNET_PORT']}")
    
    # Optional: Add other useful flags
    command.append("--enable-real-weather-fetch")
    command.append("--timeofday=noon")

    return " ".join(command)

def launch_flightgear(command: str):
    """
    Launches FlightGear using the provided command string in a new process.
    This function is adapted from the E020 example.
    """
    try:
        # We split the command string back into a list for subprocess.Popen
        args = command.split()
        
        # Launch FlightGear in a new, non-blocking process
        process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        return {"success": True, "pid": process.pid, "command": command}
    except FileNotFoundError:
        return {
            "success": False,
            "error": "The 'fgfs' command was not found. Ensure FlightGear is installed and in your system's PATH.",
            "command": command
        }
    except Exception as e:
        return {"success": False, "error": str(e), "command": command}

if __name__ == "__main__":
    print("--- [FLIGHTGEAR MISSION SETUP] ---")
    
    # 1. Construct the command
    fg_command = construct_fg_command()
    print(f"\nGenerated FlightGear Command:\n{fg_command}\n")
    
    # 2. Launch the simulator
    print("Executing launch command...")
    launch_result = launch_flightgear(fg_command)
    
    # 3. Report the outcome
    if launch_result['success']:
        print("\n--- [SUCCESS] ---")
        print(f"FlightGear launched successfully.")
        print(f"Process ID (PID): {launch_result['pid']}")
        print("The simulator is now configured for the BIKF overland approach test.")
    else:
        print("\n--- [CRITICAL FAILURE] ---")
        print(f"Failed to launch FlightGear: {launch_result['error']}")
