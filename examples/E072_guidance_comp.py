#!/usr/bin/env python3
"""
[VERIFICATION SCRIPT - V2]
This script tests the real-time GuidanceComputer in isolation.

It simulates an aircraft perfectly following a pre-defined path and verifies
that the GuidanceComputer correctly updates its target waypoint as the
aircraft "captures" each point in the sequence.

V2: Corrects the FlightPath constructor to match the data model's requirements.
"""
import sys
from pathlib import Path
import time

sys.path.append(str(Path(__file__).resolve().parent.parent))

# --- Core Components for Testing ---
from shallnotcrash.path_planner.core import GuidanceComputer
from shallnotcrash.path_planner.data_models import AircraftState, FlightPath, Waypoint

def run_guidance_test():
    """Executes the focused test of the GuidanceComputer."""
    print("--- Commencing GuidanceComputer Verification Test ---")

    # 1. Initialize the GuidanceComputer
    guidance_computer = GuidanceComputer()

    # 2. Create a Mock FlightPath
    mock_waypoints = [
        Waypoint(lat=64.05000, lon=-22.58000, alt_ft=5000.0, airspeed_kts=65), # WP 0
        Waypoint(lat=64.04995, lon=-22.58045, alt_ft=4990.3, airspeed_kts=65), # WP 1
        Waypoint(lat=64.04991, lon=-22.58089, alt_ft=4980.6, airspeed_kts=65), # WP 2
        Waypoint(lat=64.04987, lon=-22.58134, alt_ft=4970.9, airspeed_kts=65), # WP 3
        Waypoint(lat=64.04983, lon=-22.58178, alt_ft=4961.2, airspeed_kts=65), # WP 4
        Waypoint(lat=64.04980, lon=-22.58221, alt_ft=4951.5, airspeed_kts=65), # WP 5
        Waypoint(lat=64.04976, lon=-22.58265, alt_ft=4941.8, airspeed_kts=65), # WP 6
        Waypoint(lat=64.04973, lon=-22.58308, alt_ft=4932.2, airspeed_kts=65), # WP 7
    ]
    
    # --- CORRECTED LINE ---
    # Provide dummy data for the required metadata fields.
    mock_path = FlightPath(
        waypoints=mock_waypoints,
        total_distance_nm=1.0,  # Dummy value
        estimated_time_min=1.0, # Dummy value
        emergency_profile='C172P_EMERGENCY_GLIDE' # Dummy value
    )

    # 3. Load the path into the GuidanceComputer
    guidance_computer.load_new_path(mock_path)
    print("-" * 20)

    # 4. Simulate the Flight
    print("Starting flight simulation loop...\n")
    for i, current_wp in enumerate(mock_path.waypoints):
        
        simulated_aircraft_state = AircraftState(
            lat=current_wp.lat,
            lon=current_wp.lon,
            alt_ft=current_wp.alt_ft,
            airspeed_kts=68.0,
            heading_deg=225.0
        )

        print(f"SIM STEP {i}: Aircraft is now AT WP #{i} ({current_wp.lat:.4f}, {current_wp.lon:.4f})")

        target_waypoint = guidance_computer.update_and_get_target(simulated_aircraft_state)
        
        target_index = guidance_computer.current_waypoint_index
        print(f"  -> GuidanceComputer directs pilot to fly TOWARDS WP #{target_index} (Alt: {target_waypoint.alt_ft:.0f} ft)")
        print("-" * 10)
        time.sleep(0.5)

    print("\n--- Test Complete ---")
    final_target_index = guidance_computer.current_waypoint_index
    print(f"Final state: Aircraft is at WP #{len(mock_path.waypoints)-1}, Guidance is targeting WP #{final_target_index}.")
    
    if final_target_index == len(mock_path.waypoints) - 1:
        print("\nSUCCESS: Guidance correctly advanced to the final waypoint.")
    else:
        print(f"\nFAILURE: Guidance got stuck at WP #{final_target_index}.")


if __name__ == "__main__":
    run_guidance_test()