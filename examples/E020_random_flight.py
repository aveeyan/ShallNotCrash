import sys
from pathlib import Path
import subprocess
import json

# Add project root to Python path
sys.path.append(str(Path(__file__).parent.parent))

# Standard Libraries
import json

# Local Imports
from shallnotcrash.random_flight import RandomFlight

def launch_flightgear(command: str):
    """Launch FlightGear with the generated command."""
    try:
        # Split command into arguments for subprocess
        args = command.split()
        
        # Launch FlightGear in a new process (non-blocking)
        process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        return {
            "success": True,
            "pid": process.pid,
            "command": command
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "command": command
        }

# Create generator
flight_gen = RandomFlight()

# Generate flight parameters (customizable)
response = flight_gen.generate(
    airport_icao="BIKF",
    altitude_ft=4000,
    heading=69
)

# Print the generated configuration
print("Flight Configuration:")
print(json.dumps(response, indent=2))

if response['success']:
    # Extract the launch command
    fg_command = response['data']['fg_launch_command']
    
    # Ask for user confirmation
    user_input = input("\nLaunch FlightGear with these parameters? (y/n): ").strip().lower()
    
    if user_input == 'y':
        print(f"\nExecuting: {fg_command}")
        launch_result = launch_flightgear(fg_command)
        
        if launch_result['success']:
            print(f"\nFlightGear launched successfully (PID: {launch_result['pid']})")
        else:
            print(f"\nFailed to launch FlightGear: {launch_result['error']}")
    else:
        print("\nFlightGear launch cancelled.")
else:
    print("\nError generating flight parameters:")
    print(response['message'])