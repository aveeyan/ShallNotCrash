#!/usr/bin/env python3
"""
E143: Mid-Flight Emergency Detection Example (Robust Version)

This script demonstrates how to use the ShallNotCrash Emergency Coordinator
to detect in-flight emergencies using simulated telemetry data.

It includes a path correction mechanism to ensure that the 'shallnotcrash'
package can be imported correctly, regardless of how the script is run.

It simulates a flight that starts under normal conditions and then
experiences a sudden engine failure, triggering an emergency detection.

To Run:
- Navigate to the project's root directory.
- Execute: python3 examples/E143_midflight_emergencies.py
"""

# --- [START] Robust Path Correction ---
# This block ensures that the script can find the 'shallnotcrash' package.
import sys
import os

# Get the absolute path of the directory containing this script (examples/).
# Then, get the parent directory of that, which is the project root.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Prepend the project root to Python's path.
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# --- [END] Robust Path Correction ---


import time
import random
import logging
from typing import Dict, Any

# Configure basic logging to see output from the module and the script
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Imports from the shallnotcrash emergency module ---
# These imports will now succeed thanks to the path correction above.
from shallnotcrash.emergency.core import detect_emergency
from shallnotcrash.emergency.analyzers.anomaly_detector import FlightPhase


def get_nominal_telemetry() -> Dict[str, float]:
    """Generates a sample of normal flight telemetry, simulating minor fluctuations."""
    return {
        # Engine Parameters
        'rpm': 2400 + random.uniform(-50, 50),
        'oil_pressure': 75.0 + random.uniform(-5, 5),
        'cht': 380.0 + random.uniform(-10, 10),
        'egt': 1400.0 + random.uniform(-20, 20),
        'oil_temp': 200.0 + random.uniform(-5, 5),
        # Shared Parameters (Engine/Structural)
        'vibration': 0.2 + random.uniform(-0.1, 0.1),
        # Fuel Parameters
        'fuel_flow': 12.5 + random.uniform(-1, 1),
        # Structural Parameters
        'g_load': 1.0 + random.uniform(-0.05, 0.05),
        'aileron': 0.0 + random.uniform(-0.02, 0.02),
        'elevator': 0.0 + random.uniform(-0.02, 0.02),
        'rudder': 0.0 + random.uniform(-0.02, 0.02),
    }

def get_engine_failure_telemetry() -> Dict[str, float]:
    """Generates a sample of telemetry indicative of a sudden engine failure."""
    return {
        # Engine Parameters - showing failure
        'rpm': 0.0,
        'oil_pressure': 5.0 + random.uniform(-5, 5),      # Drastically reduced
        'cht': 350.0 - random.uniform(0, 15),             # Cooling down
        'egt': 200.0 - random.uniform(0, 20),             # Cooling down rapidly
        'oil_temp': 180.0 - random.uniform(0, 10),        # Cooling down
        # Shared Parameters - showing severe stress
        'vibration': 4.5 + random.uniform(-0.5, 0.5),     # High vibration spike
        # Fuel Parameters - engine is off
        'fuel_flow': 0.0,
        # Structural Parameters - simulating pilot reaction
        'g_load': 0.8 + random.uniform(-0.05, 0.05),      # Unsettled flight
        'aileron': 0.05 + random.uniform(-0.02, 0.02),    # Corrective input
        'elevator': -0.05 + random.uniform(-0.02, 0.02),  # Corrective input
        'rudder': 0.1 + random.uniform(-0.02, 0.02),      # Corrective input
    }

def simulate_anomaly_detector(telemetry: Dict[str, float], is_emergency: bool) -> Dict[str, Any]:
    """
    Simulates the output of the AnomalyDetector component.

    As per core.py, the EmergencyCoordinator ACCEPTS pre-computed anomaly scores.
    This function generates low scores for normal telemetry and high scores for
    parameters affected by the simulated emergency.
    """
    anomaly_scores = {}
    if not is_emergency:
        # For normal flight, all anomaly scores are very low.
        for param in telemetry.keys():
            anomaly_scores[param] = {'score': random.uniform(0.0, 0.15)}
    else:
        # During an emergency, certain parameters have very high anomaly scores.
        emergency_params = {'rpm', 'oil_pressure', 'fuel_flow', 'vibration', 'egt'}
        for param in telemetry.keys():
            if param in emergency_params:
                anomaly_scores[param] = {'score': random.uniform(0.9, 1.0)}
            else:
                # Other parameters remain normal.
                anomaly_scores[param] = {'score': random.uniform(0.0, 0.2)}

    return anomaly_scores


def run_flight_simulation():
    """
    Main simulation loop.

    This function simulates a flight for 15 seconds. The first 5 seconds are
    normal, after which an engine failure is injected to test the detection pipeline.
    """
    logger.info("--- Starting Mid-Flight Emergency Simulation ---")
    flight_duration_seconds = 15
    emergency_time_seconds = 5
    is_emergency_active = False

    for i in range(flight_duration_seconds):
        logger.info(f"--- [T+{i:02d}s] Simulating next telemetry frame ---")

        if not is_emergency_active and i >= emergency_time_seconds:
            logger.warning("!!! INJECTING SIMULATED ENGINE FAILURE EVENT !!!")
            is_emergency_active = True

        # Step 1: Get raw telemetry from the aircraft (simulated here).
        if is_emergency_active:
            current_telemetry = get_engine_failure_telemetry()
        else:
            current_telemetry = get_nominal_telemetry()

        # Step 2: Get anomaly scores from the anomaly detector (simulated here).
        anomaly_scores = simulate_anomaly_detector(current_telemetry, is_emergency_active)

        # Step 3: Call the public detection function with the data.
        flight_phase = FlightPhase.CRUISE

        logger.info("Calling Emergency Coordinator with new data...")
        emergency_result = detect_emergency(
            telemetry=current_telemetry,
            anomaly_scores=anomaly_scores,
            flight_phase=flight_phase
        )

        # Step 4: Display the final result from the coordinator.
        print("\n" + "="*40)
        print(f"      COORDINATOR RESULT AT T+{i:02d}s")
        print("="*40)
        print(f"  Detected Pattern:      {emergency_result['pattern_type']}")
        print(f"  Confidence:            {emergency_result['confidence']:.2f}")
        print(f"  Probability:           {emergency_result['probability']:.2%}")
        print(f"  Contributing Features: {emergency_result['contributing_features']}")
        print("="*40 + "\n")

        time.sleep(1) # Wait for 1 second to simulate real-time processing.

    logger.info("--- Simulation Finished ---")


if __name__ == "__main__":
    run_flight_simulation()