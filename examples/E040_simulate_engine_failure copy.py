#!/usr/bin/env python3
"""
E040: Emergency Engine Failure Detection Example

This script demonstrates emergency detection using a simplified approach
that doesn't rely on the full ShallNotCrash module structure.
"""

import time
import random
import logging
from typing import Dict, Any, List
from enum import Enum

# Configure basic logging to see output from the module and the script
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FlightPhase(Enum):
    TAKEOFF = "takeoff"
    CLIMB = "climb"
    CRUISE = "cruise"
    DESCENT = "descent"
    LANDING = "landing"

class EmergencyPattern(Enum):
    NORMAL = "normal"
    ENGINE_FAILURE = "engine_failure"
    FUEL_EMERGENCY = "fuel_emergency"
    STRUCTURAL_FAILURE = "structural_failure"
    UNKNOWN = "unknown"

def detect_emergency_simple(telemetry: Dict[str, float], anomaly_scores: Dict[str, Any], flight_phase: FlightPhase) -> Dict[str, Any]:
    """
    Simplified emergency detection function that mimics the real one.
    """
    # Check for engine failure pattern
    if (telemetry.get('rpm', 0) < 500 and 
        telemetry.get('oil_pressure', 0) < 10 and 
        telemetry.get('fuel_flow', 0) < 1.0):
        return {
            'pattern_type': EmergencyPattern.ENGINE_FAILURE.value,
            'confidence': 0.95,
            'probability': 0.98,
            'contributing_features': ['rpm', 'oil_pressure', 'fuel_flow']
        }
    
    # Check for high vibration indicating potential structural issues
    if telemetry.get('vibration', 0) > 3.0:
        return {
            'pattern_type': EmergencyPattern.STRUCTURAL_FAILURE.value,
            'confidence': 0.85,
            'probability': 0.75,
            'contributing_features': ['vibration']
        }
    
    # Check for low fuel flow (potential fuel emergency)
    if telemetry.get('fuel_flow', 0) < 5.0 and flight_phase != FlightPhase.DESCENT:
        return {
            'pattern_type': EmergencyPattern.FUEL_EMERGENCY.value,
            'confidence': 0.7,
            'probability': 0.65,
            'contributing_features': ['fuel_flow']
        }
    
    # Normal operation
    return {
        'pattern_type': EmergencyPattern.NORMAL.value,
        'confidence': 0.9,
        'probability': 0.92,
        'contributing_features': []
    }

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
    """
    logger.info("--- Starting Engine Failure Emergency Simulation ---")
    logger.info("Using simplified emergency detection (bypassing module import issues)")
    
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

        # Step 3: Call our simplified detection function
        flight_phase = FlightPhase.CRUISE

        logger.info("Calling Emergency Detection with new data...")
        emergency_result = detect_emergency_simple(
            telemetry=current_telemetry,
            anomaly_scores=anomaly_scores,
            flight_phase=flight_phase
        )

        # Step 4: Display the final result
        print("\n" + "="*50)
        print(f"      EMERGENCY DETECTION RESULT AT T+{i:02d}s")
        print("="*50)
        print(f"  Detected Pattern:      {emergency_result['pattern_type']}")
        print(f"  Confidence:            {emergency_result['confidence']:.2f}")
        print(f"  Probability:           {emergency_result['probability']:.2%}")
        print(f"  Contributing Features: {emergency_result['contributing_features']}")
        
        # Show some key telemetry values
        print(f"  Key Telemetry:")
        print(f"    RPM: {current_telemetry['rpm']:.0f}")
        print(f"    Oil Pressure: {current_telemetry['oil_pressure']:.1f} psi")
        print(f"    Fuel Flow: {current_telemetry['fuel_flow']:.1f} gph")
        print(f"    Vibration: {current_telemetry['vibration']:.1f} g")
        print("="*50 + "\n")

        time.sleep(1) # Wait for 1 second to simulate real-time processing.

    logger.info("--- Simulation Finished ---")


if __name__ == "__main__":
    run_flight_simulation()
    