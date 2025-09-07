#!/usr/bin/env python3
"""
Simple example script demonstrating how to use the emergency detection pipeline.
This script simulates a single data point and runs it through the AnomalyDetector,
CorrelationAnalyzer, and PatternRecognizer to get a final prediction.
"""
import logging
import os
import sys

# --- Pathing setup to ensure imports work ---
# This is a critical step to make sure the script can find the 'shallnotcrash' modules
try:
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
except NameError:
    # Fallback for environments where __file__ is not defined
    project_root = os.path.abspath(os.path.join(os.getcwd()))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

# Correcting the model path to match the file saved by training.py
from shallnotcrash.emergency.core import EMERGENCY_COORDINATOR, detect_emergency
from shallnotcrash.emergency.synthetic_data import generate_training_data
from shallnotcrash.emergency.analyzers.anomaly_detector import AnomalyDetector, FlightPhase

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    logging.info("--- Starting Emergency Detection Example ---")

    # The EmergencyCoordinator and AnomalyDetector are already set up as singletons
    # in their respective modules, so you just need to access them.
    # The coordinator will handle loading the model internally.
    
    # 1. Simulate a telemetry data point.
    # We will use the synthetic data generator to create a realistic
    # "Fuel Leak" scenario. The generator also produces the anomaly scores.
    logging.info("Simulating a single 'Fuel Leak' emergency data point...")
    
    # Generate 1 sample with a very low normal flight ratio to force an emergency
    sample = generate_training_data(num_samples=1, normal_flight_ratio=0.0)[0]
    
    # Extract the telemetry and anomaly scores from the generated sample
    telemetry_data = sample['telemetry']
    anomaly_scores = sample['anomaly_scores']
    
    print("\n--- Simulated Telemetry Data ---")
    for key, value in telemetry_data.items():
        print(f"  {key:<15}: {value:.2f}")
    
    print("\n--- Simulated Anomaly Scores ---")
    for key, score in anomaly_scores.items():
        if score.is_anomaly:
            print(f"  {key:<15}: Normalized Score: {score.normalized_score:.2f} | Severity: {score.severity.name}")

    # 2. Run the detection pipeline
    # The `detect_emergency` function orchestrates the entire process.
    logging.info("\nCalling the integrated emergency detection pipeline...")
    final_result = detect_emergency(
        telemetry=telemetry_data,
        anomaly_scores=anomaly_scores,
        flight_phase=FlightPhase.CRUISE # Pass the current flight phase
    )

    # 3. Display the results
    print("\n--- Final Detection Result ---")
    print(f"Detected Pattern: {final_result['pattern_type']}")
    print(f"Prediction Probability: {final_result['probability']:.2f}")
    print(f"Recommended Action: {final_result['recommended_action']}")
    print(f"Contributing Features: {', '.join(final_result['contributing_features'])}")
    
    logging.info("\n--- Emergency detection pipeline complete ---")

if __name__ == '__main__':
    main()
