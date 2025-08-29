#!/usr/bin/env python3
"""
Example E140: Emergency Detection System Test

This script serves as a practical example of how to use the 'shallnotcrash'
emergency detection module. It simulates a flight scenario with abnormal
telemetry and passes it to the detection pipeline, printing the final diagnosis.

This file is intended to be run as a standalone script from the project root.
"""
import sys
import os
import json

# --- Path Setup ---
# This is the crucial part that allows Python to find the 'shallnotcrash' package.
# It adds the project's root directory to the list of places Python looks for modules.
def setup_project_path():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        print(f"Added '{project_root}' to Python path.")

setup_project_path()

# --- Imports from our package ---
# With the path set up, we can now import from our library as if it were installed.
try:
    from shallnotcrash.emergency.core import detect_emergency
    from shallnotcrash.emergency.analyzers.anomaly_detector import FlightPhase
except ImportError as e:
    print(f"Error: Could not import the 'shallnotcrash' module.")
    print(f"Please ensure you are running this script from the project root directory.")
    print(f"Details: {e}")
    sys.exit(1)


def run_detection_scenario(scenario_name: str, telemetry: dict, phase: FlightPhase):
    """Runs a single detection scenario and prints the results."""
    print(f"\n--- Running Scenario: {scenario_name} ---")
    print(f"Flight Phase: {phase.name}")
    print(f"Input Telemetry:\n{json.dumps(telemetry, indent=2)}\n")

    # Call the main detection function from our package.
    result = detect_emergency(
        telemetry=telemetry,
        flight_phase=phase
    )

    print("--- Detection Result ---")
    # Use json to pretty-print the result dictionary
    print(json.dumps(result, indent=2, default=str))


def main():
    """Main function to define and run test scenarios."""
    print("==========================================")
    print("= ShallNotCrash Emergency System Test    =")
    print("==========================================")

    # --- Scenario 1: Engine Degradation during Cruise ---
    # Simulates a developing engine issue with high vibration and dropping RPM/pressure.
    engine_degradation_telemetry = {
        'rpm': 1950.0,          # Lower than normal cruise RPM (e.g., 2300)
        'oil_pressure': 45.0,   # Dropping from a normal of ~65 psi
        'fuel_flow': 11.5,      # May be slightly erratic
        'vibration': 2.1,       # Significantly higher than normal (< 0.5)
        'g_load': 1.0,
        'cht': 440.0,           # Cylinder head temperature might rise
        'egt': 1350.0,
        'oil_temp': 235.0,      # Oil temperature might also rise
        'aileron': 0.0,
        'elevator': -0.05,      # Minor trim change to compensate for power loss
        'rudder': 0.02
    }
    run_detection_scenario(
        "Engine Degradation",
        engine_degradation_telemetry,
        FlightPhase.CRUISE
    )

    # --- Scenario 2: Normal Flight Operations ---
    # This should result in a 'NORMAL' pattern with high confidence.
    normal_telemetry = {
        'rpm': 2345.0,
        'oil_pressure': 68.0,
        'fuel_flow': 12.1,
        'vibration': 0.2,
        'g_load': 1.01,
        'cht': 380.0,
        'egt': 1300.0,
        'oil_temp': 205.0,
        'aileron': 0.01,
        'elevator': 0.0,
        'rudder': 0.0
    }
    run_detection_scenario(
        "Normal Operations",
        normal_telemetry,
        FlightPhase.CRUISE
    )

    print("\n✅ All scenarios complete.")


if __name__ == "__main__":
    main()