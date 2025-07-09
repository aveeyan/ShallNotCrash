#!/usr/bin/env python3
"""
Training Script - Final Working Version
"""
import numpy as np
from collections import Counter
from pr1_pattern_types import EmergencyPattern, AnomalyScore
from pr2_feature_extractor import FeatureExtractor
from pr3_ml_models import MLModelManager
import os

def generate_training_data(samples_per_pattern=125):
    """Generate balanced training data with all pattern types"""
    samples = []
    pattern_types = list(EmergencyPattern)
    
    for pattern in pattern_types:
        for _ in range(samples_per_pattern):
            # Base normal values
            telemetry = {
                'rpm': np.random.normal(2300, 100),
                'oil_pressure': np.random.normal(35, 3),
                'vibration': np.random.uniform(0.5, 1.2),
                'cht': np.random.normal(300, 20),
                'altitude': np.random.normal(5000, 500),
            }
            
            # Modify values for non-normal patterns
            if pattern != EmergencyPattern.NORMAL:
                telemetry['rpm'] *= 1.5 + np.random.uniform(-0.2, 0.2)
                telemetry['oil_pressure'] *= 0.5 + np.random.uniform(-0.1, 0.1)
                telemetry['vibration'] *= 1.5 + np.random.uniform(-0.2, 0.2)
            
            # Calculate anomaly scores and severity
            rpm_severity = min(1.0, abs(telemetry['rpm'] - 2300) / 500)
            oil_severity = min(1.0, abs(telemetry['oil_pressure'] - 35) / 10)
            
            anomalies = {
                'rpm': AnomalyScore(
                    is_anomaly=pattern != EmergencyPattern.NORMAL,
                    normalized_score=np.clip(
                        (0.7 if pattern != EmergencyPattern.NORMAL else 0.2) + np.random.uniform(-0.1, 0.1),
                        0, 1
                    ),
                    severity=rpm_severity
                ),
                'oil_pressure': AnomalyScore(
                    is_anomaly=pattern != EmergencyPattern.NORMAL,
                    normalized_score=np.clip(
                        (0.6 if pattern != EmergencyPattern.NORMAL else 0.2) + np.random.uniform(-0.1, 0.1),
                        0, 1
                    ),
                    severity=oil_severity
                )
            }
            
            samples.append({
                'telemetry': telemetry,
                'anomaly_scores': anomalies,
                'correlation_data': {
                    'engine-fuel': np.random.uniform(0.1, 0.8),
                    'engine-structural': np.random.uniform(0.1, 0.9)
                },
                'pattern_label': pattern.value  # Store as integer
            })
    
    return samples

def train_system():
    """Complete training workflow"""
    # Initialize components
    feature_extractor = FeatureExtractor(window_size=30)
    ml_models = MLModelManager()

    # 1. Generate and prepare training data
    print("Generating training data...")
    raw_data = generate_training_data()
    processed_data = []
    
    print("Extracting features...")
    for sample in raw_data:
        features = feature_extractor.extract(
            telemetry=sample['telemetry'],
            anomalies=sample['anomaly_scores'],
            correlation_data=sample['correlation_data']
        )
        processed_data.append({
            'features': features,
            'pattern_label': sample['pattern_label']  # Already an integer
        })

    # Prepare data for training
    X = np.array([list(sample['features'].values()) for sample in processed_data])
    y = np.array([sample['pattern_label'] for sample in processed_data])

    print("\n=== Data Shapes ===")
    print(f"Features shape: {X.shape}")
    print(f"Labels shape: {y.shape}")

    # 2. Train models
    print("\nTraining ML models...")
    train_results = ml_models.train(X, y, validation_split=0.2)
    
    if not train_results['success']:
        raise RuntimeError(f"Training failed: {train_results.get('error')}")

    print(f"\nTraining successful!")
    print(f"Validation accuracy: {train_results['accuracy']:.2f}")

    # 3. Save models
    model_path = "models/c172p_emergency_model.joblib"
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    
    if ml_models.save(model_path):
        print(f"\nModels saved successfully to {model_path}")
    else:
        print("\nFailed to save models")

if __name__ == "__main__":
    train_system()