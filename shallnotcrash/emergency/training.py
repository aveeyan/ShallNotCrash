#!/usr/bin/env python3
"""
Emergency Detection Model Training Script (V3.0 - Hyperparameter Tuning)
This version integrates GridSearchCV to find the optimal hyperparameters for
both the triage and specialist classifiers, maximizing predictive accuracy.
"""
import joblib
import numpy as np
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
import logging
import os
import sys

# --- (Pathing setup is the same) ---
try:
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root not in sys.path: sys.path.insert(0, project_root)
except NameError:
    project_root = os.path.abspath(os.path.join(os.getcwd()))
    if project_root not in sys.path: sys.path.insert(0, project_root)

from shallnotcrash.emergency.synthetic_data import generate_training_data
from shallnotcrash.emergency.analyzers.pattern_recognizer import PatternRecognizer, EmergencyPattern

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
NUM_SAMPLES = 10000
MODEL_DIR = "models"
MODEL_FILENAME = os.path.join(MODEL_DIR, "c172p_emergency_model_v3_tuned.joblib")
TRAINING_SEED = 42

def main():
    logging.info("Starting V3.0 (Hyperparameter Tuning) model training process...")

    # --- (Data generation and feature extraction are the same) ---
    logging.info(f"Generating {NUM_SAMPLES} synthetic data samples...")
    training_data = generate_training_data(NUM_SAMPLES, seed=TRAINING_SEED)
    
    logging.info("Extracting features from raw data...")
    feature_extractor = PatternRecognizer() 
    features_list = [feature_extractor.extract_features(s['telemetry'], s['anomaly_scores']) for s in training_data]
    labels = [s['pattern_label'] for s in training_data]
    X, y = np.array(features_list), np.array(labels)
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    unified_scaler = StandardScaler().fit(X_train)
    X_train_scaled = unified_scaler.transform(X_train)
    X_test_scaled = unified_scaler.transform(X_test)

    # --- [NEW] Define the grid of hyperparameters to test ---
    # These are good starting points for a RandomForest
    param_grid = {
        'n_estimators': [100, 200],         # Number of trees in the forest
        'max_depth': [10, 20, None],        # Maximum depth of the trees
        'min_samples_leaf': [1, 2, 4],      # Minimum samples required at a leaf node
        'max_features': ['sqrt', 'log2']    # Number of features to consider for best split
    }

    # --- STAGE 1: TUNE AND TRAIN THE TRIAGE CLASSIFIER ---
    logging.info("--- Tuning and Training Stage 1: Triage Classifier ---")
    y_train_triage = np.array([0 if label == EmergencyPattern.NORMAL.value else 1 for label in y_train])
    y_test_triage = np.array([0 if label == EmergencyPattern.NORMAL.value else 1 for label in y_test])
    
    # Create the GridSearchCV object
    triage_grid_search = GridSearchCV(
        estimator=RandomForestClassifier(random_state=42, class_weight='balanced'),
        param_grid=param_grid,
        cv=3,           # 3-fold cross-validation
        n_jobs=-1,      # Use all available CPU cores
        verbose=1       # Print progress
    )
    
    # Run the search
    triage_grid_search.fit(X_train_scaled, y_train_triage)
    
    # The best model is found and stored in .best_estimator_
    best_triage_classifier = triage_grid_search.best_estimator_
    
    logging.info(f"Best Triage Params found: {triage_grid_search.best_params_}")
    y_pred_t = best_triage_classifier.predict(X_test_scaled)
    logging.info("Triage Classifier Performance (with best params):")
    print(classification_report(y_test_triage, y_pred_t, target_names=['NORMAL', 'ABNORMAL']))

    # --- STAGE 2: TUNE AND TRAIN THE SPECIALIST CLASSIFIER ---
    logging.info("--- Tuning and Training Stage 2: Specialist Classifier ---")
    emergency_indices_train = np.where(y_train != EmergencyPattern.NORMAL.value)[0]
    X_train_specialist = X_train_scaled[emergency_indices_train]
    y_train_specialist = y_train[emergency_indices_train]
    
    # Repeat the grid search for the specialist model
    specialist_grid_search = GridSearchCV(
        estimator=RandomForestClassifier(random_state=42, class_weight='balanced'),
        param_grid=param_grid, cv=3, n_jobs=-1, verbose=1
    )
    specialist_grid_search.fit(X_train_specialist, y_train_specialist)
    best_specialist_classifier = specialist_grid_search.best_estimator_

    logging.info(f"Best Specialist Params found: {specialist_grid_search.best_params_}")
    emergency_indices_test = np.where(y_test != EmergencyPattern.NORMAL.value)[0]
    X_test_specialist = X_test_scaled[emergency_indices_test]
    y_test_specialist = y_test[emergency_indices_test]
    y_pred_s = best_specialist_classifier.predict(X_test_specialist)
    logging.info("Specialist Classifier Performance (with best params):")
    emergency_names = [p.name for p in EmergencyPattern if p != EmergencyPattern.NORMAL]
    print(classification_report(y_test_specialist, y_pred_s, target_names=emergency_names, labels=[p.value for p in EmergencyPattern if p != EmergencyPattern.NORMAL], zero_division=0))

    # --- Save the TUNED Model Artifact ---
    logging.info(f"Saving the complete tuned model artifact to {MODEL_FILENAME}")
    model_artifact = {
        'scaler': unified_scaler,
        'triage_classifier': best_triage_classifier,
        'specialist_classifier': best_specialist_classifier,
        'model_version': '3.0-tuned'
    }
    
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model_artifact, MODEL_FILENAME)
    
    logging.info("Training complete.")

if __name__ == '__main__':
    main()
