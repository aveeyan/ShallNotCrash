#!/usr/bin/env python3
"""
Model Training and Persistence for the Emergency Pattern Recognizer.

This script provides a clear and straightforward workflow for training the machine
learning models used by the PatternRecognizer. It handles data generation,
delegates training to the analyzer, and saves the resulting model artifacts.
"""
import os
import numpy as np
import logging
from typing import List, Dict, Any

# --- Import the components we need ---

# We only need to import the analyzer that requires training.
from .analyzers.pattern_recognizer import PATTERN_RECOGNIZER, EmergencyPattern

# Import the data structures used for generating training data.
from .analyzers.anomaly_detector import AnomalyScore, AnomalySeverity, FlightPhase

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Data Generation ---

def generate_training_data(samples_per_pattern: int = 250) -> List[Dict[str, Any]]:
    """
    Generates realistic, synthetic training data for various emergency patterns.

    This function simulates telemetry data with noise, drift, and pattern-specific
    characteristics to create a robust training set.

    Args:
        samples_per_pattern: The number of data samples to generate for each pattern.

    Returns:
        A list of training samples, where each sample is a dictionary containing
        telemetry, anomaly scores, correlation data, and a pattern label.
    """
    logger.info(f"Generating {samples_per_pattern * len(EmergencyPattern)} training samples...")
    training_data = []
    np.random.seed(42)  # for reproducibility

    base_telemetry = {'rpm': 2350, 'oil_pressure': 65, 'fuel_flow': 12, 'vibration': 0.2, 'g_load': 1.0}

    for pattern in EmergencyPattern:
        for _ in range(samples_per_pattern):
            telemetry = base_telemetry.copy()
            anomaly_scores = {}
            
            # --- Apply pattern-specific characteristics ---
            if pattern == EmergencyPattern.ENGINE_DEGRADATION:
                telemetry['rpm'] -= np.random.uniform(100, 400)
                telemetry['oil_pressure'] -= np.random.uniform(10, 25)
                telemetry['vibration'] += np.random.uniform(0.5, 1.5)
                anomaly_scores['rpm'] = AnomalyScore('rpm', telemetry['rpm'], 2400, 400, 2.5, True, AnomalySeverity.CRITICAL, FlightPhase.CRUISE)
                anomaly_scores['oil_pressure'] = AnomalyScore('oil_pressure', telemetry['oil_pressure'], 70, 20, 2.0, True, AnomalySeverity.WARNING, FlightPhase.CRUISE)

            elif pattern == EmergencyPattern.FUEL_LEAK:
                telemetry['fuel_flow'] += np.random.uniform(3, 8) # Engine compensates for leak
                # This would also manifest as a fuel quantity imbalance, a feature the recognizer can learn.
                anomaly_scores['fuel_flow'] = AnomalyScore('fuel_flow', telemetry['fuel_flow'], 12, 5, 1.8, True, AnomalySeverity.WARNING, FlightPhase.CRUISE)

            elif pattern == EmergencyPattern.STRUCTURAL_FATIGUE:
                telemetry['vibration'] += np.random.uniform(1.0, 3.0)
                telemetry['g_load'] += np.random.uniform(-0.3, 0.3) # Uncommanded pitch changes
                anomaly_scores['vibration'] = AnomalyScore('vibration', telemetry['vibration'], 0.2, 2.0, 3.0, True, AnomalySeverity.EMERGENCY, FlightPhase.CRUISE)

            # Add random noise to all parameters to make the model more robust
            for key in telemetry:
                telemetry[key] += np.random.normal(0, telemetry[key] * 0.05) # 5% noise

            sample = {
                'telemetry': telemetry,
                'anomaly_scores': anomaly_scores,
                'correlation_data': {'engine-fuel': np.random.rand()}, # Simplified for this example
                'pattern_label': pattern.value
            }
            training_data.append(sample)
    
    np.random.shuffle(training_data)
    logger.info("Training data generation complete.")
    return training_data

# --- Main Training Workflow ---

def main():
    """
    Executes the main training workflow:
    1. Generates training data.
    2. Calls the PatternRecognizer's training method.
    3. Saves the trained model artifacts.
    """
    # Step 1: Generate or load your training data.
    # The logic here can be as complex as needed, but the output format is standardized.
    training_data = generate_training_data()

    if not training_data:
        logger.error("No training data was generated. Aborting.")
        return

    # Step 2: Train the models.
    # We delegate the entire training process to the PatternRecognizer class.
    # It already knows how to process the data and train its internal models.
    logger.info("Starting model training...")
    PATTERN_RECOGNIZER.train_models(training_data)
    logger.info("Model training complete.")

    # Step 3: Save the trained models.
    # The path where the final model will be saved.
    model_path = "models/c172p_emergency_model.joblib"
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    
    logger.info(f"Saving models to {model_path}...")
    PATTERN_RECOGNIZER.save_models(model_path)
    logger.info("Models saved successfully.")
    print(f"\n✅ Training complete. Model saved to '{model_path}'.")


if __name__ == "__main__":
    main()
