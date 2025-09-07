# shallnotcrash/emergency/training_v2.py

#!/usr/bin/env python3
"""
New Emergency Detection Model Training - Improved Version
"""
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
import logging
import os
import sys

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shallnotcrash.emergency.synthetic_data import generate_training_data
from shallnotcrash.emergency.analyzers.pattern_recognizer import EmergencyPattern

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ImprovedTrainer:
    def __init__(self):
        # [MODIFIED] Add new features to the list
        self.telemetry_keys = [
            'rpm', 'oil_pressure', 'oil_temp', 'cht', 'egt', 'fuel_flow', 
            'g_load', 'vibration', 'bus_volts', 'control_asymmetry',
            'airspeed', 'yaw_rate', 'roll', 'pitch'
        ]
        
    def extract_features(self, sample):
        """Extract features from a training sample"""
        telemetry = sample['telemetry']
        anomaly_scores = sample['anomaly_scores']
        
        features = []
        
        # Telemetry values (normalized)
        for key in self.telemetry_keys:
            value = telemetry.get(key, 0.0)
            # [MODIFIED] Add normalization logic for new features
            if key == 'rpm': features.append(value / 2700.0)
            elif key == 'oil_pressure': features.append(value / 100.0)
            elif key == 'oil_temp': features.append(value / 300.0)
            elif key == 'cht': features.append(value / 500.0)
            elif key == 'egt': features.append(value / 1500.0)
            elif key == 'fuel_flow': features.append(value / 15.0)
            elif key == 'g_load': features.append((value + 3.0) / 6.0)
            elif key == 'vibration': features.append(min(value / 1.0, 1.0))
            elif key == 'bus_volts': features.append(value / 30.0)
            elif key == 'control_asymmetry': features.append(min(value / 5.0, 1.0))
            elif key == 'airspeed': features.append(value / 200.0)
            elif key == 'yaw_rate': features.append(value / 180.0) # Normalize by 180 deg/s
            elif key == 'roll': features.append(value / 180.0)   # Normalize by 180 deg
            elif key == 'pitch': features.append(value / 90.0)    # Normalize by 90 deg
        
        # Anomaly scores
        for key in self.telemetry_keys:
            score_data = anomaly_scores.get(key)
            if hasattr(score_data, 'normalized_score'):
                features.append(score_data.normalized_score / 5.0)
            else:
                features.append(0.0)
        
        return np.array(features)
    
    def train(self, num_samples=20000, test_size=0.2, random_state=42):
        """Train the improved model"""
        logging.info(f"Generating {num_samples} training samples...")
        data = generate_training_data(num_samples, seed=random_state)
        
        logging.info("Extracting features...")
        X = np.array([self.extract_features(sample) for sample in data])
        y = np.array([sample['pattern_label'] for sample in data])
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Train triage classifier (Normal vs Emergency)
        y_train_triage = np.where(y_train == EmergencyPattern.NORMAL.value, 0, 1)
        y_test_triage = np.where(y_test == EmergencyPattern.NORMAL.value, 0, 1)
        
        logging.info("Training triage classifier...")
        triage_clf = RandomForestClassifier(
            n_estimators=200,
            max_depth=20,
            min_samples_leaf=2,
            max_features='sqrt',
            random_state=random_state,
            class_weight='balanced'
        )
        triage_clf.fit(X_train_scaled, y_train_triage)
        
        # Train specialist classifier (Emergency types only)
        emergency_mask = y_train != EmergencyPattern.NORMAL.value
        X_train_emergency = X_train_scaled[emergency_mask]
        y_train_emergency = y_train[emergency_mask]
        
        logging.info("Training specialist classifier...")
        specialist_clf = RandomForestClassifier(
            n_estimators=200,
            max_depth=15,
            min_samples_leaf=1,
            max_features='log2',
            random_state=random_state,
            class_weight='balanced'
        )
        specialist_clf.fit(X_train_emergency, y_train_emergency)
        
        # Evaluate models
        self._evaluate_models(triage_clf, specialist_clf, X_test_scaled, y_test, 
                             y_test_triage, scaler)
        
        # Save model
        model_artifact = {
            'scaler': scaler,
            'triage_classifier': triage_clf,
            'specialist_classifier': specialist_clf,
            'feature_names': self.telemetry_keys,
            'model_version': '2.0-improved'
        }
        
        model_dir = "models"
        os.makedirs(model_dir, exist_ok=True)
        model_path = os.path.join(model_dir, "c172p_emergency_model_improved.joblib")
        
        joblib.dump(model_artifact, model_path)
        logging.info(f"Model saved to {model_path}")
        
        return model_artifact
    
    def _evaluate_models(self, triage_clf, specialist_clf, X_test, y_test, 
                        y_test_triage, scaler):
        """Evaluate model performance"""
        # Triage evaluation
        triage_pred = triage_clf.predict(X_test)
        triage_acc = accuracy_score(y_test_triage, triage_pred)
        logging.info(f"Triage accuracy: {triage_acc:.4f}")
        
        # Specialist evaluation (only on emergency samples)
        emergency_mask = y_test != EmergencyPattern.NORMAL.value
        if np.any(emergency_mask):
            X_emergency = X_test[emergency_mask]
            y_emergency = y_test[emergency_mask]
            
            specialist_pred = specialist_clf.predict(X_emergency)
            specialist_acc = accuracy_score(y_emergency, specialist_pred)
            logging.info(f"Specialist accuracy: {specialist_acc:.4f}")
            
            # Detailed classification report
            emergency_names = [p.name for p in EmergencyPattern if p != EmergencyPattern.NORMAL]
            emergency_values = [p.value for p in EmergencyPattern if p != EmergencyPattern.NORMAL]
            
            print("\nSpecialist Classification Report:")
            print(classification_report(y_emergency, specialist_pred, 
                                      target_names=emergency_names,
                                      labels=emergency_values,
                                      zero_division=0))
        
        # Full pipeline evaluation
        full_pred = self._full_pipeline_prediction(triage_clf, specialist_clf, X_test)
        full_acc = accuracy_score(y_test, full_pred)
        logging.info(f"Full pipeline accuracy: {full_acc:.4f}")
        
        print("\nFull Pipeline Classification Report:")
        all_names = [p.name for p in EmergencyPattern]
        all_values = [p.value for p in EmergencyPattern]
        print(classification_report(y_test, full_pred, 
                                  target_names=all_names,
                                  labels=all_values,
                                  zero_division=0))
    
    def _full_pipeline_prediction(self, triage_clf, specialist_clf, X_test):
        """Simulate the full two-stage prediction pipeline"""
        predictions = []
        
        for i in range(len(X_test)):
            # Stage 1: Triage
            triage_pred = triage_clf.predict(X_test[i].reshape(1, -1))[0]
            
            if triage_pred == 0:  # Normal
                predictions.append(EmergencyPattern.NORMAL.value)
            else:  # Emergency - use specialist
                specialist_pred = specialist_clf.predict(X_test[i].reshape(1, -1))[0]
                predictions.append(specialist_pred)
        
        return np.array(predictions)

def main():
    trainer = ImprovedTrainer()
    trainer.train(num_samples=25000, random_state=42)

if __name__ == '__main__':
    main()
    