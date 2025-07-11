#!/usr/bin/env python3
"""
Example Usage of Emergency Pattern Recognition System
"""
import os
import numpy as np
from train_emergency_detector import (
    generate_training_data,
    FeatureExtractor,
    MLModelManager,
    EmergencyPattern
)

def main():
    # 1. Initialize components
    print("Initializing emergency pattern recognition system...")
    feature_extractor = FeatureExtractor(window_size=30)
    model_manager = MLModelManager()
    
    # 2. Generate and prepare training data
    print("\nGenerating training data...")
    training_data = generate_training_data()
    
    # Process samples through feature extractor
    processed_data = []
    for sample in training_data:
        features = feature_extractor.extract(
            telemetry=sample['telemetry'],
            anomalies=sample['anomaly_scores'],
            correlation_data=sample['correlation_data']
        )
        processed_data.append({
            'features': features,
            'pattern_label': sample['pattern_label']
        })
    
    # 3. Train the model
    print("\nTraining model...")
    train_results = model_manager.train(processed_data, validation_split=0.2)
    
    if not train_results['success']:
        print(f"Training failed: {train_results.get('error')}")
        return
    
    print("\nTraining Results:")
    print(f"Training Accuracy: {train_results['training_accuracy']:.2f}")
    print(f"Validation Accuracy: {train_results['validation_accuracy']:.2f}")
    print("\nClassification Report:")
    print(train_results['validation_report'])
    
    # 4. Save the trained model
    model_path = "emergency_model.joblib"
    if model_manager.save(model_path):
        print(f"\nModel saved successfully to {model_path}")
    else:
        print("\nFailed to save model")
        return
    
    # 5. Example Predictions
    print("\nRunning example predictions...")
    
    # Create some test samples
    test_samples = [
        # Normal operation
        {
            'telemetry': {
                'rpm': 2300,
                'oil_pressure': 35,
                'vibration': 0.8,
                'cht': 300,
                'fuel_flow': 15,
                'altitude': 5000
            },
            'anomaly_scores': {
                'rpm': {'is_anomaly': False, 'normalized_score': 0.1, 'severity': 0},
                'oil_pressure': {'is_anomaly': False, 'normalized_score': 0.05, 'severity': 0}
            },
            'correlation_data': {
                'engine-fuel': 0.3,
                'engine-structural': 0.2
            }
        },
        # Engine degradation
        {
            'telemetry': {
                'rpm': 1900,
                'oil_pressure': 25,
                'vibration': 2.5,
                'cht': 350,
                'fuel_flow': 18,
                'altitude': 4500
            },
            'anomaly_scores': {
                'rpm': {'is_anomaly': True, 'normalized_score': 0.8, 'severity': 3},
                'oil_pressure': {'is_anomaly': True, 'normalized_score': 0.7, 'severity': 3}
            },
            'correlation_data': {
                'engine-fuel': 0.6,
                'engine-structural': 0.4
            }
        }
    ]
    
    # Make predictions
    for i, sample in enumerate(test_samples):
        features = feature_extractor.extract(
            telemetry=sample['telemetry'],
            anomalies=sample['anomaly_scores'],
            correlation_data=sample['correlation_data']
        )
        
        prediction = model_manager.predict(features)
        pattern_name = EmergencyPattern(prediction).name
        
        print(f"\nSample {i+1} Prediction: {pattern_name}")
        print("Feature Values:")
        for k, v in features.items():
            print(f"  {k}: {v:.4f}")
    
    print("\nEmergency pattern recognition demo complete!")

if __name__ == "__main__":
    main()