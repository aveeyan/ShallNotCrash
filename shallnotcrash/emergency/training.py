#!/usr/bin/env python3
"""
Emergency Detection Model Training Script (V2.1 - Unified Scaler)
"""
import joblib
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
import logging
import os
import sys

# --- PATHING FORTIFICATION ---
try:
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
except NameError:
    project_root = os.path.abspath(os.path.join(os.getcwd()))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from shallnotcrash.emergency.synthetic_data import generate_training_data
from shallnotcrash.emergency.analyzers.pattern_recognizer import PatternRecognizer, EmergencyPattern

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
NUM_SAMPLES = 10000
MODEL_DIR = "models"
MODEL_FILENAME = os.path.join(MODEL_DIR, "c172p_emergency_model_v2.joblib")
TRAINING_SEED = 42

def main():
    logging.info("Starting V2.1 (Unified Scaler) model training process...")

    logging.info(f"Generating {NUM_SAMPLES} synthetic data samples...")
    training_data = generate_training_data(NUM_SAMPLES, seed=TRAINING_SEED)
    
    logging.info("Extracting features from raw data...")
    feature_extractor = PatternRecognizer() 
    features_list = [feature_extractor.extract_features(s['telemetry'], s['anomaly_scores']) for s in training_data]
    labels = [s['pattern_label'] for s in training_data]
        
    X = np.array(features_list)
    y = np.array(labels)
    
    # --- THE FIX: Create a single, unified feature space ---
    # We split the data first to prevent data leakage from the test set into the scaler.
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # Create and fit ONE scaler on the entire training distribution.
    unified_scaler = StandardScaler().fit(X_train)
    X_train_scaled = unified_scaler.transform(X_train)
    X_test_scaled = unified_scaler.transform(X_test)

    # --- STAGE 1: TRAIN THE TRIAGE CLASSIFIER ---
    logging.info("--- Training Stage 1: Triage Classifier ---")
    y_train_triage = np.array([0 if label == EmergencyPattern.NORMAL.value else 1 for label in y_train])
    y_test_triage = np.array([0 if label == EmergencyPattern.NORMAL.value else 1 for label in y_test])
    
    triage_classifier = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced').fit(X_train_scaled, y_train_triage)
    y_pred_t = triage_classifier.predict(X_test_scaled)
    logging.info("Triage Classifier Performance:")
    print(classification_report(y_test_triage, y_pred_t, target_names=['NORMAL', 'ABNORMAL']))

    # --- STAGE 2: TRAIN THE SPECIALIST CLASSIFIER ---
    logging.info("--- Training Stage 2: Specialist Classifier ---")
    emergency_indices_train = np.where(y_train != EmergencyPattern.NORMAL.value)[0]
    X_train_specialist = X_train_scaled[emergency_indices_train]
    y_train_specialist = y_train[emergency_indices_train]
    
    specialist_classifier = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced').fit(X_train_specialist, y_train_specialist)

    # Evaluate on the emergency-only portion of the test set
    emergency_indices_test = np.where(y_test != EmergencyPattern.NORMAL.value)[0]
    X_test_specialist = X_test_scaled[emergency_indices_test]
    y_test_specialist = y_test[emergency_indices_test]
    
    y_pred_s = specialist_classifier.predict(X_test_specialist)
    logging.info("Specialist Classifier Performance (on emergencies only):")
    emergency_names = [p.name for p in EmergencyPattern if p != EmergencyPattern.NORMAL]
    print(classification_report(y_test_specialist, y_pred_s, target_names=emergency_names, labels=[p.value for p in EmergencyPattern if p != EmergencyPattern.NORMAL], zero_division=0))

    # --- Save the UNIFIED Model Artifact ---
    logging.info(f"Saving the complete unified-scaler model artifact to {MODEL_FILENAME}")
    model_artifact = {
        'scaler': unified_scaler, # THE FIX: Save the single scaler
        'triage_classifier': triage_classifier,
        'specialist_classifier': specialist_classifier,
        'model_version': '2.3-unified'
    }
    
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model_artifact, MODEL_FILENAME)
    
    logging.info("Training complete.")

if __name__ == '__main__':
    main()
